from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from src.backend.core.ws_manager import ws_manager
from src.backend.services.db_service import db_manager
from src.backend.routers import auth, students, cameras, notifications, ai_motor

app = FastAPI(title="Control Acceso Modular API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.backend.core.audit import AuditLogMiddleware
app.add_middleware(AuditLogMiddleware)

async def evaluador_10_minutos():
    while True:
        try:
            alertas = db_manager.verificar_regla_10_minutos()
            if alertas:
                for alerta in alertas:
                    await ws_manager.emit_event("ALERTA_UBICACION", alerta)
        except Exception as e:
            pass
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    # Inicialización central
    asyncio.create_task(evaluador_10_minutos())

from src.backend.routers import auth, students, cameras, notifications, ai_motor, users, courses, reports, settings

# Routers para la Fase 2 y 3
app.include_router(auth.router, tags=["Auth"])
app.include_router(users.router, tags=["Users"])
app.include_router(students.router, tags=["Students"])
app.include_router(courses.router, tags=["Courses"])
app.include_router(cameras.router, tags=["Cameras"])
app.include_router(notifications.router, tags=["Notifications"])
app.include_router(reports.router, tags=["Reports"])
app.include_router(settings.router, tags=["Settings"])
app.include_router(ai_motor.router, tags=["AI Motor"])

# Redireccionador temporal de WebSockets de app.py
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
