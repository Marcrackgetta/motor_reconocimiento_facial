import unittest
from src.backend.models.domain import (
    Student, Course, Representative, RepresentativeStudent, Camera, Event, Alert, Recognition
)
from src.backend.services.db_service import DatabaseManager

class TestDomainModels(unittest.TestCase):
    def test_student_model_isolation(self):
        """Verifica que el modelo Student aisle estrictamente el nombre sin concatenar el curso."""
        student = Student(
            id="3_CN_A_Mat_Edward_Jaime",
            name="Edward Jaime",
            first_name="Edward",
            last_name="Jaime",
            origin_course_id="3_CN_A_Mat",
            representatives=["representante@colegio.edu.ec"],
            current_status="CURSO_DIFERENTE",
            last_detected_course_id="3_CN_B_Mat"
        )
        
        self.assertEqual(student.name, "Edward Jaime")
        self.assertEqual(student.origin_course_id, "3_CN_A_Mat")
        self.assertEqual(student.last_detected_course_id, "3_CN_B_Mat")
        self.assertEqual(student.current_status, "CURSO_DIFERENTE")
        self.assertNotIn("3_CN_A_Mat", student.name)

    def test_event_model_isolation(self):
        """Verifica que un evento separe el curso de origen, curso detectado, tipo y duración."""
        event = Event(
            id="evt_001",
            student_id="3_CN_A_Mat_Edward_Jaime",
            student_name="Edward Jaime",
            origin_course_id="3_CN_A_Mat",
            detected_course_id="3_CN_B_Mat",
            type="CURSO_DIFERENTE",
            status="ACTIVO",
            duration_seconds=120.5
        )
        
        self.assertEqual(event.student_name, "Edward Jaime")
        self.assertEqual(event.origin_course_id, "3_CN_A_Mat")
        self.assertEqual(event.detected_course_id, "3_CN_B_Mat")
        self.assertEqual(event.type, "CURSO_DIFERENTE")
        self.assertEqual(event.duration_seconds, 120.5)

    def test_db_service_parsing(self):
        """Verifica que DatabaseManager._parse_identity parsee los nombres sin concatenación."""
        db = DatabaseManager()
        
        # Test 1: Etiqueta normal
        nombre, curso = db._parse_identity("3_CN_A_Mat_Edward_Jaime")
        self.assertEqual(nombre, "Edward Jaime")
        self.assertEqual(curso, "3_CN_A_Mat")
        
        # Test 2: Desconocido
        nombre_desc, curso_desc = db._parse_identity("Desconocido")
        self.assertEqual(nombre_desc, "Desconocido")
        self.assertEqual(curso_desc, "Desconocido")

    def test_event_processing_different_course(self):
        """Verifica el flujo de detección en un curso diferente."""
        class MockDB:
            def collection(self, name):
                class MockCollection:
                    def document(self, doc_id=None):
                        class MockDoc:
                            def __init__(self, id):
                                self.id = id or "mock_id"
                            def get(self):
                                class MockSnapshot:
                                    exists = False
                                    def to_dict(self): return {}
                                return MockSnapshot()
                            def set(self, data): pass
                            def update(self, data): pass
                        return MockDoc(doc_id)
                return MockCollection()

        db = DatabaseManager()
        db.db = MockDB()
        camara_info = {"tipo": "AULA", "curso_asignado": "3_CN_B_Mat"}
        
        # Simular detección de Edward (su curso origen es 3_CN_A_Mat, pero está en 3_CN_B_Mat)
        evento = db._procesar_evento_estudiante("3_CN_A_Mat_Edward_Jaime", "INTRUSO", camara_info)
        
        self.assertIsNotNone(evento)
        self.assertEqual(evento["nombre"], "Edward Jaime")
        self.assertEqual(evento["curso_origen"], "3_CN_A_Mat")
        self.assertEqual(evento["curso_detectado"], "3_CN_B_Mat")
        self.assertEqual(evento["tipo_evento"], "CURSO_DIFERENTE")

if __name__ == "__main__":
    unittest.main()
