from fastapi import APIRouter, HTTPException
from typing import List
from src.backend.services.db_service import db_manager

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/daily")
def get_daily_attendance(curso: str = None):
    """
    Obtiene los registros diarios de asistencia de las sesiones de cámara.
    """
    if not db_manager.db:
        return []
    
    try:
        registros = db_manager.db.collection_group("RegistroDiario").get()
        resultados = []
        for doc in registros:
            data = doc.to_dict()
            if curso and data.get("curso") != curso:
                continue
            resultados.append({"id": doc.id, **data})
            
        resultados.sort(key=lambda x: f"{x.get('fecha', '')} {x.get('hora_inicio', '')}", reverse=True)
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo asistencia: {e}")
