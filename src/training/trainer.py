import time
import logging
from pathlib import Path
from typing import Dict, List, Any
import numpy as np  # <-- NUEVO: Importación necesaria para promediar

import cv2

from src.vision.vision_engine import VisionEngine
from src.utils.config import INSIGHTFACE_EMBEDDING_SIZE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Entrenador de modelo adaptado al motor de visión asíncrono/diferido.
    """

    def __init__(self, detection_model: str = "hog"):
        self.engine = VisionEngine()
        self.expected_dim = INSIGHTFACE_EMBEDDING_SIZE
        self.known_encodings: List[Any] = []
        self.known_names: List[str] = []

    def train_from_directory(self, person_directories: List[Any]) -> Dict[str, Any]:

        if not person_directories:
            logger.warning("No se encontraron directorios de entrenamiento.")
            return {"encodings": [], "names": []}

        start_time = time.time()
        total_ok = 0
        total_fail = 0

        for idx, person_dir in enumerate(person_directories, 1):
            person_dir = Path(person_dir)
            person_name = person_dir.name.replace("_", " ")

            print(f"[{idx}/{len(person_directories)}] Procesando: {person_name}")

            images = [
                f
                for f in person_dir.iterdir()
                if f.suffix.lower() in [".png", ".jpg", ".jpeg"]
            ]

            if not images:
                print("  -> Carpeta vacía, se omite.")
                continue

            ok = 0
            fail = 0
            person_embeddings = []  # <-- NUEVO: Lista temporal para las fotos de esta persona

            for img_path in images:
                try:
                    frame = cv2.imread(str(img_path))

                    if frame is None:
                        fail += 1
                        continue

                    # 1. Ejecutar Detección
                    context = self.engine.detect(frame)

                    if not context.faces:
                        fail += 1
                        continue

                    face = context.faces[0]

                    # 2. Ejecutar Extracción
                    self.engine.extract_embedding(frame, face)

                    if face.embedding is None:
                        fail += 1
                        continue

                    encoding = face.embedding

                    if len(encoding) != self.expected_dim:
                        logger.warning(
                            f"Dimensión inválida: {len(encoding)} != {self.expected_dim}"
                        )
                        fail += 1
                        continue

                    # Guardar el encoding en la lista temporal en vez de la lista final
                    person_embeddings.append(encoding)
                    ok += 1

                except Exception as e:
                    logger.error(f"Error en {img_path}: {e}")
                    fail += 1

            # --- NUEVA LÓGICA: CONSOLIDAR AL USUARIO EN UN SOLO PERFIL ---
            if person_embeddings:
                # Calcula el vector promedio de todas las fotos válidas (las 30 capturas)
                avg_embedding = np.mean(person_embeddings, axis=0)

                # Guarda un único registro para el modelo
                self.known_encodings.append(avg_embedding)
                self.known_names.append(person_name)

            total_ok += ok
            total_fail += fail

            print(f"  -> OK: {ok} | FAIL: {fail}")

        elapsed = time.time() - start_time

        print("\n" + "=" * 50)
        print(" RESUMEN ENTRENAMIENTO ".center(50, "="))
        print("=" * 50)
        print(f"Personas: {len(person_directories)}")
        print(f"Imágenes analizadas OK: {total_ok}")
        print(f"Imágenes FAIL: {total_fail}")
        print(
            f"Usuarios únicos registrados en modelo: {len(self.known_names)}"
        )  # Indicador extra
        print(f"Tiempo: {elapsed:.2f}s")
        print("=" * 50)

        return {
            "encodings": self.known_encodings,
            "names": self.known_names,
        }
