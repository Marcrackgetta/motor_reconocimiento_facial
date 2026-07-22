import unittest
from fastapi.testclient import TestClient
from src.backend.main import app

class TestFastAPIDomainArchitecture(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_domain_routers_registered(self):
        """Verifica que todos los routers organizados por dominio estén registrados y activos en FastAPI"""
        self.assertNotEqual(self.client.get("/students/me?email=test@test.com").status_code, 404)
        self.assertNotEqual(self.client.get("/representatives/students?email=test@test.com").status_code, 404)
        self.assertNotEqual(self.client.get("/courses/").status_code, 404)
        self.assertNotEqual(self.client.get("/cameras").status_code, 404)
        self.assertNotEqual(self.client.get("/attendance/daily").status_code, 404)
        self.assertNotEqual(self.client.get("/events/").status_code, 404)
        self.assertNotEqual(self.client.get("/alerts/").status_code, 404)
        self.assertNotEqual(self.client.get("/notifications/me?email=test@test.com").status_code, 404)

    def test_representatives_domain_endpoint(self):
        """Verifica el funcionamiento del endpoint /representatives/students"""
        response = self.client.get("/representatives/students?email=representante@prueba.com")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_events_domain_endpoint(self):
        """Verifica el funcionamiento del endpoint /events/"""
        response = self.client.get("/events/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

if __name__ == "__main__":
    unittest.main()
