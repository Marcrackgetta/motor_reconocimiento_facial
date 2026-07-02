# main_train.py
import time
from src.utils.config import DATASET_DIR, MODEL_PATH
from src.storage.file_manager import FileManager
from src.training.trainer import ModelTrainer


def main():
    print("=== MÓDULO DE ENTRENAMIENTO Y EXTRACCIÓN DE CARACTERÍSTICAS ===")

    # 1. Obtener la lista de directorios a procesar
    directories = FileManager.get_dataset_directories(DATASET_DIR)

    if not directories:
        print("[Error] El directorio del dataset está vacío o no existe.")
        print(
            f"Por favor, ejecute el módulo de registro primero y verifique la ruta: {DATASET_DIR}"
        )
        return

    print(f"[Info] Se han detectado {len(directories)} personas en el dataset.")
    print("[Info] Iniciando proceso de extracción neuronal (HOG + ResNet)...")

    start_time = time.time()

    # 2. Inicializar el módulo de entrenamiento
    trainer = ModelTrainer(detection_model="hog")

    # 3. Procesar imágenes y compilar datos
    model_data = trainer.train_from_directory(directories)

    # 4. Verificación de seguridad antes de guardar
    total_encodings = len(model_data["encodings"])
    if total_encodings == 0:
        print(
            "[Error Crítico] No se pudo generar ningún embedding válido. Entrenamiento abortado."
        )
        return

    print(
        f"[Info] Se generaron {total_encodings} vectores de características en total."
    )

    # 5. Guardar el modelo físico en disco
    print("[Info] Serializando modelo en disco...")
    success = FileManager.save_model(model_data, MODEL_PATH)

    end_time = time.time()
    elapsed_time = end_time - start_time

    if success:
        print(
            f"\n[Éxito] Entrenamiento completado y modelo guardado en {elapsed_time:.2f} segundos."
        )
        print(f"[Éxito] Ruta del modelo: {MODEL_PATH}")
    else:
        print("\n[Error] Ocurrió un fallo al intentar guardar el archivo del modelo.")


if __name__ == "__main__":
    main()
