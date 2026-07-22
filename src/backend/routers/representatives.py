from fastapi import APIRouter, HTTPException, Depends
from typing import List
from src.backend.services.db_service import db_manager
from src.backend.schemas.domain_schemas import StudentResponseSchema

router = APIRouter(prefix="/representatives", tags=["Representatives"])

@router.get("/students", response_model=List[StudentResponseSchema])
def get_representative_students(email: str):
    """
    Obtiene la lista de estudiantes asignados a la cuenta del representante.
    """
    if not email:
        raise HTTPException(status_code=400, detail="El correo del representante es requerido.")
    
    students = db_manager.get_students_for_representative(email)
    return [
        StudentResponseSchema(
            id=s.get("id", ""),
            nombre=s.get("nombre", "Desconocido"),
            curso_origen=s.get("curso_origen", "Desconocido"),
            curso_detectado=s.get("curso_detectado", "General"),
            estado_actual=s.get("estado_actual", "DESCONOCIDO"),
            representantes=s.get("representantes", []),
            ultima_deteccion=s.get("ultima_deteccion")
        )
        for s in students
    ]
