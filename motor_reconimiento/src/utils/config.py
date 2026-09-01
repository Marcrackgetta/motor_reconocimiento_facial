# src/utils/config.py
from pathlib import Path

# --- RUTAS Y DIRECTORIOS BASE ---
# BASE_DIR apunta a la raíz del proyecto (2 niveles arriba de config.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Carpetas de almacenamiento local (Edge)
DATASET_DIR = str(BASE_DIR / "data" / "dataset")
MODEL_PATH = str(BASE_DIR / "data" / "models" / "encodings.pkl")

# --- CONFIGURACIÓN DE CÁMARAS ---
# El motor Edge solo necesita saber el ID de la cámara y su fuente.
# Las reglas de a qué curso pertenece se evalúan en el Backend en la nube.
CAMERA_SOURCES = [
    {
        "camera_id": "CAM_001",
        "nombre": "Camara 1",
        "curso": "2_INFO_B", # NUEVO: Vinculación directa al curso
        "src": 0, 
        "ubicacion": {"latitude": -2.128589, "longitude": -79.931099}
    },
    {
        "camera_id": "CAM_002",
        "nombre": "Camara 2",
        "curso": "2_INFO_A",
        "src": 1, 
        "ubicacion": {"latitude": -2.128720, "longitude": -79.931061}
    },
    {
        "camera_id": "CAM_003",
        "nombre": "Camara 3",
        "curso": "1_INFO_C",
        "src": 2, 
        "ubicacion": {"latitude": -2.129581, "longitude": -79.931084}
    }
]

RECONNECT_DELAY_SECONDS = 2
MAX_PHOTOS_PER_PERSON = 30
BLUR_THRESHOLD = 70.0

# --- CONFIGURACIÓN INSIGHTFACE (SCRFD + ARCFACE) ---
INSIGHTFACE_MODEL_PACK = "buffalo_l"
INSIGHTFACE_DET_THRESH = 0.5
INSIGHTFACE_INPUT_SIZE = (320, 320)
INSIGHTFACE_EMBEDDING_SIZE = 512
INSIGHTFACE_REC_THRESH = 0.45

# --- CONFIGURACIÓN DEL TRACKER (BYTETRACK) ---
TRACKER_BUFFER = 30
TRACKER_MATCH_THRESH = 0.8