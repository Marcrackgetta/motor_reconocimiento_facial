import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk

import platform

if platform.system() == "Windows":
    import winsound

from pathlib import Path

from src.capture.camera_stream import CameraStream
from src.storage.file_manager import FileManager
from src.storage.firebase_manager import FirebaseManager
from src.utils.config import (
    CAMERA_SOURCES,
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

        # Variables de control operacional
        self.running = True
        self.mode = "RECOGNIZE"
        self.register_name = ""
        self.register_course = ""
        self.identity_label = ""
        self.captured_photos = 0
        self.cooldown_time = 0.0
        self.current_imgtk = None

        self.active_camera_idx = 0
        self.view_mode = "SINGLE"
        self.streams = []

        # Cooldown para registros redundantes en base de datos (10 minutos)
        self.cooldown_seconds = 600

        self.firebase = FirebaseManager()
        self.camera_sessions = {}

        self.active_tracks = {i: {} for i in range(len(CAMERA_SOURCES))}
        self.db_cooldowns = {i: {} for i in range(len(CAMERA_SOURCES))}

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

        lbl_title = tk.Label(
            self.control_frame,
            text="Panel de Control",
            font=("Helvetica", 16, "bold"),
            bg="#2C3E50",
            fg="white",
        )
        lbl_title.pack(pady=(0, 20))

        self.lbl_status = tk.Label(
            self.control_frame,
            text="Estado: Reconocimiento Activo",
            font=("Helvetica", 11),
            bg="#2C3E50",
            fg="#2ECC71",
        )
        self.lbl_status.pack(pady=(0, 20))

        lbl_zoom = tk.Label(
            self.control_frame,
            text="Zoom Digital",
            font=("Helvetica", 10, "bold"),
            bg="#2C3E50",
            fg="#BDC3C7",
        )
        lbl_zoom.pack(pady=(10, 0))

        self.zoom_slider = tk.Scale(
            self.control_frame,
            from_=1.0,
            to=4.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.zoom_factor,
            bg="#2C3E50",
            fg="white",
            highlightthickness=0,
            troughcolor="#34495E",
            activebackground="#3498DB",
        )
        self.zoom_slider.pack(fill="x", pady=(0, 10))

        lbl_pan_x = tk.Label(
            self.control_frame,
            text="Desplazamiento H.",
            font=("Helvetica", 9, "bold"),
            bg="#2C3E50",
            fg="#BDC3C7",
        )
        lbl_pan_x.pack(pady=(5, 0))

        self.pan_x_slider = tk.Scale(
            self.control_frame,
            from_=-1.0,
            to=1.0,
            resolution=0.05,
            orient="horizontal",
            variable=self.pan_x,
            bg="#2C3E50",
            fg="white",
            highlightthickness=0,
            troughcolor="#34495E",
            activebackground="#3498DB",
        )
        self.pan_x_slider.pack(fill="x", pady=(0, 5))

        lbl_pan_y = tk.Label(
            self.control_frame,
            text="Desplazamiento V.",
            font=("Helvetica", 9, "bold"),
            bg="#2C3E50",
            fg="#BDC3C7",
        )
        lbl_pan_y.pack(pady=(5, 0))

        self.pan_y_slider = tk.Scale(
            self.control_frame,
            from_=-1.0,
            to=1.0,
            resolution=0.05,
            orient="horizontal",
            variable=self.pan_y,
            bg="#2C3E50",
            fg="white",
            highlightthickness=0,
            troughcolor="#34495E",
            activebackground="#3498DB",
        )
        self.pan_y_slider.pack(fill="x", pady=(0, 20))

        lbl_cams = tk.Label(
            self.control_frame,
            text="Selector de Cámara/Curso",
            font=("Helvetica", 10, "bold"),
            bg="#2C3E50",
            fg="#BDC3C7",
        )
        lbl_cams.pack(pady=(10, 5))

        cam_options = [
            f"{cam.get('nombre', f'Cam {i}')} - {cam.get('curso_asignado', 'General')}"
            for i, cam in enumerate(CAMERA_SOURCES)
        ]
        self.cam_var = tk.StringVar()
        self.cam_combo = ttk.Combobox(
            self.control_frame,
            textvariable=self.cam_var,
            values=cam_options,
            state="readonly",
            font=("Helvetica", 10),
        )
        self.cam_combo.pack(fill="x", pady=5)
        if cam_options:
            self.cam_combo.current(0)
        self.cam_combo.bind("<<ComboboxSelected>>", self.on_camera_select)

        btn_grid = tk.Button(
            self.control_frame,
            text="Vista General (Todas)",
            bg="#9B59B6",
            fg="white",
            command=self.show_grid_view,
        )
        btn_grid.pack(fill="x", pady=(0, 15))

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
        print("[INFO] Inicializando núcleos y sub-motores de video...")
        model = FileManager.load_model(Path(MODEL_PATH))
        known_encodings = model.get("encodings", [])
        known_names = model.get("names", [])

        self.vision_engine = VisionEngine()
        self.trackers = [FaceTracker() for _ in CAMERA_SOURCES]
        self.recognition_engine = RecognitionEngine(
            known_encodings=known_encodings,
            known_names=known_names,
            threshold=INSIGHTFACE_REC_THRESH,
        )

        for i, cam in enumerate(CAMERA_SOURCES):
            stream = CameraStream(
                source=cam["src"], reconnect_delay=RECONNECT_DELAY_SECONDS
            )
            self.streams.append(stream)

            # NO iniciamos la sesión aquí. Solo preparamos el diccionario
            # Guardamos 'cam_info' para registrar la cámara más tarde cuando dé video.
            self.camera_sessions[i] = {"session_id": None, "cam_info": cam}

    def switch_camera(self, idx):
        self.active_camera_idx = idx
        self.view_mode = "SINGLE"
        if platform.system() == "Windows":
            winsound.Beep(800, 100)

    def on_camera_select(self, event):
        self.switch_camera(self.cam_combo.current())

    def show_grid_view(self):
        self.view_mode = "GRID"
        if platform.system() == "Windows":
            winsound.Beep(850, 100)

    def create_connection_lost_frame(self):
        w, h = (
            max(640, self.video_label.winfo_width()),
            max(480, self.video_label.winfo_height()),
        )
        display_frame = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(
            display_frame,
            "CONEXION PERDIDA",
            (w // 2 - 130, h // 2 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )
        return display_frame

    def update_frame(self):
        if not self.running:
            return

        for i, stream in enumerate(self.streams):
            # Si el stream tiene conexión pero la sesión en Firebase aún no se ha creado
            if (
                getattr(stream, "is_connected", False)
                and self.camera_sessions[i].get("session_id") is None
            ):
                # Confirmar que realmente ya llegó un fotograma
                if stream.get_frame() is not None:
                    print(
                        f"[INFO] Video detectado en la cámara {i}. Iniciando sesión en Firebase..."
                    )
                    session_id = self.firebase.iniciar_sesion_camara(
                        self.camera_sessions[i]["cam_info"],
                        known_names=self.recognition_engine.known_names,
                    )
                    self.camera_sessions[i]["session_id"] = session_id

        display_frame = None

        if self.view_mode == "SINGLE":
            stream = self.streams[self.active_camera_idx]
            frame = None
            try:
                frame = stream.get_frame()
            except Exception:
                pass

            if getattr(stream, "is_connected", True) and frame is not None:
                z = self.zoom_factor.get()
                if z > 1.0:
                    h, w = frame.shape[:2]
                    new_h, new_w = int(h / z), int(w / z)
                    max_shift_x, max_shift_y = w - new_w, h - new_h
                    x1 = max(
                        0,
                        min(
                            int(max_shift_x * ((self.pan_x.get() + 1.0) / 2.0)),
                            max_shift_x,
                        ),
                    )
                    y1 = max(
                        0,
                        min(
                            int(max_shift_y * ((self.pan_y.get() + 1.0) / 2.0)),
                            max_shift_y,
                        ),
                    )
                    frame = cv2.resize(
                        frame[y1 : y1 + new_h, x1 : x1 + new_w],
                        (w, h),
                        interpolation=cv2.INTER_LINEAR,
                    )

                display_frame = frame.copy()
                if self.mode == "RECOGNIZE":
                    display_frame = self.process_recognition(frame, display_frame)
                elif self.mode == "REGISTER":
                    display_frame = self.process_registration(frame, display_frame)
                elif self.mode == "TRAINING":
                    cv2.putText(
                        display_frame,
                        "Entrenando modelo... Por favor espere",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 165, 255),
                        2,
                    )
            else:
                display_frame = self.create_connection_lost_frame()

        elif self.view_mode == "GRID":
            frames = []
            target_w, target_h = 320, 240
            for i, stream in enumerate(self.streams):
                f = None
                try:
                    f = stream.get_frame()
                except Exception:
                    pass

                if f is not None and getattr(stream, "is_connected", True):
                    proc_frame = f.copy()
                    if self.mode == "RECOGNIZE":
                        proc_frame = self.process_recognition(
                            f, proc_frame, stream_idx=i
                        )
                    elif self.mode == "REGISTER":
                        proc_frame = self.process_registration(f, proc_frame)
                    frames.append(cv2.resize(proc_frame, (target_w, target_h)))
                else:
                    blank = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                    cv2.putText(
                        blank,
                        "SIN CONEXION",
                        (80, target_h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 255),
                        2,
                    )
                    frames.append(blank)

            if len(frames) == 1:
                display_frame = frames[0]
            elif len(frames) == 2:
                display_frame = np.hstack((frames[0], frames[1]))
            elif len(frames) == 3:
                blank = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                display_frame = np.vstack(
                    (np.hstack((frames[0], frames[1])), np.hstack((frames[2], blank)))
                )
            else:
                display_frame = np.vstack(
                    (
                        np.hstack((frames[0], frames[1])),
                        np.hstack((frames[2], frames[3])),
                    )
                )

        if display_frame is not None:
            img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
            lw, lh = (
                max(10, self.video_label.winfo_width()),
                max(10, self.video_label.winfo_height()),
            )
            img.thumbnail((lw, lh), Image.Resampling.LANCZOS)
            self.current_imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.configure(image=self.current_imgtk)

        self.root.after(16, self.update_frame)

    def process_recognition(self, frame, display_frame, stream_idx=None):
        if stream_idx is None:
            stream_idx = self.active_camera_idx

        context = self.vision_engine.detect(frame)
        context = self.trackers[stream_idx].update(context)
        context = self.recognition_engine.process(frame, context, self.vision_engine)

        session_info = self.camera_sessions.get(stream_idx, {})
        session_id = session_info.get("session_id")

        try:
            camara_activa = CAMERA_SOURCES[stream_idx]
            curso_actual = camara_activa.get("curso_asignado", "")
        except IndexError:
            camara_activa = {}
            curso_actual = ""

        curso_actual_norm = curso_actual.lower().replace("_", " ").strip()
        current_track_ids = set()

        for face in context.faces:
            track_id = getattr(face, "track_id", None)
            if track_id is None:
                continue

            current_track_ids.add(track_id)
            confidence = getattr(face, "confidence", 0.0)
            identity = getattr(face, "identity", "Calculando...")
            estado_txt = ""
            tipo_registro = "DESCONOCIDO"

            if identity == "Desconocido":
                color = (0, 0, 255)
                tipo_registro = "DESCONOCIDO"
            elif identity == "Calculando...":
                color = (255, 255, 0)
            else:
                ident_norm = identity.lower().replace("_", " ").strip()
                is_valid = False
                if curso_actual_norm == "" or curso_actual_norm in ident_norm:
                    is_valid = True
                else:
                    partes = identity.rsplit("_", 1)
                    if len(partes) == 2:
                        curso_reg_norm = partes[0].lower().replace("_", " ").strip()
                        if curso_reg_norm and (
                            curso_reg_norm in curso_actual_norm
                            or curso_actual_norm in curso_reg_norm
                        ):
                            is_valid = True

                if is_valid:
                    color = (0, 255, 0)
                    estado_txt = " [PRESENTE]"
                    tipo_registro = "PRESENTE"
                else:
                    color = (0, 165, 255)
                    estado_txt = " [INTRUSO]"
                    tipo_registro = "INTRUSO"

            # Transacciones dinámicas hacia la subcolección unificada
            if identity != "Calculando..." and session_id:
                cooldown_key = (
                    identity if identity != "Desconocido" else f"DESC_{track_id}"
                )

                if track_id not in self.active_tracks[stream_idx]:
                    last_db_time = self.db_cooldowns[stream_idx].get(cooldown_key, 0)
                    doc_id = None

                    if time.time() - last_db_time > self.cooldown_seconds:
                        custom_id = (
                            f"INTRUSO_{identity}"
                            if tipo_registro == "INTRUSO"
                            else identity
                        )

                        # Mapea y actualiza directamente la subcolección usando el nuevo ID compuesto
                        print(f"DEBUG UI -> DB: Enviando identidad {identity}")
                        doc_id = self.firebase.registrar_deteccion(
                            session_id=session_id,
                            identidad=identity,
                            estado=tipo_registro,
                            confianza=confidence,
                            camara_info=camara_activa,
                            custom_doc_id=custom_id,
                            known_names=self.recognition_engine.known_names,
                        )

                    self.active_tracks[stream_idx][track_id] = {
                        "doc_id": doc_id,
                        "cooldown_key": cooldown_key,
                        "tipo": tipo_registro,
                        "start_time": time.time(),
                        "last_seen": time.time(),
                        "missed_frames": 0,
                        "best_identity": identity,
                    }
                    self.db_cooldowns[stream_idx][cooldown_key] = time.time()

                else:
                    track_data = self.active_tracks[stream_idx][track_id]
                    track_data["missed_frames"] = 0
                    track_data["last_seen"] = time.time()

                    if (
                        track_data["best_identity"] == "Desconocido"
                        and identity != "Desconocido"
                    ):
                        track_data["best_identity"] = identity
                        track_data["cooldown_key"] = identity
                        track_data["tipo"] = tipo_registro

                        last_db_time = self.db_cooldowns[stream_idx].get(identity, 0)
                        if time.time() - last_db_time > self.cooldown_seconds:
                            custom_id = (
                                f"INTRUSO_{identity}"
                                if tipo_registro == "INTRUSO"
                                else identity
                            )

                            doc_id = self.firebase.registrar_deteccion(
                                session_id=session_id,
                                identidad=identity,
                                estado=tipo_registro,
                                confianza=confidence,
                                camara_info=camara_activa,
                                custom_doc_id=custom_id,
                                known_names=self.recognition_engine.known_names,
                            )
                            track_data["doc_id"] = doc_id

                    self.db_cooldowns[stream_idx][track_data["cooldown_key"]] = (
                        time.time()
                    )

            # Renderizado visual en pantalla
            cv2.rectangle(
                display_frame,
                (face.left, face.top),
                (face.right, face.bottom),
                color,
                2,
            )
            partes = identity.split()
            if len(partes) >= 2:
                nombre_mostrar = " ".join(partes[-2:])
            else:
                nombre_mostrar = identity

            if confidence > 0:
                label = f"{nombre_mostrar}{estado_txt} ({confidence:.1f}%)"
            else:
                label = f"{nombre_mostrar}{estado_txt}"
            cv2.putText(
                display_frame,
                label,
                (face.left, face.top - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

        # Evaluar salidas de escena para cerrar métricas de permanencia
        expired_track_ids = []
        for t_id, track_data in self.active_tracks[stream_idx].items():
            if t_id not in current_track_ids:
                track_data["missed_frames"] = track_data.get("missed_frames", 0) + 1
                if track_data["missed_frames"] > 30:
                    expired_track_ids.append(t_id)

        for t_id in expired_track_ids:
            track_data = self.active_tracks[stream_idx].pop(t_id)
            if (
                track_data.get("tipo") == "INTRUSO"
                and track_data.get("doc_id")
                and session_id
            ):
                duration = round(
                    track_data.get("last_seen", time.time())
                    - track_data.get("start_time", time.time()),
                    2,
                )
                if duration > 0:
                    self.firebase.actualizar_duracion_intruso(
                        session_id=session_id,
                        doc_id=track_data.get("doc_id"),
                        duracion=duration,
                        identidad=track_data.get("best_identity"),
                    )

        return display_frame

    def process_registration(self, frame, display_frame):
        faces = self.vision_engine.app.get(frame)
        if len(faces) == 1:
            box = faces[0].bbox.astype(int)
            x1, y1, x2, y2 = (
                max(0, box[0]),
                max(0, box[1]),
                min(frame.shape[1], box[2]),
                min(frame.shape[0], box[3]),
            )
            face_crop = frame[y1:y2, x1:x2]

            if face_crop.size > 0:
                blur_variance = cv2.Laplacian(
                    cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F
                ).var()
                color = (0, 0, 255)

                if blur_variance >= BLUR_THRESHOLD and (
                    time.time() - self.cooldown_time > 0.4
                ):
                    cv2.imwrite(
                        os.path.join(
                            self.person_dir,
                            f"{self.identity_label}_{self.captured_photos:03d}.jpg",
                        ),
                        face_crop,
                    )
                    self.captured_photos += 1
                    self.cooldown_time = time.time()
                    color = (0, 255, 0)
                    if platform.system() == "Windows":
                        winsound.Beep(1000, 150)

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
                    f"Se registraron {MAX_PHOTOS_PER_PERSON} fotos para {self.identity_label}.",
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
            "Registro",
            "Ingrese el nombre del cadete (ej. Juan_Perez):",
            parent=self.root,
        )
        if not name or not name.strip():
            return
        course = simpledialog.askstring(
            "Registro", "Ingrese el curso (ej. 2_Informatica_B):", parent=self.root
        )
        if not course or not course.strip():
            return

        self.register_name, self.register_course = name.strip(), course.strip()
        self.identity_label = f"{self.register_course}_{self.register_name}"
        self.person_dir = os.path.join(DATASET_DIR, self.identity_label)
        os.makedirs(self.person_dir, exist_ok=True)

        self.captured_photos = 0
        self.cooldown_time = time.time()
        self.mode = "REGISTER"
        self.update_ui_state(f"Estado: Registrando {self.identity_label}...", "#3498DB")

    def start_training(self):
        if self.mode == "TRAINING":
            return
        if messagebox.askyesno(
            "Confirmar",
            "¿Desea iniciar el entrenamiento con los nuevos usuarios registrados?",
        ):
            self.mode = "TRAINING"
            self.update_ui_state("Estado: Entrenando Modelo...", "#F39C12")
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
            self.root.after(
                0,
                lambda msg=str(e): messagebox.showerror("Error de Entrenamiento", msg),
            )
        finally:
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
            for stream in self.streams:
                stream.release()

            print("[INFO] Finalizando registros de permanencia activos de intrusos...")
            for stream_idx, tracks in self.active_tracks.items():
                session_info = self.camera_sessions.get(stream_idx, {})
                session_id = session_info.get("session_id")

                if session_id:
                    for t_id, track_data in tracks.items():
                        if track_data.get("tipo") == "INTRUSO" and track_data.get(
                            "doc_id"
                        ):
                            duration = round(
                                time.time() - track_data.get("start_time", time.time()),
                                2,
                            )
                            self.firebase.actualizar_duracion_intruso(
                                session_id=session_id,
                                doc_id=track_data.get("doc_id"),
                                duracion=duration,
                                identidad=track_data.get("best_identity"),
                            )

            print(
                "[INFO] Inyectando hora de fin en subcolecciones y cerrando canales..."
            )
            for i, session_info in self.camera_sessions.items():
                if session_info:
                    session_id = session_info.get("session_id")
                    if session_id:
                        self.firebase.cerrar_sesion_camara(session_id=session_id)

            self.root.destroy()
            sys.exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = FaceRecognitionGUI(root)
    root.mainloop()
