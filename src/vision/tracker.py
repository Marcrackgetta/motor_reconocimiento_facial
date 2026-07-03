# src/vision/tracker.py
import numpy as np
from typing import List, Tuple
import supervision as sv

from src.utils.config import TRACKER_BUFFER, TRACKER_MATCH_THRESH


class FaceTracker:
    """
    Motor de seguimiento espacial basado en ByteTrack.
    Asigna y mantiene IDs únicos (temporales) por cada rostro detectado.
    """

    def __init__(self):
        # ByteTrack optimizado para CPU
        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=TRACKER_BUFFER,
            minimum_matching_threshold=TRACKER_MATCH_THRESH,
            frame_rate=30,
        )
        self.generated_ids: set[int] = set()

    def update(
        self, face_locations: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[int, int, int, int, int]]:
        """
        Recibe detecciones y asigna IDs de seguimiento.
        Retorna: Lista de (top, right, bottom, left, track_id)
        """
        if not face_locations:
            # Es vital actualizar el tracker vacío para que los buffers de frames perdidos avancen
            self.tracker.update_with_detections(sv.Detections.empty())
            return []

        # Convertir formato Legacy (top, right, bottom, left) al formato (x1, y1, x2, y2)
        xyxy = np.array(
            [[left, top, right, bottom] for top, right, bottom, left in face_locations],
            dtype=np.float32,
        )

        # Emulamos confianza máxima para que ByteTrack acepte todas las cajas
        confidence = np.ones(len(face_locations), dtype=np.float32)

        detections = sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=np.zeros(len(face_locations), dtype=int),
        )

        # Ejecutar el motor de rastreo
        tracked_detections = self.tracker.update_with_detections(detections)

        results = []
        if len(tracked_detections) > 0:
            for i in range(len(tracked_detections)):
                box = tracked_detections.xyxy[i]
                t_id = int(tracked_detections.tracker_id[i])

                # Registrar histórico de IDs para métricas
                self.generated_ids.add(t_id)

                left, top, right, bottom = map(int, box)
                results.append((top, right, bottom, left, t_id))

        return results

    def get_total_ids(self) -> int:
        """Retorna la cantidad histórica de IDs únicos generados en la sesión."""
        return len(self.generated_ids)
