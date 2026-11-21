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
v0.4.0 — Asignación, colaboración y ciclo de vida
```

La versión `v0.4.0` está:

- implementada;
- testeada (2201 tests);
- documentada;
- mergeada en `main` (PR #23 a #35).

Las versiones `v0.1.0 — Fundación técnica`, `v0.2.0 — Usuarios, autenticación completa y RBAC`, `v0.3.0 — Núcleo de tickets` y `v0.4.0` están etiquetadas.

## Rama estable

```text
main
```

`main` debe representar siempre el estado estable del proyecto.

## Rama de trabajo actual

```text
feature/work-calendar
```

Entrega 2 de `v0.5.0 — SLA y notificaciones internas` (ver "Próximo hito"): el calendario laboral administrable. El motor de tiempo laboral admite franjas distintas por día (ver "Tiempo laboral"); tres tablas nuevas guardan las versiones del calendario, sus franjas y sus feriados; `resolve_work_calendar` decide cuál es el vigente (el guardado o el de por defecto); el Administrador lo configura desde «SLA» y «Configurar calendario»; y `seed-demo-tickets` lee el calendario resuelto (ver "Calendario laboral administrable"). Incluye una migración.

Ya integradas en `main`: la sincronización documental (PR #4), la base RBAC (PR #5), los límites de sesión (PR #6), la auditoría administrativa (PR #7), la base de seguridad de contraseñas (PR #8), el cambio de contraseña propio y obligatorio (PR #9), el listado y creación de usuarios (PR #10), la administración de usuarios existentes (PR #11), la base de la interfaz administrativa (PR #12), "Mi cuenta" y los datos demo (PR #13, cierre de `v0.2.0`), los catálogos de tickets (PR #14), el modelo de tickets (PR #15), la administración de catálogos (PR #16), la creación de tickets (PR #17), el listado de tickets (PR #18), la edición de tickets (PR #19), el cierre de `v0.3.0` (PR #20), el seed `seed-demo-tickets` (PR #21), el plan del módulo de proyectos posterior al MVP (PR #22) y las 12 entregas de `v0.4.0` (PR #23 a #35): visibilidad y vocabulario del historial (PR #23), catálogo de motivos de espera (PR #24), estados y transiciones (PR #25), grupos (PR #26), asignación (PR #27) y solicitantes del ticket (PR #28), un arreglo del refresco de fechas del seed con escalamientos hechos a mano (PR #29), comentarios y notas internas (PR #30), adjuntos (PR #31), resolución y cierre (PR #32), relaciones y duplicados (PR #33), el bloqueo temporal de edición (PR #34) y la pantalla de Estados y transiciones con el cierre de la versión (PR #35), y la entrega 1 de `v0.5.0`, el motor de tiempo laboral compartido (PR #36).

`v0.5.0` se divide en 9 entregas, cada una con su rama, tests y Pull Request (decididas al empezar la fase):

| # | Entrega | Estado |
| --- | --- | --- |
| 1 | Motor de tiempo laboral compartido (`worktime.py`) | Integrada (PR #36) |
| 2 | Calendario laboral administrable: tablas, calendario vigente y pantalla del Administrador | En curso |
| 3 | Políticas de SLA por prioridad (`politicas_sla`) y su pantalla | Pendiente |
| 4 | Períodos de SLA: cálculo, pausa en `En espera` y continuidad ante cambios de prioridad | Pendiente |
| 5 | Notificaciones internas: infraestructura y centro de notificaciones | Pendiente |
| 6 | Notificaciones internas: generación por eventos (incluye RF-068 y RN-96) | Pendiente |
| 7 | Indicadores de SLA en el listado y el detalle | Pendiente |
| 8 | Planificador: avisos de SLA y cierre automático | Pendiente |
| 9 | Cierre de la versión: revisión de toda la fase y documentación | Pendiente |

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

## Hito completado: v0.3.0

```text
v0.3.0 — Núcleo de tickets
```

Es la fase central del MVP: creación, listado, búsqueda, filtros, detalle y edición de tickets, con sus catálogos. Se dividió en entregas pequeñas, cada una con su rama, tests y Pull Request, como se hizo con `v0.2.0`. Reutiliza la infraestructura de `v0.2.0` (autorización por roles, auditoría, layout con Bootstrap, navegación por rol, formularios y patrones de servicio y listado).

| # | Entrega | Estado |
| --- | --- | --- |
| 1 | Catálogos: estados, prioridades, categorías, ubicaciones y motivos de cierre (modelos, migración y `seed-catalogs`) | Integrada (PR #14) |
| 2 | Modelo de tickets (tickets, solicitantes e historial) y servicio de creación | Integrada (PR #15) |
| 3 | Administración de catálogos desde la interfaz | Integrada (PR #16) |
| 4 | Creación de tickets | Integrada (PR #17) |
| 5 | Listado con búsqueda, filtros, orden y paginación | Integrada (PR #18) |
| 6 | Detalle y edición autorizada | Integrada (PR #19) |
| 7 | Cierre de la versión: red de seguridad de rutas, guía de primera configuración y documentación | Integrada (PR #20) |

Decisiones de la fase:

- **Sin datos de ejemplo en los seeds.** Categorías, ubicaciones y tickets de ejemplo se crean a mano desde la interfaz; ningún seed los incluye, para que una instalación real no arranque con datos ficticios. El README documenta cómo hacerlo.
- **Visibilidad del Solicitante:** ve los tickets que creó o donde es solicitante vigente. Técnico, Supervisor y Administrador ven todos. Un ticket al que no se tiene acceso responde 404, igual que uno inexistente.
- **Edición:** Técnico, Supervisor y Administrador editan título, descripción, categoría y ubicación y cambian la prioridad con motivo obligatorio; el Solicitante solo lee. El Solicitante ve en el historial qué cambió, pero no el motivo.
- **Concurrencia:** en esta fase solo existe el control de versión (`tickets.version`). El bloqueo temporal de edición (RN-115 a RN-117: aviso de quién edita, expiración y renovación) se difirió a `v0.4.0`, donde se implementó.
- **Estados y transiciones** (UI-021) se difirieron a `v0.4.0`, cuando existió el flujo de estados y la tabla de transiciones; están implementados.

Cierre de la versión (entrega 7), sin migraciones ni cambios de funcionalidad:

- `tests/test_route_protection.py` recorre el mapa de rutas real y comprueba que todas redirigen al login sin sesión, salvo las públicas (`auth.login`, `system.health` y `static`, listadas en `PUBLIC_ENDPOINTS`), y que toda ruta POST responde 400 sin token CSRF. Una ruta nueva queda cubierta automáticamente: si el test falla al añadirla, no se arregla el test; o se protege la ruta o, si de verdad es pública, se añade de forma consciente a `PUBLIC_ENDPOINTS`.
- El README incorpora la guía de primera configuración paso a paso (requisitos, PostgreSQL, `.env` y preparación inicial), un recorrido de prueba por rol con un fragmento opcional que genera 25 tickets de ejemplo desde `flask shell`, y una tabla de solución de problemas.

## Hito completado: v0.4.0

```text
v0.4.0 — Asignación, colaboración y ciclo de vida
```

Es la fase en que el ticket pasa a trabajarse en equipo: grupos, asignación, estados, comentarios y notas internas, adjuntos, resolución, cierre y reapertura, relaciones, bloqueo de edición y la administración de los estados. Se dividió en 12 entregas, cada una con su rama, tests, Pull Request y ampliación del seed de demostración:

| # | Entrega | Estado |
| --- | --- | --- |
| 1 | Historial: vocabulario en la aplicación y visibilidad por evento | Integrada (PR #23) |
| 2 | Catálogo de motivos de espera y su administración | Integrada (PR #24) |
| 3 | Estados y transiciones (`transiciones_estados`) y cambios de estado operativos | Integrada (PR #25) |
| 4 | Grupos (`/groups`), con membresías y supervisores responsables | Integrada (PR #26) |
| 5 | Asignación de técnicos, grupo del ticket y escalamiento manual | Integrada (PR #27) |
| 6 | Agregar y retirar solicitantes tras crear el ticket | Integrada (PR #28) |
| 7 | Comentarios públicos y notas internas | Integrada (PR #30) |
| 8 | Adjuntos | Integrada (PR #31) |
| 9 | Resolución, validación del solicitante, cierre y reapertura | Integrada (PR #32) |
| 10 | Relaciones y duplicados | Integrada (PR #33) |
| 11 | Bloqueo temporal de edición | Integrada (PR #34) |
| 12 | Pantalla de Estados y transiciones (UI-021) y cierre de la versión | Integrada (PR #35) |

Sus reglas están en `docs/06` (RN-146 y RN-156 a RN-164) y su alcance en `docs/12_roadmap.md` (fase 4, con las decisiones de la fase).

Decisiones de la fase:

- **El vocabulario de eventos del historial vive solo en la aplicación** (se eliminó el CHECK de `tipo_evento`). Un evento nuevo obliga a decidir su nombre, su visibilidad y su descriptor, y un test lo exige. Hoy son 23.
- **Quién ve qué se decide en la consulta**, nunca en la plantilla: lo mismo para el historial, los comentarios y los adjuntos. Cada condición SQL tiene su política Python equivalente y un test comprueba que coinciden para todos los roles.
- **Una acción, una pantalla** (sin modales, y funcionan sin JavaScript): 404 si no se ve el ticket y 403 si se ve y no se puede actuar.
- **`change_state` es el único camino que escribe el estado** y los datos de resolución y cierre, así que «cerrado ⇒ fecha y motivo de cierre» no puede romperse; marcar un duplicado y la asignación lo reutilizan.
- **Lo aditivo no sube la versión del ticket:** comentarios, notas, adjuntos, relaciones y cambios de solicitantes.
- **Los parámetros que serán configuración** (plazos de edición y de reapertura, límites de adjuntos y tiempos del bloqueo) son variables de entorno hasta `v0.7.0`.

## Próximo hito

```text
v0.5.0 — SLA y notificaciones internas
```

Su alcance está en `docs/12_roadmap.md` (fase 5): SLA por prioridad calculado en tiempo laboral, con un calendario laboral administrable; pausa en `En espera`; avisos de próximo a vencer y vencido; y notificaciones internas. `v0.4.0` dejó preparado o decidido para esta fase:

- el cierre automático de un ticket `Resuelto` que nadie valida: la transición `AUTO_CIERRE`, el motivo de cierre `INACTIVIDAD` y la columna `tickets.cerrado_automaticamente` ya existen, pero nada los usa. Hasta entonces, un ticket resuelto sin solicitante solo lo cierra un Supervisor o el Administrador con el cierre excepcional;
- las notificaciones a los técnicos cuando el Solicitante comenta (RF-068) y el aviso de reapertura (RN-72 y RN-96);
- el motor de tiempo laboral del seed de demostración (`_BusinessClock`) pasó a un módulo propio, `src/workdesk/worktime.py`, para compartirlo con el SLA (entrega 1, ver "Tiempo laboral"); `DEMO_CALENDAR` es el calendario por defecto mientras no haya uno guardado, y el calendario administrable (entrega 2, ver "Calendario laboral administrable") ya existe: `resolve_work_calendar` decide cuál es el vigente;
- por el motor de estados pasa todo cambio de estado (`change_state` y `apply_derived_transition`): ahí tendrá que reaccionar el SLA al entrar y salir de `En espera`;
- la política de continuidad del SLA ante un cambio de prioridad (RN-88): `change_priority` todavía no la aplica.

Decisiones tomadas al planificar la fase (el detalle está en `docs/12_roadmap.md`):

- **El planificador será un comando propio** (`run-scheduler`), sin APScheduler ni otra dependencia nueva: las tareas son idempotentes y pueden ejecutarse también una sola vez desde el Programador de tareas de Windows o `cron`.
- **«Primera respuesta»** es el primer comentario público del personal y es un objetivo opcional de la política de SLA.
- **Las excepciones de SLA (RF-083) quedan fuera** de la fase.
- **La pausa del SLA no usa columnas nuevas:** al entrar en `En espera` se cierra el período y, al reanudar, se abre otro que arrastra el consumo acumulado.
- **El plazo del cierre automático** es una variable de entorno (24 horas por defecto) hasta que llegue la configuración administrable de `v0.7.0`.

Asignada a `v0.7.0`: la advertencia de posibles duplicados al crear un ticket (RF-061), junto a la base de conocimiento, con la que comparte la búsqueda.

Pendiente, sin fase asignada, para decidirlo al planificar:

- los adjuntos desde el formulario de creación del ticket;
- las columnas de impacto y urgencia de `tickets`, cuando existan sus catálogos;
- la liberación manual de un bloqueo de edición por el Supervisor o el Administrador;
- las pestañas del detalle (Actividad, Archivos, Historial y Relaciones; hoy son tarjetas apiladas), el color y el orden de los estados y los modales (`v0.9.0`);
- los parámetros que hoy son variables de entorno, en la configuración administrable (`v0.7.0`).

## Hito completado: v0.2.0

Durante `v0.1.0` se adelantó intencionalmente parte de la base técnica de autenticación para consolidar desde el comienzo:

- sesiones;
- seguridad;
- protección de rutas;
- bloqueo de intentos;
- invalidación de sesiones;
- testing automatizado.

La fase `v0.2.0` completó:

- gestión de usuarios (listado, creación, detalle, edición, cambio de rol, desactivación y reactivación, y restablecimiento de contraseña) — implementada;
- autorización basada en roles;
- políticas de acceso;
- navegación según rol;
- restricciones administrativas;
- cuenta propia ("Mi cuenta") — implementada;
- datos demo (comando `seed-demo`) — implementados;
- pruebas específicas de autorización;
- límites de sesión (30 minutos de inactividad y 8 horas máximo, por variables de entorno) — implementado;
- contraseñas: creación de cuentas y restablecimiento por el Administrador con contraseña temporal, cambio propio y cambio obligatorio en el primer inicio de sesión (`usuarios.debe_cambiar_password`) — implementados la política, el generador, la columna, las operaciones de dominio, la pantalla de cambio propio y la guardia de cambio obligatorio; el Administrador crea usuarios con contraseña temporal y restablece contraseñas desde la interfaz;
- tabla `auditoria_administrativa` mínima para las acciones sobre usuarios — implementada (modelo, migración y servicio), y todas las acciones sobre usuarios ya registran su evento.

`docs/12_roadmap.md` documenta las cinco entregas incrementales de `v0.2.0`, cada una con su rama y Pull Request.

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
│       ├── groups/
│       ├── main/
│       ├── models/
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
│       │   ├── sla/
│       │   ├── tickets/
│       │   └── users/
│       ├── __init__.py
│       ├── cleaning.py
│       ├── cli.py
│       ├── config.py
│       ├── errors.py
│       ├── extensions.py
│       ├── formatting.py
│       ├── logging_config.py
│       ├── navigation.py
│       ├── search.py
│       └── worktime.py
├── tests/
│   ├── conftest.py
│   ├── test_account_password.py
│   ├── test_account_profile.py
│   ├── test_app.py
│   ├── test_audit.py
│   ├── test_auth.py
│   ├── test_authorization.py
│   ├── test_catalogs.py
│   ├── test_catalogs_routes.py
│   ├── test_catalogs_service.py
│   ├── test_cli.py
│   ├── test_credentials.py
│   ├── test_formatting.py
│   ├── test_groups.py
│   ├── test_layout.py
│   ├── test_password_policy.py
│   ├── test_passwords.py
│   ├── test_route_authorization.py
│   ├── test_route_protection.py
│   ├── test_seed_demo.py
│   ├── test_seed_demo_tickets.py
│   ├── test_session_limits.py
│   ├── test_state_actions.py
│   ├── test_states_admin.py
│   ├── test_system.py
│   ├── test_ticket_assignment.py
│   ├── test_ticket_attachments.py
│   ├── test_ticket_comments.py
│   ├── test_ticket_edit_lock.py
│   ├── test_ticket_history.py
│   ├── test_ticket_history_visibility.py
│   ├── test_ticket_model.py
│   ├── test_ticket_policies.py
│   ├── test_ticket_relations.py
│   ├── test_ticket_requesters.py
│   ├── test_ticket_resolution.py
│   ├── test_ticket_state_transitions.py
│   ├── test_tickets_edit_routes.py
│   ├── test_tickets_edit_service.py
│   ├── test_tickets_list_routes.py
│   ├── test_tickets_list_service.py
│   ├── test_tickets_routes.py
│   ├── test_tickets_service.py
│   ├── test_users_manage_routes.py
│   ├── test_users_manage_service.py
│   ├── test_users_routes.py
│   ├── test_users_service.py
│   ├── test_wait_reasons.py
│   ├── test_work_calendar.py
│   ├── test_work_calendar_routes.py
│   ├── test_worktime.py
│   └── ticket_helpers.py
├── .github/
│   └── copilot-instructions.md
├── .env.example
├── .gitattributes
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── PROJECT_CONTEXT.md
├── README.md
├── requirements.txt
└── requirements-dev.txt
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

Existen actualmente dieciocho migraciones:

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

Se invoca desde todas las acciones sobre usuarios: creación (`USUARIO_CREADO`), edición de datos (`USUARIO_MODIFICADO`, con los valores anteriores y nuevos de los campos cambiados), cambio de rol (`CAMBIO_ROL`), desactivación y reactivación (`USUARIO_DESACTIVADO`, `USUARIO_ACTIVADO`) y contraseñas (`PASSWORD_CAMBIADA`, `PASSWORD_RESTABLECIDA`). Desde `v0.3.0` también la administración de catálogos (`CATALOGO_CREADO`, `CATALOGO_MODIFICADO`, `CATALOGO_ACTIVADO` y `CATALOGO_DESACTIVADO`, con el tipo en `entidad_tipo`) y, desde `v0.5.0`, el guardado del calendario laboral (`CALENDARIO_LABORAL_GUARDADO`). Las acciones críticas admiten un motivo opcional.

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

**Datos iniciales.** `seed-catalogs` (`seeds/catalogs.py`) carga los seis estados, las cuatro prioridades, la categoría `Sin clasificar`, los seis motivos de cierre y los cinco motivos de espera, y los dos tipos de relación entre tickets (`DUPLICADO` y `RELACIONADO`, ver "Relaciones y duplicados"). Es idempotente: cada registro se identifica por su `codigo` y, si existe, no se toca, de modo que respeta lo que un Administrador haya renombrado o desactivado. Confirma una sola vez al final. **No carga ubicaciones ni otras categorías**: dependen de cada organización y se crean desde la interfaz.

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

Registro cronológico **append-only**: el ORM rechaza actualizar o eliminar eventos (`TicketHistoryImmutableError`), igual que la auditoría administrativa. El actor es un usuario o el sistema (`actor_usuario_id` NULL, sin usuario ficticio) y hay una restricción de coherencia entre ambos. El vocabulario de eventos (`TicketEvent`) contiene hoy `TICKET_CREADO`, `TICKET_MODIFICADO`, `CATEGORIA_CAMBIADA`, `PRIORIDAD_CAMBIADA`, `ESTADO_CAMBIADO`, `TECNICO_ASIGNADO`, `TECNICO_DESASIGNADO`, `GRUPO_CAMBIADO`, `TICKET_ESCALADO`, `SOLICITANTE_AGREGADO`, `SOLICITANTE_RETIRADO`, `COMENTARIO_AGREGADO`, `COMENTARIO_EDITADO`, `COMENTARIO_ELIMINADO`, `ARCHIVO_ADJUNTADO`, `ARCHIVO_ELIMINADO`, `TICKET_RESUELTO`, `VALIDACION_ACEPTADA`, `VALIDACION_RECHAZADA`, `TICKET_CERRADO`, `TICKET_REABIERTO`, `RELACION_AGREGADA` y `RELACION_ELIMINADA`. Los datos variables van en `valor_anterior`, `valor_nuevo` y `contexto` (JSONB); el motivo de un cambio de prioridad va en `contexto`. La columna opcional `motivo_espera_id` (FK a `motivos_espera`, `ON DELETE RESTRICT`) guarda el motivo del catálogo cuando el evento es la entrada a `En espera`; `record_ticket_event(..., wait_reason=)` la rellena. Lo rellena `change_state` al poner un ticket en espera.

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

Módulo `src/workdesk/tickets/` (blueprint `tickets`, prefijo `/tickets`): `routes/` (un módulo por área; ver "Revisión final de la fase"), `forms.py` y `service.py`. Reglas completas en `docs/06` (RN-153).

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

**Rutas.** `edit_ticket` y `change_ticket_priority` adquieren el bloqueo al empezar (`_hold_edit_lock`, que confirma en ese momento): si es de otra persona, responden con la pantalla de solo lectura `edit_locked.html` (200; un POST añade «No se guardó nada: otra persona está editando este ticket.» y no guarda); al guardar con éxito liberan el bloqueo en la misma transacción. Un error de validación o un conflicto de versión no lo liberan. Dos rutas JSON, solo POST y con CSRF (cabecera `X-CSRFToken` o campo `csrf_token`): `POST /tickets/<n>/lock/renew` (200 `{"ok": true}`; 409 con el mensaje «X está editando este ticket.», o si el ticket está cerrado) y `POST /tickets/<n>/lock/release` (`{"ok": true, "released": bool}`). Ambas: 404 si no se ve el ticket, 403 si no puede editarlo (el Solicitante).

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

**Seed:** `seed-catalogs` carga las 20 transiciones de la matriz de `docs/08` (sección 34) más `DESASIGNACION` (Asignado → Nuevo al quitar al último técnico, que `docs/08` no lista) y `AUTO_CIERRE` (cargada pero sin uso hasta el cierre automático de `v0.5.0`). Es idempotente por (origen, destino, acción) y **no pisa una transición que el Administrador haya deshabilitado**. El comando informa `transiciones: N`. Quien tenga una base anterior debe volver a ejecutar `seed-catalogs`.

**Acciones implementadas hoy** (`STATE_ACTIONS`): iniciar el trabajo (`INICIAR`, Nuevo o Asignado → En progreso), poner en espera (`PONER_EN_ESPERA`, En progreso → En espera) y reactivar (`REACTIVAR`, En espera → En progreso). Resolver, cerrar, confirmar, rechazar y reabrir se añadieron en la entrega 9 (ver "Resolución, validación, cierre y reapertura"). Las demás acciones de la tabla (`ASIGNAR` y `DESASIGNACION`, derivadas de la asignación, y `AUTO_CIERRE`, del planificador de `v0.5.0`) no están en `STATE_ACTIONS`: `change_state` las rechaza con `StateTransitionError`. Cada acción es un `StateActionInfo` (ruta, texto, icono, mensaje y política de rol).

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

## Revisión final de la fase (entrega 12 de `v0.4.0`)

La entrega 12 cerró la versión con una revisión de todo el código de la fase. Los cambios de estructura no alteraron ninguna ruta ni comportamiento previo (los tests existentes lo siguen verificando), salvo los dos textos que se indican más abajo. Lo que cambió y por qué:

- **`tickets/state_actions.py` (nuevo):** el catálogo de acciones de estado (textos, roles, esenciales) salió de `tickets/lifecycle.py`, que ahora es solo el motor (`change_state`, `available_actions` y `apply_derived_transition`). La pantalla de administración lee el mismo catálogo, así que lo que muestra no puede separarse de lo que el código hace.
- **`tickets/routes/` (paquete):** `tickets/routes.py` había llegado a casi 1850 líneas. Ahora hay un módulo por área (`listing`, `creation`, `detail`, `editing`, `states`, `assignment`, `requesters`, `comments`, `attachments` y `relations`) más `common.py` con lo que comparten. Todos registran sus rutas en el mismo blueprint, así que los endpoints y las URL no cambiaron (se comprobó comparando el mapa de rutas antes y después). `render_detail` se dividió en piezas pequeñas.
- **`tickets/history.py` (nuevo):** `describe_history_changes` era una cadena de condiciones que crecía con cada evento. Ahora cada evento tiene una función registrada con `@describes(...)`, y `tests/test_ticket_history.py` exige que todo evento del vocabulario tenga la suya y que ninguna línea repita un motivo.
- **Ayudantes unificados:** `cleaning.py` (`blank_to_none` y `strip_text`) sustituye a las copias de los servicios y formularios de catálogos, grupos, usuarios y tickets; `current_actor()` y `admin_only` viven en `security/` en lugar de repetirse en cada módulo de rutas; en los tests, `ticket_by_public_id` y `person` pasaron de ocho y tres archivos a `tests/ticket_helpers.py`.
- **Textos sin nombres de estado escritos a mano:** como el Administrador puede renombrar los estados, el resumen del detalle usa «Fecha de resolución» y «Fecha de cierre», y las pantallas de cambio de estado y de duplicado usan el nombre vigente del estado de destino.
- **Red de seguridad de autorización:** `tests/test_route_authorization.py` recorre el mapa de rutas, como `test_route_protection.py`, y comprueba la propiedad del ticket (404 al ajeno), el rol (403 en las rutas del personal y en las áreas de administración) y que lo que un Solicitante sí puede usar está declarado a propósito (`REQUESTER_ENDPOINTS`). Una ruta nueva queda cubierta sin tocar el test.

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

Paquete `src/workdesk/sla/` (blueprint `sla`, prefijo `/admin/sla`), entrega 2 de `v0.5.0`. Es el módulo `sla` previsto en `docs/10` (sección 22), donde se sumarán las políticas y los períodos. Reglas completas en `docs/09` (21 y 40.8), `docs/11` (UI-022) y `docs/12` (fase 5). **Incluye una migración** (`create_work_calendar_tables`).

**Modelos** (`models/calendario_laboral.py`): `CalendarioLaboral` (`calendarios_laborales`: `version`, `zona_horaria`, `activo`, `fecha_creacion` y `usuario_creacion_id`), `HorarioLaboral` (`horarios_laborales`: una fila por franja, con `dia_semana` ISO de 1 a 7) y `Feriado` (`feriados`: fecha y nombre). Restricciones: versión positiva y única, **como máximo una versión vigente** (índice único parcial sobre `activo`), franjas con inicio anterior al fin y sin repetir el inicio dentro de una versión, un feriado por fecha y versión, nombre de feriado no vacío y claves foráneas con `ON DELETE RESTRICT`. Que las franjas de un día no se solapen lo comprueba el servicio (no hay restricción de exclusión: necesitaría la extensión `btree_gist`).

**Una versión nunca se modifica.** Guardar crea la siguiente y deja la anterior como histórica, así que lo que ya se calculó con una versión (los períodos de SLA, desde la entrega 4) no cambia retroactivamente. Por eso `docs/09` perdió las columnas de modificación y de vigencia por fila que el diseño inicial preveía (`nombre`, `fecha_modificacion`, `activo` de franjas y feriados...): ninguna hace falta.

**Servicio** (`sla/work_calendar.py`, sin commit):

- `resolve_work_calendar()` es la **única función que decide cuál es el calendario vigente**: el guardado o, si todavía no hay ninguno, el de por defecto (`DEMO_CALENDAR` en la zona de `APP_TIMEZONE`). Devuelve un `ResolvedCalendar` con el reloj listo, el nombre de la zona y la versión de la que sale (`record`, `None` si es el de por defecto). `clock_for(versión)` construye el reloj de una versión concreta (es lo que usará el SLA).
- `save_work_calendar(actor=, base_version=, zone_name=, franjas=, holidays=, reason=)` guarda una versión nueva y la deja vigente. `base_version` es la versión con la que se abrió la pantalla (0 si no había ninguna): si otra persona guardó mientras tanto lanza `CalendarConflictError` y no se guarda nada. Bloquea la fila vigente (`SELECT ... FOR UPDATE`), libera el lugar de «vigente» antes de insertar y, si todavía no había ninguna versión y dos personas guardan la primera a la vez, gana el índice único y la otra recibe el mismo conflicto (savepoint, como los catálogos). Guardar un contenido idéntico al vigente lanza `NothingToChangeError` y no crea una versión; la zona (se comprueba contra `available_zone_names`, no basta con que `ZoneInfo` la acepte), los feriados repetidos o sin nombre, el motivo y las franjas se validan y lanzan `CalendarRuleError`. Registra `CALENDARIO_LABORAL_GUARDADO` (`entidad_tipo` `calendario_laboral`, `detalle` «Versión N») con la versión anterior y la nueva y **solo las secciones que cambiaron** (`zona_horaria`, `horario` y `feriados`); la primera versión se compara con el calendario por defecto.
- Para las pantallas: `describe_calendar` (un `CalendarView` con el horario resumido por días seguidos que comparten horas: «Lunes a jueves · 09:00–18:00», «Viernes · 09:00–17:00»), `list_calendar_versions` (tres consultas, sin una por versión) y `describe_schedule` y `summarize`.

**Formulario** (`sla/forms.py`, `WorkCalendarForm`, que hereda el motivo opcional de `ReasonForm`): **el horario de cada día es un texto** (`09:00-18:00`, o `09:00-13:00, 14:00-18:00` si hay una pausa; vacío = no se trabaja) y **los feriados son otro, uno por línea** (`25-12-2026 Navidad`; también se acepta año-mes-día, con barras y con el día sin cero). Así se admiten varias franjas por día sin filas dinámicas ni JavaScript. `parse_day` y `parse_holidays` convierten los textos (una franja que termina antes de empezar, dos solapadas, una hora que no existe, una fecha imposible, un año fuera de 2000-2100, un nombre ausente o una fecha repetida se señalan con el campo o la línea), y `format_day` y `format_holidays` hacen el camino inverso para rellenar el formulario. Todos los errores se informan a la vez y el formulario conserva lo escrito. Un calendario sin ningún día laboral se rechaza.

**Pantallas** (todas del Administrador, 403 al resto):

- `GET /admin/sla` («SLA», UI-022): hoy solo el calendario laboral. Muestra el estado («Configurado · versión N» o «Por defecto (sin configurar)»), el horario resumido, la zona, el número de feriados con los **próximos cinco**, quién y cuándo lo guardó, y la tabla de versiones (la vigente y las anteriores).
- `GET, POST /admin/sla/calendar` («Configurar calendario»): el formulario. Lleva la versión base en un campo oculto y **se rellena con lo vigente solo al abrirlo** (en un envío manda lo que llegó, para que una petición sin versión no se complete sola y se salte la comprobación). Ante un conflicto de versión se vuelve al formulario con lo vigente y un aviso (lo escrito se pierde a propósito); sin cambios, se avisa y no se crea nada. La lista de zonas horarias válidas ayuda a escribirla (`<datalist>`).
- La tarjeta «SLA» del hub enlaza con `/admin/sla` y «Administración» se marca activa en estas pantallas.

**Seed de demostración.** `seed_demo_tickets` lee el calendario resuelto: con uno guardado planifica todas sus fechas dentro de sus franjas, en su zona horaria y sin que ninguna caiga en un feriado; con un `calendar=` explícito (los tests) manda ese. La hora de creación de cada ticket pasa por `into_business`, así que si cae en una pausa pasa al siguiente momento de trabajo (con el calendario por defecto no se mueve). Con un calendario guardado `validate_demo_tickets` no compara la hora de cada ticket con una jornada única (`calendar=None`): solo comprueba que está bien escrita. Con el calendario por defecto (y con cualquier otro de una sola jornada en la que caigan las horas de los tickets) las fechas que genera el seed son exactamente las de antes: el cambio de `_planned_times` solo afecta a combinaciones que la validación del seed rechaza.

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
GET        /health
GET        /static/<path:filename>
```

