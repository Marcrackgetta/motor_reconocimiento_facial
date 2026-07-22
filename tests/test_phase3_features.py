import unittest
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.services.push_service import push_service

class TestPhase3Features(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_reports_metrics(self):
        """Verifica el endpoint de métricas consolidadas /reports/metrics"""
        res = self.client.get("/reports/metrics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("entradas", data)
        self.assertIn("salidas", data)
        self.assertIn("total_eventos", data)

    def test_reports_attendance(self):
        """Verifica el endpoint de reporte de asistencia /reports/attendance"""
        res = self.client.get("/reports/attendance")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_reports_entries_exits_intruders_incidents(self):
        """Verifica los reportes detallados por categoría de evento"""
        for path in ["/reports/entries", "/reports/exits", "/reports/intruders", "/reports/incidents"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200)
            self.assertIsInstance(res.json(), list)

    def test_statistics_by_course_and_trends(self):
        """Verifica los endpoints de estadísticas por curso y tendencias temporales"""
        res_course = self.client.get("/reports/statistics/by-course")
        self.assertEqual(res_course.status_code, 200)
        self.assertIsInstance(res_course.json(), dict)

        res_trends = self.client.get("/reports/statistics/trends")
        self.assertEqual(res_trends.status_code, 200)
        self.assertIsInstance(res_trends.json(), list)

    def test_audit_logs(self):
        """Verifica la consulta de logs de auditoría de acciones administrativas /reports/audit"""
        res = self.client.get("/reports/audit")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_push_notification_service(self):
        """Verifica el envío de notificaciones Push con persistencia en el historial interno"""
        success = push_service.send_push_notification(
            recipient_email="representante@prueba.com",
            title="Prueba de Notificación Push",
            body="Mensaje de prueba de la Fase 3",
            data_payload={"student_id": "3_CC_A_Mat_Edward_Jaime"}
        )
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
