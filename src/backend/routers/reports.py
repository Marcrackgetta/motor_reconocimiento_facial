from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict
from src.backend.services.db_service import db_manager
from src.backend.core.dependencies import RequireRole

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/metrics")
def get_metrics():
    """Métricas consolidadas generales del sistema"""
    if not db_manager.db:
        return {"entradas": 0, "salidas": 0, "alertas_ubicacion": 0, "intrusos": 0, "total_eventos": 0}
    
    try:
        eventos = db_manager.db.collection("Eventos").get()
        total_entradas = 0
        total_salidas = 0
        total_alertas = 0
        total_intrusos = 0
        
        for doc in eventos:
            data = doc.to_dict()
            tipo = data.get("tipo_evento") or data.get("type")
            if tipo == "ENTRADA":
                total_entradas += 1
            elif tipo == "SALIDA":
                total_salidas += 1
            elif tipo in ["INTRUSO", "INTRUSO_EXTERNO"]:
                total_intrusos += 1
            
            if data.get("alerta_enviada") or data.get("alert_sent"):
                total_alertas += 1
                
        return {
            "entradas": total_entradas,
            "salidas": total_salidas,
            "alertas_ubicacion": total_alertas,
            "intrusos": total_intrusos,
            "total_eventos": len(eventos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error agregando métricas: {e}")

@router.get("/attendance")
def get_attendance_report(curso: Optional[str] = None):
    """Reporte de asistencia agregada por curso y fecha"""
    if not db_manager.db:
        return []
    
    try:
        registros = db_manager.db.collection_group("RegistroDiario").get()
        res = []
        for doc in registros:
            data = doc.to_dict()
            if curso and data.get("curso") != curso:
                continue
            res.append({
                "fecha": data.get("fecha"),
                "curso": data.get("curso"),
                "total_presentes": data.get("total_presentes", 0),
                "total_ausentes": data.get("total_ausentes", 0),
                "total_intrusos": data.get("total_intrusos", 0)
            })
        res.sort(key=lambda x: str(x.get("fecha")), reverse=True)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en reporte de asistencia: {e}")

@router.get("/entries")
def get_entries_report(limit: int = 50):
    """Reporte detallado de entradas al plantel"""
    if not db_manager.db:
        return []
    try:
        docs = db_manager.db.collection("Eventos").where("tipo_evento", "==", "ENTRADA").limit(limit).get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en reporte de entradas: {e}")

@router.get("/exits")
def get_exits_report(limit: int = 50):
    """Reporte detallado de salidas del plantel"""
    if not db_manager.db:
        return []
    try:
        docs = db_manager.db.collection("Eventos").where("tipo_evento", "==", "SALIDA").limit(limit).get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en reporte de salidas: {e}")

@router.get("/intruders")
def get_intruders_report(limit: int = 50):
    """Reporte detallado de detecciones de intrusos y personas no registradas"""
    if not db_manager.db:
        return []
    try:
        docs = db_manager.db.collection("Eventos").where("tipo_evento", "==", "INTRUSO_EXTERNO").limit(limit).get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en reporte de intrusos: {e}")

@router.get("/incidents")
def get_incidents_report(limit: int = 50):
    """Reporte de incidencias de transgresión (estudiante en curso diferente)"""
    if not db_manager.db:
        return []
    try:
        docs = db_manager.db.collection("Eventos").where("tipo_evento", "==", "CURSO_DIFERENTE").limit(limit).get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en reporte de incidencias: {e}")

@router.get("/statistics/by-course")
def get_stats_by_course():
    """Estadísticas comparativas de asistencia e incidencias por curso"""
    if not db_manager.db:
        return {}
    try:
        eventos = db_manager.db.collection("Eventos").get()
        stats: Dict[str, dict] = {}
        
        for doc in eventos:
            data = doc.to_dict()
            curso = data.get("curso_detectado") or data.get("camara_curso") or "General"
            tipo = data.get("tipo_evento")
            
            if curso not in stats:
                stats[curso] = {"presentes": 0, "incidencias": 0, "entradas": 0}
                
            if tipo == "PRESENCIA" or tipo == "PRESENCIA_NORMAL":
                stats[curso]["presentes"] += 1
            elif tipo == "CURSO_DIFERENTE":
                stats[curso]["incidencias"] += 1
            elif tipo == "ENTRADA":
                stats[curso]["entradas"] += 1

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en estadísticas por curso: {e}")

@router.get("/statistics/trends")
def get_stats_trends():
    """Tendencias temporales de actividad"""
    if not db_manager.db:
        return []
    try:
        eventos = db_manager.db.collection("Eventos").get()
        trends: Dict[str, int] = {}
        for doc in eventos:
            data = doc.to_dict()
            fecha_str = data.get("fecha_hora", "")[:10]  # AAAA-MM-DD
            if fecha_str:
                trends[fecha_str] = trends.get(fecha_str, 0) + 1
        return [{"fecha": k, "total_eventos": v} for k, v in sorted(trends.items())]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en tendencias temporales: {e}")

@router.get("/audit")
def get_audit_logs(limit: int = 50):
    """Logs de auditoría de acciones administrativas"""
    if not db_manager.db:
        return []
    try:
        docs = db_manager.db.collection("AuditLogs").order_by("timestamp", direction="DESCENDING").limit(limit).get()
        return [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo logs de auditoría: {e}")
