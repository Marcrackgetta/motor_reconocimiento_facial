# src/capture/camera_stream.py
import cv2
import time
import logging
import threading
from typing import Optional
import numpy as np

# Configuración del sistema de registros (logs) para monitorear la conexión en consola
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

        # Optimization 1: Replaced Queue with a Lock and a reference to the latest frame.
        # This completely eliminates LIFO latency accumulation and thread race conditions.
        self.frame_lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None

        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self._connect()

    def _connect(self) -> None:
        """Establishes or re-establishes the connection with the video server (IP Webcam)."""
        if self.cap is not None:
            self.cap.release()

        logging.info(f"Attempting to connect to stream: {self.url}")
        self.cap = cv2.VideoCapture(self.url)

        if self.cap is not None and self.cap.isOpened():
            self.is_connected = True
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logging.info(
                f"Connection successfully established. Resolution: {width}x{height}"
            )

            # Start frame reading thread if not running
            if self.thread is None or not self.thread.is_alive():
                self.running = True
                self.thread = threading.Thread(target=self._update, daemon=True)
                self.thread.start()
        else:
            self.is_connected = False
            logging.warning("Could not establish initial connection.")

    def _update(self) -> None:
        """Secondary loop that reads frames continuously to prevent blocking the main thread."""
        while self.running:
            if self.is_connected and self.cap is not None:
                success, frame = self.cap.read()
                if success:
                    # Optimization 1: Always keep ONLY the absolute latest frame.
                    # Overwrites the previous one instantly without queue full/empty exceptions.
                    with self.frame_lock:
                        self.latest_frame = frame
                else:
                    logging.warning(
                        "Video stream interrupted or camera disconnected in secondary thread."
                    )
                    self.is_connected = False
            else:
                time.sleep(0.1)

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Returns the most recently captured frame.
        If the stream is interrupted, handles automatic reconnection.
        """
        if not self.is_connected or self.cap is None:
            current_time = time.time()
            if current_time - self.last_reconnect_time > self.reconnect_delay:
                self.last_reconnect_time = current_time
                self._connect()
            return None

        # Optimization 1: Safely extract the latest frame and clear the buffer.
        # This guarantees that the main thread always processes the current real-time frame.
        with self.frame_lock:
            if self.latest_frame is not None:
                frame = self.latest_frame.copy()
                self.latest_frame = None
                return frame
            return None

    def _reconnect(self) -> None:
        """Pauses execution briefly and retries connection."""
        pass

    def release(self) -> None:
        """Closes the network socket, stops the secondary thread, and frees memory resources."""
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
