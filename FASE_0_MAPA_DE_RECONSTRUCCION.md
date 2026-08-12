# FASE 0 — MAPA DE RECONSTRUCCIÓN DEL PROYECTO SICA

**Estado:** Análisis completo del repositorio legado  
**Fecha:** 2026-08-10  
**Fuentes analizadas:**
- SDD (`Documento de Diseño del Sistema SICA.md`) — AUTORIDAD MÁXIMA
- `RUMBO_TECNICO_DEFINITIVO.md` — DIRECCIÓN TÉCNICA
- Repositorio legado: `github.com/Marcrackgetta/motor_reconocimiento_facial` — FUENTE DE EVIDENCIA

**Convenciones de este documento:**
- `HECHO OBSERVADO` — Verificado directamente en el código fuente
- `INFERENCIA` — Deducción razonable basada en el código, no verificada en ejecución
- `DEFINIDO POR SDD` — Decisión establecida en el SDD
- `DEFINIDO POR RUMBO TÉCNICO` — Decisión establecida en RUMBO_TECNICO_DEFINITIVO.md
- `RECOMENDACIÓN` — Sugerencia del análisis, sujeta a aprobación

---

## 1. RESUMEN EJECUTIVO

### Estado real del proyecto legado

El repositorio `motor_reconocimiento_facial` contiene un **sistema funcional de reconocimiento facial** con capacidad multicámara, tracking persistente (ByteTrack), reconocimiento asíncrono (InsightFace/ArcFace) y un backend FastAPI parcialmente implementado con persistencia en Firebase/Firestore.

**Lo que funciona técnicamente bien:**
- El pipeline de visión artificial: SCRFD → ByteTrack → ArcFace está bien desacoplado internamente y utiliza estrategias inteligentes de optimización (detección separada de extracción, caché de identidades, ThreadPoolExecutor para reconocimiento).
- La captura de cámaras mediante hilos independientes con mutex.
- El tracking por cámara con instancias independientes de ByteTrack.
- El entrenamiento con consolidación por promediado de embeddings.

**Lo que está arquitectónicamente mal:**
- `main_gui.py` es un **God Object** que contiene: GUI (Tkinter), máquina de estados de tracks, lógica de negocio (PRESENTE/INTRUSO/DESCONOCIDO), persistencia (Firebase/API), renderizado visual, entrenamiento y coordinación multicámara.
- Existe **duplicación de reglas de negocio** entre `main_gui.py` (Edge), `firebase_manager.py` (Storage) y `event_processor.py` (Backend).
- La identidad está codificada como **strings concatenados** (`2_Informatica_B_Juan_Perez`), mezclando curso + nombre en un solo campo.
- Firebase y API REST coexisten en el mismo código base sin separación clara.
- El backend FastAPI (existente) todavía depende de Firebase como base de datos.
- Flutter coexiste como frontend descartado pero aún presente en el repositorio.

### Veredicto

El repositorio contiene **lógica valiosa rescatable** en el motor de visión, tracking y reconocimiento. La arquitectura general necesita **reconstrucción completa**, no refactorización. El conocimiento técnico del Edge debe preservarse; la estructura que lo contiene debe reemplazarse.

---

## 2. ARQUITECTURA REAL DEL REPOSITORIO (Durante ejecución)

### Lo que realmente ocurre al ejecutar `main_gui.py`:

```text
┌────────────────────────────────────────────────────────────┐
│                    main_gui.py (GOD OBJECT)                │
│                                                            │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Tkinter │  │ Máquina  │  │ Reglas   │  │ Firebase/ │  │
│  │   GUI   │  │ de       │  │ de       │  │ API REST  │  │
│  │         │  │ Estados  │  │ Negocio  │  │ Client    │  │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│       │            │             │               │        │
│  ┌────▼────────────▼─────────────▼───────────────▼────┐   │
│  │              update_frame() [LOOP 30ms]            │   │
│  │                                                    │   │
│  │  Para cada cámara:                                 │   │
│  │    CameraStream.get_frame_with_id()                │   │
│  │         ↓                                          │   │
│  │    VisionEngine.detect(frame)    ← SCRFD           │   │
│  │         ↓                                          │   │
│  │    FaceTracker.update(context)   ← ByteTrack       │   │
│  │         ↓                                          │   │
│  │    RecognitionEngine.process()   ← ArcFace/Caché   │   │
│  │         ↓                                          │   │
│  │    [LÓGICA INLINE]                                 │   │
│  │    - Determinar PRESENTE/INTRUSO/DESCONOCIDO       │   │
│  │    - Gestionar active_tracks[cam_idx]              │   │
│  │    - Aplicar db_cooldowns[cam_idx]                 │   │
│  │    - Registrar en Firebase/API                     │   │
│  │    - Renderizar overlays en frame                  │   │
│  │    - Gestionar tracks expirados (missed_frames>30) │   │
│  │         ↓                                          │   │
│  │    Mostrar en Tkinter Label                        │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌──────────────┐    ┌───────────────────┐
│ CameraStream │    │  Backend FastAPI   │
│ (hilos       │    │  (parcialmente     │
│  independ.)  │    │   implementado,    │
│              │    │   depende de       │
│              │    │   Firestore)       │
└──────────────┘    └───────────────────┘
```

### Nota importante sobre la estructura del repositorio

`HECHO OBSERVADO`: El repositorio tiene **dos estructuras separadas**:

1. **`main_gui.py`** (raíz) + **`src/`** — El motor de reconocimiento Python (Edge)
2. **`control_acceso_app/`** — La app Flutter (DESCARTADA)
3. **`src/backend/`** — El backend FastAPI con Firestore

La URL del repositorio apunta a `control_acceso_app/` pero los archivos Python del motor están en la raíz y en `src/`.

---

## 3. FLUJO COMPLETO DE EJECUCIÓN

### Desde cámara hasta interfaz/persistencia:

```text
ETAPA 1 — CAPTURA
─────────────────
CameraStream (hilo daemon por cámara)
  └→ cv2.VideoCapture.read() en bucle continuo
  └→ Almacena latest_frame con threading.Lock
  └→ frame_id se incrementa en cada frame nuevo
  └→ Reconexión automática si la cámara se pierde

ETAPA 2 — OBTENCIÓN DE FRAME
─────────────────────────────
main_gui.update_frame() [cada 30ms via root.after()]
  └→ stream.get_frame_with_id() → copia segura del frame
  └→ Si frame_id == last_frame_ids[cam]: usa cached_display_frame
  └→ Si es frame nuevo: procesar

ETAPA 3 — DETECCIÓN (SCRFD)
────────────────────────────
VisionEngine.detect(frame)
  └→ SCRFD (320x320, CPU) detecta bounding boxes + landmarks
  └→ Retorna FrameContext con lista de DetectedFace
  └→ NO ejecuta ArcFace (solo detección espacial)
  └→ Tiempo típico: variable, medido con last_det_time

ETAPA 4 — TRACKING (ByteTrack)
───────────────────────────────
FaceTracker.update(context) [una instancia por cámara]
  └→ Convierte DetectedFace → sv.Detections
  └→ Truco: class_id = np.arange(len(faces)) para mapear índices
  └→ ByteTrack asigna/mantiene tracker_id
  └→ Remapea tracker_id a cada DetectedFace original
  └→ track_ids son LOCALES por instancia de tracker
      (pero main_gui NO usa camera_id+track_id compuesto)

ETAPA 5 — RECONOCIMIENTO (ArcFace + Caché)
────────────────────────────────────────────
RecognitionEngine.process(frame, context, vision_engine)
  └→ Para cada face con track_id:
      ├→ Si track_id está en caché y no ha expirado (3s): usar caché
      ├→ Si track_id es "Desconocido" con cooldown adaptativo:
      │     - ≤2 intentos: reintentar cada 1.5s
      │     - >2 intentos: reintentar cada 10s
      └→ Si necesita extracción:
            └→ ThreadPoolExecutor(max_workers=1)
            └→ Copia frame + face para thread-safety
            └→ VisionEngine.extract_embedding (ArcFace)
            └→ cosine_similarity contra known_encodings
            └→ Umbral: 0.45 (INSIGHTFACE_REC_THRESH)
            └→ Actualiza track_cache con identity + confidence

ETAPA 6 — ESTADO Y REGLAS DE NEGOCIO (dentro de main_gui)
──────────────────────────────────────────────────────────
process_recognition():
  └→ Para cada face reconocida:
      ├→ Si identity == "Desconocido": → DESCONOCIDO (rojo)
      ├→ Si identity == "Calculando...": → amarillo (espera)
      ├→ Si identity reconocida:
      │     ├→ Normalizar identity y curso_actual de la cámara
      │     ├→ Comparar curso de identity vs curso de cámara
      │     │   (mediante split("_") y comparación de strings)
      │     ├→ Si coincide: → PRESENTE (verde)
      │     └→ Si no coincide: → INTRUSO (naranja)
      └→ NOTA: Esta lógica usa comparación textual de strings,
         NO consulta al backend ni usa UUIDs

ETAPA 7 — GESTIÓN DE TRACKS (máquina de estados)
─────────────────────────────────────────────────
  └→ Si track_id NO está en active_tracks[cam_idx]:
      ├→ Verificar db_cooldowns (600s por identity)
      ├→ Si no hay cooldown activo:
      │     └→ firebase.registrar_deteccion() [asíncrono via API]
      ├→ Crear entrada en active_tracks con:
      │     doc_id, cooldown_key, tipo, start_time,
      │     last_seen, missed_frames=0, best_identity
      └→ Actualizar db_cooldowns[cam_idx][cooldown_key]

  └→ Si track_id YA está en active_tracks[cam_idx]:
      ├→ Reset missed_frames = 0
      ├→ Actualizar last_seen
      └→ Si identity mejoró (era "Desconocido", ahora tiene nombre):
            └→ Actualizar best_identity, tipo, y re-registrar

ETAPA 8 — EXPIRACIÓN DE TRACKS
───────────────────────────────
  └→ Para cada track en active_tracks que NO está en current_track_ids:
      ├→ Incrementar missed_frames
      └→ Si missed_frames > 30:
            ├→ Eliminar de active_tracks
            └→ Si era INTRUSO con doc_id:
                  └→ firebase.actualizar_duracion_intruso()

ETAPA 9 — RENDERIZADO
──────────────────────
  └→ Dibujar rectangles (color según estado) en display_frame
  └→ Extraer nombre legible: identity.split("_")[-2:]
  └→ Overlay: nombre + estado + confianza
  └→ FPS + tiempos de detección/reconocimiento
  └→ Convertir BGR→RGB, resize al label, ImageTk.PhotoImage
  └→ Cachear display_frame para frames repetidos

ETAPA 10 — PERSISTENCIA
────────────────────────
api_client.py (ThreadPoolExecutor max_workers=5):
  └→ POST /ai/session/start    (iniciar sesión cámara)
  └→ POST /ai/detection         (registrar detección)
  └→ POST /ai/intruder/duration (actualizar duración intruso)
  └→ POST /ai/session/end       (cerrar sesión)
  └→ Todas las llamadas son asíncronas (fire-and-forget)
  └→ NO hay cola local ni reintentos
  └→ NO hay manejo de servidor no disponible
```

