import pytest
from src.backend.services.db_service import DatabaseManager

def test_procesar_evento_entrada():
    # Mocking db manager dependencies
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
    
    assert evento is not None
    assert evento["tipo_evento"] == "ENTRADA"
    assert evento["nombre"] == "Perez" # Default parse from our mock
    assert evento["alerta_enviada"] is False
