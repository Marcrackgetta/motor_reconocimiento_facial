import logging
import os
from typing import Any

import firebase_admin
from firebase_admin import credentials, db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class FirebaseClient:
    """
    Cliente encargado de enviar los eventos del Motor Edge directo a Firebase Realtime Database.
    """
    def __init__(self, database_url: str = "https://motor-c7e0d-default-rtdb.firebaseio.com"):
        self.database_url = database_url
        self.is_connected = False
        
        # Inicializar Firebase Admin SDK asegurando que no se duplique
        if not firebase_admin._apps:
            cred_path = "serviceAccountKey.json"
            if not os.path.exists(cred_path):
                logging.error(f"[FIREBASE] ERROR CRÍTICO: No se encontró el archivo {cred_path}.")
                logging.info("Descarga tu clave privada desde Firebase y colócala en la raíz del motor.")
                return

            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self.database_url
                })
                self.is_connected = True
                logging.info("[FIREBASE] Conexión a Realtime Database establecida con éxito.")
            except Exception as e:
                logging.error(f"[FIREBASE] Error al inicializar: {e}")
        else:
            self.is_connected = True
            
        if self.is_connected:
            self.db_ref = db.reference('SesionesCamara')

    def send_event(self, event_data: dict[str, Any]) -> bool:
        if not self.is_connected:
            return False
            
        try:
            cam_id = event_data.get("camera_id", "CAM_DEFAULT")
            uuid = event_data.get("identity_uuid", "unknown")
            
            cam_ref = self.db_ref.child(cam_id)
            
            # 1. Mantener la cámara "Activa" para que el HTML la muestre en verde
            cam_ref.update({
                "activo": True,
                "estado": "activa",
                "camara_nombre": f"{cam_id}"
            })
            
            # 2. Estructurar los datos exactamente como los lee el HTML
            es_registrado = uuid not in ["unknown", "Desconocido", "Calculando..."]
            
            registro = {
                "timestamp": event_data.get("timestamp"),
                "bloque_horario": event_data.get("block")
            }
            
            if es_registrado:
                registro["total_presentes"] = 1
                registro["total_desconocidos"] = 0
                registro["lista_presentes"] = {
                    uuid: {"id": uuid, "nombre": uuid, "registrado": True}
                }
            else:
                registro["total_presentes"] = 0
                registro["total_desconocidos"] = 1
                registro["lista_intrusos"] = {
                    "intr_temp": {"id": "desconocido", "nombre": "Rostro No Reconocido", "registrado": False}
                }
            
            # El método push() genera un ID único automático en Firebase
            cam_ref.child("RegistroDiario").push(registro)
            logging.info(f"[FIREBASE] Evento de {uuid} guardado en {cam_id}")
            return True
            
        except Exception as e:
            logging.error(f"[FIREBASE] Error al escribir en base de datos: {e}")
            return False