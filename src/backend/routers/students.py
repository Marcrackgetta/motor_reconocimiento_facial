from fastapi import APIRouter, HTTPException
from src.backend.services.db_service import db_manager

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("/me")
def get_my_students(email: str):
    if not email:
        raise HTTPException(status_code=400, detail="El parámetro email es obligatorio.")
    return db_manager.get_students_for_representative(email)

@router.get("/{student_id}/history")
def get_student_history(student_id: str, email: str = "", limit: int = 20):
    if not db_manager.db:
        return []

    # Verificación de autorización por rol y asignación
    if email:
        role = db_manager.get_user_role(email)
        if role == "representante":
            my_students = db_manager.get_students_for_representative(email)
            my_student_ids = [s["id"] for s in my_students if "id" in s]
            if student_id not in my_student_ids:
                raise HTTPException(
                    status_code=403,
                    detail="Acceso denegado: El estudiante no está asignado a su cuenta."
                )

    eventos_ref = db_manager.db.collection("Eventos")\
        .where("estudiante_id", "==", student_id)\
        .order_by("fecha_hora", direction="DESCENDING")\
        .limit(limit)\
        .get()

    return [{"id": e.id, **e.to_dict()} for e in eventos_ref]
