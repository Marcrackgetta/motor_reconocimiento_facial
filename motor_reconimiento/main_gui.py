import os
import platform
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

if platform.system() == "Windows":
    import winsound

from pathlib import Path

from src.capture.camera_stream import CameraStream
from src.events.event_manager import EventManager

# CAMBIO: Importamos el nuevo cliente de Firebase
from src.network.firebase_client import FirebaseClient
from src.storage.file_manager import FileManager
from src.training.trainer import ModelTrainer
from src.utils.config import (
    BLUR_THRESHOLD,
    CAMERA_SOURCES,
    DATASET_DIR,
    INSIGHTFACE_REC_THRESH,
    MAX_PHOTOS_PER_PERSON,
    MODEL_PATH,
    RECONNECT_DELAY_SECONDS,
)
from src.vision.recognition_engine import RecognitionEngine
from src.vision.tracker import FaceTracker
from src.vision.vision_engine import VisionEngine


class FaceRecognitionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Motor de Reconocimiento Facial Edge")
        self.root.geometry("1100x650")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.running = True
        self.mode = "RECOGNIZE"
        self.identity_label = ""
        self.captured_photos = 0
        self.cooldown_time = 0.0
        self.current_imgtk = None

        self.active_camera_idx = 0
        self.view_mode = "SINGLE"
        self.streams = []

        self.zoom_factor = tk.DoubleVar(value=1.0)
        self.pan_x = tk.DoubleVar(value=0.0)
        self.pan_y = tk.DoubleVar(value=0.0)

        self.root.columnconfigure(0, weight=7)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        self.setup_ui()
        self.init_backend()
        self.update_frame()

    def setup_ui(self):
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.pack(expand=True, fill="both")

        self.control_frame = tk.Frame(self.root, bg="#2C3E50", padx=20, pady=20)
        self.control_frame.grid(row=0, column=1, sticky="nsew")

        lbl_title = tk.Label(self.control_frame, text="Panel de Control Edge", font=("Helvetica", 16, "bold"), bg="#2C3E50", fg="white")
        lbl_title.pack(pady=(0, 20))

        self.lbl_status = tk.Label(self.control_frame, text="Estado: Reconocimiento Activo", font=("Helvetica", 11), bg="#2C3E50", fg="#2ECC71")
        self.lbl_status.pack(pady=(0, 20))

        lbl_zoom = tk.Label(self.control_frame, text="Zoom Digital", font=("Helvetica", 10, "bold"), bg="#2C3E50", fg="#BDC3C7")
        lbl_zoom.pack(pady=(10, 0))
        self.zoom_slider = tk.Scale(self.control_frame, from_=1.0, to=4.0, resolution=0.1, orient="horizontal", variable=self.zoom_factor, bg="#2C3E50", fg="white", highlightthickness=0, troughcolor="#34495E", activebackground="#3498DB")
        self.zoom_slider.pack(fill="x", pady=(0, 10))

        lbl_pan_x = tk.Label(self.control_frame, text="Desplazamiento H. (Izquierda - Derecha)", font=("Helvetica", 9, "bold"), bg="#2C3E50", fg="#BDC3C7")
        lbl_pan_x.pack(pady=(5, 0))
        self.pan_x_slider = tk.Scale(self.control_frame, from_=-1.0, to=1.0, resolution=0.05, orient="horizontal", variable=self.pan_x, bg="#2C3E50", fg="white", highlightthickness=0, troughcolor="#34495E", activebackground="#3498DB")
        self.pan_x_slider.pack(fill="x", pady=(0, 5))

        lbl_pan_y = tk.Label(self.control_frame, text="Desplazamiento V. (Arriba - Abajo)", font=("Helvetica", 9, "bold"), bg="#2C3E50", fg="#BDC3C7")
        lbl_pan_y.pack(pady=(5, 0))
        self.pan_y_slider = tk.Scale(self.control_frame, from_=-1.0, to=1.0, resolution=0.05, orient="horizontal", variable=self.pan_y, bg="#2C3E50", fg="white", highlightthickness=0, troughcolor="#34495E", activebackground="#3498DB")
        self.pan_y_slider.pack(fill="x", pady=(0, 20))

        lbl_cams = tk.Label(self.control_frame, text="Selector de Cámara", font=("Helvetica", 10, "bold"), bg="#2C3E50", fg="#BDC3C7")
        lbl_cams.pack(pady=(10, 5))

        cam_options = [f"{cam.get('nombre', f'Cam {i}')} ({cam.get('camera_id', 'UNKNOWN')})" for i, cam in enumerate(CAMERA_SOURCES)]
        self.cam_var = tk.StringVar()
        self.cam_combo = ttk.Combobox(self.control_frame, textvariable=self.cam_var, values=cam_options, state="readonly", font=("Helvetica", 10))
        self.cam_combo.pack(fill="x", pady=5)
        if cam_options:
            self.cam_combo.current(0)
        self.cam_combo.bind("<<ComboboxSelected>>", self.on_camera_select)

        btn_grid = tk.Button(self.control_frame, text="Vista General (Todas)", bg="#9B59B6", fg="white", command=self.show_grid_view)
        btn_grid.pack(fill="x", pady=(0, 15))

        button_font = ("Helvetica", 12)
        self.btn_register = tk.Button(self.control_frame, text="Registrar Nuevo Usuario", font=button_font, bg="#3498DB", fg="white", command=self.start_registration)
        self.btn_register.pack(fill="x", pady=10, ipady=5)

        self.btn_train = tk.Button(self.control_frame, text="Actualizar Modelo", font=button_font, bg="#F39C12", fg="white", command=self.start_training)
        self.btn_train.pack(fill="x", pady=10, ipady=5)

        self.btn_quit = tk.Button(self.control_frame, text="Cerrar Programa", font=button_font, bg="#E74C3C", fg="white", command=self.on_closing)
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
        
        self.event_manager = EventManager()
        # CAMBIO: Inicializamos el cliente de Firebase
        self.api_client = FirebaseClient() 

        self.sender_thread = threading.Thread(target=self._event_sender_task, daemon=True)
        self.sender_thread.start()

        print("[INFO] Conectando a las cámaras...")
        for cam in CAMERA_SOURCES:
            stream = CameraStream(
                source=cam["src"],
                camera_id=cam.get("camera_id", "CAM_DEFAULT"),
                reconnect_delay=RECONNECT_DELAY_SECONDS,
            )
            self.streams.append(stream)

    def _event_sender_task(self):
        while self.running:
            pending_events = self.event_manager.get_pending_events()
            
            if pending_events:
                evento_actual = pending_events[0]
                success = self.api_client.send_event(evento_actual)
                
                if success:
                    self.event_manager.clear_events(1)
                else:
                    time.sleep(5)
            else:
                time.sleep(1)

    def switch_camera(self, idx):
        self.active_camera_idx = idx
        self.view_mode = "SINGLE"
        if platform.system() == "Windows":
            winsound.Beep(800, 100)

    def on_camera_select(self, event):
        idx = self.cam_combo.current()
        self.switch_camera(idx)

    def show_grid_view(self):
        self.view_mode = "GRID"
        if platform.system() == "Windows":
            winsound.Beep(850, 100)

    def create_connection_lost_frame(self):
        w = self.video_label.winfo_width()
        h = self.video_label.winfo_height()
        if w < 10 or h < 10:
            w, h = 640, 480
        display_frame = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(display_frame, "CONEXION PERDIDA", (w // 2 - 130, h // 2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(display_frame, "Intentando reconectar automaticamente...", (w // 2 - 210, h // 2 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return display_frame

    def update_frame(self):
        if not self.running:
            return

        display_frame = None

        if self.view_mode == "SINGLE":
            stream = self.streams[self.active_camera_idx]
            frame = stream.get_frame()

            if getattr(stream, "is_connected", True) and frame is not None:
                z = self.zoom_factor.get()
                if z > 1.0:
                    h, w = frame.shape[:2]
                    new_h, new_w = int(h / z), int(w / z)

                    max_shift_x = w - new_w
                    max_shift_y = h - new_h

                    pan_val_x = self.pan_x.get()
                    pan_val_y = self.pan_y.get()

                    x1 = int(max_shift_x * ((pan_val_x + 1.0) / 2.0))
                    y1 = int(max_shift_y * ((pan_val_y + 1.0) / 2.0))

                    x1 = max(0, min(x1, max_shift_x))
                    y1 = max(0, min(y1, max_shift_y))

                    cropped = frame[y1 : y1 + new_h, x1 : x1 + new_w]
                    frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

                display_frame = frame.copy()

                if self.mode == "RECOGNIZE":
                    display_frame = self.process_recognition(frame, display_frame)
                elif self.mode == "REGISTER":
                    display_frame = self.process_registration(frame, display_frame)
                elif self.mode == "TRAINING":
                    cv2.putText(display_frame, "Entrenando modelo... Por favor espere", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
            else:
                display_frame = self.create_connection_lost_frame()

        elif self.view_mode == "GRID":
            frames = []
            target_w, target_h = 320, 240

            for i, stream in enumerate(self.streams):
                f = stream.get_frame()

                if f is not None and getattr(stream, "is_connected", True):
                    proc_frame = f.copy()
                    if self.mode == "RECOGNIZE":
                        proc_frame = self.process_recognition(f, proc_frame, stream_idx=i)
                    elif self.mode == "REGISTER":
                        proc_frame = self.process_registration(f, proc_frame)
                    elif self.mode == "TRAINING":
                        cv2.putText(proc_frame, "Entrenando...", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
                    frames.append(cv2.resize(proc_frame, (target_w, target_h)))
                else:
                    blank = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                    cv2.putText(blank, "SIN CONEXION", (80, target_h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    frames.append(blank)

            if len(frames) == 1:
                display_frame = frames[0]
            elif len(frames) == 2:
                display_frame = np.hstack((frames[0], frames[1]))
            elif len(frames) == 3:
                blank = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                top = np.hstack((frames[0], frames[1]))
                bottom = np.hstack((frames[2], blank))
                display_frame = np.vstack((top, bottom))
            elif len(frames) >= 4:
                top = np.hstack((frames[0], frames[1]))
                bottom = np.hstack((frames[2], frames[3]))
                display_frame = np.vstack((top, bottom))

            cv2.putText(display_frame, "VISTA GENERAL", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if display_frame is not None:
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)

            label_w = self.video_label.winfo_width()
            label_h = self.video_label.winfo_height()

            if label_w > 10 and label_h > 10:
                img.thumbnail((label_w, label_h), Image.Resampling.LANCZOS)

            self.current_imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.configure(image=self.current_imgtk)

        self.root.after(16, self.update_frame)

    def process_recognition(self, frame, display_frame, stream_idx=None):
        if stream_idx is None:
            stream_idx = self.active_camera_idx
            
        stream = self.streams[stream_idx]
        camera_id = stream.camera_id

        context = self.vision_engine.detect(frame)
        context = self.tracker.update(context)
        
        context = self.recognition_engine.process(frame, context, self.vision_engine, camera_id)

        for face in context.faces:
            confidence = getattr(face, "confidence", 0.0)
            identity = getattr(face, "identity_uuid", "Calculando...")

            if identity == "unknown" or identity == "Desconocido":
                color = (0, 0, 255)
            elif identity == "Calculando...":
                color = (255, 255, 0)
            else:
                color = (0, 255, 0)
                self.event_manager.register_recognition(identity, camera_id)

            cv2.rectangle(display_frame, (face.left, face.top), (face.right, face.bottom), color, 2)

            display_id = identity[:15] if len(identity) > 15 else identity
            label = f"{display_id} ({confidence:.1f}%)" if confidence > 0 else f"{display_id}"
            cv2.putText(display_frame, label, (face.left, face.top - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

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
                color = (0, 0, 255)

                if blur_variance >= BLUR_THRESHOLD and (time.time() - self.cooldown_time > 0.4):
                    filename = os.path.join(self.person_dir, f"{self.identity_label}_{self.captured_photos:03d}.jpg")
                    cv2.imwrite(filename, face_crop)
                    self.captured_photos += 1
                    self.cooldown_time = time.time()
                    color = (0, 255, 0)

                    if platform.system() == "Windows":
                        winsound.Beep(1000, 150)

                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display_frame, f"Capturas: {self.captured_photos}/{MAX_PHOTOS_PER_PERSON}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            if self.captured_photos >= MAX_PHOTOS_PER_PERSON:
                if platform.system() == "Windows":
                    winsound.Beep(1500, 400)
                messagebox.showinfo("Éxito", f"Se registró el rostro a la Cédula: {self.identity_label}.")
                self.mode = "RECOGNIZE"
                self.update_ui_state("Estado: Reconocimiento Activo", "#2ECC71")

        elif len(faces) > 1:
            cv2.putText(display_frame, "ERROR: Multiples rostros detectados", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return display_frame

    def start_registration(self):
        if self.mode == "TRAINING":
            return

        codigo_institucional = simpledialog.askstring("Registro de Rostro", "Ingrese el número de Cédula (exactamente 10 dígitos numéricos):", parent=self.root)

        if not codigo_institucional or not codigo_institucional.strip():
            return
            
        codigo_limpio = codigo_institucional.strip()
        
        if not (len(codigo_limpio) == 10 and codigo_limpio.isdigit()):
            messagebox.showwarning("Error de Validación", "La cédula debe contener exactamente 10 dígitos numéricos.\nNo se aceptan letras, espacios ni otros caracteres.", parent=self.root)
            return

        self.identity_label = codigo_limpio
        self.person_dir = os.path.join(DATASET_DIR, self.identity_label)
        os.makedirs(self.person_dir, exist_ok=True)

        self.captured_photos = 0
        self.cooldown_time = time.time()
        self.mode = "REGISTER"
        
        self.update_ui_state(f"Estado: Registrando a {self.identity_label}...", "#3498DB")

    def start_training(self):
        if self.mode == "TRAINING":
            return

        confirm = messagebox.askyesno("Confirmar", "¿Desea iniciar el entrenamiento con los nuevos usuarios registrados?")

        if confirm:
            self.mode = "TRAINING"
            self.update_ui_state("Estado: Entrenando Modelo...", "#F39C12")
            threading.Thread(target=self._train_task, daemon=True).start()

    def _train_task(self):
        try:
            directories = FileManager.get_dataset_directories(DATASET_DIR)
            if not directories:
                self.root.after(0, lambda: messagebox.showerror("Error", "El directorio del dataset está vacío."))
                return

            trainer = ModelTrainer(detection_model="hog")
            model_data = trainer.train_from_directory(directories)

            if len(model_data["encodings"]) > 0:
                FileManager.save_model(model_data, MODEL_PATH)
                self.recognition_engine.known_encodings = model_data["encodings"]
                self.recognition_engine.known_names = model_data["names"]

                self.root.after(0, lambda: messagebox.showinfo("Éxito", "Modelo actualizado correctamente en el motor."))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "No se generaron embeddings."))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error de Entrenamiento", msg))
        finally:
            self.root.after(0, self._restore_recognition_mode)

    def _restore_recognition_mode(self):
        self.mode = "RECOGNIZE"
        self.update_ui_state("Estado: Reconocimiento Activo", "#2ECC71")

    def update_ui_state(self, text, color):
        self.lbl_status.config(text=text, fg=color)

    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Es seguro que deseas cerrar el programa?"):
            self.running = False
            for stream in self.streams:
                stream.release()
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    os.makedirs("src/events", exist_ok=True)
    os.makedirs("src/network", exist_ok=True)
    
    if not os.path.exists("src/events/__init__.py"):
        open("src/events/__init__.py", 'a').close()
    if not os.path.exists("src/network/__init__.py"):
        open("src/network/__init__.py", 'a').close()
        
    root = tk.Tk()
    app = FaceRecognitionGUI(root)
    root.mainloop()