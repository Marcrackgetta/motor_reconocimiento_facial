# src/capture/camera_stream.py
import cv2
import time
import logging
import threading
import os
from typing import Optional, Union
import numpy as np

# Configurar un límite de espera (timeout) corto para FFMPEG (Cámaras IP)
# Evita que el intento de conexión ahogue los recursos de red
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;2000"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CameraStream:
    """Clase responsable de gestionar la conexión y extracción asíncrona de video sin bloquear la UI."""

    def __init__(self, source: Union[str, int], reconnect_delay: int = 2):
        # Limpieza de seguridad por si el número de la cámara USB se pasa como texto
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        self.source = source
        self.reconnect_delay = reconnect_delay
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_connected: bool = False
        self.last_reconnect_time: float = 0.0

        self.frame_lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None
        self.running: bool = True

        # AISLAMIENTO DE BACKENDS PARA EVITAR CONFLICTOS
        if isinstance(self.source, int):
            self.backend = cv2.CAP_DSHOW
        else:
            self.backend = cv2.CAP_FFMPEG

        # Iniciamos el hilo secundario
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self) -> None:
        """Bucle secundario que lee fotogramas y gestiona reconexiones independientemente."""
        while self.running:
            if self.is_connected and self.cap is not None:
                success, frame = self.cap.read()
                if success:
                    with self.frame_lock:
                        self.latest_frame = frame
                else:
                    logging.warning(f"Señal interrumpida en origen: {self.source}")
                    self.is_connected = False

                    # Limpiamos el frame SOLO cuando la cámara falla realmente
                    with self.frame_lock:
                        self.latest_frame = None

                    if self.cap:
                        self.cap.release()
                        self.cap = None
            else:
                current_time = time.time()
                if current_time - self.last_reconnect_time > self.reconnect_delay:
                    self.last_reconnect_time = current_time
                    logging.info(
                        f"Intentando conexión a {self.source} (Backend: {self.backend})..."
                    )

                    self.cap = cv2.VideoCapture(self.source, self.backend)

                    if self.cap is not None and self.cap.isOpened():
                        self.is_connected = True
                        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        logging.info(
                            f"Conexión exitosa establecida en {self.source}. Resolución: {width}x{height}"
                        )
                    else:
                        if self.cap:
                            self.cap.release()
                            self.cap = None

                time.sleep(
                    0.01
                )  # Pausa ligera para no sobrecargar el procesador al reconectar

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Retorna una copia del fotograma más reciente sin borrarlo del búfer.
        Esto soluciona el falso negativo asegurando que la interfaz siempre tenga
        una imagen que dibujar aunque la cámara tarde milisegundos en capturar la siguiente.
        """
        with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def release(self) -> None:
        """Cierra el socket y detiene el hilo de lectura de manera segura."""
        self.running = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.cap is not None:
            self.cap.release()
        self.is_connected = False
        logging.info(f"Recursos liberados correctamente para: {self.source}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
