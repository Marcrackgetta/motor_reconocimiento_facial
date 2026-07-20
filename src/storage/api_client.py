import requests
import logging

class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url

    def forzar_reseteo_camaras(self, camera_sources):
        # En la Fase 2, el backend debería hacerlo al arrancar o lo obviamos desde Python,
        # pero podemos hacer un endpoint si es necesario. Por ahora pasamos.
        pass

    def iniciar_sesion_camara(self, camara_info, known_names=None):
        try:
            payload = {
                "camara_info": camara_info,
                "known_names": known_names or []
            }
            res = requests.post(f"{self.base_url}/ai/session/start", json=payload, timeout=2)
            if res.status_code == 200:
                return res.json().get("session_id")
        except Exception as e:
            logging.error(f"Error llamando a /ai/session/start: {e}")
        return None

    def registrar_deteccion(self, session_id, identidad, estado, confianza, camara_info, custom_doc_id=None, known_names=None):
        try:
            payload = {
                "session_id": session_id,
                "identidad": identidad,
                "estado": estado,
                "confianza": float(confianza),
                "camara_info": camara_info,
                "known_names": known_names or []
            }
            res = requests.post(f"{self.base_url}/ai/detection", json=payload, timeout=2)
            if res.status_code == 200:
                return res.json().get("doc_id")
        except Exception as e:
            logging.error(f"Error llamando a /ai/detection: {e}")
        return None

    def actualizar_duracion_intruso(self, session_id, doc_id, duracion, identidad=None):
        try:
            payload = {
                "session_id": session_id,
                "doc_id": doc_id,
                "duracion": float(duracion),
                "identidad": identidad or ""
            }
            requests.post(f"{self.base_url}/ai/intruder/duration", json=payload, timeout=2)
        except Exception as e:
            logging.error(f"Error llamando a /ai/intruder/duration: {e}")

    def cerrar_sesion_camara(self, session_id, avg_fps=0.0):
        try:
            requests.post(f"{self.base_url}/ai/session/end", json={"session_id": session_id}, timeout=2)
        except Exception as e:
            logging.error(f"Error llamando a /ai/session/end: {e}")

api_client = APIClient()