`/dashboard`, `/account`, `/account/password` y todas las rutas `/tickets...` requieren autenticación. En los tickets la autorización va más allá del login (ver "Creación y detalle de tickets" y "Edición de tickets"): el detalle y las pantallas de edición responden 404 a quien no puede ver el ticket, y las de edición, prioridad y solicitantes responden 403 a quien lo ve pero no puede usarlas (el Solicitante). En los comentarios, una nota interna que el usuario no puede ver responde 404 y editar o eliminar uno ajeno (o propio fuera de plazo), 403.

`/account` es "Mi cuenta" (ver "Mi cuenta"). `/account/password` permite al usuario cambiar su propia contraseña (ver "Cambio de contraseña propio y cambio obligatorio").

`/admin`, todas las rutas `/admin/...` (categorías, prioridades, ubicaciones y motivos de espera, ver "Administración de catálogos", estados y transiciones, ver "Administración de estados y transiciones", y SLA, ver "Calendario laboral administrable") y todas las rutas `/users` requieren el rol Administrador. Las rutas `/groups...` requieren Administrador o Supervisor (403 al resto) y, dentro, cada acción se vuelve a comprobar (ver "Grupos") (403 para otros roles autenticados y redirección al login para anónimos). `/admin` es el hub de administración (ver "Layout y navegación"). No existe ruta de alta de prioridades (`/admin/priorities/new`): son exactamente cuatro.

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
- No se muestran controles que todavía no funcionan (por ejemplo, las notificaciones). El buscador de tickets de la topbar sí funciona (ver "Listado de tickets").

