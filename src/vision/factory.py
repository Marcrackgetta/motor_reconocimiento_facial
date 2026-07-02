# src/vision/factory.py
from typing import List, Any
from src.utils.config import VISION_ENGINE
from src.vision.interfaces import BaseFaceDetector, BaseFaceRecognizer


def get_face_detector() -> BaseFaceDetector:
    """Instancia y retorna el detector facial según la configuración global."""
    if VISION_ENGINE == "dlib":
        from src.vision.dlib_engine.detector import DlibFaceDetector

        return DlibFaceDetector(model="hog")
    elif VISION_ENGINE == "insightface":
        from src.vision.insightface_engine.detector import InsightFaceDetector

        return InsightFaceDetector()
    else:
        raise ValueError(f"Motor de visión no soportado: {VISION_ENGINE}")


def get_face_recognizer(
    known_encodings: List[Any], known_names: List[str]
) -> BaseFaceRecognizer:
    """Instancia y retorna el reconocedor facial según la configuración global."""
    if VISION_ENGINE == "dlib":
        from src.vision.dlib_engine.recognizer import DlibFaceRecognizer

        return DlibFaceRecognizer(
            known_encodings=known_encodings, known_names=known_names, tolerance=0.6
        )

    elif VISION_ENGINE == "insightface":
        # AHORA SÍ CONECTAMOS EL RECONOCEDOR DE ARCFACE
        from src.vision.insightface_engine.recognizer import InsightFaceRecognizer
        from src.utils.config import INSIGHTFACE_REC_THRESH

        return InsightFaceRecognizer(
            known_encodings=known_encodings,
            known_names=known_names,
            tolerance=INSIGHTFACE_REC_THRESH,
        )
    else:
        raise ValueError(f"Motor de visión no soportado: {VISION_ENGINE}")
