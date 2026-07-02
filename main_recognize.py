# main_recognize.py
import cv2
import time
from src.utils.config import CAMERA_URL, RECONNECT_DELAY_SECONDS, MODEL_PATH
from src.capture.camera_stream import CameraStream
from src.vision.detector import FaceDetector
from src.vision.recognizer import FaceRecognizer
from src.storage.file_manager import FileManager


def main():
    print("=== MOTOR DE RECONOCIMIENTO FACIAL EN TIEMPO REAL ===")

    # 1. Cargar el modelo en memoria antes de inicializar la cámara
    model_data = FileManager.load_model(MODEL_PATH)
    known_encodings = model_data.get("encodings", [])
    known_names = model_data.get("names", [])

    if not known_encodings:
        print("[Advertencia] No se encontraron encodings en el modelo.")
        print("El sistema operará, pero clasificará todo como 'Desconocido'.")

    # 2. Inicialización de los subsistemas modulares
    detector = FaceDetector(model="hog")
    recognizer = FaceRecognizer(
        known_encodings=known_encodings, known_names=known_names, tolerance=0.6
    )

    prev_time = 0.0
    frame_count = 0
    face_locations = []
    identities = []

    try:
        with CameraStream(
            url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS
        ) as stream:
            while True:
                frame = stream.get_frame()
                if frame is None:
                    continue

                # 3. Cálculo de Rendimiento Funcional (FPS)
                current_time = time.time()
                time_diff = current_time - prev_time
                fps = 1.0 / time_diff if time_diff > 0 else 0.0
                prev_time = current_time

                fps_color = (0, 255, 0) if fps >= 15 else (0, 0, 255)
                cv2.putText(
                    frame,
                    f"FPS: {int(fps)}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    fps_color,
                    2,
                )

                # Optimización: Procesar detección y reconocimiento 1 de cada 2 frames
                if frame_count % 2 == 0:
                    # Optimización: Reducir resolución para inferencia
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

                    # Optimización: Convertir BGR a RGB una sola vez
                    rgb_small_frame = small_frame[:, :, ::-1]

                    # 4. Fase de Detección (Coordenadas)
                    small_face_locations = detector.detect_faces(rgb_small_frame)

                    # Escalar coordenadas de nuevo al tamaño original para la extracción de features precisa
                    face_locations = [
                        (top * 4, right * 4, bottom * 4, left * 4)
                        for top, right, bottom, left in small_face_locations
                    ]

                    # 5. Fase de Reconocimiento (Identidad y Confianza)
                    # Debe hacerse sobre el fotograma original (tamaño completo) para no perder precisión
                    rgb_frame = frame[:, :, ::-1]
                    identities = recognizer.recognize(rgb_frame, face_locations)

                frame_count += 1

                # 6. Renderizado de la Interfaz de Usuario
                # Se iteran simultáneamente las coordenadas y las identidades usando zip()
                for (top, right, bottom, left), (name, confidence) in zip(
                    face_locations, identities
                ):
                    # Diseño de color funcional estricto:
                    # Verde = Identidad confirmada (Acceso válido)
                    # Rojo = Desconocido (Alerta/Bloqueo)
                    if name != "Desconocido":
                        ui_color = (0, 255, 0)
                        display_text = f"{name} ({confidence}%)"
                    else:
                        ui_color = (0, 0, 255)
                        display_text = "Desconocido"

                    # Trazado de la caja delimitadora del rostro
                    cv2.rectangle(frame, (left, top), (right, bottom), ui_color, 2)

                    # Panel base para asegurar la legibilidad del texto
                    cv2.rectangle(
                        frame,
                        (left, bottom - 30),
                        (right, bottom),
                        ui_color,
                        cv2.FILLED,
                    )

                    # Superposición de la etiqueta (Nombre y Porcentaje)
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
