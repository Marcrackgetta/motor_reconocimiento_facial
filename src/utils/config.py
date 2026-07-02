# src/utils/config.py
from pathlib import Path

# URL del flujo de video (Debe actualizarse con la IP mostrada en la aplicación Android)
CAMERA_URL: str = "http://192.168.100.35:8080/video"

# Tiempo de espera en segundos antes de intentar una reconexión
RECONNECT_DELAY_SECONDS: int = 2

# --- CONFIGURACIÓN DEL MÓDULO DE REGISTRO ---
# Ruta raíz del almacenamiento de imágenes de entrenamiento
DATASET_DIR: Path = Path("data/dataset")

# Cantidad estandarizada de fotografías a capturar por cada individuo
MAX_PHOTOS_PER_PERSON: int = 30

# Umbral matemático para la detección de desenfoque (Varianza del operador Laplaciano)
# Valores inferiores a este límite se clasificarán como imágenes borrosas.
BLUR_THRESHOLD: float = 70.0

# Directorio físico donde se guardarán los modelos
MODELS_DIR: Path = Path("data/models")

# Ruta completa del archivo serializado que contendrá las matrices matemáticas y etiquetas
MODEL_PATH: Path = MODELS_DIR / "encodings.pkl"

# --- CONFIGURACIÓN DEL MOTOR DE VISIÓN ---
# Define qué arquitectura de inferencia se utilizará en todo el proyecto
VISION_ENGINE = "dlib"
