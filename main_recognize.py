import time
import threading
from pathlib import Path

import cv2
import numpy as np

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
from src.vision.frame_context import FrameContext


class AIVideoProcessor(threading.Thread):
    """
    Procesador en hilo paralelo para aislar la carga computacional de la IA.
    Garantiza que el bucle de renderizado de UI no sufra bloqueos.
    """

    def __init__(self, vision, tracker, recognition):
        super().__init__(daemon=True)
        self.vision = vision
        self.tracker = tracker
        self.recognition = recognition

        self.frame_to_process = None
        # Se provee un contexto vacío por defecto para prevenir errores en el dibujado inicial
        self.latest_context = FrameContext(frame=np.zeros((10, 10, 3), dtype=np.uint8))
        self.latest_context.faces = []

        self.lock = threading.Lock()
        self.running = True

        self.t_vision = 0.0
        self.t_track = 0.0
        self.t_recog = 0.0

    def push_frame(self, frame: np.ndarray) -> None:
        """Suministra el fotograma más reciente. Sobrescribe los anteriores para evitar retrasos."""
        with self.lock:
            self.frame_to_process = frame.copy()

    def get_latest_context(self) -> FrameContext:
        """Devuelve los resultados procesados más recientes de forma segura."""
        with self.lock:
            return self.latest_context

    def run(self) -> None:
        """Bucle de ejecución del sistema de reconocimiento."""
        while self.running:
            frame = None
            with self.lock:
                if self.frame_to_process is not None:
                    frame = self.frame_to_process
                    self.frame_to_process = None

            if frame is None:
                time.sleep(0.01)
                continue

            # =========================
            # VISION (Solo Detección)
            # =========================
            t0 = time.perf_counter()
            context = self.vision.detect(frame)
            vision_ms = (time.perf_counter() - t0) * 1000

            # =========================
            # TRACKER
            # =========================
            t0 = time.perf_counter()
            context = self.tracker.update(context)
            track_ms = (time.perf_counter() - t0) * 1000

            # =========================
            # RECOGNITION (Por Caché/Demanda)
            # =========================
            t0 = time.perf_counter()
            context = self.recognition.process(frame, context, self.vision)
            recog_ms = (time.perf_counter() - t0) * 1000

            with self.lock:
                self.latest_context = context
                self.t_vision = vision_ms
                self.t_track = track_ms
                self.t_recog = recog_ms

    def stop(self) -> None:
        self.running = False


def main():
    print("=" * 60)
    print(" MOTOR BASE DE RECONOCIMIENTO FACIAL ".center(60, "="))
    print("=" * 60)

    model = FileManager.load_model(Path(MODEL_PATH))
    known_encodings = model.get("encodings", [])
    known_names = model.get("names", [])

    if not known_encodings:
        print("[ADVERTENCIA] No existen embeddings entrenados.")

    # =========================
    # INICIALIZACIÓN DE MOTORES
    # =========================
    vision_engine = VisionEngine()
    tracker = FaceTracker()
    recognition_engine = RecognitionEngine(
        known_encodings=known_encodings,
        known_names=known_names,
        threshold=INSIGHTFACE_REC_THRESH,
    )

    # Iniciar el procesador de IA asíncrono
    ai_processor = AIVideoProcessor(vision_engine, tracker, recognition_engine)
    ai_processor.start()

    # =========================
    # BUCLE DE RENDERIZADO
    # =========================
    prev_time = time.perf_counter()

    try:
        with CameraStream(
            url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS
        ) as stream:
            while True:
                frame = stream.get_frame()
                if frame is None:
                    continue

                # Enviar el frame al motor de IA para su análisis asíncrono
                ai_processor.push_frame(frame)

                # Extraer los datos más recientes generados por la IA
                context = ai_processor.get_latest_context()

                # Control estricto de los fotogramas por segundo del render (UI)
                now = time.perf_counter()
                fps = 1.0 / (max(now - prev_time, 0.001))
                prev_time = now

                # =========================
                # INTERFAZ GRÁFICA (UI)
                # =========================
                cv2.putText(
                    frame,
                    f"UI FPS: {int(fps)}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Vision: {ai_processor.t_vision:.1f} ms",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Tracker: {ai_processor.t_track:.1f} ms",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Recog: {ai_processor.t_recog:.1f} ms",
                    (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

                for face in context.faces:
                    # El color cumple una función informativa estricta basada en el estado
                    color = (
                        (0, 255, 0)
                        if getattr(face, "identity", "") != "Desconocido"
                        else (0, 0, 255)
                    )
                    confidence = getattr(face, "confidence", 0.0)
                    identity = getattr(face, "identity", "Calculando...")

                    cv2.rectangle(
                        frame,
                        (face.left, face.top),
                        (face.right, face.bottom),
                        color,
                        2,
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

                cv2.imshow("Motor Facial Asíncrono", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        ai_processor.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
