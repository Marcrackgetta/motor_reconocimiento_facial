import os
import sys
import logging
from datetime import datetime

# Añadir el directorio raíz al path de python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import firebase_admin
from firebase_admin import credentials, firestore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def init_firestore(cred_path="credenciales.json"):
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def run_migration():
    logging.info("Iniciando migración de Firestore hacia la arquitectura objetivo...")
    db = init_firestore()
    if not db:
        logging.error("No se pudo conectar a Firestore.")
        return

    # 1. MIGRAR USUARIOS (usuarios -> Usuarios)
    logging.info("--- Migrando Usuarios ---")
    try:
        usuarios_antiguos = db.collection("usuarios").get()
        for doc in usuarios_antiguos:
            data = doc.to_dict()
            user_id = doc.id
            db.collection("Usuarios").document(user_id).set(data, merge=True)
            logging.info(f"Usuario migrado: {user_id}")
    except Exception as e:
        logging.error(f"Error migrando usuarios: {e}")

    # 2. MIGRAR CÁMARAS (SesionesCamara -> Camaras)
    logging.info("--- Migrando Cámaras ---")
    camera_map = {}
    try:
        sesiones_camara = db.collection("SesionesCamara").get()
        for idx, doc in enumerate(sesiones_camara):
            data = doc.to_dict()
            curso = data.get("curso_asignado", doc.id)
            camera_id = f"CAM_{idx}"
            camera_map[doc.id] = camera_id
            camera_map[curso] = camera_id

            # Guardar datos limpios de la cámara (sin tipo ENTRADA/SALIDA ni listas de estudiantes)
            clean_cam_data = {
                "camera_id": camera_id,
                "src": idx,
                "curso_asignado": curso,
                "ubicacion": data.get("ubicacion"),
                "estado": data.get("estado", "APAGADA"),
                "activa": data.get("estado") == "ACTIVA",
                "ultima_conexion": datetime.now().isoformat()
            }
            db.collection("Camaras").document(camera_id).set(clean_cam_data, merge=True)
            logging.info(f"Cámara migrada: {camera_id} para curso {curso}")

            # Migrar RegistroDiario (Telemetría -> Camaras/{id}/RegistroDiario, Asistencia -> Cursos/{curso}/InformeDiario)
            registros = db.collection("SesionesCamara").document(doc.id).collection("RegistroDiario").get()
            for reg in registros:
                reg_data = reg.to_dict()
                session_id = reg.id
                fecha = reg_data.get("fecha", session_id.split("_")[0] if "_" in session_id else datetime.now().strftime("%Y-%m-%d"))

                # Telemetría técnica para la cámara
                telemetria = {
                    "session_id": session_id,
                    "fecha": fecha,
                    "hora_inicio": reg_data.get("hora_inicio", ""),
                    "hora_fin": reg_data.get("hora_fin", ""),
                    "estado_final": "COMPLETADA" if reg_data.get("hora_fin") else "EN_CURSO"
                }
                db.collection("Camaras").document(camera_id).collection("RegistroDiario").document(session_id).set(telemetria, merge=True)

                # Informe Diario para el Curso
                curso_id = curso.strip().replace(" ", "_")
                informe = {
                    "fecha": fecha,
                    "hora_inicio": reg_data.get("hora_inicio", ""),
                    "hora_fin": reg_data.get("hora_fin", ""),
                    "curso": curso,
                    "total_presentes": reg_data.get("total_presentes", 0),
                    "lista_presentes": reg_data.get("lista_presentes", []),
                    "total_ausentes": reg_data.get("total_ausentes", 0),
                    "lista_ausentes": reg_data.get("lista_ausentes", []),
                    "total_intrusos": reg_data.get("total_intrusos", 0),
                    "lista_intrusos": reg_data.get("lista_intrusos", []),
                    "total_desconocidos": reg_data.get("total_desconocidos", 0)
                }
                db.collection("Cursos").document(curso_id).collection("InformeDiario").document(fecha).set(informe, merge=True)
                # Asegurar que el documento del curso exista
                db.collection("Cursos").document(curso_id).set({
                    "curso_id": curso_id,
                    "nombre": curso,
                    "activo": True
                }, merge=True)
                logging.info(f"RegistroDiario migrado a Cursos/{curso_id}/InformeDiario/{fecha}")

    except Exception as e:
        logging.error(f"Error migrando cámaras y registros diarios: {e}")

    # 3. MIGRAR ESTUDIANTES (Estudiantes -> Cursos/{curso}/Estudiantes)
    logging.info("--- Migrando Estudiantes ---")
    try:
        estudiantes = db.collection("Estudiantes").get()
        for doc in estudiantes:
            data = doc.to_dict()
            student_id = doc.id
            curso_origen = data.get("curso_origen", "General")
            curso_id = curso_origen.strip().replace(" ", "_")

            # Garantizar campos requeridos
            clean_estudiante = {
                "id": student_id,
                "nombre": data.get("nombre", student_id),
                "curso_origen": curso_origen,
                "estado_actual": data.get("estado_actual", "DESCONOCIDO"),
                "representantes": data.get("representantes", ["representante@prueba.com"]),
                "ultima_deteccion": data.get("ultima_deteccion", ""),
                "ultimo_evento_id": data.get("ultimo_evento_id")
            }

            db.collection("Cursos").document(curso_id).collection("Estudiantes").document(student_id).set(clean_estudiante, merge=True)
            db.collection("Cursos").document(curso_id).set({
                "curso_id": curso_id,
                "nombre": curso_origen,
                "activo": True
            }, merge=True)
            logging.info(f"Estudiante {student_id} migrado a Cursos/{curso_id}/Estudiantes")
    except Exception as e:
        logging.error(f"Error migrando estudiantes: {e}")

    # 4. MIGRAR EVENTOS (Eventos -> Cursos/{curso}/Eventos)
    logging.info("--- Migrando Eventos ---")
    try:
        eventos = db.collection("Eventos").get()
        for doc in eventos:
            data = doc.to_dict()
            event_id = doc.id
            curso_origen = data.get("curso_origen") or data.get("camara_curso") or "General"
            curso_id = curso_origen.strip().replace(" ", "_")

            clean_evento = {
                "event_id": event_id,
                "tipo_evento": data.get("tipo_evento", "DESCONOCIDO"),
                "estudiante_id": data.get("estudiante_id"),
                "nombre": data.get("nombre"),
                "curso_origen": curso_origen,
                "curso_detectado": data.get("curso_detectado") or data.get("camara_curso"),
                "fecha_hora": data.get("fecha_hora", datetime.now().isoformat()),
                "alerta_enviada": data.get("alerta_enviada", False)
            }

            db.collection("Cursos").document(curso_id).collection("Eventos").document(event_id).set(clean_evento, merge=True)
            logging.info(f"Evento {event_id} migrado a Cursos/{curso_id}/Eventos")
    except Exception as e:
        logging.error(f"Error migrando eventos: {e}")

    logging.info("¡Migración a la arquitectura objetivo completada exitosamente!")

if __name__ == "__main__":
    run_migration()
