# src/storage/firebase_manager.py
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import GeoPoint
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

        # Memoria temporal para rastrear el ID y estado de creación de cada sesión activa
        self.active_sessions = {}

    def _es_del_curso(self, identity, curso_actual):
        """Valida si un cadete pertenece al curso de la cámara activa"""
        curso_actual_norm = curso_actual.lower().replace("_", " ").strip()
        ident_norm = identity.lower().replace("_", " ").strip()

        if curso_actual_norm == "" or curso_actual_norm in ident_norm:
            return True

        partes = identity.rsplit("_", 1)
        if len(partes) == 2:
            curso_reg_norm = partes[0].lower().replace("_", " ").strip()
            if curso_reg_norm and (
                curso_reg_norm in curso_actual_norm
                or curso_actual_norm in curso_reg_norm
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

        # Registro principal: La cámara se marca como ACTIVA
        root_data = {
            "camara_nombre": camara_info.get("nombre", "Camara Desconocida"),
            "curso_asignado": curso_actual,
            "estado": "ACTIVA",
            "ubicacion": GeoPoint(lat, lon),
        }

        try:
            doc_ref = self.db.collection("SesionesCamara").document(curso_id)
            doc_ref.set(root_data)

            # Generación del ID único (Día y Hora) y guardado en memoria (Creación Diferida)
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

        # Recuperar datos de la sesión actual desde la memoria
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
                # ¡AQUÍ SE CREA EL DOCUMENTO FÍSICO! (Solo al escanear a la primera persona)
                alumnos_esperados = []
                if known_names:
                    for name in known_names:
                        if name != "Desconocido" and self._es_del_curso(
                            name, curso_actual
                        ):
                            alumnos_esperados.append(name)

                data = {
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "hora_inicio": session_data["hora_inicio"],
                    "hora_fin": "",
                    "curso_asignado_camara": curso_actual,
                    "total_presentes": 0,
                    "lista_presentes": [],
                    "total_ausentes": len(alumnos_esperados),
                    "lista_ausentes": alumnos_esperados,
                    "total_intrusos": 0,
                    "lista_intrusos": [],
                    "total_desconocidos": 0,
                }
                session_data["documento_creado"] = True
                logging.info(
                    f"Primer escaneo detectado. Creando documento de sesión: {sub_doc_id}"
                )

            actualizado = False

            if estado == "PRESENTE":
                if identidad not in data["lista_presentes"]:
                    data["lista_presentes"].append(identidad)
                    data["total_presentes"] = len(data["lista_presentes"])
                    actualizado = True

                if identidad in data["lista_ausentes"]:
                    data["lista_ausentes"].remove(identidad)
                    data["total_ausentes"] = len(data["lista_ausentes"])
                    actualizado = True

            elif estado == "INTRUSO":
                partes = identidad.rsplit("_", 1)
                curso_origen = partes[0] if len(partes) == 2 else "Desconocido"
                nombre_intruso = partes[1] if len(partes) == 2 else identidad

                ya_registrado = any(
                    i.get("identidad") == identidad for i in data["lista_intrusos"]
                )
                if not ya_registrado:
                    intruso_info = {
                        "identidad": identidad,
                        "nombre": nombre_intruso,
                        "curso_esperado": curso_origen,
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
                logging.info(
                    f"Subcolección [{sub_doc_id}] actualizada con identidad: {identidad} ({estado})"
                )

            return sub_doc_id

        except Exception as e:
            logging.error(f"Error al inyectar detección en asistencia: {e}")
            return None

    def actualizar_duracion_intruso(self, session_id, doc_id, duracion, identidad=None):
        if not self.db or not session_id or not doc_id or not identidad:
            return
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

                for idx, intruso in enumerate(intrusos):
                    if intruso.get("identidad") == identidad:
                        duracion_actual = intruso.get("duracion_segundos", 0.0)
                        intrusos[idx]["duracion_segundos"] = duracion_actual + duracion
                        modificado = True
                        break

                    if modificado:
                        doc_ref.update({"lista_intrusos": intrusos})
                        logging.info(
                            f"Permanencia de intruso recalculada: {duracion}s añadidos a {identidad}."
                        )
        except Exception as e:
            logging.error(f"Error al modificar permanencia de intruso: {e}")

    def cerrar_sesion_camara(self, session_id, avg_fps=0.0):
        if not self.db or not session_id:
            return
        try:
            # Finalizar estado en raíz
            self.db.collection("SesionesCamara").document(session_id).update(
                {
                    "estado": "APAGADA",
                }
            )

            # Modificar hora_fin únicamente si el documento fue creado (si alguien fue escaneado)
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
            else:
                logging.info(
                    f"Sesión [{session_id}] cerrada sin escaneos. No se generó documento vacío en BD."
                )

        except Exception as e:
            logging.error(f"Error al registrar conclusión de transmisión: {e}")
