import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import GeoPoint
from datetime import datetime
import logging

class DatabaseManager:
    def __init__(self, cred_path="credenciales.json"):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            logging.info("Conexión a Firebase Firestore exitosa (Backend).")
        except Exception as e:
            logging.error(f"Error al conectar con Firebase: {e}")
            self.db = None

        # Memoria temporal para rastrear el ID y estado de creación de cada sesión activa
        self.active_sessions = {}

    def get_user_role(self, email: str) -> str:
        """Obtiene el rol del usuario desde Firestore"""
        if not self.db:
            return "Desconocido"
        try:
            users_ref = self.db.collection("usuarios").where("correo", "==", email).get()
            if users_ref:
                return users_ref[0].to_dict().get("rol", "Desconocido")
            return "Desconocido"
        except Exception as e:
            logging.error(f"Error al obtener rol: {e}")
            return "Desconocido"

    def get_cameras(self) -> list:
        if not self.db:
            return []
        try:
            docs = self.db.collection("SesionesCamara").get()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logging.error(f"Error obteniendo cámaras: {e}")
            return []

    def get_students_for_representative(self, email: str) -> list:
        if not self.db:
            return []
        try:
            docs = self.db.collection("Estudiantes").where("representantes", "array_contains", email).get()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logging.error(f"Error obteniendo estudiantes para representante: {e}")
            return []

    def forzar_reseteo_camaras(self, camera_sources):
        """Limpia estados 'zombie' forzando todas las cámaras a APAGADA al inicio."""
        if not self.db:
            return

        for cam in camera_sources:
            lat = cam.get("lat", 0.0)
            lon = cam.get("lon", 0.0)
            curso_actual = cam.get("curso_asignado", "General")
            curso_id = curso_actual.strip().replace(" ", "_")

            try:
                self.db.collection("SesionesCamara").document(curso_id).set(
                    {
                        "curso_asignado": curso_actual,
                        "estado": "APAGADA",
                        "ubicacion": GeoPoint(lat, lon),
                    },
                    merge=True,
                )
                logging.info(
                    f"Estado limpiado a APAGADA para la cámara del curso: {curso_id}"
                )
            except Exception as e:
                logging.error(f"Error al resetear estado de cámara {curso_id}: {e}")

    def _parse_identity(self, identity):
        """
        Parsea la identidad recibida eliminando la concatenación con el curso.
        Retorna (nombre_limpio, curso_origen_limpio)
        Ejemplo: "3_CC_A_Mat_Edward_Jaime" -> ("Edward Jaime", "3_CC_A_Mat")
        """
        if not identity or identity in ["Desconocido", "Calculando..."]:
            return "Desconocido", "Desconocido"

        partes = identity.split("_")
        if len(partes) >= 2:
            nombre_limpio = " ".join(partes[-2:])
            curso_origen = "_".join(partes[:-2]) if len(partes) > 2 else "Desconocido"
            return nombre_limpio, curso_origen

        return identity, "Desconocido"

    def _es_del_curso(self, identity, curso_actual):
        curso_actual_norm = curso_actual.lower().replace("_", " ").strip()
        ident_norm = identity.lower().replace("_", " ").strip()

        if curso_actual_norm == "" or curso_actual_norm in ident_norm:
            return True

        _, curso_reg = self._parse_identity(identity)
        curso_reg_norm = curso_reg.lower().replace("_", " ").strip()

        if curso_reg_norm and (
            curso_reg_norm in curso_actual_norm or curso_actual_norm in curso_reg_norm
        ):
            return True

        return False

    def _procesar_evento_estudiante(self, identidad, estado, camara_info):
        from src.backend.services.event_processor import event_processor, RecognitionResult

        rec = RecognitionResult(
            session_id="session",
            track_id=1,
            identity_raw=identidad,
            confidence=95.0,
            camera_id=camara_info.get("curso_asignado", "General"),
            detected_course_id=camara_info.get("curso_asignado", "General"),
            camera_type=camara_info.get("tipo", "AULA")
        )
        event, alert = event_processor.process_recognition(rec)

        if event:
            evento_dict = event.model_dump()
            evento_dict["nombre"] = event.student_name
            evento_dict["curso_origen"] = event.origin_course_id
            evento_dict["curso_detectado"] = event.detected_course_id
            evento_dict["camara_curso"] = event.detected_course_id
            evento_dict["tipo_evento"] = event.type
            evento_dict["fecha_hora"] = event.timestamp
            evento_dict["alerta_enviada"] = event.alert_sent

            if self.db:
                try:
                    evento_ref = self.db.collection("Eventos").document()
                    evento_dict["id"] = evento_ref.id
                    evento_ref.set(evento_dict)

                    if event.student_id:
                        estudiante_ref = self.db.collection("Estudiantes").document(event.student_id)
                        doc = estudiante_ref.get()
                        if not doc.exists:
                            estudiante_ref.set({
                                "id": event.student_id,
                                "nombre": event.student_name,
                                "curso_origen": event.origin_course_id,
                                "estado_actual": event.type,
                                "representantes": ["representante@prueba.com"],
                                "ultimo_evento_id": evento_ref.id
                            })
                        else:
                            estudiante_ref.update({
                                "estado_actual": event.type,
                                "ultima_deteccion": datetime.now().isoformat(),
                                "curso_detectado": event.detected_course_id,
                                "ultimo_evento_id": evento_ref.id
                            })
                except Exception as e:
                    logging.error(f"Error al guardar evento en Firestore: {e}")

            return evento_dict

        return None

    def actualizar_duracion_intruso(self, session_id, doc_id, duracion, identidad=None):
        if not self.db or not session_id or not doc_id or not identidad:
            return None
        try:
            doc_ref = (
                self.db.collection("SesionesCamara")
                .document(session_id)
                .collection("RegistroDiario")
                .document(doc_id)
            )
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                intrusos = data.get("lista_intrusos", [])
                modificado = False
                nombre_limpio, _ = self._parse_identity(identidad)

                for idx, intruso in enumerate(intrusos):
                    if intruso.get("nombre") == nombre_limpio:
                        duracion_actual = intruso.get("duracion_segundos", 0.0)
                        intrusos[idx]["duracion_segundos"] = duracion_actual + duracion
                        modificado = True
                        break

                if modificado:
                    doc_ref.update({"lista_intrusos": intrusos})
                    return {"id": doc_id, "data": data}
        except Exception as e:
            logging.error(f"Error al modificar permanencia de intruso: {e}")
        return None

    def verificar_regla_10_minutos(self):
        from src.backend.services.event_processor import event_processor
        alertas_generadas = []
        alerts = event_processor.evaluate_pending_incidents()
        
        for alert in alerts:
            alerta_dict = alert.model_dump()
            alertas_generadas.append(alerta_dict)
            if self.db:
                try:
                    self.db.collection("Alertas").document(alert.id).set(alerta_dict)
                except Exception as e:
                    logging.error(f"Error guardando alerta en Firestore: {e}")
            
        return alertas_generadas
        
    def cerrar_sesion_camara(self, session_id, avg_fps=0.0):
        if not self.db or not session_id:
            return
        try:
            self.db.collection("SesionesCamara").document(session_id).update(
                {
                    "estado": "APAGADA",
                }
            )

            session_data = self.active_sessions.get(session_id)
            if session_data and session_data.get("documento_creado"):
                sub_doc_id = session_data["sub_doc_id"]
                hora_cierre = datetime.now().strftime("%H:%M:%S")
                self.db.collection("SesionesCamara").document(session_id).collection(
                    "RegistroDiario"
                ).document(sub_doc_id).update({"hora_fin": hora_cierre})
                logging.info(
                    f"Sesión [{session_id}] cerrada. Hora de fin inyectada en [{sub_doc_id}]."
                )

        except Exception as e:
            logging.error(f"Error al registrar conclusión de transmisión: {e}")

db_manager = DatabaseManager()
