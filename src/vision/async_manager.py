# src/vision/async_manager.py
import threading
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Tuple, Any, Set

from src.vision.interfaces import BaseFaceRecognizer


class AsyncRecognitionManager:
    """
    Gestor asíncrono para el reconocimiento facial.
    Aísla la carga de ArcFace en un hilo en segundo plano y gestiona una caché
    basada estrictamente en Track IDs generados por ByteTrack.
    """

    def __init__(self, recognizer: BaseFaceRecognizer):
        self.recognizer = recognizer
        # Un único worker para no saturar la CPU con cálculos neuronales paralelos masivos
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.cache: Dict[int, Dict[str, Any]] = {}
        self.lock = threading.Lock()

        # Variables para métricas
        self.arcface_times: list[float] = []
        self.pending_tasks: int = 0
        self.cache_hits: int = 0
        self.recognized_tracks: int = 0

    def get_state_and_identity(self, track_id: int) -> Tuple[str, str, float]:
        """Consulta la caché para verificar el estado de un Track."""
        with self.lock:
            if track_id in self.cache:
                data = self.cache[track_id]
                # Contabilizamos una reutilización solo si la identidad ya está definida
                if data["state"] in ["RECOGNIZED", "UNKNOWN"]:
                    self.cache_hits += 1
                return data["state"], data["name"], data["confidence"]
            return "NEW", "", 0.0

    def submit_recognition(
        self, track_id: int, frame: np.ndarray, location: Tuple[int, int, int, int]
    ) -> None:
        """Encola una tarea de reconocimiento asegurando que ocurra una sola vez."""
        with self.lock:
            self.cache[track_id] = {
                "state": "PROCESSING",
                "name": "Procesando...",
                "confidence": 0.0,
            }
            self.pending_tasks += 1

        # Copia obligatoria del frame para evitar que el hilo principal modifique
        # la matriz (ej. dibujando rectángulos) mientras ArcFace la procesa.
        frame_copy = frame.copy()
        self.executor.submit(self._process, track_id, frame_copy, location)

    def _process(
        self, track_id: int, frame: np.ndarray, location: Tuple[int, int, int, int]
    ) -> None:
        """Tarea en segundo plano: Ejecuta ArcFace y actualiza la caché."""
        start_time = time.time()
        try:
            results = self.recognizer.recognize(frame, [location])
            name, confidence = results[0] if results else ("Desconocido", 0.0)

            with self.lock:
                # Validamos que ByteTrack no haya eliminado el Track por abandono de escena
                if track_id in self.cache:
                    state = "RECOGNIZED" if name != "Desconocido" else "UNKNOWN"
                    self.cache[track_id] = {
                        "state": state,
                        "name": name,
                        "confidence": confidence,
                    }
                    if state == "RECOGNIZED":
                        self.recognized_tracks += 1
        except Exception:
            with self.lock:
                if track_id in self.cache:
                    self.cache[track_id] = {
                        "state": "UNKNOWN",
                        "name": "Error",
                        "confidence": 0.0,
                    }
        finally:
            elapsed = (time.time() - start_time) * 1000
            with self.lock:
                self.pending_tasks -= 1
                self.arcface_times.append(elapsed)
                # Mantener una media móvil corta (últimos 50 rostros)
                if len(self.arcface_times) > 50:
                    self.arcface_times.pop(0)

    def cleanup_lost_tracks(self, active_track_ids: Set[int]) -> None:
        """Elimina de la caché los Tracks (LOST) que ByteTrack ya descartó."""
        with self.lock:
            lost_ids = [tid for tid in self.cache.keys() if tid not in active_track_ids]
            for tid in lost_ids:
                del self.cache[tid]

    def get_metrics(self) -> Tuple[int, float, int, int]:
        """Retorna las métricas funcionales para el HUD."""
        with self.lock:
            avg_time = (
                sum(self.arcface_times) / len(self.arcface_times)
                if self.arcface_times
                else 0.0
            )
            return self.pending_tasks, avg_time, self.recognized_tracks, self.cache_hits
