# src/vision/dlib_engine/detector.py
import cv2
import face_recognition
import numpy as np
from typing import List, Tuple
from src.vision.interfaces import BaseFaceDetector


class DlibFaceDetector(BaseFaceDetector):
    def __init__(self, model: str = "hog"):
        self.model = model

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        # Forzar matriz RGB contigua en memoria para C++
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_frame, model=self.model)
        return locations
