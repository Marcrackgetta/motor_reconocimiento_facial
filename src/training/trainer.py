# src/training/trainer.py
import face_recognition
import logging
from typing import Dict, List, Any
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ModelTrainer:
    """Clase responsable de procesar el dataset y compilar los encodings faciales."""

    def __init__(self, detection_model: str = "hog"):
        self.detection_model = detection_model
        self.known_encodings: List[Any] = []
        self.known_names: List[str] = []

    def train_from_directory(self, person_directories: List[Path]) -> Dict[str, Any]:
        """
        Itera sobre los directorios, extrae los encodings y compila el modelo.
        Retorna un diccionario con los datos listos para serializar.
        """
        total_persons = len(person_directories)

        if total_persons == 0:
            logging.warning(
                "No se encontraron directorios en el dataset. El entrenamiento no puede proceder."
            )
            return {"encodings": [], "names": []}

        for idx, person_dir in enumerate(person_directories, 1):
            person_name = person_dir.name.replace("_", " ")
            print(f"[{idx}/{total_persons}] Procesando individuo: {person_name}")

            image_files = [
                f
                for f in person_dir.iterdir()
                if f.suffix.lower() in (".png", ".jpg", ".jpeg")
            ]

            if not image_files:
                print(f"  -> Advertencia: Directorio vacío para {person_name}. Se omitirá.")
                continue

            processed_count = 0
            error_count = 0

            for img_path in image_files:
                try:
                    rgb_image = face_recognition.load_image_file(str(img_path))

                    boxes = face_recognition.face_locations(
                        rgb_image, model=self.detection_model
                    )

                    if len(boxes) != 1:
                        error_count += 1
                        continue

                    encoding = face_recognition.face_encodings(rgb_image, boxes)[0]

                    self.known_encodings.append(encoding)
                    self.known_names.append(person_name)
                    processed_count += 1

                except Exception as e:
                    logging.error(f"Error procesando la imagen {img_path}: {str(e)}")
                    error_count += 1

            print(
                f"  -> {processed_count} imágenes procesadas con éxito. {error_count} descartadas por errores o múltiples rostros."
            )

        print("\n[Info] Compilación de embeddings finalizada.")

        return {"encodings": self.known_encodings, "names": self.known_names}
