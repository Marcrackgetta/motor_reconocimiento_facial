# src/utils/config.py

CAMERA_SOURCES = [
    {
        "nombre": "Cámara LP",
        "src": 0,
        "curso_asignado": "3_Info_B",
        "lat": -2.128589,
        "lon": -79.931099,
    },
    {
        "nombre": "Webcam USB1",
        "src": 1,
        "curso_asignado": "3_CN_A_Mat",
        "lat": -2.129581,
        "lon": -79.931084,
    },
    {
        "nombre": "Webcam USB2",
        "src": 3,
        "curso_asignado": "3_CT_A_Mat",
        "lat": -2.128720,
        "lon": -79.931061,
    },
]
RECONNECT_DELAY_SECONDS = 2
DATASET_DIR = "data/dataset"
MAX_PHOTOS_PER_PERSON = 30
BLUR_THRESHOLD = 70.0

# --- CONFIGURACIÓN DEL MODELO VECTORIAL ---
# Ruta única y definitiva del modelo
MODEL_PATH: str = "data/models/encodings.pkl"

# --- CONFIGURACIÓN INSIGHTFACE (SCRFD + ARCFACE) ---
INSIGHTFACE_MODEL_PACK = "buffalo_l"
INSIGHTFACE_DET_THRESH = 0.5
# Optimization 2: Reduced spatial detection tensor size to maximize CPU performance.
# Changed from (640, 640) to (320, 320) to significantly decrease arithmetic load on Intel CPUs.
INSIGHTFACE_INPUT_SIZE = (320, 320)
INSIGHTFACE_EMBEDDING_SIZE = 512
INSIGHTFACE_REC_THRESH = 0.45

# --- CONFIGURACIÓN DEL TRACKER (BYTETRACK) ---
TRACKER_BUFFER = 30
TRACKER_MATCH_THRESH = 0.8
