import unittest
from src.backend.services.db_service import DatabaseManager

class TestEventos(unittest.TestCase):
    def test_procesar_evento_entrada(self):
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
                            def set(self, data):
                                pass
                            def update(self, data):
                                pass
                        return MockDoc(doc_id)
                return MockCollection()
                
        manager = DatabaseManager()
        manager.db = MockDB()
        
        # Test Enviar a camara tipo ENTRADA
        camara_info = {"tipo": "ENTRADA", "curso_asignado": "Puerta Principal"}
        evento = manager._procesar_evento_estudiante("Juan_Perez", "PRESENTE", camara_info)
        
        self.assertIsNotNone(evento)
        self.assertEqual(evento["tipo_evento"], "ENTRADA")
        self.assertEqual(evento["nombre"], "Juan Perez")
        self.assertFalse(evento["alerta_enviada"])

if __name__ == "__main__":
    unittest.main()