## Navegación por rol

Se define en `src/workdesk/navigation.py` (`MAIN_NAVIGATION` y `ACCOUNT_NAVIGATION`) y se filtra **en backend** por rol antes de llegar a la plantilla: las opciones no autorizadas no se envían al navegador (`docs/11`, sección 5.5). Un `context_processor` (`layout_context`) entrega a la plantilla los enlaces del usuario con la opción activa marcada. Es solo presentación: cada ruta protegida sigue comprobando la autorización por sí misma.

- Hoy incluye solo las pantallas que existen: Dashboard (todos), Tickets (personal) o Mis tickets (Solicitante), Crear ticket (todos), Grupos (Supervisor), Administración (Administrador) y Mi cuenta (todos). "Tickets" y "Mis tickets" llevan al mismo listado y se marcan activas también en el detalle y en las pantallas de editar, cambiar prioridad, cambiar estado, asignación, escalamiento, solicitantes, y editar o eliminar un comentario o un archivo (`TICKET_SCREENS`); "Crear ticket" solo se marca activa en el formulario (`tickets.new_ticket`).
- Administración se marca activa en el hub, en todas las pantallas de usuarios, de catálogos, de grupos y de SLA; Grupos (del Supervisor), en las de grupos; Mi cuenta, en `/account` y en el cambio de contraseña.
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
```

`seed-catalogs` (`src/workdesk/seeds/catalogs.py`): carga los estados, las transiciones entre estados, las prioridades, la categoría `Sin clasificar`, los motivos de cierre, los motivos de espera y los tipos de relación entre tickets. Es idempotente y no pisa lo que un Administrador haya cambiado. No carga ubicaciones ni categorías de ejemplo (ver "Catálogos de tickets").

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

`seed-demo-tickets` (`src/workdesk/seeds/demo_tickets.py` y `demo_tickets_data.py`):

- carga 76 tickets de demostración, escritos como los escribiría gente real y poco técnica (títulos vagos, prisa, el problema equivocado, prioridades exageradas), a nombre del equipo de `seed-demo`: cerca de un 70 % los crean Solicitantes (que quedan como su propio solicitante, como en la pantalla de creación) y el resto el personal, con 0, 1 o 2 solicitantes;
- **datos separados de la lógica:** `demo_tickets_data.py` solo contiene la lista (`DEMO_TICKETS`, de `DemoTicket` y `DemoAdjustment`); `demo_tickets.py` tiene el motor. Cada ticket tiene una `clave` estable (nombre corto, único, que no debe cambiar una vez cargado). Para mejorar la demostración se edita la lista. Cada paso de ajuste admite campos opcionales con valor por defecto (hoy `estado`, `motivo_espera`, `texto`, `grupo`, `asignar`, `agregar_solicitante`, `retirar_solicitante`, `motivo_retiro`, `comentario`, `nota_interna` y `adjunto`) y, cuando existan cierres y comentarios, se añaden más sin invalidar los tickets ya escritos;
- necesita `seed-catalogs` y `seed-demo`; si faltan, se detiene con un mensaje que dice qué ejecutar, y lo mismo si hay transiciones deshabilitadas que la demostración recorre («Habilítalas en Administración → Estados y transiciones»), sin cargar nada. **No crea categorías ni ubicaciones**: busca por nombre exacto `Redes`, `Hardware`, `Correo`, `Impresoras` y las ubicaciones `Suc Lo Marcoleta` y `Suc Manuel Antonio Matta` (sin distinguir mayúsculas); si falta alguna, usa `Sin clasificar` o deja el ticket sin ubicación y lo informa con un `Aviso:`. Las prioridades se resuelven por código, para sobrevivir a un renombrado;
- usa los servicios reales (`create_ticket`, `update_ticket`, `change_priority`, `set_group`, `assign_technician`, `add_requester`, `remove_requester`, `add_comment`, `add_attachments` y `change_state`), así que valida, versiona y registra el historial igual que la aplicación. Los `ajustes` son pasos posteriores del personal (reclasificar, cambiar la prioridad con motivo, corregir el título, **cambiar el estado**) con su propio actor y retraso. Un ajuste con `estado` (`INICIAR`, `PONER_EN_ESPERA` o `REACTIVAR`) se ejecuta al final del paso; `motivo_espera` es el código de un motivo del catálogo y `texto` una explicación libre (solo con un motivo que la admita, como `OTRO`);
- **identidad y marca, sin migración:** al crear un ticket, el motor marca en `historial_ticket.contexto` todos los eventos que genera con `{"demo_clave": <clave>, "demo_paso": <n>}` (0 = creación, 1... = cada ajuste), junto al `motivo` si lo hay. Es la única huella del seed: permite reconocer el ticket aunque después cambie de título (en la lista o a mano) y distinguir los eventos del seed de los hechos a mano. La aplicación solo lee `contexto["motivo"]`, así que la marca no se ve en la interfaz;
- **no duplica y refresca al volver a ejecutarlo:** un ticket cuya clave ya existe no se vuelve a crear, se *refresca*: se reescriben sus fechas relativas al nuevo día de ejecución (`fecha_creacion`, `fecha_modificacion`, `fecha_hora` de los eventos del seed según su paso y `fecha_asociacion` de los solicitantes). Ejecutarlo el mismo día deja exactamente las mismas fechas, y un refresco da lo mismo que una carga nueva ese día (hay un test que lo comprueba). Las ediciones hechas a mano sobre un ticket demo (eventos sin marca) se desplazan lo mismo que el último evento del seed para seguir después de él y se recortan a «hace un minuto» si quedaran en el futuro; la fecha de modificación acompaña al evento que la originó. **No toca el contenido** (título, descripción, categoría, prioridad, versión) ni crea eventos, y nunca toca tickets creados a mano. Para cambiar el contenido de tickets ya cargados hay que recrear la base de desarrollo;
- **fechas relativas en tiempo laboral:** todo corre según un calendario laboral configurable (`WorkCalendar` / `DEMO_CALENDAR` en `worktime.py`: `dias`, `inicio`, `fin` y `feriados`; por defecto lunes a viernes de 09:00 a 18:00, sin feriados). `hace_dias` son *días laborales* antes del último día laboral (si se ejecuta un fin de semana, se cuenta desde el viernes); `hora` (en `APP_TIMEZONE`) debe caer dentro de la jornada, con el fin excluido; y `despues_horas` de cada ajuste son *horas laborales* desde el paso anterior, de modo que el reloj salta noches, fines de semana y feriados. Nada cae fuera del calendario ni en el futuro (se recorta al último momento laboral ya pasado). Desde la entrega 2 de `v0.5.0` el seed lee el calendario vigente (`resolve_work_calendar`): el que guarde el Administrador desde «SLA» o, si no hay ninguno, `DEMO_CALENDAR`, que es el calendario por defecto de todo el sistema. Con uno guardado, todas las fechas caen dentro de sus franjas y en su zona horaria, y la hora de creación de cada ticket pasa al siguiente momento de trabajo si cae en una pausa; `hora` debe caer dentro de la jornada solo cuando se usa el calendario por defecto (ver "Calendario laboral administrable"). El motor de tiempo laboral (antes `_BusinessClock`) es un módulo propio, `worktime.py`, que usará también el SLA (ver "Tiempo laboral"). Como los servicios sellan la hora actual, las fechas se escriben con un `UPDATE` de Core solo en las filas que el propio seed creó (`tickets`, `tickets_solicitantes` e `historial_ticket`). Es el único lugar del proyecto que lo hace: el guard del ORM sigue rechazando cualquier modificación normal del historial y los servicios no recibieron parámetros de fecha;
- valida sus datos antes de tocar la base (`validate_demo_tickets`: calendario coherente, horas dentro de la jornada, claves y títulos únicos, usuarios y roles, categorías y prioridades conocidas, motivo obligatorio al cambiar la prioridad, y que la secuencia de acciones de estado de cada ticket sea ejecutable desde Nuevo con la matriz de transiciones y con motivos y textos coherentes...);
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

Estado al cerrar `v0.1.0`:

```text
20 tests passing
```

Los tests actuales cubren principalmente:

- creación de la aplicación;
- configuración de testing;
- rutas;
- redirecciones;
- login válido;
- contraseña inválida;
- usuario inactivo;
- logout;
- bloqueo por intentos fallidos;
- invalidación mediante `token_version`;
- Argon2id;
- health check;
- error 400;
- error 404;
- configuración obligatoria;
- degradación de `/health` cuando PostgreSQL falla.

Estado tras la entrega 2 de `v0.5.0` (calendario laboral administrable):

```text
2508 tests passing
```

Los 207 tests nuevos cubren:

- `tests/test_worktime.py` (+67, 167 en total; unitarios, sin base de datos): **el motor con franjas por día**. `schedule_problems` y `from_schedule` (franjas sin ninguna, de un día que no existe, que terminan antes de empezar o solapadas; contiguas válidas; el orden en que llegan no importa), que una franja por día se comporta igual que un `WorkCalendar`, `is_working_time`, y cada operación con una pausa de almuerzo (pasar al horario laboral, el último minuto, avanzar horas, medir y sumar, con los bordes en el inicio y el fin de cada franja). Además, dos horarios (uno con almuerzo y otro deliberadamente incómodo, con un martes de un solo minuto, un día sin trabajo, una franja que empieza a medianoche y feriados) se comparan con el recuento minuto a minuto y cumplen que medir y sumar son operaciones inversas, que nada cae fuera de las franjas y que las mediciones suman igual sin importar cómo se divida el intervalo.
- `tests/test_work_calendar.py` (96): **el calendario por defecto** (qué se usa sin nada guardado y que sigue la zona de la aplicación); **guardar** (la versión 1, que cada guardado crea una versión nueva y deja la anterior exactamente como estaba, que una versión antigua sigue construyendo su reloj, los días ISO en la base, que guardar tal cual el calendario por defecto es válido, feriados ordenados y recortados, que el servicio no hace commit); **sin cambios, conflicto y reglas** (guardar lo mismo no crea nada, el orden de franjas y feriados no es un cambio y cualquier diferencia sí, una versión base obsoleta o del futuro es un conflicto, once datos inválidos que no dejan nada pendiente, los límites exactos, un usuario inactivo); **auditoría** (la primera versión se compara con el calendario por defecto y las siguientes solo registran las secciones que cambiaron); **descripciones** (días seguidos que comparten horas, el resumen, el historial de versiones en tres consultas); **restricciones de la base de datos** (una sola versión vigente, versión única y positiva, día de la semana de 1 a 7, inicio anterior al fin, sin repetir franja ni feriado, nombre de feriado no vacío, una versión con filas no se elimina); **los textos del formulario** (franjas de un día y feriados, con sus formas válidas y cada error con su línea) y **dos carreras con hilos** (dos Administradores que guardan la primera versión a la vez, y dos que guardan sobre la misma versión: en ambos casos queda una sola versión nueva y el otro recibe el conflicto).
- `tests/test_work_calendar_routes.py` (37): **acceso** (anónimo al login, los tres roles sin permiso reciben 403 en GET y POST sin guardar nada, el hub enlaza la pantalla y «Administración» sigue marcada); **«SLA»** (el calendario por defecto, uno guardado con su horario, su zona y sus feriados, solo los cinco próximos, el historial de versiones, el HTML de un nombre de feriado escapado); **el formulario** (abierto con lo por defecto y con lo guardado, abrirlo no guarda nada, la lista de zonas, guardar la primera versión y las siguientes, la auditoría con quién y por qué, sin cambios no se crea nada, una pantalla desactualizada vuelve con lo vigente y no guarda, una petición sin versión se rechaza en lugar de completarse sola, doce errores distintos señalados junto a su campo, que conserva lo escrito, que rechaza un calendario sin días laborales y que informa todos los errores a la vez).
- `tests/test_seed_demo_tickets.py` (+7): el seed respeta un calendario guardado (franjas, feriados y días sin trabajo), usa su zona horaria y cuenta «hoy» en ella (con una hora de referencia en la que Santiago y Bogotá no coinciden en la fecha), un calendario explícito sigue ganando, una hora de creación que cae en una pausa pasa al siguiente momento de trabajo, refrescar con un calendario guardado mantiene todo en horario laboral y la validación no compara la hora de cada ticket con una jornada única cuando no la hay.
- Ajustes por diseño, sin cambiar lo que comprueban: `tests/test_layout.py` (la tarjeta «SLA» del hub ya está enlazada) y `tests/test_worktime.py` (los atributos `start` y `end` del reloj desaparecieron: un test usa ahora `is_working_time` y el recuento minuto a minuto entiende franjas). `tests/test_route_protection.py` y `tests/test_route_authorization.py` cubren las dos rutas nuevas sin cambios (sesión obligatoria, CSRF y solo Administrador).

Estado tras la entrega 1 de `v0.5.0` (motor de tiempo laboral compartido):

```text
2301 tests passing
```

Los 100 tests nuevos están en `tests/test_worktime.py`, son unitarios y no usan la base de datos. Cubren:

- **el calendario:** el calendario por defecto, el formato HH:MM, cada problema que detecta `calendar_problems` y que `BusinessClock` se niega a construirse con un calendario inválido;
- **los días:** los días laborales, los feriados, otro día de la semana como laboral y `workdays_before` (fines de semana, contando desde un domingo y con feriados);
- **pasar al horario laboral** (`into_business` y `latest_before`): dentro de la jornada, justo al abrir y al cerrar, antes de abrir, por la noche y en fin de semana;
- **avanzar horas** (`add_hours`): terminar justo al cierre pasa a la apertura siguiente, empezar fuera de la jornada, fines de semana, feriados, la fracción de segundo y que el resultado nunca cae fuera del horario;
- **medir** (`business_seconds_between`): las noches, los fines de semana y los feriados no suman, la fracción de segundo se descarta, tres años enteros de días laborales, una comparación con un recuento minuto a minuto (con dos calendarios) que no comparte ninguna idea con el motor, y que las mediciones suman lo mismo sin importar cómo se divida el intervalo;
- **sumar** (`add_business_seconds`): un plazo que se cumple justo al cierre vence a la hora de cierre (a diferencia de `add_hours`), con 0 segundos no se mueve, no admite cantidades negativas, sumar en dos pasos equivale a sumar de una vez y medir y sumar son operaciones inversas (el resultado es además el primer instante en que se cumple);
- **zonas horarias:** las fechas en UTC se convierten a la zona del calendario, el resultado queda en esa zona, las fechas sin zona se rechazan y un fin de semana con cambio de horario de verano no mueve la jornada.

`tests/test_seed_demo_tickets.py` cambia una sola línea (importa `WorkCalendar` desde `worktime`) y ninguna comprobación se tocó: el seed sigue produciendo las mismas fechas.

Estado tras la entrega 12 de `v0.4.0` (estados y transiciones, y cierre de la versión):

```text
2201 tests passing
```

Los 160 tests nuevos cubren:

- `tests/test_states_admin.py` (69): **estados** (los seis en el orden del flujo, cuántos tickets hay en cada uno, renombrar cambia solo lo visible y audita solo los campos que cambiaron, guardar sin cambios no audita, una descripción en blanco queda vacía, el nombre no puede repetirse sin distinguir mayúsculas pero un estado conserva el suyo con otra capitalización, los límites exactos, que el servicio no hace commit y **dos Administradores que renombran al mismo nombre a la vez dejan uno solo**); **transiciones** (agrupadas por origen en el orden del flujo, cuáles son esenciales y cuáles opcionales, quién ejecuta cada acción, deshabilitar y volver a habilitar, la razón de cada protección, que la única entrada a un estado y la última salida no se pueden deshabilitar, que llegar a un estado solo volviendo atrás no cuenta, que un flujo ya roto no bloquea cambios ajenos, **dos Administradores que a la vez rompen el flujo entre los dos**, **dos que cambian la misma transición a la vez y solo uno la cambia y la audita**, que una transición deshabilitada deja de ofrecerse a los tickets y el servidor la rechaza, y que listarlas no consulta por fila); y **pantallas** (solo el Administrador, 404 con ids desconocidos, el hub enlaza la pantalla, el formulario precargado y sus validaciones, que no acepta un código ni un orden, que un estado renombrado se ve en todas partes menos en el historial antiguo, que la descripción es la ayuda de la etiqueta, las confirmaciones con los nombres vigentes, las protegidas no se pueden deshabilitar ni por la pantalla y que «Administración» sigue marcada en el menú).
- `tests/test_state_actions.py` (15): el catálogo de acciones es coherente: cada acción está descrita exactamente una vez, tiene un nombre neutro y un identificador de URL único, las esenciales y las que devuelven atrás pertenecen al vocabulario, los textos no escriben a mano ningún nombre de estado, una descripción se completa con el nombre del destino y **los roles declarados de cada acción coinciden con su política de autorización** (los cuatro roles).
- `tests/test_route_authorization.py` (13): recorre el mapa de rutas real. Un Solicitante ajeno recibe 404 en cualquier ruta de un ticket, con cualquier método; un solicitante del ticket solo usa las rutas declaradas en `REQUESTER_ENDPOINTS` (el resto responde 403) y esas sí responden; las áreas de administración son del Administrador, y `/groups` del Administrador y el Supervisor. Tres pruebas comprueban que el propio recorrido detecta una ruta sin comprobar la propiedad, una del personal abierta a Solicitantes y una de administración sin comprobar el rol.
- `tests/test_ticket_history.py` (61): todo evento del vocabulario tiene su descriptor, un evento desconocido no dice nada, qué cuenta cada uno de los 23 y que ninguna línea repite un motivo ni el texto de un comentario.
- `tests/test_seed_demo_tickets.py` (+2): el comando se detiene antes de cargar nada si hay transiciones deshabilitadas que la demostración necesita, y renombrar los estados no la afecta. `tests/test_layout.py` actualiza la prueba del hub (la tarjeta «Estados y transiciones» ya está enlazada).
- Ajustes sin cambiar lo que comprueban: `tests/test_ticket_state_transitions.py` y `tests/test_ticket_resolution.py` importan el catálogo desde `tickets/state_actions.py`; `tests/test_tickets_routes.py` apunta al módulo `routes.creation`; y ocho archivos de tests usan `ticket_by_public_id` (y tres, `person`) de `tests/ticket_helpers.py` en lugar de sus copias.

Estado tras la entrega 11 de `v0.4.0` (bloqueo temporal de edición):

```text
2041 tests passing
```

Los 59 tests nuevos (`tests/test_ticket_edit_lock.py`) cubren: **configuración** (120 s y 45 s por defecto; la aplicación no arranca con tiempos cero o negativos ni con un latido igual o mayor que la duración); **base de datos** (un solo bloqueo no liberado por ticket, los liberados no cuentan, y los `CHECK` de tiempos); **adquirir** (crea el bloqueo por el tiempo configurado, renovar es adquirir otra vez, otra persona no puede tomar uno vigente, uno expirado se libera de forma lógica y se reemplaza, el propio expirado que nadie tomó se renueva, un bloqueo por ticket, usuario inactivo, el servicio no hace commit); **liberar** (libera para otra persona, nunca toca el de otra, sin bloqueo no es error); **consultar** (solo cuenta el vigente y no modifica nada); **concurrencia con hilos** (dos personas que abren a la vez obtienen un único bloqueo, y dos que toman uno expirado también); y **pantallas** (abrir bloquea y trae lo que necesita el script, otra persona ve quién edita en una pantalla de solo lectura, guardar mientras otra edita no cambia nada, guardar libera, guardar tras expirar sin que nadie lo tome funciona y tras tomarlo otra persona se rechaza, un conflicto de versión o un error de validación no liberan, editar y cambiar la prioridad comparten el bloqueo, los demás cambios no se bloquean, un ticket cerrado y un Solicitante no bloquean, 404 sin acceso; los endpoints de renovar y liberar —JSON, 409 si es de otra persona o está cerrado, 403 al Solicitante, solo POST, nunca liberan el de otra persona—; el aviso del detalle solo para el personal que podría editar y que desaparece al expirar; y el script, servido y sin dependencias externas). `tests/test_route_protection.py` cubre las dos rutas nuevas sin cambios (sesión obligatoria y CSRF).

Estado tras la entrega 10 de `v0.4.0` (relaciones y duplicados):

```text
1982 tests passing
```

Los 116 tests nuevos cubren:

- `tests/test_ticket_relations.py` (95): **catálogo y políticas** (los dos tipos, simétrica o no; los eventos son internos y tienen nombre; solo el personal gestiona relaciones y un usuario inactivo no); **base de datos** (rechaza un ticket relacionado consigo mismo, un par repetido **también invertido**, y una desactivación incoherente; tipos distintos pueden unir el mismo par y una relación quitada admite una nueva); **número de ticket** (`12`, `#12`, espacios y ceros; todo lo demás se rechaza); **relacionar** (par normalizado desde cualquier lado, un evento interno solo en el ticket que actúa, no sube la versión ni «Actualizado», se lista desde los dos tickets, no consigo mismo ni dos veces ni a la inversa, ticket inexistente, comentario con límite exacto, un ticket cerrado no actúa pero puede ser el otro lado, actor inactivo, el servicio no hace commit); **quitar** (eliminación lógica con quién y cuándo, se puede volver a establecer, desde cualquiera de los dos tickets, ids ajenos o ya quitados, ticket cerrado, **dos personas que la quitan a la vez la quitan una sola vez**); **marcar un duplicado** (cierra con `DUPLICADO` con fecha, motivo y quién, el principal queda intacto, el historial deja la relación y luego el cierre, desde los cuatro estados abiertos, no desde Resuelto ni Cerrado, el principal puede estar en cualquier estado, no consigo mismo ni ticket inexistente, **sin cadenas ni ciclos** en ningún sentido, no se marca dos veces, un principal con varios duplicados, no transfiere nada, versión caducada, nada queda a medias si falla, **dos duplicados opuestos a la vez no se bloquean y solo uno prospera**, la relación de un duplicado cerrado no se quita y la de uno reabierto sí); **historial** (el Solicitante nunca recibe los eventos, líneas legibles); y **pantallas** (el Solicitante recibe 403 en todas y 404 si no ve el ticket, la tarjeta y la pantalla solo para el personal, relacionar con sus avisos, confirmación para quitar, la pantalla de duplicado, conservar lo escrito ante un error, conflicto de versión, qué ve el Solicitante de un duplicado cerrado —que se cerró como duplicado, pero no de cuál ni la nota—, ticket cerrado, ticket Resuelto, menú «Tickets» y que cargar las relaciones es **una sola consulta**).
- `tests/test_seed_demo_tickets.py` (+21): validación de los pasos nuevos (claves anteriores y más antiguas, no repetir, duplicado solo y sin `estado`, un ticket cerrado solo admite reabrirlo, no cadenas, solo el personal), que los datos cubran duplicados, un principal con dos duplicados y una relación, el historial igual al de la aplicación, el principal intacto, las fechas de cada relación con las de su evento (y el cierre del duplicado con el suyo), lo que ve cada rol, el refresco y una eliminación hecha a mano, y que el comando pida `seed-catalogs` si faltan los tipos. Las instantáneas incluyen ahora las relaciones.
- `tests/test_catalogs.py`: el diccionario de `seed_catalogs` incluye `tipos_relacion`.

