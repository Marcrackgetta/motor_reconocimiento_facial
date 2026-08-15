from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from . import models, schemas, auth
from .database import engine, get_db

# Como cambiamos el esquema fuertemente, forzaremos la recreación de tablas (solo en desarrollo)
# IMPORTANTE: Si te da error de base de datos, borra el archivo 'sica_local.db' antes de ejecutar
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
    """Valida credenciales y retorna un JWT"""
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
    current_admin: models.Usuario = Depends(auth.get_current_admin_user) # GUARDIÁN ACTIVO
):
    """Solo los Administradores pueden registrar nuevos usuarios (Representantes, Inspectores, etc.)"""
    existe = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    nuevo_usuario = models.Usuario(
        email=usuario.email,
        password_hash=auth.get_password_hash(usuario.password),
        rol=usuario.rol.upper(), # Aseguramos que el rol esté en mayúsculas
        nombre_completo=usuario.nombre_completo
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


# ==========================================
# RUTAS DEL MOTOR EDGE (SIN JWT POR AHORA)
# ==========================================

@app.post("/api/v1/eventos/registrar/")
def registrar_evento(evento: schemas.EventoEdge, db: Session = Depends(get_db)):
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
    
    return {"mensaje": "Evento procesado", "estado_calculado": estado_asistencia}


# ==========================================
# RUTAS DE INICIALIZACIÓN TEMPORAL (DEV ONLY)
# ==========================================

@app.post("/api/v1/setup/crear-admin-maestro/")
def crear_admin_maestro(db: Session = Depends(get_db)):
    """Crea el primer administrador para poder usar el sistema. (Borrar en producción)"""
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

@app.get("/api/v1/dashboard/")
def obtener_metricas_dashboard(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user) # GUARDIÁN AÑADIDO
):
    """Devuelve las métricas en formato JSON exigiendo un token válido."""
    # ... (El resto de la lógica de esta función se mantiene exactamente igual) ...
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
def listar_estudiantes(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user) # GUARDIÁN AÑADIDO
):
    """
    Devuelve la lista de estudiantes. 
    Lógica de Autorización: Si es representante, solo ve a sus hijos.
    """
    # Filtramos la base de datos según el rol del usuario que hace la petición
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
            "curso_nombre": e.curso.nombre if e.curso else "Sin Curso"
        })
    return lista_estudiantes