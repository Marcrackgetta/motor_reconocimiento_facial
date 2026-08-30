import logging
import time
from datetime import datetime
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EventManager:
    """
    Gestiona la cola de eventos locales de asistencia antes de enviarlos a Firebase.
    """
    def __init__(self):
        self.event_queue: list[dict[str, Any]] = []
        self.registered_in_block: set[str] = set()
        self.current_block: str = ""

    def _get_current_block(self) -> str:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        if 0 <= now.hour < 12:
            shift = "MATUTINO"
        elif 12 <= now.hour < 18:
            shift = "VESPERTINO"
        else:
            shift = "NOCTURNO"
            
        return f"{date_str}_{shift}"

    def register_recognition(self, identity_uuid: str, camera_id: str) -> None:
        if identity_uuid == "Calculando...":
            return

        active_block = self._get_current_block()
        
        if active_block != self.current_block:
            self.current_block = active_block
            self.registered_in_block.clear()
            logging.info(f"--- [NUEVO BLOQUE HORARIO: {self.current_block}] Registros reiniciados ---")

        event_key = f"{camera_id}_{identity_uuid}_{self.current_block}"
        
        # Para desconocidos, generamos una clave temporal para que se reporten cada 10 segundos
        if identity_uuid in ("unknown", "Desconocido"):
            event_key = f"{camera_id}_unknown_{int(time.time() // 10)}"

        if event_key not in self.registered_in_block:
            event = {
                "identity_uuid": identity_uuid,
                "camera_id": camera_id,
                "timestamp": time.time(),
                "block": self.current_block,
                "status": "pending"
            }
            self.event_queue.append(event)
            self.registered_in_block.add(event_key)
            
            logging.info(f"[EVENTO EN COLA] Detección: {identity_uuid} en {camera_id}")

    def get_pending_events(self) -> list[dict[str, Any]]:
        return self.event_queue
        
    def clear_events(self, count: int) -> None:
        self.event_queue = self.event_queue[count:]