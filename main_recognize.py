# main_recognize.py
import cv2
import time
from src.utils.config import CAMERA_URL, RECONNECT_DELAY_SECONDS, MODEL_PATH
from src.capture.camera_stream import CameraStream
from src.storage.file_manager import FileManager
from src.vision.factory import get_face_detector, get_face_recognizer
from src.vision.tracker import FaceTracker
from src.vision.async_manager import AsyncRecognitionManager
from pathlib import Path

# -- PARÁMETROS DE OPTIMIZACIÓN --
TARGET_FPS = 30
FRAME_TIME = 1.0 / TARGET_FPS
PROCESS_FREQUENCY = 10  # Procesar detección/reconocimiento 1 de cada 10 frames


def main():
    print("=== MOTOR DE RECONOCIMIENTO FACIAL EN TIEMPO REAL ===")

    model_data = FileManager.load_model(Path(MODEL_PATH))
    known_encodings = model_data.get("encodings", [])
    known_names = model_data.get("names", [])

    if not known_encodings:
        print("[Advertencia] No se encontraron encodings en el modelo.")

    detector = get_face_detector()
    recognizer = get_face_recognizer(
        known_encodings=known_encodings, known_names=known_names
    )

    async_manager = AsyncRecognitionManager(recognizer)

    tracker = FaceTracker()
    prev_time = time.time()

    try:
        with CameraStream(
            url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS
        ) as stream:
            while True:
                frame = stream.get_frame()
                if frame is None:
                    continue

                # 1. Fase de Detección (SCRFD)
                t0 = time.perf_counter()
                face_locations = detector.detect_faces(frame)
                det_ms = (time.perf_counter() - t0) * 1000

                # 2. Fase de Tracking (ByteTrack)
                t0 = time.perf_counter()
                tracked_faces = tracker.update(face_locations)
                track_ms = (time.perf_counter() - t0) * 1000

                # 3. Fase de Reconocimiento ASÍNCRONO
                identities = []
                active_tracks = set()

                for top, right, bottom, left, track_id in tracked_faces:
                    active_tracks.add(track_id)

                    # Consultamos el estado actual (O(1) desde Caché RAM)
                    state, name, confidence = async_manager.get_state_and_identity(
                        track_id
                    )

                    if state == "NEW":
                        # Si es nuevo, lo enviamos al ThreadPoolExecutor
                        async_manager.submit_recognition(
                            track_id, frame, (top, right, bottom, left)
                        )
                        name, confidence = "Procesando...", 0.0

                    identities.append((name, confidence))

                # Limpieza automática de memoria (Prevenir fugas en LOST tracks)
                async_manager.cleanup_lost_tracks(active_tracks)

                # 4. Cálculo de FPS Globales
                current_time = time.time()
                time_diff = current_time - prev_time
                fps = 1.0 / time_diff if time_diff > 0 else 0.0
                prev_time = current_time

                # 5. Renderizado de Interfaz y HUD
                pending, avg_time, rec_tracks, cache_hits = async_manager.get_metrics()

                # Despliegue de métricas en pantalla
                cv2.putText(
                    frame,
                    f"FPS: {int(fps)}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"ArcFace Avg: {avg_time:.1f} ms",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Pendientes: {pending}",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Reconocidos: {rec_tracks}",
                    (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Cache Hits: {cache_hits}",
                    (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    f"SCRFD: {det_ms:.1f} ms",
                    (10, 180),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Tracker: {track_ms:.1f} ms",
                    (10, 210),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )

                for (top, right, bottom, left, track_id), (name, confidence) in zip(
                    tracked_faces, identities
                ):
                    if name not in ["Desconocido", "Procesando...", "Error"]:
                        ui_color = (0, 255, 0)
                    elif name == "Procesando...":
                        ui_color = (0, 255, 255)  # Amarillo: Tarea asíncrona pendiente
                    else:
                        ui_color = (0, 0, 255)

                    display_text = f"ID:{track_id} | {name} ({confidence}%)"

                    cv2.rectangle(frame, (left, top), (right, bottom), ui_color, 2)
                    cv2.rectangle(
                        frame,
                        (left, bottom - 30),
                        (right, bottom),
                        ui_color,
                        cv2.FILLED,
                    )
                    cv2.putText(
                        frame,
                        display_text,
                        (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )

                cv2.imshow("Motor de Visión - Fase Operativa", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
