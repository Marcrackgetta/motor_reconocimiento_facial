from __future__ import annotations
from typing import List, Dict, Any
import numpy as np

from src.vision.frame_context import FrameContext
from src.vision.vision_engine import VisionEngine


class RecognitionEngine:
    """
    Motor de reconocimiento impulsado por caché.
    Evita extracciones redundantes si el rastreador mantiene el rostro.
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

        for face in context.faces:
            # Extraer de forma segura el valor
            raw_track_id = getattr(face, "track_id", None)

            # Comprobar si existe un id de seguimiento
            if raw_track_id is None:
                continue

            # Convertir (castear) explícitamente a entero para satisfacer a Pylance
            track_id: int = int(raw_track_id)

            # VALIDACIÓN CACHÉ: Si ya lo conocemos, copiamos los datos e ignoramos a la IA pesada
            if track_id in self.track_cache:
                cached = self.track_cache[track_id]
                face.identity = cached["identity"]
                face.confidence = cached["confidence"]
                face.recognition_state = (
                    "RECOGNIZED" if face.identity != "Desconocido" else "UNKNOWN"
                )
                continue

            # SOLO SI ES NUEVO: Se solicita extraer el embedding al motor de visión
            vision_engine.extract_embedding(frame, face)

            if face.embedding is None:
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

            # GUARDAR EN CACHÉ PARA PRÓXIMOS FRAMES
            self.track_cache[track_id] = {
                "identity": face.identity,
                "confidence": face.confidence,
            }

        # Optimization 3: Memory protection purge to prevent Stuttering and Thermal Throttling.
        # Instead of deleting all items (which forces total re-extraction on the next frame),
        # we remove only the oldest items, keeping the cache healthy for currently tracked faces.
        if len(self.track_cache) > self.cache_ttl:
            # We preserve 80% of the cache capacity (the most recent entries)
            purge_count = len(self.track_cache) - int(self.cache_ttl * 0.8)
            # Python dictionaries maintain insertion order, so the first elements are the oldest
            oldest_keys = list(self.track_cache.keys())[:purge_count]
            for key in oldest_keys:
                self.track_cache.pop(key, None)

        return context
