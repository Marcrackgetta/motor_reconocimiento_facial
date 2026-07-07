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

    def registrar_deteccion(self, identidad, estado, confianza, camara_info):
        """Guarda un registro individual de un estudiante/persona."""
        if not self.db:
            return

        ahora = datetime.now()
        data = {
            "identidad": identidad,
            "estado": estado,  # "PRESENTE", "CURSO INCORRECTO", "DESCONOCIDO"
            "confianza": confianza,
            "fecha": ahora.strftime("%Y-%m-%d"),
            "hora": ahora.strftime("%H:%M:%S"),
            "camara_nombre": camara_info.get("nombre"),
            "curso_asignado": camara_info.get("curso_asignado"),
            "ubicacion": GeoPoint(
                camara_info.get("lat", 0.0), camara_info.get("lon", 0.0)
            ),
            "timestamp": SERVER_TIMESTAMP,
        }

        try:
            # Crea un documento en la colección "Detecciones"
            self.db.collection("Detecciones").add(data)
            logging.info(f"Registro guardado en BD: {identidad} - {estado}")
        except Exception as e:
            logging.error(f"Error al guardar detección: {e}")

    def iniciar_sesion_camara(self, camara_info):
        """Crea el registro de la cámara al encenderse y retorna el ID del documento."""
        if not self.db:
            return None

        data = {
            "camara_nombre": camara_info.get("nombre"),
            "curso_asignado": camara_info.get("curso_asignado"),
            "hora_inicio": SERVER_TIMESTAMP,
            "estado": "ACTIVA",
            "conteos": {"conocidos": 0, "intrusos": 0, "desconocidos": 0},
        }
        try:
            doc_ref = self.db.collection("SesionesCamara").document()
            doc_ref.set(data)
            return doc_ref.id
        except Exception as e:
            logging.error(f"Error al iniciar sesión de cámara: {e}")
            return None

    def cerrar_sesion_camara(self, session_id, conteos, avg_fps):
        """Actualiza el registro de la cámara al apagarse con los totales finales."""
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
            logging.info("Sesión de cámara cerrada y guardada en BD.")
        except Exception as e:
            logging.error(f"Error al cerrar sesión de cámara: {e}")
