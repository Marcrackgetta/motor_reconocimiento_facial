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
        docs = db_manager.db.collection_group("Eventos").get()
        if not docs:
            docs = db_manager.db.collection("Eventos").get()

        res = []
        for d in docs:
            data = d.to_dict()
            if student_id and data.get("estudiante_id") != student_id:
                continue
            res.append({"id": d.id, **data})

        res.sort(key=lambda x: x.get("fecha_hora", ""), reverse=True)
        return res[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo eventos: {e}")
