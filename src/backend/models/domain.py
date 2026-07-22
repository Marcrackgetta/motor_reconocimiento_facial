from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Course(BaseModel):
    """Modelo de Dominio para Curso Escolar"""
    id: str = Field(..., description="Identificador único del curso (ej. 3_CC_A_Mat)")
    name: str = Field(..., description="Nombre del curso (ej. 3ro Ciencias A)")
    parallel: str = Field(default="", description="Paralelo o sección")
    teacher_id: Optional[str] = Field(default=None, description="Correo/ID del docente tutor")

class Student(BaseModel):
    """Modelo de Dominio para Estudiante"""
    id: str = Field(..., description="Identificador único del estudiante")
    name: str = Field(..., description="Nombre completo del estudiante (SIN concatenar curso)")
    first_name: str = Field(..., description="Primer nombre")
    last_name: str = Field(..., description="Apellidos")
    origin_course_id: str = Field(..., description="ID del curso de origen asignado")
    representatives: List[str] = Field(default_factory=list, description="Lista de correos de representantes")
    current_status: str = Field(
        default="DESCONOCIDO", 
        description="Estado actual (PRESENCIA_NORMAL, CURSO_DIFERENTE, DENTRO_DE_LA_INSTITUCION, FUERA_DE_LA_INSTITUCION, DESCONOCIDO)"
    )
    last_detected_course_id: Optional[str] = Field(default=None, description="ID del curso donde fue detectado por última vez")
    last_seen_at: Optional[str] = Field(default=None, description="ISO Timestamp de la última detección")
    last_event_id: Optional[str] = Field(default=None, description="ID del último evento generado")

class Representative(BaseModel):
    """Modelo de Dominio para Representante"""
    id: str = Field(..., description="Identificador único (correo electrónico)")
    email: str = Field(..., description="Correo electrónico del representante")
    full_name: str = Field(..., description="Nombre completo del representante")
    phone: Optional[str] = Field(default=None, description="Teléfono de contacto")

class RepresentativeStudent(BaseModel):
    """Relación entre Representante y Estudiante"""
    id: str = Field(..., description="ID único de la relación")
    representative_id: str = Field(..., description="ID/Email del representante")
    student_id: str = Field(..., description="ID del estudiante")

class Camera(BaseModel):
    """Modelo de Dominio para Cámara de Control"""
    id: str = Field(..., description="ID único de la cámara / curso asignado")
    assigned_course_id: str = Field(..., description="ID del curso asignado a la cámara")
    type: str = Field(..., description="Tipo de ubicación (AULA, ENTRADA, SALIDA)")
    location: Dict[str, float] = Field(default_factory=lambda: {"lat": 0.0, "lon": 0.0})
    status: str = Field(default="APAGADA", description="Estado de transmisión (ACTIVA, APAGADA)")

class Recognition(BaseModel):
    """Resultado bruto de reconocimiento por visión artificial"""
    id: str = Field(..., description="ID único del reconocimiento")
    track_id: int = Field(..., description="ID de rastreo ByteTrack")
    session_id: str = Field(..., description="ID de la sesión de cámara")
    identity_raw: str = Field(..., description="Etiqueta cruda reconocida por el motor IA")
    student_id: Optional[str] = Field(default=None, description="ID del estudiante si fue resuelto")
    confidence: float = Field(..., description="Porcentaje de confianza (0.0 a 100.0)")
    status: str = Field(..., description="Clasificación (PRESENTE, INTRUSO, DESCONOCIDO)")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class Event(BaseModel):
    """Hecho relevante de presencia o desplazamiento registrado"""
    id: str = Field(..., description="ID único del evento")
    student_id: Optional[str] = Field(default=None, description="ID del estudiante involucrado")
    student_name: str = Field(..., description="Nombre limpio del estudiante")
    origin_course_id: str = Field(..., description="ID del curso de origen del estudiante")
    detected_course_id: str = Field(..., description="ID del curso/cámara donde fue detectado")
    type: str = Field(..., description="Tipo de evento (ENTRADA, SALIDA, PRESENCIA_NORMAL, CURSO_DIFERENTE, INTRUSO_EXTERNO)")
    status: str = Field(default="ACTIVO", description="Estado operacional del evento")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    duration_seconds: float = Field(default=0.0, description="Duración en segundos")
    alert_sent: bool = Field(default=False, description="Flag de alerta enviada (ej. regla 10 minutos)")

class Alert(BaseModel):
    """Alerta de seguridad o alerta de permanencia excedida"""
    id: str = Field(..., description="ID único de la alerta")
    event_id: Optional[str] = Field(default=None, description="ID del evento que provocó la alerta")
    student_id: Optional[str] = Field(default=None, description="ID del estudiante involucrado")
    type: str = Field(..., description="Tipo de alerta (PERMANENCIA_EXCESIVA_10_MIN, INTRUSO_DESCONOCIDO, SALIDA_NO_AUTORIZADA)")
    message: str = Field(..., description="Mensaje explicativo para el usuario")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = Field(default=False, description="Si la alerta fue atendida/resuelta")

class Notification(BaseModel):
    """Notificación destinada a un usuario final (ej. Representante/Inspector)"""
    id: str = Field(..., description="ID único de la notificación")
    recipient_id: str = Field(..., description="ID/Correo del destinatario")
    alert_id: Optional[str] = Field(default=None, description="ID de la alerta asociada")
    title: str = Field(..., description="Título de la notificación")
    body: str = Field(..., description="Cuerpo del mensaje")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    read: bool = Field(default=False, description="Estado de lectura")
