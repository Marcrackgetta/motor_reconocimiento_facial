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
from src.vision.detector import FaceDetector
from src.storage.file_manager import FileManager


def main():
    print("=== MÓDULO DE REGISTRO DE PERSONAS ===")
    person_name = input(
        "Ingrese el nombre completo de la persona a registrar: "
    ).strip()

    if not person_name:
        print("[Error] El nombre no puede estar vacío. Proceso abortado.")
        return

    # 1. Preparación del almacenamiento físico
    target_dir = FileManager.create_person_directory(DATASET_DIR, person_name)

    # 2. Inicialización de los componentes de captura y visión
    detector = FaceDetector(model="hog")

    photo_count = 0
    print(
        f"\n[Info] Iniciando captura. Se requieren {MAX_PHOTOS_PER_PERSON} fotografías."
    )
    print(
        "[Info] Colóquese frente a la cámara y realice variaciones leves de ángulo e iluminación."
    )
    print("[Info] Presione 'q' en la ventana de video si desea CANCELAR el registro.\n")

    try:
        with CameraStream(url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS) as stream:
            while photo_count < MAX_PHOTOS_PER_PERSON:
                frame = stream.get_frame()
                if frame is None:
                    continue

                # 3. Validación de Rostros
                # Optimización: Reducir resolución para inferencia rápida
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = small_frame[:, :, ::-1]
                
                small_face_locations = detector.detect_faces(rgb_small_frame)
                
                # Escalar coordenadas de nuevo al tamaño original
                face_locations = [
                    (top * 4, right * 4, bottom * 4, left * 4) 
                    for top, right, bottom, left in small_face_locations
                ]
                
                face_count = len(face_locations)

                # --- CONTROL DE ESTADOS MEDIANTE COLORIMETRÍA FUNCIONAL ---
                # Por defecto, estado de espera o error (Amarillo: Precaución / Ajuste requerido)
                status_color = (0, 255, 255)
                status_text = "Esperando rostro..."

                if face_count == 0:
                    status_text = "ERROR: Ningun rostro detectado"
                    status_color = (0, 0, 255)  # Rojo: Alerta de ausencia
                elif face_count > 1:
                    status_text = "ERROR: Multiples rostros detectados"
                    status_color = (0, 0, 255)  # Rojo: Alerta de interferencia
                else:
                    # Existe exactamente un rostro en escena. Se procede a evaluar su nitidez.
                    # Se usa frame directamente ya que aún no se le ha dibujado nada encima.
                    is_blurry = FileManager.is_blurry(frame, BLUR_THRESHOLD)

                    if is_blurry:
                        status_text = "CALIDAD BAJA: Imagen borrosa o en movimiento"
                        status_color = (
                            0,
                            255,
                            255,
                        )  # Amarillo: No cumple el estándar pero el rostro es válido
                    else:
                        # La imagen es útil (Un solo rostro y con nitidez óptima)
                        photo_count += 1
                        # Guardamos el fotograma original ANTES de dibujar las cajas delimitadoras
                        FileManager.save_frame(target_dir, frame, photo_count)

                        status_text = (
                            f"CAPTURANDO: Foto {photo_count}/{MAX_PHOTOS_PER_PERSON}"
                        )
                        status_color = (0, 255, 0)  # Verde: Éxito en persistencia

                        # Pequeña pausa de control para evitar ráfagas idénticas y fomentar la variedad de ángulos
                        time.sleep(0.2)

                    # Dibujar la caja delimitadora del rostro detectado para feedback visual
                    # Se hace DESPUÉS de guardar para no ensuciar la imagen
                    for top, right, bottom, left in face_locations:
                        cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)

                # 4. Renderizado de la Interfaz de Usuario Funcional
                # Barra superior de estado
                cv2.putText(
                    frame,
                    status_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    status_color,
                    2,
                )

                # Barra inferior con instrucciones de cancelación
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

                # 5. Control de Cancelación por el Usuario
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print(
                        "\n[Advertencia] El registro ha sido cancelado por el usuario de forma manual."
                    )
                    break

            if photo_count == MAX_PHOTOS_PER_PERSON:
                print(f"\n[Éxito] Registro completado exitosamente para: {person_name}")
                print(
                    f"[Éxito] Se almacenaron {photo_count} imágenes útiles en '{target_dir}'."
                )

    except KeyboardInterrupt:
        print("\n[Advertencia] Proceso interrumpido desde la consola.")
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
