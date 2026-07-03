# src/training/trainer.py
import os
import cv2
import time
import logging
from typing import Dict, List, Any

# Importaciones correctas de la Factory y Configuración
from src.vision.factory import get_face_detector, get_face_recognizer
from src.utils.config import INSIGHTFACE_EMBEDDING_SIZE

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Clase responsable de procesar el dataset y compilar los encodings faciales."""

    def __init__(self, *args, **kwargs):
        # 1. Instanciamos módulos vía Factory
        self.detector = get_face_detector()
        self.recognizer = get_face_recognizer(known_encodings=[], known_names=[])

        # 2. Dimensión estricta para ArcFace
        self.expected_dim = INSIGHTFACE_EMBEDDING_SIZE

        self.known_encodings: List[Any] = []
        self.known_names: List[str] = []

    def train_from_directory(self, person_directories: List[Any]) -> Dict[str, Any]:
        """Itera sobre el dataset, usa el motor activo para extraer vectores y valida dimensiones."""
        total_persons = len(person_directories)

        if total_persons == 0:
            logger.warning("No se encontraron directorios en el dataset.")
            return {"encodings": [], "names": []}

        start_time = time.time()
        total_processed = 0
        total_errors = 0

        for idx, person_dir in enumerate(person_directories, 1):
            person_dir_str = str(person_dir)
            person_name = os.path.basename(person_dir_str).replace("_", " ")
            print(f"[{idx}/{total_persons}] Procesando individuo: {person_name}")

            image_files = [
                f
                for f in os.listdir(person_dir_str)
                if f.lower().endswith((".png", ".jpg", ".jpeg"))
            ]

            if not image_files:
                print("  -> Advertencia: Directorio vacío. Se omitirá.")
                continue

            processed_count = 0
            error_count = 0

            for img_name in image_files:
                img_path = os.path.join(person_dir_str, img_name)

                try:
                    frame = cv2.imread(img_path)
                    if frame is None:
                        error_count += 1
                        continue

                    # 1. Fase de Detección (Motor Dinámico, ya NO usamos model="hog")
                    boxes = self.detector.detect_faces(frame)

                    if len(boxes) != 1:
                        error_count += 1
                        continue

                    # 2. Fase de Extracción (Motor Dinámico)
                    embeddings = self.recognizer.extract_embeddings(frame, boxes)

                    if not embeddings:
                        error_count += 1
                        continue

                    encoding = embeddings[0]

                    if len(encoding) != self.expected_dim:
                        logger.error(
                            f"Fallo estructural: Se generaron {len(encoding)} dimensiones, se esperaban {self.expected_dim}."
                        )
                        error_count += 1
                        continue

                    self.known_encodings.append(encoding)
                    self.known_names.append(person_name)
                    processed_count += 1

                except Exception as e:
                    logger.error(f"Excepción en {img_path}: {str(e)}")
                    error_count += 1

            total_processed += processed_count
            total_errors += error_count
            print(
                f"  -> Éxito: {processed_count} imágenes. Descartadas: {error_count}."
            )

        elapsed_time = time.time() - start_time

        print("\n" + "=" * 40)
        print(" RESUMEN DE ENTRENAMIENTO ".center(40, "="))
        print("=" * 40)
        print("• Motor Activo     : INSIGHTFACE")
        print(f"• Personas         : {total_persons}")
        print(f"• Img Procesadas   : {total_processed} (Éxito)")
        print(f"• Img Descartadas  : {total_errors}")
        print(f"• Dimensión Vector : {self.expected_dim}")
        print(f"• Tiempo de CPU    : {elapsed_time:.2f} segundos")
        print("=" * 40 + "\n")

        return {"encodings": self.known_encodings, "names": self.known_names}
