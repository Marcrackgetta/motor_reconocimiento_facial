from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.backend.services.db_service import db_manager
from src.backend.core.ws_manager import ws_manager

router = APIRouter(prefix="/ai")

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

class ResetCamerasRequest(BaseModel):
    camera_sources: list = []

class EndSessionRequest(BaseModel):
    session_id: str

@router.post("/cameras/reset")
def reset_cameras(req: ResetCamerasRequest):
    db_manager.forzar_reseteo_camaras(req.camera_sources)
    return {"status": "success"}

@router.post("/session/start")
def start_session(req: StartSessionRequest, background_tasks: BackgroundTasks):
    session_id = db_manager.iniciar_sesion_camara(req.camara_info, req.known_names)
    if not session_id:
        raise HTTPException(status_code=500, detail="No se pudo iniciar la sesión")
    
    background_tasks.add_task(
        ws_manager.emit_event, 
        "SESSION_STARTED", 
        {"session_id": session_id, "camara_info": req.camara_info}
    )
    return {"session_id": session_id}

@router.post("/detection")
def register_detection(req: DetectionRequest, background_tasks: BackgroundTasks):
    updated_data = db_manager.registrar_deteccion(
        req.session_id, req.identidad, req.estado, req.confianza, req.camara_info, known_names=req.known_names
    )
    if updated_data:
        background_tasks.add_task(
            ws_manager.emit_event, 
            "DETECTION_UPDATED", 
            {"session_id": req.session_id, "data": updated_data}
        )
        
        nuevo_evento = updated_data.get("nuevo_evento")
        if nuevo_evento:
            tipo_evento = nuevo_evento.get("tipo_evento")
            if tipo_evento:
                background_tasks.add_task(
                    ws_manager.emit_event,
                    f"EVENT_{tipo_evento}",
                    nuevo_evento
                )
                
        return {"status": "success", "doc_id": updated_data.get("id")}
    return {"status": "ignored"}

@router.post("/intruder/duration")
def update_intruder_duration(req: IntruderDurationRequest, background_tasks: BackgroundTasks):
    updated_data = db_manager.actualizar_duracion_intruso(
        req.session_id, req.doc_id, req.duracion, req.identidad
    )
    if updated_data:
        background_tasks.add_task(
            ws_manager.emit_event, 
            "DETECTION_UPDATED", 
            {"session_id": req.session_id, "data": updated_data}
        )
    return {"status": "success"}

@router.post("/session/end")
def end_session(req: EndSessionRequest, background_tasks: BackgroundTasks):
    db_manager.cerrar_sesion_camara(req.session_id)
    background_tasks.add_task(
        ws_manager.emit_event, 
        "SESSION_ENDED", 
        {"session_id": req.session_id}
    )
    return {"status": "success"}
