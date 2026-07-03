# src/vision/face_data.py


from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import time

import numpy as np

BoundingBox = tuple[int, int, int, int]


@dataclass(slots=True)
class DetectedFace:
    """
    Representa un rostro detectado dentro de un FrameContext.

    Esta clase es completamente independiente de InsightFace.
    Todo el pipeline trabaja únicamente con esta estructura.
    """

    # ------------------------------
    # Detección
    # ------------------------------

    bbox: BoundingBox
    score: float = 0.0

    landmarks: Optional[np.ndarray] = None
    embedding: Optional[np.ndarray] = None

    # ------------------------------
    # Tracking
    # ------------------------------

    track_id: Optional[int] = None

    first_seen: float = 0.0
    last_seen: float = 0.0

    # ------------------------------
    # Reconocimiento
    # ------------------------------

    identity: str = "Desconocido"

    confidence: float = 0.0

    recognition_state: str = "NEW"
    # NEW
    # PROCESSING
    # RECOGNIZED
    # UNKNOWN

    # ------------------------------
    # Futuro (Attendance)
    # ------------------------------

    person_id: Optional[int] = None

    present: bool = False

    # ------------------------------
    # Futuro (Atributos)
    # ------------------------------

    age: Optional[int] = None
    gender: Optional[str] = None

    # ------------------------------------------------

    def __post_init__(self):

        now = time.time()

        if self.first_seen == 0:
            self.first_seen = now

        if self.last_seen == 0:
            self.last_seen = now

    # ------------------------------------------------

    @property
    def top(self) -> int:
        return self.bbox[0]

    @property
    def right(self) -> int:
        return self.bbox[1]

    @property
    def bottom(self) -> int:
        return self.bbox[2]

    @property
    def left(self) -> int:
        return self.bbox[3]

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[int, int]:
        return (
            self.left + self.width // 2,
            self.top + self.height // 2,
        )
