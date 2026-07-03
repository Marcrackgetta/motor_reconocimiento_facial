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
from src.vision.recognition_engine import RecognitionEngine
from src.vision.tracker import FaceTracker


def main():

    print("=" * 60)
    print(" MOTOR BASE DE RECONOCIMIENTO FACIAL ".center(60, "="))
    print("=" * 60)

    # =========================
    # MODELO
    # =========================
    model = FileManager.load_model(Path(MODEL_PATH))

    known_encodings = model.get("encodings", [])
    known_names = model.get("names", [])

    if not known_encodings:
        print("[ADVERTENCIA] No existen embeddings entrenados.")

    # =========================
    # MOTORES
    # =========================
    vision_engine = VisionEngine()
    tracker = FaceTracker()

    recognition_engine = RecognitionEngine(
        known_encodings=known_encodings,
        known_names=known_names,
        threshold=INSIGHTFACE_REC_THRESH,
    )

    # =========================
    # FPS CONTROL
    # =========================
    prev_time = time.perf_counter()
    frame_count = 0

    total_v = total_t = total_r = 0.0

    PROCESS_EVERY = 2  # 🔥 Sprint 2.5: reducción carga CPU

    try:
        with CameraStream(
            url=CAMERA_URL,
            reconnect_delay=RECONNECT_DELAY_SECONDS,
        ) as stream:
            while True:
                frame = stream.get_frame()
                if frame is None:
                    continue

                # =========================
                # VISION (OPTIMIZADO)
                # =========================
                t0 = time.perf_counter()

                skip = frame_count % PROCESS_EVERY != 0
                context = vision_engine.process(frame, skip_inference=skip)

                vision_ms = (time.perf_counter() - t0) * 1000

                # =========================
                # TRACKER
                # =========================
                t0 = time.perf_counter()
                context = tracker.update(context)
                track_ms = (time.perf_counter() - t0) * 1000

                # =========================
                # RECOGNITION
                # =========================
                t0 = time.perf_counter()
                context = recognition_engine.process(context)
                recog_ms = (time.perf_counter() - t0) * 1000

                # =========================
                # FPS
                # =========================
                now = time.perf_counter()
                fps = 1.0 / (now - prev_time)
                prev_time = now

                frame_count += 1

                total_v += vision_ms
                total_t += track_ms
                total_r += recog_ms

                avg_v = total_v / frame_count
                avg_t = total_t / frame_count
                avg_r = total_r / frame_count

                # =========================
                # HUD
                # =========================
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
                    f"Vision: {avg_v:.1f} ms",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    f"Tracker: {avg_t:.1f} ms",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    f"Recognition: {avg_r:.1f} ms",
                    (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

                # =========================
                # DRAW
                # =========================
                for face in context.faces:
                    color = (
                        (0, 255, 0) if face.identity != "Desconocido" else (0, 0, 255)
                    )

                    cv2.rectangle(
                        frame,
                        (face.left, face.top),
                        (face.right, face.bottom),
                        color,
                        2,
                    )

                    label = f"{face.identity} ({face.confidence:.1f}%)"

                    cv2.putText(
                        frame,
                        label,
                        (face.left, face.top - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        color,
                        2,
                    )

                cv2.imshow("Motor Facial Optimizado - Sprint 2.5", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        pass

    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