---

## 4. MAPA DE DEPENDENCIAS

```text
main_gui.py
  ├── src.capture.camera_stream.CameraStream
  ├── src.vision.vision_engine.VisionEngine
  ├── src.vision.tracker.FaceTracker
  ├── src.vision.recognition_engine.RecognitionEngine
  ├── src.training.trainer.ModelTrainer
  ├── src.storage.file_manager.FileManager
  ├── src.storage.api_client.api_client  ← (alias: firebase_manager)
  └── src.utils.config.*

src.vision.recognition_engine
  ├── src.vision.frame_context.FrameContext
  └── src.vision.vision_engine.VisionEngine

src.vision.vision_engine
  ├── insightface.app.FaceAnalysis
  ├── src.vision.face_data.DetectedFace
  ├── src.vision.frame_context.FrameContext
  └── src.utils.config.*

src.vision.tracker
  ├── supervision.ByteTrack
  ├── src.vision.frame_context.FrameContext
  └── src.utils.config.*

src.training.trainer
  ├── src.vision.vision_engine.VisionEngine
  └── src.utils.config.*

src.storage.api_client
  └── requests (HTTP)

src.storage.firebase_manager
  ├── firebase_admin
  └── google.cloud.firestore

src.backend.services.event_processor
  └── src.backend.models.domain.*

src.backend.services.db_service
  ├── firebase_admin
  ├── google.cloud.firestore
  └── src.backend.services.event_processor
```

### Dependencias circulares: `HECHO OBSERVADO` — No se detectaron.

### Código muerto identificado:
- `src/vision/preprocessing.py` — No es importado por ningún módulo en producción (`HECHO OBSERVADO`)
- `src/vision/interfaces.py` — No es importado por ningún módulo en producción (`HECHO OBSERVADO`)
- `src/vision/factory.py` — Define factory pero no es utilizado en main_gui.py (`HECHO OBSERVADO`)
- `src/scripts/migrate_firestore.py` — Script de migración, no se usa en runtime (`HECHO OBSERVADO`)
- Toda la carpeta `control_acceso_app/` (Flutter) — DESCARTADA (`DEFINIDO POR RUMBO TÉCNICO`)

---

## 5. INVENTARIO COMPLETO DE COMPONENTES

| Componente | Responsabilidad actual | Valor técnico | Acción | Destino en SDD |
|---|---|---|---|---|
| `main_gui.py` | God Object: GUI + estado + negocio + persistencia + render | ALTO (lógica) / BAJO (estructura) | **DESCOMPONER** | Ver sección 6 |
| `src/capture/camera_stream.py` | Captura de frames en hilo daemon con Lock | ALTO | CONSERVAR | `motor_reconocimiento/capture/camera_stream.py` |
| `src/vision/vision_engine.py` | Detección SCRFD + extracción ArcFace | ALTO | CONSERVAR | `motor_reconocimiento/vision/engine.py` |
| `src/vision/tracker.py` | ByteTrack wrapper con mapeo class_id→índice | ALTO | CONSERVAR | `motor_reconocimiento/vision/tracker.py` |
| `src/vision/recognition_engine.py` | Reconocimiento con caché + ThreadPool | ALTO | REFACTORIZAR | `motor_reconocimiento/vision/recognizer.py` |
| `src/vision/face_data.py` | DTO DetectedFace (dataclass) | ALTO | CONSERVAR | `motor_reconocimiento/core/models.py` |
| `src/vision/frame_context.py` | DTO FrameContext | ALTO | CONSERVAR | `motor_reconocimiento/core/models.py` |
| `src/vision/preprocessing.py` | Padding/recorte de faces | MEDIO | MOVER | `motor_reconocimiento/vision/preprocessing.py` (si se necesita) |
| `src/vision/interfaces.py` | Interfaces abstractas | BAJO | EVALUAR | Posiblemente innecesario |
| `src/vision/factory.py` | Factory de motores | BAJO | ELIMINAR | No usado, reemplazar con DI |
| `src/training/trainer.py` | Entrenamiento con promediado de embeddings | ALTO | REFACTORIZAR | `motor_reconocimiento/training/trainer.py` |
| `src/storage/api_client.py` | Cliente REST fire-and-forget | MEDIO | REEMPLAZAR | `motor_reconocimiento/network/api_client.py` |
| `src/storage/firebase_manager.py` | Manager Firestore directo | MEDIO (lógica) | ELIMINAR | Backend absorbe responsabilidades |
| `src/storage/file_manager.py` | Carga/guarda modelos .pkl | MEDIO | REFACTORIZAR | `motor_reconocimiento/core/` o `training/` |
| `src/utils/config.py` | Configuración centralizada | ALTO | REFACTORIZAR | `motor_reconocimiento/config.py` |
| `src/backend/services/event_processor.py` | Procesador de eventos con reglas de negocio | ALTO | REFACTORIZAR | `backend_sica/apps/control_acceso/` |
| `src/backend/services/db_service.py` | Servicio Firestore backend | MEDIO | REEMPLAZAR | `backend_sica/` (PostgreSQL vía ORM) |
| `src/backend/models/domain.py` | Modelos de dominio Pydantic | ALTO | REFACTORIZAR | `backend_sica/apps/*/models.py` |
| `src/backend/routers/*.py` | Endpoints FastAPI | MEDIO | REEMPLAZAR | Según SDD: Django/DRF o FastAPI |
| `src/backend/core/ws_manager.py` | WebSocket manager | MEDIO | REFACTORIZAR | Backend nuevo |
| `control_acceso_app/` (Flutter) | Frontend descartado | NINGUNO | ELIMINAR | N/A — Flutter descartado |
| Tests (`tests/*.py`) | Tests unitarios/integración | MEDIO | REESCRIBIR | Tests del nuevo proyecto |

---

## 6. ANÁLISIS PROFUNDO DE `main_gui.py`

### 6.1 Variables de estado (todas las que gestionan el ciclo de vida)

