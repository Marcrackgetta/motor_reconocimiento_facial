import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from src.backend.core.ws_manager import ws_manager
from src.backend.services.db_service import db_manager
from src.backend.routers import auth, students, cameras, notifications, ai_motor

app = FastAPI(title="Control Acceso Modular API")

allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:8000,http://localhost:8000"
)
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.backend.core.audit import AuditLogMiddleware
from src.backend.core.rate_limiter import RateLimiterMiddleware

app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimiterMiddleware, max_requests=10, window_seconds=60)

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

from src.backend.routers import (
    auth, users, students, representatives, courses, cameras,
    attendance, events, alerts, notifications, reports, settings, ai_motor
)

# Routers organizados por dominio
app.include_router(auth.router, tags=["Auth"])
app.include_router(users.router, tags=["Users"])
app.include_router(students.router, tags=["Students"])
app.include_router(representatives.router, tags=["Representatives"])
app.include_router(courses.router, tags=["Courses"])
app.include_router(cameras.router, tags=["Cameras"])
app.include_router(attendance.router, tags=["Attendance"])
app.include_router(events.router, tags=["Events"])
app.include_router(alerts.router, tags=["Alerts"])
app.include_router(notifications.router, tags=["Notifications"])
app.include_router(reports.router, tags=["Reports"])
app.include_router(settings.router, tags=["Settings"])
app.include_router(ai_motor.router, tags=["AI Motor"])

from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, email: str = ""):
    student_ids = []
    if email:
        students = db_manager.get_students_for_representative(email)
        student_ids = [s["id"] for s in students if "id" in s]

    await ws_manager.connect(websocket, email=email, role="admin", student_ids=student_ids)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket, email: str = ""):
    student_ids = []
    role = "guest"
    if email:
        role = db_manager.get_user_role(email)
        students = db_manager.get_students_for_representative(email)
        student_ids = [s["id"] for s in students if "id" in s]

    await ws_manager.connect(websocket, email=email, role=role, student_ids=student_ids)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
