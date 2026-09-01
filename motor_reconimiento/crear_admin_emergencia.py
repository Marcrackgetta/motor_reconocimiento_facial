import hashlib
import time
import firebase_admin
from firebase_admin import credentials, db

try:
    # 1. Conexión con privilegios administrativos
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://motor-c7e0d-default-rtdb.firebaseio.com'
    })
    print("[SISTEMA] Conectado a Firebase exitosamente.")
except Exception as e:
    print(f"[ERROR] No se pudo conectar a Firebase: {e}")
    exit()

# 2. Credenciales de recuperación
nuevo_usuario = "marcelo_admin"
nueva_clave = "Sica2026!"

# 3. Encriptación matemática SHA-256
clave_hash = hashlib.sha256(nueva_clave.encode('utf-8')).hexdigest()

try:
    # 4. Magia NoSQL: Si "Administradores" no existe, Firebase lo crea aquí mismo
    ref = db.reference(f'Administradores/{nuevo_usuario}')
    
    ref.set({
        "clave_hash": clave_hash,
        "creado_por": "script_emergencia_python",
        "timestamp": int(time.time() * 1000)
    })
    
    print(f"✅ ¡ÉXITO! El nodo 'Administradores' y el usuario '{nuevo_usuario}' han sido reconstruidos en Firebase.")
    
except Exception as e:
    print(f"❌ Error al crear la estructura en Firebase: {e}")