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
            users_ref = self.db.collection("Usuarios").where("email", "==", email).get()
            if not users_ref:
                users_ref = self.db.collection("Usuarios").where("correo", "==", email).get()
            if not users_ref:
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
            docs = self.db.collection("Camaras").get()
            if not docs:
                docs = self.db.collection("SesionesCamara").get()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logging.error(f"Error obteniendo cámaras: {e}")
            return []

    def get_students_for_representative(self, email: str) -> list:
        if not self.db:
            return []
        if not hasattr(self.db, "collection_group"):
            try:
                docs = self.db.collection("Estudiantes").where("representantes", "array_contains", email).get()
                return [{"id": doc.id, **doc.to_dict()} for doc in docs]
            except Exception as e:
                logging.error(f"Error obteniendo estudiantes para representante en Mock: {e}")
                return []
        try:
            docs = self.db.collection_group("Estudiantes").where("representantes", "array_contains", email).get()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception:
            try:
                docs = self.db.collection("Estudiantes").where("representantes", "array_contains", email).get()
                if docs:
                    return [{"id": doc.id, **doc.to_dict()} for doc in docs]

                cursos = self.db.collection("Cursos").get()
                students = []
                for curso in cursos:
                    st_docs = self.db.collection("Cursos").document(curso.id).collection("Estudiantes").get()
                    for doc in st_docs:
                        d = doc.to_dict()
                        if email in d.get("representantes", []):
                            students.append({"id": doc.id, **d})
                return students
            except Exception as e:
                logging.error(f"Error obteniendo estudiantes para representante: {e}")
                return []

    def forzar_reseteo_camaras(self, camera_sources):
        """Limpia estados 'zombie' forzando todas las cámaras a APAGADA en la colección Camaras."""
        if not self.db:
            return

        for idx, cam in enumerate(camera_sources):
            lat = cam.get("lat", 0.0)
            lon = cam.get("lon", 0.0)
            curso_actual = cam.get("curso_asignado", "General")
            camera_id = cam.get("camera_id", f"CAM_{idx}")

            try:
                self.db.collection("Camaras").document(camera_id).set(
                    {
                        "camera_id": camera_id,
                        "src": cam.get("src", idx),
                        "curso_asignado": curso_actual,
                        "estado": "APAGADA",
                        "activa": False,
                        "ubicacion": GeoPoint(lat, lon),
                        "latitud": lat,
                        "longitud": lon,
                        "ultima_desconexion": datetime.now().isoformat()
                    },
                    merge=True,
                )
                logging.info(f"Estado limpiado a APAGADA para cámara [{camera_id}] ({curso_actual})")
            except Exception as e:
                logging.error(f"Error al resetear estado de cámara {camera_id}: {e}")

    def iniciar_sesion_camara(self, camara_info, known_names=None):
        if not self.db:
            return None

        lat = camara_info.get("lat", 0.0)
        lon = camara_info.get("lon", 0.0)
        curso_actual = camara_info.get("curso_asignado", "General")
        camera_id = camara_info.get("camera_id") or f"CAM_{camara_info.get('src', 0)}"

        cam_data = {
            "camera_id": camera_id,
            "src": camara_info.get("src", 0),
            "curso_asignado": curso_actual,
            "estado": "ACTIVA",
            "activa": True,
            "ubicacion": GeoPoint(lat, lon),
            "latitud": lat,
            "longitud": lon,
            "ultima_conexion": datetime.now().isoformat()
        }

        try:
            self.db.collection("Camaras").document(camera_id).set(cam_data, merge=True)

            ahora = datetime.now()
            sub_doc_id = ahora.strftime("%Y-%m-%d_%H-%M-%S")
            fecha_hoy = ahora.strftime("%Y-%m-%d")
            hora_inicio_cambio = ahora.strftime("%H:%M:%S")

            session_key = camera_id
            self.active_sessions[session_key] = {
                "camera_id": camera_id,
                "curso_asignado": curso_actual,
                "sub_doc_id": sub_doc_id,
                "fecha": fecha_hoy,
                "hora_inicio": hora_inicio_cambio,
                "documento_creado": False,
            }

            logging.info(
                f"Cámara [{camera_id}] activa para el curso [{curso_actual}]."
            )
            return camera_id

        except Exception as e:
            logging.error(f"Error al arrancar sesión de cámara: {e}")
            return None

    def registrar_deteccion(
        self,
        session_id,
        identidad,
        estado,
        confianza,
        camara_info,
        custom_doc_id=None,
        known_names=None,
    ):
        if not self.db or not session_id:
            return None

        curso_actual = camara_info.get("curso_asignado", "General")
        curso_id = curso_actual.strip().replace(" ", "_")

        # 1. Procesar evento de la arquitectura de dominio
        nuevo_evento = None
        try:
            nuevo_evento = self._procesar_evento_estudiante(identidad, estado, camara_info)
        except Exception as e:
            logging.error(f"Error procesando evento: {e}")

        # 2. Registrar en Cursos/{curso_id}/InformeDiario/{fecha}
        ahora = datetime.now()
        fecha_hoy = ahora.strftime("%Y-%m-%d")

        informe_ref = (
            self.db.collection("Cursos")
            .document(curso_id)
            .collection("InformeDiario")
            .document(fecha_hoy)
        )

        try:
            doc = informe_ref.get()
            if hasattr(doc, "exists") and doc.exists:
                data = doc.to_dict()
            else:
                alumnos_esperados = []
                if known_names:
                    for name in known_names:
                        if name != "Desconocido" and self._es_del_curso(name, curso_actual):
                            nombre_limpio, _ = self._parse_identity(name)
                            alumnos_esperados.append(nombre_limpio)

                data = {
                    "fecha": fecha_hoy,
                    "hora_inicio": ahora.strftime("%H:%M:%S"),
                    "hora_fin": "",
                    "curso": curso_actual,
                    "total_estudiantes": len(alumnos_esperados),
                    "total_presentes": 0,
                    "lista_presentes": [],
                    "total_ausentes": len(alumnos_esperados),
                    "lista_ausentes": alumnos_esperados,
                    "total_intrusos": 0,
                    "lista_intrusos": [],
                    "total_desconocidos": 0,
                }
                self.db.collection("Cursos").document(curso_id).set({
                    "curso_id": curso_id,
                    "nombre": curso_actual,
                    "activo": True
                }, merge=True)

            actualizado = False
            nombre_limpio, curso_limpio = self._parse_identity(identidad)

            if estado == "PRESENTE":
                if nombre_limpio not in data.get("lista_presentes", []):
                    data.setdefault("lista_presentes", []).append(nombre_limpio)
                    data["total_presentes"] = len(data["lista_presentes"])
                    actualizado = True

                if nombre_limpio in data.get("lista_ausentes", []):
                    data["lista_ausentes"].remove(nombre_limpio)
                    data["total_ausentes"] = len(data["lista_ausentes"])
                    actualizado = True

            elif estado == "INTRUSO":
                ya_registrado = any(
                    i.get("nombre") == nombre_limpio for i in data.get("lista_intrusos", [])
                )
                if not ya_registrado:
                    intruso_info = {
                        "nombre": nombre_limpio,
                        "curso_esperado": curso_limpio,
                        "hora_primera_deteccion": ahora.strftime("%H:%M:%S"),
                        "duracion_segundos": 0.0,
                    }
                    data.setdefault("lista_intrusos", []).append(intruso_info)
                    data["total_intrusos"] = len(data["lista_intrusos"])
                    actualizado = True

            elif estado == "DESCONOCIDO":
                data["total_desconocidos"] = data.get("total_desconocidos", 0) + 1
                actualizado = True

            if actualizado or not (hasattr(doc, "exists") and doc.exists):
                informe_ref.set(data)

            # 3. Telemetría técnica de la Cámara
            camera_id = session_id if session_id.startswith("CAM_") else f"CAM_{camara_info.get('src', 0)}"
            telemetria_ref = (
                self.db.collection("Camaras")
                .document(camera_id)
                .collection("RegistroDiario")
                .document(fecha_hoy)
            )
            telemetria_ref.set({
                "fecha": fecha_hoy,
                "ultima_deteccion": ahora.isoformat(),
                "camera_id": camera_id
            }, merge=True)

            return {"id": fecha_hoy, "data": data, "nuevo_evento": nuevo_evento}

        except Exception as e:
            logging.error(f"Error al registrar detección en Cursos: {e}")
            return None

    def _parse_identity(self, identity):
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

        curso_actual = camara_info.get("curso_asignado", "General")
        camera_id = camara_info.get("camera_id", f"CAM_{camara_info.get('src', 0)}")
        camera_type = str(camara_info.get("tipo") or camara_info.get("camera_type") or "MONITOREO").upper()
        rec = RecognitionResult(
            session_id="session",
            track_id=1,
            identity_raw=identidad,
            confidence=95.0,
            camera_id=camera_id,
            detected_course_id=curso_actual,
            camera_type=camera_type
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
                    curso_id = event.origin_course_id.strip().replace(" ", "_")
                    curso_doc = self.db.collection("Cursos").document(curso_id)
                    if hasattr(curso_doc, "collection"):
                        evento_ref = curso_doc.collection("Eventos").document()
                    else:
                        evento_ref = self.db.collection("Eventos").document()
                    evento_dict["id"] = evento_ref.id
                    evento_ref.set(evento_dict)

                    if event.student_id:
                        if hasattr(curso_doc, "collection"):
                            estudiante_ref = curso_doc.collection("Estudiantes").document(event.student_id)
                        else:
                            estudiante_ref = self.db.collection("Estudiantes").document(event.student_id)
                        doc = estudiante_ref.get()
                        if not (hasattr(doc, "exists") and doc.exists):
                            estudiante_ref.set({
                                "id": event.student_id,
                                "nombre": event.student_name,
                                "curso_origen": event.origin_course_id,
                                "estado_actual": event.type,
                                "representantes": ["representante@prueba.com"],
                                "ultimo_evento_id": evento_ref.id,
                                "ultima_deteccion": datetime.now().isoformat()
                            })
                        else:
                            estudiante_ref.update({
                                "estado_actual": event.type,
                                "ultima_deteccion": datetime.now().isoformat(),
                                "curso_detectado": event.detected_course_id,
                                "ultimo_evento_id": evento_ref.id
                            })
                except Exception as e:
                    logging.error(f"Error al guardar evento en Cursos: {e}")

            return evento_dict

        return None

    def actualizar_duracion_intruso(self, session_id, doc_id, duracion, identidad=None):
        if not self.db or not session_id or not doc_id or not identidad:
            return None
        try:
            ahora = datetime.now()
            fecha = doc_id if "-" in doc_id else ahora.strftime("%Y-%m-%d")
            curso_id = session_id.strip().replace(" ", "_")

            doc_ref = (
                self.db.collection("Cursos")
                .document(curso_id)
                .collection("InformeDiario")
                .document(fecha)
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
            camera_id = session_id if session_id.startswith("CAM_") else session_id
            self.db.collection("Camaras").document(camera_id).set(
                {
                    "estado": "APAGADA",
                    "activa": False,
                    "ultima_desconexion": datetime.now().isoformat()
                },
                merge=True
            )
            logging.info(f"Cámara [{camera_id}] marcada como APAGADA.")

        except Exception as e:
            logging.error(f"Error al registrar conclusión de transmisión: {e}")

db_manager = DatabaseManager()
