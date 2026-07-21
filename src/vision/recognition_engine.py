from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
import time
import copy
import concurrent.futures

from src.vision.frame_context import FrameContext
from src.vision.vision_engine import VisionEngine


class RecognitionEngine:
    """
    Motor de reconocimiento impulsado por caché asíncrona y extracción en background.
    Evita caídas de FPS delegando las extracciones pesadas a un hilo secundario.
    """

    def __init__(
        self,
        known_encodings: List[np.ndarray],
        known_names: List[str],
        threshold: float,
    ):
        self.known_encodings = [
            np.asarray(e, dtype=np.float32) for e in known_encodings
        ]
        self.known_names = known_names
        self.threshold = threshold

        self.track_cache: Dict[int, Dict[str, Any]] = {}
        self.cache_ttl = 1000
        
        # Ejecutor para extracción asíncrona de embeddings (1 worker es suficiente para no saturar CPU)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.pending_extractions = set()

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        denom = np.linalg.norm(emb1) * np.linalg.norm(emb2)
        if denom == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / denom)

    def _async_extract_and_match(self, frame, face, track_id, vision_engine):
        try:
            vision_engine.extract_embedding(frame, face)
            current_time = time.time()
            
            if face.embedding is None:
                prev_attempts = self.track_cache.get(track_id, {}).get("attempts", 0)
                self.track_cache[track_id] = {
                    "identity": "Desconocido",
                    "confidence": 0.0,
                    "last_validation": current_time,
                    "attempts": prev_attempts + 1,
                }
                return

            best_similarity = -1.0
            best_index = -1

            for i, known_embedding in enumerate(self.known_encodings):
                similarity = self.cosine_similarity(face.embedding, known_embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_index = i

            is_recognized = best_index >= 0 and best_similarity >= self.threshold
            identity = self.known_names[best_index] if is_recognized else "Desconocido"
            confidence = round(best_similarity * 100, 2)

            prev_attempts = self.track_cache.get(track_id, {}).get("attempts", 0)
            new_attempts = prev_attempts + 1 if not is_recognized else 0

            self.track_cache[track_id] = {
                "identity": identity,
                "confidence": confidence,
                "last_validation": current_time,
                "attempts": new_attempts,
            }
        except Exception as e:
            print(f"[Error Recognition Background] {e}")
        finally:
            self.pending_extractions.discard(track_id)

    def process(
        self, frame: np.ndarray, context: FrameContext, vision_engine: VisionEngine
    ) -> FrameContext:

        if not self.known_encodings:
            return context

        current_time = time.time()

        for face in context.faces:
            raw_track_id = getattr(face, "track_id", None)

            if raw_track_id is None:
                continue

            track_id: int = int(raw_track_id)
            needs_extraction = False
            use_cache = False

            if track_id in self.track_cache:
                cached = self.track_cache[track_id]
                time_since_validation = current_time - cached.get("last_validation", 0)
                attempts = cached.get("attempts", 1)

                if cached["identity"] != "Desconocido":
                    if time_since_validation > 3.0:
                        needs_extraction = True
                    else:
                        use_cache = True
                else:
                    cooldown = 1.5 if attempts <= 2 else 10.0
                    if time_since_validation > cooldown:
                        needs_extraction = True
                    else:
                        use_cache = True
            else:
                needs_extraction = True

            # Si necesitamos extracción, la mandamos a background
            if needs_extraction:
                if track_id not in self.pending_extractions:
                    self.pending_extractions.add(track_id)
                    
                    # Copiamos frame y face para aislar la memoria del hilo secundario
                    frame_copy = frame.copy()
                    face_copy = copy.copy(face)
                    
                    self.executor.submit(
                        self._async_extract_and_match, 
                        frame_copy, face_copy, track_id, vision_engine
                    )
                
                # Mientras se extrae, usamos caché si hay, si no "Desconocido"
                if track_id in self.track_cache:
                    use_cache = True
                else:
                    face.identity = "Calculando..."
                    face.confidence = 0.0
                    face.recognition_state = "PROCESSING"

            if use_cache:
                face.identity = self.track_cache[track_id]["identity"]
                face.confidence = self.track_cache[track_id]["confidence"]
                face.recognition_state = (
                    "RECOGNIZED" if face.identity != "Desconocido" else "UNKNOWN"
                )

        # Purga de memoria para evitar saturación
        if len(self.track_cache) > self.cache_ttl:
            purge_count = len(self.track_cache) - int(self.cache_ttl * 0.8)
            oldest_keys = list(self.track_cache.keys())[:purge_count]
            for key in oldest_keys:
                self.track_cache.pop(key, None)

        return context
