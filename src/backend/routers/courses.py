from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from src.backend.services.db_service import db_manager
from src.backend.core.dependencies import RequireRole

router = APIRouter(prefix="/courses", tags=["Courses"])

class CourseRequest(BaseModel):
    nombre: str
    paralelo: str
    docente_id: str = None

@router.get("/")
def get_courses(user: dict = Depends(RequireRole(["Administrador", "Rector", "Inspector", "Docente"]))):
    if not db_manager.db:
        return []
    docs = db_manager.db.collection("Cursos").get()
    return [{"id": d.id, **d.to_dict()} for d in docs]

@router.post("/")
def create_course(req: CourseRequest, user: dict = Depends(RequireRole(["Administrador", "Rector"]))):
    if not db_manager.db:
        raise HTTPException(status_code=500, detail="Base de datos no disponible")
        
    new_course = {"nombre": req.nombre, "paralelo": req.paralelo, "docente_id": req.docente_id}
    doc_ref = db_manager.db.collection("Cursos").document()
    doc_ref.set(new_course)
    return {"id": doc_ref.id, **new_course}
