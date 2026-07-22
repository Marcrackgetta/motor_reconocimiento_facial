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

@router.get("/notifications/me")
def get_my_notifications(email: str):
    if not db_manager.db:
        return []
    
    notifications = []
    try:
        students = db_manager.get_students_for_representative(email)
        student_ids = [s["id"] for s in students if "id" in s]
        student_names = [s.get("nombre", "") for s in students]

        eventos = db_manager.db.collection("Eventos").get()
        for doc in eventos:
            data = doc.to_dict()
            s_id = data.get("student_id")
            s_name = data.get("nombre", "")
            
            if s_id in student_ids or s_name in student_names or data.get("tipo_evento") == "INTRUSO_EXTERNO":
                notifications.append({
                    "id": doc.id,
                    "student_id": s_id,
                    "nombre": data.get("nombre", "Persona Desconocida"),
                    "tipo_evento": data.get("tipo_evento", "EVENTO"),
                    "curso_origen": data.get("curso_origen", "Desconocido"),
                    "curso_detectado": data.get("curso_detectado", data.get("camara_curso", "General")),
                    "fecha_hora": data.get("fecha_hora", ""),
                    "alerta_enviada": data.get("alerta_enviada", False)
                })

        notifications.sort(key=lambda x: str(x.get('fecha_hora', '')), reverse=True)
        return notifications
    except Exception as e:
        logging.error(f"Error cargando notificaciones para {email}: {e}")
        return []
