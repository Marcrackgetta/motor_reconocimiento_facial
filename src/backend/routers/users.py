from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from src.backend.services.db_service import db_manager
from src.backend.core.dependencies import RequireRole

router = APIRouter(prefix="/users", tags=["Users"])

class UserRequest(BaseModel):
    email: str
    rol: str

@router.get("/")
def get_users(user: dict = Depends(RequireRole(["Administrador", "Rector"]))):
    if not db_manager.db:
        return []
    docs = db_manager.db.collection("Usuarios").get()
    return [{"id": d.id, **d.to_dict()} for d in docs]

@router.post("/")
def create_user(req: UserRequest, user: dict = Depends(RequireRole(["Administrador"]))):
    if not db_manager.db:
        raise HTTPException(status_code=500, detail="Base de datos no disponible")
    
    # Check if exists
    docs = db_manager.db.collection("Usuarios").where("email", "==", req.email).get()
    if docs:
        raise HTTPException(status_code=400, detail="Usuario ya existe")
        
    new_user = {"email": req.email, "rol": req.rol}
    doc_ref = db_manager.db.collection("Usuarios").document()
    doc_ref.set(new_user)
    return {"id": doc_ref.id, **new_user}
