from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from . import models, schemas, auth
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SICA Backend API REST", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"mensaje": "SICA API REST Segura Activa"}

# ==========================================
# RUTAS DE AUTENTICACIÓN
# ==========================================

@app.post("/api/v1/auth/login", response_model=schemas.TokenResponse)
def login_for_access_token(login_data: schemas.LoginData, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.email == login_data.email).first()
    if not user or not auth.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    
    access_token = auth.create_access_token(data={"sub": user.email, "rol": user.rol})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "rol": user.rol,
        "nombre_completo": user.nombre_completo
    }

# ==========================================
# RUTAS DE USUARIOS Y GESTIÓN (PROTEGIDAS)
# ==========================================

@app.post("/api/v1/usuarios/registrar", response_model=schemas.UsuarioResponse)
def registrar_usuario(
    usuario: schemas.UsuarioCreate, 
    db: Session = Depends(get_db), 
    current_admin: models.Usuario = Depends(auth.get_current_admin_user)
):
    existe = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    nuevo_usuario = models.Usuario(
        email=usuario.email,
        password_hash=auth.get_password_hash(usuario.password),
        rol=usuario.rol.upper(),
        nombre_completo=usuario.nombre_completo
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.get("/api/v1/usuarios/")
def listar_usuarios(db: Session = Depends(get_db), current_admin: models.Usuario = Depends(auth.get_current_admin_user)):
    return db.query(models.Usuario).all()

@app.get("/api/v1/usuarios/rol/{rol}")
def listar_usuarios_por_rol(rol: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    """Obtiene una lista de usuarios filtrada por rol (útil para dropdowns de asignación)"""
    return db.query(models.Usuario).filter(models.Usuario.rol == rol.upper()).all()

# ==========================================
# RUTAS DE LA API PARA FLUTTER (PROTEGIDAS)
# ==========================================

@app.get("/api/v1/dashboard/")
def obtener_metricas_dashboard(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    total_presentes = db.query(models.Asistencia).filter(models.Asistencia.estado == "PRESENTE").count()
    total_intrusos = db.query(models.Asistencia).filter(models.Asistencia.estado == "INTRUSO").count()
    asistencias_raw = db.query(models.Asistencia).order_by(desc(models.Asistencia.fecha_registro)).limit(50).all()

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
def listar_estudiantes(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    if current_user.rol == "REPRESENTANTE":
        estudiantes_raw = db.query(models.Estudiante).filter(models.Estudiante.representante_id == current_user.id).all()
    else:
        estudiantes_raw = db.query(models.Estudiante).all()

    lista_estudiantes = []
    for e in estudiantes_raw:
        lista_estudiantes.append({
            "id": e.id,
            "uuid": e.uuid,
            "nombre_completo": e.nombre_completo,
            "curso_id": e.curso_id,
            "curso_nombre": e.curso.nombre if e.curso else "Sin Curso",
            "representante_id": e.representante_id,
            "representante_nombre": e.representante.nombre_completo if e.representante else "Sin Asignar"
        })
    return lista_estudiantes

@app.post("/api/v1/estudiantes/nuevo")
def crear_estudiante(estudiante: schemas.EstudianteNuevo, db: Session = Depends(get_db), current_admin: models.Usuario = Depends(auth.get_current_admin_user)):
    """Crea la entidad estudiante y guarda la asignación de su curso y representante en un solo paso."""
    existe = db.query(models.Estudiante).filter(models.Estudiante.uuid == estudiante.uuid).first()
    if existe:
        raise HTTPException(status_code=400, detail="El identificador (UUID) ya existe")
    
    nuevo_estudiante = models.Estudiante(
        uuid=estudiante.uuid,
        nombre_completo=estudiante.nombre_completo,
        curso_id=estudiante.curso_id,
        representante_id=estudiante.representante_id
    )
    db.add(nuevo_estudiante)
    db.commit()
    return {"mensaje": "Estudiante creado y asignado exitosamente"}

@app.get("/api/v1/cursos/")
def listar_cursos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)):
    cursos_raw = db.query(models.Curso).all()
    lista_cursos = []
    for c in cursos_raw:
        lista_cursos.append({
            "id": c.id,
            "nombre": c.nombre,
            "inspector_id": c.inspector_id,
            "inspector_nombre": c.inspector.nombre_completo if c.inspector else "Sin Asignar"
        })
    return lista_cursos

@app.post("/api/v1/cursos/")
def crear_curso(curso: schemas.CursoCreate, db: Session = Depends(get_db), current_admin: models.Usuario = Depends(auth.get_current_admin_user)):
    nuevo_curso = models.Curso(nombre=curso.nombre, inspector_id=curso.inspector_id)
    db.add(nuevo_curso)
    db.commit()
    return {"mensaje": "Curso creado exitosamente"}

# ==========================================
# RUTAS DEL MOTOR EDGE (SIN JWT POR AHORA)
# ==========================================

@app.post("/api/v1/eventos/registrar/")
def registrar_evento(evento: schemas.EventoEdge, db: Session = Depends(get_db)):
    camara = db.query(models.Camara).filter(models.Camara.camera_id == evento.camera_id).first()
    estudiante = db.query(models.Estudiante).filter(models.Estudiante.uuid == evento.identity_uuid).first()
    
    estado_asistencia = "DESCONOCIDO"
    if estudiante and camara:
        estado_asistencia = "PRESENTE" if camara.curso_id == estudiante.curso_id else "INTRUSO"
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
    return {"mensaje": "Evento procesado"}

@app.post("/api/v1/setup/crear-admin-maestro/")
def crear_admin_maestro(db: Session = Depends(get_db)):
    existe = db.query(models.Usuario).filter(models.Usuario.email == "admin@sica.com").first()
    if not existe:
        admin = models.Usuario(
            email="admin@sica.com",
            password_hash=auth.get_password_hash("admin123"),
            rol="ADMINISTRADOR",
            nombre_completo="Administrador Principal"
        )
        db.add(admin)
        db.commit()
        return {"mensaje": "Administrador maestro creado: admin@sica.com / admin123"}
    return {"mensaje": "El administrador ya existe"}