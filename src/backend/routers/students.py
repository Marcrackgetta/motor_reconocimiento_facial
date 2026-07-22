from fastapi import APIRouter
from src.backend.services.db_service import db_manager

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("/me")
def get_my_students(email: str):
    return db_manager.get_students_for_representative(email)

@router.get("/{student_id}/history")
def get_student_history(student_id: str, limit: int = 20):
    if not db_manager.db:
        return []
        
    eventos_ref = db_manager.db.collection("Eventos")\
        .where("estudiante_id", "==", student_id)\
        .order_by("fecha_hora", direction="DESCENDING")\
        .limit(limit)\
        .get()
        
    return [{"id": e.id, **e.to_dict()} for e in eventos_ref]