| Variable | Tipo | Propósito | Acción | Destino |
|---|---|---|---|---|
| `self.active_tracks` | `{cam_idx: {track_id: {...}}}` | Tracks activos por cámara con su estado completo | **MOVER** | `core/state_manager.py` |
| `self.db_cooldowns` | `{cam_idx: {cooldown_key: timestamp}}` | Prevención de registros duplicados (600s) | **MOVER** | `core/state_manager.py` |
| `self.last_frame_ids` | `{cam_idx: frame_id}` | Detectar si el frame cambió para evitar reprocesamiento | **MOVER** | `core/orchestrator.py` |
| `self.cached_display_frames` | `{cam_idx: frame}` | Caché de frames renderizados | **MOVER** | `ui/viewer.py` |
| `self.camera_sessions` | `{cam_idx: {session_id, cam_info}}` | Sesiones activas de cámara en Firebase | **MOVER** | `network/api_client.py` |
| `self.mode` | `str` | RECOGNIZE/REGISTER/TRAINING | **MOVER** | `core/orchestrator.py` |
| `self.running` | `bool` | Control del bucle principal | **MOVER** | `core/orchestrator.py` |
| `self.zoom_factor, pan_x, pan_y` | `tk.DoubleVar` | Zoom digital del video | **MOVER** | `ui/viewer.py` |
| `self.fps, frame_count, last_time` | Profiling | Métricas de rendimiento | **MOVER** | `core/orchestrator.py` |

### 6.2 Responsabilidades identificadas — Clasificación detallada

#### R1: Bucle principal de procesamiento (`update_frame`)
- **Qué hace:** Loop cada 30ms que obtiene frames, decide modo (SINGLE/GRID), despacha a `process_recognition` o `process_registration`.
- **Dónde está:** Método `update_frame()` completo.
- **Por qué existe:** Es el corazón del motor — coordina captura→procesamiento→visualización.
- **Valor técnico:** ALTO — La lógica de coordinación es correcta conceptualmente.
- **Clasificación:** REFACTORIZAR + MOVER
- **Destino:** `core/orchestrator.py` — debe convertirse en un `Orchestrator` que coordine el pipeline.
- **Riesgo:** Alto — Es el método más complejo. Cambiar el ciclo de vida del loop afecta todo.

#### R2: Pipeline de visión (detect→track→recognize)
- **Qué hace:** Llama secuencialmente a `vision_engine.detect()`, `trackers[idx].update()`, `recognition_engine.process()`.
- **Dónde está:** Primeras líneas de `process_recognition()`.
- **Por qué existe:** Es la cadena fundamental del motor.
- **Valor técnico:** MUY ALTO — Esta secuencia es el pipeline correcto.
- **Clasificación:** CONSERVAR + MOVER
- **Destino:** `core/orchestrator.py` — este pipeline debe ser el núcleo del orquestador.
- **Riesgo:** Bajo — Los componentes ya están desacoplados internamente.

#### R3: Determinación PRESENTE/INTRUSO/DESCONOCIDO
- **Qué hace:** Compara la identidad reconocida contra el curso asignado a la cámara.
- **Dónde está:** `process_recognition()`, bloque `if identity == "Desconocido"` ... `else` con lógica de `split("_")`.
- **Por qué existe:** Implementa las reglas de asistencia.
- **Valor técnico:** MEDIO — La lógica es funcionalmente correcta pero la implementación es frágil.
- **Clasificación:** REEMPLAZAR
- **Destino:** Backend (según SDD y Rumbo Técnico, el motor solo debe emitir `camera_id + identity_uuid + confidence`).
- **Riesgo:** CRÍTICO — Esta es la separación más importante. El motor NO debe decidir PRESENTE/INTRUSO.
- **Detalle del problema:** La comparación se hace via `identity.split("_")` y normalización de strings. Esto significa que:
  - Cambiar a un estudiante de curso requiere re-entrenar y renombrar carpetas.
  - Los nombres con caracteres especiales pueden romper la comparación.
  - No hay UUID estable — la identidad ES el nombre del directorio.

#### R4: Máquina de estados de tracks (`active_tracks`)
- **Qué hace:** Gestiona el ciclo de vida de cada track: entrada → permanencia → salida/expiración.
- **Dónde está:** Dentro de `process_recognition()`, bloque tras la determinación de tipo_registro.
- **Por qué existe:** Controla cuándo registrar un evento (evitar duplicados), cuándo actualizar la identidad si mejoró, cuándo expirar un track.
- **Valor técnico:** ALTO — Resuelve un problema real: no registrar la misma persona 30 veces por segundo.
- **Clasificación:** MOVER + REFACTORIZAR
- **Destino:** `core/state_manager.py` (TrackingStateManager)
- **Riesgo:** ALTO — La máquina de estados está distribuida en múltiples bloques condicionales dentro de `process_recognition()`. Extraerla requiere cuidado.

**Detalle de la máquina de estados:**

```text
Estado: NO TRACKEADO
  └→ track_id aparece en frame por primera vez
  └→ Verificar cooldown (600s) por cooldown_key (= identity)
  └→ Si no hay cooldown activo:
  │     └→ firebase.registrar_deteccion()
  │     └→ Obtener doc_id para futuras actualizaciones
  └→ Crear entrada en active_tracks[cam][track_id] = {
        doc_id, cooldown_key, tipo, start_time,
        last_seen, missed_frames=0, best_identity
     }
  └→ Registrar cooldown

Estado: ACTIVO (track_id presente en frame)
  └→ Reset missed_frames = 0
  └→ Actualizar last_seen = time.time()
  └→ Si best_identity era "Desconocido" y ahora tiene nombre:
  │     └→ Upgrade: actualizar best_identity, tipo, cooldown_key
  │     └→ Re-registrar en Firebase con nueva identidad
  └→ Actualizar cooldown

Estado: PERDIDO (track_id NO aparece en frame)
  └→ missed_frames += 1
  └→ Si missed_frames > 30 (~1 segundo a 30fps):
        └→ EXPIRADO — eliminar de active_tracks
        └→ Si era INTRUSO: actualizar duración en Firebase
```

#### R5: Cooldowns y deduplicación (`db_cooldowns`)
- **Qué hace:** Previene re-registrar la misma persona en Firebase/API dentro de 600 segundos (10 minutos).
- **Dónde está:** `process_recognition()`, consulta `self.db_cooldowns[stream_idx].get(cooldown_key, 0)`.
- **Por qué existe:** Sin cooldown, cada aparición de una persona generaría un registro nuevo.
- **Valor técnico:** ALTO — Resuelve un problema real de deduplicación.
- **Clasificación:** MOVER
- **Destino:** `core/state_manager.py` — La deduplicación es responsabilidad del StateManager.
- **Riesgo:** Medio — La lógica es simple pero interactúa con la máquina de estados.
- **Nota importante:** `HECHO OBSERVADO` — El cooldown_key para "Desconocido" es el string literal "Desconocido", agrupando todos los desconocidos bajo una sola clave. Esto significa que detectar múltiples personas desconocidas distintas solo genera UN registro cada 10 minutos para TODOS los desconocidos combinados. Esto puede ser un bug intencional o accidental.

#### R6: Registro en Firebase/API
- **Qué hace:** Llama a `self.firebase.registrar_deteccion()` y `self.firebase.actualizar_duracion_intruso()`.
- **Dónde está:** Dentro de la máquina de estados en `process_recognition()`.
- **Por qué existe:** Persistir detecciones y actualizaciones de duración.
- **Valor técnico:** BAJO (la implementación) / ALTO (el concepto).
- **Clasificación:** REEMPLAZAR
- **Destino:** `network/api_client.py` + `network/event_queue.py` (con cola local y resiliencia).
- **Riesgo:** Medio — Actualmente es fire-and-forget sin reintentos ni cola.

#### R7: Renderizado visual
- **Qué hace:** Dibuja rectángulos, labels, overlays de FPS, convierte BGR→RGB, resize, ImageTk.
- **Dónde está:** Final de `process_recognition()` + final de `update_frame()`.
- **Por qué existe:** Visualización del estado de detección en la UI.
- **Valor técnico:** MEDIO — El renderizado básico es correcto.
- **Clasificación:** MOVER
- **Destino:** `ui/viewer.py`
- **Riesgo:** Bajo.
- **Nota:** `HECHO OBSERVADO` — La extracción de nombre legible también usa `identity.split("_")[-2:]`.

#### R8: Entrenamiento (`start_training`, `_train_task`)
- **Qué hace:** Lanza ModelTrainer en hilo daemon, recarga embeddings en RecognitionEngine.
- **Dónde está:** `start_training()` y `_train_task()`.
- **Por qué existe:** Permite re-entrenar el modelo sin reiniciar la aplicación.
- **Valor técnico:** ALTO — Hot-reload de modelo es funcionalidad valiosa.
- **Clasificación:** MOVER
- **Destino:** `training/` (trainer ya existe) + integración con `core/orchestrator.py`.
- **Riesgo:** Bajo — Ya está bien aislado en un hilo daemon.

#### R9: Registro de nuevos usuarios (`start_registration`, `process_registration`)
- **Qué hace:** Captura fotos de un rostro, las guarda en `data/dataset/Curso_Nombre/`, con control de blur y cooldown.
- **Dónde está:** `start_registration()` y `process_registration()`.
- **Por qué existe:** Enrollment de nuevos usuarios sin herramientas externas.
- **Valor técnico:** MEDIO — Funcional pero la convención de nombres es problemática.
- **Clasificación:** REFACTORIZAR
- **Destino:** `training/enrollment.py` + coordinación desde `core/orchestrator.py`.
- **Riesgo:** Medio — La nomenclatura `Curso_Nombre` deberá migrar a UUID.

