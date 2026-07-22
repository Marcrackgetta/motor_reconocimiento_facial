from fastapi import APIRouter
from src.backend.services.db_service import db_manager

router = APIRouter()

@router.get("/cameras")
def get_cameras():
    return db_manager.get_cameras()
