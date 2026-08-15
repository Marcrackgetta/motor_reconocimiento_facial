from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- ESQUEMAS DE EVENTOS (EDGE) ---
class EventoEdge(BaseModel):
    identity_uuid: str
    camera_id: str
    timestamp: float
    block: str
    status: str

# --- ESQUEMAS DE AUTENTICACIÓN ---
class LoginData(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre_completo: str

# --- ESQUEMAS DE USUARIOS ---
class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str
    rol: str
    nombre_completo: str

class UsuarioResponse(BaseModel):
    id: int
    email: str
    rol: str
    nombre_completo: str
    is_active: bool

    class Config:
        from_attributes = True

# --- ESQUEMAS PARA ESTUDIANTES Y CURSOS ---
class EstudianteNuevo(BaseModel):
    uuid: str
    nombre_completo: str
    curso_id: int
    representante_id: Optional[int] = None