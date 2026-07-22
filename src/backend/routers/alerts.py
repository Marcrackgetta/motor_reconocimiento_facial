from fastapi import APIRouter, HTTPException
from typing import List
from src.backend.services.db_service import db_manager
from src.backend.services.event_processor import event_processor

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("/")
def get_alerts():
    """
    Obtiene alertas activas de intrusos y permanencia excesiva fuera de aula.
    """
    if not db_manager.db:
        return []
    
    alertas = []
    try:
        docs = db_manager.db.collection("Alertas").get()
        for d in docs:
            alertas.append({"id": d.id, **d.to_dict()})
            
        # Incluir también registros de intrusos de RegistroDiario para retrocompatibilidad
        registros = db_manager.db.collection_group("RegistroDiario").get()
        for doc in registros:
            data = doc.to_dict()
            if data.get("total_intrusos", 0) > 0 or data.get("total_desconocidos", 0) > 0:
                alertas.append({"id": doc.id, **data})
                
        return alertas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo alertas: {e}")

@router.post("/evaluate")
def evaluate_alerts():
    """
    Fuerza la evaluación del temporizador de permanencia (regla de 10 minutos).
    """
    generated = db_manager.verificar_regla_10_minutos()
    return {"evaluadas": len(generated), "alertas": generated}
