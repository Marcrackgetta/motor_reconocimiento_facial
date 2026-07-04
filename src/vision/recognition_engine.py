from __future__ import annotations
from typing import List, Dict, Any
import numpy as np

from src.vision.frame_context import FrameContext
from src.vision.vision_engine import VisionEngine


class RecognitionEngine:
    """
    Motor de reconocimiento con memoria basada en tracking.
    Evita la ejecución redundante del modelo de embeddings si el rostro ya fue validado.
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

        # Diccionario de caché: track_id -> {'identity': str, 'confidence': float}
        self.track_cache: Dict[int, Dict[str, Any]] = {}

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
            # Evaluación directa para permitir que Pylance infiera el tipo como estricto (int)
            if face.track_id is None:
                continue

            track_id: int = face.track_id

            if track_id in self.track_cache:
                cached = self.track_cache[track_id]
                face.identity = cached["identity"]
                face.confidence = cached["confidence"]
                face.recognition_state = (
                    "RECOGNIZED" if face.identity != "Desconocido" else "UNKNOWN"
                )
                continue

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

            self.track_cache[track_id] = {
                "identity": face.identity,
                "confidence": face.confidence,
            }

        if len(self.track_cache) > 1000:
            self.track_cache.clear()

        return context
