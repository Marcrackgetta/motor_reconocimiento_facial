# src/capture/camera_stream.py
import os
# Suprimir errores molestos de OpenCV cuando una cámara no está conectada
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

import cv2
import time
import logging
import threading
from typing import Optional, Union
import numpy as np

# Configurar un límite de espera (timeout) corto para FFMPEG (Cámaras IP)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;2000"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Ya no se necesita Flask ni variables de streaming web.
command_queue = [] # Cola de comandos mantenida por compatibilidad

class CameraStream:
    """Clase responsable de gestionar la conexión y extracción asíncrona de video."""

    def __init__(self, source: Union[str, int], reconnect_delay: int = 2):
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        self.source = source
        self.reconnect_delay = reconnect_delay
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_connected: bool = False
        self.frame_lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None
        self.running: bool = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        global latest_frame_to_stream
        while self.running:
            if self.cap is None or not self.is_connected:
                self.cap = cv2.VideoCapture(self.source)
                self.is_connected = self.cap.isOpened()
                time.sleep(self.reconnect_delay)
                continue

            ret, frame = self.cap.read()
            if ret:
                with self.frame_lock:
                    self.latest_frame = frame
            else:
                self.is_connected = False
            time.sleep(0.01)

    def get_frame(self) -> Optional[np.ndarray]:
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def release(self) -> None:
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
