# main_register.py
import cv2
import time
import sys
import os

from src.utils.config import (
    CAMERA_URL,
    RECONNECT_DELAY_SECONDS,
    DATASET_DIR,
    MAX_PHOTOS_PER_PERSON,
    BLUR_THRESHOLD,
)
from src.capture.camera_stream import CameraStream
from src.vision.vision_engine import VisionEngine


def main():
    print("=" * 50)
    print("=== MÓDULO DE REGISTRO DE IDENTIDADES ===")
    print("=" * 50)

    person_name = input(
        "Ingrese el nombre de la persona a registrar (ej. Juan_Perez): "
    ).strip()
    if not person_name:
        print("[ERROR] El nombre no puede estar vacío.")
        sys.exit(1)

    print("[INFO] Inicializando Motor de Visión (InsightFace)...")
    # Optimization 5: Replaced broken legacy factory with the unified VisionEngine
    vision_engine = VisionEngine()

    # Create the required dataset directory for the new identity
    person_dir = os.path.join(DATASET_DIR, person_name)
    os.makedirs(person_dir, exist_ok=True)

    print(f"[INFO] Conectando a la cámara: {CAMERA_URL}")
    stream = CameraStream(url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS)

    # Wait for the camera buffer to initialize
    time.sleep(2.0)

    if not stream.is_connected:
        print("[ERROR] No se pudo establecer conexión con la cámara.")
        sys.exit(1)

    print(f"[INFO] Capturando {MAX_PHOTOS_PER_PERSON} fotografías.")
    print(
        "[INFO] Mire a la cámara y mueva lentamente la cabeza. Presione 'q' para cancelar."
    )

    captured_photos = 0
    cooldown_time = 0.0

    try:
        while captured_photos < MAX_PHOTOS_PER_PERSON:
            frame = stream.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            # Optimization 5: Removed useless cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # InsightFace works natively with BGR, converting it to RGB degraded detection.
            display_frame = frame.copy()

            # Accessing the FaceAnalysis instance directly to get bounding boxes
            # This standardizes the detection pipeline across the entire project
            faces = vision_engine.app.get(frame)

            if len(faces) == 1:
                face = faces[0]
                box = face.bbox.astype(int)
                x1, y1, x2, y2 = box

                # Prevent out-of-bounds array slicing
                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                face_crop = frame[y1:y2, x1:x2]

                if face_crop.size > 0:
                    # Evaluate blur using Laplacian variance
                    gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                    blur_variance = cv2.Laplacian(gray_crop, cv2.CV_64F).var()

                    color = (0, 0, 255)  # Red (Blurry or in cooldown state)

                    # Only capture if the image is sharp enough and cooldown has passed
                    if blur_variance >= BLUR_THRESHOLD and (
                        time.time() - cooldown_time > 0.4
                    ):
                        filename = os.path.join(
                            person_dir, f"{person_name}_{captured_photos:03d}.jpg"
                        )
                        cv2.imwrite(filename, face_crop)

                        captured_photos += 1
                        cooldown_time = time.time()
                        color = (0, 255, 0)  # Green (Successful capture)
                        print(
                            f"[CAPTURA] Foto {captured_photos}/{MAX_PHOTOS_PER_PERSON} guardada. (Nitidez: {blur_variance:.1f})"
                        )

                    # UI Feedback
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        display_frame,
                        f"Progreso: {captured_photos}/{MAX_PHOTOS_PER_PERSON}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        color,
                        2,
                    )
            elif len(faces) > 1:
                cv2.putText(
                    display_frame,
                    "ERROR: Multiples rostros detectados",
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow("Registro de Identidad", display_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[INFO] Operación cancelada por el usuario.")
                break

    except KeyboardInterrupt:
        print("\n[INFO] Detenido manualmente por el usuario.")
    finally:
        stream.release()
        cv2.destroyAllWindows()
        print(
            f"[INFO] Proceso finalizado. {captured_photos} fotos registradas para '{person_name}'."
        )


if __name__ == "__main__":
    main()
