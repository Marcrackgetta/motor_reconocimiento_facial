from __future__ import annotations
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field

from src.backend.models.domain import Event, Alert, Student

class RecognitionResult(BaseModel):
    """Payload de resultado bruto enviado por el Motor de Reconocimiento IA"""
    session_id: str
    track_id: int
    identity_raw: str
    confidence: float
    camera_id: str
    detected_course_id: str
    camera_type: str = Field(default="AULA", description="AULA, ENTRADA, SALIDA")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ActiveIncident(BaseModel):
    """Rastreador de estado de un incidente activo (ej. estudiante fuera de su aula)"""
    incident_id: str
    student_id: str
    student_name: str
    origin_course_id: str
    detected_course_id: str
    start_time: float
    last_seen_time: float
    duration_seconds: float = 0.0
    status: str = "ACTIVO"  # ACTIVO, RESUELTO
    alert_sent: bool = False
    initial_event_id: Optional[str] = None

class EventProcessor:
    """
    Procesador centralizado de eventos y reglas de negocio.
    Responde a la pregunta: "¿Qué significa que esta persona haya sido detectada aquí y ahora?"
    Es la ÚNICA FUENTE DE VERDAD para la generación de eventos, incidentes y alertas.
    """

    def __init__(self, time_limit_seconds: float = 600.0):
        self.active_incidents: Dict[str, ActiveIncident] = {}
        self.time_limit_seconds = time_limit_seconds

    @staticmethod
    def parse_identity(identity_raw: str) -> Tuple[str, str]:
        """
        Parsea la identidad recibida sin contaminar el nombre con el curso.
        Retorna (nombre_limpio, curso_origen_limpio)
        """
        if not identity_raw or identity_raw in ["Desconocido", "Calculando..."]:
            return "Desconocido", "Desconocido"

        partes = identity_raw.split("_")
        if len(partes) >= 2:
            nombre_limpio = " ".join(partes[-2:])
            curso_origen = "_".join(partes[:-2]) if len(partes) > 2 else "Desconocido"
            return nombre_limpio, curso_origen

        return identity_raw, "Desconocido"

    def process_recognition(
        self, rec: RecognitionResult, current_time: Optional[float] = None
    ) -> Tuple[Optional[Event], Optional[Alert]]:
        """
        Procesa el resultado de reconocimiento y aplica las reglas de negocio.
        Retorna una tupla (Event, Alert) con los objetos creados (o None si no se generó).
        """
        now = current_time if current_time is not None else time.time()
        nombre_limpio, curso_origen_limpio = self.parse_identity(rec.identity_raw)
        
        created_event: Optional[Event] = None
        created_alert: Optional[Alert] = None

        # 1. MANEJO DE PERSONAS DESCONOCIDAS / INTRUSOS EXTERNOS
        if nombre_limpio == "Desconocido":
            # Si se detecta un sujeto no registrado en un aula o zona de control
            created_event = Event(
                id=f"evt_intruso_{int(now)}_{rec.track_id}",
                student_id=None,
                student_name="Persona Desconocida",
                origin_course_id="Desconocido",
                detected_course_id=rec.detected_course_id,
                type="INTRUSO",
                status="ACTIVO",
                timestamp=rec.timestamp,
                duration_seconds=0.0,
                alert_sent=True
            )
            created_alert = Alert(
                id=f"alt_intruso_{int(now)}_{rec.track_id}",
                event_id=created_event.id,
                student_id=None,
                type="UNKNOWN_INTRUDER",
                message=f"Alerta: Rostro no registrado detectado en {rec.detected_course_id}",
                timestamp=rec.timestamp,
                resolved=False
            )
            return created_event, created_alert

        # 2. MANEJO DE ESTUDIANTES RECONOCIDOS
        student_id = f"{curso_origen_limpio}_{nombre_limpio}".replace(" ", "_")
        camera_type = rec.camera_type.upper()

        # Determinar el tipo de evento según la ubicación y estado
        if camera_type == "ENTRADA":
            # Evento de Ingreso al plantel
            created_event = Event(
                id=f"evt_ent_{student_id}_{int(now)}",
                student_id=student_id,
                student_name=nombre_limpio,
                origin_course_id=curso_origen_limpio,
                detected_course_id=rec.detected_course_id,
                type="ENTRADA",
                status="COMPLETADO",
                timestamp=rec.timestamp
            )
            # Cierra incidentes previos si existieran
            self.close_incident(student_id, now)

        elif camera_type == "SALIDA":
            # Evento de Salida del plantel
            created_event = Event(
                id=f"evt_sal_{student_id}_{int(now)}",
                student_id=student_id,
                student_name=nombre_limpio,
                origin_course_id=curso_origen_limpio,
                detected_course_id=rec.detected_course_id,
                type="SALIDA",
                status="COMPLETADO",
                timestamp=rec.timestamp
            )
            self.close_incident(student_id, now)

        else: # Camera type: AULA
            if rec.detected_course_id == curso_origen_limpio:
                # PRESENCIA NORMAL (Estudiante en su curso asignado)
                created_event = Event(
                    id=f"evt_pres_{student_id}_{int(now)}",
                    student_id=student_id,
                    student_name=nombre_limpio,
                    origin_course_id=curso_origen_limpio,
                    detected_course_id=rec.detected_course_id,
                    type="PRESENCIA",
                    status="COMPLETADO",
                    timestamp=rec.timestamp
                )
                # Si estaba registrado como incidente (fuera de curso), se cierra
                self.close_incident(student_id, now)

            else:
                # CURSO DIFERENTE (Estudiante en aula que NO es la suya)
                if student_id not in self.active_incidents:
                    # Iniciar nuevo incidente de permanencia
                    inc_id = f"inc_{student_id}_{int(now)}"
                    event_id = f"evt_cdif_{student_id}_{int(now)}"
                    
                    incident = ActiveIncident(
                        incident_id=inc_id,
                        student_id=student_id,
                        student_name=nombre_limpio,
                        origin_course_id=curso_origen_limpio,
                        detected_course_id=rec.detected_course_id,
                        start_time=now,
                        last_seen_time=now,
                        duration_seconds=0.0,
                        status="ACTIVO",
                        alert_sent=False,
                        initial_event_id=event_id
                    )
                    self.active_incidents[student_id] = incident

                    created_event = Event(
                        id=event_id,
                        student_id=student_id,
                        student_name=nombre_limpio,
                        origin_course_id=curso_origen_limpio,
                        detected_course_id=rec.detected_course_id,
                        type="CURSO_DIFERENTE",
                        status="ACTIVO",
                        timestamp=rec.timestamp
                    )
                else:
                    # Actualizar incidente existente
                    incident = self.active_incidents[student_id]
                    incident.last_seen_time = now
                    incident.duration_seconds = round(now - incident.start_time, 2)

                    # Evaluar regla de 10 minutos
                    if (
                        incident.duration_seconds >= self.time_limit_seconds
                        and not incident.alert_sent
                    ):
                        incident.alert_sent = True
                        created_alert = Alert(
                            id=f"alt_10min_{student_id}_{int(now)}",
                            event_id=incident.initial_event_id,
                            student_id=student_id,
                            type="PERMANENCIA_EXCESIVA_10_MIN",
                            message=f"Alerta: Estudiante {nombre_limpio} de {curso_origen_limpio} lleva más de {int(self.time_limit_seconds/60)} minutos en {rec.detected_course_id}",
                            timestamp=rec.timestamp,
                            resolved=False
                        )

        return created_event, created_alert

    def evaluate_pending_incidents(
        self, current_time: Optional[float] = None
    ) -> List[Alert]:
        """
        Evaluación periódica en background para detectar incidentes que superaron los 10 minutos.
        Garantiza que NO se generen alertas duplicadas para el mismo incidente.
        """
        now = current_time if current_time is not None else time.time()
        new_alerts: List[Alert] = []

        for student_id, incident in list(self.active_incidents.items()):
            if incident.status != "ACTIVO":
                continue

            incident.duration_seconds = round(now - incident.start_time, 2)

            if (
                incident.duration_seconds >= self.time_limit_seconds
                and not incident.alert_sent
            ):
                incident.alert_sent = True
                alert = Alert(
                    id=f"alt_10min_{student_id}_{int(now)}",
                    event_id=incident.initial_event_id,
                    student_id=student_id,
                    type="PERMANENCIA_EXCESIVA_10_MIN",
                    message=f"Alerta: Estudiante {incident.student_name} de {incident.origin_course_id} lleva más de {int(self.time_limit_seconds/60)} minutos en {incident.detected_course_id}",
                    timestamp=datetime.now().isoformat(),
                    resolved=False
                )
                new_alerts.append(alert)

        return new_alerts

    def close_incident(
        self, student_id: str, current_time: Optional[float] = None
    ) -> Optional[Event]:
        """Cierra el incidente activo de un estudiante cuando la situación se normaliza."""
        if student_id not in self.active_incidents:
            return None

        now = current_time if current_time is not None else time.time()
        incident = self.active_incidents.pop(student_id)
        incident.status = "RESUELTO"
        incident.last_seen_time = now
        incident.duration_seconds = round(now - incident.start_time, 2)

        closing_event = Event(
            id=f"evt_close_{student_id}_{int(now)}",
            student_id=student_id,
            student_name=incident.student_name,
            origin_course_id=incident.origin_course_id,
            detected_course_id=incident.detected_course_id,
            type="INCIDENTE_RESUELTO",
            status="RESUELTO",
            timestamp=datetime.now().isoformat(),
            duration_seconds=incident.duration_seconds
        )
        return closing_event

# Instancia global del procesador de eventos
event_processor = EventProcessor()
