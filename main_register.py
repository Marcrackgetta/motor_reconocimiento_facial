# main_register.py
import cv2
import time
from src.utils.config import (
    CAMERA_URL,
    RECONNECT_DELAY_SECONDS,
    DATASET_DIR,
    MAX_PHOTOS_PER_PERSON,
    BLUR_THRESHOLD,
)
from src.capture.camera_stream import CameraStream
from src.storage.file_manager import FileManager
from src.vision.factory import get_face_detector

TARGET_FPS = 30
FRAME_TIME = 1.0 / TARGET_FPS


def main():
    print("=== MÓDULO DE REGISTRO DE PERSONAS ===")
    person_name = input(
        "Ingrese el nombre completo de la persona a registrar: "
    ).strip()

    if not person_name:
        print("[Error] El nombre no puede estar vacío. Proceso abortado.")
        return

    target_dir = FileManager.create_person_directory(DATASET_DIR, person_name)
    detector = get_face_detector()

    photo_count = 0
    # Variable de control de tiempo no bloqueante
    last_capture_time = 0.0
    CAPTURE_DELAY = 0.2  # 200ms entre capturas

    print(
        f"\n[Info] Iniciando captura. Se requieren {MAX_PHOTOS_PER_PERSON} fotografías."
    )

    try:
        with CameraStream(
            url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS
        ) as stream:
            while photo_count < MAX_PHOTOS_PER_PERSON:
                loop_start = time.time()

                frame = stream.get_frame()
                if frame is None:
                    continue

                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                # Optimización O(N) de copia
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                small_face_locations = detector.detect_faces(rgb_small_frame)

                face_locations = [
                    (top * 4, right * 4, bottom * 4, left * 4)
                    for top, right, bottom, left in small_face_locations
                ]

                face_count = len(face_locations)
                status_color = (0, 255, 255)
                status_text = "Esperando rostro..."

                if face_count == 0:
                    status_text = "ERROR: Ningun rostro detectado"
                    status_color = (0, 0, 255)
                elif face_count > 1:
                    status_text = "ERROR: Multiples rostros detectados"
                    status_color = (0, 0, 255)
                else:
                    is_blurry = FileManager.is_blurry(frame, BLUR_THRESHOLD)

                    if is_blurry:
                        status_text = "CALIDAD BAJA: Imagen borrosa o en movimiento"
                        status_color = (0, 255, 255)
                    else:
                        current_time = time.time()
                        # Control de retardo NO bloqueante
                        if (current_time - last_capture_time) >= CAPTURE_DELAY:
                            photo_count += 1
                            FileManager.save_frame(target_dir, frame, photo_count)
                            last_capture_time = current_time

                            status_text = f"CAPTURANDO: Foto {photo_count}/{MAX_PHOTOS_PER_PERSON}"
                            status_color = (0, 255, 0)
                        else:
                            status_text = "Procesando captura..."
                            status_color = (0, 255, 0)

                    for top, right, bottom, left in face_locations:
                        cv2.rectangle(
                            frame, (left, top), (right, bottom), (255, 0, 0), 2
                        )

                cv2.putText(
                    frame,
                    status_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    status_color,
                    2,
                )
                cv2.putText(
                    frame,
                    "Presione 'q' para CANCELAR",
                    (10, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )

                cv2.imshow("Registro Base de Datos Facial", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("\n[Advertencia] Registro cancelado manualmente.")
                    break

                # Limitador de Tasa de Refresco para estabilidad térmica
                loop_duration = time.time() - loop_start
                if loop_duration < FRAME_TIME:
                    time.sleep(FRAME_TIME - loop_duration)

            if photo_count == MAX_PHOTOS_PER_PERSON:
                print(
                    f"\n[Éxito] Se almacenaron {photo_count} imágenes útiles en '{target_dir}'."
                )

    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
