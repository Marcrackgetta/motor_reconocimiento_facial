import time
import logging
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware de limitación de tasa (Rate Limiting) para prevenir 
    ataques de fuerza bruta en /login y denegación de servicio.
    """
    def __init__(self, app, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_history: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next):
        # Aplicar Rate Limiting solo en endpoints sensibles (ej. /login)
        if request.url.path == "/login" and request.method == "POST":
            client_ip = request.client.host if request.client else "127.0.0.1"
            now = time.time()
            
            # Limpiar historial viejo de peticiones fuera de la ventana de tiempo
            timestamps = self.request_history.get(client_ip, [])
            timestamps = [t for t in timestamps if now - t < self.window_seconds]
            
            if len(timestamps) >= self.max_requests:
                logging.warning(f"Rate limit excedido para IP: {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demasiados intentos de inicio de sesión. Por favor espere un minuto."}
                )

            timestamps.append(now)
            self.request_history[client_ip] = timestamps

        response = await call_next(request)
        return response