#### R10: Gestión de sesiones de cámara
- **Qué hace:** Inicia/cierra sesiones en Firebase cuando una cámara se conecta/desconecta.
- **Dónde está:** `update_frame()`, bloques de `is_connected` y `session_id`.
- **Por qué existe:** Tracking del estado operacional de cámaras.
- **Valor técnico:** MEDIO — El concepto es necesario.
- **Clasificación:** MOVER
- **Destino:** `core/orchestrator.py` (detección de conexión) + `network/api_client.py` (comunicación).
- **Riesgo:** Bajo.

#### R11: Vista GRID multicámara
- **Qué hace:** Renderiza todas las cámaras en un grid 2x2.
- **Dónde está:** Bloque `elif self.view_mode == "GRID"` en `update_frame()`.
- **Por qué existe:** Visualización simultánea de todos los feeds.
- **Valor técnico:** MEDIO.
- **Clasificación:** MOVER
- **Destino:** `ui/viewer.py`.
- **Riesgo:** Bajo.

#### R12: Zoom digital
- **Qué hace:** Recorta y escala una región del frame según zoom_factor y pan.
- **Dónde está:** `update_frame()`, bloque `if z > 1.0`.
- **Valor técnico:** BAJO — Feature cosmética.
- **Clasificación:** MOVER
- **Destino:** `ui/viewer.py`.
- **Riesgo:** Bajo.

#### R13: Limpieza al cerrar (`on_closing`)
- **Qué hace:** Libera streams, actualiza duraciones de intrusos activos, cierra sesiones.
- **Dónde está:** `on_closing()`.
- **Valor técnico:** ALTO — Sin esto, los datos de duración se pierden.
- **Clasificación:** MOVER
- **Destino:** `core/orchestrator.py` (cleanup) + `core/state_manager.py` (flush tracks).
- **Riesgo:** Medio — El shutdown graceful es crítico.

#### R14: Cola de comandos de cámara (`cs.command_queue`)
- **Qué hace:** Procesa comandos de switching de cámara desde una cola global.
- **Dónde está:** Inicio de `update_frame()`.
- **Valor técnico:** BAJO.
- **Clasificación:** EVALUAR/ELIMINAR
- **Destino:** `ui/viewer.py` o eliminar si no es necesario.

---

## 7. MOTOR DE VISIÓN — Análisis detallado

### 7.1 Captura (`CameraStream`)
- **Patrón:** Productor-consumidor con Lock.
- **Hilo:** Daemon thread que lee frames continuamente.
- **Buffer:** Solo el último frame (no hay queue de frames).
- **Reconexión:** Automática tras `RECONNECT_DELAY_SECONDS` (2s).
- **Valor:** MUY ALTO — Diseño limpio y eficiente.
- **Decisión:** CONSERVAR tal como está.
- **`HECHO OBSERVADO`**: `get_frame_with_id()` retorna `(frame.copy(), frame_id)` — la copia asegura thread-safety.

### 7.2 Detección (`VisionEngine` — SCRFD)
- **Modelo:** InsightFace `buffalo_l` con módulos `[detection, recognition]`.
- **Tensor:** 320×320 (`INSIGHTFACE_INPUT_SIZE`) — optimización CPU agresiva.
- **Proveedor:** `CPUExecutionProvider` — no hay uso de GPU.
- **Umbral detección:** 0.5 (`INSIGHTFACE_DET_THRESH`).
- **Separación clave:** `detect()` solo hace detección espacial. `extract_embedding()` se llama por separado, bajo demanda.
- **`_FaceProxy`:** Wrapper necesario porque la API de ArcFace requiere un objeto con atributos `bbox` y `kps`.
- **Valor:** MUY ALTO.
- **Decisión:** CONSERVAR con mínimas modificaciones.

### 7.3 Tracking (`FaceTracker` — ByteTrack)
- **Librería:** `supervision.ByteTrack`.
- **Parámetros:** `track_activation_threshold=0.25`, `lost_track_buffer=30`, `minimum_matching_threshold=0.8`, `frame_rate=30`.
- **Truco de class_id:** `HECHO OBSERVADO` — Usa `class_id=np.arange(len(faces))` para guardar el índice original del rostro en la lista `context.faces`. Tras el tracking, recupera el face original por su índice. Esto es **técnicamente ingenioso** y debe conservarse.
- **Por cámara:** `HECHO OBSERVADO` — `self.trackers = [FaceTracker() for _ in CAMERA_SOURCES]` crea una instancia por cámara.
- **IDs:** Los track_ids son locales a cada instancia de ByteTrack. Pero en `main_gui.py`, `self.active_tracks` y `self.db_cooldowns` ya están indexados por `stream_idx`, lo que proporciona la separación `camera_id + track_id` implícitamente.
- **Valor:** MUY ALTO.
- **Decisión:** CONSERVAR.

### 7.4 Reconocimiento (`RecognitionEngine`)
- **Patrón:** Caché con TTL + ThreadPoolExecutor(1 worker).
- **Caché (`track_cache`):** Dict `{track_id: {identity, confidence, last_validation, attempts}}`.
  - TTL para reconocidos: 3 segundos (re-valida cada 3s).
  - TTL para desconocidos: 1.5s (≤2 intentos), luego 10s (>2 intentos).
- **Extracción asíncrona:** El frame y face se copian (`frame.copy()`, `copy.copy(face)`) para el hilo secundario.
- **`pending_extractions`:** Set de track_ids en cola para evitar extracciones duplicadas.
- **Matching:** Cosine similarity contra embeddings promediados.
- **Purga de caché:** Si `len(track_cache) > 1000`, purga el 20% más antiguo.
- **Valor:** MUY ALTO — Estrategia fundamental para mantener FPS.
- **Decisión:** CONSERVAR con refactorización.
- **Problema multicámara:** `HECHO OBSERVADO` — `track_cache` usa solo `track_id` como clave, NO `(camera_id, track_id)`. Sin embargo, como los track_ids de ByteTrack son monotónicamente crecientes y únicos globalmente (por la implementación de supervision.ByteTrack), esto funciona en la práctica aunque es técnicamente incorrecto. Ver sección 9.

### 7.5 Embeddings y entrenamiento
- **Formato:** Archivo `.pkl` con `{"encodings": [np.array, ...], "names": ["str", ...]}`.
- **Consolidación:** `HECHO OBSERVADO` — Se capturan hasta 30 fotos por persona, se extraen los 30 embeddings (512-dim cada uno), y se promedian con `np.mean()` para producir UN solo vector por persona. Esto es una **optimización importante** que reduce la búsqueda de N×M a N×1.
- **Naming:** `HECHO OBSERVADO` — El nombre se toma del directorio: `person_dir.name.replace("_", " ")`. Ejemplo: carpeta `2_Informatica_B_Juan_Perez` → nombre `2 Informatica B Juan Perez`.
- **Valor de la técnica de promediado:** MUY ALTO — Es una decisión técnica acertada.
- **Decisión:** CONSERVAR la técnica, REFACTORIZAR el naming a UUID.

### 7.6 Concurrencia
- **CameraStream:** 1 hilo daemon por cámara (productor de frames).
- **RecognitionEngine:** 1 hilo en ThreadPoolExecutor (extracción de embeddings).
- **APIClient:** ThreadPoolExecutor con 5 workers (llamadas HTTP asíncronas).
- **Training:** 1 hilo daemon (entrenamiento en background).
- **Hilo principal (Tkinter):** Coordina todo via `root.after(30ms)`.
- **`INFERENCIA`:** El hilo principal de Tkinter es el cuello de botella porque ejecuta detección + tracking de forma síncrona. Con múltiples cámaras, el procesamiento es secuencial en el loop, no paralelo.

---

## 8. MÁQUINA DE ESTADOS

### Diagrama de estados de un track

```text
                    ┌──────────────────┐
                    │   NO EXISTE      │
                    │   (track_id no   │
                    │    en active_    │
                    │    tracks)       │
                    └────────┬─────────┘
                             │ track_id aparece
                             │ en frame con identity
                             ▼
                    ┌──────────────────┐
            ┌──────│   ENTRADA        │
            │      │                  │──── cooldown check ──→ registrar en DB
            │      │  missed_frames=0 │                        (si no hay cooldown activo)
            │      │  start_time=now  │
            │      └────────┬─────────┘
            │               │ track_id sigue
            │               │ apareciendo
            │               ▼
            │      ┌──────────────────┐
            │      │   PERMANENCIA    │
            │      │                  │
            │      │  missed_frames=0 │
            │      │  last_seen=now   │──── identity upgrade? ──→ re-registrar
            │      │                  │     (Desconocido → Nombre)
            │      └────────┬─────────┘
            │               │ track_id NO aparece
            │               │ en frame
            │               ▼
            │      ┌──────────────────┐
            │      │   DESAPARECIDO   │
            │      │                  │
            │      │  missed_frames++ │
            │      │                  │
            │      └────────┬─────────┘
            │               │ missed_frames > 30
            │               ▼
            │      ┌──────────────────┐
            └──────│   EXPIRADO       │
                   │                  │──── si INTRUSO: actualizar duración
                   │  eliminado de    │
                   │  active_tracks   │
                   └──────────────────┘
```

