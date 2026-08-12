# RUMBO TÉCNICO DEFINITIVO
## Motor de Reconocimiento Facial y Sistema Integral de Control de Acceso Escolar

**Estado:** Dirección técnica aprobada para reconstrucción  
**Propósito:** Servir como fuente de verdad para la reconstrucción del proyecto existente  
**Etapa:** Pre-implementación  
**Frontend objetivo:** AdminLTE 3 + PWA  
**Backend objetivo:** FastAPI + PostgreSQL  
**Edge/Motor:** Python + OpenCV + InsightFace + ByteTrack  
**Flutter:** DESCARTADO  
**Firebase/Firestore:** DESCARTADO  

---

# 1. PROPÓSITO

Este documento define el rumbo técnico para reconstruir el proyecto actual a partir del código existente y llevarlo hacia la arquitectura definida en el SDD.

El proyecto actual no debe considerarse una implementación limpia de la arquitectura objetivo. Es el resultado de un desarrollo incremental realizado originalmente sin un diseño arquitectónico formal, incorporando ideas, tecnologías y soluciones de diferentes momentos.

Por esta razón, no se debe continuar agregando funcionalidades sobre la estructura actual sin antes separar aquello que realmente constituye el motor de reconocimiento de aquello que pertenece a infraestructura, interfaz o lógica de negocio.

El objetivo no es desechar indiscriminadamente el código existente.

El objetivo es:

> **rescatar la lógica técnicamente válida, eliminar el acoplamiento innecesario y reconstruir el sistema alrededor de la arquitectura definida en el SDD.**

---

# 2. PRINCIPIO FUNDAMENTAL

> **No conservar archivos por el simple hecho de que ya existen. Conservar únicamente las capacidades, algoritmos y comportamientos que demuestren valor técnico para la arquitectura objetivo.**

Esto significa que el repositorio actual debe considerarse una fuente de componentes recuperables, no como la estructura que necesariamente debe mantenerse.

Especialmente:

- `main_gui.py` no debe conservarse como God Object.
- Su lógica útil debe identificarse y extraerse.
- La interfaz gráfica no debe controlar el motor.
- El motor no debe conocer reglas educativas.
- El motor no debe comunicarse directamente con PostgreSQL.
- El motor no debe depender de Firebase.
- El motor no debe depender de Flutter.
- El frontend no debe encargarse del procesamiento de cámaras.
- La base de datos no debe ser accedida directamente desde el Edge.

---

# 3. ARQUITECTURA OBJETIVO

La arquitectura definitiva se divide en tres grandes bloques:

