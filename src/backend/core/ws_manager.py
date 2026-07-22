import json
import logging
from typing import List, Dict, Set, Optional
from fastapi import WebSocket

class ConnectedUser:
    def __init__(self, websocket: WebSocket, email: str = "", role: str = "guest"):
        self.websocket = websocket
        self.email = email
        self.role = role
        self.assigned_student_ids: Set[str] = set()

class ConnectionManager:
    """
    Gestor centralizado de conexiones WebSockets con autenticación, 
    autorización selectiva por estudiante y reconexión limpia.
    """
    def __init__(self):
        self.active_connections: Dict[WebSocket, ConnectedUser] = {}

    async def connect(self, websocket: WebSocket, email: str = "", role: str = "guest", student_ids: Optional[List[str]] = None):
        await websocket.accept()
        user = ConnectedUser(websocket, email=email, role=role)
        if student_ids:
            user.assigned_student_ids = set(student_ids)
        self.active_connections[websocket] = user
        logging.info(f"WebSocket conectado: {email} (Rol: {role}, Estudiantes: {len(user.assigned_student_ids)})")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            user = self.active_connections.pop(websocket)
            logging.info(f"WebSocket desconectado: {user.email}")

    def update_user_students(self, websocket: WebSocket, student_ids: List[str]):
        if websocket in self.active_connections:
            self.active_connections[websocket].assigned_student_ids = set(student_ids)

    @staticmethod
    def map_event_type(internal_type: str) -> str:
        """Mapea tipos de eventos internos a la taxonomía estándar de WebSockets"""
        mapping = {
            "ENTRADA": "STUDENT_ENTRY",
            "SALIDA": "STUDENT_EXIT",
            "PRESENCIA": "STUDENT_PRESENT",
            "PRESENCIA_NORMAL": "STUDENT_PRESENT",
            "INTRUSO": "INTRUDER_DETECTED",
            "INTRUSO_EXTERNO": "INTRUDER_DETECTED",
            "UNKNOWN_INTRUDER": "INTRUDER_DETECTED",
            "CURSO_DIFERENTE": "DIFFERENT_COURSE",
            "PERMANENCIA_EXCESIVA_10_MIN": "ALERT_CREATED",
            "ALERTA_UBICACION": "ALERT_CREATED",
            "INCIDENTE_RESUELTO": "ALERT_RESOLVED"
        }
        return mapping.get(internal_type, internal_type)

    async def emit_event(self, event_type: str, payload: dict):
        """
        Emite un evento selectivamente. Los representantes solo reciben eventos
        asociados a sus estudiantes asignados o alertas de intrusos de seguridad.
        """
        standard_type = self.map_event_type(event_type)
        msg_dict = {
            "type": standard_type,
            "original_type": event_type,
            "data": payload
        }
        message = json.dumps(msg_dict)
        
        target_student_id = payload.get("student_id") or payload.get("estudiante_id")

        for websocket, user in list(self.active_connections.items()):
            try:
                # 1. Administradores, rectores e inspectores reciben todos los eventos
                if user.role in ["admin", "rector", "inspector"] or not user.email:
                    await websocket.send_text(message)
                    continue

                # 2. Representantes reciben solo si el estudiante está asignado o es intruso externo
                is_assigned = target_student_id in user.assigned_student_ids if target_student_id else False
                is_security_intruder = standard_type == "INTRUDER_DETECTED"

                if is_assigned or is_security_intruder or not user.email:
                    await websocket.send_text(message)

            except RuntimeError:
                self.disconnect(websocket)
            except Exception as e:
                logging.error(f"Error enviando WebSocket a {user.email}: {e}")
                self.disconnect(websocket)

# Instancia global del WS Manager
ws_manager = ConnectionManager()