### Parámetros clave:
- **Cooldown de registro:** 600 segundos (10 minutos) — evita re-registrar la misma persona.
- **Umbral de expiración:** 30 frames perdidos (~1 segundo a 30fps).
- **Cooldown key:** La identidad misma (o "Desconocido" para todos los desconocidos agrupados).

### Lógica de mejora de identidad (identity upgrade):
`HECHO OBSERVADO` — Si un track comienza como "Desconocido" y posteriormente el reconocimiento lo identifica, el sistema:
1. Actualiza `best_identity` con el nuevo nombre.
2. Cambia `tipo` (DESCONOCIDO → PRESENTE/INTRUSO).
3. Re-registra en la base de datos con la nueva identidad.
4. Esto es **lógica valiosa** que debe conservarse en el `StateManager`.

---

## 9. ANÁLISIS MULTICÁMARA

### Estado actual

`HECHO OBSERVADO`:
- Cada cámara tiene su **propia instancia** de `FaceTracker` (ByteTrack): `self.trackers = [FaceTracker() for _ in CAMERA_SOURCES]`.
- `active_tracks`, `db_cooldowns`, `last_frame_ids`, `cached_display_frames` están **indexados por `stream_idx`**: `{0: {}, 1: {}, 2: {}}`.
- El `RecognitionEngine` es **compartido** entre todas las cámaras — una sola instancia.
- La `VisionEngine` es **compartida** entre todas las cámaras — una sola instancia.

### Análisis de contaminación de estado

| Componente | Aislado por cámara? | Riesgo de contaminación |
|---|---|---|
| `FaceTracker` (ByteTrack) | ✅ Sí | Ninguno |
| `active_tracks[cam_idx]` | ✅ Sí | Ninguno |
| `db_cooldowns[cam_idx]` | ✅ Sí | Ninguno |
| `last_frame_ids[cam_idx]` | ✅ Sí | Ninguno |
| `cached_display_frames[cam_idx]` | ✅ Sí | Ninguno |
| `RecognitionEngine.track_cache` | ⚠️ NO — usa solo `track_id` | **Potencial pero mitigado** |
| `VisionEngine` (modelos ONNX) | ⚠️ Compartida | **Thread-safety no garantizada** |

### Análisis del `track_cache` compartido

`HECHO OBSERVADO`: `RecognitionEngine.track_cache` es un diccionario plano `{track_id: {...}}`. No usa `(camera_id, track_id)` como clave compuesta.

**¿Es esto un bug?**

`INFERENCIA`: En la implementación actual de `supervision.ByteTrack`, los `tracker_id` son enteros monotónicamente crecientes y **globales** a la instancia. Como cada cámara tiene su propia instancia de `FaceTracker`, los contadores de ID son independientes. Sin embargo:

- Si la cámara 0 genera track_id=1 y la cámara 1 también genera track_id=1, **colisionarían en el caché**.
- `HECHO OBSERVADO`: ByteTrack comienza su contador en 1 para cada instancia nueva. Esto significa que las **primeras personas detectadas en diferentes cámaras sí tendrán IDs colisionantes**.
- **Impacto:** Un track_id=1 de cámara 0 podría ver la identidad cacheada del track_id=1 de cámara 1. Esto produciría una identidad incorrecta durante hasta 3 segundos (el TTL del caché).

**Veredicto:** `INFERENCIA` — Existe un bug latente de contaminación de identidad en el caché de reconocimiento cuando dos cámaras generan el mismo track_id. Esto es coherente con la observación del Rumbo Técnico.

**Solución requerida (`DEFINIDO POR RUMBO TÉCNICO`):**
```text
CameraContext = camera_id + track_id
```
El caché de reconocimiento debe usar claves compuestas `(camera_id, track_id)`.

### Procesamiento multicámara

`HECHO OBSERVADO`: El procesamiento de múltiples cámaras es **secuencial** en el loop principal:
```python
for i, stream in enumerate(self.streams):  # secuencial
    # ...procesamiento de cada cámara...
```

**Cuellos de botella:**
1. Detección SCRFD se ejecuta una vez por cámara por iteración del loop → con 3 cámaras, 3× la latencia de detección.
2. El loop principal está en el hilo de Tkinter (30ms target) → con 3 cámaras y ~15-30ms de detección cada una, el loop puede exceder los 30ms.
3. `INFERENCIA`: Con cámaras IP (RTSP), el `CameraStream` podría acumular latencia en la reconexión.

---

## 10. FIREBASE — Inventario de responsabilidades

### Módulos que usan Firebase/Firestore directamente

| Módulo | Uso | Tipo de operación |
|---|---|---|
| `firebase_manager.py` | CRUD completo contra Firestore | Síncrono, bloqueante |
| `api_client.py` | Wrapper HTTP que llama al backend FastAPI | Asíncrono (fire-and-forget) |
| `src/backend/services/db_service.py` | Servicio de persistencia del backend | Síncrono contra Firestore |
| `src/backend/core/dependencies.py` | Inyección de dependencias Firebase | Síncrono |
| `src/backend/routers/auth.py` | Autenticación Firebase Auth | Síncrono |

### Colecciones Firestore identificadas

| Colección | Operaciones | Responsabilidades mezcladas |
|---|---|---|
| `Camaras` | read/write | Estado activa/apagada, ubicación, telemetría |
| `Cursos` | read/write | Identidad de curso, estado activo |
| `Cursos/{id}/InformeDiario/{fecha}` | read/write | **REGLAS DE NEGOCIO:** listas de presentes/ausentes/intrusos, conteos |
| `Camaras/{id}/RegistroDiario/{fecha}` | write | Telemetría de última detección |
| `Usuarios` | read/write | Gestión de usuarios del sistema |
| `Estudiantes` | read/write | Datos de estudiantes |
| `Alertas` | write | Generación de alertas |
| `Notificaciones` | write | Push notifications |
| `SesionesCamara` | read/write | Historial de sesiones |

### Reglas de negocio embebidas en Firebase operations

`HECHO OBSERVADO` — `firebase_manager.registrar_deteccion()` contiene:
1. Creación del informe diario si no existe (con cálculo de `alumnos_esperados`).
2. Determinación de si un nombre pertenece al curso (`_es_del_curso()`).
3. Gestión de listas de presentes/ausentes/intrusos.
4. Conteo de totales.
5. Parseo de identidad (`_parse_identity()` con `split("_")`).

**Estas reglas deben migrar al backend** (`DEFINIDO POR SDD` y `DEFINIDO POR RUMBO TÉCNICO`).

### Estrategia de sustitución

```text
Firebase/Firestore        →    PostgreSQL (vía ORM)
firebase_manager.py       →    ELIMINAR (backend absorbe)
api_client.py             →    REEMPLAZAR con APIClient + EventQueue
Reglas en Firebase         →    backend_sica/apps/control_acceso/
Autenticación Firebase    →    JWT (DEFINIDO POR RUMBO TÉCNICO)
```

---

## 11. IDENTIDAD Y EMBEDDINGS

### Sistema actual de identidad

`HECHO OBSERVADO`:
```text
Carpeta: data/dataset/2_Informatica_B_Juan_Perez/
    ├── 2_Informatica_B_Juan_Perez_000.jpg
    ├── 2_Informatica_B_Juan_Perez_001.jpg
    └── ... (hasta 30 fotos)

Entrenamiento:
    person_name = person_dir.name.replace("_", " ")
    → "2 Informatica B Juan Perez"

Modelo (encodings.pkl):
    names = ["2 Informatica B Juan Perez", "3 CC A Mat Maria Lopez", ...]
    encodings = [np.array(512-dim), ...]

Reconocimiento:
    identity = "2 Informatica B Juan Perez"  (con espacios)
    O tras reconstruct: "2_Informatica_B_Juan_Perez" (con guiones bajos)

Parseo en Firebase:
    partes = identity.split("_")
    nombre_limpio = " ".join(partes[-2:])  → "Juan Perez"
    curso = "_".join(partes[:-2])          → "2_Informatica_B"

Comparación PRESENTE/INTRUSO:
    curso_actual_norm = curso_camara.lower().replace("_", " ")
    ident_norm = identity.lower().replace("_", " ")
    if curso_actual_norm in ident_norm:  → PRESENTE
```

