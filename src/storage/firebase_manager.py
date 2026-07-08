# src/storage/firebase_manager.py
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import SERVER_TIMESTAMP, GeoPoint
from datetime import datetime
import logging

class FirebaseManager:
    def __init__(self, cred_path="credenciales.json"):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            logging.info("Conexión a Firebase Firestore exitosa.")
        except Exception as e:
            logging.error(f"Error al conectar con Firebase: {e}")
            self.db = None

    def iniciar_sesion_camara(self, camara_info):
        """Crea el documento principal de la cámara y retorna su ID."""
        if not self.db:
            return None

        # Obtenemos las coordenadas (si no existen en config.py, usa 0.0 por defecto)
        lat = camara_info.get("lat", 0.0)
        lon = camara_info.get("lon", 0.0)

        data = {
            "camara_nombre": camara_info.get("nombre", "Camara Desconocida"),
            "curso_asignado": camara_info.get("curso_asignado", "General"),
            "hora_inicio": SERVER_TIMESTAMP,
            "estado": "ACTIVA",
            "conteos": {"conocidos": 0, "intrusos": 0, "desconocidos": 0},
            "ubicacion": GeoPoint(lat, lon)
        }
        try:
            # Crea un documento en la colección principal "SesionesCamara"
            doc_ref = self.db.collection("SesionesCamara").document()
            doc_ref.set(data)
            logging.info(f"Sesión de cámara iniciada. ID: {doc_ref.id}")
            return doc_ref.id
        except Exception as e:
            logging.error(f"Error al iniciar sesión de cámara: {e}")
            return None

    def registrar_deteccion(self, session_id, identidad, estado, confianza, camara_info):
        """Guarda un registro dentro de la subcolección 'Detecciones' de la cámara activa."""
        if not self.db or not session_id:
            return

        ahora = datetime.now()
        data = {
            "identidad": identidad,
            "estado": estado,  # "PRESENTE", "INTRUSO", "DESCONOCIDO"
            "confianza": confianza,
            "fecha": ahora.strftime("%Y-%m-%d"),
            "hora": ahora.strftime("%H:%M:%S"),
            "curso_asignado_camara": camara_info.get("curso_asignado", "General"),
            "timestamp": SERVER_TIMESTAMP,
        }

        try:
            # Crea el documento en la subcolección Detecciones dentro del ID de la sesión
            self.db.collection("SesionesCamara").document(session_id).collection("Detecciones").add(data)
            logging.info(f"Registro guardado en subcolección: {identidad} - {estado}")
        except Exception as e:
            logging.error(f"Error al guardar detección en subcolección: {e}")

    def cerrar_sesion_camara(self, session_id, conteos, avg_fps=0.0):
        """Actualiza el documento principal de la cámara con los totales al cerrarse."""
        if not self.db or not session_id:
            return

        try:
            self.db.collection("SesionesCamara").document(session_id).update(
                {
                    "hora_fin": SERVER_TIMESTAMP,
                    "estado": "FINALIZADA",
                    "conteos": conteos,
                    "fps_promedio_sesion": round(avg_fps, 2),
                }
            )
            logging.info(f"Sesión de cámara {session_id} cerrada y guardada en BD.")
        except Exception as e:
            logging.error(f"Error al cerrar sesión de cámara: {e}")