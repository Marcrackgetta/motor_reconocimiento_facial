# src/vision/interfaces.py
from abc import ABC, abstractmethod
import numpy as np
from typing import List, Tuple


class BaseFaceDetector(ABC):
    """Interfaz abstracta que todo motor de detección facial debe cumplir."""

    @abstractmethod
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Debe retornar una lista de coordenadas en formato: (top, right, bottom, left)."""
        pass


class BaseFaceRecognizer(ABC):
    """Interfaz abstracta que todo motor de reconocimiento facial debe cumplir."""

    @abstractmethod
    def recognize(
        self, frame: np.ndarray, face_locations: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[str, float]]:
        """Debe retornar una lista alineada de tuplas: [(Nombre, Confianza), ...]."""
        pass
