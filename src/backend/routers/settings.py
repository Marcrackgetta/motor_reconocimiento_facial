from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.backend.services.db_service import db_manager
from src.backend.core.dependencies import RequireRole

router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingsRequest(BaseModel):
    regla_10_minutos_segundos: int

@router.get("/")
def get_settings(user: dict = Depends(RequireRole(["Administrador", "Rector"]))):
    if not db_manager.db:
        return {"regla_10_minutos_segundos": 600}
    doc = db_manager.db.collection("Configuracion").document("global").get()
    if doc.exists:
        return doc.to_dict()
    return {"regla_10_minutos_segundos": 600}

@router.put("/")
def update_settings(req: SettingsRequest, user: dict = Depends(RequireRole(["Administrador"]))):
    if not db_manager.db:
        raise HTTPException(status_code=500, detail="Base de datos no disponible")
    
    doc_ref = db_manager.db.collection("Configuracion").document("global")
    doc_ref.set(req.model_dump(), merge=True)
    return {"status": "success"}
