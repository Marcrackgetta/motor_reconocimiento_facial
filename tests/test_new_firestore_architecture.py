import unittest
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.services.db_service import db_manager

class TestNewFirestoreArchitecture(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_domain_collections_read(self):
        """Verifica que las lecturas a los nuevos 4 dominios (Camaras, Usuarios, Cursos, Notificaciones) respondan correctamente"""
        # 1. Dominios de Cámaras
        cams = db_manager.get_cameras()
        self.assertIsInstance(cams, list)

        # 2. Dominio de Cursos y Estudiantes
        students = db_manager.get_students_for_representative("representante@prueba.com")
        self.assertIsInstance(students, list)

        # 3. Dominio de Usuarios
        rol = db_manager.get_user_role("representante@prueba.com")
        self.assertIsInstance(rol, str)

    def test_camera_session_and_detection_writing(self):
        """Verifica que la simulación de inicio de sesión y detección escriba en las nuevas subcolecciones"""
        camara_info = {
            "camera_id": "CAM_TEST",
            "src": 99,
            "curso_asignado": "2_INFO_B_MAT",
            "lat": -0.220000,
            "lon": -78.511944
        }
        
        # Iniciar sesión
        session_id = db_manager.iniciar_sesion_camara(camara_info)
        self.assertEqual(session_id, "CAM_TEST")

        # Registrar detección
        result = db_manager.registrar_deteccion(
            session_id="CAM_TEST",
            identidad="2_INFO_B_MAT_Estudiante_Prueba",
            estado="PRESENTE",
            confianza=98.5,
            camara_info=camara_info
        )
        self.assertIsNotNone(result)
        self.assertIn("id", result)
        self.assertIn("data", result)

    def test_endpoints_return_200(self):
        """Verifica que los endpoints de la API respondan sin 404 ni 500"""
        self.assertEqual(self.client.get("/cameras").status_code, 200)
        self.assertEqual(self.client.get("/students/me?email=representante@prueba.com").status_code, 200)
        self.assertEqual(self.client.get("/events/").status_code, 200)
        self.assertEqual(self.client.get("/reports/metrics").status_code, 200)
        self.assertEqual(self.client.get("/reports/attendance").status_code, 200)

if __name__ == "__main__":
    unittest.main()
