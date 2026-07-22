from fastapi import APIRouter
import logging
from src.backend.services.db_service import db_manager

router = APIRouter()

@router.get("/alerts")
def get_alerts():
    if not db_manager.db:
        return []
    
    alertas = []
    try:
        registros = db_manager.db.collection_group("RegistroDiario").get()
        for doc in registros:
            data = doc.to_dict()
            intrusos = data.get("total_intrusos", 0)
            desconocidos = data.get("total_desconocidos", 0)
            if intrusos > 0 or desconocidos > 0:
                alertas.append(data)
                
        alertas.sort(key=lambda x: f"{x.get('fecha', '')} {x.get('hora_inicio', '')}", reverse=True)
        return alertas
    except Exception as e:
        logging.error(f"Error fetching alerts: {e}")
        return []
