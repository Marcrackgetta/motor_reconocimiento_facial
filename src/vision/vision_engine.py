from __future__ import annotations
from typing import List, Any
import numpy as np
from insightface.app import FaceAnalysis

from src.utils.config import (
    INSIGHTFACE_MODEL_PACK,
    INSIGHTFACE_DET_THRESH,
    INSIGHTFACE_INPUT_SIZE,
)
from src.vision.face_data import DetectedFace
from src.vision.frame_context import FrameContext


class _FaceProxy:
    """
    Clase proxy estructurada para satisfacer la verificación de tipos estáticos (Pylance)
    y el formato requerido por el modelo ArcFace interno de InsightFace.
    """

    def __init__(self, bbox: np.ndarray, kps: Any) -> None:
        self.bbox: np.ndarray = bbox
        self.kps: Any = kps
        self.embedding: Any = None
        self.normed_embedding: Any = None


class VisionEngine:
    """
    Motor de visión optimizado.
    Se separa la detección (SCRFD) de la extracción de características (ArcFace).
    """

    def __init__(self) -> None:
        self.app = FaceAnalysis(
            name=INSIGHTFACE_MODEL_PACK,
            allowed_modules=["detection", "recognition"],
            providers=["CPUExecutionProvider"],
        )

        self.app.prepare(
            ctx_id=0,
            det_thresh=INSIGHTFACE_DET_THRESH,
            det_size=INSIGHTFACE_INPUT_SIZE,
        )

        self.det_model = self.app.models.get("detection")
        self.rec_model = self.app.models.get("recognition")

    def detect(self, frame: np.ndarray) -> FrameContext:
        """
        Ejecuta únicamente la detección espacial y estimación de puntos de referencia.
        No calcula embeddings.
        """
        context = FrameContext(frame=frame)
        detected_faces: List[DetectedFace] = []

        if self.det_model is None:
            return context

        bboxes, kpss = self.det_model.detect(frame, max_num=0, metric="default")

        if bboxes is not None:
            for i in range(bboxes.shape[0]):
                bbox = bboxes[i, 0:4]
                score = bboxes[i, 4]
                kps = kpss[i] if kpss is not None else None

                left, top, right, bottom = (
                    max(0, int(bbox[0])),
                    max(0, int(bbox[1])),
                    max(0, int(bbox[2])),
                    max(0, int(bbox[3])),
                )

                face = DetectedFace(
                    bbox=(top, right, bottom, left),
                    embedding=None,
                    landmarks=kps,
                    score=float(score),
                )

                detected_faces.append(face)

        context.faces = detected_faces
        return context

    def extract_embedding(self, frame: np.ndarray, face: DetectedFace) -> None:
        """
        Calcula el embedding para un rostro específico bajo demanda.
        """
        if self.rec_model is None or face.landmarks is None:
            return

        # Reconstruir el bounding box en el formato NumPy esperado por InsightFace [x1, y1, x2, y2]
        top, right, bottom, left = face.bbox
        raw_bbox = np.array([left, top, right, bottom], dtype=np.float32)

        proxy = _FaceProxy(bbox=raw_bbox, kps=face.landmarks)

        self.rec_model.get(frame, proxy)

        face.embedding = getattr(
            proxy, "embedding", getattr(proxy, "normed_embedding", None)
        )
