import os
import cv2
import numpy as np
import hashlib
import logging
from pathlib import Path
from insightface.app import FaceAnalysis

from src.storage.file_manager import FileManager
from src.utils.config import MODEL_PATH, INSIGHTFACE_MODEL_PACK

class ModelTrainer:
    def __init__(self, *args, **kwargs):
        # Inicializamos el motor de InsightFace para la extracción
        self.app = FaceAnalysis(name=INSIGHTFACE_MODEL_PACK)
        self.app.prepare(ctx_id=0, det_size=(320, 320))

    def _calcular_hash(self, filepath):
        """Genera una firma criptográfica única (SHA-256) basada en los bytes de la imagen."""
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                # Leemos en fragmentos por si la imagen es muy pesada
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logging.error(f"[TRAINER] Error al calcular hash de {filepath}: {e}")
            return None

    def train_from_directory(self, directories):
        """
        Procesa el dataset de forma incremental:
        Solo extrae embeddings de fotos nuevas o modificadas.
        """
        logging.info("[TRAINER] Iniciando generación de embeddings incremental...")
        
        # 1. Cargar la memoria (caché) del procesamiento anterior
        modelo_antiguo = FileManager.load_model(Path(MODEL_PATH))
        cache_antigua = modelo_antiguo.get("cache_imagenes", {})
        
        nueva_cache = {}
        known_encodings = []
        known_names = []
        
        fotos_reutilizadas = 0
        fotos_procesadas = 0

        # 2. Recorrer cada estudiante (carpeta)
        for person_dir in directories:
            person_name = os.path.basename(person_dir)
            student_encodings = []

            # Recorrer cada fotografía del estudiante
            for image_name in os.listdir(person_dir):
                if not image_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                    
                image_path = os.path.join(person_dir, image_name)
                
                # Creamos una llave única para esta foto en la caché
                cache_key = f"{person_name}/{image_name}"
                
                # A. Calculamos la firma (Hash) de la foto actual
                file_hash = self._calcular_hash(image_path)
                if not file_hash:
                    continue
                
                # B. LÓGICA INCREMENTAL: ¿La foto ya fue procesada y no ha cambiado?
                if cache_key in cache_antigua and cache_antigua[cache_key].get("hash") == file_hash:
                    # REUTILIZAR: Saltamos el procesamiento pesado y usamos la memoria
                    student_encodings.append(cache_antigua[cache_key]["embedding"])
                    nueva_cache[cache_key] = cache_antigua[cache_key]
                    fotos_reutilizadas += 1
                    continue
                
                # C. PROCESAR: Si es nueva o se modificó, usamos InsightFace
                img = cv2.imread(image_path)
                if img is None:
                    continue
                    
                faces = self.app.get(img)
                if len(faces) >= 1:
                    # Tomamos el rostro principal (el más grande/centrado)
                    embedding = faces[0].embedding
                    student_encodings.append(embedding)
                    
                    # Guardamos en la nueva caché para el futuro
                    nueva_cache[cache_key] = {
                        "hash": file_hash,
                        "embedding": embedding
                    }
                    fotos_procesadas += 1

            # 3. Promediar los embeddings del estudiante y guardarlo en la lista final
            if student_encodings:
                avg_embedding = np.mean(student_encodings, axis=0)
                known_names.append(person_name)
                known_encodings.append(avg_embedding)

        logging.info(f"[TRAINER] Resumen: {fotos_reutilizadas} fotos recicladas de caché | {fotos_procesadas} fotos nuevas procesadas.")

        # Devolvemos el diccionario enriquecido. 
        # main_gui.py usará "names" y "encodings", ignorando "cache_imagenes".
        return {
            "names": known_names,
            "encodings": known_encodings,
            "cache_imagenes": nueva_cache
        }