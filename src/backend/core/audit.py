import logging
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.backend.services.db_service import db_manager
from datetime import datetime

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extraer info antes
        method = request.method
        path = request.url.path
        
        response = await call_next(request)
        
        # Solo registrar mutaciones (POST, PUT, DELETE, PATCH)
        # y que no sean las rutinarias de IA para no saturar los logs
        if method in ["POST", "PUT", "DELETE", "PATCH"] and not path.startswith("/ai/"):
            user = "anonimo"
            # Intento rudimentario de sacar el usuario si existe (en un entorno real se extrae del Request State)
            if hasattr(request.state, "user"):
                user = request.state.user.get("email", user)
                
            status_code = response.status_code
            
            # Registrar en DB
            if db_manager.db:
                try:
                    doc_ref = db_manager.db.collection("AuditLogs").document()
                    doc_ref.set({
                        "id": doc_ref.id,
                        "timestamp": datetime.now().isoformat(),
                        "method": method,
                        "path": path,
                        "user": user,
                        "status_code": status_code
                    })
                except Exception as e:
                    logging.error(f"Error escribiendo AuditLog: {e}")
                    
        return response
