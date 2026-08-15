from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from . import models, schemas
from .database import engine, get_db

# Crea todas las tablas en la base de datos automáticamente
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SICA Backend API REST", version="2.0.0")

# ==========================================
# CONFIGURACIÓN CORS PARA FLUTTER PWA
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitimos cualquier origen temporalmente para desarrollo local
    allow_credentials=True,
    allow_methods=["*"],  # Permitimos GET, POST, PUT, DELETE
    allow_headers=["*"],
)


# ==========================================
# RUTAS DE LA API PARA FLUTTER
# ==========================================

@app.get("/")
def read_root():
    """Ruta base para verificar que la API está activa."""
    return {"mensaje": "SICA API REST (Flutter Backend) Activa"}

@app.get("/api/v1/dashboard/")
def obtener_metricas_dashboard(db: Session = Depends(get_db)):
    """
    Devuelve las métricas en formato JSON para pintar las tarjetas y la tabla en Flutter.
    """
    total_presentes = db.query(models.Asistencia).filter(models.Asistencia.estado == "PRESENTE").count()
    total_intrusos = db.query(models.Asistencia).filter(models.Asistencia.estado == "INTRUSO").count()
    
    asistencias_raw = db.query(models.Asistencia).order_by(desc(models.Asistencia.fecha_registro)).limit(50).all()

    # Convertimos los objetos del ORM a una lista de diccionarios para el JSON
    ultimas_asistencias = []
    for a in asistencias_raw:
        ultimas_asistencias.append({
            "id": a.id,
            "estudiante_uuid": a.estudiante_uuid,
            "camera_id": a.camera_id,
            "timestamp": a.timestamp,
            "bloque_horario": a.bloque_horario,
            "estado": a.estado,
            "fecha_registro": a.fecha_registro.strftime('%Y-%m-%d %H:%M:%S')
        })

    return {
        "total_presentes": total_presentes,
        "total_intrusos": total_intrusos,
        "asistencias": ultimas_asistencias
    }

@app.get("/api/v1/estudiantes/")
def listar_estudiantes(db: Session = Depends(get_db)):
    """
    Devuelve la lista de estudiantes para el DataGrid de Flutter.
    """
    estudiantes_raw = db.query(models.Estudiante).all()
    lista_estudiantes = []
    for e in estudiantes_raw:
        lista_estudiantes.append({
            "id": e.id,
            "uuid": e.uuid,
            "nombre_completo": e.nombre_completo,
            "curso_id": e.curso_id,
            "curso_nombre": e.curso.nombre if e.curso else "Sin Curso"
        })
    return lista_estudiantes

@app.get("/api/v1/cursos/")
def listar_cursos(db: Session = Depends(get_db)):
    """
    Devuelve la lista de cursos para llenar los DropdownButton en Flutter.
    """
    cursos_raw = db.query(models.Curso).all()
    return [{"id": c.id, "nombre": c.nombre} for c in cursos_raw]

@app.post("/api/v1/estudiantes/nuevo")
def crear_estudiante(estudiante: schemas.EstudianteNuevo, db: Session = Depends(get_db)):
    """
    Recibe un JSON desde Flutter para crear un estudiante en la base de datos.
    """
    existe = db.query(models.Estudiante).filter(models.Estudiante.uuid == estudiante.uuid).first()
    
    if not existe:
        nuevo_estudiante = models.Estudiante(
            uuid=estudiante.uuid, 
            nombre_completo=estudiante.nombre_completo, 
            curso_id=estudiante.curso_id
        )
        db.add(nuevo_estudiante)
        db.commit()
        return {"mensaje": "Estudiante creado exitosamente"}
        
    return {"error": "El identificador (UUID) ya está registrado en el sistema"}


# ==========================================
# RUTAS DE COMUNICACIÓN CON EL MOTOR EDGE
# ==========================================

@app.post("/api/v1/setup/poblar-datos/")
def poblar_datos_prueba(db: Session = Depends(get_db)):
    """Mantiene la capacidad de poblar datos de prueba temporalmente."""
    curso = db.query(models.Curso).filter(models.Curso.nombre == "2° Informática B Matutino").first()
    if not curso:
        curso = models.Curso(nombre="2° Informática B Matutino")
        db.add(curso)
        db.commit()
        db.refresh(curso)

    estudiante = db.query(models.Estudiante).filter(models.Estudiante.uuid == "Marcelo_Zambrano").first()
    if not estudiante:
        estudiante = models.Estudiante(
            uuid="Marcelo_Zambrano",
            nombre_completo="Marcelo Humberto Zambrano Aguirre",
            curso_id=curso.id
        )
        db.add(estudiante)
        db.commit()

    camara = db.query(models.Camara).filter(models.Camara.camera_id == "CAM_001").first()
    if not camara:
        camara = models.Camara(
            camera_id="CAM_001",
            ubicacion="Entrada Principal",
            curso_id=curso.id
        )
        db.add(camara)
        db.commit()

    return {"mensaje": "Base de datos poblada con éxito."}

@app.post("/api/v1/eventos/registrar/")
def registrar_evento(evento: schemas.EventoEdge, db: Session = Depends(get_db)):
    """Recibe los eventos asíncronos del Motor Edge."""
    camara = db.query(models.Camara).filter(models.Camara.camera_id == evento.camera_id).first()
    estudiante = db.query(models.Estudiante).filter(models.Estudiante.uuid == evento.identity_uuid).first()
    
    estado_asistencia = "DESCONOCIDO"
    
    if estudiante and camara:
        if camara.curso_id == estudiante.curso_id:
            estado_asistencia = "PRESENTE"
        else:
            estado_asistencia = "INTRUSO"
    elif estudiante:
        estado_asistencia = "PRESENTE"

    nueva_asistencia = models.Asistencia(
        estudiante_uuid=evento.identity_uuid,
        camera_id=evento.camera_id,
        timestamp=evento.timestamp,
        bloque_horario=evento.block,
        estado=estado_asistencia
    )
    db.add(nueva_asistencia)
    db.commit()
    db.refresh(nueva_asistencia)
    
    return {
        "mensaje": "Evento procesado correctamente",
        "estado_calculado": estado_asistencia
    }