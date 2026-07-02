# src/vision/detector.py
import cv2
import face_recognition
import numpy as np
from typing import List, Tuple


class FaceDetector:
    def __init__(self, model: str = "hog"):
        self.model = model

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        # Solución: Usar OpenCV para forzar una matriz RGB contigua en memoria
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        locations = face_recognition.face_locations(rgb_frame, model=self.model)
        return locations
