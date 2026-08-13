from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Curso(Base):
    __tablename__ = "cursos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    
    # Relaciones
    estudiantes = relationship("Estudiante", back_populates="curso")
    camaras = relationship("Camara", back_populates="curso")

class Estudiante(Base):
    __tablename__ = "estudiantes"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True) # El identificador del Motor Edge
    nombre_completo = Column(String)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=True)
    
    # Relaciones
    curso = relationship("Curso", back_populates="estudiantes")
    asistencias = relationship("Asistencia", back_populates="estudiante")

class Camara(Base):
    __tablename__ = "camaras"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, unique=True, index=True) # Ej: CAM_001
    ubicacion = Column(String)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=True)
    
    # Relaciones
    curso = relationship("Curso", back_populates="camaras")

class Asistencia(Base):
    __tablename__ = "asistencias"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_uuid = Column(String, ForeignKey("estudiantes.uuid"))
    camera_id = Column(String)
    timestamp = Column(Float)
    bloque_horario = Column(String) # Ej: 2026-08-14_MATUTINO
    estado = Column(String)         # PRESENTE, INTRUSO, DESCONOCIDO
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="asistencias")