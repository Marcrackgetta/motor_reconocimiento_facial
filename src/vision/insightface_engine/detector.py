# src/vision/insightface_engine/detector.py
import numpy as np
from typing import List, Tuple
from insightface.app import FaceAnalysis

from src.vision.interfaces import BaseFaceDetector
from src.utils.config import (
    INSIGHTFACE_MODEL_PACK,
    INSIGHTFACE_DET_THRESH,
    INSIGHTFACE_INPUT_SIZE,
)


class InsightFaceDetector(BaseFaceDetector):
    """
    Implementación del detector facial utilizando InsightFace (SCRFD) y ONNX Runtime.
    Ejecución estrictamente en CPU. Retorna formato compatible con Dlib.
    """

    def __init__(self):
        # Se carga únicamente el módulo 'detection' para no sobrecargar RAM con otros modelos
        self.app = FaceAnalysis(
            name=INSIGHTFACE_MODEL_PACK,
            allowed_modules=["detection"],
            providers=["CPUExecutionProvider"],
        )

        # Preparación del grafo de ejecución ONNX
        self.app.prepare(
            ctx_id=0,  # 0 indica CPU en esta configuración
            det_thresh=INSIGHTFACE_DET_THRESH,
            det_size=INSIGHTFACE_INPUT_SIZE,
        )

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Analiza el fotograma y localiza rostros.
        InsightFace espera un frame en BGR (estándar de cv2).
        """
        # Ejecución del modelo SCRFD
        faces = self.app.get(frame)

        locations = []
        for face in faces:
            # InsightFace retorna bbox como float32: [left, top, right, bottom]
            bbox = face.bbox.astype(int)
            left, top, right, bottom = bbox[0], bbox[1], bbox[2], bbox[3]

            # Sanitización de límites (evitar coordenadas negativas)
            top = max(0, top)
            left = max(0, left)
            bottom = max(0, bottom)
            right = max(0, right)

            # Se añade a la lista transformando al formato Legacy de Dlib
            locations.append((top, right, bottom, left))

        return locations