Estado tras la entrega 9 de `v0.4.0` (resolución, cierre y reapertura):

```text
1866 tests passing
```

Los 136 tests nuevos cubren:

- `tests/test_ticket_resolution.py` (107): **constantes y configuración** (los códigos de estado de las políticas coinciden con el catálogo, `REOPEN_WINDOW_DAYS` vale 30 y la aplicación no arranca con 0 o negativo, los cinco eventos son públicos y tienen nombre); **políticas** (resolver y cerrar por rol, solo Supervisor y Administrador cierran de forma excepcional, solo un solicitante vigente valida —no otro Solicitante, ni el creador que no figura como solicitante, ni uno retirado, ni el personal—, la reapertura del personal sin límite y la del solicitante solo con el ticket Cerrado y dentro del plazo, con el límite exacto y la configuración); **base de datos** (`validaciones` rechaza un tipo inválido, un ciclo 0, un rechazo sin motivo y un duplicado en el mismo ciclo, pero admite el ciclo siguiente); **resolver** (desde los cuatro estados abiertos, evento público con el ciclo, texto opcional con límite de 2000 exacto, no se resuelve dos veces, conserva a los técnicos, conflicto de versión); **cierre directo** (desde los cuatro estados, evento propio con la acción y el motivo, cancelación, motivos de otros caminos rechazados, motivos inactivos o desconocidos, no desde Resuelto, el motivo solo en el cierre directo); **confirmar** (cierra con `RESOLUCION_VALIDADA`, registra la validación y los dos eventos en orden, basta uno de varios solicitantes, solo un solicitante vigente, funciona aunque el motivo esté desactivado, **dos solicitantes a la vez cierran una sola vez**); **rechazar** (exige explicar, limpia la resolución, deja la validación y los dos eventos, conserva a los técnicos, cada resolución abre un ciclo nuevo y la primera explicación sobrevive); **cierre excepcional** (Supervisor, motivo obligatorio, solo desde Resuelto, un Técnico no, y el ticket sin solicitante); **reabrir** (limpia el cierre y conserva el historial y los técnicos, el personal sin límite, el solicitante solo dentro del plazo, un ticket abierto no se reabre, un ticket cerrado rechaza todo lo demás, se puede resolver y cerrar de nuevo); la **regla del cierre en los tres caminos** (cerrado siempre con fecha y motivo, abierto nunca con datos de cierre); el **historial** (el Solicitante recibe los cinco eventos, líneas legibles); y las **pantallas** (botones del Técnico, resolver con su tarjeta y su fecha, límite del texto, los dos motivos del cierre directo, cancelación, aviso de validación solo para un solicitante vigente, confirmar, rechazar con su explicación, qué ve cada rol del motivo del rechazo y de las notas de cierre, 403 y 404 en cada pantalla, cierre excepcional, reapertura por el personal y por el solicitante dentro y fuera del plazo, conflicto de versión).
- `tests/test_seed_demo_tickets.py` (+31): validación de los pasos nuevos (quién ejecuta cada acción, textos obligatorios y límites, motivos de cierre, transiciones inexistentes, un ticket cerrado solo admite reabrirlo), que los datos cubran los seis caminos, el historial de cada ticket nuevo, las fechas de resolución, cierre y validación con las de sus eventos, lo que ve cada rol, y el refresco de esas fechas (también un cierre y una reapertura hechos a mano). Las instantáneas incluyen ahora la resolución, el cierre y las validaciones.
- `tests/test_ticket_state_transitions.py` (-2, ajustes por diseño): las acciones disponibles por estado incluyen resolver y cerrar y un ticket Resuelto o Cerrado ofrece reabrir; ahora están implementadas todas las acciones salvo las derivadas y la del sistema; el detalle de un ticket Resuelto o Cerrado ofrece solo reabrir. Se cambiaron esas comprobaciones porque describían el alcance anterior, no para que pasen.