### Problemas identificados

1. **La identidad codifica relaciones de base de datos** — El string `2_Informatica_B_Juan_Perez` embebe curso + nombre, creando acoplamiento.
2. **Cambio de curso = re-entrenamiento** — Si Juan cambia de curso, hay que renombrar la carpeta y re-entrenar.
3. **Homónimos** — Dos "Juan Perez" en diferentes cursos producirían colisiones o confusiones.
4. **Parseo frágil** — `split("_")` asume un formato específico. Nombres con guión bajo o cursos con formatos distintos romperían el parseo.
5. **Inconsistencia de separadores** — A veces se usa `_` (carpetas), a veces ` ` (modelo), a veces se normaliza.

### Estrategia futura (`DEFINIDO POR RUMBO TÉCNICO`)

```text
UUID
 │
 ├── identidad del estudiante (inmutable)
 ├── embeddings (asociados al UUID)
 └── relaciones (curso, representante) → administradas por Backend

Motor solo conoce: UUID → embedding_vector
Backend conoce: UUID → estudiante → curso → representante
```

---

## 12. REGLAS DE NEGOCIO — Mapa actual vs. objetivo

### Dónde se toman las decisiones actualmente

| Decisión | Dónde se toma ahora | Dónde debe estar (SDD) |
|---|---|---|
| PRESENTE | `main_gui.py` (comparación string curso↔identidad) | **Backend** |
| INTRUSO | `main_gui.py` (curso no coincide) | **Backend** |
| DESCONOCIDO | `main_gui.py` (identity == "Desconocido") | **Backend** (el motor solo reporta "no match") |
| CURSO_DIFERENTE | `event_processor.py` (backend) | **Backend** ✅ |
| PERMANENCIA_EXCESIVA | `event_processor.py` (10 min timer) | **Backend** ✅ |
| ENTRADA/SALIDA | `event_processor.py` (según camera_type) | **Backend** ✅ |
| Cooldown de registro | `main_gui.py` (600s por identity) | **Motor Edge** (deduplicación local) + **Backend** (lógica de negocio) |
| Expiración de track | `main_gui.py` (30 missed frames) | **Motor Edge** (state manager) |
| Identity upgrade | `main_gui.py` (Desconocido→Nombre) | **Motor Edge** (state manager) |

### Flujo objetivo (`DEFINIDO POR RUMBO TÉCNICO`)

```text
Motor:
  "CAM_01 detectó UUID X con confianza 98.5%, track_id 42"

Backend:
  "CAM_01 pertenece al curso Y"
  "UUID X pertenece al curso Y"
  → PRESENTE

O:
  "UUID X pertenece al curso Z ≠ Y"
  → INTRUSO / CURSO_DIFERENTE
```

El motor debe producir **eventos neutros** (DETECTION, TRACK_EXPIRED) y el backend debe clasificarlos.

---

## 13. CONFLICTOS REPOSITORIO vs SDD

| # | Conflicto | Repositorio | SDD | Resolución |
|---|---|---|---|---|
| 1 | Backend framework | FastAPI + SQLAlchemy | **Django + DRF** | Ver sección 15 (conflicto SDD vs Rumbo) |
| 2 | Reglas de negocio en Edge | `main_gui.py` decide PRESENTE/INTRUSO | Separación Edge↔Backend | **Seguir SDD**: reglas en backend |
| 3 | Firebase como DB | Firestore directo desde motor y backend | PostgreSQL | **Seguir SDD**: PostgreSQL |
| 4 | Identidad basada en strings | `Curso_Nombre_Apellido` | UUID/FK a estudiante | **Seguir SDD**: identificadores estables |
| 5 | Motor con reglas educativas | Motor conoce cursos y decide asistencia | Motor solo emite detecciones | **Seguir SDD**: motor desacoplado |
| 6 | `main_gui.py` como controlador | GUI controla pipeline completo | GUI solo muestra resultados | **Seguir SDD**: separar responsabilidades |
| 7 | Sin cola de eventos | Fire-and-forget HTTP | Comunicación desacoplada | **Seguir SDD**: cola local con resiliencia |
| 8 | Flutter presente | Flutter en repositorio | No mencionado (implícitamente no Flutter) | **Eliminar Flutter** |

---

## 14. CONFLICTOS REPOSITORIO vs RUMBO TÉCNICO

| # | Conflicto | Repositorio | Rumbo Técnico | Resolución |
|---|---|---|---|---|
| 1 | Track cache sin camera_id | `track_cache[track_id]` | Cada cámara con su contexto aislado | Usar `(camera_id, track_id)` |
| 2 | API sin cola local | `api_client._post_async()` fire-and-forget | Cola local + resiliencia | Implementar `EventQueue` |
| 3 | Sesión basada en curso | `session_id = curso.replace(" ", "_")` | Session basada en camera_id | Rediseñar sesiones |
| 4 | Estado global compartido | Un solo RecognitionEngine para todas las cámaras | CameraContext independiente | Crear CameraContext |
| 5 | Procesamiento secuencial | Loop secuencial por cámara | Diseño multicámara nativo | Evaluar paralelización |
| 6 | Reglas de negocio duplicadas | `main_gui.py` + `firebase_manager.py` + `event_processor.py` | Única fuente de verdad en backend | Centralizar en backend |

---

## 15. CONFLICTOS SDD vs RUMBO TÉCNICO

> [!IMPORTANT]
> Esta sección documenta las diferencias entre los dos documentos de autoridad. Estos conflictos deben ser resueltos antes de iniciar la implementación.

| # | Tema | SDD | Rumbo Técnico | Impacto | Resolución propuesta |
|---|---|---|---|---|---|
| **1** | **Framework Backend** | **Django 5.x + DRF** | **FastAPI + SQLAlchemy + Alembic** | CRÍTICO — Afecta toda la arquitectura backend | El SDD dice Django; el Rumbo Técnico dice FastAPI. **Requiere decisión del propietario.** Ambos son válidos. Django ofrece ORM maduro, admin integrado, ecosystem de plugins. FastAPI ofrece async nativo, rendimiento, Pydantic. |
| **2** | **ORM** | **Django ORM** (implícito por usar Django) | **SQLAlchemy** | ALTO — Migración de modelos | Depende de la decisión del punto 1 |
| **3** | **Migraciones** | Django migrations (implícito) | **Alembic** | MEDIO — Depende del punto 1 |  |
| **4** | **Estructura de carpetas del motor** | `motor_reconocimiento/src/capture/`, `src/vision/`, `src/training/`, `src/storage/` | `motor_reconocimiento/core/`, `capture/`, `vision/`, `network/`, `ui/` | MEDIO — El Rumbo Técnico refina la estructura del SDD añadiendo `core/` (orchestrator, state_manager, event_processor) y `network/` | **RECOMENDACIÓN**: Usar la estructura del Rumbo Técnico, que es más detallada y correcta. El SDD la define de forma más genérica. No hay contradicción real, sino refinamiento. |
| **5** | **Backend como autoridad vs API del SDD** | Endpoints: `POST /api/v1/sesion-camara/iniciar/`, `POST /api/v1/asistencia/registrar/`, `POST /api/v1/sesion-camara/cerrar/` | Contrato JSON con `camera_id`, `event_type`, `identity_uuid`, `confidence`, `track_id` | MEDIO — Los endpoints del SDD son más específicos al caso de uso; el Rumbo Técnico propone un contrato más genérico basado en eventos | **RECOMENDACIÓN**: El contrato del Rumbo Técnico es más flexible y extensible. Los endpoints del SDD pueden implementarse como wrapper de este contrato. |
| **6** | **`main_gui.py` en la estructura** | El SDD **mantiene** `main_gui.py` en la estructura objetivo: `motor_reconocimiento/main_gui.py` | El Rumbo Técnico establece que `main_gui.py` debe **descomponerse**, con la GUI reducida a `ui/viewer.py` y el punto de entrada en `main.py` | BAJO — El SDD probablemente menciona `main_gui.py` por inercia del repositorio original | **RECOMENDACIÓN**: Seguir el Rumbo Técnico. El SDD fue escrito antes del análisis profundo del God Object. |
| **7** | **Autenticación** | No especificada explícitamente (implícita Django Auth) | **JWT** | BAJO — JWT es compatible con ambos frameworks | Usar JWT independientemente del framework |
| **8** | **WebSocket** | No mencionado | "WebSocket cuando sea necesario para comunicación en tiempo real" | BAJO — Es una adición, no una contradicción | Incluir WebSocket como opcional |

### Veredicto sobre el conflicto Django vs FastAPI

Este es el conflicto más importante. Las opciones son:

**Opción A: Django + DRF (como dice el SDD)**
- ✅ Admin integrado (reemplaza parte de AdminLTE)
- ✅ ORM maduro con migraciones automáticas
- ✅ Ecosistema de plugins enorme
- ✅ Sesiones y auth integradas
- ❌ No es nativo async (aunque soporta ASGI)
- ❌ Más pesado para APIs puras