```text
┌─────────────────────────────────────────────────────────────┐
│                       EDGE / MOTOR                          │
│                                                             │
│ Python                                                      │
│ OpenCV                                                      │
│ InsightFace / SCRFD / ArcFace                               │
│ ByteTrack                                                   │
│ Captura de cámaras                                          │
│ Tracking                                                    │
│ Reconocimiento                                              │
│ Gestión de estado                                           │
│ Cola local                                                  │
│ Cliente HTTP                                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ REST API / eventos
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                         BACKEND                             │
│                                                             │
│ FastAPI                                                     │
│ SQLAlchemy                                                  │
│ Alembic                                                     │
│ PostgreSQL                                                  │
│ JWT                                                         │
│ Reglas de negocio                                           │
│ Usuarios                                                    │
│ Cursos                                                      │
│ Estudiantes                                                 │
│ Cámaras                                                     │
│ Asistencia                                                  │
│ Eventos                                                     │
│ Notificaciones                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ REST / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND                              │
│                                                             │
│ AdminLTE 3                                                  │
│ HTML / CSS / JavaScript                                     │
│ PWA                                                         │
│ Service Worker                                              │
│ Manifest                                                    │
│                                                             │
│ ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐   │
│ │    Web       │ │ PWA / Store  │ │ Windows .exe        │   │
│ └──────────────┘ └──────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

# 4. TECNOLOGÍAS DEFINITIVAS

## 4.1 Motor / Edge

Se conserva:

- Python
- OpenCV
- InsightFace
- SCRFD
- ArcFace
- ByteTrack

Estas tecnologías constituyen la base actual del reconocimiento y tracking y, según las auditorías realizadas, no existe razón arquitectónica para reemplazarlas durante esta reconstrucción.

Primero debe estabilizarse y desacoplarse el motor.

Las optimizaciones de rendimiento deben realizarse posteriormente sobre una arquitectura limpia.

## 4.2 Backend

La arquitectura vigente utiliza:

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- JWT
- API REST
- WebSocket cuando sea necesario para comunicación en tiempo real

El backend será el centro de autoridad del sistema.

Será responsable de:

- usuarios;
- autenticación;
- estudiantes;
- cursos;
- cámaras;
- relaciones entre estudiantes y cursos;
- asistencia;
- eventos;
- notificaciones;
- reglas de negocio;
- persistencia;
- consultas;
- administración.

---

# 5. FRONTEND DEFINITIVO

El frontend objetivo es:

> **AdminLTE 3 + PWA**

No Flutter.

La interfaz será una aplicación web que podrá utilizarse mediante navegador, como PWA instalable y mediante las estrategias de distribución definidas en el SDD.

### Web

Acceso mediante navegador.

### PWA

Instalable en dispositivos compatibles.

### Play Store

La PWA será preparada para su distribución como aplicación instalable en Android mediante la estrategia definida en el SDD.

### Windows

Se dispondrá de una distribución propia en formato `.exe`.

---

# 6. TECNOLOGÍAS DESCARTADAS

Estas decisiones deben considerarse cerradas, salvo que posteriormente el SDD sea modificado deliberadamente.

| Tecnología | Estado |
|---|---|
| Flutter | ❌ DESCARTADO |
| Firebase | ❌ DESCARTADO |
| Firestore | ❌ DESCARTADO |
| Firebase Authentication | ❌ DESCARTADO |
| Acceso directo del motor a Firestore | ❌ PROHIBIDO |
| Acceso directo del motor a PostgreSQL | ❌ PROHIBIDO |
| Lógica educativa dentro del motor | ❌ PROHIBIDO |
| Cámara procesada desde Flutter | ❌ PROHIBIDO |

La existencia de código antiguo relacionado con estas tecnologías no significa que deban conservarse.

---

# 7. EL CASO ESPECIAL DE `main_gui.py`

`main_gui.py` no debe simplemente eliminarse.

Tampoco debe conservarse íntegramente.

Debe tratarse como una fuente de lógica recuperable.

La auditoría identificó que actualmente contiene responsabilidades mezcladas:

```text
main_gui.py
│
├── GUI
├── Captura
├── Procesamiento
├── Tracking
├── Reconocimiento
├── Estado de tracks
├── Cooldowns
├── Reglas de curso
├── Detección de intrusos
├── Firebase
├── Persistencia
└── Renderizado
```

La reconstrucción debe separar esas responsabilidades.

---

# 8. QUÉ DEBE RESCATARSE DE `main_gui.py`

Se deben recuperar principalmente:

### Máquina de estados

- `active_tracks`
- seguimiento del ciclo de vida del track;
- detección de entrada;
- permanencia;
- desaparición;
- `missed_frames`;
- cálculo de duración.

### Control de eventos

- cooldowns;
- prevención de duplicados;
- control temporal de registros;
- asociación entre cámara y track.

### Coordinación del procesamiento

La lógica que actualmente coordina:

```text
Frame
 ↓
Detection
 ↓
Tracking
 ↓
Recognition
 ↓
State
 ↓
Event
```

debe mantenerse conceptualmente, pero trasladarse fuera de la GUI.

---

# 9. QUÉ DEBE DESAPARECER DE `main_gui.py`

Debe eliminarse de la responsabilidad del motor local:

- lógica de cursos;
- determinación de intrusos;
- reglas de asistencia;
- consultas directas a Firebase;
- construcción de nombres mediante `split("_")`;
- decisiones relacionadas con estudiantes y cursos;
- persistencia directa;
- reglas educativas.

La GUI tampoco debe encargarse del procesamiento de visión.

---

# 10. NUEVA DIVISIÓN INTERNA DEL MOTOR

La estructura objetivo del motor será conceptualmente:

```text
motor_reconocimiento/
│
├── core/
│   ├── orchestrator.py
│   ├── state_manager.py
│   ├── event_processor.py
│   └── models.py
│
├── capture/
│   └── camera_stream.py
│
├── vision/
│   ├── engine.py
│   ├── tracker.py
│   └── recognizer.py
│
├── network/
│   ├── api_client.py
│   ├── event_queue.py
│   └── payload_builder.py
│
├── ui/
│   └── viewer.py
│
└── main.py
```

La estructura exacta de archivos podrá variar durante la implementación, pero la separación de responsabilidades no debe variar.

---

# 11. CAPA DE CAPTURA

`CameraStream` pertenece al Edge.

Su responsabilidad es exclusivamente:

```text
Cámara
 ↓