Estado tras la entrega 8 de `v0.4.0` (adjuntos):

```text
1730 tests passing
```

Los 95 tests nuevos cubren:

- `tests/test_ticket_attachments.py` (83): **almacenamiento** (nombres depurados que nunca son una ruta, lista blanca de extensiones, contenido que debe coincidir con la extensión, MIME declarado ignorado, nombre físico UUID y SHA-256 por bloques, límite de tamaño exacto sin dejar restos, archivo vacío, rutas que no pueden salir de la raíz); **modelo y configuración** (límites mayores que cero, valores por defecto y almacenamiento fuera de `static/`, eventos internos por defecto, restricciones de la base de datos); **servicio** (metadatos y evento público o interno según el comentario, partes vacías del formulario, máximo por envío y por ticket contando solo los activos, un archivo malo no deja restos, ticket cerrado, actor inactivo, compensación con `discard_files`, eliminación lógica que conserva el archivo); **visibilidad** (el Solicitante nunca recibe el adjunto de una nota, un comentario eliminado oculta los suyos, **la condición SQL coincide con la política `can_view_attachment`** para todos los perfiles, y los eventos de archivos de una nota no llegan al Solicitante); y **pantallas** (subir y descargar con `attachment`, `nosniff` y sin caché, avisos, tamaño excedido, 413, 404 sin acceso o entre tickets, archivo físico ausente o ruta manipulada, comentario con archivos y comentario con un archivo malo que conserva el texto, ticket cerrado, nombres escapados y eliminar con su plazo).
- `tests/test_seed_demo_tickets.py` (+11): validación del `adjunto`, que cuelgue del comentario correcto y exista en disco con su hash, la descarga del Solicitante, las fechas de cada archivo con las de su evento y tras un refresco, que volver a ejecutar no duplique archivos y que una eliminación hecha a mano siga al refresco. Las instantáneas incluyen los adjuntos.
- `tests/test_layout.py` (+1 caso). `tests/conftest.py`: la fixture `app` usa un directorio temporal para `UPLOADS_DIR`, sin tocar la protección de `workdesk_test`.

Estado tras la entrega 7 de `v0.4.0` (comentarios y notas internas):

```text
1635 tests passing
```

Los 130 tests nuevos cubren:

- `tests/test_ticket_comments.py` (86): **vocabulario y configuración** (los tres eventos son internos por defecto y tienen nombre; la aplicación no arranca con un plazo de edición menor o igual a cero; el plazo por defecto es 30 minutos); **base de datos** (rechaza un tipo desconocido, un contenido vacío, un comentario activo con datos de eliminación, uno eliminado sin fecha y uno editado sin fecha de modificación); **servicio** (comentario público con su evento público y nota interna con su evento interno, sin subir la versión ni tocar «Actualizado», contenido recortado y con los saltos de línea unificados, vacío y de más de 5000 caracteres, tipo desconocido, ticket cerrado, actor inactivo, que no hace commit; editar con el contenido anterior en el historial, sin cambios, el tipo que no cambia, ids inexistentes, de otro ticket o eliminados; eliminar de forma lógica, que ya no se lista a nadie y que no se puede eliminar dos veces); **consultas y visibilidad** (orden, el Solicitante nunca recibe las notas, `get_comment` oculta notas y comentarios de otros tickets, **la condición SQL coincide con la política `can_view_comment`** para los seis perfiles más un usuario inactivo y uno anónimo, y una sola consulta por lista); **historial** (el Solicitante solo recibe los eventos del comentario público, las líneas indican el tipo y nunca el texto); **concurrencia con hilos** (dos ediciones se aplican una tras otra y dos eliminaciones, una sola); y **pantallas** (publicar como Solicitante y como personal, avisos por tipo, tipo por defecto, **un Solicitante no puede escribir una nota interna ni enviándola a mano (403)**, 404 sin acceso o para tickets inexistentes, errores del formulario con lo escrito conservado, HTML escapado y saltos de línea conservados, ticket cerrado sin formulario, que el Solicitante no recibe la nota en ninguna forma —ni texto, ni marcas, ni historial, ni conteo, ni sus pantallas—, que el personal la ve marcada, que el historial no filtra el texto anterior, el selector de tipo según el rol, editar y eliminar con sus plazos, la configuración del plazo, quién puede abrir la edición de comentarios ajenos y los enlaces según los permisos).
- `tests/test_ticket_policies.py` (+25): `can_write_internal_note`, `can_comment_publicly`, `can_view_comment`, `can_edit_comment` (plazo, límite exacto, configuración, autor y terceros, Supervisor y Administrador sin plazo, nota interna del Solicitante) y `can_delete_comment`, que sigue la misma regla; y que `INTERNAL_COMMENT_TYPE` coincida con el modelo.
- `tests/test_seed_demo_tickets.py` (+17): validación de los pasos de comentarios (quién puede comentar, límites, texto), que los datos cubran los casos, el historial de una conversación igual que el de la aplicación, que los comentarios no modifiquen el ticket, la fecha de cada comentario con la de su evento, lo que ven el Solicitante y el personal, el refresco de esas fechas y que una edición y una eliminación hechas a mano sigan al refresco en orden. Las instantáneas de fechas y de contenido incluyen ahora los comentarios.
- `tests/test_layout.py` (+2 casos): las pantallas de editar y eliminar un comentario marcan «Tickets». `tests/test_route_protection.py` cubre las tres rutas nuevas sin cambios.

