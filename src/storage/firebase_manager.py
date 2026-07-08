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

        # El ID del documento será exclusivamente la fecha
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        doc_ref = (
            self.db.collection("SesionesCamara")
            .document(session_id)
            .collection("RegistroDiario")
            .document(fecha_hoy)
        )

        try:
            doc = doc_ref.get()
            curso_actual = camara_info.get("curso_asignado", "General")

            if doc.exists:
                data = doc.to_dict()
            else:
                # Inicializar documento. Se calculan los ausentes restando de todos los registrados.
                alumnos_esperados = []
                if known_names:
                    for name in known_names:
                        if name != "Desconocido" and self._es_del_curso(
                            name, curso_actual
                        ):
                            alumnos_esperados.append(name)

                data = {
                    "fecha": fecha_hoy,
                    "curso_asignado_camara": curso_actual,
                    "total_presentes": 0,
                    "lista_presentes": [],
                    "total_ausentes": len(alumnos_esperados),
                    "lista_ausentes": alumnos_esperados,
                    "total_intrusos": 0,
                    "lista_intrusos": [],
                }

            actualizado = False

            if estado == "PRESENTE":
                if identidad not in data["lista_presentes"]:
                    data["lista_presentes"].append(identidad)
                    data["total_presentes"] = len(data["lista_presentes"])
                    actualizado = True

                # Si llegó, ya no está ausente
                if identidad in data["lista_ausentes"]:
                    data["lista_ausentes"].remove(identidad)
                    data["total_ausentes"] = len(data["lista_ausentes"])
                    actualizado = True

            elif estado == "INTRUSO":
                # Extraer el curso del intruso asumiendo el formato Curso_Nombre
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

            if actualizado or not doc.exists:
                doc_ref.set(data)
                logging.info(
                    f"Registro diario [{fecha_hoy}] actualizado para identidad: {identidad}"
                )

            return fecha_hoy  # Retornamos la fecha para usarla como doc_id al actualizar la duración

        except Exception as e:
            logging.error(f"Error al actualizar asistencia diaria: {e}")
            return None

    def actualizar_duracion_intruso(self, session_id, doc_id, duracion, identidad=None):
        if not self.db or not session_id or not doc_id or not identidad:
            return
        try:
            # doc_id en este contexto corresponde a la fecha ("YYYY-MM-DD")
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

                # Buscar al intruso en la lista y actualizar su duración
                for idx, intruso in enumerate(intrusos):
                    if intruso.get("identidad") == identidad:
                        duracion_actual = intruso.get("duracion_segundos", 0.0)
                        intrusos[idx]["duracion_segundos"] = duracion_actual + duracion
                        modificado = True
                        break

                if modificado:
                    doc_ref.update({"lista_intrusos": intrusos})
                    logging.info(
                        f"Permanencia de intruso consolidada: {duracion}s sumados a {identidad}."
                    )
        except Exception as e:
            logging.error(f"Error al inyectar tiempo de permanencia: {e}")

    def actualizar_contadores(self, session_id, conteos):
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
