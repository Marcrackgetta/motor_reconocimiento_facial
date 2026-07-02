# main_recognize.py
import cv2
import time
from src.utils.config import CAMERA_URL, RECONNECT_DELAY_SECONDS, MODEL_PATH
from src.capture.camera_stream import CameraStream
from src.storage.file_manager import FileManager
from src.vision.factory import get_face_detector, get_face_recognizer

# -- PARÁMETROS DE OPTIMIZACIÓN --
TARGET_FPS = 30
FRAME_TIME = 1.0 / TARGET_FPS
PROCESS_FREQUENCY = 10  # Procesar detección/reconocimiento 1 de cada 10 frames


def main():
    print("=== MOTOR DE RECONOCIMIENTO FACIAL EN TIEMPO REAL ===")

    model_data = FileManager.load_model(MODEL_PATH)
    known_encodings = model_data.get("encodings", [])
    known_names = model_data.get("names", [])

    if not known_encodings:
        print("[Advertencia] No se encontraron encodings en el modelo.")

    detector = get_face_detector()
    recognizer = get_face_recognizer(
        known_encodings=known_encodings, known_names=known_names
    )
    frame_count = 0
    # Variables de Caché de Estado
    cached_face_locations = []
    cached_identities = []

    # Variables para cálculo visual de FPS (independiente del limitador)
    fps_start_time = time.time()
    visual_fps = 0

    try:
        with CameraStream(
            url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS
        ) as stream:
            while True:
                loop_start = time.time()  # Marca de inicio para el limitador

                frame = stream.get_frame()
                if frame is None:
                    continue

                # 1. Lógica de Frecuencia Espaciada (Caché de Estados)
                # Solo ejecutamos el bloque pesado en múltiplos de PROCESS_FREQUENCY
                if frame_count % PROCESS_FREQUENCY == 0:
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                    # Optimización: cv2.cvtColor es más rápido y eficiente en memoria que [:, :, ::-1]
                    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                    small_face_locations = detector.detect_faces(rgb_small_frame)

                    cached_face_locations = [
                        (top * 4, right * 4, bottom * 4, left * 4)
                        for top, right, bottom, left in small_face_locations
                    ]

                    # Si hay rostros, procedemos al reconocimiento
                    if cached_face_locations:
                        # Se mantiene el fotograma original según requerimiento, pero optimizando la copia RGB
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        cached_identities = recognizer.recognize(
                            rgb_frame, cached_face_locations
                        )
                    else:
                        cached_identities = []

                frame_count += 1

                # 2. Renderizado de Interfaz (O(1) a O(N rostros) - Extremadamente rápido)
                for (top, right, bottom, left), (name, confidence) in zip(
                    cached_face_locations, cached_identities
                ):
                    # Se mantiene la semántica de colorimetría funcional estricta
                    if name != "Desconocido":
                        ui_color = (0, 255, 0)
                        display_text = f"{name} ({confidence}%)"
                    else:
                        ui_color = (0, 0, 255)
                        display_text = "Desconocido"

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

                # Cálculo de FPS visual (promediado para lectura estable)
                if frame_count % TARGET_FPS == 0:
                    current_time = time.time()
                    visual_fps = TARGET_FPS / (current_time - fps_start_time)
                    fps_start_time = current_time

                fps_color = (
                    (0, 255, 0) if visual_fps >= (TARGET_FPS * 0.8) else (0, 0, 255)
                )
                cv2.putText(
                    frame,
                    f"FPS: {int(visual_fps)}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    fps_color,
                    2,
                )

                cv2.imshow("Motor de Vision - Fase Operativa", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

                # 3. Limitador Estricto de Tasa de Refresco (Elimina los picos de 400 FPS)
                loop_duration = time.time() - loop_start
                if loop_duration < FRAME_TIME:
                    time.sleep(FRAME_TIME - loop_duration)

    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