Estado tras la entrega 6 de `v0.4.0` (solicitantes del ticket):

```text
1505 tests passing
```

Los 73 tests nuevos cubren:

- `tests/test_ticket_requesters.py` (45): **vocabulario** (los dos eventos son internos y tienen nombre); **servicio** (agregar con su evento interno y sin subir la versión ni tocar «Actualizado», el personal de cada rol, solo usuarios activos con rol Solicitante, duplicados, ticket cerrado, actor inactivo, que no hace commit, que agregar y retirar en una misma transacción respeta el `CHECK` de fechas, que quien abrió la edición antes del cambio guarda sin conflicto y los candidatos; retirar conserva la participación con quién y cuándo, con y sin motivo, dejar un ticket sin solicitantes, volver a agregar con una fila nueva, ids inexistentes, de otro ticket o ya retirados, motivo de 500 y 501 caracteres); **concurrencia con hilos** (dos altas de la misma persona producen una sola participación vigente y dos retiros, uno solo); **quién ve el ticket** (quien se agrega lo ve —con su historial público completo— y quien se retira deja de verlo en el detalle y en el listado, el creador lo conserva, **la condición SQL coincide con la política `can_view_ticket` tras agregar, retirar y volver a agregar** para los seis perfiles, y la búsqueda del personal por solicitante sigue a los cambios); **historial** (el Solicitante no recibe los eventos ni los nombres de otros solicitantes ni el motivo, tampoco en la consulta; el personal los ve con su motivo; líneas de `describe_history_changes` sin el motivo); y **pantallas** (403 al Solicitante en las cuatro rutas, 404 para tickets ajenos o inexistentes, la pantalla por rol, mensajes cuando no hay solicitantes o nadie que agregar, agregar y sus validaciones, confirmación antes de retirar, aviso del creador, motivo largo, ticket cerrado, solicitante inactivo marcado y aun así retirable, enlace «Gestionar» solo para el personal y con el ticket abierto).
- `tests/test_seed_demo_tickets.py` (+20; uno de ellos es la regresión de un escalamiento hecho a mano cuyo refresco violaba el `CHECK` de fechas de `tickets_tecnicos`, un fallo de la entrega 5): validación de los pasos de solicitantes (roles, quién es solicitante en cada momento, retirar y agregar a la misma persona, motivo del retiro), que los datos cubran los cuatro casos, el historial de cada ticket nuevo igual que el de la aplicación (retirar antes de agregar, marca del seed, sin versión ni fecha de modificación), las fechas de asociación y retiro con las de sus eventos, el creador que sigue viendo su ticket, el solicitante retirado que lo pierde, los eventos solo para el personal, el refresco de esas fechas y que los cambios hechos a mano sigan al refresco en orden. Ajustes por diseño de tests existentes: las instantáneas de fechas y de contenido incluyen el retiro; «los tickets siguen las reglas de creación» y «un solicitante demo solo ve sus tickets» calculan los solicitantes con los cambios de cada ticket; y la comprobación de la fecha de modificación pasó de «existe si hay ajustes» a la regla de la aplicación (`version > 1` si y solo si hay fecha de modificación, que es la de uno de sus eventos).
- `tests/test_ticket_policies.py` (+6): `can_manage_requesters` por rol, usuarios inactivos y anónimos, y que siga la misma regla que `can_choose_requesters`. `tests/test_layout.py` (+2 casos): las dos pantallas marcan «Tickets».
- `tests/test_route_protection.py` cubre las tres rutas nuevas sin cambios (sesión obligatoria y CSRF).

Estado tras la entrega 5 de `v0.4.0` (asignación):

```text
1432 tests passing
```

Los 92 tests nuevos cubren:

- `tests/test_ticket_assignment.py` (68): **servicio** (asignar mueve un ticket `Nuevo` a `Asignado` con su evento derivado, más técnicos y otros estados no cambian el estado ni la versión, transición deshabilitada, autoasignación, solo Técnicos activos, duplicados, ticket cerrado, usuario inactivo, que no hace commit, candidatos; quitar conserva la asignación, el último técnico devuelve a `Nuevo`, ids ajenos o ya quitados, motivo largo; grupo: fijar, quitar, mismo grupo, grupos inactivos y desconocidos, el actual desactivado se conserva, versión caduca y ticket cerrado; escalar: grupo, técnico que reemplaza, ambos, necesidad de un cambio real y de motivo, grupos y técnicos inválidos, versión y ticket cerrado) y **concurrencia con hilos** (dos autoasignaciones del mismo técnico producen una sola, y dos técnicos a la vez pasan el ticket a `Asignado` una sola vez); **visibilidad** (el Solicitante ve «Atendido por» y el técnico asignado pero ni el grupo ni el escalamiento ni su motivo; el personal lo ve todo; sin asignar; técnico inactivo); y **pantallas** (autoasignarse y dejar el ticket, solo Técnicos, un Técnico solo se quita a sí mismo, 403 a Técnicos y Solicitantes en las pantallas de gestión, 404 para tickets ajenos en todas las rutas, asignar y quitar como Supervisor y Administrador, validaciones, grupo con conflicto de versión, ticket cerrado, botones por rol, opción «Tickets» marcada y la pantalla y el formulario de escalamiento).
- `tests/test_seed_demo_tickets.py` (+16): validación de `grupo` y `asignar` (grupo desconocido, quién fija el grupo, técnico inválido, quién asigna a otra persona), la simulación del estado derivado, que los datos cubran grupo sin técnico, dos técnicos, autoasignación y asignación por un Supervisor, el historial igual al de la aplicación, que cada asignación lleve la fecha de su evento, lo que ven el Solicitante y el personal, un grupo que falta solo avisa, el refresco de fechas de las asignaciones (incluida una desasignación hecha a mano) y que refrescar no toca grupo ni técnicos. `final_state` tiene en cuenta que asignar pasa el ticket a `Asignado`, ya alcanzable en los datos, y `prepare` carga los grupos de `seed-demo`.
- `tests/test_ticket_policies.py` (+6): `can_assign_self` y `can_manage_assignments` por rol, usuarios inactivos y anónimos. `tests/test_layout.py` (+2 casos): asignación y escalamiento marcan «Tickets».

Estado tras la entrega 4 de `v0.4.0` (grupos):

```text
1340 tests passing
```

Los 116 tests nuevos cubren:

- `tests/test_groups.py` (109): **base de datos** (nombre único sin distinguir mayúsculas, miembro y responsable únicos mientras estén vigentes pero con posibilidad de volver, y que un cierre no preceda al inicio); **políticas** por rol, para anónimos e inactivos, el supervisor responsable (vigente, retirado, otro supervisor, otro grupo) y **la condición SQL equivalente a la política** para los cinco perfiles; **servicio** (alta con auditoría, nombre obligatorio y repetido, carrera de nombre con savepoint, edición de solo lo cambiado, sin cambios sin auditar, desactivar y reactivar conservando miembros y responsables, agregar y retirar técnicos con su historial, solo técnicos y supervisores activos, duplicados y carreras, grupos desactivados, candidatos, listados por rol y por estado y que el listado no consulte por grupo); **ganchos de usuarios** (cambio de rol de técnico y de supervisor, desactivación, que reactivar no restaure y el contador de cierres); y **pantallas** (403 al Técnico y al Solicitante, 404 a un Supervisor ante grupos ajenos, el Supervisor sin acceso a editar, desactivar ni a los responsables, ids de otro grupo que no sirven para retirar, alta y edición con sus validaciones, confirmaciones con motivo, formularios de agregar y designar, grupo sin responsable ni técnicos, escape de HTML, filtros, navegación del Supervisor y tarjeta del hub).
- `tests/test_seed_demo.py` (+5): los tres grupos de demostración con sus miembros y responsables, que usen solo técnicos y supervisores del equipo, auditoría como acción del sistema, idempotencia sin tocar un grupo existente y que un supervisor demo vea solo los suyos. El test que comprobaba que toda la auditoría de `seed-demo` eran altas de usuario se acotó a las entradas de usuario, porque el comando ahora también crea grupos.
- `tests/test_layout.py` (+2 casos y un test dividido): el Supervisor ve **Grupos** en su menú, los grupos cuelgan de Administración para el Administrador y el hub enlaza con `/groups`.
- `tests/test_route_protection.py` cubre las rutas nuevas sin cambios.

Estado tras la entrega 3 de `v0.4.0` (estados y transiciones):

```text
1224 tests passing
```

Los 103 tests nuevos cubren:

- `tests/test_ticket_state_transitions.py` (75): **tabla y seed** (20 transiciones, la matriz de `docs/08` comprobada por propiedades —cierre directo nunca desde Resuelto, Cerrado solo sale reabriendo, la espera solo se entra desde En progreso, solo los seis estados—, todas las acciones del vocabulario presentes, idempotencia sin pisar una transición deshabilitada, salida del comando, unicidad por (origen, destino, acción) y que una transición no vaya de un estado a sí mismo); **acciones disponibles** por estado y por rol, destino, transición deshabilitada y que solo estén implementadas las tres operativas; **servicio** (iniciar, el ciclo completo con la versión subiendo cada vez, esperar con y sin motivo, con texto libre y sus reglas, motivo inactivo o inexistente, acciones que no admiten motivo, transiciones inválidas desde cada estado, acciones sin implementar, ticket cerrado, versión caduca, usuario inactivo, que no hace commit y **dos hilos que actúan a la vez producen una sola transición**); **pantallas** (los tres roles del personal, pantalla de confirmación, motivos activos en la de espera, motivo y texto visibles solo para el personal, 403 al Solicitante, 404 para tickets ajenos, acciones desconocidas, acción que ya no corresponde, ticket cerrado, conflicto de versión, versión ausente, validaciones del formulario y que se conserve lo escrito); y **detalle** (el botón correcto por estado y ninguno para Resuelto, Cerrado ni el Solicitante, y la opción "Tickets" marcada).
- `tests/test_seed_demo_tickets.py` (+20 netos): validación de los pasos de estado y de los motivos, los datos cubren los tres estados alcanzables hoy, los cinco motivos de espera, un ciclo completo y un texto libre; el historial queda igual que el de la aplicación (versión, actor, marca, motivo y texto); el Solicitante no ve el motivo y el personal sí; falta de transiciones o de un motivo de espera; y que refrescar no toca estado ni versión. `test_tickets_follow_the_creation_rules` ya no espera `Nuevo` en todos: calcula el estado final de cada ticket demo a partir de sus ajustes.
- `tests/test_ticket_policies.py` (+5): `can_change_state` en las tres comprobaciones que ya cubrían editar y cambiar la prioridad. `tests/test_layout.py` (+3 casos): Editar, Cambiar prioridad y Cambiar estado marcan "Tickets". `tests/test_catalogs.py`: el diccionario de `seed_catalogs` incluye `transiciones`.
- `tests/test_tickets_edit_service.py`: solo cambia el módulo desde el que importa `TicketClosedError` y `TicketConflictError` (ahora `tickets/versioning.py`), sin tocar ninguna comprobación.

Estado tras la entrega 2 de `v0.4.0` (catálogo de motivos de espera):

```text
1121 tests passing
```

Los 72 tests nuevos están en `tests/test_wait_reasons.py` (más dos ajustes por diseño: el diccionario que devuelve `seed_catalogs` en `test_catalogs.py` y la lista de tarjetas enlazadas del hub en `test_layout.py`). Cubren:

- **Seed y modelo:** los cinco motivos en orden, solo `OTRO` admite texto libre, idempotencia sin pisar cambios de un Administrador, salida del comando `seed-catalogs`, nombre único sin distinguir mayúsculas, código opcional y único, y valores por defecto.
- **Servicio:** alta (recorte, creador y auditoría con `entidad_tipo` `motivo_espera`), nombre repetido, edición de solo lo cambiado, edición sin cambios sin auditar, que ningún motivo esté protegido (se pueden desactivar todos), desactivar y reactivar con auditoría, y orden y filtro del listado.
- **Historial:** un evento puede referenciar un motivo (`wait_reason`), los demás eventos lo dejan vacío, desactivar un motivo no afecta a lo ya registrado y la base impide eliminar uno en uso.
- **Pantallas:** acceso (anónimo a login, los tres roles sin permiso reciben 403 en GET y no pueden cambiar nada por POST, ids inexistentes 404, CSRF), enlace en el hub, listado con la columna "Texto libre" y sin acciones protegidas, filtro, escape de HTML, alta con y sin la casilla, validaciones (nombre obligatorio y repetido, orden y largos), edición precargada, edición que desmarca la casilla, edición sin cambios, y desactivar/reactivar.

Estado tras la entrega 1 de `v0.4.0` (visibilidad y vocabulario del historial):

