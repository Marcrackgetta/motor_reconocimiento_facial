import requests
import logging
import concurrent.futures

class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

    def _post_async(self, url, payload):
        try:
            requests.post(url, json=payload, timeout=2)
        except Exception as e:
            logging.error(f"Error llamando asíncronamente a {url}: {e}")

    def forzar_reseteo_camaras(self, camera_sources):
        payload = {"camera_sources": camera_sources}
        self.executor.submit(self._post_async, f"{self.base_url}/ai/cameras/reset", payload)

    def iniciar_sesion_camara(self, camara_info, known_names=None):
        # Generar session_id de inmediato para no bloquear el hilo de interfaz/visión
        curso_actual = camara_info.get("curso_asignado", "General")
        session_id = curso_actual.strip().replace(" ", "_")
        
        payload = {
            "camara_info": camara_info,
            "known_names": known_names or []
        }
        self.executor.submit(self._post_async, f"{self.base_url}/ai/session/start", payload)
        return session_id

    def registrar_deteccion(self, session_id, identidad, estado, confianza, camara_info, custom_doc_id=None, known_names=None):
        # Esta función originalmente retorna un doc_id, pero al guardar intrusos asíncronamente, 
        # necesitamos el doc_id de inmediato para guardarlo en la estructura. 
        # Modificación: Generar un UUID único o usar el track_id/custom_doc_id como fallback, o simplemente 
        # retornar el custom_doc_id y que el backend lo maneje.
        # En la lógica actual, el backend devuelve el `doc_id`.
        # Si lo pasamos asíncrono, no tendremos el `doc_id` para actualizar la duración luego.
        # Vamos a hacerlo pseudo-asíncrono o vamos a esperar el doc_id rápido y lo demás en background.
        # Mejor aún, hacer que Firebase acepte el custom_doc_id como el doc_id real, entonces retornamos custom_doc_id.
        doc_id = custom_doc_id or f"{session_id}_{identidad}_{int(confianza)}"
        
        payload = {
            "session_id": session_id,
            "identidad": identidad,
            "estado": estado,
            "confianza": float(confianza),
            "camara_info": camara_info,
            "known_names": known_names or [],
            "doc_id": doc_id  # Sugerimos al backend este ID
        }
        self.executor.submit(self._post_async, f"{self.base_url}/ai/detection", payload)
        return doc_id

    def actualizar_duracion_intruso(self, session_id, doc_id, duracion, identidad=None):
        payload = {
            "session_id": session_id,
            "doc_id": doc_id,
            "duracion": float(duracion),
            "identidad": identidad or ""
        }
        self.executor.submit(self._post_async, f"{self.base_url}/ai/intruder/duration", payload)

    def cerrar_sesion_camara(self, session_id, avg_fps=0.0):
        # Síncrono o asíncrono al cerrar, da igual. Lo hacemos asíncrono para no trabar al salir.
        self.executor.submit(self._post_async, f"{self.base_url}/ai/session/end", {"session_id": session_id})

api_client = APIClient()
