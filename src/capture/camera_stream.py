# src/capture/camera_stream.py
import cv2
import time
import logging
import threading
import queue
import numpy as np
from typing import Optional

# Configuración del sistema de registros (logs) para monitorear la conexión en consola
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CameraStream:
    """Clase responsable de gestionar la conexión de red y extracción de video de forma asíncrona."""

    def __init__(self, url: str, reconnect_delay: int = 2):
        self.url = url
        self.reconnect_delay = reconnect_delay
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_connected: bool = False
        self.last_reconnect_time: float = 0.0
        self.q: queue.Queue = queue.Queue(maxsize=1)
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self._connect()

    def _connect(self) -> None:
        """Establece o restablece la conexión con el servidor de video (IP Webcam)."""
        if self.cap is not None:
            self.cap.release()

        logging.info(f"Intentando conectar al flujo: {self.url}")
        self.cap = cv2.VideoCapture(self.url)

        if self.cap is not None and self.cap.isOpened():
            self.is_connected = True
            logging.info(
                "Conexión establecida correctamente."
                f"Resolución: "
                f"{int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
                f"{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
            )

            # Iniciar hilo de lectura de fotogramas si no está corriendo
            if self.thread is None or not self.thread.is_alive():
                self.running = True
                self.thread = threading.Thread(target=self._update, daemon=True)
                self.thread.start()
        else:
            self.is_connected = False
            logging.warning("No se pudo establecer la conexión inicial.")

    def _update(self) -> None:
        """Bucle secundario que lee fotogramas continuamente para no bloquear el hilo principal."""
        while self.running:
            if self.is_connected and self.cap is not None:
                success, frame = self.cap.read()
                if success:
                    # Mantener solo el fotograma más reciente en la cola para reducir latencia
                    if not self.q.empty():
                        try:
                            self.q.get_nowait()
                        except queue.Empty:
                            pass
                    self.q.put(frame)
                else:
                    logging.warning(
                        "Flujo de video interrumpido o cámara desconectada en el hilo secundario."
                    )
                    self.is_connected = False
            else:
                time.sleep(0.1)

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Retorna el fotograma capturado más reciente.
        Bloquea hasta que un nuevo fotograma esté disponible o ocurra un timeout.
        Si el flujo se interrumpe, gestiona la reconexión automáticamente.
        """
        if not self.is_connected or self.cap is None:
            current_time = time.time()
            if current_time - self.last_reconnect_time > self.reconnect_delay:
                self.last_reconnect_time = current_time
                self._connect()
            return None

        try:
            return self.q.get(timeout=0.1)
        except queue.Empty:
            return None

    def _reconnect(self) -> None:
        """Pausa la ejecución brevemente y reintenta la conexión."""
        pass

    def release(self) -> None:
        """Cierra el socket de red, detiene el hilo secundario y libera los recursos de memoria."""
        self.running = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.cap is not None:
            self.cap.release()
            self.is_connected = False
            logging.info("Recursos de captura liberados correctamente.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
