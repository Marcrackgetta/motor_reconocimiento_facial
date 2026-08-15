from pydantic import BaseModel

# Esquema para validar los datos que envía el Motor Edge
class EventoEdge(BaseModel):
    identity_uuid: str
    camera_id: str
    timestamp: float
    block: str
    status: str

# Esquema para validar los datos que enviará Flutter al crear un usuario
class EstudianteNuevo(BaseModel):
    uuid: str
    nombre_completo: str
    curso_id: int