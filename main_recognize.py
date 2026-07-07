import time
from pathlib import Path

import cv2

from src.capture.camera_stream import CameraStream
from src.storage.file_manager import FileManager
from src.utils.config import (
    CAMERA_SOURCES,
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

    # Extraemos la cámara a usar y su curso asignado
    camara_activa = CAMERA_SOURCES[0]
    curso_camara = camara_activa.get("curso_asignado", "")

    with CameraStream(
        source=camara_activa, reconnect_delay=RECONNECT_DELAY_SECONDS
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
                confidence = getattr(face, "confidence", 0.0)
                identity = getattr(face, "identity", "Calculando...")

                # --- Lógica de filtrado por curso ---
                estado = ""

                if identity == "Desconocido":
                    color = (0, 0, 255)  # Rojo: Totalmente desconocido
                elif identity == "Calculando...":
                    color = (255, 255, 0)  # Cian/Celeste: Procesando
                else:
                    # Es un rostro conocido. Verificamos si pertenece a este curso.
                    if curso_camara in identity:
                        color = (0, 255, 0)  # Verde: Correcto
                        estado = " [PRESENTE]"

                        # TODO: A FUTURO - Aquí irá la petición a la Base de Datos.
                        # Ejemplo: bd.marcar_asistencia(identity, curso_camara, hora)

                    else:
                        color = (0, 165, 255)  # Naranja: Cadete de otro curso
                        estado = " [CURSO INCORRECTO]"

                # Dibujar la caja contenedora
                cv2.rectangle(
                    frame, (face.left, face.top), (face.right, face.bottom), color, 2
                )

                # Construir la etiqueta final
                label = (
                    f"{identity}{estado} ({confidence:.1f}%)"
                    if confidence > 0
                    else f"{identity}{estado}"
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
