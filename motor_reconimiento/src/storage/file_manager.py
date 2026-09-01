import os
import pickle
import logging

class FileManager:
    @staticmethod
    def get_dataset_directories(dataset_dir):
        """Devuelve una lista con las rutas de las carpetas de los estudiantes."""
        dirs = []
        if os.path.exists(dataset_dir):
            for d in os.listdir(dataset_dir):
                path = os.path.join(dataset_dir, d)
                if os.path.isdir(path):
                    dirs.append(path)
        return dirs

    @staticmethod
    def load_model(model_path):
        """Carga el modelo de reconocimiento y la caché de imágenes desde el archivo .pkl."""
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logging.warning(f"[FILE MANAGER] No se pudo cargar el modelo anterior o está corrupto: {e}")
        
        # Si no existe o falla, devolvemos un diccionario base vacío
        return {"names": [], "encodings": [], "cache_imagenes": {}}

    @staticmethod
    def save_model(model_data, model_path):
        """Guarda los embeddings promediados y la caché actualizada."""
        try:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            logging.info(f"[FILE MANAGER] Modelo y caché guardados exitosamente en {model_path}")
        except Exception as e:
            logging.error(f"[FILE MANAGER] Error al guardar el modelo: {e}")