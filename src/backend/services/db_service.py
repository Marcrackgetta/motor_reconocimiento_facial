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
        if not identity or identity in ["Desconocido", "Calculando..."]:
            return identity, "Desconocido"

        partes = identity.split("_")
        if len(partes) >= 2:
            nombre_limpio = " ".join(partes[-2:])
            curso = " ".join(partes[:-2]) if len(partes) > 2 else "Desconocido"
            return nombre_limpio, curso

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

    def iniciar_sesion_camara(self, camara_info, known_names=None):
        if not self.db:
            return None

        lat = camara_info.get("lat", 0.0)
        lon = camara_info.get("lon", 0.0)
        curso_actual = camara_info.get("curso_asignado", "General")
        curso_id = curso_actual.strip().replace(" ", "_")

        root_data = {
            "curso_asignado": curso_actual,
            "estado": "ACTIVA",
            "ubicacion": GeoPoint(lat, lon),
        }

        try:
            doc_ref = self.db.collection("SesionesCamara").document(curso_id)
            doc_ref.set(root_data)

            ahora = datetime.now()
            sub_doc_id = ahora.strftime("%Y-%m-%d_%H-%M-%S")
            hora_inicio_cambio = ahora.strftime("%H:%M:%S")

            self.active_sessions[curso_id] = {
                "sub_doc_id": sub_doc_id,
                "hora_inicio": hora_inicio_cambio,
                "documento_creado": False,
            }

            logging.info(
                f"Cámara activa. El documento [{sub_doc_id}] se creará en BD al primer escaneo."
            )
            return doc_ref.id

        except Exception as e:
            logging.error(f"Error al arrancar sesión principal de cámara: {e}")
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

        # Procesar evento de la Fase 1.5
        nuevo_evento = None
        try:
            nuevo_evento = self._procesar_evento_estudiante(identidad, estado, camara_info)
        except Exception as e:
            logging.error(f"Error procesando evento 1.5: {e}")

        session_data = self.active_sessions.get(session_id)
        if not session_data:
            ahora = datetime.now()
            session_data = {
                "sub_doc_id": ahora.strftime("%Y-%m-%d_%H-%M-%S"),
                "hora_inicio": ahora.strftime("%H:%M:%S"),
                "documento_creado": False,
            }
            self.active_sessions[session_id] = session_data

        sub_doc_id = session_data["sub_doc_id"]
        doc_ref = (
            self.db.collection("SesionesCamara")
            .document(session_id)
            .collection("RegistroDiario")
            .document(sub_doc_id)
        )

        try:
            doc = doc_ref.get()
            curso_actual = camara_info.get("curso_asignado", "General")

            if doc.exists:
                data = doc.to_dict()
            else:
                alumnos_esperados = []
                if known_names:
                    for name in known_names:
                        if name != "Desconocido" and self._es_del_curso(
                            name, curso_actual
                        ):
                            nombre_limpio, _ = self._parse_identity(name)
                            alumnos_esperados.append(nombre_limpio)

                data = {
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "hora_inicio": session_data["hora_inicio"],
                    "hora_fin": "",
                    "curso": curso_actual,
                    "total_presentes": 0,
                    "lista_presentes": [],
                    "total_ausentes": len(alumnos_esperados),
                    "lista_ausentes": alumnos_esperados,
                    "total_intrusos": 0,
                    "lista_intrusos": [],
                    "total_desconocidos": 0,
                }
                session_data["documento_creado"] = True

            actualizado = False
            nombre_limpio, curso_limpio = self._parse_identity(identidad)

            if estado == "PRESENTE":
                if nombre_limpio not in data["lista_presentes"]:
                    data["lista_presentes"].append(nombre_limpio)
                    data["total_presentes"] = len(data["lista_presentes"])
                    actualizado = True

                if nombre_limpio in data["lista_ausentes"]:
                    data["lista_ausentes"].remove(nombre_limpio)
                    data["total_ausentes"] = len(data["lista_ausentes"])
                    actualizado = True

            elif estado == "INTRUSO":
                ya_registrado = any(
                    i.get("nombre") == nombre_limpio for i in data["lista_intrusos"]
                )
                if not ya_registrado:
                    intruso_info = {
                        "nombre": nombre_limpio,
                        "curso_esperado": curso_limpio,
                        "hora_primera_deteccion": datetime.now().strftime("%H:%M:%S"),
                        "duracion_segundos": 0.0,
                    }
                    data["lista_intrusos"].append(intruso_info)
                    data["total_intrusos"] = len(data["lista_intrusos"])
                    actualizado = True

            elif estado == "DESCONOCIDO":
                data["total_desconocidos"] = data.get("total_desconocidos", 0) + 1
                actualizado = True

            if actualizado or not doc.exists:
                doc_ref.set(data)
                return {"id": sub_doc_id, "data": data, "nuevo_evento": nuevo_evento}

            return {"id": sub_doc_id, "data": data, "nuevo_evento": nuevo_evento} if nuevo_evento else None

        except Exception as e:
            logging.error(f"Error al inyectar detección en asistencia: {e}")
            return None

    def _procesar_evento_estudiante(self, identidad, estado, camara_info):
        nombre_limpio, curso_limpio = self._parse_identity(identidad)
        if nombre_limpio == "Desconocido":
            # Guardamos un evento genérico de intruso sin asociar a estudiante
            if estado == "DESCONOCIDO":
                return
            # Si es intruso puro, se maneja abajo o en RegistroDiario
            return
            
        estudiante_id = f"{curso_limpio}_{nombre_limpio}".replace(" ", "_")
        estudiante_ref = self.db.collection("Estudiantes").document(estudiante_id)
        
        doc = estudiante_ref.get()
        if not doc.exists:
            estudiante_ref.set({
                "nombre": nombre_limpio,
                "curso_origen": curso_limpio,
                "estado_actual": "DESCONOCIDO",
                "representantes": ["representante@prueba.com"],
                "ultimo_evento_id": None
            })
            est_data = {"estado_actual": "DESCONOCIDO", "curso_origen": curso_limpio}
        else:
            est_data = doc.to_dict()
            
        tipo_camara = camara_info.get("tipo", "AULA")
        curso_actual = camara_info.get("curso_asignado", "General")
        
        nuevo_estado = est_data.get("estado_actual")
        tipo_evento = None
        
        if tipo_camara == "ENTRADA":
            if nuevo_estado != "DENTRO_DE_LA_INSTITUCION":
                tipo_evento = "ENTRADA"
                nuevo_estado = "DENTRO_DE_LA_INSTITUCION"
        elif tipo_camara == "SALIDA":
            if nuevo_estado != "FUERA_DE_LA_INSTITUCION":
                tipo_evento = "SALIDA"
                nuevo_estado = "FUERA_DE_LA_INSTITUCION"
        else:
            if estado == "PRESENTE":
                if nuevo_estado != "PRESENCIA_NORMAL":
                    tipo_evento = "PRESENCIA_NORMAL"
                    nuevo_estado = "PRESENCIA_NORMAL"
            elif estado == "INTRUSO":
                if nuevo_estado != "CURSO_DIFERENTE":
                    tipo_evento = "CURSO_DIFERENTE"
                    nuevo_estado = "CURSO_DIFERENTE"
                    
        # Actualizamos la última detección independientemente de si hay un evento nuevo
        estudiante_ref.update({
            "ultima_deteccion": datetime.now().isoformat(),
            "curso_detectado": curso_actual
        })

        if tipo_evento:
            evento_ref = self.db.collection("Eventos").document()
            evento_dict = {
                "estudiante_id": estudiante_id,
                "tipo_evento": tipo_evento,
                "camara_curso": curso_actual,
                "fecha_hora": datetime.now().isoformat(),
                "alerta_enviada": False,
                "nombre": nombre_limpio,
                "curso_origen": curso_limpio
            }
            evento_ref.set(evento_dict)
            estudiante_ref.update({
                "estado_actual": nuevo_estado,
                "ultimo_evento_id": evento_ref.id
            })
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
        alertas_generadas = []
        if not self.db:
            return alertas_generadas
            
        try:
            # Obtener configuración global
            tiempo_limite = 600
            conf_doc = self.db.collection("Configuracion").document("global").get()
            if conf_doc.exists:
                tiempo_limite = conf_doc.to_dict().get("regla_10_minutos_segundos", 600)
                
            estudiantes = self.db.collection("Estudiantes").where("estado_actual", "==", "CURSO_DIFERENTE").get()
            
            for est_doc in estudiantes:
                est = est_doc.to_dict()
                evento_id = est.get("ultimo_evento_id")
                if not evento_id:
                    continue
                    
                evento_ref = self.db.collection("Eventos").document(evento_id)
                evento_doc = evento_ref.get()
                
                if evento_doc.exists:
                    evento = evento_doc.to_dict()
                    if not evento.get("alerta_enviada", False):
                        fecha_str = evento.get("fecha_hora")
                        if fecha_str:
                            fecha_evento = datetime.fromisoformat(fecha_str)
                            diferencia = datetime.now() - fecha_evento
                            # Uso del tiempo configurado
                            if diferencia.total_seconds() > tiempo_limite:
                                evento_ref.update({"alerta_enviada": True})
                                logging.info(f"ALERTA: Estudiante {est.get('nombre')} lleva más de {tiempo_limite} segundos fuera.")
                                alerta = {
                                    "estudiante_id": est_doc.id,
                                    "nombre": est.get('nombre'),
                                    "curso_origen": est.get('curso_origen'),
                                    "curso_detectado": est.get('curso_detectado'),
                                    "tiempo_fuera_segundos": diferencia.total_seconds()
                                }
                                alertas_generadas.append(alerta)
        except Exception as e:
            logging.error(f"Error evaluando regla de 10 minutos: {e}")
            
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
