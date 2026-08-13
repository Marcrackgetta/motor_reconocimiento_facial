from pydantic import BaseModel

# Este esquema valida que los datos JSON que envíe el Edge sean correctos
class EventoEdge(BaseModel):
    identity_uuid: str
    camera_id: str
    timestamp: float
    block: str
    status: str