```text
1049 tests passing
```

Los 15 tests nuevos cubren:

- `tests/test_ticket_history_visibility.py` (13): todo evento del vocabulario declara su visibilidad por defecto; el servicio usa ese valor, admite indicar otra y rechaza (sin dejar nada pendiente) un evento fuera del vocabulario o una visibilidad desconocida; el personal ve los eventos internos y el Solicitante no; **la condición SQL coincide con la política `can_view_internal_activity` para los cuatro roles**; un conteo construido con la condición excluye lo interno; anónimos y usuarios inactivos no ven nada; y el detalle no muestra al Solicitante ni el evento interno ni su motivo, mientras el personal sí los ve.
- `tests/test_ticket_model.py` (+2 netos): la visibilidad por defecto es `PUBLICO`, la base rechaza una visibilidad desconocida y ya no restringe el vocabulario de `tipo_evento`. El test que comprobaba el CHECK de `tipo_evento` se sustituyó a propósito: esa restricción se eliminó por decisión de la fase y el rechazo de eventos desconocidos se prueba ahora en el servicio.
- `tests/test_tickets_service.py`: el test del historial pasa ahora el `viewer`, que `list_ticket_history` exige.

Estado tras el seed de tickets de demostración (entre `v0.3.0` y `v0.4.0`):

```text
1034 tests passing
```

Los 67 tests nuevos (`tests/test_seed_demo_tickets.py`) cubren:

- **los datos** (`DEMO_TICKETS`): son válidos, hay unos 40 con claves y títulos distintos, cubren todas las categorías, prioridades y ubicaciones (incluido «sin ubicación»), a todas las personas solicitantes y a buena parte del personal, con 0, 1 y 2 solicitantes, historias con ajustes, antigüedades repartidas, descripciones de largos distintos y un texto con caracteres que HTML interpretaría; y `validate_demo_tickets` rechaza datos incoherentes (clave o título repetidos o mal formados, usuario, categoría, prioridad o ubicación desconocidos, hora mal formada, Solicitante con `solicitantes`, ajustes sin cambio, sin motivo o hechos por alguien que no es personal);
- **el comando:** crea todos los tickets, se niega a ejecutarse en producción y pide `seed-demo` o `seed-catalogs` si faltan, sin cargar nada;
- **lo que crea:** creadores y solicitantes según las reglas de creación, categoría, prioridad y ubicación resueltas por nombre y código, una persona demo que solo ve los suyos (404 para el resto) y textos que se muestran escapados;
- **la marca:** todos los eventos de un ticket demo llevan su clave y su paso, el motivo de la prioridad convive con la marca y la marca no se ve en la interfaz;
- **volver a ejecutarlo:** no crea tickets ni eventos nuevos y responde `Actualizados (ya existían)`; el mismo día deja exactamente las mismas fechas; refrescar no toca el contenido ni las versiones; **un refresco da las mismas fechas que una carga nueva en el día nuevo** (se comparan las historias completas de los 40 tickets); los tickets se mueven al nuevo día; y las ediciones hechas a mano sobre un ticket demo siguen al ticket, en orden y sin quedar nunca en el futuro;
- **identidad:** mejorar un título en la lista no duplica el ticket ni sobrescribe el contenido ya cargado, añadir un ticket a la lista crea solo el nuevo, cambiar la antigüedad en la lista mueve el ticket, y nunca se toca un ticket creado a mano, ni siquiera uno con el mismo título y autor;
- **catálogos que faltan:** `Aviso:` y alternativa (`Sin clasificar` o sin ubicación), sin fallar;
- **fechas:** relativas al día de carga y medidas en días laborales, con ejemplos exactos, historial en orden cronológico, `fecha_modificacion` igual al último ajuste y solicitantes asociados en la fecha de creación;
- **tiempo laboral:** nada cae fuera de la jornada ni en fin de semana, en ejecuciones de mañana temprano, de noche y de domingo; los ajustes avanzan en horas laborales y saltan la noche y el fin de semana; un feriado se salta al contar días y horas; el calendario es configurable (otros días, otra jornada) y validado; y un refresco da lo mismo que una carga nueva incluso con un calendario distinto y feriados;
- **ajustes:** el historial queda igual que el de la aplicación (eventos, motivo en `contexto`, actor y versión) y el guard de inmutabilidad del ORM sigue rechazando una modificación normal.

Estado tras el cierre de `v0.3.0` (entrega 7):

```text
967 tests passing
```

Los 9 tests nuevos (`tests/test_route_protection.py`) recorren el mapa de rutas real en lugar de una lista escrita a mano:

- el recorrido encuentra rutas (no pasa en vacío) y cada ruta pública declarada (`auth.login`, `system.health` y `static`) existe y responde sin pedir sesión;
- **toda ruta, con cada método (GET y POST), redirige al login sin sesión** salvo las públicas, de modo que una ruta nueva no puede quedar sin autenticación por olvido;
- **toda ruta POST responde 400 sin token CSRF**, incluida la del login;
- dos pruebas de la propia red de seguridad: añaden una ruta abierta y una ruta POST exenta de CSRF, y comprueban que el recorrido las señala.

Estado tras la edición de tickets (entrega 6 de `v0.3.0`):

```text
958 tests passing
```

Los 112 tests nuevos cubren:

- `tests/test_tickets_edit_service.py` (35): cambios de título, descripción, categoría y ubicación y qué eventos registran (solo lo que cambió, un evento por tipo, una sola subida de versión), edición sin cambios, que no confirma, las mismas validaciones que la creación y sus límites exactos, valores de catálogo desactivados (rechazados si son nuevos, aceptados si el ticket ya los tenía), usuario inactivo, ticket cerrado, **conflicto de versión** (el cambio ajeno se conserva y el rechazado no deja rastro), prioridad con motivo (obligatorio, recortado, límite de 500), la misma prioridad sin efecto, prioridad inactiva o inexistente, y la descripción del historial sin el motivo.
- `tests/test_tickets_edit_routes.py` (67): acceso (anónimo, el personal, el Solicitante con 403 en GET y POST sin cambiar nada, 404 para tickets ajenos idénticos a los inexistentes, identificadores inválidos y ticket cerrado con su aviso), botones del detalle por rol y estado, formulario precargado, edición correcta con su historial visible, sin cambios, cada validación, que el formulario conserve lo escrito, categoría actual desactivada, CSRF, **conflicto entre dos ediciones** y su recarga con los datos actuales, cambio de prioridad (opciones, motivo, misma prioridad, prioridad inactiva), que el Solicitante vea qué cambió pero no el motivo, y escape de HTML.
- `tests/test_ticket_policies.py` (+10): `can_edit_ticket` y `can_change_priority`.

Estado tras el listado de tickets (entrega 5 de `v0.3.0`):

```text
846 tests passing
```

Los 86 tests nuevos cubren:

- `tests/test_tickets_list_service.py` (30): visibilidad (personal, Solicitante, solicitante retirado y usuario inactivo), **equivalencia entre la condición SQL y la política `can_view_ticket`** para todos los roles y casos, búsqueda (número con y sin `#`, número exacto y no prefijo, título y descripción sin distinguir mayúsculas, comodines literales, texto muy largo, solicitantes solo para el personal y solicitantes retirados), pestañas y contadores, filtros (estado, prioridad, categoría, ubicación y fechas por día local, incluido el límite entre días), los cuatro órdenes, paginación y que mostrar la lista no genere consultas por fila.
- `tests/test_tickets_list_routes.py` (55): acceso, cabecera y menú según el rol, lo que ve cada rol, columna de solicitantes solo para el personal, pestañas y contadores, buscador de la barra superior, filtros por URL, "Más filtros" que se abre solo si hay uno aplicado, valores inválidos ignorados, valores de catálogo desactivados, orden, paginación con los parámetros conservados, estados vacíos, tarjetas móviles, escape de HTML, y la ruta de navegación del detalle y el "Cancelar" del formulario.
- `tests/test_layout.py` (+1 caso): "Tickets" para el personal, "Mis tickets" para el Solicitante, y activas en el listado y el detalle.
- `tests/ticket_helpers.py` y la fixture `catalog` (en `tests/conftest.py`) concentran lo que comparten los tests de tickets.

Estado tras la creación de tickets (entrega 4 de `v0.3.0`):

```text
760 tests passing
```

Los 116 tests nuevos cubren:

- `tests/test_ticket_policies.py` (19): `can_create_ticket`, `can_choose_requesters` y `can_view_ticket` por rol, el Solicitante creador, solicitante vigente, solicitante retirado y ajeno, y usuarios inactivos o anónimos.
- `tests/test_tickets_routes.py` (82): acceso (anónimo, los cuatro roles); contenido del formulario por rol (la sección de solicitantes solo para el personal), solo valores activos, `Sin clasificar` al final y `Media` preseleccionada; creación como Solicitante (queda como su solicitante, historial, aviso y redirección) y como personal con 0, 1 y varios solicitantes; un Solicitante que manipula el envío para registrar otros solicitantes; solicitantes inválidos (inactivo, otro rol, inexistente); validaciones de cada campo y límites (los saltos de línea cuentan una vez); valores de catálogo inactivos o inexistentes; que el formulario conserve lo escrito; error de regla del servicio; CSRF; visibilidad del detalle (creador, solicitante vigente, retirado, ajeno, personal, inexistente e identificadores no numéricos, con la misma respuesta 404); y contenido del detalle (resumen, fechas en hora local, historial, datos solo para el personal y escape de HTML).
- `tests/test_formatting.py` (5): el filtro `local_datetime` (verano e invierno, fecha sin zona, zona desconocida y uso en plantillas).
- `tests/test_tickets_service.py` (+8): límite de la descripción, candidatos a solicitante, categorías para el selector, búsqueda por identificador público e historial.
- `tests/test_layout.py` (+2 casos): todos los roles ven ahora "Crear ticket" en el menú (antes solo Dashboard), y la opción solo se marca activa en el formulario, no en el detalle.
- `tests/conftest.py`: `make_user` admite sobrescribir cualquier valor por defecto (nombre, apellido, estado...).

Estado tras las tres primeras entregas de `v0.3.0` (catálogos, modelo de tickets y administración de catálogos):

```text
644 tests passing
```

- **Catálogos** (`tests/test_catalogs.py`, 17 tests; 402 en total): datos iniciales de `seed-catalogs` (estados en orden, prioridades con nivel creciente, categoría de respaldo y motivos de cierre), que no crea ubicaciones, idempotencia, que no pisa cambios de un Administrador, restricciones de base de datos (códigos únicos, nivel positivo y único entre activas, nombre de categoría único sin distinguir mayúsculas) y el comando CLI.
- **Modelo de tickets** (`tests/test_ticket_model.py` y `tests/test_tickets_service.py`, 44 tests; 446 en total): valores por defecto, `public_id` consecutivo y único, restricciones del cierre, solicitantes vigentes (índice parcial, retiro y nueva asociación), historial inmutable y con actor coherente, y el servicio `create_ticket` (datos, normalización, que el creador no sea solicitante por defecto, historial, validaciones, valores de catálogo inactivos o inexistentes y que no hace commit).
- **Administración de catálogos** (198 tests nuevos; 644 en total):
  - `tests/test_catalogs_service.py` (41): alta, edición (solo lo cambiado), duplicados sin distinguir mayúsculas y carrera de unicidad, desactivar y reactivar con auditoría y motivo, categoría de respaldo y última prioridad activa protegidas, conflicto al reactivar una prioridad, que desactivar no afecta a tickets existentes pero impide elegir el valor en tickets nuevos, y orden de los listados.
  - `tests/test_catalogs_routes.py` (154): control de acceso en todas las rutas (anónimo, roles sin permiso por GET y POST, ids inexistentes, CSRF), listados con filtro y estado vacío, formularios con sus validaciones, prioridades que ignoran nivel y color enviados y no se pueden crear, confirmaciones y protecciones, y escape de HTML.
  - `tests/test_layout.py`: el hub enlaza ahora cuatro secciones (antes solo Usuarios) y la navegación marca Administración como activa en las pantallas de catálogos.

Estado tras "Mi cuenta" y los datos demo (paso 5.2, cierre de `v0.2.0`):

```text
385 tests passing
```

Los 40 tests nuevos cubren:

- `tests/test_account_profile.py` (24): acceso (anónimo, todos los roles, bloqueo mientras haya un cambio de contraseña pendiente), contenido (datos propios, campos precargados, enlace al cambio de contraseña, sin acciones administrativas), edición (actualiza el contacto, auditoría por el propio usuario con solo los campos cambiados, sin cambios, vaciado de opcionales, los campos que gestiona el Administrador no se pueden cambiar, solo se edita la propia cuenta, validaciones y CSRF), navegación (Mi cuenta activa, menú del avatar) y las dos modalidades de la pantalla de contraseña (con layout en modo normal y aislada en modo obligatorio);
- `tests/test_seed_demo.py` (16): coherencia de los datos con las reglas de username, correo y longitudes, solo roles operativos, creación del equipo y carga de roles, la contraseña nunca se muestra, usuarios activos que pueden entrar sin cambio obligatorio, ningún Administrador, auditoría como acción del sistema, idempotencia, no modifica a quien ya existe, correo ocupado, ejecución sin interacción por variable de entorno, rechazo en producción, contraseña débil o con confirmación distinta, y respeto de un Administrador existente.

