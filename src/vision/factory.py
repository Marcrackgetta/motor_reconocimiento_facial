# src/vision/factory.py
from typing import List, Any
from src.utils.config import VISION_ENGINE
from src.vision.interfaces import BaseFaceDetector, BaseFaceRecognizer


def get_face_detector() -> BaseFaceDetector:
    """Instancia y retorna el detector facial según la configuración global."""
    if VISION_ENGINE == "dlib":
        from src.vision.dlib_engine.detector import DlibFaceDetector

        # Los parámetros específicos de dlib (como 'hog') quedan ocultos aquí
        return DlibFaceDetector(model="hog")
    else:
        raise ValueError(f"Motor de visión no soportado: {VISION_ENGINE}")


def get_face_recognizer(
    known_encodings: List[Any], known_names: List[str]
) -> BaseFaceRecognizer:
    """Instancia y retorna el reconocedor facial según la configuración global."""
    if VISION_ENGINE == "dlib":
        from src.vision.dlib_engine.recognizer import DlibFaceRecognizer

        # El parámetro tolerance de dlib se inyecta aquí
        return DlibFaceRecognizer(
            known_encodings=known_encodings, known_names=known_names, tolerance=0.6
        )
    else:
        raise ValueError(f"Motor de visión no soportado: {VISION_ENGINE}")
