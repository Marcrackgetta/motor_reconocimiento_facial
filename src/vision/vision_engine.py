from __future__ import annotations

from typing import List
import numpy as np
from insightface.app import FaceAnalysis

from src.utils.config import (
    INSIGHTFACE_MODEL_PACK,
    INSIGHTFACE_DET_THRESH,
    INSIGHTFACE_INPUT_SIZE,
)

from src.vision.face_data import DetectedFace
from src.vision.frame_context import FrameContext


class VisionEngine:
    """
    ÚNICO punto de inferencia InsightFace.

    Optimización Sprint 2.5:
    - Soporta skip_inference (reduce FPS cost)
    - Evita ejecución innecesaria de SCRFD
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

    def process(self, frame: np.ndarray, skip_inference: bool = False) -> FrameContext:
        context = FrameContext(frame=frame)

        # 🔥 Modo ligero: NO inferencia
        if skip_inference:
            return context

        insight_faces = self.app.get(frame)

        detected_faces: List[DetectedFace] = []

        for face in insight_faces:
            bbox = face.bbox.astype(int)

            left, top, right, bottom = (
                max(0, int(bbox[0])),
                max(0, int(bbox[1])),
                max(0, int(bbox[2])),
                max(0, int(bbox[3])),
            )

            detected_faces.append(
                DetectedFace(
                    bbox=(top, right, bottom, left),
                    embedding=getattr(face, "embedding", None),
                    landmarks=getattr(face, "kps", None),
                    score=float(getattr(face, "det_score", 0.0)),
                )
            )

        context.faces = detected_faces
        return context