Frame
```

Debe:

- capturar;
- mantener el frame más reciente;
- controlar acceso concurrente;
- evitar bloquear innecesariamente el procesamiento.

No debe:

- conocer estudiantes;
- conocer cursos;
- acceder a PostgreSQL;
- decidir asistencia;
- decidir intrusión.

---

# 12. CAPA DE VISIÓN

Esta capa contiene:

### Detection

SCRFD / InsightFace.

Entrada:

```text
Frame
```

Salida:

```text
Bounding boxes
Landmarks
Metadata
```

### Tracking

ByteTrack.

Entrada:

```text
Detecciones
```

Salida:

```text
Track IDs
```

Los IDs deben considerarse locales a cada cámara.

Por tanto:

```text
CAM_01 + Track 1
```

no es lo mismo que:

```text
CAM_02 + Track 1
```

La arquitectura debe respetar explícitamente esta separación.

---

# 13. RECOGNITION ENGINE

El reconocimiento seguirá funcionando localmente.

El motor debe poder calcular:

```text
Embedding
      ↓
Comparación
      ↓
Identidad
      ↓
Confianza
```

Pero la identidad debe ser representada mediante un identificador estable.

Preferentemente:

```text
student_uuid
```

y no:

```text
2_INFORMATICA_B_Juan_Perez
```

La estructura de nombres de archivos o carpetas no debe convertirse en un mecanismo de modelado de relaciones de base de datos.

---

# 14. IDENTIDAD Y EMBEDDINGS

La identidad debe separarse completamente de:

- nombre;
- apellido;
- curso;
- grado;
- paralelo.

Conceptualmente:

```text
UUID
 │
 ├── identidad del estudiante
 ├── embeddings
 └── relaciones administradas por Backend
```

El motor puede recibir desde el backend los datos necesarios para realizar reconocimiento local, pero no necesita conocer las relaciones educativas para reconocer una identidad.

---

# 15. REGLAS DE NEGOCIO

Esta es una de las separaciones más importantes.

El motor debe poder producir:

```text
CAM_01
+
student_uuid
+
confidence
+
track_id
+
timestamp
```

Pero no debe producir como decisión propia:

```text
PRESENTE
INTRUSO
JUSTIFICADO
NO JUSTIFICADO
```

Esas decisiones pertenecen al backend.

Ejemplo:

```text
Motor:
"CAM_01 detectó UUID X con confianza 98.5%"

Backend:
"CAM_01 pertenece al curso X"

Backend:
"UUID X pertenece al curso X"

Backend:
=> PRESENTE
```

O:

```text
Motor:
"CAM_01 detectó UUID Y"

Backend:
"UUID Y no pertenece al curso de CAM_01"

Backend:
=> INTRUSO
```

Esto elimina el acoplamiento entre visión artificial y reglas educativas.

---

# 16. ESTADO Y COOLDOWNS

La lógica de:

- `active_tracks`;
- cooldown;
- duración;
- entrada;
- permanencia;
- salida;
- `missed_frames`;

debe mantenerse porque resuelve un problema real del reconocimiento.

Pero debe convertirse en una abstracción independiente.

Por ejemplo:

```text
StateManager
```

o

```text
TrackingStateManager
```

La decisión final del nombre puede realizarse durante la implementación.

Lo importante es que la lógica no pertenezca a la GUI ni al cliente HTTP.

---

# 17. MULTICÁMARA

La arquitectura debe diseñarse desde el principio para múltiples cámaras.

No se debe implementar primero una solución que funcione únicamente para una cámara y posteriormente intentar multiplicarla.

Cada cámara debe poseer su propio contexto:

```text
CameraContext
│
├── Camera ID
├── CameraStream
├── Tracker
├── Track states
└── Recognition context
```

Los estados no deben contaminarse entre cámaras.

Esto incluye:

- tracks;
- cachés;
- cooldowns;
- estados temporales.

---

# 18. RED Y PERSISTENCIA

El motor no debe bloquear el procesamiento esperando una respuesta HTTP.

El flujo será:

```text
Vision
 ↓
