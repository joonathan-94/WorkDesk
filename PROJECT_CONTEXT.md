# WorkDesk — Contexto actual del proyecto

## 1. Propósito

Este archivo resume el estado real y actual de **WorkDesk**.

Su objetivo es permitir que cualquier desarrollador, asistente o herramienta pueda incorporarse al proyecto sin depender del historial de conversaciones anteriores.

Este documento **no reemplaza** la documentación oficial ubicada en `docs/`.

Debe utilizarse como:

- resumen del estado actual;
- punto de entrada al proyecto;
- referencia rápida de arquitectura;
- registro de decisiones relevantes;
- guía para distinguir lo implementado de lo planificado;
- referencia para identificar el siguiente paso del desarrollo.

Cuando una decisión necesite mayor detalle, se debe consultar el documento correspondiente dentro de `docs/`.

---

# 2. Descripción general

**WorkDesk** es una aplicación web orientada inicialmente a la gestión de tickets de soporte TI.

El objetivo del MVP es permitir gestionar de forma estructurada:

- usuarios;
- roles;
- tickets;
- asignaciones;
- comentarios públicos;
- notas internas;
- archivos adjuntos;
- estados;
- prioridades;
- categorías;
- ubicaciones;
- SLA;
- notificaciones;
- dashboards;
- carga de trabajo;
- base de conocimiento;
- reportes;
- auditoría;
- administración;
- backups locales.

A futuro, WorkDesk podrá evolucionar hacia una solución más amplia de gestión del trabajo, tareas y proyectos.

Esa evolución futura no debe introducir complejidad prematura en el MVP actual. La gestión de proyectos y tareas está definida como un módulo secundario, solo para el personal, que deja a los tickets como núcleo (`docs/13_evolucion_post_mvp.md`, ola 5). Es solo planificación: todavía no existe en el código.

---

# 3. Estado actual

## Versión estable

```text
v0.5.0 — SLA y notificaciones internas
```

La versión `v0.5.0` está:

