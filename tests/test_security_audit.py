import unittest
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.services.db_service import DatabaseManager

class TestSecurityAudit(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_cors_security_headers(self):
        """Verifica que CORS no utilice la wildcard universal insegura '*' con credenciales"""
        response = self.client.options(
            "/login",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")

    def test_authorization_bypass_prevention(self):
        """Verifica la prevención de bypass de autorización al consultar historial de otro estudiante"""
        class MockDB:
            def collection(self, name):
                class MockColl:
                    def get(self): return []
                    def where(self, *args): return self
                    def order_by(self, *args, **kwargs): return self
                    def limit(self, *args): return self
                    def document(self, doc_id=None):
                        class MockDoc:
                            id = "mock_audit_id"
                            def set(self, data): pass
                        return MockDoc()
                return MockColl()

        db = DatabaseManager()
        db.db = MockDB()

        # Simular que el representante 'rep1@prueba.com' solo posee acceso al estudiante '3_CC_A_Mat_Juan_Perez'
        def mock_get_students(email):
            if email == "rep1@prueba.com":
                return [{"id": "3_CC_A_Mat_Juan_Perez", "nombre": "Juan Perez"}]
            return []

        def mock_get_role(email):
            return "representante"

        db.get_students_for_representative = mock_get_students
        db.get_user_role = mock_get_role

        from src.backend.routers.students import db_manager as student_db
        student_db.get_students_for_representative = mock_get_students
        student_db.get_user_role = mock_get_role
        student_db.db = MockDB()

        # Intento de consultar estudiante ajeno '3_CC_A_Mat_Estudiante_Ajeno' ➔ DEBE RETORNAR 403 FORBIDDEN
        res_forbidden = self.client.get(
            "/students/3_CC_A_Mat_Estudiante_Ajeno/history?email=rep1@prueba.com"
        )
        self.assertEqual(res_forbidden.status_code, 403)
        self.assertIn("Acceso denegado", res_forbidden.json()["detail"])

    def test_rate_limiter_login(self):
        """Verifica que el middleware de Rate Limiting bloquee ataques de fuerza bruta en /login"""
        # Ejecutar peticiones hasta superar el límite de 10 peticiones por minuto
        blocked = False
        for _ in range(12):
            res = self.client.post("/login", json={"email": "test@test.com", "password": "wrongpassword"})
            if res.status_code == 429:
                blocked = True
                break
        self.assertTrue(blocked, "El rate limiter no bloqueó los intentos de login repetidos")

if __name__ == "__main__":
    unittest.main()
