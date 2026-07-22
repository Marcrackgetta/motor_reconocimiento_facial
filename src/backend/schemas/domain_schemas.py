from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# --- SCHEMAS DE AUTENTICACIÓN ---
class LoginRequestSchema(BaseModel):
    email: str
    password: str

class LoginResponseSchema(BaseModel):
    token: str
    email: str
    rol: str

# --- SCHEMAS DE ESTUDIANTES Y REPRESENTANTES ---
class StudentResponseSchema(BaseModel):
    id: str
    nombre: str
    curso_origen: str
    curso_detectado: Optional[str] = "General"
    estado_actual: str = "DESCONOCIDO"
    representantes: List[str] = []
    ultima_deteccion: Optional[str] = None

class RepresentativeStudentsRequestSchema(BaseModel):
    email: str

# --- SCHEMAS DE CURSOS ---
class CourseCreateSchema(BaseModel):
    nombre: str
    paralelo: str
    docente_id: Optional[str] = None

class CourseResponseSchema(BaseModel):
    id: str
    nombre: str
    paralelo: str
    docente_id: Optional[str] = None

# --- SCHEMAS DE CÁMARAS ---
class CameraResponseSchema(BaseModel):
    id: str
    curso_asignado: str
    estado: str = "APAGADA"
    tipo: str = "AULA"

# --- SCHEMAS DE MOTOR IA ---
class StartSessionRequestSchema(BaseModel):
    camara_info: dict
    known_names: List[str] = []

class DetectionRequestSchema(BaseModel):
    session_id: str
    identidad: str
    estado: str
    confianza: float
    camara_info: dict
    known_names: List[str] = []

class IntruderDurationRequestSchema(BaseModel):
    session_id: str
    doc_id: str
    duracion: float
    identidad: str

class EndSessionRequestSchema(BaseModel):
    session_id: str

# --- SCHEMAS DE EVENTOS, ASISTENCIA Y ALERTAS ---
class EventResponseSchema(BaseModel):
    id: str
    student_id: Optional[str] = None
    nombre: str
    curso_origen: str
    curso_detectado: str
    tipo_evento: str
    fecha_hora: str
    alerta_enviada: bool = False

class AlertResponseSchema(BaseModel):
    id: str
    event_id: Optional[str] = None
    student_id: Optional[str] = None
    type: str
    message: str
    timestamp: str
    resolved: bool = False

class AttendanceRecordSchema(BaseModel):
    fecha: str
    hora_inicio: str
    hora_fin: Optional[str] = ""
    curso: str
    total_presentes: int = 0
    total_ausentes: int = 0
    total_intrusos: int = 0
    total_desconocidos: int = 0
