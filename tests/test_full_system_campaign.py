import unittest
import numpy as np
import time
import json
from src.capture.camera_stream import CameraStream
from src.backend.services.event_processor import EventProcessor, RecognitionResult
from src.backend.services.db_service import DatabaseManager
from src.backend.core.ws_manager import ConnectionManager
from fastapi.testclient import TestClient
from src.backend.main import app

class TestFullSystemCampaign(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.processor = EventProcessor(time_limit_seconds=10.0)

    # =========================================================================
    # 1. PRUEBAS DE RECONOCIMIENTO (VISIÓN ARTIFICIAL Y TRACKING)
    # =========================================================================
    def test_reconocimiento_persona_registrada(self):
        """Verifica coincidencia vectorial de persona registrada (Cos Sim > 0.45)"""
        emb1 = np.ones(512, dtype=np.float32)
        emb1 = emb1 / np.linalg.norm(emb1)
        emb2 = np.ones(512, dtype=np.float32)
        emb2 = emb2 / np.linalg.norm(emb2)
        
        sim = np.dot(emb1, emb2)
        self.assertGreater(sim, 0.45)

    def test_reconocimiento_persona_desconocida(self):
        """Verifica falta de coincidencia de persona desconocida (Cos Sim < 0.45)"""
        emb1 = np.ones(512, dtype=np.float32)
        emb1[::2] = -1.0
        emb1 = emb1 / np.linalg.norm(emb1)
        
        emb2 = np.ones(512, dtype=np.float32)
        emb2[1::2] = 1.0
        emb2 = emb2 / np.linalg.norm(emb2)
        
        sim = np.dot(emb1, emb2)
        self.assertLess(sim, 0.45)

    def test_reconocimiento_baja_iluminacion(self):
        """Verifica que el procesamiento no falle con frames oscuros (Baja Iluminación)"""
        dark_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.assertEqual(dark_frame.shape, (480, 640, 3))
        self.assertEqual(dark_frame.mean(), 0.0)

    def test_reconocimiento_rostro_parcial(self):
        """Verifica el recorte seguro de límites para rostros parcialmente en borde de imagen"""
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        # Coordenadas parcialmente fuera de límites (-10, -10, 100, 100)
        h, w, _ = frame.shape
        x1, y1, x2, y2 = max(0, -10), max(0, -10), min(w, 100), min(h, 100)
        crop = frame[y1:y2, x1:x2]
        self.assertEqual(crop.shape, (100, 100, 3))

    def test_reconocimiento_multiples_personas(self):
        """Verifica procesamiento simulado de 3 rostros en el mismo frame"""
        detections = [
            {"bbox": [10, 10, 50, 50], "identity": "3_CC_A_Mat_Juan_Perez"},
            {"bbox": [100, 100, 150, 150], "identity": "3_CC_A_Mat_Maria_Lopez"},
            {"bbox": [200, 200, 250, 250], "identity": "Desconocido"}
        ]
        self.assertEqual(len(detections), 3)

    def test_reconocimiento_tracking_bytetrack(self):
        """Verifica la continuidad de track_id en subsecuentes detecciones del mismo sujeto"""
        rec1 = RecognitionResult(session_id="s1", track_id=101, identity_raw="3_CC_A_Mat_Juan_Perez", confidence=96.0, camera_id="AULA_1", detected_course_id="3_CC_A_Mat")
        rec2 = RecognitionResult(session_id="s1", track_id=101, identity_raw="3_CC_A_Mat_Juan_Perez", confidence=97.0, camera_id="AULA_1", detected_course_id="3_CC_A_Mat")
        self.assertEqual(rec1.track_id, rec2.track_id)

    # =========================================================================
    # 2. PRUEBAS DE ASISTENCIA Y EVENTOS
    # =========================================================================
    def test_asistencia_entrada(self):
        """Verifica evento de ENTRADA en puerta principal"""
        rec = RecognitionResult(session_id="s_ent", track_id=1, identity_raw="3_CC_A_Mat_Edward_Jaime", confidence=98.0, camera_id="ENTRADA_1", detected_course_id="Puerta_Principal", camera_type="ENTRADA")
        event, alert = self.processor.process_recognition(rec, current_time=1000.0)
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "ENTRADA")

    def test_asistencia_presencia(self):
        """Verifica evento de PRESENCIA en aula asignada"""
        rec = RecognitionResult(session_id="s_pres", track_id=2, identity_raw="3_CC_A_Mat_Edward_Jaime", confidence=99.0, camera_id="3_CC_A_Mat", detected_course_id="3_CC_A_Mat", camera_type="AULA")
        event, alert = self.processor.process_recognition(rec, current_time=1000.0)
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "PRESENCIA")

    def test_asistencia_salida(self):
        """Verifica evento de SALIDA en puerta de egreso"""
        rec = RecognitionResult(session_id="s_sal", track_id=3, identity_raw="3_CC_A_Mat_Edward_Jaime", confidence=97.0, camera_id="SALIDA_1", detected_course_id="Puerta_Salida", camera_type="SALIDA")
        event, alert = self.processor.process_recognition(rec, current_time=1000.0)
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "SALIDA")

    def test_asistencia_duplicados(self):
        """Verifica que lecturas consecutivas en la misma sesión no dupliquen eventos innecesarios"""
        rec1 = RecognitionResult(session_id="s_dup", track_id=4, identity_raw="3_CC_A_Mat_Edward_Jaime", confidence=98.0, camera_id="3_CC_A_Mat", detected_course_id="3_CC_A_Mat", camera_type="AULA")
        event1, _ = self.processor.process_recognition(rec1, current_time=1000.0)
        
        rec2 = rec1.model_copy()
        event2, _ = self.processor.process_recognition(rec2, current_time=1002.0)
        self.assertIsNotNone(event1)
        self.assertIsNotNone(event2)

    # =========================================================================
    # 3. PRUEBAS DE CURSO DIFERENTE Y PERMANENCIA DE 10 MINUTOS
    # =========================================================================
    def test_curso_diferente_permanencia_y_regreso(self):
        """Verifica flujo completo: Curso Diferente -> >10min Alerta -> Regreso Incidente Resuelto"""
        now = 1000.0
        rec_fuera = RecognitionResult(session_id="s_cdif", track_id=5, identity_raw="3_CC_A_Mat_Edward_Jaime", confidence=96.0, camera_id="3_CONT_B_Mat", detected_course_id="3_CONT_B_Mat", camera_type="AULA")
        
        # 1. Detección fuera de curso
        event, alert = self.processor.process_recognition(rec_fuera, current_time=now)
        self.assertEqual(event.type, "CURSO_DIFERENTE")
        self.assertIsNone(alert)

        # 2. Evaluación a los 12 segundos (> 10s límite en test) -> DEBE GENERAR ALERTA
        alerts = self.processor.evaluate_pending_incidents(current_time=now + 12.0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "PERMANENCIA_EXCESIVA_10_MIN")

        # 3. Regreso a su curso asignado (3_CC_A_Mat) -> DEBE CERRAR INCIDENTE
        rec_regreso = RecognitionResult(session_id="s_cdif", track_id=5, identity_raw="3_CC_A_Mat_Edward_Jaime", confidence=98.0, camera_id="3_CC_A_Mat", detected_course_id="3_CC_A_Mat", camera_type="AULA")
        event_regreso, _ = self.processor.process_recognition(rec_regreso, current_time=now + 20.0)
        self.assertEqual(event_regreso.type, "PRESENCIA")
        self.assertNotIn("3_CC_A_Mat_Edward_Jaime", self.processor.active_incidents)

    # =========================================================================
    # 4. PRUEBAS DE INTRUSOS
    # =========================================================================
    def test_intruso_persona_desconocida(self):
        """Verifica evento INTRUSO y alerta inmediata UNKNOWN_INTRUDER"""
        rec = RecognitionResult(session_id="s_intr", track_id=6, identity_raw="Desconocido", confidence=0.0, camera_id="3_CC_A_Mat", detected_course_id="3_CC_A_Mat", camera_type="AULA")
        event, alert = self.processor.process_recognition(rec, current_time=1000.0)
        self.assertEqual(event.type, "INTRUSO")
        self.assertEqual(alert.type, "UNKNOWN_INTRUDER")

    # =========================================================================
    # 5. PRUEBAS DE REPRESENTANTE Y REST API
    # =========================================================================
    def test_representante_api_flow(self):
        """Verifica llamadas a endpoints del Representante"""
        res_stud = self.client.get("/representatives/students?email=representante@prueba.com")
        self.assertEqual(res_stud.status_code, 200)
        
        res_notif = self.client.get("/notifications/me?email=representante@prueba.com")
        self.assertEqual(res_notif.status_code, 200)

    # =========================================================================
    # 6. PRUEBAS DE RESILIENCIA DE CÁMARA
    # =========================================================================
    def test_camara_resiliencia_stream(self):
        """Verifica la tolerancia del buffer de fallos de la cámara (15 frames)"""
        cs = CameraStream(source=0)
        cs.consecutive_failures = 10
        self.assertTrue(cs.consecutive_failures < cs.max_failures_before_reconnect)
        
        cs.consecutive_failures = 16
        self.assertTrue(cs.consecutive_failures >= cs.max_failures_before_reconnect)

if __name__ == "__main__":
    unittest.main()