Event
 ↓
Local Queue
 ↓
API Client
 ↓
FastAPI
 ↓
PostgreSQL
```

No:

```text
Vision
 ↓
HTTP POST
 ↓
esperar respuesta
 ↓
continuar procesamiento
```

La comunicación debe ser desacoplada mediante una cola.

---

# 19. RESILIENCIA

La pérdida temporal de red no debe detener el motor.

Si FastAPI no está disponible:

```text
Motor
 ↓
Evento
 ↓
Cola local
 ↓
[Servidor no disponible]
 ↓
Evento permanece pendiente
```

Cuando vuelva la conexión:

```text
Cola
 ↓
API
 ↓
Backend
```

Esto es especialmente importante porque el motor es un componente Edge.

---

# 20. CONTRATO MOTOR → BACKEND

El contrato debe ser neutral.

Ejemplo conceptual:

```json
{
  "camera_id": "CAM_001",
  "timestamp": "2026-08-10T03:39:12Z",
  "event_type": "DETECTION",
  "data": {
    "identity_uuid": "e2b4-5c1",
    "confidence": 0.985,
    "track_id": 42
  }
}
```

Y para finalización de un track:

```json
{
  "camera_id": "CAM_001",
  "timestamp": "2026-08-10T03:40:02Z",
  "event_type": "TRACK_EXPIRED",
  "data": {
    "identity_uuid": "e2b4-5c1",
    "duration_seconds": 50.0,
    "track_id": 42
  }
}
```

Estos contratos deberán ser validados contra el SDD antes de implementarse definitivamente.

---

# 21. BACKEND COMO AUTORIDAD

FastAPI será la autoridad para:

- Usuarios
- Estudiantes
- Cursos
- Cámaras
- Matrículas
- Asistencia
- Intrusos
- Notificaciones
- Eventos
- Permisos
- Autenticación

El Edge no debe replicar estas reglas.

Esto permite que un cambio como:

```text
Juan cambia de curso
```

no requiera:

```text
reentrenar
modificar carpetas
modificar nombres
modificar código
reiniciar reglas del motor
```

La relación cambia en PostgreSQL y el backend empieza a aplicar la nueva realidad.

---

# 22. FRONTEND COMO CLIENTE

AdminLTE/PWA no debe convertirse en otro God Object.

Su responsabilidad será:

```text
Mostrar
Consultar
Enviar acciones
Recibir actualizaciones
```

No:

```text
Procesar reconocimiento
Decidir intrusos
Manipular PostgreSQL
Ejecutar reglas de asistencia
```

El frontend consume la API.

---

# 23. ELIMINACIÓN PROGRESIVA DE LEGACY

No se debe eliminar código indiscriminadamente.

El proceso será:

```text
Código actual
     ↓
Inventario
     ↓
Clasificación
     ├── conservar
     ├── refactorizar
     ├── reemplazar
     └── eliminar
     ↓
Nueva arquitectura
```

Cada componente deberá tener una razón técnica para existir en la arquitectura final.

---

# 24. ORDEN DE RECONSTRUCCIÓN

## Fase 0 — Congelación y diagnóstico

Antes de modificar código:

- congelar el estado actual;
- identificar dependencias;
- identificar puntos de entrada;
- identificar módulos usados realmente;
- identificar código muerto;
- identificar duplicaciones;
- documentar comportamiento actual;
- establecer pruebas de referencia.

**No refactorizar todavía.**

## Fase 1 — Extracción del motor

Separar de `main_gui.py`:

- captura;
- detección;
- tracking;
- reconocimiento;
- estados;
- cooldowns;
- eventos.

La GUI debe convertirse progresivamente en consumidor de resultados.

## Fase 2 — Corrección multicámara

Corregir:

- cachés globales;
- `track_id`;
- estados;
- cooldowns;
- contexto de cámara.

Garantizar aislamiento entre feeds.

## Fase 3 — Eliminación de Firebase

Introducir:

```text
APIClient
EventQueue
PayloadBuilder
```

Inicialmente puede existir un backend simulado.

El objetivo es demostrar:

```text
Motor → Evento → Cola
```

sin depender de Firebase.

## Fase 4 — Identidad mediante UUID

Eliminar gradualmente:

```text
Curso_Nombre_Apellido
```

como mecanismo de identidad.

Adoptar identificadores estables.

## Fase 5 — Integración FastAPI

Conectar:

```text
Edge
 ↓