- implementada;
- testeada (3965 tests);
- documentada;
- mergeada en `main` (PR #36 a #45).

Las versiones `v0.1.0 — Fundación técnica`, `v0.2.0 — Usuarios, autenticación completa y RBAC`, `v0.3.0 — Núcleo de tickets`, `v0.4.0 — Asignación, colaboración y ciclo de vida` y `v0.5.0` están etiquetadas.

## Rama estable

```text
main
```

`main` debe representar siempre el estado estable del proyecto.

## Rama de trabajo actual

```text
docs/review-readme-and-context
```

Entrega 2 de `v0.6.0 — Dashboards y carga de trabajo`: revisión de la documentación, sin cambios de código. El relato por entrega (hitos de `v0.2.0` a `v0.5.0`, la revisión final de `v0.4.0` y el historial de tests por entrega) pasó de este archivo y del README al nuevo `docs/14_historial_de_implementacion.md`, de modo que este archivo describe lo que existe hoy y cómo funciona, y no cómo se llegó a ello (de 3070 a 2316 líneas; el README, de 1679 a 1497). La fase 6 de `docs/12` incorpora ahora las 10 entregas, las decisiones tomadas al planificarla y la reasignación masiva, que la nota de `v0.4.0` le asignaba pero su alcance no listaba.

Ya integradas en `main`: la sincronización documental (PR #4), la base RBAC (PR #5), los límites de sesión (PR #6), la auditoría administrativa (PR #7), la base de seguridad de contraseñas (PR #8), el cambio de contraseña propio y obligatorio (PR #9), el listado y creación de usuarios (PR #10), la administración de usuarios existentes (PR #11), la base de la interfaz administrativa (PR #12), "Mi cuenta" y los datos demo (PR #13, cierre de `v0.2.0`), los catálogos de tickets (PR #14), el modelo de tickets (PR #15), la administración de catálogos (PR #16), la creación de tickets (PR #17), el listado de tickets (PR #18), la edición de tickets (PR #19), el cierre de `v0.3.0` (PR #20), el seed `seed-demo-tickets` (PR #21), el plan del módulo de proyectos posterior al MVP (PR #22) y las 12 entregas de `v0.4.0` (PR #23 a #35): visibilidad y vocabulario del historial (PR #23), catálogo de motivos de espera (PR #24), estados y transiciones (PR #25), grupos (PR #26), asignación (PR #27) y solicitantes del ticket (PR #28), un arreglo del refresco de fechas del seed con escalamientos hechos a mano (PR #29), comentarios y notas internas (PR #30), adjuntos (PR #31), resolución y cierre (PR #32), relaciones y duplicados (PR #33), el bloqueo temporal de edición (PR #34) y la pantalla de Estados y transiciones con el cierre de la versión (PR #35), y las nueve entregas de `v0.5.0` (y la optimización de la suite de tests, PR #42): el motor de tiempo laboral compartido (PR #36), el calendario laboral administrable (PR #37), las políticas de SLA por prioridad (PR #38), los períodos de SLA (PR #39), el centro de notificaciones (PR #40), los avisos por los eventos de un ticket (PR #41), los indicadores de SLA (PR #43), el planificador (PR #44) y el cierre de la versión (PR #45).

`v0.5.0` se divide en 9 entregas, cada una con su rama, tests y Pull Request (decididas al empezar la fase):

| # | Entrega | Estado |
| --- | --- | --- |
| 1 | Motor de tiempo laboral compartido (`worktime.py`) | Integrada (PR #36) |
| 2 | Calendario laboral administrable: tablas, calendario vigente y pantalla del Administrador | Integrada (PR #37) |
| 3 | Políticas de SLA por prioridad (`politicas_sla`) y su pantalla | Integrada (PR #38) |
| 4 | Períodos de SLA: cálculo, pausa en `En espera` y continuidad ante cambios de prioridad | Integrada (PR #39) |
| 5 | Notificaciones internas: infraestructura y centro de notificaciones | Integrada (PR #40) |
| 6 | Notificaciones internas: generación por eventos (incluye RF-068 y RN-96) | Integrada (PR #41) |
| 7 | Indicadores de SLA en el listado y el detalle | Integrada (PR #43) |
| 8 | Planificador: avisos de SLA y cierre automático | Integrada (PR #44) |
| 9 | Cierre de la versión: revisión de toda la fase y documentación | Integrada (PR #45) |

## Identidad visual (integrada en `main`)

La rama `feature/branding-login` (Pull Request #3) ya fue fusionada en `main`. Incorporó:

- isotipo y logotipo oficial;
- variantes principal e inversa;
- branding específico de Login;
- favicon SVG;
- favicon ICO;
- favicon PNG 32 × 32;
- `apple-touch-icon`;
- iconos de aplicación de 192 × 192 y 512 × 512;
- icono `maskable` de 512 × 512;
- integración global de favicons en los templates actuales;
- imagen `workdesk-social-preview.png`;
- actualización de README;
- actualización de `docs/11_diseno_de_pantallas.md`.

## Historial de versiones

Cada versión se construyó en entregas pequeñas, con su rama, sus tests y su Pull Request. El relato completo de cada una (decisiones, errores hallados, qué cubre cada prueba y cuántos tests había) está en [`docs/14_historial_de_implementacion.md`](docs/14_historial_de_implementacion.md); lo que cada fase planificó y entregó, en `docs/12_roadmap.md`.

| Versión | Qué añadió | Entregas | Pull Requests | Tests al cerrar |
| --- | --- | --- | --- | --- |
| `v0.1.0` | Fundación técnica: Flask, PostgreSQL, autenticación, sesiones, CSRF y logging | — | — | 20 |
| `v0.2.0` | Usuarios, autenticación completa y RBAC, auditoría, «Mi cuenta» y `seed-demo` | 5 | #4 a #13 | 385 |
| `v0.3.0` | Núcleo de tickets: catálogos, creación, listado, detalle y edición | 7 | #14 a #20 | 967 |
| `v0.4.0` | Asignación, colaboración y ciclo de vida: grupos, comentarios, adjuntos, resolución, relaciones y bloqueo de edición | 12 | #23 a #35 | 2201 |
| `v0.5.0` | SLA en tiempo laboral, calendario administrable, notificaciones internas y planificador | 9 | #36 a #45 | 3965 |

Decisiones de las fases que siguen vigentes (cada una con su detalle en las secciones de este archivo):

- **Quién ve qué se decide en la consulta**, nunca en la plantilla, y cada condición SQL tiene su política Python equivalente con un test que comprueba que coinciden.
- **Una acción, una pantalla** (sin modales, y funcionan sin JavaScript): 404 si no se ve el ticket y 403 si se ve y no se puede actuar.
- **`change_state` es el único camino que escribe el estado** y los datos de resolución y cierre: «cerrado ⇒ fecha y motivo» no puede romperse.
- **Lo aditivo no sube la versión del ticket** (comentarios, notas, adjuntos, relaciones y solicitantes); la barrera final de concurrencia es `tickets.version`.
- **El SLA es solo del personal** (RN-169) y **un cambio de prioridad nunca reinicia el reloj ni borra un incumplimiento** (RN-88).
- **Un único motor de tiempo laboral** (`worktime.py`) y **un único lugar que decide el calendario vigente** (`resolve_work_calendar`).
- **Siempre se bloquea el ticket primero** (cambios de estado, planificador, reasignación): evita bloqueos mutuos.
- **Los parámetros que serán configuración** (plazos, límites, tiempos del bloqueo, cierre automático) son variables de entorno hasta `v0.7.0`.

## Revisión de lo construido (entrega 1 de `v0.6.0`)

Primera entrega de la fase: revisar todo lo hecho hasta `v0.5.0` antes de construir encima. Se midió antes de cambiar y se actuó donde la medida lo justificaba. **Sin migraciones y sin cambios de comportamiento** salvo los dos que se indican (cabeceras y forma de los errores JSON). El mapa de rutas (88 líneas) es idéntico antes y después.

- **El seed de tickets pasó a un paquete** (`seeds/demo_tickets/`: `common`, `validation`, `catalogs`, `dates` y `loader`; la API pública no cambió: `seed_demo_tickets`, `validate_demo_tickets`, `DemoTicketsError`). Las seis únicas funciones de todo `src` por encima de complejidad 12 vivían ahí (`_refresh` 52, `_check_adjustment` 29, `_write_new_dates` 24, `_apply_adjustment` 19, `_check_state_steps` 17 y `validate_demo_tickets` 13) y se descompusieron en piezas con nombre. La carga y el refresco de fechas comparten ahora la misma idea (cada fila «sigue» al evento del historial que la originó) en lugar de dos cadenas de condiciones. Los 259 tests del área del seed pasaron sin tocarlos, incluidos los que comprueban que refrescar equivale a cargar de nuevo.
- **`tickets/queries.py`** recoge desde `tickets/service.py` la visibilidad (`visible_tickets_condition`), las condiciones del listado (`listing_conditions`, antes privada), `list_tickets`, `count_tickets_by_tab` y `TicketFilters`. `service.py` queda con la creación, el historial y los ayudantes (de 670 a 402 líneas). Es la pieza que reutilizarán los dashboards, la carga de trabajo y la reasignación.
- **Una forma de error JSON** (`responses.py`) y **cabeceras de seguridad en todas las respuestas** (`security/headers.py`): ver "Respuestas JSON y cabeceras de seguridad". Dos aserciones que fijaban la forma antigua del error (`test_session_limits.py` y `test_ticket_edit_lock.py`) se actualizaron a propósito.
- **`ruff.toml`** conserva las reglas por defecto y añade un límite de complejidad (12, 12 ramas y 50 sentencias) para `src/workdesk`: hoy no hay ninguna función por encima. Se comprobó que el guardián salta con una función de prueba de complejidad 15.
- **Tests:** `test_seed_demo_tickets.py` (3417 líneas) se partió por tema en seis módulos (`data`, `load`, `dates`, `steps`, `people` y `lifecycle`) con sus ayudantes en `tests/seed_helpers.py`; las copias idénticas de `login`, `text`, `audit_entries` y `_run_in_threads` pasaron a `tests/ticket_helpers.py`; `test_pages_smoke` cubre ahora también las pantallas de categorías, prioridades, ubicaciones y motivos de espera y el detalle de cada grupo, usuario y política de SLA, con su presupuesto de consultas; y `test_security_headers.py` (9 tests) vigila las cabeceras y la forma de los errores JSON.
- **Pequeños arreglos** que señaló la auditoría con reglas de Ruff adicionales: cuatro comprensiones innecesarias, un `return` implícito al final de `add_business_seconds` (ahora falla con un mensaje si algún día se llegara a él) y el bloque duplicado de `/health`.
- **Medido y dejado como está:** 3975 tests en 4 min 51 s con `-n 6` (3965 en 4 min 53 s antes). Los más largos son de infraestructura (las dos pruebas de migraciones, 34 s y 23 s, y las 1064 pantallas de acción, 26 s) y 27 de los 40 más lentos son del seed, porque cada uno ejecuta la carga real (de 4 a 14 s): es el coste de probar la carga y no de un fixture mal montado, y solo seis tests la ejecutan dos veces. Los 800 tests del umbral de SLA ya eran unitarios (sin base de datos). Los fixtures con el mismo nombre no eran copias: `login` tiene cuatro variantes distintas, así que solo se consolidó lo idéntico (comparado por AST).

## Próximo hito

```text
v0.6.0 — Dashboards y carga de trabajo
```

`v0.6.0` se divide en 10 entregas, cada una con su rama, tests y Pull Request (planificadas al empezar la fase):

| # | Entrega | Estado |
| --- | --- | --- |
| 1 | Revisión de lo construido: backend/API y tests | Integrada (PR #46) |
| 2 | Revisión: README, PROJECT_CONTEXT y docs | En curso (`docs/review-readme-and-context`) |
| 3 | Listado: filtros de asignación (técnico, grupo, sin asignar) | Pendiente |
| 4 | Dashboard del Solicitante | Pendiente |
| 5 | Carga de trabajo: consultas | Pendiente |
| 6 | Carga de trabajo: pantalla | Pendiente |
| 7 | Dashboard operacional (Técnico, Supervisor, Administrador) | Pendiente |
| 8 | Reasignación masiva: servicio | Pendiente |
| 9 | Reasignación masiva: pantalla | Pendiente |
| 10 | Cierre de la fase | Pendiente |


Su alcance está en `docs/12_roadmap.md` (fase 6): el dashboard del Solicitante (abiertos, en progreso, requiere revisión, cerrados recientes, tickets recientes y notificaciones), el dashboard operacional (abiertos, sin asignar, críticos, fuera de SLA, próximos a vencer, en espera, prioritarios, carga de trabajo y actividad reciente) y la carga de trabajo (tickets activos por técnico, por grupo, críticos, con SLA en riesgo y sin asignar), con navegación hacia los listados relacionados. Un ticket puede tener varios técnicos, así que la suma de la carga por técnico no tiene por qué coincidir con el total de tickets únicos. `v0.5.0` deja preparado:

- los datos de SLA (`evaluate_tickets_sla`, que evalúa por lotes con un número fijo de consultas, y las condiciones SQL de `sla/queries.py`, que filtran y cuentan en la base de datos sin evaluar ticket por ticket);
- el filtro del listado por estado de SLA y por orden de urgencia, a donde pueden enlazar los contadores «fuera de SLA» y «próximos a vencer»;
- las notificaciones (`count_unread`) para el dashboard del Solicitante;
- los 76 tickets de demostración compartidos por los tests (`tests/demo_data.py`) y la prueba de pantallas con presupuesto de consultas (`tests/test_pages_smoke.py`), a la que las pantallas nuevas se añaden;
- el seed `seed-demo-tickets`, que se amplía en cada fase (ver "22. CLI").

Pendiente, sin fase asignada, para decidirlo al planificar:

- los adjuntos desde el formulario de creación del ticket;
- las columnas de impacto y urgencia de `tickets`, cuando existan sus catálogos;
- la liberación manual de un bloqueo de edición por el Supervisor o el Administrador;
- las excepciones de SLA (RF-083), que `docs/12` propone decidir con los dashboards o con la configuración de `v0.7.0`;
- las pestañas del detalle (Actividad, Archivos, Historial y Relaciones; hoy son tarjetas apiladas), el color y el orden de los estados y los modales (`v0.9.0`);
- los parámetros que hoy son variables de entorno, en la configuración administrable (`v0.7.0`).

Asignada a `v0.7.0`: la advertencia de posibles duplicados al crear un ticket (RF-061), junto a la base de conocimiento, con la que comparte la búsqueda.

---

# 4. Stack tecnológico actual

## Backend

- Python
- Flask
- Flask-SQLAlchemy
- SQLAlchemy
- Flask-Migrate
- Alembic
- PostgreSQL
- psycopg
- Flask-Login
- Flask-WTF / CSRFProtect
- argon2-cffi
- python-dotenv
- tzdata (base de zonas horarias para `zoneinfo`; Windows no trae la suya)

## Frontend

- HTML5
- CSS3
- JavaScript
- Jinja2

Bootstrap 5.3.8 y Bootstrap Icons 1.13.1 están integrados y se sirven **localmente** (sin CDN) desde `static/vendor/`, sin modificar y con su licencia MIT. `static/vendor/README.md` documenta versiones, origen y huellas SHA-256, y `.gitattributes` evita que Git altere sus saltos de línea. Las pantallas con el layout principal (administración, usuarios y dashboard) usan Bootstrap con la paleta del Design System (`static/css/theme.css`). El Login, el cambio de contraseña y las páginas de error mantienen su CSS propio (`auth.css`, `errors.css`) y no cargan Bootstrap.

Convención de rutas: las rutas internas se escriben en inglés (`/login`, `/dashboard`, `/users`, etc.) y la interfaz de usuario permanece en español.

## Desarrollo y calidad

- Git
- GitHub
- VS Code
- pytest
- Ruff

---

# 5. Arquitectura

WorkDesk utiliza:

```text
Monolito modular
```

La aplicación se mantiene dentro de un único proyecto Flask y utiliza PostgreSQL como base de datos.

No utiliza microservicios.

## Application Factory

La aplicación utiliza:

```python
create_app()
```

La Application Factory es responsable de:

- crear la aplicación Flask;
- cargar configuración;
- validar configuración obligatoria;
- inicializar extensiones;
- configurar autenticación;
- configurar logging;
- registrar comandos CLI;
- registrar manejadores de errores;
- registrar Blueprints;
- devolver la aplicación lista para ejecución.

## Principio arquitectónico

La arquitectura debe crecer de forma proporcional al producto.

No deben crearse anticipadamente:

- capas vacías;
- services innecesarios;
- repositories genéricos;
- módulos sin uso;
- abstracciones sin una necesidad real;
- nuevas dependencias únicamente por preferencia técnica.

## Ejecución local de forma permanente

WorkDesk es una aplicación **100 % local o de intranet**, por decisión del proyecto (2026-11-15): no depende de Internet ni de servicios externos (correo, SMS, mensajería, nube, autenticación externa o APIs de terceros) y sus notificaciones son siempre internas. Se ejecuta en un equipo local o en un servidor propio de la organización. Detalle y consecuencias en `docs/13_evolucion_post_mvp.md` (principio P1).

La documentación arquitectónica puede describir una estructura objetivo más amplia que la estructura actual.

Eso no obliga a implementarla completa desde el comienzo.

---

# 6. Estructura actual relevante

```text
WorkDesk/
├── docs/
├── instance/
│   ├── backups/
│   ├── logs/
│   └── uploads/
├── migrations/
│   └── versions/
├── src/
│   └── workdesk/
│       ├── account/
│       ├── admin/
│       ├── audit/
│       ├── auth/
│       ├── catalogs/
│       ├── cli/
│       ├── groups/
│       ├── main/
│       ├── models/
│       ├── notifications/
│       ├── security/
│       ├── seeds/
│       ├── sla/
│       ├── tickets/
│       │   └── routes/
│       ├── users/
│       ├── static/
│       │   ├── css/
│       │   ├── img/
│       │   │   └── brand/
│       │   │       ├── apple-touch-icon.png
│       │   │       ├── favicon-32x32.png
│       │   │       ├── favicon.ico
│       │   │       ├── favicon.svg
│       │   │       ├── icon-192x192.png
│       │   │       ├── icon-512x512.png
│       │   │       ├── icon-maskable-512x512.png
│       │   │       ├── workdesk-login-brand-inverse.svg
│       │   │       ├── workdesk-login-brand.svg
│       │   │       ├── workdesk-logo-inverse.svg
│       │   │       ├── workdesk-logo.svg
│       │   │       ├── workdesk-mark-inverse.svg
│       │   │       ├── workdesk-mark.svg
│       │   │       └── workdesk-social-preview.png
│       │   ├── js/
│       │   └── vendor/
│       ├── system/
│       ├── templates/
│       │   ├── account/
│       │   ├── admin/
│       │   ├── auth/
│       │   ├── catalogs/
│       │   ├── errors/
│       │   ├── groups/
│       │   ├── layouts/
│       │   ├── main/
│       │   ├── notifications/
│       │   ├── sla/
│       │   ├── tickets/
│       │   └── users/
│       ├── __init__.py
│       ├── cleaning.py
│       ├── config.py
│       ├── errors.py
│       ├── extensions.py
│       ├── formatting.py
│       ├── logging_config.py
│       ├── navigation.py
│       ├── responses.py
│       ├── scheduler.py
│       ├── search.py
│       └── worktime.py
├── tests/
│   ├── conftest.py            # fixtures: app, client, make_user, instantáneas de datos de demostración
│   ├── database.py            # protección de workdesk_test, esquemas por proceso, limpieza e instantáneas
│   ├── areas.py               # qué módulo de tests pertenece a qué área (marcadores de pytest)
│   ├── demo_data.py           # los 76 tickets de demostración compartidos por los tests
│   ├── seed_helpers.py, sla_helpers.py, ticket_helpers.py   # ayudantes compartidos
│   └── test_*.py              # un módulo por tema (autenticación, tickets, SLA, notificaciones, seeds...)
│
├── .github/
│   └── copilot-instructions.md
├── .env.example
├── .gitattributes
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── PROJECT_CONTEXT.md
├── README.md
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── ruff.toml
```

No deben versionarse:

- `.env`;
- `.venv/`;
- `instance/`;
- logs;
- caches;
- archivos temporales;
- credenciales.

---

# 7. Configuración

La configuración utiliza variables de entorno cargadas mediante `python-dotenv`.

Variables principales:

```text
APP_ENV
APP_TIMEZONE
SECRET_KEY
DATABASE_URL
TEST_DATABASE_URL
LOGIN_MAX_FAILED_ATTEMPTS
LOGIN_LOCK_MINUTES
PASSWORD_MIN_LENGTH
SESSION_COOKIE_SECURE
SESSION_IDLE_MINUTES
SESSION_MAX_HOURS
COMMENT_EDIT_WINDOW_MINUTES
REOPEN_WINDOW_DAYS
AUTO_CLOSE_HOURS
SCHEDULER_INTERVAL_SECONDS
EDIT_LOCK_TTL_SECONDS
EDIT_LOCK_HEARTBEAT_SECONDS
UPLOAD_MAX_BYTES
UPLOAD_MAX_FILES_PER_TICKET
UPLOADS_DIR
LOG_LEVEL
LOG_MAX_BYTES
LOG_BACKUP_COUNT
```

Valores normales de desarrollo:

```text
APP_ENV=development
APP_TIMEZONE=America/Santiago
LOGIN_MAX_FAILED_ATTEMPTS=5
LOGIN_LOCK_MINUTES=15
PASSWORD_MIN_LENGTH=12
SESSION_COOKIE_SECURE=false
SESSION_IDLE_MINUTES=30
SESSION_MAX_HOURS=8
COMMENT_EDIT_WINDOW_MINUTES=30
REOPEN_WINDOW_DAYS=30
AUTO_CLOSE_HOURS=24
SCHEDULER_INTERVAL_SECONDS=60
EDIT_LOCK_TTL_SECONDS=120
EDIT_LOCK_HEARTBEAT_SECONDS=45
UPLOAD_MAX_BYTES=10485760
UPLOAD_MAX_FILES_PER_TICKET=20
LOG_LEVEL=DEBUG
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=5
```

Los secretos reales permanecen fuera del repositorio.

---

# 8. Base de datos

## Motor

```text
PostgreSQL
```

## Bases locales

```text
workdesk_dev
workdesk_test
```

`workdesk_dev` se utiliza para desarrollo normal.

`workdesk_test` se utiliza exclusivamente para testing automatizado.

## Rol local de aplicación

```text
workdesk_app
```

Las credenciales reales no deben quedar documentadas ni versionadas.

---

# 9. Migraciones

Existen actualmente veintitrés migraciones:

```text
create_roles_table
create_users_table
create_admin_audit_log_table
add_must_change_password_flag_to_users
create_ticket_catalogs_tables
create_tickets_tables
add_unique_name_indexes_to_priorities_and_locations
add_visibility_to_ticket_history_and_drop_event_type_check
create_wait_reasons_table_and_history_wait_reason
create_state_transitions_table
create_groups_tables
create_ticket_technicians_table_and_ticket_group
create_comments_table
create_attachments_table
create_validations_table
create_ticket_relations_tables
create_ticket_edit_locks_table
create_work_calendar_tables
create_sla_policies_table
create_sla_periods_table
create_notifications_table
add_warning_threshold_to_sla_periods
add_sla_notice_marks_to_sla_periods
```

Alembic no detecta las secuencias de PostgreSQL: `create_tickets_tables` crea a mano `tickets_public_id_seq` (identificador público de los tickets) antes de la tabla que la usa, y la elimina en el `downgrade`. Cualquier migración autogenerada que dependa de una secuencia nueva debe completarse igual.

La revisión técnica final de `v0.1.0` confirmó:

```text
db current → head
db heads   → mismo head
db check   → sin operaciones pendientes
```

## Regla de evolución de esquema

Los cambios de esquema deben seguir:

```text
modelo
→ migración
→ revisión
→ aplicación
→ tests
```

No utilizar `db.create_all()` como mecanismo normal para evolucionar la base de datos.

No modificar migraciones históricas ya aplicadas salvo que exista un problema confirmado que realmente lo justifique.

---

# 10. Roles

Existe el modelo `Role`.

Roles estructurales:

```text
SOLICITANTE
TECNICO
SUPERVISOR
ADMINISTRADOR
```

Los roles se cargan mediante un seed idempotente:

```bash
python -m flask --app src.workdesk seed-roles
```

---

# 11. Usuarios

Existe el modelo `User` sobre la tabla:

```text
usuarios
```

Campos principales:

- `id`
- `nombre`
- `apellido`
- `username`
- `email`
- `telefono`
- `cargo`
- `departamento_area`
- `password_hash`
- `rol_id`
- `token_version`
- `intentos_fallidos`
- `bloqueado_hasta`
- `debe_cambiar_password`
- `activo`
- `fecha_creacion`
- campos de auditoría de creación, modificación y desactivación

Restricciones relevantes:

- `username` único;
- `email` único;
- `rol_id` FK a `roles`;
- `token_version >= 1`;
- `intentos_fallidos >= 0`;
- índice sobre `rol_id`.

`User.get_id()` incorpora:

```text
id + token_version
```

para permitir invalidación de sesiones.

## Auditoría administrativa

Existe el modelo `AdminAuditLog` sobre la tabla:

```text
auditoria_administrativa
```

Registra acciones administrativas y de seguridad (quién, cuándo, sobre qué, qué cambió y por qué). Los eventos de autenticación quedan fuera de esta tabla (`eventos_autenticacion`, previsto para `v0.8.0`).

Campos: `id`, `fecha_hora`, `actor_usuario_id` (NULL si actúa el sistema), `actor_tipo` (`USUARIO` o `SISTEMA`), `accion`, `entidad_tipo` + `entidad_id` (referencia lógica, sin FK), `detalle`, `valor_anterior` y `valor_nuevo` (JSONB), `ip_origen`, `user_agent`, `resultado` (`EXITOSO` o `FALLIDO`) y `motivo`.

Integridad en base de datos:

- CHECK de coherencia entre `actor_tipo` y `actor_usuario_id`, de valores válidos de `actor_tipo` y `resultado`, y de `entidad_id` con `entidad_tipo`;
- FK del actor con `ON DELETE RESTRICT`;
- índices `(fecha_hora)`, `(actor_usuario_id, fecha_hora)` y `(entidad_tipo, entidad_id)`.

Uso desde el código (`src/workdesk/audit/service.py`):

```python
record_admin_event(
    AuditAction.CAMBIO_ROL,
    actor=current_user,
    entity_type="usuario",
    entity_id=user.id,
    old_value={"rol": "TECNICO"},
    new_value={"rol": "SUPERVISOR"},
    reason="...",
)
```

Reglas:

- **No hace commit:** el evento se confirma o se revierte junto con la operación auditada; el commit lo realiza quien llama.
- **Vocabulario controlado:** `AuditAction` define las acciones válidas; cualquier otra se rechaza.
- **Sin datos sensibles:** se rechazan claves que sugieran contraseñas, hashes, secretos, cookies o tokens en `valor_anterior` y `valor_nuevo` (se permite `token_version`).
- **Origen de la petición:** la IP y el user agent se toman de la petición actual y se truncan al tamaño de la columna.
- **Append-only:** el ORM rechaza actualizar o eliminar registros existentes (`AuditLogImmutableError`). Una corrección se registra como un evento nuevo.

Se invoca desde todas las acciones sobre usuarios: creación (`USUARIO_CREADO`), edición de datos (`USUARIO_MODIFICADO`, con los valores anteriores y nuevos de los campos cambiados), cambio de rol (`CAMBIO_ROL`), desactivación y reactivación (`USUARIO_DESACTIVADO`, `USUARIO_ACTIVADO`) y contraseñas (`PASSWORD_CAMBIADA`, `PASSWORD_RESTABLECIDA`). Desde `v0.3.0` también la administración de catálogos (`CATALOGO_CREADO`, `CATALOGO_MODIFICADO`, `CATALOGO_ACTIVADO` y `CATALOGO_DESACTIVADO`, con el tipo en `entidad_tipo`) y, desde `v0.5.0`, el guardado del calendario laboral (`CALENDARIO_LABORAL_GUARDADO`) y las políticas de SLA (`POLITICA_SLA_CREADA`, `POLITICA_SLA_MODIFICADA`, `POLITICA_SLA_ACTIVADA` y `POLITICA_SLA_DESACTIVADA`, con `politica_sla` en `entidad_tipo`). Las acciones críticas admiten un motivo opcional.

## Gestión de usuarios (Administrador)

Módulo `src/workdesk/users/` (blueprint `users`, prefijo `/users`), accesible solo para el rol Administrador mediante `roles_required`.

- **Listado** (`GET /users`): búsqueda por nombre, apellido, nombre completo, usuario o correo (sin distinguir mayúsculas; `%`, `_` y `\` se buscan literalmente); filtros por rol y estado; orden por apellido y nombre; paginación de 20 en PostgreSQL. El rol se carga con el mismo JOIN del filtro (`contains_eager`), sin una consulta por fila. Los filtros y páginas inválidos se ignoran.
- **Creación** (`GET, POST /users/new`): formulario Flask-WTF con CSRF. `users/service.py` concentra las reglas (`create_user`): normaliza username y correo a minúsculas, comprueba rol existente y unicidad, aplica la política de contraseñas, crea el usuario activo y con el cambio de contraseña pendiente, y audita `USUARIO_CREADO`. No hace commit.
- **Carreras de unicidad:** si dos altas pasan la comprobación a la vez, gana la restricción UNIQUE; un savepoint (`begin_nested`) deshace solo ese intento y se informa como duplicado.
- **Contraseña temporal:** se genera automáticamente (por defecto) o la escribe el Administrador. La generada se muestra una sola vez en la propia respuesta del POST (no se redirige): no se guarda en la sesión (cookie firmada pero legible), en la base de datos ni en la auditoría, y la respuesta lleva `Cache-Control: no-store`.
- **Reglas de datos:** formato del username y del correo en `docs/06` (RN-148). El username no se puede cambiar después de crearlo.
- **Formularios:** el rol y el modo de contraseña se validan en el formulario sin usar `SelectField` ni `RadioField` de WTForms (sus opciones como tuplas están obsoletas en WTForms 3.3); las opciones se pasan como atributo (`role_choices`).
- **Presentación:** las pantallas usan `templates/layouts/app.html` (ver "Layout y navegación") y los macros `templates/_form_macros.html` y `templates/_ui_macros.html`.
- Las plantillas consultan la política `can_manage_users` (disponible vía `context_processor`) solo para decidir qué enlaces mostrar; la autorización real se aplica en las rutas.

### Administración de usuarios existentes (paso 4.4)

Rutas bajo `/users/<id>`, todas exclusivas del Administrador (`admin_only = roles_required(RoleCode.ADMINISTRADOR)`). Las reglas están en `users/service.py` y las rutas solo orquestan. Reglas completas en `docs/06` (RN-149).

- **Detalle** (`GET /users/<id>`): datos, rol, estado y acciones. En la propia cuenta se omiten las acciones no permitidas.
- **Edición de datos** (`/edit`): nombre, apellido, correo, teléfono, cargo y departamento. El username no se edita. Devuelve si hubo cambios; sin cambios no audita. La auditoría guarda solo los campos modificados con su valor anterior y nuevo. El correo se comprueba contra otros usuarios y una carrera se resuelve con la restricción UNIQUE y un savepoint.
- **Cambio de rol** (`/role`): confirmación explícita y motivo opcional. Sube `token_version`, así que el usuario debe iniciar sesión de nuevo con el nuevo rol.
- **Desactivar y reactivar** (`/deactivate`, `/activate`): confirmación y motivo opcional. Desactivar rellena `fecha_desactivacion` y `usuario_desactivacion_id` y sube `token_version`; reactivar los limpia y reinicia intentos fallidos y bloqueo (las sesiones anteriores no reviven). No existe borrado físico de usuarios.
- **Restablecer contraseña** (`/reset-password`): mismo selector de contraseña temporal (generada o escrita) que el alta. La generada se muestra una vez, sin caché, y no se guarda en la auditoría.
- **Salvaguardas:** un Administrador no puede cambiar su propio rol, desactivar su cuenta ni restablecer su propia contraseña desde la administración (se bloquea en el servicio y también en la ruta, desde el GET). Siempre debe quedar al menos un Administrador activo: la comprobación bloquea las filas de los Administradores activos (`SELECT ... FOR UPDATE`) para que dos Administradores no se desactiven mutuamente a la vez; los Administradores inactivos no cuentan.
- Los errores de regla (`UserRuleError`: `SelfProtectionError`, `LastAdministratorError`, `NothingToChangeError`) se muestran como mensaje y se vuelve al detalle.
- **Formularios** (`users/forms.py`): `ProfileForm` y `TemporaryPasswordForm` comparten campos entre alta, edición y restablecimiento; `ChangeRoleForm` y `ReasonForm` para las confirmaciones.
- **Plantillas:** macros compartidos en `_form_macros.html` (campos, selector de contraseña temporal y aviso de contraseña); el script `static/js/common/temporary-password.js` muestra el campo manual solo al elegir esa opción.
- **Modelo:** `User.mark_modified(actor)` registra quién y cuándo modificó el usuario por última vez.

---

# 11 bis. Catálogos de tickets

Seis catálogos que los tickets necesitan, cada uno con su modelo en `src/workdesk/models/`:

| Catálogo | Tabla | Notas |
| --- | --- | --- |
| `Estado` | `estados` | Los seis estructurales (`NUEVO`, `ASIGNADO`, `EN_PROGRESO`, `EN_ESPERA`, `RESUELTO`, `CERRADO`). El código es inmutable; el nombre visible y la descripción se editan desde la administración (`v0.4.0`, entrega 12) y el color y el orden no se editan. Sin columnas de vigencia. |
| `Prioridad` | `prioridades` | Baja, Media, Alta y Crítica. `nivel > 0` y único entre las activas (índice parcial). Nombre único sin distinguir mayúsculas. |
| `Categoria` | `categorias` | `codigo` opcional y único. Nombre único sin distinguir mayúsculas. La categoría de respaldo `SIN_CLASIFICAR` (orden 0) siempre existe y no puede desactivarse. |
| `Ubicacion` | `ubicaciones` | Nombre único sin distinguir mayúsculas. `tipo` guarda el código de `LocationType` (`SUCURSAL`, `OFICINA`, `EDIFICIO`, `PISO`, `AREA`, `INSTALACION`, `OTRA`) o NULL; la lista vive en la aplicación, no en la base de datos. |
| `MotivoCierre` | `motivos_cierre` | Seis códigos base (`RESOLUCION_VALIDADA`, `CIERRE_DIRECTO`, `INACTIVIDAD`, `DUPLICADO`, `CANCELACION`, `CIERRE_EXCEPCIONAL`). Cancelación y duplicidad no son estados: son un cierre con ese motivo. |
| `MotivoEspera` | `motivos_espera` | Motivo **opcional** con el que un ticket pasa a `En espera` (RN-49). Cinco códigos base (`INFORMACION_PENDIENTE`, `ESPERA_TERCERO`, `APROBACION_PENDIENTE`, `RECURSO_PENDIENTE`, `OTRO`); solo `OTRO` tiene `permite_texto_otro` (admite un texto libre). `codigo` opcional y único (los creados desde la interfaz no lo llevan), nombre único sin distinguir mayúsculas y `orden` opcional (no figura en docs/09 12.3; hace falta para que la opción genérica vaya al final). Ninguno está protegido: se pueden desactivar todos. |

Prioridad, categoría, ubicación, motivo de cierre y motivo de espera comparten el mixin `CatalogAuditMixin` (`models/_catalog.py`): `activo`, `fecha_creacion`, `usuario_creacion_id`, `fecha_modificacion`, `usuario_modificacion_id` y el método `mark_modified(actor)`. Desactivar un valor no afecta a los tickets que ya lo referencian: solo impide elegirlo en operaciones nuevas.

**Datos iniciales.** `seed-catalogs` (`seeds/catalogs.py`) carga los seis estados, las cuatro prioridades con sus políticas de SLA (ver "Políticas de SLA"), la categoría `Sin clasificar`, los seis motivos de cierre y los cinco motivos de espera, y los dos tipos de relación entre tickets (`DUPLICADO` y `RELACIONADO`, ver "Relaciones y duplicados"). Es idempotente: cada registro se identifica por su `codigo` (las políticas, por su prioridad) y, si existe, no se toca, de modo que respeta lo que un Administrador haya renombrado o desactivado. Confirma una sola vez al final. **No carga ubicaciones ni otras categorías**: dependen de cada organización y se crean desde la interfaz.

## Administración de catálogos (entrega 3 de `v0.3.0`)

Módulo `src/workdesk/catalogs/` (blueprint `catalogs`, prefijo `/admin`), exclusivo del Administrador mediante `roles_required`. Reglas completas en `docs/06` (RN-152). Sigue el patrón de la administración de usuarios: las reglas están en `catalogs/service.py` y las rutas solo orquestan.

- **Pantallas** (`/admin/categories`, `/admin/priorities`, `/admin/locations`): listado con filtro Todos / Activos / Inactivos (sin paginación: son catálogos cortos), formulario de alta y edición, y confirmación de desactivar o reactivar con motivo opcional. Las tres comparten las plantillas de `templates/catalogs/` (`list.html`, `form.html`, `status_confirm.html` y un parcial de campos por catálogo); `catalogs/screens.py` guarda lo que cambia de una a otra (textos, rutas, columnas).
- **Categorías:** nombre, descripción y orden. Las creadas desde la interfaz no llevan `codigo`. Se ordenan por `orden` (las sin orden al final) y nombre.
- **Prioridades:** no se crean y su nivel y color son fijos (docs/11, UI-019); solo se edita el nombre y la descripción, y se activa o desactiva. Siempre debe quedar al menos una activa: la comprobación bloquea las filas activas (`SELECT ... FOR UPDATE`) para que dos Administradores no desactiven a la vez las dos últimas. Reactivar una prioridad cuyo nivel ocupa otra activa se rechaza con un mensaje (índice único parcial).
- **Ubicaciones:** nombre, descripción y tipo (lista controlada `LocationType`).
- **Motivos de espera** (entrega 2 de `v0.4.0`, `/admin/wait-reasons`): nombre, descripción, orden y la casilla "Permite añadir un texto libre" (`permite_texto_otro`, una `BooleanField`: sin marcar llega como falso). Comparten con las categorías el formulario base de nombre, descripción y orden (`_OrderedItemForm`) y las plantillas de `templates/catalogs/` (parcial `_fields_wait_reason.html` y el macro `checkbox_field` de `_form_macros.html`); el listado añade la columna "Texto libre". Ninguno está protegido: el motivo es opcional, así que no hace falta uno de respaldo. Aún no se usan al poner un ticket en espera: eso llega con los cambios de estado (entrega 3).
- **Nombres únicos** sin distinguir mayúsculas, con comprobación en el servicio y respaldo en un índice único de base de datos. Una carrera entre dos altas la resuelve el índice y un savepoint (`begin_nested`), como en la creación de usuarios.
- **Protecciones:** `SIN_CLASIFICAR` no se desactiva (se comprueba también al abrir la pantalla de confirmación). `SIN_CLASIFICAR` sí puede renombrarse; su código no cambia.
- **Auditoría:** cuatro acciones genéricas (`CATALOGO_CREADO`, `CATALOGO_MODIFICADO`, `CATALOGO_ACTIVADO`, `CATALOGO_DESACTIVADO`) con `entidad_tipo` `categoria`, `prioridad`, `ubicacion` o `motivo_espera`, el nombre del registro en `detalle`, y los valores anterior y nuevo solo de los campos que cambiaron. Sin cambios, no se audita. Las acciones de activar y desactivar admiten un motivo opcional.
- **Formularios** (`catalogs/forms.py`): `CategoryForm`, `PriorityForm` y `LocationForm`; `OptionalIntegerField` (número opcional con mensajes en español) para el orden; el tipo de ubicación se valida sin `SelectField`, como el rol en los formularios de usuarios. La confirmación reutiliza `ReasonForm` de `users/forms.py`.
- **Hub y navegación:** las tarjetas Categorías, Prioridades y Ubicaciones del hub enlazan con sus listados, y "Administración" queda activa en las pantallas del módulo (prefijo `catalogs.` en `navigation.py`).
- Los estados y sus transiciones tienen su propia pantalla (ver "Administración de estados y transiciones").

---

# 11 ter. Modelo de tickets

Modelos en `models/ticket.py`, `models/ticket_requester.py`, `models/ticket_technician.py` y `models/ticket_history.py`, con el servicio en `src/workdesk/tickets/service.py`. La creación, un detalle de solo lectura y el listado están descritos más abajo ("Creación y detalle de tickets" y "Listado de tickets"); la edición está en "Edición de tickets" y los cambios de estado en "Estados y transiciones".

## Ticket (`tickets`)

Entidad central. Campos principales: `public_id`, `titulo` (máximo 200 caracteres), `descripcion`, `creado_por_usuario_id` (creador original, no cambia), `categoria_id`, `prioridad_id`, `estado_id`, `ubicacion_id` (opcional), `resolucion`, las fechas y usuarios de modificación, resolución y cierre, `motivo_cierre_id`, `cerrado_automaticamente`, `version` (control optimista, inicia en 1) y `activo` (desactivación lógica excepcional, no equivale a un ticket cerrado).

- **`public_id`:** lo genera la secuencia de PostgreSQL `tickets_public_id_seq` (segura ante concurrencia), se guarda como texto y la interfaz lo mostrará como `#N`. Para ordenar por antigüedad se usa `id` o las fechas, no `public_id`.
- **Restricciones:** `version >= 1`; `fecha_cierre` y `motivo_cierre_id` van siempre juntos o ambos vacíos; un cierre automático no tiene usuario que cierra. Que un ticket en estado `CERRADO` tenga fecha y motivo de cierre no puede expresarse en la base (depende del código del estado en otra tabla): lo aplica el servicio de cierre de `tickets/lifecycle.py` (ver "Resolución, validación, cierre y reapertura").
- **Grupo (`grupo_id`, opcional, FK a `grupos`):** lo fijan el Supervisor y el Administrador (ver "Asignación"). **Aún sin** impacto ni urgencia: sus catálogos llegan en fases posteriores, y las columnas se añadirán entonces.
- Índices por estado, prioridad, categoría, ubicación, fecha de creación, fecha de cierre y creador; todas las claves foráneas son `ON DELETE RESTRICT`.

## Solicitantes (`tickets_solicitantes`)

Relación N:M temporal: un ticket tiene 0..N solicitantes y el creador no se convierte en solicitante por sí mismo. La participación vigente es la que no tiene `fecha_retiro`; al retirar a alguien el registro se conserva. Un índice único parcial impide que una persona figure dos veces como solicitante vigente del mismo ticket (puede volver a asociarse después de ser retirada). `Ticket.solicitantes_vigentes` devuelve las vigentes. Cómo se agregan y retiran después de crear el ticket está en "Solicitantes del ticket".

## Historial (`historial_ticket`)

Registro cronológico **append-only**: el ORM rechaza actualizar o eliminar eventos (`TicketHistoryImmutableError`), igual que la auditoría administrativa. El actor es un usuario o el sistema (`actor_usuario_id` NULL, sin usuario ficticio) y hay una restricción de coherencia entre ambos. El vocabulario de eventos (`TicketEvent`) contiene hoy `TICKET_CREADO`, `TICKET_MODIFICADO`, `CATEGORIA_CAMBIADA`, `PRIORIDAD_CAMBIADA`, `ESTADO_CAMBIADO`, `TECNICO_ASIGNADO`, `TECNICO_DESASIGNADO`, `GRUPO_CAMBIADO`, `TICKET_ESCALADO`, `SOLICITANTE_AGREGADO`, `SOLICITANTE_RETIRADO`, `COMENTARIO_AGREGADO`, `COMENTARIO_EDITADO`, `COMENTARIO_ELIMINADO`, `ARCHIVO_ADJUNTADO`, `ARCHIVO_ELIMINADO`, `TICKET_RESUELTO`, `VALIDACION_ACEPTADA`, `VALIDACION_RECHAZADA`, `TICKET_CERRADO`, `TICKET_REABIERTO`, `RELACION_AGREGADA`, `RELACION_ELIMINADA` y `SLA_VENCIDO` (interno, lo registra el planificador). Los datos variables van en `valor_anterior`, `valor_nuevo` y `contexto` (JSONB); el motivo de un cambio de prioridad va en `contexto`. La columna opcional `motivo_espera_id` (FK a `motivos_espera`, `ON DELETE RESTRICT`) guarda el motivo del catálogo cuando el evento es la entrada a `En espera`; `record_ticket_event(..., wait_reason=)` la rellena. Lo rellena `change_state` al poner un ticket en espera.

**Vocabulario solo en la aplicación (`v0.4.0`, entrega 1).** La base de datos ya no restringe `tipo_evento` (se eliminó el CHECK `ck_historial_ticket_tipo_evento`; los de actor se conservan): `record_ticket_event` convierte el evento con `TicketEvent(...)` y rechaza con `ValueError` cualquiera que no pertenezca al vocabulario, igual que `AuditAction` en la auditoría administrativa. Añadir un evento es añadirlo al enum, a `TICKET_EVENT_LABELS` y a `DEFAULT_EVENT_VISIBILITY`, y escribir su descriptor en `tickets/history.py` (un test comprueba que no falte ninguno), sin migración.

**Visibilidad por evento.** Cada fila lleva `visibilidad` (`PUBLICO` o `INTERNO`, NOT NULL, por defecto `PUBLICO`, con CHECK `ck_historial_ticket_visibilidad`). El servicio la fija al registrar el evento: `record_ticket_event(..., visibility=)` y, si se omite, el valor de `DEFAULT_EVENT_VISIBILITY`, que obliga a decidir la visibilidad de cada evento nuevo (un test comprueba que el mapa cubre todo el vocabulario). `INTERNO` significa que solo lo ve el personal.
- **El filtro lo aplica la consulta, nunca la plantilla:** `visible_history_condition(user)` (`tickets/service.py`) devuelve la condición SQL (personal: todo; Solicitante: solo `PUBLICO`; anónimo, inactivo o sin rol: nada) y `list_ticket_history(ticket, viewer)` la usa. `viewer` es obligatorio a propósito. Cualquier conteo futuro debe salir de una consulta que use la misma condición. Como `visible_tickets_condition`, no comprueba el acceso al ticket: antes hay que aplicar `can_view_ticket`.
- La política `can_view_internal_activity(user)` (`security/authorization.py`) dice quién ve lo interno (hoy el personal) y la condición SQL se apoya en ella; un test comprueba que ambas coinciden para los cuatro roles.
- Los cuatro eventos actuales quedan `PUBLICO`, como ya los veía el Solicitante (el motivo de un cambio de prioridad sigue ocultándose en la ruta del detalle). La ola 5 de `docs/13` reutilizará el mismo mecanismo.

## Servicio (`tickets/service.py`)

- `create_ticket(...)`: crea el ticket en estado `NUEVO` y registra `TICKET_CREADO`. Exige título y descripción, que el actor esté activo, que categoría, prioridad y ubicación existan y estén activas, y que los solicitantes sean usuarios activos con rol Solicitante (sin duplicados). Lanza `TicketRuleError` sin dejar nada pendiente. **No hace commit.**
- `record_ticket_event(...)`: añade un evento al historial en la sesión actual, sin commit; lo usan la edición y todo el ciclo de vida.
- Quién puede crear tickets a nombre de otras personas lo decide la capa de rutas, no el servicio.
- La descripción admite hasta 2000 caracteres (`MAX_DESCRIPTION_LENGTH`, en `models/ticket.py`) y el título hasta 200; los comprueba el servicio y también el formulario.
- Consultas para las pantallas: `get_ticket_by_public_id` (carga de una vez estado, prioridad, categoría, ubicación, creador y solicitantes, sin una consulta por cada uno; no comprueba permisos), `list_ticket_history`, `list_requester_candidates` (usuarios activos con rol Solicitante, por apellido y nombre) y `categories_for_selection` (categorías activas con `Sin clasificar` siempre al final).

## Creación y detalle de tickets (entrega 4 de `v0.3.0`)

Módulo `src/workdesk/tickets/` (blueprint `tickets`, prefijo `/tickets`): `routes/` (un módulo por área: `listing`, `creation`, `detail`, `editing`, `states`, `assignment`, `requesters`, `comments`, `attachments` y `relations`, más `common.py`), `forms.py` y `service.py`. Reglas completas en `docs/06` (RN-153).

**Políticas** (`security/authorization.py`, usadas por las rutas; las plantillas no autorizan nada):

- `can_create_ticket(user)`: los cuatro roles activos.
- `can_choose_requesters(user)`: Técnico, Supervisor y Administrador (`STAFF_ROLES`). El Solicitante no elige solicitantes.
- `can_view_ticket(user, ticket)`: el personal ve todos; el Solicitante ve los que creó y aquellos donde es solicitante vigente (sin `fecha_retiro`). Un solicitante retirado deja de verlos, pero el creador original no deja de serlo. En la entrega 5 el listado necesitará este mismo criterio como condición SQL; deben mantenerse en sincronía.

**Creación** (`GET, POST /tickets/new`, opción "Crear ticket" del menú, para todos los roles):

- Formulario con tres secciones numeradas (docs/11, UI-004): título y descripción (con contador de caracteres); categoría, prioridad y ubicación; y, solo para el personal, los solicitantes. Los adjuntos se suben desde el detalle del ticket: el formulario de creación no los incluye.
- Las opciones salen de la base de datos y solo se ofrecen valores **activos**. La categoría es obligatoria, empieza sin elegir y `Sin clasificar` va siempre al final. La prioridad viene preseleccionada en `Media` si está activa, pero solo al abrir el formulario: un envío sin prioridad se rechaza.
- **Solicitantes:** si crea un Solicitante, es siempre su propio solicitante y cualquier valor enviado se ignora (un envío manipulado no puede registrar a otras personas). El personal marca 0..N en una lista de casillas con buscador (mejora progresiva); los ids se validan contra los usuarios activos con rol Solicitante. Un ticket sin solicitantes es válido.
- `TicketForm` valida con las opciones recibidas como atributos, sin `SelectField` (igual que el rol en `users/forms.py`). Los saltos de línea de la descripción se normalizan a uno solo para que el límite coincida con el contador. `IntegerListField` recoge las casillas.
- Tras crear, la ruta confirma (commit) y redirige al detalle con el aviso "Ticket #N creado correctamente.". Si el servicio rechaza algo (por ejemplo, un valor desactivado mientras se rellenaba el formulario), se muestra el mensaje y no se guarda nada.

**Detalle** (`GET /tickets/<public_id>`): solo lectura. Cabecera con número, título, estado y prioridad; tarjeta de descripción (conserva los saltos de línea y escapa el HTML); resumen (estado, prioridad, categoría, ubicación y fecha); y un historial simple (evento, fecha y persona). El personal ve además "Creado por" y los solicitantes vigentes ("Sin solicitante" si no hay); el Solicitante no (docs/11, UI-005).

- **Un ticket inexistente, con un identificador que no es un número o al que el usuario no tiene acceso responde 404 en todos los casos.** Los números son correlativos y con un 403 cualquiera podría descubrir cuáles existen.
- El detalle muestra la ruta de navegación "Tickets / #N" (o "Mis tickets / #N") y cuenta como parte de la opción "Tickets" del menú, no de "Crear ticket".

**Fechas en hora local:** el filtro de plantilla `local_datetime` (`src/workdesk/formatting.py`) convierte las fechas (guardadas con zona horaria) a `APP_TIMEZONE` con el formato `dd-mm-aaaa hh:mm` (docs/10, sección 79). Si la zona configurada no existe, muestra UTC. `start_of_local_day` da el primer instante de un día local, para filtrar por fechas, y `app_zone()` devuelve la zona horaria de la aplicación (también la usa `seed-demo-tickets`). Requiere el paquete `tzdata` en Windows.

**Presentación:** macros nuevos en `_form_macros.html` (`checkbox_list_field`, y `textarea_field` ahora admite `required` y `counter`) y en `_ui_macros.html` (`state_badge`, `priority_badge`, con los colores de docs/11); scripts `static/js/common/char-counter.js` y `checklist-filter.js`, ambos mejoras progresivas.

## Listado de tickets (entrega 5 de `v0.3.0`)

`GET /tickets` (`tickets/routes/listing.py`, `list_tickets_page`), para los cuatro roles. Las reglas están en `tickets/service.py` y en `docs/06` (RN-154); la ruta solo lee y valida los parámetros de la URL.

- **Visibilidad en SQL:** `visible_tickets_condition(user)` devuelve la condición de la consulta (personal: todo; Solicitante: creados por él o con él como solicitante vigente, mediante `EXISTS`; cualquier otro caso: nada). Es el mismo criterio que la política `can_view_ticket`, y un test comprueba que ambos coinciden para todos los roles y casos (creador, solicitante vigente, retirado, ajeno, inactivo). Si se cambia uno hay que cambiar el otro.
- **`list_tickets(user, filters, tab=, sort=, page=)`:** pagina en PostgreSQL (20 por página). Estado y prioridad se cargan con el mismo JOIN del filtro (`contains_eager`), la categoría con `joinedload` y los solicitantes con `selectinload`: la página, el total y los solicitantes son tres consultas fijas, sin una por fila (hay un test que lo comprueba).
- **`count_tickets_by_tab(user, filters)`:** los contadores de las tres pestañas en una sola consulta (`COUNT ... FILTER`), con la visibilidad, la búsqueda y los filtros aplicados.
- **Pestañas:** `todos`, `abiertos` (por defecto) y `cerrados`; *abierto* es todo ticket cuyo estado no es `CERRADO` (un `RESUELTO` sigue abierto).
- **Búsqueda** (`TicketFilters.query_text`, máx. 100 caracteres): número exacto (con o sin `#`) o `ILIKE` en título y descripción con los comodines escapados (`search.escape_like`, compartido con el listado de usuarios); para el personal también el nombre, apellido, nombre completo o usuario de los solicitantes vigentes.
- **Filtros** (`TicketFilters`): estado, prioridad, categoría, ubicación y fechas de creación (días de `APP_TIMEZONE`; "hasta" incluye el día completo). Las opciones de los desplegables incluyen los valores desactivados (marcados "(inactiva)") porque los tickets antiguos los usan. Los valores inválidos de la URL se ignoran.
- **Orden:** `recientes` (por defecto), `antiguos`, `prioridad` (por nivel) y `actualizados` (`Ticket.fecha_actualizacion`: la última modificación o, si no hay, la creación); siempre con desempate por antigüedad.
- **Parámetros de la URL:** `q`, `vista`, `estado`, `prioridad`, `categoria`, `ubicacion`, `desde`, `hasta`, `orden` y `page`. Los enlaces de pestañas y de páginas conservan los que están aplicados.
- **Plantilla** `tickets/list.html`: tabla desde pantallas medianas y tarjetas en móvil; columna "Solicitante(s)" solo para el personal; "Más filtros" es un `<details>` que se abre solo si hay un filtro de ese grupo aplicado; paginación con números de página.
- **Menú y buscador:** "Tickets" (personal) y "Mis tickets" (Solicitante) apuntan al mismo listado (`navigation.py`) y se marcan activas también en el detalle. El buscador de la barra superior (`layouts/app.html`, visible desde pantallas medianas) envía `q` a este listado con `vista=todos`, para que un ticket cerrado también se encuentre.

## Edición de tickets (entrega 6 de `v0.3.0`)

Reglas completas en `docs/06` (RN-155). Las reglas están en `tickets/editing.py`; las rutas (`tickets/routes/editing.py`) solo orquestan.

**Políticas** (`security/authorization.py`): `can_edit_ticket(user)` y `can_change_priority(user)`, hoy iguales (Técnico, Supervisor y Administrador) pero separadas porque el diseño las nombra aparte. Que el ticket esté cerrado no es una política de rol sino una regla del ticket y la aplica el servicio.

**Rutas** (`GET, POST`): `/tickets/<n>/edit` (título, descripción, categoría y ubicación) y `/tickets/<n>/priority` (prioridad con motivo). Ambas, igual que el detalle, responden **404** si el usuario no puede ver el ticket y además **403** si lo ve pero no puede editarlo (el Solicitante). Con un ticket cerrado vuelven al detalle con un aviso, también desde el GET. El detalle muestra los botones "Editar" y "Cambiar prioridad" solo al personal y mientras el ticket no esté cerrado (solo presentación: la autorización real está en las rutas).

**Servicio** (`tickets/editing.py`, sin commit):

- `update_ticket(ticket, actor=, expected_version=, title=, description=, category_id=, location_id=)`: mismas reglas de título y descripción que la creación (`clean_title_and_description`, compartida con `create_ticket`). La categoría y la ubicación nuevas deben estar activas, pero las que el ticket ya tiene pueden conservarse aunque se hayan desactivado. Solo aplica y registra lo que cambió; devuelve `False` si no hay cambios. Registra `TICKET_MODIFICADO` (título, descripción y ubicación, con los valores anterior y nuevo solo de lo cambiado) y, si cambia la categoría, `CATEGORIA_CAMBIADA` con los nombres.
- `change_priority(ticket, actor=, expected_version=, priority_id=, reason=)`: motivo obligatorio (recortado, máx. 500 caracteres), prioridad nueva activa y distinta de la actual (la misma prioridad devuelve `False`, sin cambio ni registro). Registra `PRIORIDAD_CAMBIADA` con un resumen de la prioridad anterior y la nueva (id, código y nombre) y el motivo en `contexto`.
- **Ticket cerrado:** `TicketClosedError` (definido en `tickets/versioning.py`). Hoy nadie puede cerrar tickets desde la interfaz; la regla queda aplicada para cuando exista el cierre (`v0.4.0`).
- **Control de versión:** `apply_ticket_changes` (en `tickets/versioning.py`, junto con `TicketClosedError` y `TicketConflictError`, compartido con los cambios de estado) hace un único `UPDATE ... WHERE id = :id AND version = :esperada` que aplica los cambios, sube `version` en uno y registra quién y cuándo (`usuario_modificacion_id`, `fecha_modificacion`). Si no coincide ninguna fila se lanza `TicketConflictError`. Si dos guardados llegan a la vez, el segundo espera al primero y, al reevaluar la condición, ya no encuentra la versión esperada. Un guardado con dos eventos (datos y categoría) sube la versión una sola vez.
- **Conflicto en la interfaz:** los formularios llevan la versión con la que se abrieron en un campo oculto. Ante un conflicto se vuelve al formulario con los datos actuales y un aviso (lo escrito se pierde, a propósito: reenviarlo pisaría el cambio ajeno sin haberlo visto). El bloqueo temporal de edición queda para `v0.4.0`.

**Formularios** (`tickets/forms.py`): `_TicketFieldsForm` concentra los campos comunes a la creación y a la edición; `TicketForm` (creación), `TicketEditForm` y `PriorityChangeForm`, estos dos con la versión como campo obligatorio. La prioridad no se puede cambiar desde la edición de datos.

**Historial en el detalle:** `describe_history_changes(entry)` devuelve las líneas de lo que cambió (`Título: «a» → «b»`, `Descripción modificada.`, `Ubicación: — → «c»`, `Categoría: …`, `Prioridad: …`) y **nunca incluye el motivo**. La ruta del detalle pasa el motivo a la plantilla solo si el usuario es del personal: el Solicitante ve qué cambió, no por qué. La descripción completa no se repite en el historial. El resumen del detalle muestra también "Actualizado" (`Ticket.fecha_actualizacion`).




## Bloqueo temporal de edición (entrega 11 de `v0.4.0`)

Reglas completas en `docs/06` (RN-163), `docs/09` (28.2) y `docs/10` (secciones 71 a 77). El servicio está en `tickets/locking.py`; las rutas (`tickets/routes/editing.py`) solo orquestan. **Incluye una migración** (`create_ticket_edit_locks_table`). Es una mejora de la experiencia: la barrera de integridad sigue siendo `tickets.version`.

**Modelo** (`models/edit_lock.py`, `TicketEditLock`, tabla `bloqueos_edicion_tickets`): `ticket_id`, `usuario_id`, `fecha_inicio` (la pone la base de datos), `fecha_expiracion` y `fecha_liberacion`. `CHECK` de expiración posterior al inicio y de liberación no anterior al inicio; **índice único parcial** `(ticket_id) WHERE fecha_liberacion IS NULL` (nunca dos bloqueos no liberados del mismo ticket) e índice por usuario. Las claves foráneas son `ON DELETE RESTRICT`. Un bloqueo está **vigente** si no se liberó y su expiración es futura.

**Servicio** (`tickets/locking.py`, sin commit):

- `acquire_edit_lock(ticket, actor) -> EditLockStatus(lock, mine)`: bloquea la fila del ticket (`lock_ticket`) para serializar a quienes adquieren a la vez; si ya es del actor, renueva su expiración (también si había expirado pero nadie lo tomó); si lo tiene otra persona y está vigente, devuelve el suyo con `mine=False`; si el que había expiró, lo **libera de forma lógica** y crea el nuevo en la misma transacción. Es idempotente: **renovar y adquirir son la misma operación**.
- `release_edit_lock(ticket, actor) -> bool`: libera el del actor; nunca toca el de otra persona; liberar sin tener bloqueo no es un error.
- `current_edit_lock(ticket)`: el bloqueo vigente (de quien sea) con la persona cargada, sin modificar nada; sirve para el aviso del detalle.
- Los tiempos salen de `clock_timestamp()` de la base de datos, no del reloj del servidor web.

**Rutas.** `edit_ticket` y `change_ticket_priority` adquieren el bloqueo al empezar (`_hold_edit_lock`, que confirma en ese momento): si es de otra persona, responden con la pantalla de solo lectura `edit_locked.html` (200; un POST añade «No se guardó nada: otra persona está editando este ticket.» y no guarda); al guardar con éxito liberan el bloqueo en la misma transacción. Un error de validación o un conflicto de versión no lo liberan. Dos rutas JSON, solo POST y con CSRF (cabecera `X-CSRFToken` o campo `csrf_token`): `POST /tickets/<n>/lock/renew` (200 `{"ok": true}`; 409 con la forma común de error: `lock_held` y el mensaje «X está editando este ticket.», o `ticket_closed` si el ticket está cerrado; ver "Respuestas JSON y cabeceras de seguridad") y `POST /tickets/<n>/lock/release` (`{"ok": true, "released": bool}`). Ambas: 404 si no se ve el ticket, 403 si no puede editarlo (el Solicitante).

**Pantalla.** `edit.html` y `priority.html` llevan en el formulario `data-edit-lock` y las URL, el token y el latido; el parcial `_edit_lock_notice.html` explica que el ticket queda reservado y trae el aviso rojo (oculto) del bloqueo perdido. `static/js/tickets/edit-lock.js` (mejora progresiva, sin dependencias externas) renueva cada `data-lock-heartbeat` segundos, libera al salir con `sendBeacon` salvo que se esté enviando el formulario y, si el servidor responde 409, avisa y desactiva el botón de guardar. El detalle muestra «X está editando este ticket» solo al personal que podría editar y nunca a quien tiene el bloqueo.

**Configuración:** `EDIT_LOCK_TTL_SECONDS` (120) y `EDIT_LOCK_HEARTBEAT_SECONDS` (45), variables de entorno validadas al iniciar (enteros mayores que cero y el latido menor que la duración); pasarán a la configuración administrable en `v0.7.0`.

**Seed demo:** no cambia: un bloqueo es un estado transitorio y no tiene sentido sembrarlo.

## Relaciones y duplicados (entrega 10 de `v0.4.0`)

Reglas completas en `docs/06` (RN-162) y `docs/09` (19). El servicio está en `tickets/relations.py` y las rutas (`tickets/routes/relations.py`) solo orquestan. **Incluye una migración** (`create_ticket_relations_tables`).

**Modelos.** `TipoRelacionTicket` (`models/tipo_relacion.py`, tabla `tipos_relacion_ticket`, con `CatalogAuditMixin`; `codigo` único, `nombre`, `descripcion` y `es_simetrica`) y `RelationType` (`DUPLICADO` y `RELACIONADO`). `TicketRelation` (`models/ticket_relation.py`, tabla `tickets_relaciones`): `ticket_origen_id`, `ticket_destino_id`, `tipo_relacion_id`, `comentario`, `usuario_creacion_id`, `fecha_creacion` (la pone la base de datos), `activo`, `fecha_desactivacion` y `usuario_desactivacion_id`. En `DUPLICADO` el origen es el ticket duplicado y el destino el principal; en `RELACIONADO` el par se guarda con el id menor primero. Restricciones: origen distinto de destino, coherencia de la desactivación y un **índice único parcial sobre el par vigente** (`least(origen, destino)`, `greatest(origen, destino)` y el tipo, `WHERE activo`) que impide repetir una relación aunque se invierta. Las claves foráneas son `ON DELETE RESTRICT`. Esa migración se escribió con el índice funcional (Alembic lo genera bien) y `db check` queda limpio.

**Datos iniciales.** `seed-catalogs` carga los dos tipos (`INITIAL_RELATION_TYPES`; el comando informa `tipos de relación: N`). Quien tenga una base anterior debe volver a ejecutarlo. No hay pantalla de administración: los tipos son estructurales.

**Política** (`security/authorization.py`): `can_manage_relations(user)` (Técnico, Supervisor y Administrador; sirve para ver y para gestionar). Que el ticket esté abierto lo aplica el servicio.

**Servicio** (`tickets/relations.py`, sin commit):

- `list_relations(ticket)`: las relaciones vigentes con el otro ticket (y su estado), el tipo y quién la creó en **una sola consulta** (hay un test); devuelve `RelationView(kind, relation, other, removable)` con `kind` `duplicado_de` (este ticket es duplicado de `other`), `principal_de` (`other` es duplicado de este) o `relacionado`. `removable` es falso para la relación de un duplicado que sigue cerrado.
- `add_relation(ticket, other_number, *, actor, comment=)`: empieza con `begin_ticket_operation` (el ticket debe estar abierto); el otro, por su número, en cualquier estado; no consigo mismo ni repetida (comprobación más índice único con savepoint). Registra `RELACION_AGREGADA` (interno, solo en este ticket).
- `remove_relation(ticket, relation_id, *, actor)`: eliminación lógica bajo `SELECT ... FOR UPDATE` de la relación (dos personas que la quitan a la vez la quitan una sola vez; hay un test con dos hilos). Un duplicado cerrado no se quita. Registra `RELACION_ELIMINADA`.
- `mark_duplicate(ticket, principal_number, *, actor, expected_version, comment=)`: bloquea las dos filas **en orden de id**, valida que no haya cadenas ni ciclos (el principal no es duplicado, el ticket no es principal de otros y no figura ya como duplicado), crea la relación, registra `RELACION_AGREGADA` y cierra el ticket con `change_state(..., action=CIERRE_DIRECTO, close_reason_code="DUPLICADO", extra_context={"duplicado_de", "relacion_id"})`. Reutiliza así el único camino de cierre (la regla «cerrado ⇒ fecha y motivo» de la entrega 9). `change_state` ganó los parámetros `close_reason_code` y `extra_context`, que no usa ninguna pantalla: solo este flujo; el motivo es estructural, como los demás que fija el flujo, y solo el cierre directo lo admite.
- `parse_ticket_number` acepta `12` o `#12`.

**Pantallas** (404 si el usuario no ve el ticket, 403 si es Solicitante; un ticket cerrado vuelve al detalle con un aviso salvo la pantalla de relaciones, que sigue visible): `GET /tickets/<n>/relations`, `POST /tickets/<n>/relations/add`, `GET, POST /tickets/<n>/relations/<id>/remove` (confirmación) y `GET, POST /tickets/<n>/duplicate` (confirmación; lleva la versión y conserva lo escrito ante un error). El detalle muestra la tarjeta **Relaciones (n)** solo al personal. Formularios: `RelationForm` y `DuplicateForm`. `TICKET_SCREENS` incluye las tres pantallas.

**Historial.** `RELACION_AGREGADA` y `RELACION_ELIMINADA` son **internos** (el Solicitante no los recibe) y se registran solo en el ticket desde el que se actúa (`valor_nuevo` o `valor_anterior` con `{relacion_id, tipo, ticket, titulo}`; `contexto["relacion_id"]`). El cierre de un duplicado es `TICKET_CERRADO` (público, motivo «Duplicado») con `contexto["duplicado_de"]`: el Solicitante ve que se cerró como duplicado, pero no de cuál.

**Seed demo:** `DemoAdjustment` admite `relacionar` y `duplicado_de` (la clave de otro ticket de la lista, anterior y más antiguo), con cuatro tickets nuevos (76 en total; ver "22. CLI").

## Resolución, validación, cierre y reapertura (entrega 9 de `v0.4.0`)

Reglas completas en `docs/06` (RN-161) y `docs/09` (16.1). Todas las acciones son cambios de estado y pasan por `change_state` (`tickets/lifecycle.py`; la sección "Estados y transiciones" describe el mecanismo común). **Incluye una migración** (`create_validations_table`).

**Modelo** (`models/validation.py`, `Validation`, tabla `validaciones`): `ticket_id`, `solicitante_id`, `ciclo_resolucion`, `tipo_validacion` (`ValidationType`: `ACEPTADA` o `RECHAZADA`), `motivo_rechazo`, `comentario_adicional` y `fecha_validacion` (la pone la base de datos). `CHECK` de ciclo mayor o igual a 1, de tipo válido y de que un rechazo siempre lleve motivo no vacío; `UNIQUE (ticket_id, solicitante_id, ciclo_resolucion)`. No hay tabla de resoluciones: el ciclo en curso es el número de eventos `TICKET_RESUELTO` del ticket (cada entrada a `Resuelto` abre uno nuevo). `Ticket.motivo_cierre` es una relación nueva.

**Acciones** (`STATE_ACTIONS`, además de las operativas):

| Acción (`slug`) | Quién | Desde → hacia | Texto |
| --- | --- | --- | --- |
| `RESOLVER` (`resolve`) | personal | Nuevo, Asignado, En progreso o En espera → Resuelto | explicación de la solución, opcional, máx. 2000, en `tickets.resolucion` |
| `CIERRE_DIRECTO` (`close`) | personal | los mismos cuatro → Cerrado | opcional, solo personal; motivo `CIERRE_DIRECTO` (por defecto) o `CANCELACION` |
| `CONFIRMAR` (`confirm`) | un solicitante vigente | Resuelto → Cerrado | comentario opcional (en `validaciones`); motivo `RESOLUCION_VALIDADA` |
| `RECHAZAR` (`reject`) | un solicitante vigente | Resuelto → En progreso | **obligatorio**, público; limpia la resolución |
| `CIERRE_EXCEPCIONAL` (`close-exceptional`) | Supervisor y Administrador | Resuelto → Cerrado | **obligatorio**, solo personal; motivo `CIERRE_EXCEPCIONAL` |
| `REABRIR` (`reopen`) | personal siempre; un solicitante vigente solo un ticket **Cerrado** dentro de `REOPEN_WINDOW_DAYS` desde el cierre | Resuelto o Cerrado → En progreso | sin texto |

**Políticas** (`security/authorization.py`): `can_resolve_ticket`, `can_close_directly`, `can_close_exceptionally`, `is_current_requester` (Solicitante activo con participación vigente, sin `fecha_retiro`), `can_validate_resolution(user, ticket)` y `can_reopen_ticket(user, ticket, now=, window_days=)`. `CLOSED_STATE` y `RESOLVED_STATE` repiten los códigos de estado para que ese módulo no dependa de los modelos (un test comprueba que coinciden). Las políticas de las acciones de estado tienen ahora la firma `(usuario, ticket)` (`_by_role` adapta las que solo miran el rol).

**La regla del cierre.** Un ticket `CERRADO` siempre tiene fecha y motivo de cierre (lo que antes quedó pendiente de esta entrega). Todo cierre pasa por `_closing_changes` y toda salida de `Resuelto` o `Cerrado` hacia el trabajo (`RECHAZAR` y `REABRIR`) por `_CLEARED_FIELDS`, en el mismo `UPDATE` versionado que cambia el estado: no hay otro camino que escriba esos campos, así que nunca queda un ticket cerrado sin fecha ni motivo, ni uno abierto con datos de cierre. Los motivos de la confirmación y del cierre excepcional son estructurales (se buscan por código aunque estén desactivados, para que desactivarlos en el catálogo no impida cerrar); los del cierre directo deben estar activos y solo se ofrecen `CIERRE_DIRECTO` y `CANCELACION`. `DUPLICADO` (entrega 10) e `INACTIVIDAD` (`v0.5.0`) no se pueden elegir.

**Servicio.** `change_state(..., close_reason_id=)` añade el motivo de cierre. Tras bloquear el ticket y refrescar sus solicitantes: un ticket cerrado solo admite `REABRIR` (el resto lanza `TicketClosedError`), la versión debe coincidir, **la política de la acción se vuelve a comprobar** (`StateTransitionError`: «No puedes realizar esta acción sobre este ticket.», pues una confirmación registra al actor como solicitante) y debe existir la transición activa. Dos solicitantes que confirman a la vez cierran el ticket una vez (el segundo recibe `TicketClosedError`; hay un test con dos hilos). `list_close_reasons(info)` entrega los motivos que ofrece la pantalla.

**Historial.** Cada acción deja su evento propio, con los estados anterior y nuevo, en vez de `ESTADO_CAMBIADO` (que queda para las acciones operativas): `TICKET_RESUELTO` (`valor_nuevo` con `resolucion` y `ciclo`), `VALIDACION_ACEPTADA` y `VALIDACION_RECHAZADA` (con `contexto["validacion_id"]` y, en el rechazo, `motivo_rechazo`), `TICKET_CERRADO` (`valor_nuevo["motivo_cierre"]` y `contexto["motivo_cierre"]`) y `TICKET_REABIERTO` (`contexto["desde"]`). Confirmar deja `VALIDACION_ACEPTADA` y luego `TICKET_CERRADO`; rechazar, `VALIDACION_RECHAZADA` y luego `TICKET_REABIERTO`. Los cinco son **públicos**. El texto de un cierre directo o excepcional va en `contexto["motivo"]` (solo lo ve el personal); el motivo de un rechazo, en `contexto["motivo_rechazo"]` (lo ve quien ve el ticket). `describe_history_changes` muestra el cambio de estado, la resolución y el motivo de cierre.

**Pantallas** (`GET, POST /tickets/<n>/status/<slug>`; 404 si no se ve el ticket, 403 si la política de la acción no lo permite, aviso si la acción ya no corresponde al estado; un ticket cerrado solo abre `reopen`). La pantalla (`state_change.html`) muestra, según la acción, el selector de motivo de cierre y el campo de texto (etiqueta, obligatoriedad y límite de `StateActionInfo`); `StateChangeForm` recibe esos datos y valida el límite y la obligatoriedad. La cabecera del detalle ofrece los botones de estado (principales o secundarios según `StateActionInfo.primary`); confirmar y rechazar no son botones de cabecera: el solicitante los ve en el aviso de `Resuelto` (UI-005A). El detalle añade la tarjeta **Resolución** y, en el resumen, **Fecha de resolución** y **Fecha de cierre** (esta con su motivo). `_render_detail` separa `validation_actions` de `state_actions`.

**Configuración:** `REOPEN_WINDOW_DAYS` (30, variable de entorno validada al iniciar como los límites de sesión; pasará a la configuración administrable en `v0.7.0`).

**Seed demo:** `DemoAdjustment` admite `motivo_cierre` y las acciones `RESOLVER`, `CIERRE_DIRECTO`, `CIERRE_EXCEPCIONAL`, `CONFIRMAR`, `RECHAZAR` y `REABRIR` en `estado` (ver "22. CLI"), con siete tickets nuevos (72 en total).

## Archivos adjuntos (entrega 8 de `v0.4.0`)

Reglas completas en `docs/06` (RN-160), `docs/09` (18.1) y `docs/10` (secciones 61 a 69). Los archivos se tratan en `tickets/storage.py` (sin base de datos) y los metadatos y reglas en `tickets/attachments.py`; las rutas solo orquestan. **Incluye una migración** (`create_attachments_table`).

**Modelo** (`models/attachment.py`, `Attachment`, tabla `archivos`): `ticket_id`, `comentario_id` (opcional: el adjunto de un comentario o nota hereda su visibilidad), `nombre_original` (depurado, solo metadato), `nombre_interno` (UUID, único), `ruta_archivo` (relativa), `mime_type` (deducido de la extensión), `tamano_bytes`, `hash` (SHA-256), `usuario_subida_id`, `fecha_subida`, y la eliminación lógica (`activo`, `fecha_eliminacion`, `usuario_eliminacion_id`). `CHECK` de tamaño y de coherencia de la eliminación.

**Almacenamiento** (`tickets/storage.py`): lista blanca `ALLOWED_TYPES` (`png`, `jpg`, `jpeg`, `gif`, `pdf`, `txt`, `log`, `csv`, `docx`, `xlsx`, `pptx`) con comprobación de la firma de bytes (los de texto, sin bytes nulos); el MIME declarado por el cliente se ignora. `store_upload` escribe por bloques en `UPLOADS_DIR/_tmp`, calcula el SHA-256 y comprueba el tamaño mientras lee, y solo entonces mueve el archivo a `AAAA/MM/<uuid>`; un rechazo no deja nada. `absolute_path` resuelve contra la raíz y rechaza rutas que salgan de ella. `clean_filename` quita directorios y caracteres de control. `MAX_FILES_PER_REQUEST` = 5.

**Configuración:** `UPLOAD_MAX_BYTES` (10 MB), `UPLOAD_MAX_FILES_PER_TICKET` (20) y `UPLOADS_DIR` (por defecto `instance/uploads`); las dos primeras se validan al iniciar. `MAX_CONTENT_LENGTH` se calcula con ellas y una petición mayor responde 413 (`errors.py`). En los tests, `UPLOADS_DIR` es un directorio temporal (fixture `app`).

**Políticas** (`security/authorization.py`): `can_attach_files` (quien comenta públicamente), `can_view_attachment` (hereda la visibilidad del comentario y se oculta si este se elimina) y `can_delete_attachment` (el Supervisor y el Administrador siempre; el resto, los que subieron ellos dentro de `COMMENT_EDIT_WINDOW_MINUTES`). `visible_attachments_condition` es el equivalente SQL de `can_view_attachment`; un test comprueba que coinciden.

**Servicio** (`tickets/attachments.py`, sin commit; empieza con `begin_ticket_operation`): `add_attachments(ticket, actor=, uploads=, comment=)` valida cantidad por envío y por ticket, guarda, registra `ARCHIVO_ADJUNTADO` por archivo con la visibilidad del comentario y, si algo falla, no deja archivos físicos; `delete_attachment` (lógica, conserva el archivo) registra `ARCHIVO_ELIMINADO`; `discard_files(rutas)` borra los físicos si la transacción no se confirma (las rutas lo llaman ante un fallo de la base de datos). No sube la versión del ticket.

**Rutas** (404 si no se ve el ticket o el archivo —nota interna para un Solicitante, otro ticket o eliminado—, 403 si se ve y no se puede actuar; un ticket cerrado vuelve al detalle con un aviso):

- `POST /tickets/<n>/attachments`: sube a la tarjeta «Archivos».
- `POST /tickets/<n>/comments` admite también `archivos`: cuelgan del comentario; si uno no es válido no se guarda ni el comentario y se vuelve al detalle con el texto.
- `GET /tickets/<n>/attachments/<id>/download`: descarga autenticada, siempre `attachment`, `X-Content-Type-Options: nosniff` y sin caché; funciona también en un ticket cerrado. Un archivo físico que falta responde 404.
- `GET, POST /tickets/<n>/attachments/<id>/delete`: confirmación.

**Detalle:** tarjeta «Archivos (n)» bajo «Actividad» (lista, formulario y límites) y los adjuntos de cada comentario bajo él (macro `file_list`). Las pestañas siguen pendientes.

**Seed demo:** `DemoAdjustment.adjunto = (nombre, texto)` con dos tickets nuevos (65 en total).

## Comentarios y notas internas (entrega 7 de `v0.4.0`)

Reglas completas en `docs/06` (RN-159) y `docs/09` (17.1). Las reglas están en `tickets/comments.py`; las rutas (`tickets/routes/comments.py`) solo orquestan. **Incluye una migración** (`create_comments_table`).

**Modelo** (`models/comment.py`, `Comment`, tabla `comentarios`): una única entidad para los dos tipos (`CommentType`: `PUBLICO` e `INTERNO`, la nota interna). Campos: `ticket_id`, `autor_usuario_id`, `tipo`, `contenido` (TEXT; el límite de 5000 caracteres, `MAX_COMMENT_LENGTH`, lo comprueban el servicio y el formulario), `fecha_creacion`, `fecha_modificacion`, `usuario_modificacion_id`, `editado`, `activo`, `fecha_eliminacion` y `usuario_eliminacion_id` (la eliminación es lógica). Restricciones: tipo válido, contenido no vacío, coherencia de la eliminación (activo sin datos de eliminación; eliminado con fecha) y `editado` solo con fecha de modificación; claves foráneas `ON DELETE RESTRICT` e índice `(ticket_id, fecha_creacion)`. Las horas las pone la base de datos. `Comment.es_nota_interna` evita comparar cadenas en las plantillas.

**Políticas** (`security/authorization.py`):

- `can_comment_publicly(user, ticket)`: quien puede ver el ticket (el personal en todos; el Solicitante en los suyos).
- `can_write_internal_note(user)`: solo el personal.
- `can_view_comment(user, comment)`: el personal ve todos; el Solicitante, solo los públicos. Es el equivalente en Python de `visible_comments_condition`, y un test comprueba que coinciden para todos los roles, usuarios inactivos y anónimos.
- `can_edit_comment(user, comment, now=, window_minutes=)` y `can_delete_comment` (hoy la misma regla): el Supervisor y el Administrador, cualquier comentario visible y sin plazo; el resto, solo los suyos dentro de `COMMENT_EDIT_WINDOW_MINUTES` (30 por defecto, variable de entorno validada al iniciar como los límites de sesión; pasará a la configuración administrable en `v0.7.0`). `INTERNAL_COMMENT_TYPE` repite el código del tipo interno para que este módulo no dependa de los modelos; un test comprueba que coincide.

**Servicio** (`tickets/comments.py`, sin commit; cada operación empieza con `begin_ticket_operation`: usuario activo, fila del ticket bloqueada y ticket no cerrado):

- `visible_comments_condition(user)` y `list_comments(ticket, viewer)` / `get_comment(ticket, comment_id, viewer)`: **el filtro por tipo está en la consulta**, nunca en la plantilla (docs/10, sección 57). `viewer` es obligatorio a propósito. `list_comments` carga el autor y su rol en una sola consulta (hay un test) y solo devuelve comentarios activos.
- `add_comment(ticket, actor=, content=, kind=)`: contenido obligatorio (se recortan los espacios y se unifican los saltos de línea). No comprueba que el actor pueda escribir ese tipo: lo hace la ruta (403).
- `edit_comment(ticket, comment_id, actor=, content=)`: devuelve `False` sin cambios. El tipo no cambia nunca. Lee el comentario de nuevo con `populate_existing` bajo el bloqueo del ticket, así que dos ediciones simultáneas se aplican una tras otra (el contenido anterior del segundo evento es el nuevo del primero).
- `delete_comment(ticket, comment_id, actor=)`: eliminación lógica; ya no se muestra a nadie.
- **Eventos del historial:** `COMENTARIO_AGREGADO`, `COMENTARIO_EDITADO` (`valor_anterior` y `valor_nuevo` con el contenido) y `COMENTARIO_ELIMINADO` (contenido y tipo anteriores), con `contexto["comentario_id"]`. Su visibilidad sigue al tipo del comentario (los de una nota interna son internos); el valor por defecto de los tres es `INTERNO`, el seguro, y el servicio indica siempre la visibilidad. `describe_history_changes` muestra solo el tipo (`Comentario público` o `Nota interna`), nunca el texto.
- **No sube la versión** del ticket ni cambia «Actualizado».

**Rutas** (404 si el usuario no ve el ticket; 404 si no ve el comentario —nota interna para un Solicitante, comentario de otro ticket o eliminado—; 403 si lo ve pero no puede actuar; un ticket cerrado vuelve al detalle con un aviso):

- `POST /tickets/<n>/comments`: publica. Si el formulario no es válido se vuelve a mostrar el detalle (`_render_detail`, compartido con el GET) con los errores y lo escrito. Una nota interna enviada por un Solicitante responde 403.
- `GET, POST /tickets/<n>/comments/<id>/edit`: pantalla con el texto actual (no hay selector de tipo).
- `GET, POST /tickets/<n>/comments/<id>/delete`: confirmación.
- Formularios (`tickets/forms.py`): `CommentEditForm` (contenido) y `CommentForm` (añade `tipo`, validado contra el vocabulario).

**Detalle:** tarjeta «Actividad (n)» entre la descripción y el historial (las pestañas Actividad / Archivos / Historial de `docs/11` llegarán con los adjuntos), con el formulario en línea; el personal elige «Comentario público» o «Nota interna» y el Solicitante no ve el selector. La nota interna tiene fondo y acento morados (`--wd-purple` y `--wd-purple-soft`, tokens nuevos en `app.css`), `NOTA INTERNA` y «Solo visible para soporte». Los enlaces Editar y Eliminar son solo presentación (cada ruta comprueba la autorización). El filtro de plantilla `initials` (iniciales del avatar) reutiliza `user_initials`.

**Seed demo:** `DemoAdjustment` admite `comentario` y `nota_interna` (ver "22. CLI"), con cinco tickets nuevos (63 en total).

## Solicitantes del ticket (entrega 6 de `v0.4.0`)

Reglas completas en `docs/06` (RN-158) y `docs/09` (14.1). Las reglas están en `tickets/requesters.py`; las rutas (`tickets/routes/requesters.py`) solo orquestan. **No hay migración:** las columnas de retiro de `tickets_solicitantes` ya existían.

**Política** (`security/authorization.py`): `can_manage_requesters(user)` (Técnico, Supervisor y Administrador; es la misma regla que `can_choose_requesters` y un test comprueba que no se separen). El Solicitante no gestiona solicitantes ni en su propio ticket.

**Servicio** (`tickets/requesters.py`, sin commit; cada operación empieza con `begin_ticket_operation`: usuario activo, fila del ticket bloqueada y ticket no cerrado):

- `add_requester(ticket, requester_id, actor=)`: la persona debe ser un usuario **activo con rol Solicitante** y no ser ya solicitante vigente (comprobación más índice único parcial con savepoint). Si estuvo retirada se crea una fila nueva. Registra `SOLICITANTE_AGREGADO` (**interno**; `valor_nuevo` con `{"usuario_id", "username", "nombre"}` y `contexto["participacion_id"]`).
- `remove_requester(ticket, participation_id, actor=, reason=)`: `participation_id` es el id de la fila de `tickets_solicitantes`. Cierra la participación (`fecha_retiro` con el `now()` de la base de datos y `retirado_por_usuario_id`) y la conserva. El motivo es opcional (máx. 500) y va en `contexto["motivo"]` del evento `SOLICITANTE_RETIRADO` (**interno**; `valor_anterior` con la persona): la tabla no tiene columna para él.
- `list_addable_requesters(ticket)`: los solicitantes activos que aún no lo son (incluye al creador si es Solicitante).
- Un ticket cerrado lanza `TicketClosedError`. Un ticket puede quedarse sin solicitantes (RN-12).
- **No sube la versión** ni toca `fecha_modificacion` («Actualizado»): quien abrió la edición antes del cambio guarda sin conflicto (hay un test). Dos altas o dos retiros simultáneos se resuelven con el bloqueo de la fila (tests con dos hilos).
- **Piezas compartidas:** `begin_ticket_operation(ticket, actor, expire=)` vive en `tickets/versioning.py` (antes era el `_begin` de `assignment.py`, que ahora la usa); `full_name`, `person_snapshot`, `clean_optional_reason` y `MAX_REASON_LENGTH` viven en `tickets/service.py` y los usan asignación, solicitantes y edición.

**Acceso al ticket.** Retirar a un solicitante le quita el acceso (`can_view_ticket` ignora las participaciones con `fecha_retiro`; la condición SQL del listado ya hacía lo mismo y un test comprueba que ambas coinciden tras agregar, retirar y volver a agregar), **salvo que además sea el creador**: el creador original conserva siempre el acceso. Quien se agrega ve el ticket y todo su historial público, también lo anterior a su incorporación. La búsqueda del personal por solicitante sigue a los cambios (un retirado deja de encontrarse).

**Rutas** (404 si el usuario no ve el ticket, 403 si lo ve y no es personal; un ticket cerrado vuelve al detalle con un aviso):

- `GET /tickets/<n>/requesters`: pantalla con los solicitantes actuales (con **Retirar**) y el selector para agregar, con el formato «Apellido, Nombre (usuario)».
- `POST /tickets/<n>/requesters/add`.
- `GET, POST /tickets/<n>/requesters/<participation_id>/remove`: confirmación con motivo opcional (`ReasonForm` de `users/forms.py`); avisa si la persona dejará de ver el ticket o si lo seguirá viendo por haberlo creado.
- Formulario: `RequesterPickForm` (`tickets/forms.py`, opciones como atributo, sin `SelectField`). `TICKET_SCREENS` (`navigation.py`) incluye las dos pantallas.

**Detalle:** el resumen del personal muestra el enlace **Gestionar** junto a **Solicitante(s)** mientras el ticket no esté cerrado (solo presentación: las rutas comprueban la autorización). `Ticket.solicitantes_vigentes` sustituye al filtro que antes hacían las plantillas. Historial: `Solicitante agregado: «…»` y `Solicitante retirado: «…»` (más `Motivo: …`), solo para el personal.

**Seed demo:** `DemoAdjustment` admite `agregar_solicitante`, `retirar_solicitante` (username de un Solicitante demo) y `motivo_retiro`. En un paso se retira primero y después se agrega; la validación simula quién es solicitante en cada paso (retirar exige que lo sea, agregar que no lo sea). Las fechas de esas filas se escriben al crear (la asociación y el retiro son las de sus eventos, con una sola actualización por fila) y se refrescan siguiendo a sus eventos (también los hechos a mano). Cuatro tickets nuevos al final de la lista (58 en total): cambio de persona en un mismo paso, alta en un ticket sin solicitantes, alta y retiro posterior, y retiro del creador. **Cambio de criterio:** `fecha_modificacion` la fija ahora solo un paso que sube la versión del ticket, como en la aplicación (antes, cualquier paso con eventos); afecta a un ticket existente, `mouse-inalambrico`, cuyo segundo paso (asignar a un técnico más) ya no la mueve.

## Asignación (entrega 5 de `v0.4.0`)

Reglas completas en `docs/06` (RN-157) y `docs/09` (15.1). Las reglas están en `tickets/assignment.py`; las rutas (`tickets/routes/assignment.py`) solo orquestan.

**Modelo** (`models/ticket_technician.py`, `TicketTechnician`, tabla `tickets_tecnicos`): relación N:M temporal entre tickets y técnicos con `fecha_asignacion`, `asignado_por_usuario_id`, `fecha_desasignacion`, `desasignado_por_usuario_id` y `motivo_desasignacion`. La asignación vigente es la que no tiene `fecha_desasignacion`, con índice único parcial (un técnico no figura dos veces como asignado vigente del mismo ticket; puede volver con una fila nueva), `CHECK` de fechas y los índices `(ticket_id, fecha_desasignacion)` y `(tecnico_id, fecha_desasignacion)`. Las horas las pone la base de datos (`now()`). `Ticket.tecnicos` y `Ticket.tecnicos_vigentes` las exponen y `tickets.grupo_id` (FK a `grupos`, con índice) guarda el grupo.

**Políticas** (`security/authorization.py`): `can_assign_self(user)` (solo un **Técnico**: es el único rol que puede figurar como técnico de un ticket) y `can_manage_assignments(user)` (Supervisor y Administrador: asignar, quitar y reasignar a cualquier técnico, fijar el grupo y escalar).

**Servicio** (`tickets/assignment.py`, sin commit; cada operación bloquea la fila del ticket con `lock_ticket` antes de validar):

- `assign_technician(ticket, technician_id, actor=)`: el técnico debe ser un **Técnico activo** y no estar ya asignado (comprobación más índice único con savepoint). Registra `TECNICO_ASIGNADO` (público; `contexto["asignacion_id"]`). Si el ticket está `Nuevo` lo pasa a `Asignado`.
- `unassign_technician(ticket, assignment_id, actor=, reason=)`: cierra la asignación (la conserva) y registra `TECNICO_DESASIGNADO` (público). Si era el último técnico de un ticket `Asignado`, lo devuelve a `Nuevo`.
- `set_group(ticket, group_id, actor=, expected_version=)`: fija o quita (`None`) el grupo. El grupo nuevo debe estar activo; el actual puede conservarse aunque esté desactivado. Devuelve `False` si es el mismo. Sube la versión y registra `GRUPO_CAMBIADO` (**interno**). No cambia el estado.
- `escalate_ticket(ticket, actor=, expected_version=, group_id=, technician_id=, reason=)`: hay que cambiar el grupo y/o el técnico y el motivo es obligatorio (máx. 500). Un técnico nuevo **reemplaza** a los asignados (sus asignaciones se cierran con el motivo «Escalamiento.»). Sube la versión siempre y registra **un único** evento interno `TICKET_ESCALADO` con el grupo y los técnicos anteriores y nuevos y el motivo en `contexto`. Si el ticket está `Nuevo` y se asigna un técnico, pasa a `Asignado`.
- Un ticket cerrado lanza `TicketClosedError`. **Estado derivado:** `apply_derived_transition` (en `tickets/lifecycle.py`) aplica `ASIGNAR` (Nuevo → Asignado) y `DESASIGNACION` (Asignado → Nuevo) si la transición está activa, sube la versión y registra `ESTADO_CAMBIADO` con `contexto={"accion": ..., "derivado": True}`.
- **Versión:** suben `version` el grupo, el escalamiento y el estado derivado; asignar y quitar técnicos por sí solos no (son aditivos). Un test con dos hilos comprueba que dos autoasignaciones del mismo técnico producen una sola asignación y que dos técnicos que se asignan a la vez a un ticket `Nuevo` lo pasan a `Asignado` una sola vez.
- Consultas: `list_assignable_technicians`, `list_escalation_technicians` y `list_groups_for_ticket` (grupos activos más el actual aunque esté desactivado). `lock_ticket` y `begin_ticket_operation` (en `tickets/versioning.py`) son el bloqueo y el prólogo compartidos con `change_state` y con los solicitantes (ver "Solicitantes del ticket").

**Rutas** (siempre 404 si el usuario no ve el ticket y 403 si lo ve pero no puede actuar; un ticket cerrado vuelve al detalle con un aviso):

- `POST /tickets/<n>/assign-me` y `/unassign-me`: solo un Técnico (403 al resto).
- `GET /tickets/<n>/assignment` (pantalla de asignación), `POST .../assignment/technicians/add`, `POST .../assignment/technicians/<assignment_id>/remove` y `POST .../assignment/group`: Supervisor y Administrador (un Técnico solo puede usar `remove` con su propia asignación).
- `GET, POST /tickets/<n>/escalate`: Supervisor y Administrador. Fijar el grupo y escalar llevan la versión en un campo oculto; un conflicto avisa sin guardar.
- Formularios (`tickets/forms.py`): `TechnicianPickForm`, `GroupChangeForm` y `EscalationForm`, con las opciones como atributo (sin `SelectField`).

**Detalle:** el Técnico ve **Asignarme** o **Dejar ticket** (un clic, con CSRF); Supervisor y Administrador ven **Asignar**. El resumen muestra al personal **Técnico(s)** (con «(inactivo)» si corresponde) y **Grupo**, y al Solicitante solo **Atendido por** (o «Aún sin asignar»), nunca el grupo. Historial: `Técnico asignado: «…»`, `Técnico desasignado: «…»`, `Grupo: «a» → «b»` y `Ticket escalado` (con líneas de grupo y técnicos); `GRUPO_CAMBIADO` y `TICKET_ESCALADO` son internos y el Solicitante no los recibe (el filtro está en la consulta, como siempre).

**Seed demo:** `DemoAdjustment` admite `grupo` (nombre de un grupo de `seed-demo`, lo fija un Supervisor) y `asignar` (username de un técnico; lo asigna él mismo o un Supervisor). En un paso el orden es datos, prioridad, grupo, asignación y estado. La validación simula que asignar a un técnico pasa un ticket `Nuevo` a `Asignado`. Las fechas de las asignaciones se escriben al crear (la de su evento) y se refrescan con el resto, en una sola actualización por fila para que una desasignación hecha a mano nunca preceda a su asignación. Si un grupo falta o está desactivado el ticket queda sin grupo y se avisa.

## Grupos (entrega 4 de `v0.4.0`)

Módulo `src/workdesk/groups/` (blueprint `groups`, prefijo `/groups`): `routes.py`, `forms.py` y `service.py`. Reglas completas en `docs/06` (RN-146) y `docs/09` (10.1 a 10.3).

**Modelos** (`models/grupo.py`): `Grupo` (`grupos`), `UsuarioGrupo` (`usuarios_grupos`) y `GrupoSupervisor` (`grupos_supervisores`). `Grupo` comparte con los catálogos las columnas de vigencia y trazabilidad (`CatalogAuditMixin`) más `fecha_desactivacion` y `usuario_desactivacion_id`, con nombre único sin distinguir mayúsculas. Las otras dos son relaciones N:M temporales: la vigente es la que no tiene `fecha_fin`, con índice único parcial (nadie figura dos veces como miembro o responsable vigente del mismo grupo; puede volver con una fila nueva) y `CHECK` de que el fin no precede al inicio. El cierre usa `now()` de la base de datos, igual que el inicio. Los grupos no se eliminan, solo se desactivan. `Grupo.miembros_vigentes` y `Grupo.supervisores_vigentes` filtran las vigentes.

**Políticas** (`security/authorization.py`): `can_access_groups` (Administrador y Supervisor), `can_manage_groups` (solo el Administrador: crear, editar, activar, desactivar y designar responsables), `is_responsible_supervisor(user, group)` (Supervisor activo con designación vigente), `can_view_group` (Administrador, o responsable) y `can_manage_group_members` (la misma regla). `visible_groups_condition(user)` (`groups/service.py`) es su equivalente en SQL (Administrador todo; Supervisor, los grupos donde es responsable vigente mediante `EXISTS`; el resto, ninguno) y un test comprueba que ambos coinciden. Si se cambia uno hay que cambiar el otro.

**Rutas.** Todas exigen Administrador o Supervisor (`roles_required`; el Técnico y el Solicitante reciben 403) y, dentro del área, se vuelven a comprobar:

- `GET /groups` (listado con filtro por estado), `GET /groups/<id>` (detalle con técnicos y responsables): el Administrador ve todos los grupos; el Supervisor, los suyos. **Un grupo ajeno responde 404**, igual que uno inexistente.
- `GET, POST /groups/new`, `/groups/<id>/edit`, `/deactivate` y `/activate`: solo el Administrador (403 para el Supervisor, que ve el grupo pero no puede gestionarlo).
- `POST /groups/<id>/members/add` y `GET, POST /groups/<id>/members/<membership_id>/remove`: el Administrador y el Supervisor responsable. El id de una membresía de otro grupo no sirve para retirar de este.
- `POST /groups/<id>/supervisors/add` y `GET, POST /groups/<id>/supervisors/<designation_id>/remove`: solo el Administrador.
- Pantallas separadas, sin modales: alta y edición con nombre y descripción; confirmación con motivo opcional para desactivar, reactivar y retirar. Agregar y designar son un selector de una línea en el propio detalle (las opciones salen de la base y se validan como en el resto de formularios, sin `SelectField`).

**Servicio** (`groups/service.py`, sin commit): `create_group`, `update_group` (devuelve `False` sin auditar si nada cambió), `deactivate_group` y `activate_group`; `add_member` y `remove_member`; `designate_supervisor` y `remove_supervisor`; `list_groups(user, status)` (carga miembros y supervisores sin una consulta por grupo), `get_group`, `list_member_candidates` y `list_supervisor_candidates`. Reglas: solo un **Técnico activo** puede ser miembro y solo un **Supervisor activo** responsable; el grupo debe estar activo para cambiar sus miembros o responsables (un grupo desactivado los conserva); nadie figura dos veces como vigente (comprobación y respaldo en el índice único con savepoint, como los catálogos); un grupo puede tener varios responsables o ninguno (sin responsable solo el Administrador gestiona sus técnicos).

**Ganchos en la administración de usuarios** (`users/service.py`): `close_user_group_links` cierra membresías y designaciones. `change_role` lo llama para quien deja de ser Técnico (sus membresías) o Supervisor (sus designaciones) y `deactivate_user` para ambas, con el motivo «Cambio de rol.» o «Usuario desactivado.». Reactivar a un usuario no las restaura. El historial se conserva y cada cierre se audita.

**Auditoría** (`AuditAction`): `GRUPO_CREADO`, `GRUPO_MODIFICADO`, `GRUPO_ACTIVADO`, `GRUPO_DESACTIVADO`, `GRUPO_MIEMBRO_AGREGADO`, `GRUPO_MIEMBRO_RETIRADO`, `GRUPO_SUPERVISOR_DESIGNADO` y `GRUPO_SUPERVISOR_RETIRADO`, con `entidad_tipo` `grupo`, el nombre en `detalle` y la persona (`usuario_id` y `username`) en los valores. Retirar y desactivar admiten un motivo opcional.

**Navegación y hub:** el Supervisor tiene la opción **Grupos** en el menú lateral; el Administrador llega desde la tarjeta **Grupos** del hub (la opción "Administración" se marca activa en `groups.`). Se corrige la matriz de `docs/11`: "Grupos" es del Administrador y, condicionado a sus grupos, del Supervisor.

**Seed:** `seed-demo` carga además tres grupos de ejemplo (`seeds/demo.py`, `DEMO_GROUPS`: Soporte Redes, Soporte Usuarios y Aplicaciones, con sus técnicos y supervisores; un técnico está en dos grupos y un grupo tiene dos responsables). Es idempotente por nombre (un grupo existente no se toca) y, como no hay Administrador en los datos demo, se registra como acción del sistema. Aún **no se asignan a tickets**: `tickets.grupo_id` llega con la asignación (entrega 5).

## Estados y transiciones (entrega 3 de `v0.4.0`)

Reglas completas en `docs/06` (RN-156) y `docs/09` (12.2). Las reglas están en `tickets/lifecycle.py` (y el catálogo de acciones en `tickets/state_actions.py`); la ruta (`tickets/routes/states.py`) solo orquesta.

**Tabla `transiciones_estados`** (`models/transicion_estado.py`, `TransicionEstado`): `estado_origen_id`, `estado_destino_id`, `accion`, `activa`, `descripcion`, `fecha_modificacion` y `usuario_modificacion_id`. Es único por (origen, destino, acción) y el origen no puede ser igual al destino. Una fila es una transición estructuralmente válida del flujo; `activa` permite al Administrador deshabilitarla (pantalla UI-021, entrega 12). No guarda permisos: quién ejecuta cada acción lo decide el código.

**Vocabulario de acciones** (`StateAction`, solo en la aplicación como `TicketEvent`): `ASIGNAR`, `DESASIGNACION`, `INICIAR`, `PONER_EN_ESPERA`, `REACTIVAR`, `RESOLVER`, `CIERRE_DIRECTO`, `CONFIRMAR`, `RECHAZAR`, `AUTO_CIERRE`, `CIERRE_EXCEPCIONAL` y `REABRIR`. Un mismo par origen-destino puede existir con varias acciones (Resuelto → Cerrado tiene tres).

**Seed:** `seed-catalogs` carga las 20 transiciones de la matriz de `docs/08` (sección 34) más `DESASIGNACION` (Asignado → Nuevo al quitar al último técnico, que `docs/08` no lista) y `AUTO_CIERRE` (la ejecuta el planificador de `v0.5.0`, no una persona). Es idempotente por (origen, destino, acción) y **no pisa una transición que el Administrador haya deshabilitado**. El comando informa `transiciones: N`. Quien tenga una base anterior debe volver a ejecutar `seed-catalogs`.

**Acciones implementadas hoy** (`STATE_ACTIONS`): iniciar el trabajo (`INICIAR`, Nuevo o Asignado → En progreso), poner en espera (`PONER_EN_ESPERA`, En progreso → En espera) y reactivar (`REACTIVAR`, En espera → En progreso). Resolver, cerrar, confirmar, rechazar y reabrir se añadieron en la entrega 9 (ver "Resolución, validación, cierre y reapertura"). Las demás acciones de la tabla (`ASIGNAR` y `DESASIGNACION`, derivadas de la asignación, y `AUTO_CIERRE`, del planificador de `v0.5.0`, que cierra con `close_automatically`) no están en `STATE_ACTIONS`: `change_state` las rechaza con `StateTransitionError`. Cada acción es un `StateActionInfo` (ruta, texto, icono, mensaje y política de rol).

**Política:** `can_change_state(user)` (Técnico, Supervisor y Administrador; el Solicitante no cambia estados operativos). Que la transición exista desde el estado actual lo decide `available_actions` / `change_state`.

**Servicio** (`tickets/lifecycle.py`, sin commit):

- `available_actions(ticket, user)`: las acciones que ese usuario puede ejecutar ahora (implementada, transición activa desde el estado actual y política de rol), con su estado de destino. Un ticket cerrado solo ofrece reabrirlo.
- `change_state(ticket, actor=, action=, expected_version=, wait_reason_id=, text=, close_reason_id=)`: bloquea la fila del ticket (`SELECT ... FOR UPDATE`) y la vuelve a leer, así que la transición se valida contra el estado real; comprueba el ticket cerrado (`TicketClosedError`), la versión (`TicketConflictError`) y que exista una transición activa desde el estado actual (`StateTransitionError`); aplica el cambio con `apply_ticket_changes` (sube la versión) y registra `ESTADO_CAMBIADO` con el estado anterior y el nuevo (columnas `estado_anterior_id` y `estado_nuevo_id`, snapshots en `valor_anterior` y `valor_nuevo`) y `contexto["accion"]`. Dos personas que actúan a la vez producen una sola transición (hay un test con dos hilos).
- **Motivo de espera:** solo con `PONER_EN_ESPERA` y siempre opcional. El motivo debe estar activo (`motivo_espera_id` del evento) y un texto libre (máx. 500 caracteres, `contexto["motivo"]`) exige un motivo con `permite_texto_otro`. El resto de acciones rechaza motivo y texto.
- Los cambios de estado **suben `version`**, como la edición y la prioridad.

**Ruta** (`GET, POST /tickets/<public_id>/status/<action_slug>`, con `start`, `hold` y `resume`): una pantalla de confirmación por acción, como Editar y Cambiar prioridad (funciona sin JavaScript). 404 si el usuario no puede ver el ticket o la acción no existe; 403 si lo ve pero no puede cambiar estados (el Solicitante); un ticket cerrado o una acción que ya no corresponde al estado actual (también en GET, por si la pantalla estaba abierta) vuelven al detalle con un aviso; un conflicto de versión reabre la pantalla con el aviso. La pantalla de espera ofrece los motivos activos (más "Sin motivo") y una explicación libre que `static/js/tickets/wait-reason.js` muestra solo con un motivo que la admita (mejora progresiva: el servidor valida igual).

**Detalle:** la cabecera muestra un botón por cada acción disponible (como mucho una o dos) y el historial el evento "Estado cambiado" con `Estado: «a» → «b»` para todos los roles. **El motivo de espera y su texto los ve solo el personal** (`Motivo de espera: …` y `Motivo: …`), igual que el motivo de una prioridad; el evento es público.

**Navegación:** las pantallas Editar, Cambiar prioridad y Cambiar estado marcan activa la opción "Tickets" (`TICKET_SCREENS` en `navigation.py`); "Crear ticket" sigue marcándose solo en su formulario.

## Administración de estados y transiciones (entrega 12 de `v0.4.0`)

Reglas completas en `docs/06` (RN-164), `docs/09` (12.1 y 12.2) y `docs/11` (UI-021). El servicio está en `catalogs/flow.py` y las rutas en `catalogs/flow_routes.py` (mismo blueprint `catalogs`, prefijo `/admin`); las rutas solo orquestan. **No hay migración.** Todas son del Administrador (`admin_only`), y la tarjeta «Estados y transiciones» del hub enlaza con la pantalla.

**Pantallas:** `GET /admin/states` (los estados y las transiciones en una sola pantalla), `GET, POST /admin/states/<id>/edit` y `GET, POST /admin/transitions/<id>/deactivate` y `/activate` (confirmación con motivo opcional, `ReasonForm`). Las plantillas están en `templates/catalogs/` (`states.html`, `state_form.html` y `transition_confirm.html`).

**Estados:** solo se editan `nombre_visible` (hasta 50 caracteres) y `descripcion` (opcional, hasta 300); el código, el orden y el color no se editan. `update_state` bloquea las seis filas (`SELECT ... FOR UPDATE`) y rechaza un nombre repetido entre los seis, sin distinguir mayúsculas; devuelve `False` sin auditar si nada cambió. Renombrar no toca el historial (los eventos guardan el nombre de su momento). El macro `state_badge` muestra la descripción como ayuda (`title`) en toda la aplicación.

**Transiciones:** se deshabilitan y habilitan una a una (`deactivate_transition` y `activate_transition`; habilitar siempre se puede). Hay dos protecciones:

- las **esenciales** (`ESSENTIAL_REASONS` en `tickets/state_actions.py`: `ASIGNAR`, `DESASIGNACION`, `CONFIRMAR`, `RECHAZAR`, `CIERRE_EXCEPCIONAL`, `AUTO_CIERRE` y `REABRIR`; 8 de las 20 filas, cada una con su razón) no se pueden deshabilitar;
- el **flujo completo** (`_Graph` y `_flow_problem`): ninguna deshabilitación puede dejar un estado inalcanzable desde `Nuevo` avanzando (las acciones de `RETURN_ACTIONS`, que devuelven un ticket atrás, no cuentan) ni sin camino hasta `Cerrado`. Casi no conoce acciones concretas y solo bloquea lo que empeora el grafo actual. Al deshabilitar se bloquean las filas de transiciones, para que dos Administradores no rompan el flujo entre los dos; habilitar bloquea la fila de la transición. En ambos casos, si otra persona ya hizo el mismo cambio, el segundo recibe «ya está habilitada» o «ya está deshabilitada» (`ALREADY_ENABLED` y `ALREADY_DISABLED`) y el cambio no se repite ni se audita dos veces.

Los errores son `EssentialTransitionError` y `BrokenFlowError` (de `CatalogRuleError`), y la regla se comprueba también al abrir la confirmación.

**Quién ejecuta cada acción** sale del catálogo: `StateActionInfo.roles` (y `roles_note` para el matiz «solo un solicitante del ticket») y, para las automáticas, `AUTOMATIC_ACTIONS`. La etiqueta de cada acción es `STATE_ACTION_LABELS` (`models/transicion_estado.py`). `tests/test_state_actions.py` comprueba que los roles declarados coinciden con las políticas, que todas las acciones del vocabulario están descritas y que los textos no escriben a mano ningún nombre de estado: usan el vigente (`StateActionInfo.describe`).

**Auditoría:** `ESTADO_MODIFICADO` (`entidad_tipo` `estado`, el código en `detalle` y solo los campos cambiados), `TRANSICION_DESACTIVADA` y `TRANSICION_ACTIVADA` (`entidad_tipo` `transicion`, «Origen → Destino (Acción)» en `detalle`, `{"activa": ...}` en los valores y el motivo si se escribió).

**Seed demo:** `seed-demo-tickets` ejecuta las acciones de estado de verdad: si una transición que necesita está deshabilitada, se detiene antes de cargar nada con un mensaje que dice dónde habilitarla.

---

# 11 quater. Tiempo laboral

Módulo `src/workdesk/worktime.py` (entrega 1 de `v0.5.0`). Es el motor de tiempo laboral. Hoy lo usa el seed `seed-demo-tickets` (donde vivía como `_BusinessClock`) y lo usará el SLA, por eso tiene su propio módulo. No usa la base de datos ni Flask: recibe un calendario y una zona horaria. Sus decisiones están en `docs/10` (sección «Tiempo laboral»).

- **`WorkCalendar`** (`dias`, `inicio`, `fin` y `feriados`) describe una jornada única, igual para todos los días laborales, y **`DEMO_CALENDAR`** (lunes a viernes de 09:00 a 18:00, sin feriados) es el calendario por defecto. Los dos salieron de `seeds/demo_tickets_data.py`.
- **`BusinessClock(calendario, zona)`** (o `BusinessClock.from_schedule(franjas, feriados, zona)`, ver abajo) ofrece los días (`is_workday`, `previous_workday`, `next_workday` y `workdays_before`), los momentos (`is_working_time`, `into_business` y `latest_before`), `business_seconds_between(inicio, fin)` (los segundos laborales completos entre dos momentos) y dos formas de avanzar: `add_business_seconds` calcula un vencimiento (si el plazo se cumple justo al cerrar, el resultado es la hora de cierre) y `add_hours` un momento de trabajo (en ese caso pasa a la apertura del día siguiente, que es lo que necesita el seed). Son nuevas `business_seconds_between` y `add_business_seconds`; `add_hours` conserva su comportamiento y ahora se apoya en la segunda, y el resto se movió con el mismo comportamiento para las fechas que ya estaban en la zona del calendario (lo único que ganaron es la conversión a esa zona).
- **Medir y sumar son operaciones inversas**, y `tests/test_worktime.py` lo comprueba, además de comparar la medición con un recuento minuto a minuto que no comparte ninguna idea con el motor.
- **La jornada incluye el inicio y excluye el fin.** Las fechas llevan siempre zona horaria: el motor las convierte a la zona del calendario (se le pueden pasar las de la base de datos, en UTC) y rechaza las que no la tienen. Se calcula con la hora de pared y se da por hecho que ninguna jornada cruza un cambio de horario de verano.
- **`calendar_problems(calendario)`** valida un calendario con mensajes pensados para quien lo edita (la usan el seed y, desde la entrega 2, la pantalla del Administrador), y `BusinessClock` lanza `ValueError` ante un calendario inválido: sin días laborales, buscar el siguiente día laboral no terminaría nunca.
- **El seed no cambió su comportamiento con el calendario por defecto.** `seed_demo_tickets` usa `BusinessClock` y `calendar_problems` en lugar de sus copias privadas, y sus tests siguen igual (solo cambió el módulo desde el que importan `WorkCalendar`).
- **Franjas distintas por día (entrega 2).** Además de una jornada única, el motor admite una lista de `Franja` (`BusinessClock.from_schedule`): horarios distintos según el día o varias franjas en un mismo día, como una pausa de almuerzo. Internamente el reloj guarda las franjas de cada día de la semana y una única jornada es el caso particular de una franja por día laboral; un test comprueba que ambas formas se comportan igual. `schedule_problems` es el equivalente de `calendar_problems` para las franjas (al menos una, días de 0 a 6, cada una empieza antes de terminar y las de un día no se solapan). `is_working_time(momento)` dice si en un momento se trabaja y `WEEKDAY_NAMES` da los nombres de los días en el orden de `date.weekday()`. Los atributos `start`, `end` y `days` del reloj desaparecieron: con franjas por día ya no hay una jornada única que exponer.

---

# 11 quinquies. Calendario laboral administrable

Paquete `src/workdesk/sla/` (blueprint `sla`, prefijo `/admin/sla`), entrega 2 de `v0.5.0`. Es el módulo `sla` previsto en `docs/10` (sección 22), donde se sumaron las políticas (entrega 3, ver "Políticas de SLA") y se sumarán los períodos. Reglas completas en `docs/09` (21 y 40.8), `docs/11` (UI-022) y `docs/12` (fase 5). **Incluye una migración** (`create_work_calendar_tables`).

**Modelos** (`models/calendario_laboral.py`): `CalendarioLaboral` (`calendarios_laborales`: `version`, `zona_horaria`, `activo`, `fecha_creacion` y `usuario_creacion_id`), `HorarioLaboral` (`horarios_laborales`: una fila por franja, con `dia_semana` ISO de 1 a 7) y `Feriado` (`feriados`: fecha y nombre). Restricciones: versión positiva y única, **como máximo una versión vigente** (índice único parcial sobre `activo`), franjas con inicio anterior al fin y sin repetir el inicio dentro de una versión, un feriado por fecha y versión, nombre de feriado no vacío y claves foráneas con `ON DELETE RESTRICT`. Que las franjas de un día no se solapen lo comprueba el servicio (no hay restricción de exclusión: necesitaría la extensión `btree_gist`).

**Una versión nunca se modifica.** Guardar crea la siguiente y deja la anterior como histórica, así que lo que ya se calculó con una versión (los períodos de SLA, desde la entrega 4) no cambia retroactivamente. Por eso `docs/09` perdió las columnas de modificación y de vigencia por fila que el diseño inicial preveía (`nombre`, `fecha_modificacion`, `activo` de franjas y feriados...): ninguna hace falta.

**Servicio** (`sla/work_calendar.py`, sin commit):

- `resolve_work_calendar()` es la **única función que decide cuál es el calendario vigente**: el guardado o, si todavía no hay ninguno, el de por defecto (`DEMO_CALENDAR` en la zona de `APP_TIMEZONE`). Devuelve un `ResolvedCalendar` con el reloj listo, el nombre de la zona y la versión de la que sale (`record`, `None` si es el de por defecto). `clock_for(versión)` construye el reloj de una versión concreta (es lo que usará el SLA).
- `save_work_calendar(actor=, base_version=, zone_name=, franjas=, holidays=, reason=)` guarda una versión nueva y la deja vigente. `base_version` es la versión con la que se abrió la pantalla (0 si no había ninguna): si otra persona guardó mientras tanto lanza `CalendarConflictError` y no se guarda nada. Bloquea la fila vigente (`SELECT ... FOR UPDATE`), libera el lugar de «vigente» antes de insertar y, si todavía no había ninguna versión y dos personas guardan la primera a la vez, gana el índice único y la otra recibe el mismo conflicto (savepoint, como los catálogos). Guardar un contenido idéntico al vigente lanza `NothingToChangeError` y no crea una versión; la zona (se comprueba contra `available_zone_names`, no basta con que `ZoneInfo` la acepte), los feriados repetidos o sin nombre, el motivo y las franjas se validan y lanzan `CalendarRuleError`. Registra `CALENDARIO_LABORAL_GUARDADO` (`entidad_tipo` `calendario_laboral`, `detalle` «Versión N») con la versión anterior y la nueva y **solo las secciones que cambiaron** (`zona_horaria`, `horario` y `feriados`); la primera versión se compara con el calendario por defecto.
- Para las pantallas: `describe_calendar` (un `CalendarView` con el horario resumido por días seguidos que comparten horas: «Lunes a jueves · 09:00–18:00», «Viernes · 09:00–17:00»), `list_calendar_versions` (tres consultas, sin una por versión) y `describe_schedule` y `summarize`.

**Formulario** (`sla/forms.py`, `WorkCalendarForm`, que hereda el motivo opcional de `ReasonForm`): **el horario de cada día es un texto** (`09:00-18:00`, o `09:00-13:00, 14:00-18:00` si hay una pausa; vacío = no se trabaja) y **los feriados son otro, uno por línea** (`25-12-2026 Navidad`; también se acepta año-mes-día, con barras y con el día sin cero). Así se admiten varias franjas por día sin filas dinámicas ni JavaScript. `parse_day` y `parse_holidays` convierten los textos (una franja que termina antes de empezar, dos solapadas, una hora que no existe, una fecha imposible, un año fuera de 2000-2100, un nombre ausente o una fecha repetida se señalan con el campo o la línea), y `format_day` y `format_holidays` hacen el camino inverso para rellenar el formulario. Todos los errores se informan a la vez y el formulario conserva lo escrito. Un calendario sin ningún día laboral se rechaza.

**Pantallas** (todas del Administrador, 403 al resto):

- `GET /admin/sla` («SLA», UI-022): los objetivos por prioridad (entrega 3) y el calendario laboral. Del calendario muestra el estado («Configurado · versión N» o «Por defecto (sin configurar)»), el horario resumido, la zona, el número de feriados con los **próximos cinco**, quién y cuándo lo guardó, y la tabla de versiones (la vigente y las anteriores).
- `GET, POST /admin/sla/calendar` («Configurar calendario»): el formulario. Lleva la versión base en un campo oculto y **se rellena con lo vigente solo al abrirlo** (en un envío manda lo que llegó, para que una petición sin versión no se complete sola y se salte la comprobación). Ante un conflicto de versión se vuelve al formulario con lo vigente y un aviso (lo escrito se pierde a propósito); sin cambios, se avisa y no se crea nada. La lista de zonas horarias válidas ayuda a escribirla (`<datalist>`).
- La tarjeta «SLA» del hub enlaza con `/admin/sla` y «Administración» se marca activa en estas pantallas.

**Seed de demostración.** `seed_demo_tickets` lee el calendario resuelto: con uno guardado planifica todas sus fechas dentro de sus franjas, en su zona horaria y sin que ninguna caiga en un feriado; con un `calendar=` explícito (los tests) manda ese. La hora de creación de cada ticket pasa por `into_business`, así que si cae en una pausa pasa al siguiente momento de trabajo (con el calendario por defecto no se mueve). Con un calendario guardado `validate_demo_tickets` no compara la hora de cada ticket con una jornada única (`calendar=None`): solo comprueba que está bien escrita. Con el calendario por defecto (y con cualquier otro de una sola jornada en la que caigan las horas de los tickets) las fechas que genera el seed son exactamente las de antes: el cambio de `_planned_times` solo afecta a combinaciones que la validación del seed rechaza.

---

# 11 sexies. Políticas de SLA

Entrega 3 de `v0.5.0`, en el mismo paquete `src/workdesk/sla/` que el calendario laboral. Reglas completas en `docs/06` (RN-165), `docs/09` (20.2 y 40.9), `docs/10` (sección 28.1, «Políticas de SLA por prioridad») y `docs/11` (UI-022). **Incluye una migración** (`create_sla_policies_table`). Los objetivos se aplican a los tickets desde la entrega 4 (ver "Períodos de SLA").

**Modelo** (`models/politica_sla.py`, `PoliticaSla`, tabla `politicas_sla`): `prioridad_id` (FK `ON DELETE RESTRICT`), `tiempo_objetivo_respuesta_minutos` (opcional), `tiempo_objetivo_resolucion_minutos`, `pausa_en_espera` (verdadero por defecto), `umbral_aviso_consumo_porcentaje` (opcional) y las columnas del mixin `CatalogAuditMixin` (`activo`, creación y modificación). Restricciones: resolución mayor que cero, respuesta mayor que cero y **no mayor que la resolución**, umbral entre 1 y 100, e **índice único parcial** `(prioridad_id) WHERE activo` (como máximo una política activa por prioridad). Se omiten dos columnas de `docs/09` (20.2): `calendario_laboral_id` (el calendario es global y versionado: la política usa el vigente y cada período de SLA anotará la versión con la que se calculó) y `nombre` (sería el de la prioridad). Los tiempos son **minutos laborales**.

**Reglas** (`sla/policies.py`, sin commit):

- **Una política por prioridad, editada en el sitio.** `save_policy(prioridad, actor=, base_token=, response_minutes=, resolution_minutes=, warning_percent=, pause_on_hold=, reason=)` la crea si la prioridad no tiene (`POLITICA_SLA_CREADA`) o aplica solo los campos que cambiaron (`POLITICA_SLA_MODIFICADA`, con sus valores anterior y nuevo); devuelve `SaveOutcome.CREATED`, `UPDATED` o `UNCHANGED` (sin cambios no audita). Nunca crea una segunda fila para la misma prioridad (activa o no). Una política desactivada puede editarse y sigue desactivada. `deactivate_policy` y `activate_policy` (`POLITICA_SLA_DESACTIVADA` y `POLITICA_SLA_ACTIVADA`, con motivo opcional) no tocan los objetivos; desactivarla significa que esa prioridad no tiene SLA.
- **Los valores se validan en un solo lugar.** `policy_problems` devuelve lo que está mal por campo (resolución obligatoria, mayor que cero y de hasta 1000 horas; primera respuesta, si existe, mayor que cero y no mayor que la resolución; umbral entre 1 y 100). La usan el formulario (todos los errores a la vez, cada uno junto a su campo) y `save_policy`, que lanza `PolicyRuleError` con el campo afectado. La primera respuesta no se compara con una resolución que ya está mal.
- **Quien edita dice qué vio.** El formulario lleva `policy_token` (la fecha de la última modificación de la política, o «0» si todavía no hay): si no coincide con la actual, `save_policy` lanza `PolicyConflictError` y no guarda nada. No necesita una columna de versión porque cada cambio, activación y desactivación anota su fecha.
- **Concurrencia.** Toda escritura empieza bloqueando la fila de la prioridad con `FOR NO KEY UPDATE` (el bloqueo más débil que sirve: no frena la creación de tickets, que solo lee su clave) y relee la política con `populate_existing`: sin él, la sesión devolvería la copia que cargó la propia petición antes de que otra transacción confirmara y el conflicto pasaría inadvertido (hay tests que lo demuestran). Dos Administradores que definen, editan o desactivan a la vez la misma política dejan un solo resultado y una sola auditoría (tests con dos hilos). El índice único parcial es la última defensa.
- Para las pantallas: `list_policy_rows()` (todas las prioridades por nivel, cada una con su política, en una sola consulta), `get_priority`, `get_policy` y `on_hold_state_name()` (el nombre vigente del estado en espera, que el Administrador puede renombrar; el código `EN_ESPERA` es `ON_HOLD_STATE_CODE` en `models/estado.py`).

**Formulario** (`sla/policy_forms.py`, `PolicyForm`, que hereda el motivo opcional de `ReasonForm`): **las duraciones son un texto** («30 min», «4 h», «1 h 30 min»). `parse_duration` entiende `h`, `hr`, `hrs`, `hora(s)`, `m`, `min`, `mins`, `minuto(s)` con o sin espacios, también «1h30»; rechaza los decimales, los días (su duración depende del calendario) y un número suelto (no dice si son minutos u horas); `duration_text` hace el camino inverso. El umbral es un número opcional, la pausa una casilla y la marca de la política un campo oculto. Todos los errores se informan a la vez junto a su campo y el formulario conserva lo escrito. Se rellena con lo vigente **solo al abrirlo** (en un envío manda lo que llegó: una petición sin marca no debe completarse sola y saltarse la comprobación). Una política nueva se propone con el umbral en 80 % y la pausa activada.

**Pantallas** (todas del Administrador, 403 al resto, 404 con una prioridad inexistente; sin modales y sin JavaScript). La política se identifica por su **prioridad** (`/admin/sla/priorities/<id>/...`):

- `GET /admin/sla` («Configuración de SLA»): ahora empieza con la tarjeta **Objetivos por prioridad** (una fila por prioridad, de menor a mayor nivel: primera respuesta, resolución, umbral, pausa en «<nombre del estado en espera>», estado y acciones) y sigue con el calendario laboral. Una prioridad sin política muestra «Sin definir» y el botón **Definir**; una desactivada, la fila atenuada y **Reactivar**; una prioridad inactiva se marca «(inactiva)» pero se lista, porque conserva su política.
- `GET, POST /admin/sla/priorities/<id>/edit`: define o edita los objetivos. Ante un conflicto se vuelve al formulario con lo vigente y un aviso (lo escrito se pierde a propósito); sin cambios, se avisa y no se audita.
- `GET, POST /admin/sla/priorities/<id>/deactivate` y `/activate`: confirmación con motivo opcional. Una acción que ya no corresponde (ya desactivada, ya activa o sin política) vuelve a «SLA» con un aviso, también desde el GET.
- Las plantillas son `sla/_policies.html` (la tarjeta, que incluye `index.html`), `sla/policy_form.html` y `sla/policy_status.html`. El formateo es el filtro `duration` (`format_duration` en `formatting.py`, que también usará la entrega 7). El macro `checkbox_field` ganó un parámetro `label` para poner el nombre vigente del estado en la etiqueta de la pausa.

**Datos iniciales.** `seed-catalogs` carga una política por prioridad con los valores de ejemplo de UI-022 (`INITIAL_SLA_POLICIES`; minutos laborales, pausa en espera): Baja 8 h / 24 h / 80 %, Media 4 h / 12 h / 80 %, Alta 2 h / 6 h / 75 % y Crítica 30 min / 4 h / 75 % (primera respuesta, resolución y umbral). Cada política se identifica por su prioridad: si ya hay una fila (activa o no) no se toca, así que no pisa lo editado ni reactiva lo desactivado. El seed `seed-demo-tickets` no cambia en esta entrega: sin períodos de SLA no hay nada que sembrar en los tickets.

**Quedan fuera** (ver `docs/06`, RN-165): el interruptor general «Aplicar SLA a los tickets» y los avisos configurables de UI-022, que dependen de la tabla `configuracion` de `v0.7.0`; mientras tanto, desactivar las políticas desactiva el SLA.

**Mejora de lo existente.** La red de seguridad de autorización (`tests/test_route_authorization.py`) no cubría las rutas `sla.*`, que ya eran del Administrador: ahora las recorre como a `users`, `catalogs` y `admin`.

---

# 11 septies. Períodos de SLA

Entrega 4 de `v0.5.0`, en el paquete `src/workdesk/sla/` (módulo `periods.py`). Reglas completas en `docs/06` (RN-166), `docs/09` (20.3), `docs/10` (sección 28.1, «Períodos de SLA»). **Incluye una migración** (`create_sla_periods_table`). No tiene pantallas: el estado del SLA se verá en el listado y el detalle con la entrega 7; mientras tanto se consulta con el comando `sla-status`.

**Modelo** (`models/periodo_sla.py`, `PeriodoSla`, tabla `tickets_sla_periodos`): `ticket_id`, `politica_sla_id`, `prioridad_id`, `calendario_laboral_id`, los objetivos copiados (`tiempo_objetivo_respuesta_minutos`, `tiempo_objetivo_resolucion_minutos`) y `pausa_en_espera`, `fecha_inicio`, `fecha_fin` (NULL mientras está vigente), `segundos_consumidos`, `fecha_vencimiento_respuesta`, `fecha_vencimiento_resolucion`, `usuario_cambio_id` y `motivo_cambio`. Restricciones: fin no anterior al inicio, consumo no negativo, objetivos positivos, claves foráneas `ON DELETE RESTRICT` e **índice único parcial** `(ticket_id) WHERE fecha_fin IS NULL` (un solo período vigente por ticket). Se aparta de `docs/09` en que `calendario_laboral_id` admite NULL (el calendario por defecto no tiene fila). Propiedades `esta_vigente` y `esta_pausado`.

**Cómo funciona** (`sla/periods.py`, sin commit):

- **`reconcile_sla(ticket, actor, reason=)` es el único punto de entrada.** La llaman `create_ticket` (sin usuario: el período de la creación no anota quién cambió), `change_priority` (con el motivo) y `change_state` al terminar. No recibe qué pasó: mira la prioridad y el estado del ticket y deja los períodos como deben estar, así que es idempotente. Las asignaciones (`Nuevo` ↔ `Asignado`) no la llaman: no cambian el reloj.
- **Modo del reloj según el estado:** corriendo (en trabajo), pausado (`En espera` con una política que pausa) o detenido (`Resuelto`, `Cerrado`, o prioridad sin política). Cambiar de modo o de prioridad cierra el período vigente (anota lo consumido, en tiempo laboral, con el calendario del propio período) y abre otro.
- **Continuidad:** el vencimiento del período nuevo es el momento del cambio más lo que queda del objetivo (`objetivo − consumo acumulado`, en horario laboral); si no queda nada, nace vencido. Mientras la prioridad no cambia, los períodos nuevos **copian las condiciones del anterior** (editar una política no altera el SLA en curso); un cambio de prioridad toma la política vigente de la prioridad nueva. Un ticket cuya prioridad no tiene política activa no tiene SLA.
- **Pausa:** un período pausado es un período vigente sin `fecha_vencimiento_resolucion` (no hay columna de pausa). No consume tiempo; al reanudar se abre otro con lo que queda.
- **Primera respuesta** (`first_response_at`): el primer comentario público del personal que sigue visible. Se evalúa al abrir cada período y deja de tener vencimiento una vez respondida.
- **`evaluate_ticket_sla(ticket_id, now=)`** calcula sin guardar nada un `SlaSnapshot`: estado (`SlaStatus`: `DENTRO`, `PROXIMO_A_VENCER`, `VENCIDO`, `PAUSADO`), consumo acumulado, porcentaje, vencimientos, si la primera respuesta venció y si el ticket ya incumplió alguna vez (un incumplimiento no se borra al bajar la prioridad). Devuelve `None` si el ticket no tiene SLA. El umbral de aviso se lee de la política de origen.
- **`current_time()`** es el `now()` de la base de datos (el mismo instante que los eventos del historial); los tests lo reemplazan para fijar «la hora».
- **`rebuild_ticket_periods(ticket)`** reconstruye los períodos repasando el historial (creación, cambios de prioridad y de estado) con la misma lógica que el cálculo en vivo (comparten `_reconcile`; un test comprueba que dan el mismo resultado para un recorrido completo). Usa la política y el calendario vigentes hoy, porque el historial no guarda cuáles eran. **`rebuild_periods(only_missing=, public_id=)`** lo aplica a varios tickets.

**Comandos** (`cli/sla.py`):

- `sla-rebuild [--all] [--ticket N]`: calcula los períodos de los tickets que **no tienen ninguno** (los anteriores al SLA); `--all` recalcula también los que ya tienen y se niega con `APP_ENV=production` (son el cálculo en vivo); `--ticket` limita a uno. Además completa la fecha de aviso de los períodos en marcha que no la tienen (los anteriores a la entrega 7), sin tocar el resto. Informa `Tickets recalculados: N. Períodos de SLA: M. Fechas de aviso completadas: K.`.
- `sla-status <número>`: el estado del SLA de un ticket (dentro de plazo, próximo a vencer, vencido o pausado), el consumo (`3 h de 12 h (25 %)`), el vencimiento, la fecha de aviso, la primera respuesta y la lista de períodos.

**Seed de demostración.** `seed_demo_tickets` recalcula los períodos de todos sus tickets (`rebuild_ticket_periods`) al terminar, cuando el historial ya está en fechas pasadas: los servicios abren los períodos con la hora real de la carga y ese cálculo se descarta. Así los tickets quedan en tiempo, próximos a vencer, vencidos y pausados según su historia. Es idempotente y los períodos siguen a las fechas al refrescar otro día.

El estado del SLA en la interfaz es la entrega 7 (ver "Indicadores de SLA") y los avisos de SLA y el cierre automático, la entrega 8 (ver "Planificador"). Los tickets anteriores al SLA no tienen períodos hasta que se ejecuta `sla-rebuild`.

---

# 11 octies. Notificaciones internas

Entrega 5 de `v0.5.0`, en el paquete `src/workdesk/notifications/` (blueprint `notifications`, prefijo `/notifications`). Reglas completas en `docs/06` (RN-167, que precisa RN-93), `docs/09` (22.1), `docs/10` (secciones 23, 28.1 y 89) y `docs/11` (sección 30 y UI-008). **Incluye una migración** (`create_notifications_table`). Es la infraestructura y la pantalla: los eventos de un ticket los crean desde la entrega 6 (ver "Avisos por los eventos de un ticket") y los avisos de SLA los crea el planificador (entrega 8, ver "Planificador").

**Modelo** (`models/notificacion.py`, `Notificacion`, tabla `notificaciones`): `usuario_id` (el destinatario), `ticket_id` (opcional: sin ticket es un aviso general), `tipo_evento`, `titulo` (opcional), `mensaje`, `leida`, `fecha_creacion` (la pone la base de datos) y `fecha_lectura`. Restricciones: `leida` y `fecha_lectura` siempre juntas, mensaje con al menos un carácter que no sea un espacio ni un salto de línea (`mensaje ~ '\S'`, porque `btrim` solo recorta espacios), claves foráneas `ON DELETE RESTRICT` e índice `(usuario_id, leida, fecha_creacion)` para el contador y el listado. **El contenido no se reescribe:** el ORM rechaza modificar el destinatario, el ticket, el evento, el título, el mensaje y la fecha de creación (`NotificationContentImmutableError`); solo cambian `leida` y `fecha_lectura`. Propiedades `etiqueta` y `icono` (con respaldo si el vocabulario cambió).

**Vocabulario solo en la aplicación** (`NotificationEvent`, sin `CHECK` en la base, como el historial): `TICKET_CREADO`, `TICKET_ASIGNADO`, `TICKET_REASIGNADO`, `ESTADO_CAMBIADO`, `COMENTARIO_PUBLICO`, `NOTA_INTERNA`, `TICKET_EN_ESPERA`, `TICKET_RESUELTO`, `VALIDACION_PENDIENTE`, `TICKET_CERRADO`, `TICKET_REABIERTO`, `SLA_PROXIMO_A_VENCER` y `SLA_VENCIDO` y `SLA_PRIORIDAD_BAJADA` (14). Cada uno tiene su nombre (`NOTIFICATION_EVENT_LABELS`) y su icono (`NOTIFICATION_EVENT_ICONS`) y un test exige que ninguno falte.

**Servicio** (`notifications/service.py`):

- `notify(destinatario, evento, *, message, title=None, ticket=None)` y `notify_many(destinatarios, evento, ...)`: **no hacen commit** (el aviso se confirma o se revierte con la operación que lo provoca). Validan el evento contra el vocabulario, recortan el mensaje (obligatorio, hasta 1000 caracteres) y el título (hasta 150) y lanzan `NotificationRuleError` sin dejar nada pendiente. Un destinatario inactivo no recibe nada (devuelven `None` o lo omiten) y `notify_many` no repite destinatarios.
- **Quién recibe un aviso lo decide quien lo genera**, no el servicio: no comprueba si el destinatario puede ver el ticket ni si el evento es interno. Quien produzca avisos (`notifications/events.py` desde la entrega 6, y el planificador en la 8) debe seguir la visibilidad del historial; el servicio solo exige un destinatario activo.
- `count_unread(usuario)` (la campana), `count_notifications(usuario)` (total y no leídas en una consulta), `list_notifications(usuario, view=, page=)` (20 por página, de la más reciente a la más antigua, con el ticket cargado en la misma consulta) y `get_notification(usuario, id)`. **Todas filtran por el usuario**: la de otra persona devuelve `None`.
- `mark_as_read(usuario, id)` y `mark_all_as_read(usuario)`: un solo `UPDATE ... WHERE leida = FALSE`, así que son idempotentes, conservan la **primera** lectura y, con dos pestañas a la vez, una sola escribe.

**Pantallas** (las ven los cuatro roles, cada uno las suyas; una notificación ajena responde 404 como una inexistente):

- `GET /notifications` (opción **Notificaciones** del menú, para todos los roles): pestañas «Todas» y «No leídas» con sus contadores (`?vista=no-leidas`; un valor inválido se trata como «todas»), 20 por página (`?page=`), «Marcar todas como leídas» solo si hay alguna sin leer y estados vacíos distintos por pestaña. Las no leídas llevan un punto y un fondo azul suave (tokens `--wd-primary-soft` y `--wd-on-primary`, nuevos en `app.css`) y un «(no leída)» para lectores de pantalla.
- `POST /notifications/<id>/read` (marcar como leída), `POST /notifications/<id>/open` (marcar y abrir el ticket; sin ticket, vuelve al listado) y `POST /notifications/read-all`: **todo lo que cambia algo es POST con CSRF**, también «abrir» (un GET no debe cambiar nada). Vuelven al listado con la pestaña y la página en que estaba la persona. Abrir no es un permiso: si ya no ve el ticket, este responde 404.
- `GET /notifications/unread-count`: `{"unread": N}` sin caché, para la campana.

**La campana** (`layouts/app.html`, a la izquierda del menú del usuario) es un enlace al centro con el contador de no leídas (sin número si no hay; «99+» desde 100). `layout_context` (`navigation.py`) calcula el número en cada página autenticada y `static/js/common/notifications.js` (mejora progresiva) lo actualiza cada 30 segundos mientras la pestaña está visible y al volver a ella; se detiene si el servidor deja de responder JSON (sesión caducada: responde `401`). Esa consulta **no cuenta como actividad** de la persona y no renueva la sesión (ver "15. Sesiones"). Es un polling simple, sin WebSockets (`docs/12`, sección 32, los deja para después del MVP).

**Seed de demostración** (`seeds/demo_notifications.py`): `seed-demo-notifications [--username ...]` (ver "22. CLI"). Mientras nada genera avisos, deja cinco notificaciones de ejemplo por persona, escritas para su rol: el personal recibe asignaciones, respuestas, SLA próximo a vencer, SLA vencido y reaperturas; el Solicitante, cambios de estado, respuestas, la revisión de la solución, el cierre y la creación (el SLA es solo para el personal). Cada aviso apunta a un ticket **que esa persona puede ver** (el mismo criterio que el listado de tickets), unos están leídos y otros no, y su antigüedad va de minutos a días. Es idempotente por (persona, ticket, evento, mensaje).

## Avisos por los eventos de un ticket (entrega 6 de `v0.5.0`)

Reglas completas en `docs/06` (RN-168) y `docs/10` (28.1, «Notificaciones internas»). **Sin migración ni pantallas nuevas.** Quién recibe cada aviso se decide en `notifications/events.py`, que las operaciones de los tickets llaman al terminar, dentro de su propia transacción (sin commit: el aviso se confirma o se revierte con la operación):

- `change_state` → `notify_state_change`; `assign_technician` → `notify_assignment`; `unassign_technician` → `notify_unassignment`; `escalate_ticket` → `notify_escalation`; `add_comment` → `notify_comment`. Al estar en los servicios, los cubren también el seed y cualquier otra vía.
- **Reglas comunes:** nunca se avisa a quien hizo el cambio; solo a solicitantes no retirados y técnicos que siguen asignados; un Solicitante solo recibe lo que vería en el historial (nada de notas internas, escalamientos, grupo, motivos ni texto de comentarios o de la solución: los avisos dicen qué pasó y en qué ticket, nunca copian el contenido).
- **Quién recibe qué** (tabla completa en RN-168): asignar avisa al técnico y a los solicitantes; los cambios de estado, a solicitantes y técnicos asignados (resolver pide al solicitante revisar la solución, RN-95; reabrir avisa a los técnicos, RN-96); un comentario público del personal avisa a los solicitantes y el de un solicitante a los técnicos asignados (RF-068); una nota interna, a los demás técnicos asignados; escalar, a los técnicos que entran y salen. **Crear un ticket no avisa a nadie.** Las asignaciones derivadas de estado (`Nuevo` ↔ `Asignado`) no se avisan aparte.
- **`STATE_NOTICES`** (por acción de estado, el aviso a los solicitantes y el de los técnicos) y un test exige que toda acción de `STATE_ACTIONS` figure en ella, así que una acción nueva obliga a decidir a quién avisa.
- **Seed de tickets de demostración:** `seed-demo-tickets` ejecuta los servicios reales, que ahora avisan; al terminar elimina los avisos de los tickets que creó (solo esos) para que su historia, que es del pasado, no llene a nadie de avisos sin leer. Los avisos de ejemplo se cargan con `seed-demo-notifications`.

---

# 11 nonies. Indicadores de SLA

Entrega 7 de `v0.5.0`. Reglas completas en `docs/06` (RN-169, que precisa RN-88 y RN-91), `docs/09` (20.3), `docs/10` (28.1, «Indicadores de SLA») y `docs/11` (UI-003 y UI-005). **Incluye una migración** (`add_warning_threshold_to_sla_periods`). El SLA es **solo del personal**.

**Qué cambió en los períodos** (`models/periodo_sla.py`, `sla/periods.py`):

- Dos columnas nuevas en `tickets_sla_periodos`: `umbral_aviso_porcentaje` (copia del umbral de la política, como los objetivos) y `fecha_umbral_aviso` (cuándo el consumo lo alcanza, en tiempo laboral, calculada al abrir el período como el vencimiento). `warning_seconds` da el consumo exacto (el entero siguiente a `objetivo * porcentaje / 100`) y un test comprueba que es el primer segundo que alcanza el porcentaje. Dos `CHECK`: el umbral entre 1 y 100 y la fecha de aviso entre el inicio y el vencimiento (y solo con el reloj en marcha). La migración copia el umbral de la política a los períodos existentes; `sla-rebuild` completa su fecha (`fill_missing_warning_dates`).
- **Cambia un criterio anterior:** el umbral ya no se lee de la política al evaluar (editarlo alteraba un SLA en curso); se hereda como los objetivos. Y un ticket resuelto o cerrado nunca está «próximo a vencer»: queda dentro de plazo o vencido.
- **Evaluación por lotes** (`evaluate_tickets_sla`): el estado de muchos tickets con un número fijo de consultas (períodos, estados, primeras respuestas y un reloj por calendario distinto); `evaluate_ticket_sla` es el caso de uno. `SlaSnapshot.overdue_seconds` es lo que el consumo pasa del objetivo y `SLA_STATUS_LABELS`, los nombres de cada estado.

**Filtrar y ordenar en la base de datos** (`sla/queries.py`): `SlaFilter` (`dentro`, `proximo`, `vencido`, `pausado`, `sin`), `sla_condition(opción, now)` y `sla_urgency_order()` expresan el estado del SLA como condiciones SQL con las fechas guardadas, y son el equivalente exacto de la evaluación en Python: un test los compara en catorce tipos de ticket y más de 150 momentos (con los bordes de un segundo). El orden «SLA más urgente» pone primero el vencimiento más cercano (los ya vencidos van delante) y al final los que no tienen reloj en marcha.

**Listado** (`GET /tickets`): para el personal, parámetro `sla` (valores inválidos se ignoran), orden `orden=sla`, columna «SLA» con la insignia y el tiempo que queda o que se pasó, e insignia en las tarjetas móviles. El instante es uno por petición y lo usan el filtro, los contadores de las pestañas y las insignias. **Para un Solicitante los dos parámetros no existen** (se ignoran en la ruta y también en `list_tickets`), así que no puede deducir el SLA probando filtros. El SLA de la página sale por lotes: las mismas consultas con una fila o con quince (hay un test).

**Detalle:** tarjeta «SLA» (solo personal) con la insignia, la barra de consumo, `5 h 30 min de 6 h (91 %)`, el vencimiento (o «Detenido» / «En pausa»), la primera respuesta y, plegada, la lista de períodos con el motivo de cada cambio de prioridad. Un ticket sin SLA lo dice.

**Bajar la prioridad con el SLA en riesgo** (RN-88): la pantalla `/tickets/<n>/priority` muestra una alerta (ámbar o roja) si el SLA está próximo a vencer o vencido. `change_priority` evalúa el SLA antes del cambio y, si estaba en riesgo y la prioridad baja (nivel menor), `notify_priority_lowered` (`notifications/events.py`) crea un aviso `SLA_PRIORIDAD_BAJADA` para los **Supervisores responsables del grupo del ticket** (activos) o, si no tiene grupo o ninguno está activo, **todos los Supervisores activos**; nunca a quien hizo el cambio. No copia el motivo. No se avisa al subir la prioridad ni con el SLA dentro de plazo, pausado o inexistente.

**Seed de demostración:** `seed-demo-tickets` ya deja las fechas de aviso (los períodos se abren con el mismo código) y un test lo comprueba. No hay datos nuevos que sembrar.

---

# 11 decies. Planificador

Entrega 8 de `v0.5.0`, en `src/workdesk/scheduler.py`. Reglas completas en `docs/06` (RN-170, que aplica RN-58, RN-59 y RN-91) y `docs/10` (secciones 84 a 87). **Incluye una migración** (`add_sla_notice_marks_to_sla_periods`). Sin pantallas nuevas.

**El comando.** `run-scheduler` (ver "22. CLI") es un comando propio, sin APScheduler ni otra dependencia: sin opciones se queda en marcha y repite las dos tareas cada `SCHEDULER_INTERVAL_SECONDS` segundos (60 por defecto, `--interval` lo cambia; Ctrl+C lo detiene); con `--once` hace una pasada y termina, para el Programador de tareas de Windows o `cron`. Es un proceso separado del web, con el mismo código y la misma base de datos. Si algún elemento falla, `--once` termina con error.

**Idempotencia.** Las tareas se pueden repetir, o correr dos planificadores a la vez, sin duplicar nada. Cada elemento (un período, un ticket) se procesa en **su propia transacción**: se bloquea el **ticket** (siempre el ticket primero y su período después, que es el orden de los cambios de estado y de prioridad), se **vuelve a comprobar** que sigue correspondiendo (otra transacción pudo cambiarlo desde que se lo encontró) y solo entonces se actúa y se confirma. Un fallo deshace solo ese elemento, se registra en el log y se sigue con los demás. Este módulo es de los pocos que hace commit: es quien inicia las transacciones.

**Avisos de SLA** (`run_sla_notices`). Busca los períodos en marcha cuyo `fecha_umbral_aviso` o `fecha_vencimiento_resolucion` ya pasó sin que el aviso se hubiera enviado. Las marcas están en el propio período: `fecha_aviso_umbral_enviado` y `fecha_aviso_vencimiento_enviado` (dos columnas nuevas; un período nuevo de la misma prioridad las hereda y un cambio de prioridad empieza sin ellas; la migración da por avisado lo que los períodos abiertos ya habían alcanzado, para que la primera ejecución no avise de todo lo atrasado). *Próximo a vencer* (`SLA_PROXIMO_A_VENCER`): a los técnicos asignados o, si no hay, a los Supervisores del grupo (o a todos). *Vencido* (`SLA_VENCIDO`): a los técnicos asignados y a esos Supervisores. Nunca a los solicitantes. Si se encuentra ya vencido, solo se envía el de vencido. Los destinatarios se deciden en `notifications/events.py` (`notify_sla_warning` y `notify_sla_breach`). **Al vencer, además, el incumplimiento queda registrado** (RN-91): el evento interno `SLA_VENCIDO` del historial, con el Sistema como actor y, en el contexto, el período, el objetivo en minutos y el instante en que venció; se guarda en la misma transacción que el aviso, así que una sola vez. Solo lo ve el personal.

**Cierre automático** (`run_auto_close`). Busca los tickets `Resuelto` cuya resolución es anterior a `AUTO_CLOSE_HOURS` horas (horas corridas, 24 por defecto) y llama a `close_automatically` (`tickets/lifecycle.py`). Esta función bloquea el ticket y **vuelve a comprobar** el estado, el plazo (la fecha de resolución sigue siendo anterior al límite, así que un ticket rechazado y resuelto de nuevo reinicia la espera) y que la transición `AUTO_CIERRE` siga activa; cierra con el motivo `INACTIVIDAD`, `cerrado_automaticamente` verdadero y sin usuario que cierra; registra `TICKET_CERRADO` con actor **Sistema** (`actor_tipo` `SISTEMA`) y `contexto["accion"]` `AUTO_CIERRE`; sube la versión, detiene el SLA y avisa a los solicitantes vigentes y a los técnicos asignados («Ticket cerrado automáticamente»). Reutiliza `_closing_changes`, así que «cerrado ⇒ fecha y motivo» sigue sin poder romperse. Para que el sistema pudiera actuar sin usuario, `apply_ticket_changes` y las funciones de avisos admiten `actor=None`. Un ticket cerrado así se puede reabrir como cualquier otro (la reapertura limpia `cerrado_automaticamente`).

**Configuración.** `AUTO_CLOSE_HOURS` y `SCHEDULER_INTERVAL_SECONDS`, variables de entorno validadas al iniciar (enteros mayores que cero) hasta que la configuración administrable de `v0.7.0` las reemplace.

**Seed de demostración.** No cambia: un cierre automático depende del paso del tiempo, no se siembra. Una base **nueva** cargada con `seed-demo-tickets` deja sus períodos sin marcas, así que el primer `run-scheduler` avisa de todo lo que ya está vencido o próximo y cierra lo resuelto sin validar desde hace más de 24 horas. Una base de desarrollo **anterior** a la migración tiene esos avisos marcados como ya enviados (a propósito): para ver avisos hay que reiniciar las marcas de unos pocos períodos a mano y, para ver un cierre automático, resolver un ticket y envejecer su `fecha_resolucion` (SQL en el README, paso 19). Lo mismo vale tras `sla-rebuild`: los períodos que crea empiezan sin marcas y el planificador avisa una vez de los que ya estén vencidos.

---

# 12. Autenticación actual

La autenticación utiliza:

```text
username + contraseña
```

No utiliza actualmente:

- email como identificador de login;
- registro público;
- recuperación pública de contraseña;
- selector de rol;
- remember-me.

## Implementado

- login;
- logout;
- Flask-Login;
- protección de rutas;
- usuario activo/inactivo;
- Argon2id;
- rehash de contraseña cuando corresponde;
- bloqueo temporal por intentos fallidos;
- CSRF;
- `token_version`;
- configuración segura de cookies;
- mensajes genéricos de error de autenticación.

---

# 13. Política de intentos fallidos

Configuración actual:

```text
5 intentos fallidos
→ bloqueo durante 15 minutos
```

Ambos valores son configurables mediante variables de entorno.

---

# 14. Contraseñas

Se utiliza:

```text
Argon2id
```

mediante:

```text
argon2-cffi
```

Las funciones actuales permiten:

- generar hash;
- verificar contraseña;
- detectar necesidad de rehash.

Nunca almacenar ni registrar contraseñas en texto plano.

## Política de contraseñas

Implementada en `src/workdesk/security/password_policy.py`. Es la única fuente de la regla: la usan el cambio propio, las contraseñas temporales y `create-admin`.

- Longitud mínima: `PASSWORD_MIN_LENGTH` (12 por defecto). La aplicación no arranca si el valor está fuera del rango 8 a 128.
- Longitud máxima: 128 caracteres.
- Sin reglas de composición (mayúsculas, números, símbolos).
- No se recortan espacios; una contraseña solo de espacios no es válida.
- En un cambio propio, la nueva debe ser distinta de la actual.
- `generate_temporary_password`: 16 caracteres aleatorios (`secrets`), sin caracteres ambiguos.

## Operaciones de contraseña

Implementadas en `src/workdesk/auth/credentials.py`. Ninguna hace commit: se confirman junto con la operación que las invoca.

- `change_own_password`: verifica la contraseña actual, valida la nueva, limpia `debe_cambiar_password`, sube `token_version` (invalida todas las sesiones, incluida la actual: quien llama debe reiniciar la sesión actual) y audita `PASSWORD_CAMBIADA`.
- `set_temporary_password`: asigna una contraseña temporal y marca `debe_cambiar_password` (para crear usuarios).
- `reset_password`: restablecimiento por un Administrador. Asigna la temporal, exige el cambio, invalida las sesiones, limpia intentos fallidos y bloqueo, y audita `PASSWORD_RESTABLECIDA`.
- La auditoría nunca incluye contraseñas ni hashes.

`change_own_password` se invoca desde `/account/password`, `set_temporary_password` desde la creación de usuarios y `reset_password` desde el restablecimiento por el Administrador (`users.service.reset_user_password`, que además impide restablecer la propia contraseña).

## Cambio de contraseña propio y cambio obligatorio

Blueprint `account` (`src/workdesk/account/`), ruta `GET, POST /account/password` con formulario Flask-WTF (CSRF) de contraseña actual, nueva y confirmación. El formulario solo valida su forma; las reglas de la contraseña las aplica la política (`security/password_policy.py`).

- **Contraseña actual incorrecta:** cuenta como intento fallido y respeta el bloqueo temporal. Al alcanzar el máximo de intentos se cierra la sesión; con la cuenta bloqueada no se acepta ningún cambio, ni siquiera con la contraseña correcta.
- **Cambio correcto:** sube `token_version` (invalida las demás sesiones), reinicia los intentos fallidos y vuelve a iniciar la sesión actual para no desconectar al usuario. El inicio de la sesión no se reinicia: cambiar la contraseña no amplía la duración máxima (8 horas por defecto).
- **Cambio obligatorio:** mientras `debe_cambiar_password` sea verdadero, un `before_app_request` (`require_password_change`, en `auth/routes.py`) redirige cualquier ruta a `/account/password`. Solo se permiten esa pantalla, `POST /logout` y las rutas técnicas (`/health`, `static`). Se aplica en backend, no solo ocultando enlaces, y se ejecuta después de los límites de sesión.
- La pantalla tiene dos modos. En modo obligatorio (`account/password_required.html`) es una pantalla aislada, con el estilo del login, sin navegación y con la opción de cerrar sesión. En modo normal (`account/password.html`) usa el layout principal con Bootstrap y el botón "Volver a Mi cuenta".

## Mi cuenta

`GET, POST /account` (`src/workdesk/account/`), disponible para todos los roles (RN-150). Usa el layout principal y se enlaza desde la sidebar y desde el menú del avatar.

- **Mis datos:** nombre, usuario, correo y rol, de solo lectura (los gestiona el Administrador).
- **Información de contacto:** el usuario edita su teléfono, cargo y departamento o área. `account/service.py` (`update_own_contact`) delega en `users.service.update_profile`, así que reutiliza su validación y su auditoría (`USUARIO_MODIFICADO` con el propio usuario como actor y solo los campos cambiados). Aunque el formulario reciba nombre, apellido, correo, username o rol, se ignoran.
- La pantalla no recibe el identificador de ningún usuario: solo edita la cuenta de la sesión actual.
- **Seguridad:** enlace al cambio de contraseña.
- Con el cambio de contraseña obligatorio pendiente, `/account` se redirige a `/account/password` (guardia de `auth/routes.py`).
- `ContactForm` (`users/forms.py`) comparte los campos de contacto con el formulario de edición del Administrador.
- Los errores se muestran junto a cada campo y nunca se devuelven las contraseñas enviadas.
- El botón "Mostrar/Ocultar" es una mejora progresiva (`static/js/common/password-toggle.js`, compartido con la creación de usuarios): el formulario funciona sin JavaScript.

---

# 15. Sesiones

La sesión utiliza Flask-Login.

Configuración relevante:

```text
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = Lax
SESSION_COOKIE_SECURE   = configurable
session_protection      = strong
```

En desarrollo local HTTP:

```text
SESSION_COOKIE_SECURE=false
```

En una futura ejecución HTTPS deberá utilizarse:

```text
SESSION_COOKIE_SECURE=true
```

## Límites de sesión

```text
Inactividad máxima:  SESSION_IDLE_MINUTES (30 por defecto)
Duración máxima:     SESSION_MAX_HOURS    (8 por defecto)
```

Al iniciar sesión se guardan en la cookie firmada el instante de inicio y el de última actividad. En cada petición autenticada se comprueban ambos límites (`before_app_request` en `auth/routes.py`; lógica en `auth/session.py`). Si alguno se supera, se cierra la sesión y se redirige al login con el aviso "Tu sesión expiró".

- Una sesión autenticada sin marcas de tiempo válidas se considera expirada.
- `/health` y `static` no renuevan la actividad ni provocan la expiración.
- Las consultas que el navegador hace solo (hoy, la de la campana de notificaciones, cada 30 segundos: `PASSIVE_ENDPOINTS` en `auth/session.py`) **se comprueban como cualquier petición pero no cuentan como actividad**: si contaran, una pestaña abandonada renovaría la sesión sin parar y la inactividad nunca se aplicaría. Con la sesión expirada responden `401` en JSON, sin cerrarla: la siguiente acción de la persona la cierra con su aviso. El latido del bloqueo de edición de un ticket (`v0.4.0`) sí renueva la sesión mientras la pantalla de edición está abierta: quien tiene un formulario abierto está trabajando.
- Valores menores o iguales a cero impiden iniciar la aplicación.

## token_version

Cada usuario posee:

```text
token_version
```

Si la versión almacenada en la sesión no coincide con la versión actual del usuario:

```text
sesión inválida
```

Esto permite invalidar sesiones anteriores sin mantener una tabla persistente de sesiones.

---

# 16. CSRF

Se utiliza:

```text
Flask-WTF / CSRFProtect
```

Las operaciones que modifican estado deben respetar CSRF.

El logout actual utiliza:

```text
POST /logout
```

y requiere autenticación.

---

# 17. Rutas actuales

```text
GET        /
GET, POST  /login
POST       /logout
GET        /dashboard
GET, POST  /account
GET, POST  /account/password
GET        /admin
GET        /users
GET, POST  /users/new
GET        /users/<id>
GET, POST  /users/<id>/edit
GET, POST  /users/<id>/role
GET, POST  /users/<id>/deactivate
GET, POST  /users/<id>/activate
GET, POST  /users/<id>/reset-password
GET        /admin/categories
GET, POST  /admin/categories/new
GET, POST  /admin/categories/<id>/edit
GET, POST  /admin/categories/<id>/deactivate
GET, POST  /admin/categories/<id>/activate
GET        /admin/priorities
GET, POST  /admin/priorities/<id>/edit
GET, POST  /admin/priorities/<id>/deactivate
GET, POST  /admin/priorities/<id>/activate
GET        /admin/locations
GET, POST  /admin/locations/new
GET, POST  /admin/locations/<id>/edit
GET, POST  /admin/locations/<id>/deactivate
GET, POST  /admin/locations/<id>/activate
GET        /admin/wait-reasons
GET, POST  /admin/wait-reasons/new
GET, POST  /admin/wait-reasons/<id>/edit
GET, POST  /admin/wait-reasons/<id>/deactivate
GET, POST  /admin/wait-reasons/<id>/activate
GET        /admin/states
GET, POST  /admin/states/<id>/edit
GET, POST  /admin/transitions/<id>/deactivate
GET, POST  /admin/transitions/<id>/activate
GET        /admin/sla
GET, POST  /admin/sla/calendar
GET, POST  /admin/sla/priorities/<id>/edit
GET, POST  /admin/sla/priorities/<id>/deactivate
GET, POST  /admin/sla/priorities/<id>/activate
GET        /groups
GET, POST  /groups/new
GET        /groups/<id>
GET, POST  /groups/<id>/edit
GET, POST  /groups/<id>/deactivate
GET, POST  /groups/<id>/activate
POST       /groups/<id>/members/add
GET, POST  /groups/<id>/members/<membership_id>/remove
POST       /groups/<id>/supervisors/add
GET, POST  /groups/<id>/supervisors/<designation_id>/remove
GET        /tickets
GET, POST  /tickets/new
GET        /tickets/<public_id>
GET, POST  /tickets/<public_id>/edit
GET, POST  /tickets/<public_id>/priority
GET, POST  /tickets/<public_id>/status/<action_slug>
POST       /tickets/<public_id>/assign-me
POST       /tickets/<public_id>/unassign-me
GET        /tickets/<public_id>/assignment
POST       /tickets/<public_id>/assignment/technicians/add
POST       /tickets/<public_id>/assignment/technicians/<assignment_id>/remove
POST       /tickets/<public_id>/assignment/group
GET, POST  /tickets/<public_id>/escalate
GET        /tickets/<public_id>/requesters
POST       /tickets/<public_id>/requesters/add
GET, POST  /tickets/<public_id>/requesters/<participation_id>/remove
POST       /tickets/<public_id>/comments
GET, POST  /tickets/<public_id>/comments/<comment_id>/edit
GET, POST  /tickets/<public_id>/comments/<comment_id>/delete
POST       /tickets/<public_id>/attachments
GET        /tickets/<public_id>/attachments/<attachment_id>/download
GET, POST  /tickets/<public_id>/attachments/<attachment_id>/delete
GET        /tickets/<public_id>/relations
POST       /tickets/<public_id>/relations/add
GET, POST  /tickets/<public_id>/relations/<relation_id>/remove
GET, POST  /tickets/<public_id>/duplicate
POST       /tickets/<public_id>/lock/renew
POST       /tickets/<public_id>/lock/release
GET        /notifications
POST       /notifications/<id>/read
POST       /notifications/<id>/open
POST       /notifications/read-all
GET        /notifications/unread-count
GET        /health
GET        /static/<path:filename>
```

`/dashboard`, `/account`, `/account/password` y todas las rutas `/tickets...` requieren autenticación. En los tickets la autorización va más allá del login (ver "Creación y detalle de tickets" y "Edición de tickets"): el detalle y las pantallas de edición responden 404 a quien no puede ver el ticket, y las de edición, prioridad y solicitantes responden 403 a quien lo ve pero no puede usarlas (el Solicitante). En los comentarios, una nota interna que el usuario no puede ver responde 404 y editar o eliminar uno ajeno (o propio fuera de plazo), 403.

`/account` es "Mi cuenta" (ver "Mi cuenta"). `/account/password` permite al usuario cambiar su propia contraseña (ver "Cambio de contraseña propio y cambio obligatorio").

Las rutas `/notifications...` las ven los cuatro roles, cada uno las suyas: una notificación ajena responde 404 como una inexistente (ver "Notificaciones internas").

`/admin`, todas las rutas `/admin/...` (categorías, prioridades, ubicaciones y motivos de espera, ver "Administración de catálogos", estados y transiciones, ver "Administración de estados y transiciones", y SLA, ver "Calendario laboral administrable" y "Políticas de SLA") y todas las rutas `/users` requieren el rol Administrador. Las rutas `/groups...` requieren Administrador o Supervisor (403 al resto) y, dentro, cada acción se vuelve a comprobar (ver "Grupos") (403 para otros roles autenticados y redirección al login para anónimos). `/admin` es el hub de administración (ver "Layout y navegación"). No existe ruta de alta de prioridades (`/admin/priorities/new`): son exactamente cuatro.

Una prueba automática (`tests/test_route_protection.py`) recorre todas las rutas registradas y exige que, sin sesión, todas redirijan al login (salvo `/login`, `/health` y `static`) y que toda ruta POST rechace una petición sin token CSRF. Una ruta nueva queda cubierta sin tocar el test.

El dashboard actual es temporal.

No representa todavía los dashboards finales del MVP.

---

# 17 bis. Layout y navegación

## App shell

`templates/layouts/app.html` es el layout de las pantallas autenticadas (dashboard, administración y usuarios). Las pantallas de acceso y las páginas de error son independientes y no lo usan.

- **Sidebar** de 248 px sobre `#111827` con icono y texto. Se contrae a 72 px (solo iconos, con tooltip) con el botón "Contraer"; la preferencia se guarda en `localStorage` (`static/js/common/layout.js`, mejora progresiva). Por debajo de 992 px se convierte en `offcanvas`.
- **Topbar** de 64 px con avatar de iniciales, nombre, rol y menú de usuario (cambiar contraseña, cerrar sesión mediante POST con CSRF). En móvil: botón de menú, marca y avatar.
- **Accesibilidad:** enlace "Saltar al contenido", `aria-current="page"` en la opción activa, foco visible y etiquetas ARIA.
- **Avisos:** las categorías de `flash` (`success`, `error`, `warning`, `info`) se traducen a alertas de Bootstrap cerrables.
- **La campana de notificaciones** de la topbar (a la izquierda del menú del usuario) lleva al centro de notificaciones y cuenta las no leídas (ver "Notificaciones internas"). No se muestran controles que todavía no funcionan. El buscador de tickets de la topbar también funciona (ver "Listado de tickets").

## Navegación por rol

Se define en `src/workdesk/navigation.py` (`MAIN_NAVIGATION` y `ACCOUNT_NAVIGATION`) y se filtra **en backend** por rol antes de llegar a la plantilla: las opciones no autorizadas no se envían al navegador (`docs/11`, sección 5.5). Un `context_processor` (`layout_context`) entrega a la plantilla los enlaces del usuario con la opción activa marcada. Es solo presentación: cada ruta protegida sigue comprobando la autorización por sí misma.

- Hoy incluye solo las pantallas que existen: Dashboard (todos), Tickets (personal) o Mis tickets (Solicitante), Crear ticket (todos), Notificaciones (todos), Grupos (Supervisor), Administración (Administrador) y Mi cuenta (todos). "Tickets" y "Mis tickets" llevan al mismo listado y se marcan activas también en el detalle y en las pantallas de editar, cambiar prioridad, cambiar estado, asignación, escalamiento, solicitantes, y editar o eliminar un comentario o un archivo (`TICKET_SCREENS`); "Crear ticket" solo se marca activa en el formulario (`tickets.new_ticket`).
- Administración se marca activa en el hub, en todas las pantallas de usuarios, de catálogos, de grupos y de SLA; Grupos (del Supervisor), en las de grupos; Notificaciones, en el centro de notificaciones; Mi cuenta, en `/account` y en el cambio de contraseña.
- `layout_context` entrega además `unread_notifications` (el número de no leídas del usuario): una consulta por página autenticada, resuelta por el índice `(usuario_id, leida, fecha_creacion)`.
- Para añadir una opción cuando exista su pantalla, basta con añadir un `NavItem` indicando los roles que la ven.
- Las iniciales del avatar salen de `user_initials` (nombre y apellido; usa el username si no hay ninguno).

## Hub de administración

`GET /admin` muestra las cuatro secciones del diseño (UI-014), definidas en `src/workdesk/admin/hub.py`: Personas y organización, Configuración de tickets, Operación y políticas, y Sistema y seguridad. Están implementadas y enlazadas "Usuarios", "Grupos", "Categorías", "Prioridades", "Ubicaciones", "Motivos de espera", "Estados y transiciones" y "SLA"; el resto se muestra atenuado con la etiqueta "Próximamente" y sin enlace. Al implementar una sección basta con indicar su ruta en `hub.py`.

## Estilos

- `static/css/app.css`: tokens del Design System (`--wd-*`) y base.
- `static/css/theme.css`: mapea los tokens a las variables de Bootstrap (colores, radio, tipografía, botones, tarjetas, tablas, badges suaves). No se modifican los archivos de `static/vendor/`.
- `static/css/layout.css`: sidebar, topbar y hub.
- `static/css/auth.css`: login y cambio de contraseña (con sus estilos de formulario propios).

---

# 18. Login visual

Existe una interfaz visual de login implementada y validada.

Características:

- branding oficial mediante `workdesk-login-brand.svg`;
- username;
- contraseña;
- botón principal full-width;
- mostrar/ocultar contraseña;
- mensajes de error;
- conservación de username después de fallo;
- protección CSRF;
- diseño responsive;
- fondo `#F1F5F9`;
- card central clara;
- integración del favicon oficial.

La variante actual utiliza branding para tema claro.

Existe `workdesk-login-brand-inverse.svg` como recurso preparado para una futura implementación de modo oscuro, pero todavía no se conmuta dinámicamente en código.

No añadir sin una decisión funcional previa:

- remember-me;
- registro público;
- recuperación pública;
- selector de rol.

---

# 19. Health check

Existe:

```text
GET /health
```

Comprueba:

- aplicación;
- PostgreSQL.

Respuesta saludable:

```json
{
  "application": "ok",
  "database": "ok",
  "status": "ok"
}
```

HTTP:

```text
200
```

Si PostgreSQL falla:

```json
{
  "application": "ok",
  "database": "unavailable",
  "status": "degraded"
}
```

HTTP:

```text
503
```

No exponer detalles técnicos sensibles en la respuesta pública.

---

# 20. Manejo de errores

Existen handlers globales para:

```text
400
403
404
500
```

Se utiliza un template común de error.

No mostrar al usuario:

- stack traces;
- SQL interno;
- credenciales;
- secretos;
- rutas internas sensibles.

---

## Respuestas JSON y cabeceras de seguridad

WorkDesk no tiene API pública. Las cuatro rutas JSON (`GET /health`, `GET /notifications/unread-count`, `POST /tickets/<n>/lock/renew` y `POST /tickets/<n>/lock/release`) y el `401` de la sesión expirada son consultas que hace su propio JavaScript. `docs/10` (secciones 33 y 34) preveía un prefijo `/api/v1/` para cuando formen una interfaz reutilizable; hoy no lo usan y no se renombraron.

- **Una forma de error** (`responses.py`, `json_error`): `{"ok": false, "error": "<código>", "message": "<texto>"}`, con códigos estables (`session_expired`, `lock_held`, `ticket_closed`) y sin caché. Las respuestas correctas conservan su forma (`{"ok": true}`, `{"ok": true, "released": bool}`, `{"unread": N}` y la de `/health`).
- **Cabeceras en todas las respuestas** (`security/headers.py`, un único `after_request`; `setdefault`, así que una ruta que fija la suya, como la descarga de un adjunto, manda): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Content-Security-Policy` y `Cache-Control: no-store` en todo lo que no sea un archivo estático. `Strict-Transport-Security` solo con `SESSION_COOKIE_SECURE=true`.
- **La política de contenido** (`default-src 'self'`, `script-src 'self'`, `style-src 'self' 'unsafe-inline'`, `img-src 'self' data:`, `frame-ancestors 'none'`...) se apoya en dos hechos medidos: las 24 etiquetas `<script>` de las plantillas llevan `src` (no hay JavaScript en línea ni manejadores `on...=`) y solo quedan 3 atributos `style=` en línea, de datos (el ancho de la barra de SLA y el color de una prioridad), por eso los estilos admiten `'unsafe-inline'` y los scripts no.

# 21. Logging

Se utiliza:

```text
logging
```

con:

```text
RotatingFileHandler
```

Ruta actual:

```text
instance/logs/workdesk.log
```

Configuración predeterminada:

```text
5 MB por archivo
5 backups
```

Variables:

```text
LOG_LEVEL
LOG_MAX_BYTES
LOG_BACKUP_COUNT
```

No registrar:

- contraseñas;
- `SECRET_KEY`;
- credenciales de PostgreSQL;
- cookies;
- tokens;
- CSRF;
- hashes completos sin necesidad.

---

# 22. CLI

Comandos propios actuales:

```bash
python -m flask --app src.workdesk seed-roles
python -m flask --app src.workdesk seed-catalogs
python -m flask --app src.workdesk create-admin
python -m flask --app src.workdesk seed-demo
python -m flask --app src.workdesk seed-demo-tickets
python -m flask --app src.workdesk sla-rebuild
python -m flask --app src.workdesk sla-status <número>
python -m flask --app src.workdesk run-scheduler [--once] [--interval <segundos>]
python -m flask --app src.workdesk seed-demo-notifications [--username <usuario>]
```

Los comandos viven en el paquete `src/workdesk/cli/`, un módulo por área (`setup`: `seed-roles`, `seed-catalogs` y `create-admin`; `demo`: los tres `seed-demo*`; `sla`: `sla-rebuild` y `sla-status`; `scheduling`: `run-scheduler`), y `register_commands` los registra todos desde la Application Factory. Solo orquestan: la lógica está en los servicios.

`sla-rebuild` y `sla-status` calculan y muestran los períodos de SLA de los tickets (ver "Períodos de SLA").

`run-scheduler` (`src/workdesk/scheduler.py`, entrega 8 de `v0.5.0`, ver "Planificador"): avisa de los SLA próximos a vencer y vencidos y cierra los tickets `Resuelto` que nadie validó. Sin opciones queda en marcha (bucle cada `SCHEDULER_INTERVAL_SECONDS`, `--interval` lo cambia, Ctrl+C lo detiene); con `--once` hace una pasada. En el bucle solo imprime cuando hubo algo que hacer; con `--once` informa `SLA próximo a vencer: N. SLA vencido: N. Tickets cerrados automáticamente: N. Errores: N.` y falla si algún elemento falló. Se puede repetir sin riesgo.

`seed-demo-notifications` (`src/workdesk/seeds/demo_notifications.py`, entrega 5 de `v0.5.0`): deja cinco notificaciones de ejemplo por persona para ver el centro de notificaciones y la campana, para ver el centro con datos sin tener que provocar eventos (ver "Notificaciones internas").

- sin opciones, las crea para el equipo de `seed-demo`; con `--username` (se puede repetir), para esas cuentas, por ejemplo la del Administrador real, que `seed-demo` no crea;
- necesita tickets que la persona pueda ver (por ejemplo, los de `seed-demo-tickets`): cada aviso apunta a uno de ellos, con el mismo criterio de visibilidad que el listado. Quien no ve ningún ticket queda sin avisos y el comando lo informa con un `Aviso:`;
- el personal recibe avisos de asignación, respuesta, SLA próximo a vencer, SLA vencido y reapertura; el Solicitante, de cambio de estado, respuesta, revisión de la solución, cierre y creación. Unos quedan leídos y otros no, con antigüedades de minutos a días;
- es idempotente (no repite un aviso de la misma persona, ticket, evento y mensaje), se niega a ejecutarse con `APP_ENV=production` y falla con un mensaje claro si falta una cuenta o no hay usuarios de demostración (`seed-demo`);
- informa `Notificaciones demo creadas: N.`.

`seed-catalogs` (`src/workdesk/seeds/catalogs.py`): carga los estados, las transiciones entre estados, las prioridades con sus políticas de SLA, la categoría `Sin clasificar`, los motivos de cierre, los motivos de espera y los tipos de relación entre tickets. Es idempotente y no pisa lo que un Administrador haya cambiado. Informa cuántos registros creó de cada tipo (`políticas de SLA: N`); quien tenga una base anterior a la entrega 3 de `v0.5.0` debe volver a ejecutarlo para cargar las políticas. No carga ubicaciones ni categorías de ejemplo (ver "Catálogos de tickets").

`create-admin`:

- crea el Administrador inicial;
- valida datos básicos;
- exige la longitud mínima de contraseña configurada (`PASSWORD_MIN_LENGTH`, 12 por defecto).

`seed-demo` (`src/workdesk/seeds/demo.py`, RN-151):

- carga un equipo de soporte ficticio de 12 personas: 2 supervisores, 4 técnicos y 6 solicitantes, con correos `@workdesk.local`, y tres grupos de ejemplo con sus técnicos y supervisores responsables (`seed_demo_groups`, idempotente por nombre);
- **no crea ningún Administrador** (el real se crea con `create-admin`);
- pide la contraseña común al ejecutarse (oculta, con confirmación) o la toma de la variable `WORKDESK_DEMO_PASSWORD`; la valida con la política de contraseñas y nunca la muestra ni la guarda;
- carga antes los roles estructurales (`seed-roles`);
- es idempotente: omite a quien ya tenga ese username o ese correo y al grupo que ya exista, sin modificarlos;
- se niega a ejecutarse con `APP_ENV=production`;
- los usuarios quedan activos y sin cambio de contraseña obligatorio, y cada creación (de un usuario o de un grupo) se audita como acción del sistema.

`seed-demo-tickets` (`src/workdesk/seeds/demo_tickets/` (un paquete) y `demo_tickets_data.py`):

- carga 76 tickets de demostración, escritos como los escribiría gente real y poco técnica (títulos vagos, prisa, el problema equivocado, prioridades exageradas), a nombre del equipo de `seed-demo`: cerca de un 70 % los crean Solicitantes (que quedan como su propio solicitante, como en la pantalla de creación) y el resto el personal, con 0, 1 o 2 solicitantes;
- **datos separados de la lógica:** `demo_tickets_data.py` solo contiene la lista (`DEMO_TICKETS`, de `DemoTicket` y `DemoAdjustment`); `demo_tickets.py` tiene el motor. Cada ticket tiene una `clave` estable (nombre corto, único, que no debe cambiar una vez cargado). Para mejorar la demostración se edita la lista. Cada paso de ajuste admite campos opcionales con valor por defecto (hoy `estado`, `motivo_espera`, `texto`, `grupo`, `asignar`, `agregar_solicitante`, `retirar_solicitante`, `motivo_retiro`, `comentario`, `nota_interna` y `adjunto`) y, cuando existan cierres y comentarios, se añaden más sin invalidar los tickets ya escritos;
- necesita `seed-catalogs` y `seed-demo`; si faltan, se detiene con un mensaje que dice qué ejecutar, y lo mismo si hay transiciones deshabilitadas que la demostración recorre («Habilítalas en Administración → Estados y transiciones»), sin cargar nada. **No crea categorías ni ubicaciones**: busca por nombre exacto `Redes`, `Hardware`, `Correo`, `Impresoras` y las ubicaciones `Suc Lo Marcoleta` y `Suc Manuel Antonio Matta` (sin distinguir mayúsculas); si falta alguna, usa `Sin clasificar` o deja el ticket sin ubicación y lo informa con un `Aviso:`. Las prioridades se resuelven por código, para sobrevivir a un renombrado;
- usa los servicios reales (`create_ticket`, `update_ticket`, `change_priority`, `set_group`, `assign_technician`, `add_requester`, `remove_requester`, `add_comment`, `add_attachments` y `change_state`), así que valida, versiona y registra el historial igual que la aplicación. Los `ajustes` son pasos posteriores del personal (reclasificar, cambiar la prioridad con motivo, corregir el título, **cambiar el estado**) con su propio actor y retraso. Un ajuste con `estado` (`INICIAR`, `PONER_EN_ESPERA` o `REACTIVAR`) se ejecuta al final del paso; `motivo_espera` es el código de un motivo del catálogo y `texto` una explicación libre (solo con un motivo que la admita, como `OTRO`);
- **identidad y marca, sin migración:** al crear un ticket, el motor marca en `historial_ticket.contexto` todos los eventos que genera con `{"demo_clave": <clave>, "demo_paso": <n>}` (0 = creación, 1... = cada ajuste), junto al `motivo` si lo hay. Es la única huella del seed: permite reconocer el ticket aunque después cambie de título (en la lista o a mano) y distinguir los eventos del seed de los hechos a mano. La aplicación solo lee `contexto["motivo"]`, así que la marca no se ve en la interfaz;
- **no duplica y refresca al volver a ejecutarlo:** un ticket cuya clave ya existe no se vuelve a crear, se *refresca*: se reescriben sus fechas relativas al nuevo día de ejecución (`fecha_creacion`, `fecha_modificacion`, `fecha_hora` de los eventos del seed según su paso y `fecha_asociacion` de los solicitantes). Ejecutarlo el mismo día deja exactamente las mismas fechas, y un refresco da lo mismo que una carga nueva ese día (hay un test que lo comprueba). Las ediciones hechas a mano sobre un ticket demo (eventos sin marca) se desplazan lo mismo que el último evento del seed para seguir después de él y se recortan a «hace un minuto» si quedaran en el futuro; la fecha de modificación acompaña al evento que la originó. **No toca el contenido** (título, descripción, categoría, prioridad, versión) ni crea eventos, y nunca toca tickets creados a mano. Para cambiar el contenido de tickets ya cargados hay que recrear la base de desarrollo;
- **fechas relativas en tiempo laboral:** todo corre según un calendario laboral configurable (`WorkCalendar` / `DEMO_CALENDAR` en `worktime.py`: `dias`, `inicio`, `fin` y `feriados`; por defecto lunes a viernes de 09:00 a 18:00, sin feriados). `hace_dias` son *días laborales* antes del último día laboral (si se ejecuta un fin de semana, se cuenta desde el viernes); `hora` (en `APP_TIMEZONE`) debe caer dentro de la jornada, con el fin excluido; y `despues_horas` de cada ajuste son *horas laborales* desde el paso anterior, de modo que el reloj salta noches, fines de semana y feriados. Nada cae fuera del calendario ni en el futuro (se recorta al último momento laboral ya pasado). Desde la entrega 2 de `v0.5.0` el seed lee el calendario vigente (`resolve_work_calendar`): el que guarde el Administrador desde «SLA» o, si no hay ninguno, `DEMO_CALENDAR`, que es el calendario por defecto de todo el sistema. Con uno guardado, todas las fechas caen dentro de sus franjas y en su zona horaria, y la hora de creación de cada ticket pasa al siguiente momento de trabajo si cae en una pausa; `hora` debe caer dentro de la jornada solo cuando se usa el calendario por defecto (ver "Calendario laboral administrable"). El motor de tiempo laboral (antes `_BusinessClock`) es un módulo propio, `worktime.py`, que usará también el SLA (ver "Tiempo laboral"). Como los servicios sellan la hora actual, las fechas se escriben con un `UPDATE` de Core solo en las filas que el propio seed creó (`tickets`, `tickets_solicitantes` e `historial_ticket`). Es el único lugar del proyecto que lo hace: el guard del ORM sigue rechazando cualquier modificación normal del historial y los servicios no recibieron parámetros de fecha;
- valida sus datos antes de tocar la base (`validate_demo_tickets`: calendario coherente, horas dentro de la jornada, claves y títulos únicos, usuarios y roles, categorías y prioridades conocidas, motivo obligatorio al cambiar la prioridad, y que la secuencia de acciones de estado de cada ticket sea ejecutable desde Nuevo con la matriz de transiciones y con motivos y textos coherentes...);
- **períodos de SLA:** al terminar recalcula los períodos de todos sus tickets desde su historial (`rebuild_ticket_periods`): los servicios los abren con la hora real de la carga y el historial se mueve después a fechas pasadas, así que ese cálculo se descarta y se rehace sobre la línea de tiempo del seed. Los tickets quedan en tiempo, próximos a vencer, vencidos y pausados. Ver "Períodos de SLA";
- una sola transacción: si algo falla se revierte todo (`DemoTicketsError`);
- se niega a ejecutarse con `APP_ENV=production`;
- **grupo y asignación:** los seis últimos de la lista (bloque "Tickets con grupo y asignación") se asignan a técnicos y se agrupan: uno solo con grupo (queda `Nuevo`), uno con dos técnicos (uno se asigna a sí mismo y otro lo asigna un Supervisor), dos que además se inician y uno que queda en espera. Necesitan los grupos de `seed-demo`: si faltan, se avisa y el ticket queda sin grupo;
- los tickets sin cambios de estado ni asignación quedan en `Nuevo`; los ocho del bloque "Tickets con cambios de estado" quedan En progreso o En espera, con los cinco motivos de espera y un ciclo completo (iniciar, esperar y reactivar). **Necesita que `seed-catalogs` haya cargado las transiciones** (si faltan se detiene con ese mensaje) y, si un motivo de espera falta o está desactivado, registra la espera sin motivo y lo avisa. Al volver a ejecutarlo solo se crean los tickets nuevos de la lista: un ticket ya cargado no cambia de estado, grupo ni técnicos (hay que recrear la base de desarrollo para verlo en tickets antiguos). Los cambios de estado y de grupo no necesitan extender el refresco de fechas (sus eventos llevan la marca del seed); las asignaciones sí, porque `tickets_tecnicos` tiene fechas propias: se reescriben siguiendo a su evento (`contexto["asignacion_id"]`). Una asignación sin evento propio —por ejemplo, la que cierra un escalamiento hecho a mano, cuyo evento `TICKET_ESCALADO` no lleva `asignacion_id`— sigue al evento cuya hora coincide con la suya (se crean en la misma transacción) y su cierre nunca queda antes de su asignación (el `CHECK` de la base de datos lo exige);
- **solicitantes agregados y retirados:** los cuatro últimos de la lista (bloque "Tickets con solicitantes agregados y retirados") cambian de solicitantes después de crearse. Sus filas de `tickets_solicitantes` también tienen fechas propias: se escriben al crear y se refrescan siguiendo a sus eventos (`contexto["participacion_id"]`), en una sola actualización por fila para que un retiro nunca preceda a su asociación; los solicitantes de la creación siguen a la fecha de creación. Ver "Solicitantes del ticket";
- **comentarios y notas internas:** los cinco últimos de la lista (bloque "Tickets con comentarios y notas internas") tienen una conversación: respuestas del personal, comentarios de un Solicitante y notas internas (uno con más notas que comentarios públicos). Un paso con `comentario` escrito por un Solicitante debe ser solo ese comentario y su actor, el creador o un solicitante del ticket en ese momento (la validación lo simula); el comentario público se escribe antes que la nota y ambos antes del cambio de estado. Los comentarios tienen fechas propias (`fecha_creacion`, `fecha_modificacion` y `fecha_eliminacion`): se escriben al crear y se refrescan siguiendo a sus eventos (`contexto["comentario_id"]`), también las ediciones y eliminaciones hechas a mano. Los comentarios no suben la versión del ticket, así que no mueven su fecha de modificación. Ver "Comentarios y notas internas";
- **archivos adjuntos:** los dos últimos de la lista (bloque "Tickets con archivos adjuntos") llevan archivos reales de texto (`adjunto=("nombre.log", "contenido")`, solo `.txt`, `.log` o `.csv`), guardados con el servicio real en `UPLOADS_DIR` (`instance/uploads`; en los tests, un directorio temporal). El archivo cuelga del comentario público del paso, si no de la nota y si no, del ticket. Las fechas (`fecha_subida`, `fecha_eliminacion`) se escriben al crear y se refrescan siguiendo a sus eventos (`contexto["archivo_id"]`); volver a ejecutar el seed no duplica archivos. Ver "Archivos adjuntos".
- **resolución, cierre y reapertura:** los siete últimos de la lista (bloque "Tickets con resolución, cierre y reapertura") recorren cada camino: uno Resuelto pendiente de validación, uno confirmado por su solicitante (cerrado con `RESOLUCION_VALIDADA`), uno rechazado y resuelto por segunda vez (dos ciclos), un cierre directo sin solicitante, una cancelación (cierre directo con `motivo_cierre="CANCELACION"`), uno Resuelto sin solicitante cerrado por un Supervisor (cierre excepcional) y uno cerrado y reabierto. Los pasos usan `estado` con `RESOLVER`, `CIERRE_DIRECTO`, `CIERRE_EXCEPCIONAL`, `CONFIRMAR`, `RECHAZAR` o `REABRIR` y `texto` (la solución, el motivo de un rechazo o de un cierre) y los ejecutan los servicios reales. `CONFIRMAR` y `RECHAZAR` los ejecuta un Solicitante que sea solicitante del ticket en ese momento (el paso no puede cambiar nada más salvo su comentario público); `CIERRE_EXCEPCIONAL`, un Supervisor; y un ticket cerrado solo admite un paso `REABRIR`, solo. Las fechas de la resolución y el cierre (`tickets.fecha_resolucion` y `fecha_cierre`) y de cada validación (`validaciones.fecha_validacion`) se escriben al crear y se refrescan siguiendo a sus eventos (`TICKET_RESUELTO`, `TICKET_CERRADO` y `contexto["validacion_id"]`), también los hechos a mano; una reapertura hecha a mano deja el ticket sin fechas de cierre. Ver "Resolución, validación, cierre y reapertura".
- **relaciones y duplicados:** los cuatro últimos de la lista (bloque "Tickets con duplicados y relaciones"): dos tickets que repiten el del wifi de la bodega (`duplicado_de="wifi-bodega"`, que queda como principal de los dos, sin cambios y sin eventos de relación propios) y dos relacionados con otros (`relacionar="..."`). `duplicado_de` cierra el ticket por `mark_duplicate`, así que no puede ir con `estado`; `relacionar` y `duplicado_de` son la clave de un ticket que aparezca **antes** en la lista y sea más antiguo (la relación no puede preceder a su creación), no se repiten, el principal no es a su vez un duplicado y un ticket cerrado solo admite reabrirlo. Las fechas de cada relación (`fecha_creacion` y, si se quita, `fecha_desactivacion`) se escriben al crear y se refrescan siguiendo a sus eventos `RELACION_AGREGADA` y `RELACION_ELIMINADA` (no al de cierre del duplicado, que comparte `relacion_id`), también los hechos a mano. El comando se detiene si faltan los tipos de relación y pide ejecutar `seed-catalogs`. Ver "Relaciones y duplicados".

---

# 23. Testing

Se utiliza:

```text
pytest
```

## Cómo se ejecutan y se aíslan los tests

Detalle y comandos en el `README.md` (sección «Tests»). Resumen de las decisiones, tomadas al medir que el 83 % del tiempo de la suite se iba en preparar y limpiar fixtures y solo el 17 % en los tests:

- **Un esquema por sesión, no por test** (`tests/database.py`, `tests/conftest.py`): el esquema se crea una vez y entre tests solo se vacían las tablas con filas (`empty_tables`, con `DELETE` y reinicio de las secuencias: `TRUNCATE` cuesta más que recrear el esquema en esta base). Se descartó envolver cada test en una transacción que se deshace porque la aplicación y los tests dependen de confirmaciones reales (`now()` cambia entre transacciones; los tests con hilos usan otras conexiones).
- **Instantáneas** (`take_snapshot` y `restore_snapshot`): los estados caros de construir (los 76 tickets de demostración, 2,6 s) se construyen una vez por proceso y cada test restaura una copia exacta de la base (y de los adjuntos que dejó la carga) en milisegundos.
- **Paralelo con `pytest-xdist`** (`-n 6`, un proceso por núcleo físico): cada proceso usa su propio esquema de PostgreSQL (`wd_test_gw0`...) dentro de `workdesk_test`, así que no hay bases nuevas y la protección sigue valiendo.
- **Áreas** (`tests/areas.py`): cada módulo de tests pertenece a un área y su marcador se asigna solo (`pytest -m sla`, `-m "tickets or notifications"`); `unit` marca a los que no usan la base. Un módulo sin área hace fallar la recolección, así que ninguno queda fuera. Los marcadores están declarados en `pytest.ini` (`--strict-markers`).
- **Hash de la contraseña de prueba:** se calcula una vez por proceso (hash real de Argon2id con los parámetros de producción).
- **Datos de demostración compartidos** (`tests/demo_data.py` y los fixtures `prepared` y `seeded` de `conftest.py`): los 76 tickets de `seed-demo-tickets` sirven de datos realistas para probar cualquier pantalla. `clock` (la hora de las pruebas de SLA) también vive en `conftest.py`.
- **Migraciones** (`tests/test_migrations.py`): como el esquema de la suite sale de los modelos (`db.create_all()`), ninguna otra prueba comprobaba las migraciones. Esta las sube, las compara con los modelos (`db check`), las baja y las vuelve a subir en un esquema desechable de `workdesk_test`, en un subproceso (el `env.py` de Alembic reconfigura el logging de todo el proceso).
- Mientras se desarrolla basta con el área que se toca; **antes de un commit o un Pull Request se ejecuta siempre la suite completa**.

## Estado actual de la suite

```text
3975 tests passing (4 min 51 s con `-n 6`)
```

Los tests cubren, por área: autenticación y sesiones; usuarios y autorización; catálogos; el núcleo de tickets y todo su ciclo de vida; SLA, calendario y planificador; notificaciones; seeds de demostración; y la plataforma (rutas, cabeceras, migraciones y coherencia con los documentos).

Hay cinco redes de seguridad que no dependen de recordar nada al añadir código: `tests/test_route_protection.py` (toda ruta exige sesión y toda ruta POST exige CSRF), `tests/test_route_authorization.py` (propiedad del ticket y rol en cada ruta), `tests/test_pages_smoke.py` (todas las pantallas con los 76 tickets de demostración y un presupuesto de consultas por petición), `tests/test_migrations.py` (las migraciones suben, coinciden con los modelos, bajan y una instalación limpia funciona) y `tests/test_docs_coherence.py` (variables de entorno, comandos, migraciones y rutas documentadas).

El relato por entrega —cuántos tests aportó cada una, qué cubre cada módulo y las pruebas de mutación que las defendieron— está en `docs/14_historial_de_implementacion.md`.

## Protección crítica de testing

`checked_database_url` (en `tests/database.py`) valida explícitamente que la base utilizada sea:

```text
workdesk_test
```

`tests/conftest.py` la llama antes de construir cualquier aplicación que pueda crear o vaciar tablas, y `tests/test_suite_infrastructure.py` comprueba que rechaza cualquier otra base (`workdesk_dev`, `postgres`, nombres parecidos, una URL con `workdesk_test` solo en el usuario o el servidor...).

Esto protege `workdesk_dev` frente a operaciones destructivas ejecutadas por pytest.

No debilitar esta protección.

---

# 24. Calidad

Comandos esperados después de cambios relevantes en backend:

```bash
ruff check src/workdesk tests
python -m pytest -q
```

Estado al cierre de `v0.1.0`:

```text
All checks passed!
20 passed
```

---

# 25. Comandos frecuentes

## Ejecutar aplicación

```bash
python -m flask --app src.workdesk run --debug
```

## Aplicar migraciones

```bash
python -m flask --app src.workdesk db upgrade
```

## Estado Alembic

```bash
python -m flask --app src.workdesk db current
python -m flask --app src.workdesk db heads
python -m flask --app src.workdesk db check
```

## Ver rutas

```bash
python -m flask --app src.workdesk routes
```

## Cargar roles

```bash
python -m flask --app src.workdesk seed-roles
```

## Cargar catálogos iniciales

```bash
python -m flask --app src.workdesk seed-catalogs
```

## Crear Administrador inicial

```bash
python -m flask --app src.workdesk create-admin
```

## Tests

```bash
# La suite completa, en paralelo (antes de un commit o un Pull Request)
python -m pytest -n 6

# Solo un área, o solo los tests que no usan la base de datos
python -m pytest -m sla
python -m pytest -m unit
```

## Ruff

```bash
ruff check src/workdesk tests
```

---

# 26. Git y flujo de trabajo

`main` representa el estado estable.

No desarrollar funcionalidades importantes directamente sobre `main`.

Flujo recomendado:

```text
main actualizada
→ crear feature branch
→ implementación incremental
→ tests
→ Ruff
→ revisar git diff
→ commits pequeños
→ push
→ Pull Request
→ revisión
→ merge
→ eliminar branch
→ actualizar main
```

## Convención de commits

Los commits se escriben en inglés.

Ejemplos:

```text
feat: add ...
fix: prevent ...
test: add ...
refactor: extract ...
docs: update ...
chore: configure ...
```

Evitar mensajes vagos:

```text
changes
update
fix
final
final2
```

---

# 27. Design System resumido

WorkDesk debe transmitir:

- profesionalismo;
- orden;
- control;
- simplicidad;
- tecnología;
- sobriedad.

## Paleta

```text
Azul principal:       #1D4ED8
Sidebar:              #111827
Fondo app:            #F1F5F9
Cards:                #FCFCFD
Texto principal:      #111827
Texto secundario:     #64748B
Bordes:               #DDE3EA
Verde:                #16A34A
Ámbar:                #F59E0B
Rojo:                 #EF4444
Morado:               #7C3AED
```

## Tipografía

```text
Inter / Roboto / fallback del sistema
```

## Principios visuales

- tema claro;
- sidebar oscuro;
- densidad intermedia;
- espaciado consistente;
- bordes de 1 px;
- radio aproximado de 8 px;
- sombras sutiles;
- foco visible;
- badges suaves;
- preparado para un tema oscuro posterior al MVP: los colores nuevos usan tokens `--wd-*`, nunca valores fijos (`docs/11`, sección 41.1);
- rojo reservado principalmente para acciones destructivas;
- tablas compactas;
- diseño responsive;
- accesibilidad.

Para detalle completo consultar:

```text
docs/11_diseno_de_pantallas.md
```

## Identidad visual oficial

WorkDesk dispone de una identidad visual propia y aprobada.

Principios:

- isotipo basado en una `W` modular de formas redondeadas;
- referencia sutil a ticket mediante un ojal circular;
- combinación principal azul/cian;
- wordmark con `Work` oscuro y `Desk` azul para tema claro;
- variantes inversas preparadas para superficies oscuras;
- el branding oficial no debe rediseñarse ni sustituirse arbitrariamente.

Directorio oficial:

```text
src/workdesk/static/img/brand/
```

Recursos principales:

```text
workdesk-mark.svg
workdesk-mark-inverse.svg
workdesk-logo.svg
workdesk-logo-inverse.svg
workdesk-login-brand.svg
workdesk-login-brand-inverse.svg
favicon.svg
favicon.ico
favicon-32x32.png
apple-touch-icon.png
icon-192x192.png
icon-512x512.png
icon-maskable-512x512.png
workdesk-social-preview.png
```

Uso actual:

- Login → `workdesk-login-brand.svg`;
- favicon global → integrado en Login, Dashboard y páginas de error;
- variantes inversas → reservadas para modo oscuro futuro;
- `workdesk-social-preview.png` → presentación visual del proyecto;
- iconos 192/512/maskable → preparados para uso futuro; no existe todavía manifest ni PWA.

---


# 28. Fuentes de verdad

## Visión

```text
docs/01_vision_del_proyecto.md
```

## Objetivos

```text
docs/02_objetivos.md
```

## Roles y permisos

```text
docs/03_roles_y_permisos.md
```

## Requisitos funcionales

```text
docs/04_requisitos_funcionales.md
```

## Requisitos no funcionales

```text
docs/05_requisitos_no_funcionales.md
```

## Reglas de negocio

```text
docs/06_reglas_de_negocio.md
```

## Casos de uso

```text
docs/07_casos_de_uso.md
```

## Flujo de tickets

```text
docs/08_flujo_de_tickets.md
```

## Modelo de datos

```text
docs/09_modelo_de_datos.md
```

## Arquitectura

```text
docs/10_arquitectura.md
```

## UI / UX / Design System

```text
docs/11_diseno_de_pantallas.md
```

## Roadmap

```text
docs/12_roadmap.md
```

## Evolución posterior al MVP

```text
docs/13_evolucion_post_mvp.md
```

---

# 29. Estado actual vs objetivo futuro

La documentación describe en muchos casos el **MVP completo**.

Eso NO significa que toda funcionalidad descrita esté implementada.

Para determinar el estado real del proyecto utilizar, en conjunto:

1. código actual;
2. tests;
3. migraciones;
4. `PROJECT_CONTEXT.md`;
5. `README.md`;
6. `docs/12_roadmap.md`.

Nunca presentar como implementada una funcionalidad futura únicamente porque aparezca en `docs/`.

---

# 30. Fases completadas y siguiente fase

`v0.1.0`, `v0.2.0 — Usuarios, autenticación completa y RBAC`, `v0.3.0 — Núcleo de tickets` y `v0.4.0 — Asignación, colaboración y ciclo de vida` y `v0.5.0 — SLA y notificaciones internas` están completas. Lo que dejó cada una está en «Historial de versiones» y con detalle en `docs/14_historial_de_implementacion.md`; la siguiente fase es `v0.6.0 — Dashboards y carga de trabajo` (ver "Próximo hito").

## Pendiente para la siguiente fase

Nada de `v0.2.0` a `v0.5.0`. Lo que falta pertenece a las fases posteriores (lo que `v0.5.0` deja preparado o pendiente está en "Próximo hito"):

- `v0.6.0`: dashboards y carga de trabajo;
- las opciones de navegación y del hub de administración se añaden cuando existan sus pantallas (`navigation.py` y `admin/hub.py`);
- las políticas de autorización adicionales se incorporan con cada módulo;
- `v0.7.0`: la configuración administrable (que reemplaza a las variables de entorno de plazos y límites y trae el interruptor general del SLA y la configuración de eventos y destinatarios de las notificaciones), la advertencia de duplicados al crear un ticket y la base de conocimiento;
- `v0.9.0`: preparación para el tema oscuro (los colores escritos a mano en `theme.css`, `layout.css`, `auth.css` y `errors.css` pasan a tokens `--wd-*`); desde ya, toda pantalla nueva usa tokens;
- después del MVP: modo oscuro, evaluación de actualizaciones en tiempo real (`docs/12`, sección 32) y las mejoras evaluadas en `docs/13_evolucion_post_mvp.md` (autoservicio y calidad, automatización operativa, flujos ITSM, activos y un módulo secundario de gestión de proyectos y tareas, solo para el personal); ninguna interfiere con el MVP.

El orden propuesto de entregas está en `docs/12_roadmap.md`.

Documentos especialmente relevantes:

```text
docs/03_roles_y_permisos.md
docs/04_requisitos_funcionales.md
docs/06_reglas_de_negocio.md
docs/07_casos_de_uso.md
docs/09_modelo_de_datos.md
docs/10_arquitectura.md
docs/11_diseno_de_pantallas.md
docs/12_roadmap.md
```

---

# 31. Principios de implementación

WorkDesk debe permanecer:

- comprensible;
- mantenible;
- seguro;
- testeable;
- documentado;
- proporcional al MVP.

No introducir tecnologías únicamente porque sean populares.

Evitar sin necesidad demostrable:

- microservicios;
- Redis;
- Kafka;
- RabbitMQ;
- Celery;
- Elasticsearch;
- React;
- Angular;
- Vue;
- SPA completa;
- infraestructura cloud prematura;
- abstracciones genéricas innecesarias.

---

# 32. Continuidad del proyecto

Al finalizar una versión importante:

1. actualizar este archivo;
2. actualizar `README.md`;
3. actualizar `docs/10_arquitectura.md` si cambió una decisión arquitectónica;
4. actualizar `docs/11_diseno_de_pantallas.md` si cambió UI, UX, Design System o branding;
5. actualizar `docs/12_roadmap.md` cuando corresponda;
6. ejecutar Ruff;
7. ejecutar pytest;
8. revisar Git;
9. crear Pull Request;
10. mergear;
11. volver a `main` limpia.

Las conversaciones con asistentes NO deben ser la única fuente de decisiones importantes.

Toda decisión relevante debe terminar reflejada en:

- código;
- tests;
- migraciones;
- documentación;
- o este archivo.

---

# 33. Principio rector

> WorkDesk debe evolucionar mediante cambios pequeños, comprensibles, testeables y coherentes con su documentación, evitando tanto la improvisación como la sobrearquitectura.