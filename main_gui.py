import os
import sys
import time
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
import cv2
from PIL import Image, ImageTk

# Soporte opcional para feedback de audio en Windows
import platform

if platform.system() == "Windows":
    import winsound

from pathlib import Path

from src.capture.camera_stream import CameraStream
from src.storage.file_manager import FileManager
from src.utils.config import (
    CAMERA_URL,
    RECONNECT_DELAY_SECONDS,
    MODEL_PATH,
    INSIGHTFACE_REC_THRESH,
    DATASET_DIR,
    MAX_PHOTOS_PER_PERSON,
    BLUR_THRESHOLD,
)
from src.vision.vision_engine import VisionEngine
from src.vision.tracker import FaceTracker
from src.vision.recognition_engine import RecognitionEngine
from src.training.trainer import ModelTrainer


class FaceRecognitionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Motor de Reconocimiento Facial")
        self.root.geometry("1100x650")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Variables de estado
        self.running = True
        self.mode = "RECOGNIZE"  # Modos: RECOGNIZE, REGISTER, TRAINING
        self.register_name = ""
        self.captured_photos = 0
        self.cooldown_time = 0.0
        self.current_imgtk = None  # Almacena la referencia de la imagen para Tkinter

        # Configurar la cuadrícula: 70% video (col 0), 30% controles (col 1)
        self.root.columnconfigure(0, weight=7)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        self.setup_ui()
        self.init_backend()

        # Iniciar bucle de actualización de video
        self.update_frame()

    def setup_ui(self):
        # Panel de Video (Izquierda - 70%)
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew")

        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.pack(expand=True, fill="both")

        # Panel de Controles (Derecha - 30%)
        self.control_frame = tk.Frame(self.root, bg="#2C3E50", padx=20, pady=20)
        self.control_frame.grid(row=0, column=1, sticky="nsew")

        # Título del panel
        lbl_title = tk.Label(
            self.control_frame,
            text="Panel de Control",
            font=("Helvetica", 16, "bold"),
            bg="#2C3E50",
            fg="white",
        )
        lbl_title.pack(pady=(0, 30))

        # Indicador de estado actual
        self.lbl_status = tk.Label(
            self.control_frame,
            text="Estado: Reconocimiento Activo",
            font=("Helvetica", 11),
            bg="#2C3E50",
            fg="#2ECC71",
        )
        self.lbl_status.pack(pady=(0, 20))

        # Botones
        button_font = ("Helvetica", 12)

        self.btn_register = tk.Button(
            self.control_frame,
            text="Registrar Nuevo Usuario",
            font=button_font,
            bg="#3498DB",
            fg="white",
            command=self.start_registration,
        )
        self.btn_register.pack(fill="x", pady=10, ipady=5)

        self.btn_train = tk.Button(
            self.control_frame,
            text="Actualizar Modelo",
            font=button_font,
            bg="#F39C12",
            fg="white",
            command=self.start_training,
        )
        self.btn_train.pack(fill="x", pady=10, ipady=5)

        self.btn_quit = tk.Button(
            self.control_frame,
            text="Cerrar Programa",
            font=button_font,
            bg="#E74C3C",
            fg="white",
            command=self.on_closing,
        )
        self.btn_quit.pack(fill="x", pady=10, ipady=5)

    def init_backend(self):
        print("[INFO] Cargando modelo y motores de visión...")
        model = FileManager.load_model(Path(MODEL_PATH))
        known_encodings = model.get("encodings", [])
        known_names = model.get("names", [])

        self.vision_engine = VisionEngine()
        self.tracker = FaceTracker()
        self.recognition_engine = RecognitionEngine(
            known_encodings=known_encodings,
            known_names=known_names,
            threshold=INSIGHTFACE_REC_THRESH,
        )

        print(f"[INFO] Conectando a la cámara: {CAMERA_URL}")
        self.stream = CameraStream(
            url=CAMERA_URL, reconnect_delay=RECONNECT_DELAY_SECONDS
        )

    def update_frame(self):
        if not self.running:
            return

        frame = self.stream.get_frame()

        if frame is not None:
            display_frame = frame.copy()

            if self.mode == "RECOGNIZE":
                display_frame = self.process_recognition(frame, display_frame)
            elif self.mode == "REGISTER":
                display_frame = self.process_registration(frame, display_frame)
            elif self.mode == "TRAINING":
                # Mostrar overlay de entrenamiento
                cv2.putText(
                    display_frame,
                    "Entrenando modelo... Por favor espere",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 165, 255),
                    2,
                )

            # Convertir de BGR a RGB para Tkinter
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)

            # Redimensionar la imagen para que encaje mejor en la UI manteniendo proporción
            label_w = self.video_label.winfo_width()
            label_h = self.video_label.winfo_height()
            if label_w > 10 and label_h > 10:
                img.thumbnail((label_w, label_h), Image.Resampling.LANCZOS)

            # Corrección aplicada para Pylance: guardando la referencia de forma segura en la clase
            self.current_imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.configure(image=self.current_imgtk)

        # Solicitar el siguiente fotograma (~60 FPS máximo)
        self.root.after(16, self.update_frame)

    def process_recognition(self, frame, display_frame):
        # 1. Detección
        context = self.vision_engine.detect(frame)
        # 2. Tracking
        context = self.tracker.update(context)
        # 3. Reconocimiento
        context = self.recognition_engine.process(frame, context, self.vision_engine)

        for face in context.faces:
            color = (
                (0, 255, 0)
                if getattr(face, "identity", "") != "Desconocido"
                else (0, 0, 255)
            )
            confidence = getattr(face, "confidence", 0.0)
            identity = getattr(face, "identity", "Calculando...")

            cv2.rectangle(
                display_frame,
                (face.left, face.top),
                (face.right, face.bottom),
                color,
                2,
            )
            label = (
                f"{identity} ({confidence:.1f}%)" if confidence > 0 else f"{identity}"
            )
            cv2.putText(
                display_frame,
                label,
                (face.left, face.top - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

        return display_frame

    def process_registration(self, frame, display_frame):
        faces = self.vision_engine.app.get(frame)

        if len(faces) == 1:
            face = faces[0]
            box = face.bbox.astype(int)
            x1, y1, x2, y2 = box

            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            face_crop = frame[y1:y2, x1:x2]

            if face_crop.size > 0:
                gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                blur_variance = cv2.Laplacian(gray_crop, cv2.CV_64F).var()
                color = (0, 0, 255)  # Rojo indicando desenfoque o espera

                if blur_variance >= BLUR_THRESHOLD and (
                    time.time() - self.cooldown_time > 0.4
                ):
                    filename = os.path.join(
                        self.person_dir,
                        f"{self.register_name}_{self.captured_photos:03d}.jpg",
                    )
                    cv2.imwrite(filename, face_crop)
                    self.captured_photos += 1
                    self.cooldown_time = time.time()
                    color = (0, 255, 0)  # Verde al capturar

                    if platform.system() == "Windows":
                        winsound.Beep(1000, 150)  # Feedback auditivo de captura exitosa

                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    display_frame,
                    f"Capturas: {self.captured_photos}/{MAX_PHOTOS_PER_PERSON}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )

            if self.captured_photos >= MAX_PHOTOS_PER_PERSON:
                if platform.system() == "Windows":
                    winsound.Beep(1500, 400)
                messagebox.showinfo(
                    "Éxito",
                    f"Se registraron {MAX_PHOTOS_PER_PERSON} fotos para {self.register_name}.",
                )
                self.mode = "RECOGNIZE"
                self.update_ui_state("Estado: Reconocimiento Activo", "#2ECC71")

        elif len(faces) > 1:
            cv2.putText(
                display_frame,
                "ERROR: Multiples rostros detectados",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        return display_frame

    def start_registration(self):
        if self.mode == "TRAINING":
            return

        name = simpledialog.askstring(
            "Registrar Nuevo Usuario",
            "Ingrese el nombre de la persona (ej. Juan_Perez):",
            parent=self.root,
        )
        if name and name.strip():
            self.register_name = name.strip()
            self.person_dir = os.path.join(DATASET_DIR, self.register_name)
            os.makedirs(self.person_dir, exist_ok=True)
            self.captured_photos = 0
            self.cooldown_time = time.time()
            self.mode = "REGISTER"
            self.update_ui_state("Estado: Capturando Rostro...", "#3498DB")

    def start_training(self):
        if self.mode == "TRAINING":
            return

        confirm = messagebox.askyesno(
            "Confirmar",
            "¿Desea iniciar el entrenamiento con los nuevos usuarios registrados?",
        )
        if confirm:
            self.mode = "TRAINING"
            self.update_ui_state("Estado: Entrenando Modelo...", "#F39C12")
            # Se ejecuta en un hilo separado para evitar que la interfaz visual se congele
            threading.Thread(target=self._train_task, daemon=True).start()

    def _train_task(self):
        try:
            directories = FileManager.get_dataset_directories(DATASET_DIR)
            if not directories:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error", "El directorio del dataset está vacío."
                    ),
                )
                return

            trainer = ModelTrainer(detection_model="hog")
            model_data = trainer.train_from_directory(directories)

            if len(model_data["encodings"]) > 0:
                FileManager.save_model(model_data, MODEL_PATH)

                # Actualizar el motor de reconocimiento en memoria sin reiniciar
                self.recognition_engine.known_encodings = model_data["encodings"]
                self.recognition_engine.known_names = model_data["names"]

                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Éxito", "Modelo actualizado correctamente en el motor."
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error", "No se generaron embeddings."
                    ),
                )

        except Exception as e:
            # Corrección aplicada para Ruff: guardando la variable en el ámbito correcto
            error_msg = str(e)
            self.root.after(
                0,
                lambda msg=error_msg: messagebox.showerror(
                    "Error de Entrenamiento", msg
                ),
            )
        finally:
            # Regresar al modo reconocimiento de forma segura desde el hilo
            self.root.after(0, self._restore_recognition_mode)

    def _restore_recognition_mode(self):
        self.mode = "RECOGNIZE"
        self.update_ui_state("Estado: Reconocimiento Activo", "#2ECC71")

    def update_ui_state(self, text, color):
        self.lbl_status.config(text=text, fg=color)

    def on_closing(self):
        if messagebox.askokcancel(
            "Salir", "¿Estás seguro que deseas cerrar el programa?"
        ):
            self.running = False
            self.stream.release()
            self.root.destroy()
            sys.exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = FaceRecognitionGUI(root)
    root.mainloop()
