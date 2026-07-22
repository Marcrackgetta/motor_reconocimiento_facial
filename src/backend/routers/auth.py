import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.backend.services.db_service import db_manager

router = APIRouter()

FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "AIzaSyBtX7uKiGBcJKANRZ4KLW3Tvge2NgDsmoU")

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(req: LoginRequest):
    # Validar con Firebase Authentication
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": req.email,
        "password": req.password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        token = data["idToken"]
        
        # Obtener rol
        rol = db_manager.get_user_role(req.email)
        if rol == "Desconocido":
            raise HTTPException(status_code=403, detail="Usuario sin rol asignado.")
            
        return {"token": token, "email": req.email, "rol": rol}
    else:
        error_msg = response.json().get("error", {}).get("message", "Verifique sus credenciales")
        raise HTTPException(status_code=401, detail=error_msg)
