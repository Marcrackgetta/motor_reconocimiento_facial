import unittest
import time
import numpy as np
import cv2
from src.capture.camera_stream import CameraStream
from src.storage.api_client import APIClient
from src.vision.frame_context import FrameContext
from src.vision.face_data import DetectedFace
from src.vision.recognition_engine import RecognitionEngine
from src.vision.tracker import FaceTracker

class TestMotorOptimizaciones(unittest.TestCase):
    def test_camera_stream_resilience(self):
        """Verifica que CameraStream maneje correctamente reconexión, fallos y secuencias de frames."""
        stream = CameraStream(source=0)
        # Esperar inicio de hilo
        time.sleep(0.2)
        
        # Verificar atributos iniciales
        self.assertIsNotNone(stream)
        self.assertTrue(hasattr(stream, "consecutive_failures"))
        self.assertEqual(stream.max_failures_before_reconnect, 15)
        
        # Test get_frame_with_id
        frame, frame_id = stream.get_frame_with_id()
        self.assertIsInstance(frame_id, int)
        
        # Probar liberación limpia
        stream.release()
        self.assertFalse(stream.running)
        self.assertIsNone(stream.cap)

    def test_api_client_non_blocking(self):
        """Verifica que la llamada a iniciar_sesion_camara sea instantánea y no bloquee el hilo de interfaz."""
        client = APIClient(base_url="http://127.0.0.1:9999") # URL inalcanzable para probar asincronía
        camara_info = {"curso_asignado": "3_INFO_A", "tipo": "AULA"}
        
        t0 = time.perf_counter()
        session_id = client.iniciar_sesion_camara(camara_info)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        
        self.assertEqual(session_id, "3_INFO_A")
        # Debe retornar en menos de 50 ms sin bloquear 2 segundos esperando HTTP
        self.assertLess(elapsed_ms, 50.0)

    def test_recognition_cache_and_tracker(self):
        """Verifica que RecognitionEngine y FaceTracker manejen la caché sin fugas ni cierres prematuros."""
        known_names = ["3_INFO_A_Juan_Perez"]
        known_encodings = [np.ones(512, dtype=np.float32)]
        
        engine = RecognitionEngine(known_encodings=known_encodings, known_names=known_names, threshold=0.45)
        tracker = FaceTracker()
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        context = FrameContext(frame=frame)
        
        # Simular un rostro detectado
        face = DetectedFace(bbox=(50, 150, 150, 50), embedding=None, score=0.9)
        context.faces = [face]
        
        # Tracking actualiza track_id
        context = tracker.update(context)
        self.assertEqual(len(context.faces), 1)
        self.assertIsNotNone(context.faces[0].track_id)
        
        # Motor de reconocimiento asigna estado inicial "Calculando..." mientras procesa en background
        class MockVisionEngine:
            def extract_embedding(self, frame, face):
                face.embedding = np.ones(512, dtype=np.float32)
                
        context = engine.process(frame, context, MockVisionEngine())
        self.assertIn(context.faces[0].recognition_state, ["PROCESSING", "RECOGNIZED"])

if __name__ == "__main__":
    unittest.main()