**Opción B: FastAPI + SQLAlchemy (como dice el Rumbo Técnico)**
- ✅ Async nativo
- ✅ Pydantic integrado (validación)
- ✅ Documentación automática (Swagger)
- ✅ Más liviano y rápido para APIs
- ❌ No tiene admin integrado
- ❌ Requiere más setup manual (Alembic, auth)

**`RECOMENDACIÓN`:** Dado que el SDD es la autoridad máxima, **la decisión debe ser tomada por el propietario del proyecto**. El Rumbo Técnico contradice explícitamente al SDD en este punto.

---

## 16. CÓDIGO QUE DEBE RESCATARSE

| Componente | Por qué rescatarlo | Forma de rescate |
|---|---|---|
| **Pipeline detect→track→recognize** | Es el corazón funcional del motor. Está bien diseñado. | Mover a `core/orchestrator.py` |
| **CameraStream** | Diseño limpio de captura concurrente. | Conservar casi intacto |
| **VisionEngine** (detect + extract_embedding) | Separación detection/recognition es la optimización clave. | Conservar |
| **FaceTracker** (truco class_id) | Mapeo ingenioso de índices para ByteTrack. | Conservar |
| **RecognitionEngine** (caché + async) | Estrategia que salva el rendimiento. | Refactorizar (añadir camera_id a caché) |
| **Técnica de promediado de embeddings** | Reduce complejidad de búsqueda dramáticamente. | Conservar en trainer |
| **Máquina de estados** (active_tracks) | Resuelve el problema real de deduplicación y ciclo de vida. | Extraer a `core/state_manager.py` |
| **Cooldown de 600s** | Previene saturación de la base de datos. | Mover a state_manager |
| **Identity upgrade** (Desconocido→Nombre) | Lógica inteligente que mejora la precisión progresivamente. | Mover a state_manager |
| **Expiración de tracks** (missed_frames>30) | Limpieza necesaria de tracks perdidos. | Mover a state_manager |
| **Shutdown graceful** (on_closing) | Flush de datos de permanencia antes de cerrar. | Mover a orchestrator |
| **DetectedFace dataclass** | DTO limpio e independiente de InsightFace. | Conservar en models |
| **FrameContext** | Contrato claro entre componentes del pipeline. | Conservar en models |
| **EventProcessor** (backend) | Reglas de negocio bien modeladas (ENTRADA/SALIDA/PERMANENCIA). | Refactorizar para el backend nuevo |
| **Domain models** (Event, Alert, Student) | Modelos de dominio bien definidos. | Adaptar al ORM elegido |

---

## 17. CÓDIGO QUE DEBE DESCARTARSE

| Componente | Por qué descartarlo |
|---|---|
| **Flutter (`control_acceso_app/`)** | `DEFINIDO POR RUMBO TÉCNICO`: Flutter descartado. AdminLTE/PWA es el frontend. |
| **`firebase_manager.py`** | `DEFINIDO POR RUMBO TÉCNICO`: Firebase descartado. Las responsabilidades migran al backend. |
| **Lógica PRESENTE/INTRUSO en `main_gui.py`** | `DEFINIDO POR SDD/RUMBO TÉCNICO`: El motor no debe decidir estado educativo. |
| **`_es_del_curso()` y `_parse_identity()`** en Firebase manager | Reglas de negocio que no deben existir en la capa de almacenamiento. |
| **`main_gui.py` como God Object** | Debe descomponerse, no conservarse como estructura. |
| **`factory.py`** | No utilizado en producción. |
| **`interfaces.py`** | No utilizado en producción. |
| **Naming `Curso_Nombre_Apellido`** | `DEFINIDO POR RUMBO TÉCNICO`: Migrar a UUID. |
| **`migrate_firestore.py`** | Script de migración Firebase, irrelevante para arquitectura nueva. |
| **Tests acoplados a Firebase** | Deben reescribirse para la nueva arquitectura. |
| **`winsound.Beep()`** en main_gui | Acoplamiento a Windows innecesario. |
| **`cs.command_queue`** | Comunicación global por cola estática, anti-patrón. |

---

## 18. MAPEO HACIA LA ESTRUCTURA DEL SDD

### Estructura SDD (con refinamientos del Rumbo Técnico)

```text
proyecto_sica/
├── motor_reconocimiento/           # Fase 1: Motor Edge
│   ├── main.py                     # Punto de entrada
│   ├── config.py                   # Configuración centralizada
│   │
│   ├── core/                       # [NUEVO] Orquestación y estado
│   │   ├── orchestrator.py         # Pipeline principal
│   │   ├── state_manager.py        # Máquina de estados de tracks
│   │   ├── event_processor.py      # Generación de eventos
│   │   └── models.py              # DTOs (DetectedFace, FrameContext, etc.)
│   │
│   ├── capture/
│   │   └── camera_stream.py        # Captura de frames
│   │
│   ├── vision/
│   │   ├── engine.py              # SCRFD + ArcFace
│   │   ├── tracker.py             # ByteTrack
│   │   └── recognizer.py          # Reconocimiento + caché
│   │
│   ├── training/
│   │   └── trainer.py             # Entrenamiento + enrollment
│   │
│   ├── network/                    # [NUEVO] Comunicación con backend
│   │   ├── api_client.py          # Cliente REST
│   │   ├── event_queue.py         # Cola local resiliente
│   │   └── payload_builder.py     # Construcción de payloads
│   │
│   ├── ui/                         # [NUEVO] Interfaz local
│   │   └── viewer.py             # Visualización (Tkinter o headless)
│   │
│   └── requirements.txt
│
├── backend_sica/                   # Fase 2: Plataforma Central
│   ├── manage.py                   # (Django) o main.py (FastAPI)
│   ├── requirements.txt
│   ├── sica_project/              # Configuración
│   │   └── settings.py
│   ├── apps/
│   │   ├── usuarios/              # Auth, roles, permisos
│   │   ├── institucion/           # Cursos, Estudiantes, Cámaras
│   │   ├── control_acceso/        # API REST, Eventos, Asistencia
│   │   └── notificaciones/        # Alertas, reportes
│   ├── static/                    # AdminLTE + PWA
│   └── templates/                 # Vistas HTML
│
├── Documento de Diseño del Sistema SICA.md
├── RUMBO_TECNICO_DEFINITIVO.md
├── FASE_0_MAPA_DE_RECONSTRUCCION.md
└── README.md
```

### Mapeo detallado: código legado → estructura nueva

| Código legado | → | Destino nuevo | Razón arquitectónica |
|---|---|---|---|
| `main_gui.py` (pipeline detect→track→recognize) | → | `core/orchestrator.py` | Coordinación sin GUI |
| `main_gui.py` (active_tracks, cooldowns, missed_frames) | → | `core/state_manager.py` | Estado independiente de GUI |
| `main_gui.py` (PRESENTE/INTRUSO/DESCONOCIDO) | → | `backend_sica/apps/control_acceso/` | Reglas de negocio en backend |
| `main_gui.py` (renderizado, zoom, grid) | → | `ui/viewer.py` | Presentación separada |
| `main_gui.py` (registro usuario) | → | `training/enrollment.py` | Enrollment separado |
| `main_gui.py` (start_training, _train_task) | → | `training/trainer.py` + orchestrator | Entrenamiento separado |
| `main_gui.py` (camera sessions) | → | `core/orchestrator.py` + `network/api_client.py` | Gestión de sesiones |
| `main_gui.py` (on_closing) | → | `core/orchestrator.py` (shutdown) | Cleanup centralizado |
| `src/capture/camera_stream.py` | → | `capture/camera_stream.py` | ~Sin cambios |
| `src/vision/vision_engine.py` | → | `vision/engine.py` | Renombrar |
| `src/vision/tracker.py` | → | `vision/tracker.py` | ~Sin cambios |
| `src/vision/recognition_engine.py` | → | `vision/recognizer.py` | Añadir camera_id a caché |
| `src/vision/face_data.py` | → | `core/models.py` | Mover a modelos centrales |
| `src/vision/frame_context.py` | → | `core/models.py` | Mover a modelos centrales |
| `src/training/trainer.py` | → | `training/trainer.py` | Migrar naming a UUID |
| `src/storage/api_client.py` | → | `network/api_client.py` | Reemplazar con cola + resiliencia |
| `src/storage/firebase_manager.py` | → | ELIMINAR | Backend absorbe |
| `src/storage/file_manager.py` | → | `core/` o `training/` | Simplificar |
| `src/utils/config.py` | → | `config.py` | Centralizar |
| `src/backend/services/event_processor.py` | → | `backend_sica/apps/control_acceso/services/` | Migrar reglas de negocio |
| `src/backend/models/domain.py` | → | `backend_sica/apps/*/models.py` | Adaptar a ORM |

