from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
import requests
import asyncio
import json
import logging
from .database import db_manager

app = FastAPI(title="Motor Reconocimiento Facial Backend")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FIREBASE_WEB_API_KEY = "AIzaSyBtX7uKiGBcJKANRZ4KLW3Tvge2NgDsmoU"

# Connection manager para WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

async def evaluador_10_minutos():
    while True:
        try:
            db_manager.verificar_regla_10_minutos()
        except Exception as e:
            pass
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    manager.reset_camera_states()
    asyncio.create_task(evaluador_10_minutos())

class LoginRequest(BaseModel):
    email: str
    password: str

class StartSessionRequest(BaseModel):
    camara_info: dict
    known_names: list = []

class DetectionRequest(BaseModel):
    session_id: str
    identidad: str
    estado: str
    confianza: float
    camara_info: dict
    known_names: list = []

class IntruderDurationRequest(BaseModel):
    session_id: str
    doc_id: str
    duracion: float
    identidad: str

class EndSessionRequest(BaseModel):
    session_id: str

@app.post("/login")
def login(req: LoginRequest):
    # Usar Firebase REST API para validar email/password
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": req.email,
        "password": req.password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        token = data["idToken"]
        # Obtener rol del usuario desde Firestore
        rol = db_manager.get_user_role(req.email)
        if rol == "Desconocido":
            raise HTTPException(status_code=403, detail="Usuario sin rol asignado.")
        return {"token": token, "email": req.email, "rol": rol}
    else:
        error_msg = response.json().get("error", {}).get("message", "Verifique sus credenciales")
        raise HTTPException(status_code=401, detail=error_msg)

@app.get("/cameras")
def get_cameras():
    return db_manager.get_cameras()

@app.get("/students/me")
def get_my_students(email: str):
    return db_manager.get_students_for_representative(email)

# --- PROXY ENDPOINTS HACIA EL MOTOR IA ---
ENGINE_URL = "http://127.0.0.1:5000"

@app.post("/ai/session/start")
def start_session(req: StartSessionRequest, background_tasks: BackgroundTasks):
    session_id = db_manager.iniciar_sesion_camara(req.camara_info, req.known_names)
    if not session_id:
        raise HTTPException(status_code=500, detail="No se pudo iniciar la sesión")
    
    # Notificar al dashboard por WebSocket
    background_tasks.add_task(manager.broadcast, json.dumps({
        "type": "SESSION_STARTED",
        "session_id": session_id,
        "camara_info": req.camara_info
    }))
    
    return {"session_id": session_id}

@app.post("/ai/detection")
def register_detection(req: DetectionRequest, background_tasks: BackgroundTasks):
    updated_data = db_manager.registrar_deteccion(
        req.session_id, req.identidad, req.estado, req.confianza, req.camara_info, known_names=req.known_names
    )
    if updated_data:
        # Notificar al dashboard por WebSocket
        background_tasks.add_task(manager.broadcast, json.dumps({
            "type": "DETECTION_UPDATED",
            "session_id": req.session_id,
            "data": updated_data
        }))
        return {"status": "success", "doc_id": updated_data.get("id")}
    return {"status": "ignored"}

@app.post("/ai/intruder/duration")
def update_intruder_duration(req: IntruderDurationRequest, background_tasks: BackgroundTasks):
    updated_data = db_manager.actualizar_duracion_intruso(
        req.session_id, req.doc_id, req.duracion, req.identidad
    )
    if updated_data:
         background_tasks.add_task(manager.broadcast, json.dumps({
            "type": "DETECTION_UPDATED",
            "session_id": req.session_id,
            "data": updated_data
        }))
    return {"status": "success"}

@app.post("/ai/session/end")
def end_session(req: EndSessionRequest, background_tasks: BackgroundTasks):
    db_manager.cerrar_sesion_camara(req.session_id)
    background_tasks.add_task(manager.broadcast, json.dumps({
        "type": "SESSION_ENDED",
        "session_id": req.session_id
    }))
    return {"status": "success"}

@app.get("/alerts")
def get_alerts():
    # En FastAPI con Firebase Admin, necesitamos buscar en la base de datos
    # como en collectionGroup('RegistroDiario').
    if not db_manager.db:
        return []
    
    alertas = []
    try:
        # En Firebase Admin python, podemos usar collection_group
        registros = db_manager.db.collection_group("RegistroDiario").get()
        for doc in registros:
            data = doc.to_dict()
            intrusos = data.get("total_intrusos", 0)
            desconocidos = data.get("total_desconocidos", 0)
            if intrusos > 0 or desconocidos > 0:
                alertas.append(data)
                
        # Ordenamos por fecha y hora (descendente)
        alertas.sort(key=lambda x: f"{x.get('fecha', '')} {x.get('hora_inicio', '')}", reverse=True)
        return alertas
    except Exception as e:
        logging.error(f"Error fetching alerts: {e}")
        return []

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Mantener conexión viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
