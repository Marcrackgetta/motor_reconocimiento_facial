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
        self.frame_id: int = 0
        self.consecutive_failures: int = 0
        self.max_failures_before_reconnect: int = 15  # Hasta 15 frames fallidos antes de declarar desconexión
        self.running: bool = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            if self.cap is None or not self.is_connected:
                # Liberar captura previa de forma segura
                if self.cap is not None:
                    try:
                        self.cap.release()
                    except Exception as e:
                        logging.error(f"[CameraStream] Error liberando cámara {self.source}: {e}")
                    self.cap = None

                logging.info(f"[CameraStream] Intentando conectar a la cámara {self.source}...")
                try:
                    self.cap = cv2.VideoCapture(self.source)
                    if self.cap and self.cap.isOpened():
                        self.is_connected = True
                        self.consecutive_failures = 0
                        logging.info(f"[CameraStream] Cámara {self.source} conectada exitosamente.")
                    else:
                        self.is_connected = False
                        if self.cap:
                            self.cap.release()
                            self.cap = None
                        time.sleep(self.reconnect_delay)
                        continue
                except Exception as e:
                    logging.error(f"[CameraStream] Excepción conectando a {self.source}: {e}")
                    self.is_connected = False
                    self.cap = None
                    time.sleep(self.reconnect_delay)
                    continue

            try:
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    with self.frame_lock:
                        self.latest_frame = frame
                        self.frame_id += 1
                    self.consecutive_failures = 0
                else:
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.max_failures_before_reconnect:
                        logging.warning(
                            f"[CameraStream] {self.max_failures_before_reconnect} fallos consecutivos en cámara {self.source}. Iniciando reconexión..."
                        )
                        self.is_connected = False
                        if self.cap:
                            try:
                                self.cap.release()
                            except Exception:
                                pass
                            self.cap = None
                        time.sleep(self.reconnect_delay)
            except Exception as e:
                logging.error(f"[CameraStream] Error leyendo frame de cámara {self.source}: {e}")
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.max_failures_before_reconnect:
                    self.is_connected = False

            time.sleep(0.01)

    def get_frame(self) -> Optional[np.ndarray]:
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def get_frame_with_id(self) -> tuple[Optional[np.ndarray], int]:
        with self.frame_lock:
            if self.latest_frame is None:
                return None, 0
            return self.latest_frame.copy(), self.frame_id

    def release(self) -> None:
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                logging.error(f"[CameraStream] Error al cerrar VideoCapture: {e}")
            self.cap = None

