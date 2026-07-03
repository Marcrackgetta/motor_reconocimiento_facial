# src/vision/interfaces.py
from abc import ABC, abstractmethod
import numpy as np
from typing import List, Tuple


class BaseFaceDetector(ABC):
    @abstractmethod
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        pass


class BaseFaceRecognizer(ABC):
    @abstractmethod
    def recognize(
        self, frame: np.ndarray, face_locations: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[str, float]]:
        pass

    @abstractmethod
    def extract_embeddings(
        self, frame: np.ndarray, face_locations: List[Tuple[int, int, int, int]]
    ) -> List[list]:
        """
        Extrae las características matemáticas crudas (embeddings) de los rostros en las ubicaciones dadas.
        Utilizado estrictamente para el proceso de entrenamiento.
        """
        pass
