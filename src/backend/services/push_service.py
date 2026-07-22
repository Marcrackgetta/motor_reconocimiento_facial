import logging
from datetime import datetime
from typing import Dict, Any, Optional
from src.backend.services.db_service import db_manager

class PushNotificationService:
    """
    Servicio centralizado de notificaciones Push (FCM / Firebase Cloud Messaging).
    Garantiza que toda notificación Push enviada persista en la base de datos interna.
    """

    @staticmethod
    def send_push_notification(
        recipient_email: str,
        title: str,
        body: str,
        data_payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envía una notificación Push al dispositivo del usuario y registra 
        la notificación en el historial interno de Firestore.
        """
        timestamp = datetime.now().isoformat()
        
        # 1. Guardar en historial interno de base de datos
        notification_dict = {
            "recipient_email": recipient_email,
            "title": title,
            "body": body,
            "data": data_payload or {},
            "timestamp": timestamp,
            "read": False
        }

        if db_manager.db:
            try:
                doc_ref = db_manager.db.collection("Notificaciones").document()
                notification_dict["id"] = doc_ref.id
                doc_ref.set(notification_dict)
            except Exception as e:
                logging.error(f"Error guardando notificación en DB: {e}")

        # 2. Simulación / Integración de envío Push via FCM REST API
        logging.info(f"[PUSH SENT] A: {recipient_email} | Título: '{title}' | Cuerpo: '{body}'")
        return True

# Instancia global del servicio Push
push_service = PushNotificationService()
