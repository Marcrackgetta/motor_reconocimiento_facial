from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np


class BaseFaceDetector(ABC):
    @abstractmethod
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        pass


class BaseFaceRecognizer(ABC):
    @abstractmethod
    def recognize(
        self,
        frame: np.ndarray,
        face_locations: List[Tuple[int, int, int, int]],
    ) -> List[Tuple[str, float]]:
        pass

    @abstractmethod
    def extract_embeddings(
        self,
        frame: np.ndarray,
        face_locations: List[Tuple[int, int, int, int]],
    ) -> List[list]:
        pass
