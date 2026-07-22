import unittest
import time
from src.backend.services.db_service import DatabaseManager
from src.backend.services.event_processor import EventProcessor, RecognitionResult

class TestRepresentativeE2E(unittest.TestCase):
    def setUp(self):
        class MockDB:
            def __init__(self):
                self.events_db = []
                self.students_db = [
                    {
                        "id": "3_CC_A_Mat_Edward_Jaime",
                        "nombre": "Edward Jaime",
                        "curso_origen": "3_CC_A_Mat",
                        "curso_detectado": "3_CC_A_Mat",
                        "estado_actual": "PRESENCIA_NORMAL",
                        "representantes": ["rep_edward@prueba.com"]
                    },
                    {
                        "id": "3_CC_A_Mat_Maria_Lopez",
                        "nombre": "Maria Lopez",
                        "curso_origen": "3_CC_A_Mat",
                        "curso_detectado": "3_CC_A_Mat",
                        "estado_actual": "PRESENCIA_NORMAL",
                        "representantes": ["rep_edward@prueba.com", "rep_maria@prueba.com"]
                    }
                ]

            def collection(self, name):
                db_self = self
                class MockCollection:
                    def __init__(self, coll_name):
                        self.coll_name = coll_name
                        self.query_field = None
                        self.query_op = None
                        self.query_val = None

                    def where(self, field, op, val):
                        self.query_field = field
                        self.query_op = op
                        self.query_val = val
                        return self

                    def get(self):
                        if self.coll_name == "Estudiantes":
                            if self.query_field == "representantes" and self.query_op == "array_contains":
                                filtered = [s for s in db_self.students_db if self.query_val in s.get("representantes", [])]
                                return [MockDocSnapshot(s["id"], s) for s in filtered]
                            return [MockDocSnapshot(s["id"], s) for s in db_self.students_db]
                        elif self.coll_name == "Eventos":
                            if self.query_field == "estudiante_id" and self.query_op == "==":
                                filtered = [e for e in db_self.events_db if e.get("student_id") == self.query_val]
                                return [MockDocSnapshot(e["id"], e) for e in filtered]
                            return [MockDocSnapshot(e["id"], e) for e in db_self.events_db]
                        return []

                    def document(self, doc_id=None):
                        class MockDoc:
                            def __init__(self, d_id):
                                self.id = d_id or f"doc_{len(db_self.events_db)}"
                            def get(self):
                                return MockDocSnapshot(self.id, {})
                            def set(self, data):
                                if "id" not in data:
                                    data["id"] = self.id
                                db_self.events_db.append(data)
                            def update(self, data):
                                pass
                        return MockDoc(doc_id)
                return MockCollection(name)

        class MockDocSnapshot:
            def __init__(self, doc_id, data):
                self.id = doc_id
                self._data = data
                self.exists = True
            def to_dict(self):
                return self._data

        self.mock_db = MockDB()
        self.db_manager = DatabaseManager()
        self.db_manager.db = self.mock_db
        self.processor = EventProcessor(time_limit_seconds=10.0)

    def test_representante_obtener_estudiantes_asignados(self):
        """Verifica que el representante consulte sus estudiantes asignados"""
        students = self.db_manager.get_students_for_representative("rep_edward@prueba.com")
        self.assertEqual(len(students), 2)
        names = [s["nombre"] for s in students]
        self.assertIn("Edward Jaime", names)
        self.assertIn("Maria Lopez", names)

    def test_representante_varios_estudiantes_y_varios_representantes(self):
        """Verifica relación de varios estudiantes a un representante y viceversa"""
        students_maria = self.db_manager.get_students_for_representative("rep_maria@prueba.com")
        self.assertEqual(len(students_maria), 1)
        self.assertEqual(students_maria[0]["nombre"], "Maria Lopez")

    def test_flujo_camara_evento_notificacion_representante(self):
        """Test End-to-End: Cámara -> EventProcessor -> Firestore Event -> Representante Notification"""
        now = 2000.0
        
        # 1. Cámara detecta a Edward en curso diferente (3_CONT_B_Mat)
        rec = RecognitionResult(
            session_id="ses_e2e",
            track_id=10,
            identity_raw="3_CC_A_Mat_Edward_Jaime",
            confidence=97.5,
            camera_id="3_CONT_B_Mat",
            detected_course_id="3_CONT_B_Mat",
            camera_type="AULA"
        )
        
        event, alert = self.processor.process_recognition(rec, current_time=now)
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "CURSO_DIFERENTE")

        # Inyectar evento simulando persistencia
        evento_dict = event.model_dump()
        evento_dict["nombre"] = event.student_name
        evento_dict["curso_origen"] = event.origin_course_id
        evento_dict["curso_detectado"] = event.detected_course_id
        evento_dict["camara_curso"] = event.detected_course_id
        evento_dict["tipo_evento"] = event.type
        self.mock_db.events_db.append(evento_dict)

        # 2. Representante consulta eventos de sus representados
        events_edward = self.mock_db.collection("Eventos").where("estudiante_id", "==", "3_CC_A_Mat_Edward_Jaime").get()
        self.assertTrue(len(events_edward) >= 1)
        res_event = events_edward[0].to_dict()
        self.assertEqual(res_event["nombre"], "Edward Jaime")
        self.assertEqual(res_event["tipo_evento"], "CURSO_DIFERENTE")
        self.assertEqual(res_event["curso_detectado"], "3_CONT_B_Mat")

if __name__ == "__main__":
    unittest.main()
