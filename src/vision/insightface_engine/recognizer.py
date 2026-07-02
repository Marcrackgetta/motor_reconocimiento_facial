# src/vision/insightface_engine/recognizer.py
import logging
import numpy as np
from typing import List, Tuple, Any
from insightface.app import FaceAnalysis

from src.vision.interfaces import BaseFaceRecognizer
from src.utils.config import (
    INSIGHTFACE_MODEL_PACK,
    INSIGHTFACE_EMBEDDING_SIZE,
    INSIGHTFACE_INPUT_SIZE,
)

logger = logging.getLogger(__name__)


class InsightFaceRecognizer(BaseFaceRecognizer):
    """
    Implementación del reconocedor facial utilizando ArcFace (InsightFace).
    Calcula similitud mediante Cosine Similarity y devuelve formato Dlib compatible.
    """

    def __init__(
        self,
        known_encodings: List[Any],
        known_names: List[str],
        tolerance: float = 0.45,
    ):
        self.known_encodings = known_encodings
        self.known_names = known_names
        self.tolerance = tolerance  # Funciona como umbral de similitud del coseno

        # --- PREPARACIÓN ARQUITECTÓNICA (Futuras optimizaciones) ---
        # TODO: Implementar Redis/Memcached para caché de embeddings.
        # TODO: Implementar ThreadPoolExecutor para reconocimiento asíncrono.

        # Inicializamos detección y reconocimiento para garantizar la alineación por landmarks.
        self.app = FaceAnalysis(
            name=INSIGHTFACE_MODEL_PACK,
            allowed_modules=["detection", "recognition"],
            providers=["CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=0, det_thresh=0.5, det_size=INSIGHTFACE_INPUT_SIZE)

        # --- CAPA DE VALIDACIÓN TEMPORAL (Protección de Compatibilidad) ---
        self.is_valid_database = True
        if self.known_encodings:
            embedding_dim = len(self.known_encodings[0])
            if embedding_dim != INSIGHTFACE_EMBEDDING_SIZE:
                self.is_valid_database = False
                logger.error(
                    f"INCOMPATIBILIDAD CRÍTICA: El modelo cargado tiene {embedding_dim} "
                    f"dimensiones (probablemente Dlib). ArcFace requiere {INSIGHTFACE_EMBEDDING_SIZE}."
                )
                logger.warning(
                    "El reconocedor operará en modo seguro ('Desconocido'). Debe re-entrenar el dataset."
                )

    def _compute_cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calcula la similitud del coseno entre dos vectores."""
        dot_product = np.dot(emb1, emb2)
        norm_product = np.linalg.norm(emb1) * np.linalg.norm(emb2)
        if norm_product == 0:
            return 0.0
        return float(dot_product / norm_product)

    def recognize(
        self, frame: np.ndarray, face_locations: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[str, float]]:
        # Por defecto, llenamos con "Desconocido"
        results = [("Desconocido", 0.0) for _ in face_locations]

        if not self.is_valid_database or not self.known_encodings or not face_locations:
            return results

        # Extraer todas las caras del frame con sus landmarks y embeddings ArcFace
        faces = self.app.get(frame)
        if not faces:
            return results

        # Asignación Espacial: Emparejar los bboxes de la interfaz con los rostros detectados por InsightFace
        for i, (top, right, bottom, left) in enumerate(face_locations):
            # Centro del bounding box solicitado
            cx = (left + right) / 2
            cy = (top + bottom) / 2

            best_face = None
            min_dist = float("inf")

            # Encontrar el rostro de InsightFace más cercano a estas coordenadas
            for face in faces:
                fx1, fy1, fx2, fy2 = face.bbox
                fcx = (fx1 + fx2) / 2
                fcy = (fy1 + fy2) / 2

                # Distancia euclidiana entre centros
                dist = (cx - fcx) ** 2 + (cy - fcy) ** 2
                if dist < min_dist:
                    min_dist = dist
                    best_face = face

            if best_face is not None:
                current_embedding = best_face.embedding

                max_sim = -1.0
                best_match_idx = -1

                # Comparar contra la base de datos (O(n) convertible a O(1) con librerías FAISS en el futuro)
                for j, known_emb in enumerate(self.known_encodings):
                    sim = self._compute_cosine_similarity(current_embedding, known_emb)
                    if sim > max_sim:
                        max_sim = sim
                        best_match_idx = j

                # Si supera el umbral, es un Match positivo
                if max_sim >= self.tolerance:
                    name = self.known_names[best_match_idx]
                    # Convertir similitud (0 a 1) a porcentaje funcional
                    confidence = round(max_sim * 100.0, 2)
                    results[i] = (name, confidence)

        return results