REST API
 ↓
FastAPI
 ↓
PostgreSQL
```

## Fase 6 — Backend completo

Implementar las reglas:

- asistencia;
- intrusión;
- permanencia;
- notificaciones;
- usuarios;
- cursos;
- cámaras;
- permisos.

## Fase 7 — AdminLTE/PWA

Construir la interfaz administrativa y operacional sobre la API.

## Fase 8 — Distribución

Preparar:

```text
Web
PWA
Play Store
Windows .exe
```

---

# 25. CRITERIOS DE ACEPTACIÓN DEL MOTOR

El motor no se considerará correctamente reconstruido solamente porque ejecute.

Debe cumplir como mínimo:

### Aislamiento

No debe depender de:

- Firebase;
- Flutter;
- PostgreSQL directo;
- reglas educativas.

### Multicámara

Dos cámaras pueden tener simultáneamente:

```text
Track 1
```

sin compartir identidad o estado accidentalmente.

### Resiliencia

La pérdida de red no debe congelar la inferencia ni el video.

### Trazabilidad

Debe poder seguirse:

```text
Frame
 ↓
Detection
 ↓
Track
 ↓
Recognition
 ↓
State
 ↓
Event
 ↓
Queue
 ↓
API
```

### Mantenibilidad

Cada componente debe tener una responsabilidad claramente identificable.

---

# 26. CRITERIO ESPECIAL PARA `main_gui.py`

No se acepta una "refactorización" que simplemente cambie nombres de funciones manteniendo el mismo acoplamiento.

El objetivo es que eventualmente:

```text
main_gui.py
```

sea una interfaz de presentación y control de la aplicación local, no el cerebro completo del sistema.

La lógica rescatada deberá vivir en módulos especializados.

---

# 27. REGLA DE ORO PARA ANTIGRAVITY

Cuando este documento pase a Antigravity, deberá entenderse como:

> **dirección arquitectónica, no como sugerencia.**

Antigravity podrá decidir:

- nombres concretos de clases;
- nombres de archivos;
- detalles de implementación;
- patrones internos;
- optimizaciones.

Pero no podrá modificar unilateralmente decisiones arquitectónicas fundamentales como:

```text
Flutter fuera
Firebase fuera
PostgreSQL detrás de FastAPI
AdminLTE/PWA como frontend
Motor Python como Edge
Reglas educativas en backend
Cámaras procesadas en Edge
```

Si durante la implementación descubre una contradicción técnica real con el SDD, deberá documentarla antes de alterar la decisión arquitectónica.

---

# 28. PRINCIPIO FINAL

La reconstrucción no consiste en:

> "arreglar el proyecto viejo".

Consiste en:

> **extraer el conocimiento técnico válido del proyecto viejo y reconstruirlo bajo una arquitectura coherente.**

El código existente es el punto de partida.

El SDD es la definición del sistema.

Las auditorías de Gemini sirven para comprender el estado real y detectar riesgos.

Antigravity será el ejecutor de la reconstrucción.

La dirección queda definida como:

```text
             ┌──────────────────────┐
             │      CÁMARAS         │
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │   PYTHON EDGE        │
             │                      │
             │ OpenCV               │
             │ SCRFD                │
             │ ArcFace              │
             │ ByteTrack            │
             │ Recognition          │
             │ State Manager        │
             │ Event Queue          │
             └──────────┬───────────┘
                        │
                     REST API
                        │
                        ▼
             ┌──────────────────────┐
             │       FASTAPI        │
             │                      │
             │ Business Rules       │
             │ Auth / JWT           │
             │ Events               │
             │ Attendance           │
             │ Notifications        │
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │     POSTGRESQL       │
             └──────────┬───────────┘
                        │
                  REST / WebSocket
                        │
                        ▼
             ┌──────────────────────┐
             │    ADMINLTE 3 / PWA  │
             │                      │
             │ Web                  │
             │ PWA / Play Store     │
             │ Windows .exe         │
             └──────────────────────┘
```

**Esta es la línea arquitectónica que debe utilizarse como base para la reconstrucción. Flutter no forma parte de la arquitectura objetivo.**
