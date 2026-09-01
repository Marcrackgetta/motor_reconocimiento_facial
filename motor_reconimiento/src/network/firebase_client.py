import logging
import os
import threading
import time
from datetime import datetime
from typing import Any

import firebase_admin
from firebase_admin import credentials, db, messaging

# Configuración del sistema de registro de eventos (consola)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class FirebaseClient:
    """
    Gestiona Firebase RTDB y las notificaciones Push (Entrada, Salida y Faltas).
    Incluye rutina automática de faltas, actualización de estado de cámaras y 
    gestión de asistencia global por estudiante.
    """
    def __init__(self, database_url: str = "https://motor-c7e0d-default-rtdb.firebaseio.com"):
        self.database_url = database_url
        self.is_connected = False
        
        self.daily_notifications: dict[str, dict[str, dict[str, Any]]] = {}
        self.horas_minimas_para_salida = 4.0 
        
        self.horarios_entrada = {
            "MATUTINO": "07:00",
            "VESPERTINO": "13:00",
        }
        
        if not firebase_admin._apps:
            cred_path = "serviceAccountKey.json"
            if not os.path.exists(cred_path):
                logging.error(f"[FIREBASE] ERROR CRÍTICO: No se encontró el archivo {cred_path}.")
                return

            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self.database_url
                })
                self.is_connected = True
                logging.info("[FIREBASE] Conexión a Realtime Database y FCM establecida con éxito.")
            except Exception as e:
                logging.error(f"[FIREBASE] Error al inicializar: {e}")
        else:
            self.is_connected = True
            
        if self.is_connected:
            self.db_ref = db.reference('SesionesCamara')
            self.estudiantes_ref = db.reference('Estudiantes')
            self.usuarios_ref = db.reference('Usuarios')

    def iniciar_rutina_faltas_automatica(self, hora_check: str = "10:00"):
        def _rutina():
            logging.info(f"[SISTEMA] Reloj automático de faltas iniciado. Evaluación programada a las {hora_check}.")
            while True:
                ahora = datetime.now().strftime("%H:%M")
                if ahora == hora_check:
                    self.procesar_inasistencias()
                    time.sleep(61)
                time.sleep(30)
        
        hilo = threading.Thread(target=_rutina, daemon=True)
        hilo.start()

    def registrar_estudiante_en_curso(self, cedula: str, nombre: str, cam_id: str):
        """
        Asocia un nuevo estudiante al curso representado por la cámara y lo añade a la nómina oficial.
        """
        if not self.is_connected: 
            return
            
        try:
            # Importamos la configuración localmente para evitar dependencias circulares
            from src.utils.config import CAMERA_SOURCES
            
            # Identificamos el curso al que pertenece esta cámara
            curso = next((c.get("curso", "SIN_CURSO") for c in CAMERA_SOURCES if c.get("camera_id") == cam_id), "SIN_CURSO")
            
            # 1. Guardamos al estudiante en la nómina del curso (vinculado a la cámara)
            self.db_ref.child(cam_id).child("NominaCurso").child(cedula).set({
                "cedula": cedula,
                "nombre": nombre,
                "curso": curso,
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # 2. Guardamos la información en el nodo global de Estudiantes (Para futura vinculación con representantes)
            self.estudiantes_ref.child(cedula).update({
                "nombre": nombre,
                "curso": curso
            })
            logging.info(f"[SISTEMA] Estudiante {nombre} ({cedula}) añadido a la nómina de {curso}.")
            
        except Exception as e:
            logging.error(f"[FIREBASE] Error al registrar estudiante en el curso: {e}")

    def send_event(self, event_data: dict[str, Any], modo_operacion: str = "ENTRADA") -> bool:
        if not self.is_connected:
            return False
            
        try:
            if isinstance(event_data, str):
                uuid_raw = event_data
                cam_id = "CAM_001"
                timestamp_evento = time.time()
                bloque_horario = "MATUTINO"
            else:
                cam_id = event_data.get("camera_id", "CAM_DEFAULT")
                uuid_raw = event_data.get("identity_uuid", "unknown")
                timestamp_evento = event_data.get("timestamp", time.time())
                bloque_horario = event_data.get("block", "MATUTINO")
            
            # --- NUEVA LÓGICA DE IDENTIFICACIÓN: Separar Cédula y Nombre ---
            if isinstance(uuid_raw, str) and "--" in uuid_raw:
                cedula, nombre_estudiante = uuid_raw.split("--", 1)
            else:
                # Fallback por si detecta "unknown" o formatos antiguos
                cedula = uuid_raw if isinstance(uuid_raw, str) else "unknown"
                nombre_estudiante = cedula
                
            es_registrado = cedula not in ["unknown", "Desconocido", "Calculando..."]

            cam_ref = self.db_ref.child(cam_id)
            
            # Reafirmamos que la cámara está activa
            cam_ref.update({
                "activo": True,
                "estado": "activa",
                "status": "online"
            })
            
            hoy = datetime.fromtimestamp(timestamp_evento).strftime("%Y-%m-%d")
            hora_real = datetime.fromtimestamp(timestamp_evento).strftime("%H:%M:%S")
            
            # Referencia al documento de asistencia ÚNICO del día
            registro_diario_ref = cam_ref.child("RegistroDiario").child(hoy)
            
            if es_registrado:
                estudiante_data = self.estudiantes_ref.child(cedula).get()
                if estudiante_data:
                    # Preferimos el nombre almacenado en base de datos si existe
                    nombre_estudiante = estudiante_data.get('nombre', nombre_estudiante)
                    rep_uid = estudiante_data.get('representante_uid')
                    
                    if rep_uid:
                        self._evaluar_reglas_y_notificar(rep_uid, nombre_estudiante, cam_id, cedula, bloque_horario, timestamp_evento, modo_operacion)

                # --- NUEVA LÓGICA DE ROSTER: Agregar a la lista de presentes del día ---
                # Si estaba en la lista de ausentes (implementación futura), lo quitamos
                registro_diario_ref.child("lista_ausentes").child(cedula).delete()
                
                # Lo agregamos a los presentes. Al usar .set() con su cédula, no sobrescribe a los demás.
                registro_diario_ref.child("lista_presentes").child(cedula).set({
                    "id": cedula,
                    "nombre": nombre_estudiante,
                    "registrado": True,
                    "hora_deteccion": hora_real
                })
            else:
                nombre_estudiante = "Rostro No Reconocido"
                # Usamos el timestamp como ID único para que no se sobrescriban los diferentes intrusos
                intruder_key = str(int(timestamp_evento))
                registro_diario_ref.child("lista_intrusos").child(intruder_key).set({
                    "id": "desconocido",
                    "nombre": nombre_estudiante,
                    "registrado": False,
                    "hora_intento": hora_real
                })
            
            # Actualizamos meta-datos del día
            registro_diario_ref.update({
                "fecha": hoy,
                "ultimo_evento": timestamp_evento
            })

            logging.info(f"[FIREBASE] Evento de {modo_operacion} para {nombre_estudiante} ({cedula}) guardado en la asistencia diaria.")
            return True
            
        except Exception as e:
            logging.error(f"[FIREBASE] Error al escribir en base de datos: {e}")
            return False

    def _evaluar_reglas_y_notificar(self, rep_uid: str, nombre_estudiante: str, cam_id: str, uuid: str, bloque_horario: str, timestamp_evento: float, modo_operacion: str):
        hoy = datetime.fromtimestamp(timestamp_evento).strftime("%Y-%m-%d")
        
        if hoy not in self.daily_notifications:
            self.daily_notifications.clear()
            self.daily_notifications[hoy] = {}

        if uuid not in self.daily_notifications[hoy]:
            self.daily_notifications[hoy][uuid] = {}

        historial = self.daily_notifications[hoy][uuid]
        tipo_notificacion = None
        estado_entrada = None

        if modo_operacion == "ENTRADA":
            if "entrada" not in historial:
                historial["entrada"] = timestamp_evento
                
                if "falta" in historial:
                    historial.pop("falta")
                    logging.info(f"[SISTEMA] Falta anulada para {nombre_estudiante}. Actualizando a llegada con atraso.")
                
                jornada = bloque_horario.split("_")[-1] if "_" in bloque_horario else "MATUTINO"
                hora_esperada_str = self.horarios_entrada.get(jornada, "07:00")
                
                hora_esperada_dt = datetime.strptime(hora_esperada_str, "%H:%M").time()
                hora_real_dt = datetime.fromtimestamp(timestamp_evento).time()
                
                if hora_real_dt > hora_esperada_dt:
                    estado_entrada = "ATRASADO"
                else:
                    estado_entrada = "PUNTUAL"
                    
                tipo_notificacion = "ENTRADA"
                
        elif modo_operacion == "SALIDA":
            if "entrada" in historial and "salida" not in historial and "falta" not in historial:
                historial["salida"] = timestamp_evento
                tipo_notificacion = "SALIDA"

        if tipo_notificacion:
            self._disparar_push(rep_uid, nombre_estudiante, tipo_notificacion, timestamp_evento, estado_entrada)

    def procesar_inasistencias(self):
        if not self.is_connected:
            return
            
        logging.info("[SISTEMA] Evaluando inasistencias del día...")
        hoy = datetime.now().strftime("%Y-%m-%d")
        timestamp_actual = time.time()
        
        if hoy not in self.daily_notifications:
            self.daily_notifications[hoy] = {}

        try:
            todos_los_estudiantes = self.estudiantes_ref.get()
            if not todos_los_estudiantes:
                return

            for uuid, data in todos_los_estudiantes.items():
                rep_uid = data.get('representante_uid')
                nombre_estudiante = data.get('nombre', uuid)
                
                if uuid not in self.daily_notifications[hoy]:
                    self.daily_notifications[hoy][uuid] = {}
                
                historial = self.daily_notifications[hoy][uuid]
                
                if "entrada" not in historial and "falta" not in historial:
                    historial["falta"] = True
                    
                    if rep_uid:
                        self._disparar_push(rep_uid, nombre_estudiante, "FALTA", timestamp_actual)
                        
            logging.info("[SISTEMA] Procesamiento de inasistencias finalizado con éxito.")
        except Exception as e:
            logging.error(f"[SISTEMA] Error al procesar inasistencias: {e}")

    def _disparar_push(self, rep_uid: str, nombre_estudiante: str, tipo: str, timestamp_evento: float, estado_entrada: str = None):
        try:
            usuario_data = self.usuarios_ref.child(rep_uid).get()
            if not usuario_data:
                return
            
            fcm_token = usuario_data.get('fcm_token')
            hora_real = datetime.fromtimestamp(timestamp_evento).strftime("%H:%M")
            
            if fcm_token:
                if tipo == "ENTRADA":
                    if estado_entrada == "ATRASADO":
                        titulo = '⚠️ Ingreso con Atraso'
                        cuerpo = f'Su representado {nombre_estudiante} llegó atrasado a la institución a las {hora_real}.'
                    else:
                        titulo = '✅ Ingreso Confirmado'
                        cuerpo = f'Su representado {nombre_estudiante} llegó a la institución a las {hora_real}.'
                elif tipo == "SALIDA":
                    titulo = '👋 Salida de la Institución'
                    cuerpo = f'Su representado {nombre_estudiante} salió de la institución a las {hora_real}.'
                elif tipo == "FALTA":
                    titulo = '❌ Inasistencia Registrada'
                    cuerpo = f'Su representado {nombre_estudiante} no asistió a la institución el día de hoy.'

                mensaje = messaging.Message(
                    notification=messaging.Notification(title=titulo, body=cuerpo),
                    token=fcm_token,
                )
                response = messaging.send(mensaje)
                logging.info(f"[FCM] Notificación de {tipo} enviada para {nombre_estudiante}. ID: {response}")
            else:
                logging.info(f"[FCM] Omitiendo {tipo} para {nombre_estudiante}: Representante sin Token configurado.")
                
        except Exception as e:
            logging.error(f"[FCM] Error al enviar notificación Push: {e}")

    def set_camera_status(self, camera_id, is_active, ubicacion=None, nombre_camara=None):
        """
        Actualiza el estado de conexión, nombre y ubicación de la cámara en Firebase.
        Se ajustó a minúsculas ('activa' / 'desactivada') para que el HTML lo detecte correctamente.
        """
        if not self.is_connected:
            return
            
        try:
            cam_ref = self.db_ref.child(camera_id)
            
            datos = {
                'activo': is_active,
                'estado': 'activa' if is_active else 'desactivada',
                'status': 'online' if is_active else 'offline'
            }
            
            if is_active:
                if nombre_camara:
                    datos['camara_nombre'] = nombre_camara
                if ubicacion:
                    datos['ubicacion'] = ubicacion
                    
            cam_ref.update(datos)
            estado_str = "ENCENDIDA" if is_active else "APAGADA"
            logging.info(f"[FIREBASE] Estado de la cámara {camera_id} actualizado a: {estado_str}")
            
        except Exception as e:
            logging.error(f"[ERROR] No se pudo actualizar el estado de la cámara {camera_id}: {e}")