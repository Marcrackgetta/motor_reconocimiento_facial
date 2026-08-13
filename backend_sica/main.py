from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from . import models, schemas
from .database import engine, get_db

# Crea todas las tablas en la base de datos automáticamente
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SICA Backend API", version="1.0.0")

# Configuramos el motor de plantillas apuntando a nuestra nueva carpeta
templates = Jinja2Templates(directory="backend_sica/templates")


# ==========================================
# RUTAS DEL FRONTEND (INTERFAZ WEB)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def leer_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Renderiza la vista principal del panel de control.
    """
    # Por ahora solo cargamos la plantilla. Más adelante le pasaremos datos reales.
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={"titulo": "Dashboard SICA"}
    )


# ==========================================
# RUTAS DE LA API (COMUNICACIÓN CON EL MOTOR)
# ==========================================

@app.post("/api/v1/setup/poblar-datos/")
def poblar_datos_prueba(db: Session = Depends(get_db)):
    """
    Ruta para inicializar la base de datos con información de prueba.
    """
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
    """
    Recibe un evento del Motor Edge, evalúa la regla de negocio y guarda la asistencia.
    """
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