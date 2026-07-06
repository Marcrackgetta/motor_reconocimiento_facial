import time
from pathlib import Path

import cv2

from src.capture.camera_stream import CameraStream
from src.storage.file_manager import FileManager
from src.utils.config import (
    CAMERA_URL,
    RECONNECT_DELAY_SECONDS,
    MODEL_PATH,
    INSIGHTFACE_REC_THRESH,
)

from src.vision.vision_engine import VisionEngine
from src.vision.tracker import FaceTracker
from src.vision.recognition_engine import RecognitionEngine

# Configuración del limitador global de FPS ajustado a 30
TARGET_FPS = 120
FRAME_TIME_LIMIT = 1.0 / TARGET_FPS


def main():
    print("=" * 60)
    print(" MOTOR DE RECONOCIMIENTO FACIAL ".center(60, "="))
    print("=" * 60)

    model = FileManager.load_model(Path(MODEL_PATH))
    known_encodings = model.get("encodings", [])
    known_names = model.get("names", [])

    if not known_encodings:
        print("[ADVERTENCIA] No existen embeddings entrenados.")

    vision_engine = VisionEngine()
    tracker = FaceTracker()
    recognition_engine = RecognitionEngine(
        known_encodings=known_encodings,
        known_names=known_names,
        threshold=INSIGHTFACE_REC_THRESH,
    )

    prev_time = time.perf_counter()
    fps_history = []  # Historial para estabilizar la lectura de FPS en pantalla

    with CameraStream(
        url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS
    ) as stream:
        while True:
            # Inicia el cronómetro del frame actual para el limitador
            loop_start = time.perf_counter()

            frame = stream.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            # 1. Detección espacial (Rápida - Sin Embeddings)
            context = vision_engine.detect(frame)

            # 2. Seguimiento / Tracking
            context = tracker.update(context)

            # 3. Reconocimiento Inteligente (Usa caché, extrae embeddings solo si es rostro nuevo)
            context = recognition_engine.process(frame, context, vision_engine)

            # Cálculo de FPS de renderizado real usando promedio móvil
            now = time.perf_counter()
            instant_fps = 1.0 / max(now - prev_time, 0.001)
            prev_time = now

            fps_history.append(instant_fps)
            if len(fps_history) > 15:
                fps_history.pop(0)

            avg_fps = sum(fps_history) / len(fps_history)

            cv2.putText(
                frame,
                f"FPS: {int(avg_fps)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            for face in context.faces:
                color = (
                    (0, 255, 0)
                    if getattr(face, "identity", "") != "Desconocido"
                    else (0, 0, 255)
                )
                confidence = getattr(face, "confidence", 0.0)
                identity = getattr(face, "identity", "Calculando...")

                cv2.rectangle(
                    frame, (face.left, face.top), (face.right, face.bottom), color, 2
                )

                label = (
                    f"{identity} ({confidence:.1f}%)"
                    if confidence > 0
                    else f"{identity}"
                )
                cv2.putText(
                    frame,
                    label,
                    (face.left, face.top - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2,
                )

            cv2.imshow("Motor de Reconocimiento", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            # ==========================================================
            # LIMITADOR GLOBAL DE FPS
            # Libera CPU impidiendo que el bucle corra más rápido de lo necesario
            # ==========================================================
            elapsed = time.perf_counter() - loop_start
            if elapsed < FRAME_TIME_LIMIT:
                time.sleep(FRAME_TIME_LIMIT - elapsed)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