Dos tests existentes se ajustaron por el cambio de diseño: en modo normal, la pantalla de cambio de contraseña ya no ofrece "Volver al dashboard" sino "Volver a Mi cuenta".

Estado tras la base de la interfaz administrativa (paso 5.1):

```text
345 tests passing
```

Los 46 tests nuevos (`tests/test_layout.py`) cubren:

- la navegación por rol (opciones por rol, usuarios inactivos y anónimos, opción activa según el endpoint, que todos los endpoints existan) y las iniciales del avatar;
- el layout renderizado (sidebar filtrada por rol, sección activa, avatar, nombre y rol en la topbar, enlace para saltar al contenido, menú móvil, correspondencia de las categorías de aviso con las alertas de Bootstrap);
- el hub de administración (todas las secciones, solo Usuarios enlazada, el resto como "Próximamente", endpoints válidos);
- los activos locales: Bootstrap y sus iconos se sirven desde el propio servidor, **las huellas SHA-256 de los archivos coinciden con las documentadas**, ninguna plantilla ni hoja de estilo propia carga recursos externos, y el login sigue usando su CSS propio sin Bootstrap.

Un test existente se ajustó por el cambio de diseño: el dashboard ya no muestra un enlace directo a `/users` para el Administrador, sino a `/admin` (el hub), según `docs/11` sección 5.4.

Estado tras la administración de usuarios (paso 4.4):

```text
299 tests passing
```

Los 93 tests nuevos cubren:

- `tests/test_users_manage_service.py` (26): edición (solo los campos cambiados, sin cambios, normalización, correo de otro usuario, carrera por el correo), cambio de rol (efectos, sesiones, motivo, autoprotección, rol repetido o inexistente, protección del último Administrador activo, los inactivos no cuentan), desactivación y reactivación (efectos, sesiones, autoprotección, último Administrador, las sesiones anteriores no reviven) y restablecimiento de contraseña (medidas de seguridad, autoprotección, contraseña débil);
- `tests/test_users_manage_routes.py` (67): control de acceso en todas las rutas (anónimo, roles sin permiso por GET y POST, usuario inexistente, CSRF), detalle, edición (precarga, validaciones, el username no cambia), cambio de rol (con cierre de sesión del usuario), desactivación (confirmación, bloqueo de acceso, filtro de inactivos), reactivación, restablecimiento (contraseña mostrada una vez, sin caché, sin quedar en la auditoría, cambio obligatorio al volver a entrar) y todas las autoprotecciones.

`tests/conftest.py`: `make_user` admite un `username` y campos adicionales (por ejemplo `activo=False`) para crear varios usuarios del mismo rol.

Estado tras el listado y la creación de usuarios (paso 4.3):

```text
206 tests passing
```

Los 72 tests nuevos cubren:

- `tests/test_users_service.py` (23): creación (datos, normalización, auditoría sin secretos, sin commit, duplicados sin distinguir mayúsculas, rol inexistente, contraseña débil, carrera de unicidad con savepoint) y listado (orden, búsqueda por cada campo, comodines literales, límite de la búsqueda, filtros, combinación, paginación y ausencia de consultas N+1 al mostrar el rol);
- `tests/test_users_routes.py` (49): control de acceso (anónimo, roles sin permiso, también por POST, enlaces visibles solo para el Administrador), listado (búsqueda, filtros, filtros inválidos, estado vacío, paginación con filtros, escape de HTML), formulario de alta (opciones, CSRF), contraseña generada (se muestra una vez, sin caché, no se guarda en la auditoría, el nuevo usuario inicia sesión y es obligado a cambiarla), contraseña escrita y validaciones de cada campo.

`tests/conftest.py` suma la fixture `seeded_roles` y, al terminar cada test, cierra el pool de conexiones del engine (`db.engine.dispose()`): sin eso, cada test dejaba conexiones abiertas y a partir de unos 200 tests PostgreSQL agotaba `max_connections`.

Estado tras el cambio de contraseña propio y obligatorio (paso 4.2):

```text
134 tests passing
```

`tests/test_account_password.py` (25 tests) cubre: acceso anónimo, CSRF, cambio correcto (credenciales, sesión que se mantiene, mensaje de confirmación, auditoría, nuevo login, invalidación de otras sesiones, duración máxima no ampliada y reinicio de intentos fallidos), contraseña actual incorrecta (conteo, bloqueo y cierre de sesión, cuenta bloqueada), confirmación distinta, contraseña demasiado corta o igual a la actual, campos vacíos, que nunca se devuelvan las contraseñas, y la guardia de cambio obligatorio (rutas redirigidas, pantalla de cambio y cierre de sesión permitidos, rutas técnicas permitidas, restricción que se libera al completar el cambio y que permanece tras un intento fallido).

Estado tras la base de seguridad de contraseñas (paso 4.1):

```text
109 tests passing
```

Los 40 tests nuevos cubren:

- `tests/test_password_policy.py`: límites de longitud, ausencia de reglas de composición, espacios, contraseña igual a la actual, generador de contraseñas temporales (longitud, alfabeto sin ambiguos, unicidad) y validación del rango de `PASSWORD_MIN_LENGTH` al iniciar;
- `tests/test_credentials.py`: cambio propio (credenciales, invalidación de sesiones, auditoría sin secretos, contraseña actual incorrecta, contraseña nueva inválida o igual), contraseña temporal y restablecimiento (cambio obligatorio, sesiones, bloqueo, auditoría);
- `tests/test_cli.py`: `create-admin` con contraseña válida, demasiado corta y con longitud mínima configurada.

Estado tras la entrega de auditoría administrativa:

```text
69 tests passing
```

`tests/test_audit.py` (24 tests) cubre: registro de eventos de usuario y de sistema, captura de IP y user agent dentro y fuera de una petición, truncado del user agent, ausencia de commit en el servicio, vocabulario controlado de acciones, rechazo de claves sensibles (incluidas las anidadas), inmutabilidad (no se actualiza ni se elimina), restricciones CHECK y FK de la base de datos y existencia de los índices documentados.

Estado tras la entrega de límites de sesión:

```text
45 tests passing
```

`tests/test_session_limits.py` (13 tests) cubre: marcas de tiempo al iniciar sesión, renovación de la actividad, expiración por inactividad y por duración máxima, aviso en el login, sesión sin marcas de tiempo, límites tomados de la configuración, `/health` sin efecto sobre la sesión, limpieza al cerrar sesión, nuevo login tras expirar y rechazo de límites no positivos.

Estado tras la entrega RBAC base:

```text
32 tests passing
```

Los 12 tests nuevos (`tests/test_authorization.py`) cubren: anónimo redirigido al login, 403 para Solicitante, Técnico y Supervisor en `/admin`, acceso del Administrador, pérdida de acceso al desactivar al Administrador, políticas `can_manage_users` y `can_view_audit` por rol y comportamiento ante usuario anónimo.

## Protección crítica de testing

`tests/conftest.py` valida explícitamente que la base utilizada sea:

```text
workdesk_test
```

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
python -m pytest -q
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

`v0.1.0`, `v0.2.0 — Usuarios, autenticación completa y RBAC`, `v0.3.0 — Núcleo de tickets` y `v0.4.0 — Asignación, colaboración y ciclo de vida` están completas. Este apartado resume lo que dejaron implementado; la siguiente fase es `v0.5.0 — SLA y notificaciones internas` (ver "Próximo hito").

## Implementado hasta `v0.2.0`

- modelo Role;
- modelo User;
- roles estructurales;
- login;
- logout;
- Argon2id;
- Flask-Login;
- CSRF;
- protección de rutas;
- usuario activo/inactivo;
- bloqueo por intentos fallidos;
- `token_version`;
- login visual con branding oficial;
- favicons integrados en los templates actuales;
- tests de autenticación base;
- base RBAC: `RoleCode`, `has_any_role`, políticas `can_manage_users` y `can_view_audit`, decorador `roles_required` (en `src/workdesk/security/authorization.py`), manejador 403 y área `/admin` protegida;
- límites de sesión por inactividad y duración máxima;
- auditoría administrativa mínima: modelo `AdminAuditLog`, migración y servicio `record_admin_event`;
- base de seguridad de contraseñas: política, generador de contraseñas temporales, columna `debe_cambiar_password` y operaciones de cambio propio y restablecimiento;
- cambio de contraseña propio (`/account/password`) y cambio obligatorio de la contraseña temporal aplicado en backend;
- listado de usuarios (búsqueda, filtros y paginación) y creación de usuarios con contraseña temporal, solo para el Administrador;
- administración de usuarios existentes: detalle, edición de datos, cambio de rol, desactivación y reactivación, y restablecimiento de contraseña, con salvaguardas (nadie actúa sobre sí mismo, siempre queda un Administrador activo) y auditoría;
- Bootstrap y Bootstrap Icons locales, app shell (sidebar, topbar, avatar), navegación por rol filtrada en backend y hub de administración;
- "Mi cuenta" (`/account`): datos propios, edición de la información de contacto y acceso al cambio de contraseña;
- comando `seed-demo`: equipo de soporte ficticio, sin Administrador.

## Implementado en `v0.3.0`

- catálogos de tickets (estados, prioridades, categorías, ubicaciones y motivos de cierre) y el comando `seed-catalogs`;
- modelo de tickets (`tickets`, `tickets_solicitantes` e `historial_ticket` inmutable) con identificador público generado por una secuencia de PostgreSQL;
- administración de categorías, prioridades y ubicaciones por el Administrador, con auditoría;
- creación de tickets para los cuatro roles, con solicitantes elegidos por el personal;
- detalle de ticket con historial, visible solo para quien corresponde (404 para lo ajeno);
- listado "Tickets" / "Mis tickets" con pestañas, búsqueda, filtros, orden y paginación, con la visibilidad aplicada en la propia consulta;
- edición de título, descripción, categoría y ubicación, y cambio de prioridad con motivo obligatorio, con control de versión para las ediciones simultáneas;
- políticas de autorización de tickets: `can_create_ticket`, `can_choose_requesters`, `can_view_ticket`, `can_edit_ticket` y `can_change_priority`;
- red de seguridad automática sobre todas las rutas (autenticación y CSRF);
- guía de primera configuración, recorrido de prueba y solución de problemas en el README.

## Añadido después de `v0.3.0`

- comando opcional `seed-demo-tickets`: unos 40 tickets de demostración realistas, con fechas relativas, historial de ajustes del personal y datos separados de la lógica (ver "22. CLI"); creció con cada entrega de `v0.4.0` hasta los 76 tickets actuales.

## Implementado en `v0.4.0`

- historial con el vocabulario de eventos solo en la aplicación, visibilidad (pública o interna) por evento filtrada en la consulta y un descriptor por evento;
- catálogo y administración de motivos de espera;
- estados y transiciones: la tabla `transiciones_estados`, los cambios de estado operativos y el motor `change_state` con control de versión y bloqueo de la fila;
- grupos, con membresías y supervisores responsables (`/groups`);
- asignación de técnicos, grupo del ticket y escalamiento manual, con el estado derivado (`Nuevo` ↔ `Asignado`);
- agregar y retirar solicitantes tras crear el ticket;
- comentarios públicos y notas internas, con edición y eliminación con plazo;
- archivos adjuntos: almacenamiento local, validación por extensión y contenido, y descarga autenticada;
- resolución, validación del solicitante, cierre directo y excepcional y reapertura, con la regla «un ticket cerrado tiene fecha y motivo de cierre»;
- relaciones entre tickets y duplicados;
- bloqueo temporal de edición;
- administración de estados y transiciones (nombre visible, descripción y transiciones opcionales, con protecciones para no romper el flujo);
- políticas de autorización por acción (`can_change_state`, `can_assign_self`, `can_manage_assignments`, `can_manage_requesters`, `can_write_internal_note`, `can_resolve_ticket`, `can_close_directly`, `can_close_exceptionally`, `can_validate_resolution`, `can_reopen_ticket`, `can_manage_relations`, `can_access_groups`...) y su red de seguridad sobre todas las rutas;
- migraciones: diez nuevas (de 7 a 17) y 23 eventos del historial.

## Pendiente para la siguiente fase

Nada de `v0.2.0`, `v0.3.0` ni `v0.4.0`. Lo que falta pertenece a las fases posteriores (lo que `v0.4.0` deja preparado o pendiente está en "Próximo hito"):

- `v0.5.0`: SLA, cierre automático y notificaciones internas (ver "Próximo hito");
- las opciones de navegación y del hub de administración se añaden cuando existan sus pantallas (`navigation.py` y `admin/hub.py`);
- las políticas de autorización adicionales se incorporan con cada módulo;
- `v0.5.0`: el calendario laboral administrable y el motor de tiempo laboral compartido ya existen (entregas 1 y 2: `worktime.py` y el paquete `sla/`); falta que el SLA los use (entregas 3 y 4);
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