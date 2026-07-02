# src/vision/recognizer.py
import cv2
import face_recognition
import numpy as np
from typing import List, Tuple, Any


class FaceRecognizer:
    def __init__(
        self, known_encodings: List[Any], known_names: List[str], tolerance: float = 0.6
    ):
        self.known_encodings = known_encodings
        self.known_names = known_names
        self.tolerance = tolerance

    def recognize(
        self, frame: np.ndarray, face_locations: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[str, float]]:
        if not self.known_encodings:
            return [("Desconocido", 0.0) for _ in face_locations]

        # Solución: Usar OpenCV para forzar una matriz RGB contigua en memoria
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        results = []

        for face_encoding in face_encodings:
            distances = face_recognition.face_distance(
                self.known_encodings, face_encoding
            )

            if len(distances) == 0:
                continue

            best_match_index = np.argmin(distances)
            min_distance = distances[best_match_index]

            if min_distance <= self.tolerance:
                name = self.known_names[best_match_index]
                confidence = round((1.0 - min_distance) * 100.0, 2)
            else:
                name = "Desconocido"
                confidence = 0.0

            results.append((name, confidence))

        return results