---

## 19. RIESGOS DE RECONSTRUCCIÓN

### CRÍTICO

| Riesgo | Descripción | Mitigación |
|---|---|---|
| **Conflicto Django vs FastAPI** | SDD dice Django, Rumbo dice FastAPI. No hay consenso. | Resolver ANTES de empezar. |
| **Pérdida de máquina de estados** | La lógica de active_tracks/cooldowns/missed_frames está entrelazada con la GUI. Extraerla incorrectamente puede perder comportamiento. | Tests de referencia antes de migrar. Mapear cada variable y su ciclo de vida. |
| **Regresión en reconocimiento** | Cambiar la arquitectura del caché o la concurrencia del reconocimiento puede degradar FPS o precisión. | Benchmark de FPS y accuracy antes y después. |

### ALTO

| Riesgo | Descripción | Mitigación |
|---|---|---|
| **Colisión de track_ids en caché** | El bug latente del caché compartido puede manifestarse al cambiar la arquitectura. | Implementar CameraContext desde el inicio. |
| **Migración de identidad a UUID** | Cambiar de `Curso_Nombre_Apellido` a UUID afecta: carpetas, modelo .pkl, entrenamiento, reconocimiento, comparación, y persistencia. | Fase gradual: primero UUID+nombre, luego solo UUID. |
| **Procesamiento secuencial multicámara** | Con la arquitectura actual, añadir más cámaras degrada linealmente el rendimiento. | Diseñar para paralelismo desde el inicio (un hilo/proceso por cámara). |

### MEDIO

| Riesgo | Descripción | Mitigación |
|---|---|---|
| **Sin cola de eventos resiliente** | Actualmente las llamadas HTTP son fire-and-forget. Pérdida de red = pérdida de datos. | Implementar EventQueue con persistencia local temprano. |
| **Thread-safety del VisionEngine** | VisionEngine compartido entre cámaras; ONNX runtime puede no ser thread-safe. | Evaluar con `max_workers=1` o instanciar un VisionEngine por cámara. |
| **Complejidad del shutdown** | El cleanup actual depende de flush de todos los tracks activos a Firebase. Sin cola, algunos datos se pierden. | Implementar shutdown graceful con timeout. |

### BAJO

| Riesgo | Descripción | Mitigación |
|---|---|---|
| **Pérdida de zoom digital** | Feature cosmética que podría no re-implementarse. | Documentar para implementar en ui/viewer.py. |
| **Pérdida de vista grid** | Feature de visualización multicámara. | Implementar en ui/viewer.py. |

---

## 20. ORDEN RECOMENDADO DE IMPLEMENTACIÓN

### Fase 0 — Congelación y diagnóstico ✅ (ESTE DOCUMENTO)
- [x] Leer SDD
- [x] Leer RUMBO_TECNICO_DEFINITIVO.md
- [x] Analizar repositorio legado completo
- [x] Trazar dependencias
- [x] Trazar flujo de ejecución
- [x] Identificar lógica valiosa
- [x] Identificar deuda técnica
- [x] Contrastar contra SDD
- [x] Contrastar contra Rumbo Técnico
- [x] Crear FASE_0_MAPA_DE_RECONSTRUCCION.md
- [ ] **RESOLVER CONFLICTO Django vs FastAPI**

### Fase 1 — Fundación del motor Edge
**Objetivo:** Motor funcional desacoplado de GUI y Firebase.

1. Crear estructura de carpetas del motor (`motor_reconocimiento/`)
2. Migrar `core/models.py` (DetectedFace, FrameContext) — sin cambios funcionales
3. Migrar `capture/camera_stream.py` — sin cambios funcionales
4. Migrar `vision/engine.py` (VisionEngine) — sin cambios funcionales
5. Migrar `vision/tracker.py` (FaceTracker) — sin cambios funcionales
6. Migrar `vision/recognizer.py` (RecognitionEngine) — **añadir `camera_id` al caché**
7. Migrar `config.py` — limpiar, centralizar
8. Crear `core/state_manager.py` — extraer de main_gui: active_tracks, cooldowns, missed_frames, identity upgrade, expiración
9. Crear `core/orchestrator.py` — pipeline detect→track→recognize→state→event sin GUI
10. Crear `core/event_processor.py` — generación de eventos neutros (DETECTION, TRACK_EXPIRED)

**Criterio de aceptación Fase 1:**
- El motor puede ejecutarse headless (sin Tkinter)
- Pipeline completo funciona para N cámaras
- No hay dependencia de Firebase
- No hay reglas de negocio (PRESENTE/INTRUSO)
- Cada cámara tiene contexto aislado
- Track cache usa (camera_id, track_id)

### Fase 2 — Comunicación y resiliencia
1. Crear `network/event_queue.py` — cola local con persistencia
2. Crear `network/api_client.py` — cliente REST con reintentos
3. Crear `network/payload_builder.py` — construcción de payloads JSON
4. Integrar cola con orchestrator

**Criterio de aceptación Fase 2:**
- Eventos se encolan localmente
- Pérdida de red no detiene el motor
- Reconexión automática envía eventos pendientes

### Fase 3 — UI local (opcional para Edge)
1. Crear `ui/viewer.py` — visualización (Tkinter, headless, o ambos)
2. Migrar renderizado, zoom, grid
3. Crear `main.py` — punto de entrada

### Fase 4 — Entrenamiento y UUID
1. Migrar `training/trainer.py` — mantener técnica de promediado
2. Crear `training/enrollment.py` — captura de fotos
3. Implementar transición de naming a UUID
4. Definir formato de galería de embeddings compatible con UUID

### Fase 5 — Backend (Django o FastAPI — según decisión)
1. Setup del proyecto backend
2. Modelos de base de datos (usuarios, cursos, estudiantes, cámaras)
3. API REST para recibir eventos del motor
4. Reglas de negocio (PRESENTE/INTRUSO/PERMANENCIA)
5. Autenticación JWT
6. WebSocket para tiempo real (opcional)

### Fase 6 — Frontend (AdminLTE/PWA)
1. Dashboards por rol
2. Gestión de cursos/estudiantes
3. Reportes de asistencia
4. Alertas y notificaciones
5. PWA + Service Worker

### Fase 7 — Integración y distribución
1. Motor ↔ Backend integration testing
2. Backend ↔ Frontend integration testing
3. Distribución Windows (.exe)
4. PWA para Play Store

---

## 21. CRITERIOS DE ACEPTACIÓN

### Motor Edge (reconstruido)

| Criterio | Método de verificación |
|---|---|
| Motor funciona sin Firebase | Ejecutar motor sin credenciales Firebase — no debe crashear |
| Motor no decide PRESENTE/INTRUSO | Inspección de código: no hay lógica educativa en motor |
| Pipeline detect→track→recognize funciona | Test con video pregrabado: detección + tracking + reconocimiento exitoso |
| Multicámara aislada | Test con 2 cámaras: track_id=1 en cámara 0 y track_id=1 en cámara 1 no comparten identidad |
| Caché de reconocimiento con camera_id | Test: misma persona en 2 cámaras tiene entradas separadas en caché |
| Cola de eventos funciona offline | Desconectar red → motor sigue procesando → reconectar → eventos enviados |
| FPS comparable al original | Benchmark: ≥ 80% del FPS del sistema legado con misma configuración |
| Máquina de estados preservada | Test: track entry → permanencia → missed_frames → expiración funciona igual |
| Cooldown funciona | Test: misma persona no se re-registra dentro de 600s |
| Identity upgrade funciona | Test: track inicia como Desconocido, luego se identifica |
| Shutdown graceful | Test: cerrar motor → todos los tracks activos se flushean |

### Backend (nuevo)

| Criterio | Método de verificación |
|---|---|
| Recibe eventos del motor | POST al endpoint → evento persiste en PostgreSQL |
| Clasifica PRESENTE/INTRUSO | Motor envía UUID+camera_id → backend responde con clasificación |
| No depende de Firebase | Sin import de firebase_admin en el proyecto |
| Roles funcionan | Admin/Inspector/Representante con permisos diferenciados |
| Reportes de asistencia | Endpoint retorna resumen diario por curso |

---

## NOTA FINAL

Este documento es el resultado de una ingeniería inversa profunda del repositorio legado, contrastada contra el SDD y el Rumbo Técnico. Cada afirmación está etiquetada como HECHO OBSERVADO, INFERENCIA, DEFINIDO POR SDD, DEFINIDO POR RUMBO TÉCNICO o RECOMENDACIÓN.

**Antes de comenzar la implementación, se requiere resolver:**

1. **El conflicto Django vs FastAPI** (Sección 15, Punto 1).
2. **Aprobación de la estructura de carpetas refinada** (Sección 18).
3. **Aprobación del orden de implementación** (Sección 20).

Una vez resueltos estos puntos, este documento servirá como mapa de navegación para la reconstrucción completa del sistema SICA.
