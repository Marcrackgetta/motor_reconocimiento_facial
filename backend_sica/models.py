from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(String, nullable=False) # 'ADMINISTRADOR', 'INSPECTOR', 'REPRESENTANTE'
    nombre_completo = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relaciones
    cursos_a_cargo = relationship("Curso", back_populates="inspector")
    estudiantes_representados = relationship("Estudiante", back_populates="representante")

class Curso(Base):
    __tablename__ = "cursos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    inspector_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    # Relaciones
    inspector = relationship("Usuario", back_populates="cursos_a_cargo")
    estudiantes = relationship("Estudiante", back_populates="curso")
    camaras = relationship("Camara", back_populates="curso")

class Estudiante(Base):
    __tablename__ = "estudiantes"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True)
    nombre_completo = Column(String)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=True)
    representante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    # Relaciones
    curso = relationship("Curso", back_populates="estudiantes")
    representante = relationship("Usuario", back_populates="estudiantes_representados")
    asistencias = relationship("Asistencia", back_populates="estudiante")
    notificaciones = relationship("Notificacion", back_populates="estudiante")

class Camara(Base):
    __tablename__ = "camaras"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, unique=True, index=True)
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
    bloque_horario = Column(String)
    estado = Column(String)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    estudiante = relationship("Estudiante", back_populates="asistencias")

class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    estudiante_uuid = Column(String, ForeignKey("estudiantes.uuid"))
    tipo = Column(String) # 'NOVEDAD', 'ALERTA', 'FALTA'
    mensaje = Column(String, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    leida = Column(Boolean, default=False)

    # Relaciones
    estudiante = relationship("Estudiante", back_populates="notificaciones")