import unittest
import asyncio
import json
from src.backend.core.ws_manager import ConnectionManager

class MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent_messages = []
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, message: str):
        if self.closed:
            raise RuntimeError("WebSocket closed")
        self.sent_messages.append(message)

class TestWebSocketLive(unittest.TestCase):
    def setUp(self):
        self.manager = ConnectionManager()
        self.ws_admin = MockWebSocket()
        self.ws_rep1 = MockWebSocket()
        self.ws_rep2 = MockWebSocket()

    def test_websocket_selective_broadcasting(self):
        """Verifica la emisión selectiva de eventos autorizados por representante"""
        async def run_test():
            # Conectar Admin (recibe todo)
            await self.manager.connect(self.ws_admin, email="admin@colegio.edu.ec", role="admin")

            # Conectar Representante 1 (solo alumno Edward Jaime)
            await self.manager.connect(
                self.ws_rep1,
                email="rep1@colegio.edu.ec",
                role="representante",
                student_ids=["3_CC_A_Mat_Edward_Jaime"]
            )

            # Conectar Representante 2 (solo alumna Maria Lopez)
            await self.manager.connect(
                self.ws_rep2,
                email="rep2@colegio.edu.ec",
                role="representante",
                student_ids=["3_CC_A_Mat_Maria_Lopez"]
            )

            # 1. Emitir evento para Edward Jaime
            payload_edward = {
                "student_id": "3_CC_A_Mat_Edward_Jaime",
                "nombre": "Edward Jaime",
                "tipo_evento": "ENTRADA"
            }
            await self.manager.emit_event("ENTRADA", payload_edward)

            # Admin y Rep1 deben recibirlo. Rep2 NO debe recibirlo.
            self.assertEqual(len(self.ws_admin.sent_messages), 1)
            self.assertEqual(len(self.ws_rep1.sent_messages), 1)
            self.assertEqual(len(self.ws_rep2.sent_messages), 0)

            msg_rep1 = json.loads(self.ws_rep1.sent_messages[0])
            self.assertEqual(msg_rep1["type"], "STUDENT_ENTRY")
            self.assertEqual(msg_rep1["data"]["nombre"], "Edward Jaime")

            # 2. Emitir alerta de intruso de seguridad (debe llegar a todos)
            payload_intruso = {
                "nombre": "Persona Desconocida",
                "tipo_evento": "INTRUSO_EXTERNO"
            }
            await self.manager.emit_event("INTRUSO_EXTERNO", payload_intruso)

            # Rep2 ahora debe tener 1 mensaje (la alerta de intruso)
            self.assertEqual(len(self.ws_rep2.sent_messages), 1)
            msg_rep2 = json.loads(self.ws_rep2.sent_messages[0])
            self.assertEqual(msg_rep2["type"], "INTRUDER_DETECTED")

            # 3. Desconexión limpia
            self.manager.disconnect(self.ws_rep1)
            self.assertNotIn(self.ws_rep1, self.manager.active_connections)

        asyncio.run(run_test())

    def test_event_type_mapping(self):
        """Verifica el mapeo correcto de la taxonomía de eventos de WebSockets"""
        self.assertEqual(ConnectionManager.map_event_type("ENTRADA"), "STUDENT_ENTRY")
        self.assertEqual(ConnectionManager.map_event_type("SALIDA"), "STUDENT_EXIT")
        self.assertEqual(ConnectionManager.map_event_type("PRESENCIA_NORMAL"), "STUDENT_PRESENT")
        self.assertEqual(ConnectionManager.map_event_type("CURSO_DIFERENTE"), "DIFFERENT_COURSE")
        self.assertEqual(ConnectionManager.map_event_type("INTRUSO"), "INTRUDER_DETECTED")
        self.assertEqual(ConnectionManager.map_event_type("PERMANENCIA_EXCESIVA_10_MIN"), "ALERT_CREATED")
        self.assertEqual(ConnectionManager.map_event_type("INCIDENTE_RESUELTO"), "ALERT_RESOLVED")

if __name__ == "__main__":
    unittest.main()
