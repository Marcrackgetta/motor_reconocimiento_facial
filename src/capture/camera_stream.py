# src/capture/camera_stream.py
import cv2
import time
import logging
import threading
from typing import Optional
import numpy as np

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CameraStream:
    """Class responsible for managing network connection and asynchronous video extraction."""

    def __init__(self, url: str, reconnect_delay: int = 2):
        self.url = url
        self.reconnect_delay = reconnect_delay
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_connected: bool = False
        self.last_reconnect_time: float = 0.0

        self.frame_lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None

        self.running: bool = True
        # Iniciamos el hilo directamente para que la conexión no congele la interfaz
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self) -> None:
        """Secondary loop that reads frames and handles reconnections independently."""
        while self.running:
            if self.is_connected and self.cap is not None:
                success, frame = self.cap.read()
                if success:
                    with self.frame_lock:
                        self.latest_frame = frame
                else:
                    logging.warning("Video stream interrupted in secondary thread.")
                    self.is_connected = False
                    if self.cap:
                        self.cap.release()
                        self.cap = None
            else:
                # La reconexión ahora ocurre aquí, sin bloquear el programa principal
                current_time = time.time()
                if current_time - self.last_reconnect_time > self.reconnect_delay:
                    self.last_reconnect_time = current_time
                    logging.info(f"Attempting connection to {self.url}...")

                    self.cap = cv2.VideoCapture(self.url)

                    if self.cap is not None and self.cap.isOpened():
                        self.is_connected = True
                        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        logging.info(
                            f"Connection successfully established. {width}x{height}"
                        )
                    else:
                        if self.cap:
                            self.cap.release()
                            self.cap = None

                time.sleep(0.1)

    def get_frame(self) -> Optional[np.ndarray]:
        """Returns the most recently captured frame, or None if no new frame is ready."""
        with self.frame_lock:
            if self.latest_frame is not None:
                frame = self.latest_frame.copy()
                self.latest_frame = None
                return frame
            return None

    def release(self) -> None:
        """Closes the network socket and stops the thread."""
        self.running = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.cap is not None:
            self.cap.release()
        self.is_connected = False
        logging.info("Capture resources successfully released.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
