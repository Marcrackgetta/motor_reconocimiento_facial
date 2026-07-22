from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.backend.services.db_service import db_manager
import logging

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Simula la validación de un token JWT o de Firebase.
    Para la fase de desarrollo, si el token no se provee, asignamos un usuario anónimo,
    pero si se usa, extrae el rol desde la base de datos.
    """
    if not credentials:
        # Modo de transición: algunos endpoints pueden estar sin token momentáneamente.
        return {"email": "anonimo@sistema.com", "rol": "Desconocido"}
    
    # En producción aquí se usaría: firebase_admin.auth.verify_id_token(credentials.credentials)
    # Por ahora simularemos con un token hardcodeado o el correo si pasamos el correo como token.
    token = credentials.credentials
    email = token if "@" in token else "admin@colegio.edu.ec" # Mock
    
    rol = db_manager.get_user_role(email)
    
    return {"email": email, "rol": rol}

class RequireRole:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: dict = Depends(get_current_user)):
        # Normalizar roles (minusculas)
        rol_usuario = user.get("rol", "").lower()
        roles_permitidos = [r.lower() for r in self.allowed_roles]
        
        # Administrador supremo siempre pasa (asumiendo rol: 'administrador')
        if "administrador" in rol_usuario:
            return user
            
        if rol_usuario not in roles_permitidos:
            raise HTTPException(
                status_code=403, 
                detail=f"Permisos insuficientes. Se requiere uno de: {self.allowed_roles}"
            )
        return user
