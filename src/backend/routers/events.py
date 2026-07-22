from fastapi import APIRouter, HTTPException
from typing import List, Optional
from src.backend.services.db_service import db_manager

router = APIRouter(prefix="/events", tags=["Events"])

@router.get("/")
def get_events(student_id: Optional[str] = None, limit: int = 50):
    """
    Obtiene la lista de eventos institucionales de presencia, entradas, salidas e incidentes.
    """
    if not db_manager.db:
        return []
    
    try:
        ref = db_manager.db.collection("Eventos")
        if student_id:
            ref = ref.where("estudiante_id", "==", student_id)
            
        docs = ref.order_by("fecha_hora", direction="DESCENDING").limit(limit).get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo eventos: {e}")
