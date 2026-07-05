from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
import time

from src.vision.frame_context import FrameContext
from src.vision.vision_engine import VisionEngine


class RecognitionEngine:
    """
    Motor de reconocimiento impulsado por caché asíncrona.
    Evita caídas de FPS limitando las extracciones pesadas a 1 por frame
    y soluciona los cruces de identidad re-validando periódicamente.
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

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        denom = np.linalg.norm(emb1) * np.linalg.norm(emb2)
        if denom == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / denom)

    def process(
        self, frame: np.ndarray, context: FrameContext, vision_engine: VisionEngine
    ) -> FrameContext:

        if not self.known_encodings:
            return context

        current_time = time.time()

        # Bandera para limitar el estrés de la CPU. Solo permitimos 1 extracción pesada por frame.
        extraction_done_this_frame = False

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

                if cached["identity"] != "Desconocido":
                    # Si es conocido, re-validar cada 3.0 segundos para corregir errores del tracker por oclusión
                    if time_since_validation > 3.0:
                        needs_extraction = True
                    else:
                        use_cache = True
                else:
                    # Si es desconocido, re-validar cada 1.5 segundos
                    if time_since_validation > 1.5:
                        needs_extraction = True
                    else:
                        use_cache = True
            else:
                # Rostro completamente nuevo para el tracker
                needs_extraction = True

            # Si necesitamos extraer pero la CPU ya hizo una extracción en este frame,
            # posponemos la extracción para el siguiente frame y usamos la caché temporalmente.
            if (
                needs_extraction
                and extraction_done_this_frame
                and track_id in self.track_cache
            ):
                needs_extraction = False
                use_cache = True

            if use_cache and not needs_extraction:
                face.identity = self.track_cache[track_id]["identity"]
                face.confidence = self.track_cache[track_id]["confidence"]
                face.recognition_state = (
                    "RECOGNIZED" if face.identity != "Desconocido" else "UNKNOWN"
                )
                continue

            # ==========================================
            # EXTRACCIÓN PESADA NEURONAL
            # ==========================================
            vision_engine.extract_embedding(frame, face)
            extraction_done_this_frame = (
                True  # Bloqueamos más extracciones en este frame
            )

            if face.embedding is None:
                self.track_cache[track_id] = {
                    "identity": "Desconocido",
                    "confidence": 0.0,
                    "last_validation": current_time,
                }
                face.identity = "Desconocido"
                face.confidence = 0.0
                face.recognition_state = "UNKNOWN"
                continue

            best_similarity = -1.0
            best_index = -1

            for i, known_embedding in enumerate(self.known_encodings):
                similarity = self.cosine_similarity(face.embedding, known_embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_index = i

            is_recognized = best_index >= 0 and best_similarity >= self.threshold

            face.identity = (
                self.known_names[best_index] if is_recognized else "Desconocido"
            )
            face.confidence = round(best_similarity * 100, 2)
            face.recognition_state = "RECOGNIZED" if is_recognized else "UNKNOWN"

            # GUARDAR EN CACHÉ (Actualizando timestamp de validación)
            self.track_cache[track_id] = {
                "identity": face.identity,
                "confidence": face.confidence,
                "last_validation": current_time,
            }

        # Purga de memoria para evitar saturación
        if len(self.track_cache) > self.cache_ttl:
            purge_count = len(self.track_cache) - int(self.cache_ttl * 0.8)
            oldest_keys = list(self.track_cache.keys())[:purge_count]
            for key in oldest_keys:
                self.track_cache.pop(key, None)

        return context
