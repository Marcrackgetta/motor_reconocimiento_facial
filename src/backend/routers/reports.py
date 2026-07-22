from fastapi import APIRouter, Depends
from src.backend.services.db_service import db_manager
from src.backend.core.dependencies import RequireRole

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/metrics")
def get_metrics(user: dict = Depends(RequireRole(["Administrador", "Rector", "Inspector"]))):
    if not db_manager.db:
        return {}
    
    # Simple metrics aggregation
    eventos = db_manager.db.collection("Eventos").get()
    
    total_entradas = 0
    total_salidas = 0
    total_alertas = 0
    
    for doc in eventos:
        data = doc.to_dict()
        tipo = data.get("tipo_evento")
        if tipo == "ENTRADA":
            total_entradas += 1
        elif tipo == "SALIDA":
            total_salidas += 1
        
        if data.get("alerta_enviada"):
            total_alertas += 1
            
    return {
        "entradas": total_entradas,
        "salidas": total_salidas,
        "alertas_ubicacion": total_alertas,
        "total_eventos": len(eventos)
    }
