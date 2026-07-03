# src/vision/factory.py
from typing import List, Any
from src.vision.interfaces import BaseFaceDetector, BaseFaceRecognizer
from src.vision.insightface_engine.detector import InsightFaceDetector
from src.vision.insightface_engine.recognizer import InsightFaceRecognizer
from src.utils.config import INSIGHTFACE_REC_THRESH


def get_face_detector() -> BaseFaceDetector:
    """Instancia y retorna el detector facial."""
    return InsightFaceDetector()


def get_face_recognizer(
    known_encodings: List[Any], known_names: List[str]
) -> BaseFaceRecognizer:
    """Instancia y retorna el reconocedor facial."""
    return InsightFaceRecognizer(
        known_encodings=known_encodings,
        known_names=known_names,
        tolerance=INSIGHTFACE_REC_THRESH,
    )
