import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Por defecto usamos SQLite para desarrollo local (es gratis y no requiere instalación extra).
# Para producción en PostgreSQL, solo cambiaremos esta URL de entorno.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sica_local.db")

# connect_args solo es necesario para SQLite (para permitir múltiples hilos)
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

# Motor de conexión a la base de datos
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# Creador de sesiones de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base de la que heredarán nuestros modelos
Base = declarative_base()

# Función para obtener la sesión de la base de datos en nuestras rutas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()