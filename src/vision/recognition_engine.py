from __future__ import annotations

from typing import List

import numpy as np

from src.vision.frame_context import FrameContext


class RecognitionEngine:
    """
    Motor encargado únicamente de comparar embeddings ya calculados.

    No ejecuta InsightFace.
    No detecta rostros.
    No genera embeddings.

    Solo compara vectores.
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

    @staticmethod
    def cosine_similarity(
        emb1: np.ndarray,
        emb2: np.ndarray,
    ) -> float:

        denom = np.linalg.norm(emb1) * np.linalg.norm(emb2)

        if denom == 0:
            return 0.0

        return float(np.dot(emb1, emb2) / denom)

    def process(
        self,
        context: FrameContext,
    ) -> FrameContext:

        if not self.known_encodings:
            return context

        for face in context.faces:
            if face.embedding is None:
                continue

            best_similarity = -1.0
            best_index = -1

            for i, known_embedding in enumerate(self.known_encodings):
                similarity = self.cosine_similarity(
                    face.embedding,
                    known_embedding,
                )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_index = i

            if best_index >= 0 and best_similarity >= self.threshold:
                face.identity = self.known_names[best_index]
                face.confidence = round(best_similarity * 100, 2)
                face.recognition_state = "RECOGNIZED"

            else:
                face.identity = "Desconocido"
                face.confidence = round(best_similarity * 100, 2)
                face.recognition_state = "UNKNOWN"

        return context
