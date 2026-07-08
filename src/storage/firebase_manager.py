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
        if not self.db:
            return None

        lat = camara_info.get("lat", 0.0)
        lon = camara_info.get("lon", 0.0)
        curso_id = (
            camara_info.get("curso_asignado", "General").strip().replace(" ", "_")
        )

        data = {
            "camara_nombre": camara_info.get("nombre", "Camara Desconocida"),
            "curso_asignado": camara_info.get("curso_asignado", "General"),
            "hora_inicio": SERVER_TIMESTAMP,
            "estado": "ACTIVA",
            "conteos": {"conocidos": 0, "intrusos": 0, "desconocidos": 0},
            "ubicacion": GeoPoint(lat, lon),
        }
        try:
            doc_ref = self.db.collection("SesionesCamara").document(curso_id)
            doc_ref.set(data)
            logging.info(f"Sesión establecida bajo ID de Curso: {doc_ref.id}")
            return doc_ref.id
        except Exception as e:
            logging.error(f"Error al iniciar sesión de curso con ID estático: {e}")
            return None

    def registrar_deteccion(
        self, session_id, identidad, estado, confianza, camara_info, custom_doc_id=None
    ):
        if not self.db or not session_id:
            return None

        ahora = datetime.now()
        data = {
            "identidad": identidad,
            "estado": estado,
            "confianza": confianza,
            "fecha": ahora.strftime("%Y-%m-%d"),
            "hora": ahora.strftime("%H:%M:%S"),
            "curso_asignado_camara": camara_info.get("curso_asignado", "General"),
            "timestamp": SERVER_TIMESTAMP,
            "duracion_permanencia_segundos": 0.0,
        }

        try:
            if custom_doc_id:
                # Limpiamos el ID por si tiene caracteres que a Firebase no le gustan
                safe_doc_id = custom_doc_id.replace("/", "_").replace(" ", "_")
                doc_ref = (
                    self.db.collection("SesionesCamara")
                    .document(session_id)
                    .collection("Detecciones")
                    .document(safe_doc_id)
                )
                doc_ref.set(data)
                logging.info(
                    f"Registro en subcolección con ID [{safe_doc_id}] guardado exitosamente."
                )
                return safe_doc_id
            else:
                _, doc_ref = (
                    self.db.collection("SesionesCamara")
                    .document(session_id)
                    .collection("Detecciones")
                    .add(data)
                )
                return doc_ref.id
        except Exception as e:
            logging.error(f"Error al añadir detección a subcolección: {e}")
            return None

    def actualizar_duracion_intruso(self, session_id, doc_id, duracion):
        if not self.db or not session_id or not doc_id:
            return
        try:
            self.db.collection("SesionesCamara").document(session_id).collection(
                "Detecciones"
            ).document(doc_id).update({"duracion_permanencia_segundos": duracion})
            logging.info(
                f"Permanencia de intruso finalizada: {duracion}s asignados al registro {doc_id}"
            )
        except Exception as e:
            logging.error(f"Error al inyectar tiempo de permanencia: {e}")

    def actualizar_contadores(self, session_id, conteos):
        """Sube el total del contador a la base de datos en tiempo real (ideal para los desconocidos)."""
        if not self.db or not session_id:
            return
        try:
            self.db.collection("SesionesCamara").document(session_id).update(
                {"conteos": conteos}
            )
        except Exception as e:
            logging.error(f"Error al actualizar contadores en vivo: {e}")

    def cerrar_sesion_camara(self, session_id, conteos, avg_fps=0.0):
        if not self.db or not session_id:
            return
        try:
            self.db.collection("SesionesCamara").document(session_id).update(
                {
                    "hora_fin": SERVER_TIMESTAMP,
                    "estado": "FINALIZADA",
                    "conteos": conteos,
                }
            )
            logging.info(
                f"Sesión del curso/cámara [{session_id}] concluida y consolidada."
            )
        except Exception as e:
            logging.error(f"Error al cerrar canal de curso: {e}")
