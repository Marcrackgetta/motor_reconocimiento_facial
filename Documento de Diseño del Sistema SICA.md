# Documento de Diseño del Sistema (SDD) - Proyecto SICA/SICAE

## 1. Visión General y Objetivos
* **Nombre del Sistema:** SICA / SICAE (Sistema Interno de Control de Acceso Escolar).
* **Propósito:** Automatizar el registro de asistencia de estudiantes, control de ingresos/salidas y detección de personas no autorizadas (intrusos) en planteles educativos.
* **Integración:** Comunicación asíncrona entre el Motor de Reconocimiento Facial (cliente local) y la Plataforma Web (servidor central).

## 2. Arquitectura Global del Sistema
El sistema se divide en dos componentes principales completamente desacoplados, comunicándose mediante una API REST en formato JSON. La plataforma web nunca recibirá video en vivo de las cámaras.

```text
[ MOTOR DE RECONOCIMIENTO FACIAL (Fase 1) ]
  - InsightFace + OpenCV + ByteTrack
  - Envía eventos HTTP POST a la API
                    |
                    v (API REST JSON)
                    |
[ PLATAFORMA CENTRAL SICA (Fase 2) ]
  - Django + Django REST Framework + AdminLTE
  - Módulos de Usuarios, Cursos y Asistencias
                    |
                    v (ORM)
                    |
[ BASE DE DATOS POSTGRESQL ]
```

## 3. Pila Tecnológica (Tech Stack)

| Capa | Tecnología | Descripción |
| :--- | :--- | :--- |
| Backend Web | Django 5.x (Python) | Framework web principal, ORM y lógica de negocio. |
| API REST | Django REST Framework | Recepción de eventos desde el motor facial. |
| Base de Datos | PostgreSQL | Almacenamiento relacional de usuarios y registros. |
| Frontend / UI | AdminLTE 3 + PWA | Plantilla de panel de control adaptada a dispositivos móviles. |

## 4. Estructura de Carpetas (Monorepo)
```text
proyecto_sica/
├── motor_reconocimiento/           # Fase 1: Procesamiento de Video
│   ├── main_gui.py
│   ├── src/
│   │   ├── capture/
│   │   ├── vision/
│   │   ├── training/
│   │   └── storage/                # Modificar para enviar peticiones HTTP
│   └── requirements.txt
│
├── backend_sica/                   # Fase 2: Plataforma Django
│   ├── manage.py
│   ├── requirements.txt
│   ├── sica_project/               # Configuración principal
│   │   └── settings.py
│   │
│   ├── apps/                       # Aplicaciones de negocio
│   │   ├── usuarios/               # Modelos de Rango
│   │   ├── institucion/            # Cursos, Estudiantes, Cámaras
│   │   ├── control_acceso/         # API REST y Registros Diarios
│   │   └── notificaciones/         # Alertas y Reportes
│   │
│   ├── static/                     # Archivos PWA y AdminLTE
│   │   └── manifest.json
│   │
│   └── templates/                  # Vistas HTML
│       ├── base.html
│       └── dashboards/
└── README.md
```

## 5. Modelo de Base de Datos Relacional
* **Usuarios (usuarios_usuario):** Hereda de AbstractUser. Incluye el Rango (Administrador, Inspector, Representante).
* **Cursos (institucion_curso):** Contiene el nombre del curso y FK al Inspector asignado.
* **Estudiantes (institucion_estudiante):** FK a Curso y FK a Representante.
* **Cámaras (institucion_camara):** Código único, FK a Curso, ubicación y estado de conexión.
* **Registro Diario (control_acceso_registro):** Control de una sesión de cámara en un día (totales de presentes e intrusos).
* **Eventos (control_acceso_evento):** Cada detección específica (Presente, Intruso, Desconocido) con FK a Estudiante o texto libre.
* **Notificaciones (notificaciones_alerta):** FK a Usuario destinatario y estado de lectura.

## 6. Roles y Control de Acceso
* **Administrador:** Acceso completo al sistema, configuración general y capacidad de ver los paneles de otros usuarios.
* **Inspector:** Gestión de sus cursos asignados, generación de reportes y envío de notificaciones.
* **Representante:** Visualización de sus estudiantes, reportes de entrada/salida y justificación de faltas (UI optimizada PWA).

## 7. Especificación de API REST
Endpoints que consumirá el motor Python mediante requests:
* `POST /api/v1/sesion-camara/iniciar/` : Abre la sesión diaria de la cámara.
* `POST /api/v1/asistencia/registrar/` : Envía JSON con el evento (Intruso, Presente, Desconocido) y el nivel de confianza.
* `POST /api/v1/sesion-camara/cerrar/` : Cierra la sesión activa.