import unittest
import time
from src.backend.services.event_processor import (
    EventProcessor, RecognitionResult, Event, Alert
)

class TestEventProcessor(unittest.TestCase):
    def setUp(self):
        # Usar un tiempo límite corto de 10 segundos para pruebas unitarias rápidas
        self.processor = EventProcessor(time_limit_seconds=10.0)
        self.start_time = 1000.0

    def test_evento_entrada(self):
        """Verifica la generación de evento de ENTRADA"""
        rec = RecognitionResult(
            session_id="ses_01",
            track_id=1,
            identity_raw="3_CC_A_Mat_Juan_Perez",
            confidence=98.0,
            camera_id="Puerta_Principal",
            detected_course_id="Puerta_Principal",
            camera_type="ENTRADA"
        )
        event, alert = self.processor.process_recognition(rec, current_time=self.start_time)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "ENTRADA")
        self.assertEqual(event.student_name, "Juan Perez")
        self.assertEqual(event.origin_course_id, "3_CC_A_Mat")
        self.assertIsNone(alert)

    def test_evento_salida(self):
        """Verifica la generación de evento de SALIDA"""
        rec = RecognitionResult(
            session_id="ses_02",
            track_id=2,
            identity_raw="3_CC_A_Mat_Juan_Perez",
            confidence=97.0,
            camera_id="Puerta_Salida",
            detected_course_id="Puerta_Salida",
            camera_type="SALIDA"
        )
        event, alert = self.processor.process_recognition(rec, current_time=self.start_time)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "SALIDA")
        self.assertEqual(event.student_name, "Juan Perez")
        self.assertIsNone(alert)

    def test_evento_presencia_normal(self):
        """Verifica la presencia normal de un alumno en su aula asignada"""
        rec = RecognitionResult(
            session_id="ses_03",
            track_id=3,
            identity_raw="3_CC_A_Mat_Juan_Perez",
            confidence=99.0,
            camera_id="3_CC_A_Mat",
            detected_course_id="3_CC_A_Mat",
            camera_type="AULA"
        )
        event, alert = self.processor.process_recognition(rec, current_time=self.start_time)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "PRESENCIA")
        self.assertEqual(event.student_name, "Juan Perez")
        self.assertIsNone(alert)

    def test_evento_intruso_desconocido(self):
        """Verifica la detección de un rostro desconocido y la alerta inmediata"""
        rec = RecognitionResult(
            session_id="ses_04",
            track_id=4,
            identity_raw="Desconocido",
            confidence=0.0,
            camera_id="3_CC_A_Mat",
            detected_course_id="3_CC_A_Mat",
            camera_type="AULA"
        )
        event, alert = self.processor.process_recognition(rec, current_time=self.start_time)
        
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "INTRUSO")
        self.assertEqual(event.student_name, "Persona Desconocida")
        self.assertIsNotNone(alert)
        self.assertEqual(alert.type, "UNKNOWN_INTRUDER")

    def test_evento_curso_diferente_y_permanencia_menor_10min(self):
        """Verifica estudiante en curso diferente durante menos del límite de tiempo (sin alerta)"""
        rec = RecognitionResult(
            session_id="ses_05",
            track_id=5,
            identity_raw="3_CC_A_Mat_Edward_Jaime",
            confidence=96.0,
            camera_id="3_CONT_B_Mat",
            detected_course_id="3_CONT_B_Mat",
            camera_type="AULA"
        )
        
        # t = 1000s (Inicio)
        event, alert = self.processor.process_recognition(rec, current_time=self.start_time)
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "CURSO_DIFERENTE")
        self.assertIsNone(alert)
        
        # t = 1005s (5 segundos transcurridos, límite = 10s -> NO genera alerta)
        rec2 = rec.model_copy()
        event2, alert2 = self.processor.process_recognition(rec2, current_time=self.start_time + 5.0)
        self.assertIsNone(alert2)

    def test_permanencia_mayor_10min_y_prevencion_duplicados(self):
        """Verifica la alerta por permanencia excedida y prevención estricta de duplicados"""
        rec = RecognitionResult(
            session_id="ses_06",
            track_id=6,
            identity_raw="3_CC_A_Mat_Edward_Jaime",
            confidence=95.0,
            camera_id="3_CONT_B_Mat",
            detected_course_id="3_CONT_B_Mat",
            camera_type="AULA"
        )
        
        # t = 1000s: Inicio de permanencia fuera de curso
        self.processor.process_recognition(rec, current_time=self.start_time)
        
        # t = 1012s: (12s transcurridos > 10s límite) -> DEBE generar alerta por primera vez
        alerts = self.processor.evaluate_pending_incidents(current_time=self.start_time + 12.0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "PERMANENCIA_EXCESIVA_10_MIN")
        self.assertIn("Edward Jaime", alerts[0].message)

        # t = 1015s: Segunda evaluación -> NO debe generar alerta duplicada
        alerts_dup = self.processor.evaluate_pending_incidents(current_time=self.start_time + 15.0)
        self.assertEqual(len(alerts_dup), 0)

    def test_cierre_de_incidente(self):
        """Verifica el cierre automático de un incidente cuando el alumno regresa a su curso"""
        rec_fuera = RecognitionResult(
            session_id="ses_07",
            track_id=7,
            identity_raw="3_CC_A_Mat_Edward_Jaime",
            confidence=94.0,
            camera_id="3_CONT_B_Mat",
            detected_course_id="3_CONT_B_Mat",
            camera_type="AULA"
        )
        # Registra en curso diferente
        self.processor.process_recognition(rec_fuera, current_time=self.start_time)
        self.assertIn("3_CC_A_Mat_Edward_Jaime", self.processor.active_incidents)

        # Registra regreso a su curso asignado (3_CC_A_Mat)
        rec_regreso = RecognitionResult(
            session_id="ses_07",
            track_id=7,
            identity_raw="3_CC_A_Mat_Edward_Jaime",
            confidence=98.0,
            camera_id="3_CC_A_Mat",
            detected_course_id="3_CC_A_Mat",
            camera_type="AULA"
        )
        event, _ = self.processor.process_recognition(rec_regreso, current_time=self.start_time + 8.0)
        
        # El incidente debió cerrarse y eliminarse de active_incidents
        self.assertNotIn("3_CC_A_Mat_Edward_Jaime", self.processor.active_incidents)
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "PRESENCIA")

if __name__ == "__main__":
    unittest.main()
