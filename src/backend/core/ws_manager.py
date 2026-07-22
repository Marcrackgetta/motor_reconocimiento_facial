import json
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        # Creamos una copia de la lista para evitar errores si se modifica durante la iteración
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except RuntimeError as e:
                # Si hay error (ej. "Cannot call 'send' once a close message has been sent")
                # removemos la conexión.
                self.disconnect(connection)
            except Exception as e:
                # Logear o ignorar otros errores
                self.disconnect(connection)
                
    async def emit_event(self, event_type: str, payload: dict):
        """Helper to emit typed events"""
        msg_dict = {"type": event_type}
        msg_dict.update(payload)
        message = json.dumps(msg_dict)
        await self.broadcast(message)

# Instancia global del WS Manager
ws_manager = ConnectionManager()
