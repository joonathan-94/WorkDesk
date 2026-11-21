# WorkDesk

<p align="center">
  <img
    src="src/workdesk/static/img/brand/workdesk-logo-inverse.svg"
    alt="WorkDesk"
    width="360"
  >
</p>

<p align="center">
  <strong>Gestión de tickets de soporte TI con foco en seguridad, trazabilidad y evolución progresiva.</strong>
</p>

<p align="center">
  <img
    src="src/workdesk/static/img/brand/workdesk-social-preview.png"
    alt="Vista previa de WorkDesk"
    width="100%"
  >
</p>

> Plataforma web para la gestión y seguimiento de tickets de soporte TI, diseñada para evolucionar progresivamente hacia una solución más amplia de gestión del trabajo.

WorkDesk es un proyecto personal de desarrollo de software orientado inicialmente a la gestión integral de solicitudes de soporte TI.

El sistema busca centralizar el ciclo de vida de los tickets, facilitar la colaboración entre solicitantes y equipos técnicos, controlar prioridades y SLA, mantener trazabilidad de las acciones y proporcionar herramientas de seguimiento, conocimiento y análisis operacional.

---

## Guía rápida

¿Quieres ejecutar WorkDesk en tu equipo? Estos son los pasos, en orden. Cada uno enlaza con su explicación detallada.

1. [Instala los requisitos](#requisitos): Python, PostgreSQL y Git.
2. [Clona el repositorio, crea el entorno virtual e instala las dependencias](#instalación).
3. [Crea el rol y las dos bases de datos en PostgreSQL](#configuración-de-postgresql).
4. [Crea y completa el archivo `.env`](#variables-de-entorno).
5. [Prepara la base de datos](#preparación-inicial): migraciones, roles, catálogos y tu cuenta de Administrador.
6. [Arranca WorkDesk](#ejecutar-workdesk) y abre `http://127.0.0.1:5000`.
7. [Crea las categorías y ubicaciones](#configurar-categorías-y-ubicaciones) de tu organización desde la interfaz.
8. [Crea tu primer ticket](#crear-un-ticket) y haz el [recorrido de prueba](#recorrido-de-prueba) para ver todo lo que ya funciona.

Si algo falla por el camino, consulta la [solución de problemas](#solución-de-problemas).

---

## Estado del proyecto

### `v0.4.0 — Asignación, colaboración y ciclo de vida`

La cuarta versión de WorkDesk está implementada y validada. Con ella un ticket deja de ser algo que solo se registra y se edita: **se trabaja en equipo** y recorre su ciclo completo, desde que se crea hasta que se cierra (y, si hace falta, se reabre). Se construyó en 12 entregas pequeñas, cada una con su rama, tests y Pull Request:

- **Historial con visibilidad por evento:** cada evento del historial es público o interno, y es la consulta (no la plantilla) la que decide qué ve cada rol. El vocabulario de eventos vive en la aplicación, así que añadir uno no requiere una migración.
- **Motivos de espera:** catálogo administrable, con la opción genérica «Otro motivo» que admite un texto libre.
- **Estados y transiciones:** iniciar el trabajo, poner en espera y reactivar, con una tabla de transiciones que valida cada cambio y bloquea la fila del ticket para que dos personas que actúan a la vez no apliquen dos transiciones.
- **Grupos:** el Administrador los crea y el Supervisor gestiona los técnicos de los grupos de los que es responsable (los demás responden 404). Cambiar el rol de una persona o desactivarla cierra sus membresías.
- **Asignación:** un Técnico se asigna a sí mismo; el Supervisor y el Administrador asignan, reasignan, fijan el grupo y **escalan** un ticket con un motivo. Asignar al primer técnico pasa el ticket a `Asignado`.
- **Solicitantes del ticket:** el personal agrega o retira solicitantes después de crearlo. Quien se retira deja de ver el ticket, salvo que lo haya creado.
- **Comentarios y notas internas:** el Solicitante y el personal conversan en comentarios públicos; el personal escribe además notas internas que el Solicitante no ve por ninguna vía. El autor edita y elimina dentro de un plazo.
- **Archivos adjuntos:** se guardan en disco, fuera de `static/`, con validación por extensión y por contenido, SHA-256 y descarga autenticada. El adjunto de una nota interna hereda su visibilidad.
- **Resolución, validación, cierre y reapertura:** el personal resuelve y el solicitante confirma o rechaza la solución; también hay cierre directo, cierre excepcional del Supervisor y reapertura (con plazo para el solicitante). Un ticket cerrado siempre tiene fecha y motivo de cierre.
- **Relaciones y duplicados:** el personal relaciona tickets y marca un ticket como duplicado de otro (lo cierra con el motivo «Duplicado»).
- **Bloqueo temporal de edición:** mientras alguien edita un ticket, los demás lo ven en solo lectura y saben quién lo edita; el bloqueo se renueva solo y expira si el navegador se cierra. La versión del ticket sigue siendo la barrera final.
- **Estados y transiciones en la administración, y cierre de la versión:** el Administrador renombra los estados y habilita o deshabilita las transiciones opcionales sin poder romper el flujo. Además, una revisión de toda la fase reorganizó el código que había crecido y añadió un recorrido automático de la autorización de todas las rutas.

El seed de demostración (`seed-demo-tickets`) creció con cada entrega: hoy carga **76 tickets** que recorren todos esos caminos. Si vienes de `v0.3.0`, mira cómo [actualizar una instalación existente](#actualizar-una-instalación-existente) y el [recorrido de prueba](#recorrido-de-prueba).

Al cerrar la versión, la suite contaba con **2201 tests automatizados**.

### `v0.3.0 — Núcleo de tickets`

La tercera versión de WorkDesk está implementada y validada. Es la fase central del MVP: ya se pueden **crear, consultar, buscar y editar tickets**, y cada rol ve únicamente lo que le corresponde. Se construyó en entregas pequeñas, cada una con su rama, tests y Pull Request:

- **Catálogos de tickets:** estados (los seis estructurales), prioridades (Baja, Media, Alta y Crítica), categorías, ubicaciones, motivos de cierre y motivos de espera, con el comando `seed-catalogs` para cargar los datos iniciales.
- **Modelo de datos de tickets:** tabla de tickets con identificador público generado por una secuencia de PostgreSQL, solicitantes de cada ticket (relación temporal N:M) e historial de eventos inmutable, más el servicio que crea tickets.
- **Administración de catálogos:** el Administrador gestiona categorías, prioridades y ubicaciones desde la interfaz (crear, editar, desactivar y reactivar), con auditoría de cada cambio.
- **Creación de tickets:** cualquier rol puede crear un ticket desde "Crear ticket". El Solicitante queda como su propio solicitante; el personal (Técnico, Supervisor y Administrador) puede crearlo a nombre de otras personas, eligiendo ninguno, uno o varios solicitantes. Tras crearlo se abre su detalle, visible solo para quien corresponde.
- **Listado de tickets:** "Tickets" (personal) y "Mis tickets" (Solicitante) muestran solo lo que cada rol puede ver, con pestañas Todos, Abiertos y Cerrados, buscador (número, título, contenido y, para el personal, solicitante), filtros, orden y paginación. La barra superior también busca tickets.
- **Edición de tickets:** el personal puede editar el título, la descripción, la categoría y la ubicación de un ticket, y cambiar su prioridad indicando un motivo. Cada cambio queda en el historial con lo que había antes y lo que hay ahora, y si dos personas editan a la vez, la segunda recibe un aviso en lugar de pisar el cambio de la primera.
- **Cierre de la versión:** revisión final, tests que recorren todas las rutas de la aplicación para comprobar que ninguna queda sin autenticación ni sin protección CSRF, y la guía de primera configuración con un recorrido de prueba y una solución de problemas.

Al cerrar la versión, la suite contaba con **967 tests automatizados**.

### `v0.2.0 — Usuarios, autenticación completa y RBAC`

La segunda versión de WorkDesk está implementada y validada. Suma a la fundación:

- Autorización por roles (Solicitante, Técnico, Supervisor y Administrador) comprobada en backend, con error 403 y navegación filtrada por rol.
- Límites de sesión por inactividad (30 minutos) y por duración máxima (8 horas), configurables.
- Política de contraseñas configurable, contraseñas temporales y cambio obligatorio en el primer inicio de sesión.
- Administración de usuarios por el Administrador: listado con búsqueda, filtros y paginación; creación; edición; cambio de rol; desactivación y reactivación; y restablecimiento de contraseña, con salvaguardas (nadie actúa sobre sí mismo y siempre queda un Administrador activo).
- Auditoría administrativa inmutable de todas las acciones sobre usuarios.
- Pantalla "Mi cuenta": datos del usuario, edición de su información de contacto y cambio de contraseña.
- Interfaz administrativa con Bootstrap servido localmente (sin CDN): sidebar y topbar, navegación por rol y hub de administración.
- Comando `seed-demo` para cargar un equipo de soporte ficticio con el que mostrar el sistema.

Al cerrar la versión, la suite contaba con 385 tests automatizados.

### `v0.1.0 — Fundación técnica`

La fundación técnica de WorkDesk se encuentra implementada y validada.

Actualmente el proyecto dispone de:

- Aplicación Flask mediante patrón Application Factory.
- Arquitectura de monolito modular.
- Configuración mediante variables de entorno.
- PostgreSQL como base de datos principal.
- SQLAlchemy y Flask-SQLAlchemy.
- Migraciones mediante Alembic / Flask-Migrate.
- Modelos iniciales de usuarios y roles.
- Carga idempotente de roles estructurales.
- Creación segura del Administrador inicial mediante CLI.
- Autenticación por username y contraseña.
- Hash de contraseñas mediante Argon2id.
- Gestión de sesión mediante Flask-Login.
- Protección CSRF mediante Flask-WTF.
- Bloqueo temporal después de intentos fallidos de autenticación.
- Invalidación de sesiones mediante `token_version`.
- Protección de cookies de sesión.
- Usuario activo/inactivo integrado al flujo de autenticación.
- Interfaz visual de login con identidad gráfica oficial de WorkDesk.
- Identidad visual propia con isotipo, logotipo y variantes para fondos claros y oscuros.
- Favicons e iconos de aplicación integrados globalmente en los templates actuales.
- Manejo controlado de errores HTTP.
- Health check de aplicación y PostgreSQL.
- Logging persistente con rotación configurable.
- Base PostgreSQL independiente para pruebas.
- Suite inicial automatizada con `pytest`.
- Análisis estático mediante Ruff.

La suite de fundación cuenta actualmente con **20 tests automatizados**.

### Próximo hito

La siguiente versión es `v0.5.0 — SLA y notificaciones internas`: objetivos de SLA por prioridad calculados en tiempo laboral (con un calendario laboral que configura el Administrador), pausa mientras un ticket está en espera, cierre automático de los tickets resueltos que nadie valida y notificaciones internas. El detalle de cada fase está en [`docs/12_roadmap.md`](docs/12_roadmap.md).

---

## Alcance del MVP

WorkDesk se desarrollará de forma incremental hasta completar un MVP orientado a soporte TI.

Entre las capacidades planificadas se encuentran:

- Gestión completa de tickets.
- Roles y permisos.
- Asignación de múltiples técnicos.
- Comentarios públicos y notas internas.
- Archivos adjuntos.
- Estados y prioridades.
- Categorías y ubicaciones.
- Gestión de SLA.
- Notificaciones internas.
- Dashboards por rol.
- Visualización de carga de trabajo.
- Base de conocimiento.
- Reportes.
- Administración.
- Auditoría.
- Backups locales.
- Diseño responsive.

WorkDesk es una aplicación 100 % local o de intranet, por decisión del proyecto: no depende de Internet, correo, nube ni servicios de terceros, y sus notificaciones son internas. Se ejecuta en un equipo local o en un servidor propio de la organización.

---

## Stack tecnológico

### Backend

- Python
- Flask `3.1.3`
- Flask-SQLAlchemy `3.1.1`
- Flask-Migrate `4.1.0`
- SQLAlchemy
- PostgreSQL
- psycopg `3.3.6`
- Flask-Login `0.6.3`
- argon2-cffi `25.1.0`
- Flask-WTF `1.3.0`
- python-dotenv `1.2.4`
- tzdata `2026.5` (base de zonas horarias para mostrar las fechas en hora local; Windows no trae la suya)

### Frontend

Implementado actualmente con:

- HTML5
- CSS3
- JavaScript
- Jinja2

Las pantallas administrativas usan Bootstrap 5 y Bootstrap Icons, servidos localmente (sin CDN) desde `src/workdesk/static/vendor/`, con la paleta del Design System de WorkDesk. Las pantallas de acceso (login y cambio de contraseña) usan CSS propio.

### Desarrollo y calidad

- Git
- GitHub
- VS Code
- Alembic / Flask-Migrate
- pytest `9.1.1`
- Ruff `0.16.7`

---

## Arquitectura

WorkDesk utiliza una arquitectura de **monolito modular**.

La aplicación se mantiene dentro de un único proyecto Flask y una única base de datos PostgreSQL, separando las responsabilidades mediante módulos internos.

La inicialización utiliza el patrón:

```python
create_app()
```

La Application Factory se encarga de:

- crear la aplicación Flask;
- cargar la configuración;
- validar configuración obligatoria;
- inicializar extensiones;
- configurar autenticación;
- configurar logging;
- registrar comandos CLI;
- registrar manejadores de errores;
- registrar Blueprints.

La estructura continuará creciendo de manera progresiva, evitando crear capas o componentes que todavía no tengan una necesidad real.

---

## Estructura actual

```text
WorkDesk/
│
├── .github/
│   └── copilot-instructions.md
│
├── docs/
│   ├── assets/
│   ├── 01_vision_del_proyecto.md
│   ├── 02_objetivos.md
│   ├── 03_roles_y_permisos.md
│   ├── 04_requisitos_funcionales.md
│   ├── 05_requisitos_no_funcionales.md
│   ├── 06_reglas_de_negocio.md
│   ├── 07_casos_de_uso.md
│   ├── 08_flujo_de_tickets.md
│   ├── 09_modelo_de_datos.md
│   ├── 10_arquitectura.md
│   ├── 11_diseno_de_pantallas.md
│   └── 12_roadmap.md
│
├── instance/
│   ├── backups/
│   ├── logs/
│   └── uploads/
│
├── migrations/
│   └── versions/
│
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
│       ├── tickets/
│       │   └── routes/
│       ├── users/
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
│
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
│
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

`instance/`, los archivos `.env`, entornos virtuales, logs y caches de herramientas permanecen fuera del control de versiones.

Cada área funcional es un paquete con sus rutas, formularios y servicio. `tickets/` es el más grande y por eso tiene su propia organización (rutas por área, el catálogo de acciones de estado separado del motor y un descriptor por evento del historial); está explicada en [`docs/10_arquitectura.md`](docs/10_arquitectura.md), sección 28.

---

## Requisitos

Para ejecutar WorkDesk localmente se requiere:

| Requisito | Versión | Notas |
| --- | --- | --- |
| Python | 3.11 o superior | WorkDesk se desarrolla y se prueba con Python 3.14. En Windows, marca "Add python.exe to PATH" al instalarlo. |
| PostgreSQL | Una versión reciente | WorkDesk se desarrolla con PostgreSQL 18. Debe estar **instalado y en ejecución**. |
| Git | Cualquier versión reciente | Para clonar el repositorio. |

No hace falta Docker ni ningún servicio externo.

Comprueba lo que ya tienes instalado:

```bash
python --version
psql --version
git --version
```

En Windows, si `python` no se reconoce, prueba con `py`. Si `psql` no se reconoce, PostgreSQL puede estar instalado pero fuera del `PATH`: más adelante se explica cómo abrir su consola sin necesidad de él.

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/joonathan-94/WorkDesk.git
cd WorkDesk
```

A partir de aquí, **todos los comandos se ejecutan desde esta carpeta** (la raíz del proyecto, donde están `README.md` y `src/`).

---

### 2. Crear el entorno virtual

El entorno virtual mantiene las dependencias de WorkDesk separadas del resto de tu equipo.

```bash
python -m venv .venv
```

Actívalo según tu terminal:

| Terminal | Comando |
| --- | --- |
| Git Bash (Windows) | `source .venv/Scripts/activate` |
| PowerShell (Windows) | `.venv\Scripts\Activate.ps1` |
| CMD (Windows) | `.venv\Scripts\activate.bat` |
| macOS y Linux | `source .venv/bin/activate` |

Sabrás que está activo porque la línea de comandos empieza con `(.venv)`. Cada vez que abras una terminal nueva para trabajar con WorkDesk, tendrás que activarlo otra vez.

Si PowerShell se niega a ejecutar el script por la política de ejecución, ejecuta una sola vez `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` y vuelve a intentarlo, o usa CMD o Git Bash.

---

### 3. Instalar dependencias

Para desarrollo:

```bash
python -m pip install -r requirements-dev.txt
```

Esto instala tanto las dependencias necesarias para ejecutar WorkDesk como las herramientas de testing y análisis estático.

Para instalar únicamente las dependencias de ejecución:

```bash
python -m pip install -r requirements.txt
```

Para comprobar que quedaron instaladas:

```bash
python -m pip show flask
```

---

## Configuración de PostgreSQL

WorkDesk utiliza dos bases de datos locales separadas:

```text
workdesk_dev
workdesk_test
```

`workdesk_dev` es la base de la aplicación: ahí viven tus usuarios, catálogos y tickets.

`workdesk_test` se utiliza exclusivamente para los tests automatizados. Cada test **borra y vuelve a crear las tablas** antes de empezar, por eso nunca deben apuntar a `workdesk_dev` (WorkDesk lo impide: ver [Tests](#tests)).

Ambas pertenecen a un rol PostgreSQL dedicado, `workdesk_app`, para que la aplicación no tenga que usar el superusuario.

### 1. Abrir la consola de PostgreSQL

Las sentencias de abajo se ejecutan una sola vez, como el superusuario `postgres` (con la contraseña que elegiste al instalar PostgreSQL). Usa la opción que prefieras:

- **`psql`:** desde el menú Inicio abre **SQL Shell (psql)** y pulsa Enter en cada valor propuesto hasta que pida la contraseña de `postgres`. Si `psql` está en el `PATH`, también sirve `psql -U postgres`.
- **pgAdmin:** conéctate al servidor, haz clic derecho sobre la base `postgres` y elige **Query Tool**. Ejecuta **cada sentencia por separado** (selecciónala y pulsa ejecutar): `CREATE DATABASE` no puede ir dentro de un lote de varias sentencias.

### 2. Crear el rol y las bases de datos

```sql
CREATE ROLE workdesk_app WITH LOGIN PASSWORD 'elige-una-contraseña';

CREATE DATABASE workdesk_dev OWNER workdesk_app;

CREATE DATABASE workdesk_test OWNER workdesk_app;
```

- Cambia `elige-una-contraseña` por una contraseña tuya. La necesitarás en el archivo `.env`; para uso local conviene una sin símbolos (ver [Variables de entorno](#variables-de-entorno)).
- Que `workdesk_app` sea el **propietario** de las dos bases es importante: desde PostgreSQL 15, un rol que no es propietario de la base no puede crear tablas en ella por defecto, y las migraciones fallarían.
- Si el rol o las bases ya existen, PostgreSQL responde `already exists` (o "ya existe"): puedes continuar.
- En `psql`, `\l` lista las bases creadas y `\q` cierra la consola.

Las credenciales reales deben definirse únicamente en el archivo `.env` local.

---

## Variables de entorno

WorkDesk lee su configuración de un archivo `.env` ubicado en la raíz del proyecto. Ese archivo **no se versiona** porque contiene secretos; el repositorio incluye `.env.example` como plantilla.

### 1. Copiar la plantilla

| Terminal | Comando |
| --- | --- |
| Git Bash, macOS y Linux | `cp .env.example .env` |
| PowerShell | `Copy-Item .env.example .env` |
| CMD | `copy .env.example .env` |

### 2. Generar la `SECRET_KEY`

`SECRET_KEY` es la clave con la que Flask firma la cookie de sesión. Cada instalación debe tener la suya: genérala con este comando y copia el resultado (64 caracteres).

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Completar tres valores

La plantilla ya trae valores razonables para casi todo. Edita `.env` y completa solo estas tres líneas:

```env
SECRET_KEY=pega-aqui-la-clave-generada

DATABASE_URL=postgresql+psycopg://workdesk_app:TU_CONTRASENA@localhost:5432/workdesk_dev

TEST_DATABASE_URL=postgresql+psycopg://workdesk_app:TU_CONTRASENA@localhost:5432/workdesk_test
```

La dirección de conexión tiene este formato:

```text
postgresql+psycopg://USUARIO:CONTRASEÑA@SERVIDOR:PUERTO/BASE
```

- `TU_CONTRASENA` es la contraseña que le pusiste al rol `workdesk_app`.
- Si la contraseña tiene símbolos, deben escribirse codificados en la dirección: `@` → `%40`, `:` → `%3A`, `/` → `%2F`, `#` → `%23`, `?` → `%3F` y `%` → `%25`. Para un equipo local, lo más simple es una contraseña sin símbolos.
- `5432` es el puerto habitual de PostgreSQL; cámbialo si lo instalaste con otro.
- `TEST_DATABASE_URL` **nunca** debe apuntar a `workdesk_dev`: la suite se niega a ejecutarse si la base no se llama `workdesk_test`.

No deben versionarse credenciales reales: `.env` está en `.gitignore`, y `git status` no debería mostrarlo.

### Todas las variables

Solo `SECRET_KEY` y `DATABASE_URL` son obligatorias para arrancar la aplicación; `TEST_DATABASE_URL` hace falta únicamente para los tests. El resto tiene un valor por defecto.

| Variable | Valor por defecto | Para qué sirve |
| --- | --- | --- |
| `APP_ENV` | `development` | Entorno. Con `production`, `seed-demo` y `seed-demo-tickets` se niegan a ejecutarse. |
| `APP_TIMEZONE` | `America/Santiago` | Zona horaria en la que se muestran las fechas (nombre de la base IANA, por ejemplo `Europe/Madrid`). |
| `SECRET_KEY` | — (obligatoria) | Clave que firma las sesiones. |
| `SESSION_COOKIE_SECURE` | `false` | `false` mientras uses HTTP local; `true` solo con HTTPS. |
| `DATABASE_URL` | — (obligatoria) | Conexión a la base de la aplicación (`workdesk_dev`). |
| `TEST_DATABASE_URL` | — | Conexión a la base de los tests (`workdesk_test`). |
| `LOGIN_MAX_FAILED_ATTEMPTS` | `5` | Intentos fallidos de inicio de sesión antes de bloquear la cuenta. |
| `LOGIN_LOCK_MINUTES` | `15` | Minutos que dura ese bloqueo. |
| `PASSWORD_MIN_LENGTH` | `12` | Longitud mínima de las contraseñas (entre 8 y 128). |
| `SESSION_IDLE_MINUTES` | `30` | Minutos de inactividad tras los cuales se cierra la sesión. |
| `SESSION_MAX_HOURS` | `8` | Duración máxima de una sesión, aunque se use todo el tiempo. |
| `UPLOAD_MAX_BYTES` | `10485760` (10 MB) | Tamaño máximo de cada archivo adjunto, en bytes. Debe ser mayor que cero. |
| `UPLOAD_MAX_FILES_PER_TICKET` | `20` | Cantidad máxima de archivos activos por ticket. Debe ser mayor que cero. |
| `UPLOADS_DIR` | `instance/uploads` | Carpeta donde se guardan los adjuntos (fuera de `static/`, no se versiona). |
| `COMMENT_EDIT_WINDOW_MINUTES` | `30` | Minutos durante los que el autor de un comentario puede editarlo o eliminarlo (el Supervisor y el Administrador pueden siempre). Debe ser mayor que cero. |
| `REOPEN_WINDOW_DAYS` | `30` | Días, desde el cierre, durante los que un solicitante puede reabrir su ticket (el personal puede siempre). Debe ser mayor que cero. |
| `EDIT_LOCK_TTL_SECONDS` | `120` | Segundos que dura el bloqueo de edición de un ticket sin renovarse. Debe ser mayor que cero. |
| `EDIT_LOCK_HEARTBEAT_SECONDS` | `45` | Cada cuántos segundos renueva el bloqueo la pantalla de edición mientras está abierta. Debe ser mayor que cero y menor que `EDIT_LOCK_TTL_SECONDS`. |
| `LOG_LEVEL` | `DEBUG` en desarrollo, `INFO` en otro entorno | Nivel de detalle del registro técnico. |
| `LOG_MAX_BYTES` | `5242880` (5 MB) | Tamaño máximo de cada archivo de log. |
| `LOG_BACKUP_COUNT` | `5` | Cantidad de archivos de log antiguos que se conservan. |
| `WORKDESK_DEMO_PASSWORD` | — | Opcional, solo desarrollo: contraseña de `seed-demo` para ejecutarlo sin que la pida. |

Durante el desarrollo local mediante HTTP debe mantenerse `SESSION_COOKIE_SECURE=false`. En una futura ejecución mediante HTTPS deberá utilizarse `SESSION_COOKIE_SECURE=true`.

---

## Preparación inicial

Con las bases de datos creadas y el archivo `.env` configurado (secciones anteriores), ejecuta estos pasos **en este orden**, con el entorno virtual activado y desde la carpeta del proyecto:

| Paso | Comando | Para qué sirve |
| --- | --- | --- |
| 1 | `db upgrade` | Crea las tablas en PostgreSQL. |
| 2 | `seed-roles` | Carga los cuatro roles del sistema. |
| 3 | `seed-catalogs` | Carga estados y sus transiciones, prioridades, la categoría de respaldo, los motivos de cierre, los motivos de espera y los tipos de relación entre tickets. |
| 4 | `create-admin` | Crea tu cuenta de Administrador. |
| 5 | `seed-demo` (opcional) | Carga un equipo de soporte ficticio para probar el sistema. |
| 6 | `run` | Arranca WorkDesk. |
| 7 | Desde la interfaz | Crea las categorías y ubicaciones de tu organización. |
| 8 | `seed-demo-tickets` (opcional) | Carga 76 tickets de ejemplo, escritos como los escribiría gente real. Necesita los pasos 3, 5 y 7 (ver [Tickets de demostración](#tener-tickets-con-los-que-probar)). |
| 9 | Desde la interfaz | Crea tu primer ticket. |

Todos los comandos llevan el prefijo `python -m flask --app src.workdesk` (por ejemplo, `python -m flask --app src.workdesk seed-roles`). Cada paso se explica a continuación. Si alguno falla, consulta la [solución de problemas](#solución-de-problemas).

---

### Aplicar migraciones

```bash
python -m flask --app src.workdesk db upgrade
```

Las migraciones actuales crean estas tablas:

- `roles` y `usuarios`: identidad y roles.
- `auditoria_administrativa`: registro inmutable de las acciones administrativas.
- `estados`, `transiciones_estados`, `prioridades`, `categorias`, `ubicaciones`, `motivos_cierre` y `motivos_espera`: catálogos de tickets y las transiciones válidas entre estados.
- `tickets`, `tickets_solicitantes` e `historial_ticket`: los tickets, sus solicitantes y su historial.
- `grupos`, `usuarios_grupos` y `grupos_supervisores`: los grupos de atención, sus técnicos y sus supervisores responsables.
- `tickets_tecnicos` (y la columna `tickets.grupo_id`): los técnicos asignados a cada ticket y su grupo.
- `comentarios`: los comentarios públicos y las notas internas de los tickets.
- `archivos`: los metadatos de los archivos adjuntos (el contenido va a `instance/uploads`, no a la base de datos).
- `validaciones`: la respuesta de cada solicitante a la resolución de un ticket (confirmada o rechazada), por ciclo de resolución.
- `tipos_relacion_ticket` y `tickets_relaciones`: los tipos de relación entre tickets (`DUPLICADO` y `RELACIONADO`) y las relaciones vigentes o quitadas.
- `bloqueos_edicion_tickets`: el bloqueo temporal de edición de un ticket (quién lo edita ahora y hasta cuándo).
- `calendarios_laborales`, `horarios_laborales` y `feriados`: las versiones del calendario laboral, sus franjas por día y sus feriados.

Para comprobar que se aplicaron:

```bash
python -m flask --app src.workdesk db current
```

La última línea debe ser un identificador seguido de `(head)`. Si no se muestra ninguno, la base sigue vacía y falta ejecutar `db upgrade`.

---

### Cargar roles estructurales

```bash
python -m flask --app src.workdesk seed-roles
```

Se crean de manera idempotente:

```text
SOLICITANTE
TECNICO
SUPERVISOR
ADMINISTRADOR
```

El comando puede volver a ejecutarse sin duplicar los roles existentes.

---

### Cargar los catálogos iniciales

```bash
python -m flask --app src.workdesk seed-catalogs
```

Carga, de manera idempotente, los datos que WorkDesk necesita para funcionar:

```text
Estados             Nuevo, Asignado, En progreso, En espera, Resuelto, Cerrado
Transiciones        las 20 transiciones válidas entre esos estados
Prioridades         Baja, Media, Alta, Crítica
Categoría           Sin clasificar (categoría de respaldo)
Motivos de cierre   Resolución validada, Cierre directo, Inactividad,
                    Duplicado, Cancelación, Cierre excepcional
Motivos de espera   Información pendiente, Espera de un tercero,
                    Aprobación pendiente, Recurso pendiente, Otro motivo
```

El comando puede volver a ejecutarse sin duplicar nada y sin pisar lo que un Administrador haya renombrado o desactivado.

**No carga categorías de ejemplo ni ubicaciones.** Dependen de cada organización, así que ningún seed las incluye: una instalación real no debe arrancar con datos ficticios. Se crean desde la interfaz, como se explica en [Configurar categorías y ubicaciones](#configurar-categorías-y-ubicaciones).

---

### Crear el Administrador inicial

```bash
python -m flask --app src.workdesk create-admin
```

El comando solicita:

- nombre;
- apellido;
- username (es lo que escribirás para iniciar sesión; se guarda en minúsculas);
- email;
- contraseña (no se muestra al escribirla y se pide dos veces).

La contraseña debe cumplir la longitud mínima configurada (`PASSWORD_MIN_LENGTH`, 12 caracteres por defecto) y se almacena utilizando Argon2id. Al terminar, el comando responde `Administrador '...' creado correctamente.`

El comando impide crear accidentalmente más de un Administrador inicial mediante este mecanismo de bootstrap: si ya existe uno responde `Ya existe un usuario con rol ADMINISTRADOR.` Los demás usuarios se crean desde la interfaz, en **Administración → Usuarios**.

---

### Cargar datos de demostración (opcional)

```bash
python -m flask --app src.workdesk seed-demo
```

Crea un equipo de soporte ficticio de 12 personas (2 supervisores, 4 técnicos y 6 solicitantes) con correos `@workdesk.local`, útil para mostrar el sistema, y tres grupos de ejemplo (Soporte Redes, Soporte Usuarios y Aplicaciones) con sus técnicos y supervisores responsables. Es idempotente: no duplica a las personas ni a los grupos que ya existan, así que puedes volver a ejecutarlo para cargar solo los grupos. No crea ningún Administrador: usa `create-admin` para crear el tuyo.

- La contraseña común de los usuarios demo se pide al ejecutar el comando (oculta). Para ejecutarlo sin interacción se puede definir la variable de entorno `WORKDESK_DEMO_PASSWORD`. Nunca se muestra ni se guarda.
- Es idempotente: omite a quien ya exista, sin modificarlo.
- No se ejecuta con `APP_ENV=production`.
- Los usuarios quedan activos y sin cambio de contraseña obligatorio, para poder entrar directamente.

---

## Actualizar una instalación existente

Si ya tenías WorkDesk funcionando con una versión anterior (por ejemplo, `v0.3.0`) y traes los cambios nuevos con `git pull`, estos son los pasos, con el entorno virtual activado y desde la carpeta del proyecto. **No hace falta recrear la base de datos:** tus datos se conservan.

| Paso | Comando | Para qué sirve |
| --- | --- | --- |
| 1 | `python -m pip install -r requirements-dev.txt` | Instala las dependencias si cambiaron (si no cambiaron, no hace nada). |
| 2 | `python -m flask --app src.workdesk db upgrade` | Aplica las migraciones nuevas. |
| 3 | `python -m flask --app src.workdesk seed-catalogs` | Carga lo estructural que las versiones nuevas necesitan: las transiciones entre estados, los motivos de espera y los tipos de relación entre tickets. No duplica nada ni pisa lo que hayas renombrado o desactivado. |
| 4 | `python -m flask --app src.workdesk run --debug` | Reinicia WorkDesk. |

Para comprobarlo, `db current` debe terminar en `(head)` y `db check` no debe encontrar cambios pendientes.

Al pasar de `v0.3.0` a `v0.4.0` conviene saber que:

- Las variables de entorno nuevas (`UPLOAD_MAX_BYTES`, `UPLOAD_MAX_FILES_PER_TICKET`, `UPLOADS_DIR`, `COMMENT_EDIT_WINDOW_MINUTES`, `REOPEN_WINDOW_DAYS`, `EDIT_LOCK_TTL_SECONDS` y `EDIT_LOCK_HEARTBEAT_SECONDS`) tienen valor por defecto, así que no hace falta tocar tu `.env`. Están descritas en la [tabla de variables](#todas-las-variables).
- Los eventos que ya tenía el historial se conservan y siguen siendo visibles para el Solicitante, como antes.
- Los datos de demostración no modifican lo que ya cargaste. Para ver los grupos de ejemplo, ejecuta `seed-demo` de nuevo (no duplica a nadie). `seed-demo-tickets` crea solo los tickets que falten, y los que ya tenías conservan su contenido: para verlos con las historias nuevas hay que recrear la base de desarrollo, como se explica en el [recorrido de prueba](#tener-tickets-con-los-que-probar).

---

## Ejecutar WorkDesk

Con el entorno virtual activado y desde la raíz del proyecto:

```bash
python -m flask --app src.workdesk run --debug
```

La aplicación estará disponible normalmente en:

```text
http://127.0.0.1:5000
```

Abre esa dirección en el navegador e inicia sesión con el Administrador que creaste en el paso 4.

- **Comprobar que todo responde:** abre `http://127.0.0.1:5000/health`. Debe mostrar `"status": "ok"`, lo que confirma que la aplicación y PostgreSQL funcionan.
- **Detenerla:** pulsa `Ctrl+C` en la terminal.
- **`--debug`:** recarga la aplicación cada vez que cambias el código y muestra errores detallados. Úsalo solo en desarrollo.
- **Puerto ocupado:** si el 5000 está en uso (en macOS lo ocupa AirPlay), añade `--port 5001` al comando y abre esa dirección.

---

## Configurar categorías y ubicaciones

Los tickets necesitan una categoría y, opcionalmente, una ubicación. WorkDesk solo trae la categoría de respaldo `Sin clasificar`; el resto lo define cada organización desde la interfaz, con la sesión del Administrador iniciada:

1. En el menú lateral, abre **Administración**.
2. **Categorías** → **Nueva categoría**. El nombre es obligatorio; la descripción y el orden son opcionales (las categorías con número menor aparecen primero). Para un equipo de soporte TI, por ejemplo: `Accesos y cuentas`, `Correo`, `Hardware`, `Software`, `Redes`, `Impresoras`.
3. **Ubicaciones** → **Nueva ubicación**. Indica el nombre y, si quieres, el tipo (Sucursal, Oficina, Edificio, Piso, Área, Instalación u Otra). Por ejemplo, `Casa matriz` (Sucursal) o `Edificio A - Piso 2` (Piso).
4. **Prioridades** (opcional): puedes cambiar el nombre y la descripción de las cuatro prioridades, o desactivar alguna. Su nivel y su color son fijos, y siempre debe quedar al menos una activa.
5. **Motivos de espera** (opcional): `seed-catalogs` ya carga cinco. Puedes renombrarlos, crear otros (con la casilla "Permite añadir un texto libre" para los genéricos) o desactivarlos. Se ofrecen al poner un ticket en espera.
6. **Estados y transiciones** (opcional): renombra los estados si tu equipo usa otras palabras y deshabilita las transiciones que no uses (por ejemplo, el cierre directo). Los seis estados y sus transiciones son estructurales: no se crean ni se eliminan, y hay transiciones protegidas que no se pueden deshabilitar.

Reglas que conviene conocer:

- El nombre no puede repetirse dentro de un mismo catálogo, sin distinguir mayúsculas. Si dos edificios tienen un `Piso 2`, nómbralos `Edificio A - Piso 2` y `Edificio B - Piso 2`.
- **Desactivar** un valor no afecta a los tickets que ya lo usan: solo deja de poder elegirse en tickets nuevos. Se puede reactivar cuando quieras.
- `Sin clasificar` se puede renombrar, pero no desactivar.
- Cada cambio queda registrado en la auditoría administrativa.

Si solo quieres probar el sistema, bastan tres o cuatro categorías y una o dos ubicaciones.

Si además vas a cargar los [tickets de demostración](#tener-tickets-con-los-que-probar), crea exactamente estas, con estos nombres: categorías `Redes`, `Hardware`, `Correo` e `Impresoras`, y ubicaciones `Suc Lo Marcoleta` (Sucursal) y `Suc Manuel Antonio Matta` (Oficina).

---

## Crear un ticket

Con las categorías (y, si quieres, las ubicaciones) ya creadas, cualquier usuario puede registrar un ticket desde **Crear ticket**, en el menú lateral:

1. **Título** (obligatorio, hasta 200 caracteres) y **Descripción** (obligatoria, hasta 2000; un contador muestra cuántos llevas). No incluyas contraseñas ni información sensible.
2. **Categoría** (obligatoria): si no sabes cuál elegir, `Sin clasificar` aparece siempre al final de la lista. **Prioridad** (obligatoria; viene preseleccionada `Media`) y **Ubicación** (opcional).
3. **Solicitantes**, solo para Técnico, Supervisor y Administrador y de forma opcional: marca a las personas a cuyo nombre se crea el ticket (hay un buscador sobre la lista). Si no eliges a nadie, el ticket se crea sin solicitante, por ejemplo una mantención interna. Un Solicitante no ve esta sección: queda siempre como su propio solicitante.

Al crearlo se abre el detalle del ticket, con su número (`#1`, `#2`...), su estado inicial `Nuevo`, el resumen y el historial. Quien crea el ticket queda registrado como **creador**, aunque no sea el solicitante.

Para probar los distintos roles sin crear usuarios a mano, carga el equipo de demostración con `seed-demo` (paso 5 de la preparación inicial) y, si quieres datos con los que ver los listados, `seed-demo-tickets` (paso 8). Con un Solicitante comprueba que solo ve los tickets que creó o donde es solicitante; el de cualquier otra persona responde "no encontrado".

---

## Consultar y buscar tickets

La opción **Tickets** (para el personal) o **Mis tickets** (para el Solicitante), en el menú lateral, lista los tickets que cada persona puede ver:

- **Pestañas:** Todos, Abiertos y Cerrados, cada una con su contador. Se abre en **Abiertos**, que incluye todo lo que no está Cerrado (un ticket Resuelto sigue abierto porque espera la confirmación del solicitante).
- **Buscador:** acepta el número (`12` o `#12`), parte del título o de la descripción. El personal también puede escribir el nombre de un solicitante. La barra superior busca igual, en todas las pestañas.
- **Filtros:** estado y prioridad; y, en "Más filtros", categoría, ubicación y fechas de creación. Se pueden combinar entre sí y con el buscador.
- **Orden:** más recientes (por defecto), más antiguos, mayor prioridad primero o recién actualizados.
- **Paginación:** de 20 tickets por página; los enlaces conservan la búsqueda, los filtros y el orden.

Cada rol ve solo lo suyo desde la propia consulta a la base de datos: el personal ve todos los tickets y el Solicitante solo los que creó o donde es solicitante.

---

## Editar un ticket

Al abrir un ticket, el personal (Técnico, Supervisor y Administrador) ve dos botones; el Solicitante no los ve y, aunque abriera la dirección a mano, el servidor se lo impide:

- **Editar:** cambia el título, la descripción, la categoría y la ubicación. Solo se ofrecen valores activos, pero el valor que el ticket ya tiene se puede conservar aunque se haya desactivado después. Si no cambias nada, no se registra nada.
- **Cambiar prioridad:** pantalla aparte, porque **exige un motivo** (hasta 500 caracteres). Elegir la misma prioridad que ya tiene el ticket no genera ningún cambio.

Cosas que conviene saber:

- **Historial:** en el detalle, cada cambio muestra qué se modificó (por ejemplo, `Prioridad: «Media» → «Alta»`). El **motivo** de un cambio de prioridad lo ve solo el personal: el Solicitante ve qué cambió, pero no por qué.
- **Ediciones simultáneas:** si mientras editas un ticket otra persona lo modifica, al guardar verás un aviso y el formulario se recarga con los datos actuales, sin pisar su cambio. Además, mientras alguien tiene abierta la pantalla de editar (o de cambiar la prioridad), el ticket queda reservado para esa persona: las demás pueden consultarlo, pero no editarlo, y ven quién lo está editando.
- **Tickets cerrados:** no se editan ni se les cambia la prioridad; primero deben reabrirse (ver **Resolver, cerrar y reabrir**).

---

## El ciclo de vida de un ticket

Un ticket nace `Nuevo` y recorre estos estados. Cada cambio es una acción con su propia pantalla de confirmación y queda en el historial. Los nombres son los de fábrica: el Administrador puede renombrar los estados.

| Acción | Quién | Desde → hacia |
| --- | --- | --- |
| Asignar al primer técnico | Supervisor, Administrador; un Técnico se asigna a sí mismo | `Nuevo` → `Asignado` (automático) |
| Quitar al último técnico | los mismos | `Asignado` → `Nuevo` (automático) |
| Iniciar trabajo | Personal | `Nuevo` o `Asignado` → `En progreso` |
| Poner en espera | Personal | `En progreso` → `En espera` (con un motivo opcional) |
| Reactivar | Personal | `En espera` → `En progreso` |
| Resolver | Personal | `Nuevo`, `Asignado`, `En progreso` o `En espera` → `Resuelto` |
| Cierre directo | Personal | Esos cuatro → `Cerrado` (motivo «Cierre directo» o «Cancelación») |
| Confirmar la solución | Un solicitante del ticket | `Resuelto` → `Cerrado` |
| Rechazar la solución | Un solicitante del ticket (debe explicar qué falta) | `Resuelto` → `En progreso` |
| Cierre excepcional | Supervisor, Administrador (con un motivo) | `Resuelto` → `Cerrado` |
| Reabrir | Personal; un solicitante, solo un ticket cerrado y dentro del plazo | `Resuelto` o `Cerrado` → `En progreso` |

Dos ideas que atraviesan todo el flujo:

- **Un ticket cerrado siempre tiene fecha y motivo de cierre**, y es de solo lectura salvo para reabrirlo. Cancelar y marcar un duplicado no son estados: son un cierre con ese motivo.
- **Lo que el Solicitante no debe ver, no le llega por ninguna vía.** Las notas internas, el grupo, el escalamiento, las relaciones y los cambios de solicitantes quedan fuera de su historial; lo decide la consulta, no la plantilla.

Si dos personas actúan sobre el mismo ticket a la vez, la segunda recibe un aviso en lugar de pisar a la primera.

---

## Recorrido de prueba

Una lista de comprobación, de media hora si la sigues entera, para ver con tus propios ojos todo lo que hace `v0.4.0`. Parte de una instalación terminada: los pasos 1 a 8 de la [preparación inicial](#preparación-inicial), es decir, con los usuarios de demostración (personas de cada rol), las categorías y ubicaciones de la demostración y los tickets de ejemplo ya cargados. Si prefieres no cargar los tickets de ejemplo, crea algunos a mano desde **Crear ticket**.

### Tener tickets con los que probar

Para ver la paginación, la búsqueda, los filtros y los historiales hacen falta muchos tickets. WorkDesk incluye un comando opcional que carga 76 tickets de demostración:

```bash
python -m flask --app src.workdesk seed-demo-tickets
```

**Antes de ejecutarlo** necesitas:

- los catálogos iniciales (`seed-catalogs`, paso 3) y los usuarios de demostración (`seed-demo`, paso 5), porque los tickets se crean a nombre de ese equipo;
- las categorías y ubicaciones de la demostración, creadas desde **Administración** (paso 7) con estos nombres exactos: categorías `Redes`, `Hardware`, `Correo` e `Impresoras`; ubicaciones `Suc Lo Marcoleta` y `Suc Manuel Antonio Matta`.

**Qué crea**

- Tickets escritos como los escribiría gente real y poco técnica: títulos vagos («no puedo abrir el excel», «el wifi!!!!»), prisa, faltas de tilde, prioridades exageradas y, a veces, el problema equivocado (alguien dice «no tengo internet» y era un cable suelto). Otros los registra el personal a nombre de alguien, con un tono más ordenado.
- Un reparto realista: cerca de un 70 % lo crean Solicitantes y el resto el personal (con 0, 1 o 2 solicitantes); hay tickets en las cuatro categorías y en `Sin clasificar` (el usuario no siempre sabe elegir), en las cuatro prioridades, en ambas ubicaciones y algunos sin ubicación.
- Ocho tickets tienen además una historia posterior hecha por el personal: reclasificaciones, cambios de prioridad con motivo y títulos corregidos tras hablar con la persona. Quedan en el historial como en la aplicación real (el Solicitante ve qué cambió, pero no el motivo).
- Otros catorce, al final de la lista, ya han avanzado en el flujo (seis de ellos con grupo y técnicos asignados, uno solo con grupo y otro con dos técnicos). Los ocho primeros de ese bloque: quedan **En progreso** o **En espera**, con los cinco motivos de espera (uno con un texto libre) y un ticket que completó el ciclo iniciar, esperar y reactivar. El Solicitante ve que el ticket está en espera, pero no el motivo.
- Otros cuatro, también al final, muestran cambios de solicitantes después de crear el ticket: uno en el que el personal se equivocó de persona y la cambia por la correcta (con el motivo del retiro), uno que nació sin solicitante y al que después se agrega el jefe de bodega, uno al que se suma una segunda persona que luego se retira, y uno que creó un Solicitante a nombre de un colega: se le retira como solicitante pero, como lo creó, lo sigue viendo. Estos cambios son eventos internos del historial: el Solicitante no los ve.
- Otros cinco, al final de todo, tienen una conversación: respuestas del personal, comentarios del propio Solicitante y notas internas (un ticket con dos notas del equipo y un solo comentario público, para ver lo poco que ve el Solicitante). El Solicitante ve la conversación pública; las notas internas, solo el personal.
- Dos más, también al final, con archivos adjuntos reales (de texto: un registro de errores de un Solicitante, un diagnóstico del equipo y una lista `.csv` del ticket), guardados en `instance/uploads`. Así se puede probar la descarga y comprobar que los archivos de una nota interna no los ve el Solicitante.
- Siete más, al final de todo, recorren la resolución y el cierre: uno **Resuelto** esperando que la solicitante lo confirme (ella ve el aviso «¿Tu solicitud quedó resuelta?»), uno que la solicitante **confirmó** y se cerró con el motivo «Resolución validada», uno que la solicitante **rechazó** («Sigo sin poder entrar...») y que el técnico resolvió por segunda vez, un **cierre directo** sin solicitante (una mantención rutinaria), una **cancelación** (cierre directo con ese motivo), uno **Resuelto sin solicitante** que cerró un Supervisor con un **cierre excepcional** y uno que se cerró y el personal **reabrió** porque el problema volvió. Así la pestaña **Cerrados** tiene tickets y se puede probar cada camino.
- Cuatro más, al final de todo, con **duplicados y relaciones**: dos tickets de la bodega que repiten el del wifi (el personal los marca como duplicados y se cierran con el motivo «Duplicado», dejando al ticket del wifi como principal de ambos) y dos tickets que el personal relaciona con otros sin ser duplicados (una impresora y el wifi de la sala de reuniones). Solo el personal ve las relaciones.
- Fechas repartidas hasta unas nueve semanas atrás, **relativas al día en que lo ejecutes** y medidas en **tiempo laboral**: «hace 3 días» son tres días laborales antes de hoy, cada ticket se crea dentro de la jornada y los pasos posteriores del personal avanzan en horas laborales (el reloj salta noches, fines de semana y feriados). La jornada es la del calendario laboral vigente: el que guarde el Administrador en **Administración → SLA** o, si no hay ninguno, el de por defecto (lunes a viernes de 09:00 a 18:00, que se define en `DEMO_CALENDAR`, en `src/workdesk/worktime.py`). Nada queda fuera de ese calendario ni en el futuro, y si lo ejecutas un fin de semana, cuenta desde el último día laboral. Así los filtros por fecha y «Recién actualizados» se ven vivos en cualquier demostración.

**Cómo se comporta**

- **Puedes ejecutarlo de nuevo cuando quieras y no duplica nada.** Cada ticket de la lista tiene una `clave` estable, así que los que ya existen no se vuelven a crear: se **refrescan**. Sus fechas (creación, historial, solicitantes y última modificación) se recalculan respecto del día en que lo ejecutas, de modo que la demostración siempre parece reciente. Responde `Tickets demo creados: 0. Actualizados (ya existían): 76.`
- Un ticket demo se reconoce aunque después le cambien el título. Si lo editaste a mano mientras probabas, esa edición se desplaza junto con el ticket para que el historial siga en orden y nada quede en el futuro. El contenido (título, descripción, categoría, prioridad...) no se sobrescribe, y los tickets que creaste a mano no se tocan nunca.
- No crea categorías ni ubicaciones. Si falta alguna, usa `Sin clasificar` o deja el ticket sin ubicación, y te avisa con un mensaje `Aviso:`.
- Si falta `seed-demo` o `seed-catalogs`, se detiene con un mensaje que dice qué ejecutar primero y no carga nada. Si algo falla a mitad de la carga, se revierte todo.
- Se niega a ejecutarse con `APP_ENV=production`.
- Los tickets que no avanzaron en el flujo quedan en `Nuevo`. Los de la resolución y el cierre quedan Resueltos o Cerrados, así que la pestaña **Cerrados** tiene contenido. El comando necesita que `seed-catalogs` haya cargado las transiciones entre estados y los tipos de relación: si cargaste los catálogos antes de esta versión, ejecútalo de nuevo (no duplica nada).

**Cómo mejorarlo.** Los textos están separados de la lógica: para cambiar un título, una prioridad o la antigüedad de un ticket, o para añadir más, se edita la lista de [`src/workdesk/seeds/demo_tickets_data.py`](src/workdesk/seeds/demo_tickets_data.py) sin tocar el código que los carga. En el mismo archivo, `DEMO_CALENDAR` define los días laborales, la jornada y los feriados con los que se fechan los tickets (las horas de creación deben caer dentro de la jornada). Al volver a ejecutar el comando, los tickets ya cargados solo refrescan sus fechas: un cambio de texto, categoría o prioridad en la lista se ve en los tickets **nuevos** (los que tengan otra `clave`), pero no en los ya cargados. Para ver esos cambios en tickets existentes, recrea la base de desarrollo y vuelve a cargar los datos. Una vez cargado un ticket, no cambies su `clave`: es lo que lo identifica.

**Empezar de cero.** Recrear la base **borra todo lo que contiene** (usuarios, categorías, tickets...), así que hazlo solo en tu entorno de prueba. Detén WorkDesk (`Ctrl+C`) y, desde la consola de PostgreSQL como `postgres` (ver [Configuración de PostgreSQL](#configuración-de-postgresql)), ejecuta:

```sql
DROP DATABASE workdesk_dev;
CREATE DATABASE workdesk_dev OWNER workdesk_app;
```

Después repite la [preparación inicial](#preparación-inicial) desde el paso 1. `DROP DATABASE` falla si queda alguna conexión abierta: cierra WorkDesk y cualquier herramienta (pgAdmin, `psql`) conectada a esa base.

### Usuarios de demostración

`seed-demo` crea estas cuentas, todas con la contraseña que escribiste al ejecutarlo. El username es lo que se escribe en el login.

| Rol | Usernames |
| --- | --- |
| Supervisor | `camila.rojas`, `matias.fuentes` |
| Técnico | `diego.soto`, `valentina.pizarro`, `felipe.araya`, `francisca.munoz` |
| Solicitante | `javiera.torres`, `sebastian.vargas`, `constanza.herrera`, `ignacio.molina`, `paula.contreras`, `andres.silva` |

Tu cuenta de Administrador es la que creaste con `create-admin`. Para cambiar de usuario, cierra la sesión desde el menú del avatar (arriba a la derecha).

### 1. Como Administrador

1. Inicia sesión. La barra lateral muestra **Dashboard**, **Tickets**, **Crear ticket**, **Administración** y **Mi cuenta**.
2. **Crear ticket:** envía el formulario incompleto (por ejemplo, solo con el título). Cada campo obligatorio que falta muestra su error y el formulario conserva lo que ya habías escrito. Luego créalo bien, marcando dos solicitantes (el buscador filtra la lista). Debes ver el aviso `Ticket #N creado correctamente.` y el detalle con estado `Nuevo`, el creador y los solicitantes.
3. **Tickets:** comprueba las pestañas **Todos**, **Abiertos** y **Cerrados** con sus contadores. Con los tickets de demostración verás `Todos 76`, `Abiertos 70` y `Cerrados 6` (más los que hayas creado tú) y cuatro páginas de 20; al cambiar de página se conserva lo que hayas filtrado.
4. **Buscar:** escribe `impresora`: con los tickets de demostración aparecen doce, porque la palabra está en títulos y en descripciones. Escribe `#7` y aparece solo el ticket 7. El buscador de la barra superior hace lo mismo.
5. **Filtrar y ordenar:** filtra por estado y por prioridad, abre **Más filtros** (categoría, ubicación y fechas) y combínalos con la búsqueda. **Limpiar filtros** los quita. Cambia **Ordenar por** a `Mayor prioridad primero`.
6. **Editar:** abre un ticket y pulsa **Editar**. Cambia el título y guarda: aparece `Ticket #N actualizado.` y el historial muestra `Título: «antes» → «después»`. Vuelve a guardar sin tocar nada: `No había cambios que guardar.`
7. **Cambiar prioridad:** pulsa **Cambiar prioridad**. Sin motivo, el formulario lo rechaza. Con un motivo, el historial muestra el cambio y `Motivo: ...`.
8. **Ediciones simultáneas:** abre el mismo ticket en dos pestañas del navegador (A y B) y pulsa **Editar** en ambas. Guarda en A. Al guardar en B aparece `Otra persona modificó este ticket mientras lo editabas...` y el formulario se recarga con los datos de A, sin pisar su cambio.
9. **Una historia con varias manos:** busca `bodega sin red` y abre ese ticket. Empezó como «se cayo el sistema», que una persona de la bodega clasificó como `Sin clasificar` con prioridad `Crítica`. En el historial verás cómo una técnica lo reclasificó a `Redes`, bajó la prioridad a `Alta` explicando el motivo (que tú, como personal, ves) y otro técnico corrigió el título. Es lo que ocurre en un soporte real: lo que se pide no siempre es el problema.
10. **Catálogos:** en **Administración → Categorías**, desactiva una categoría que ya usan tickets. Esos tickets la conservan, pero ya no aparece en **Crear ticket**. Reactívala cuando quieras.
11. **Grupos:** en **Administración → Grupos** ves los tres grupos de demostración (si ejecutaste `seed-demo`). Crea uno nuevo, ábrelo y designa a un supervisor responsable y agrega técnicos con los selectores de cada tarjeta. Prueba **Editar**, **Desactivar** (un grupo desactivado no admite cambios de técnicos ni de responsables) y **Reactivar**.
12. **Estados y transiciones:** en **Administración → Estados y transiciones** ves los seis estados con cuántos tickets hay en cada uno. Pulsa **Editar** en `En progreso`, cámbiale el nombre a `En curso` y guarda: el nuevo nombre aparece en el listado, el detalle y los botones, pero el historial de los tickets que ya pasaron por ahí conserva el que tenía entonces. Prueba a ponerle a otro estado un nombre que ya existe: lo rechaza. Más abajo están las transiciones, agrupadas por estado de origen, con quién ejecuta cada una. Algunas llevan la etiqueta **Protegida** (pasa el cursor para ver por qué): por ejemplo, confirmar la solución no se puede deshabilitar. Deshabilita **Iniciar trabajo** desde `Nuevo`: pide confirmación y, desde ahora, ese botón no se ofrece a los tickets `Nuevo`. Fíjate en el mismo botón desde `Asignado`: ahora aparece como **Protegida**, porque deshabilitarlo también dejaría `En progreso` sin camino de entrada desde `Nuevo`. Vuelve a habilitar la primera con **Habilitar**. Cada cambio queda registrado en la auditoría administrativa (la pantalla para consultarla llega más adelante).
13. **Calendario laboral:** en **Administración → SLA** ves el calendario laboral. Mientras no hayas guardado ninguno dice **Por defecto (sin configurar)**: lunes a viernes de 09:00 a 18:00, sin feriados. Pulsa **Configurar calendario**. El horario de cada día es un texto: déjale al viernes `09:00-17:00` y escribe en el sábado `10:00-12:00`; si quieres una pausa de almuerzo, usa `09:00-13:00, 14:00-18:00`. En **Feriados** escribe uno por línea, por ejemplo `25-12-2026 Navidad` (también vale `2026-12-25`). Guarda: la pantalla pasa a decir **Configurado · versión 1** y resume el horario («Lunes a jueves · 09:00–18:00», «Viernes · 09:00–17:00»…). Vuelve a configurarlo, cambia una hora y guarda: ahora hay una **versión 2** y la 1 queda en la tabla de versiones como **Anterior**, tal como se guardó. Prueba a escribir `mañana` en un día, una hora de fin anterior a la de inicio, dos franjas que se solapan o un feriado sin nombre: cada error aparece junto a su campo y lo escrito no se pierde. Para ver el control de versiones, abre **Configurar calendario** en dos pestañas, guarda en una y luego en la otra: la segunda avisa de que otra persona guardó mientras editabas y no pisa el cambio. Si no cambias nada y guardas, avisa de que no hay cambios y no crea una versión. Si ejecutas `seed-demo-tickets` de nuevo con un calendario guardado, las fechas de los tickets de demostración respetan sus franjas y sus feriados.

### 2. Como Solicitante

Cierra la sesión y entra, por ejemplo, como `paula.contreras`.

1. La barra lateral muestra **Dashboard**, **Mis tickets**, **Crear ticket** y **Mi cuenta**; no hay Administración.
2. **Mis tickets** lista solo los tickets que creó o donde figura como solicitante: con los datos de demostración, `paula.contreras` ve 12 (los 10 que escribió, uno que registró el personal a su nombre y otro en el que el personal la agregó como solicitante). Compáralo con lo que veías como Administrador.
3. Abre uno: ves la descripción, el resumen y el historial, pero no "Creado por" ni los solicitantes, y no hay botones **Editar**, **Cambiar prioridad** ni de cambio de estado.
4. Entra como `ignacio.molina`, busca `bodega sin red` y ábrelo: el historial muestra qué cambió (la categoría, la prioridad y el título) pero **no el motivo** de la prioridad, que solo ve el personal.
5. En la barra de direcciones, cambia el número por el de un ticket de otra persona (`/tickets/N`): aparece **Página no encontrada** (404), igual que con un número que no existe (`/tickets/9999`). No se puede deducir qué tickets existen.
6. Abre `/tickets/N/edit` con el número de un ticket propio: aparece **Acceso denegado** (403). Lo mismo con `/admin`.
7. **Crear ticket:** no hay sección de solicitantes; al crearlo, quedas registrado como su solicitante.
8. Abre un ticket tuyo: no ves **Gestionar** ni a los demás solicitantes, y `/tickets/N/requesters` responde **Acceso denegado** (403). Decidir quiénes más figuran en un ticket es del personal.
9. **Comentar:** en la tarjeta **Actividad** de un ticket tuyo escribe un comentario y pulsa **Publicar**: aparece con tu nombre, tu rol y la hora. No hay selector de tipo: un Solicitante escribe siempre comentarios públicos. Mientras pasen menos de 30 minutos (`COMMENT_EDIT_WINDOW_MINUTES`) ves **Editar** y **Eliminar** en los tuyos; después, ya no. Abre `intranet-credenciales` (`sebastian.vargas` es su creador): ves la conversación con soporte, pero ni rastro de las notas internas del equipo.
10. **Adjuntar:** en tu ticket puedes subir archivos (tarjeta **Archivos**) o adjuntarlos a un comentario (**Adjuntar archivos (opcional)**). Ves y descargas los tuyos y los del equipo en comentarios públicos, pero no los de una nota interna.
11. **Validar una solución:** abre `el lector de huella de la entrada no me reconoce` (es de `paula.contreras`, está Resuelto). Arriba aparece **«¿Tu solicitud quedó resuelta?»** y, en la tarjeta **Resolución**, lo que escribió el técnico. Pulsa **No, necesito más ayuda**: te pide explicar qué falta (sin texto no avanza); al enviar, el ticket vuelve a **En progreso** y el historial muestra tu motivo. Como técnico, vuelve a resolverlo; entra otra vez como `paula.contreras` y pulsa **Sí, está resuelto**: el ticket queda **Cerrado**, el resumen indica la fecha y el motivo «Resolución validada», y aparece **Reabrir ticket** (lo tienes disponible durante `REOPEN_WINDOW_DAYS` días desde el cierre; después, `/tickets/N/status/reopen` responde **Acceso denegado**). Tampoco puedes resolver ni cerrar tickets: `/tickets/N/status/resolve` y `/tickets/N/status/close` responden 403.
12. **Relaciones:** abre `otra vez sin wifi en la bodega` (`ignacio.molina`): está Cerrado con el motivo «Duplicado», pero no ves de qué ticket es duplicado ni hay tarjeta de **Relaciones**. `/tickets/N/relations` y `/tickets/N/duplicate` responden **Acceso denegado** (403): las relaciones las gestiona el personal.

### 3. Como Técnico

Entra, por ejemplo, como `diego.soto`.

1. **Tickets** muestra todos los tickets (con los datos de demostración, los 76), incluidos los que crearon otras personas.
2. Puede abrir y editar cualquier ticket y cambiar su prioridad con motivo.
3. **Cambiar el estado:** abre un ticket `Nuevo` y pulsa **Iniciar trabajo**: una pantalla de confirmación muestra `Nuevo → En progreso`; al confirmar, el ticket queda **En progreso** y el historial registra `Estado: «Nuevo» → «En progreso»`. Ahora el botón es **Poner en espera**: elige un motivo (por ejemplo `Otro motivo`, que permite escribir una explicación) y confirma. En el historial, tú ves `Motivo de espera: ...`; el Solicitante ve solo el cambio de estado. Pulsa **Reactivar** para volver a En progreso.
4. Prueba el aviso de conflicto: abre un ticket en dos pestañas (A y B) y pulsa **Iniciar trabajo** en ambas. Confirma en A; al confirmar en B aparece `Otra persona modificó este ticket mientras decidías...`.
5. **Asignarte un ticket:** abre un ticket `Nuevo` y pulsa **Asignarme**: queda **Asignado**, el resumen muestra tu nombre en **Técnico** y el historial registra `Técnico asignado` y el cambio de estado. El botón pasa a **Dejar ticket**; púlsalo y el ticket vuelve a `Nuevo`. Como técnico no ves **Asignar** ni **Escalar**: `/tickets/N/assignment` responde **Acceso denegado**.
6. **Solicitantes:** en el resumen de un ticket abierto, junto a **Solicitante(s)**, pulsa **Gestionar**. Agrega a otra persona con el selector (aparecen solo las personas activas con rol Solicitante que aún no lo son) y retírala con **Retirar**: pide confirmación y un motivo opcional, y avisa si la persona dejará de ver el ticket. El historial registra `Solicitante agregado` y `Solicitante retirado` (con el motivo), que solo ve el personal. Abre `Proyector de la sala chica no muestra imagen`: ahí se cambió a Constanza por Paula. Entra como `constanza.herrera`: ese ticket ya no aparece y su dirección responde **404**; en cambio `la impresora de proyectos dice error de conexion`, que ella creó, lo sigue viendo aunque el personal la retiró como solicitante (el creador original no cambia).
7. **Comentarios y notas internas:** en la tarjeta **Actividad** escribe un comentario público y luego una **nota interna** (el selector **Tipo** solo lo ve el personal). La nota aparece con fondo morado, `NOTA INTERNA` y «Solo visible para soporte». Edita el comentario que acabas de escribir (**Editar** guarda el texto anterior en el historial, que no lo muestra) y elimínalo (**Eliminar** pide confirmación y lo oculta para todos). Ni editar ni eliminar cambian «Actualizado». Abre `switch-bodega-puertos`: tiene dos notas del equipo y un comentario público; entra después como `ignacio.molina` y comprueba que solo ve el comentario y que `Actividad` cuenta uno, no tres.
8. **Archivos adjuntos:** en la tarjeta **Archivos** pulsa **Elegir archivos**, selecciona uno o varios (por ejemplo un `.pdf` o `.png` pequeño) y pulsa **Subir**: aparecen con su tamaño, quién y cuándo; el nombre es un enlace que lo **descarga** (siempre como descarga, nunca se abre en el navegador). Prueba un `.exe` o un archivo con la extensión cambiada a mano (un `.txt` renombrado a `.png`): se rechaza con un aviso y no se guarda nada. Escribe una **nota interna** y adjúntale un archivo: lo ve el personal, pero para el Solicitante no existe ni su descarga (404). Elimina un archivo con **Eliminar**: deja de verse y de descargarse, pero se conserva en `instance/uploads`. Abre `error-sistema-contable-log` para ver archivos de ejemplo (de un Solicitante y del equipo).
9. **Resolver, cerrar y reabrir:** abre un ticket en curso. Además de los botones de estado ves **Resolver** y **Cerrar ticket**. **Resolver** pide una explicación de la solución (opcional): el ticket queda **Resuelto** y espera al solicitante; tú no puedes confirmar por él (`/tickets/N/status/confirm` responde **Acceso denegado**). **Cerrar ticket** lo cierra sin pasar por Resuelto y deja elegir el motivo: **Cierre directo** o **Cancelación** (no hay un estado «Cancelado»). En un ticket cerrado, el resumen muestra cuándo y por qué se cerró y solo queda **Reabrir ticket**, que lo devuelve a **En progreso** conservando a los técnicos. Abre `impresora-contratos-rayas` (`la impresora de contratos imprime con rayas`): se cerró, se reabrió y el historial cuenta cada paso. Un Técnico no ve **Cierre excepcional**: `/tickets/N/status/close-exceptional` responde 403.
10. **Relaciones y duplicados:** abre `el wifi de la bodega se cae todo el dia`: la tarjeta **Relaciones (2)** muestra sus dos duplicados («Su duplicado»). Abre uno (`otra vez sin wifi en la bodega`): está Cerrado con el motivo «Duplicado» y la tarjeta dice «Duplicado de». Para probarlo tú, abre un ticket en curso, pulsa **Gestionar** en **Relaciones** y relaciónalo con otro por su número (`12` o `#12`): aparece en los dos tickets, y puedes **Quitar** la relación (pide confirmación). Con **Marcar como duplicado** escribes el número del ticket principal: el ticket se cierra con el motivo «Duplicado» y queda vinculado. No se puede relacionar un ticket consigo mismo ni repetir una relación (tampoco al revés), ni marcar como duplicado de otro que ya es un duplicado; un ticket Resuelto no se cierra así. La relación de un duplicado cerrado no se quita: si lo reabres, sí.
11. **Bloqueo de edición:** necesitas dos usuarios del personal a la vez (por ejemplo, un navegador normal y una ventana de incógnito: `diego.soto` y `camila.rojas`). Con `diego.soto` abre un ticket y pulsa **Editar**: la pantalla avisa de que el ticket queda reservado. Con `camila.rojas` abre el mismo ticket: ves **«Diego Soto está editando este ticket»** y, si pulsas **Editar** (o **Cambiar prioridad**), una pantalla de solo lectura con quién edita y hasta cuándo; no puedes editar. Cuando `diego.soto` guarda o pulsa **Cancelar**, `camila.rojas` ya puede editar (pulsa **Volver a intentar**). Si `diego.soto` cierra la pestaña sin guardar, el bloqueo se libera al salir; si apagas la conexión, expira solo a los 2 minutos (`EDIT_LOCK_TTL_SECONDS`). Los cambios de estado, la asignación y los comentarios no se bloquean. Con el mismo usuario en dos pestañas el bloqueo es compartido, y la versión del ticket sigue avisando si guardas sobre un cambio ajeno.
12. No ve **Administración**; `/admin` responde **Acceso denegado**.

### 4. Como Supervisor

Entra, por ejemplo, como `camila.rojas` (o `matias.fuentes`).

1. La barra lateral muestra la opción **Grupos**. No hay Administración.
2. **Grupos** lista solo los grupos de los que eres responsable: `camila.rojas` ve Soporte Redes y Aplicaciones; `matias.fuentes`, Soporte Usuarios y Aplicaciones. Cambia el número en la URL (`/groups/N`) por el de un grupo del que no eres responsable: **Página no encontrada** (404).
3. Abre un grupo tuyo: ves a los técnicos y a los responsables. **Agrega un técnico** con el selector y **retíralo** (con un motivo opcional). No hay **Editar**, **Desactivar** ni selector para designar responsables, y abrir `/groups/N/edit` responde **Acceso denegado** (403).
4. Como Administrador, retira a este supervisor del grupo y vuelve a entrar como él: el grupo ya no aparece y su dirección responde 404.
5. Como Administrador, cambia el rol de un técnico de un grupo (o desactívalo): en el grupo ya no figura como miembro, y la auditoría registra el cierre con el motivo.

**Asignar y escalar tickets.** Abre un ticket y pulsa **Asignar** (no ves **Asignarme**: solo un Técnico se asigna a sí mismo). En la pantalla asigna a un técnico, asigna a un segundo, quita a uno y elige un grupo con **Guardar grupo**. Luego pulsa **Escalar**: elige otro grupo y/u otro técnico y escribe el motivo; sin motivo, o sin cambiar nada, el formulario lo rechaza. En el historial verás `Ticket escalado` con el grupo y los técnicos de antes y de después, y el motivo. Como Solicitante, abre ese mismo ticket: ves **Atendido por** con el técnico actual, pero ni el grupo ni el escalamiento.

**Cierre excepcional.** Abre `Actualización de antivirus en los notebooks de la bodega` (Resuelto y sin solicitante, así que nadie puede confirmarlo) o cualquier ticket Resuelto: ves **Cierre excepcional**, que pide un motivo obligatorio y cierra el ticket con el motivo «Cierre excepcional». Es una decisión del Supervisor y el Administrador; el historial la marca como excepcional y el texto lo ve solo el personal.

Un Técnico o un Solicitante que abre `/groups` recibe **Acceso denegado**: pertenecer a un grupo no cambia lo que ve ni lo que hace.

### Lo que todavía no verás

- No hay cierre automático de un ticket Resuelto que nadie valida: llega con el planificador (`v0.5.0`). Mientras tanto, un ticket Resuelto sin solicitante lo cierra un Supervisor con el cierre excepcional.
- Todavía no hay la advertencia de posibles duplicados al crear un ticket.
- El aviso de quién edita no se actualiza solo: aparece al abrir o recargar la pantalla (la actualización en tiempo real es posterior al MVP).
- La pantalla de Estados y transiciones cambia el nombre, la descripción y las transiciones; el color y el orden de los estados no se editan todavía (llegan con el pulido visual, `v0.9.0`).
- El detalle de un ticket muestra sus secciones (actividad, archivos, relaciones e historial) una debajo de otra; las pestañas llegan con el pulido visual.
- Los límites (plazo para editar comentarios, plazo de reapertura, tamaño y cantidad de archivos, tiempos del bloqueo de edición) se cambian en el `.env`, no desde la interfaz: pasan a la configuración administrable en `v0.7.0`.
- El dashboard es una pantalla temporal.

---

## Solución de problemas

| Síntoma | Causa probable | Qué hacer |
| --- | --- | --- |
| `Falta configuración obligatoria: SECRET_KEY` (o `SQLALCHEMY_DATABASE_URI`) | `.env` no existe, no está en la raíz del proyecto o tiene la variable vacía. `SQLALCHEMY_DATABASE_URI` se toma de `DATABASE_URL`. | Comprueba que `.env` está junto a `README.md` y que `SECRET_KEY` y `DATABASE_URL` tienen valor. |
| `Connection refused`, `connection failed` o "se rechazó la conexión" | PostgreSQL no está en ejecución, o escucha en otro puerto. | Inicia el servicio (en Windows: **Servicios** → `postgresql-x64-18`, donde el número es la versión → **Iniciar**) y revisa el puerto de `DATABASE_URL`. |
| `password authentication failed for user "workdesk_app"` | La contraseña de `DATABASE_URL` no es la del rol, o tiene símbolos sin codificar. | Revísala (ver [Variables de entorno](#variables-de-entorno)) o cámbiala con `ALTER ROLE workdesk_app WITH PASSWORD 'nueva';` desde la consola de PostgreSQL. |
| `database "workdesk_dev" does not exist` | La base no se creó, o el nombre al final de la dirección no coincide. | Créala como se explica en [Configuración de PostgreSQL](#configuración-de-postgresql). |
| `permission denied for schema public` al migrar | La base no pertenece a `workdesk_app`. | Desde la consola de PostgreSQL: `ALTER DATABASE workdesk_dev OWNER TO workdesk_app;` |
| `relation "usuarios" does not exist` (o "no existe la relación") | Faltan las migraciones. | Ejecuta `python -m flask --app src.workdesk db upgrade`. |
| `ModuleNotFoundError: No module named 'flask'` | El entorno virtual no está activo o no se instalaron las dependencias. | Actívalo (ver [Instalación](#instalación)) y ejecuta `python -m pip install -r requirements-dev.txt`. |
| `Could not import 'src.workdesk'` o `No module named 'src'` | Estás fuera de la raíz del proyecto. | Entra con `cd` en la carpeta que contiene `src/` y `README.md`. |
| PowerShell: "la ejecución de scripts está deshabilitada en este sistema" | Política de ejecución de PowerShell. | Mira el paso 2 de la [Instalación](#instalación). |
| `psql` no se reconoce | La carpeta `bin` de PostgreSQL no está en el `PATH`. | Usa **SQL Shell (psql)** desde el menú Inicio o pgAdmin, o añade esa carpeta al `PATH`. |
| `create-admin`: "No existe el rol ADMINISTRADOR. Ejecuta primero el comando seed-roles." | Se saltó el paso 2 de la preparación. | Ejecuta `seed-roles` y vuelve a intentarlo. |
| `seed-demo-tickets`: "Faltan usuarios de demostración... Ejecuta primero seed-demo." | Todavía no cargaste el equipo de demostración. | Ejecuta `seed-demo` y vuelve a intentarlo. No se cargó ningún ticket. |
| `seed-demo-tickets`: "Faltan los catálogos iniciales. Ejecuta primero seed-catalogs." o "Faltan las transiciones de estado..." | Se saltó el paso 3 de la preparación, o los catálogos se cargaron antes de que existieran las transiciones entre estados. | Ejecuta `seed-catalogs` (no duplica nada) y vuelve a intentarlo. |
| `seed-demo-tickets`: "Hay transiciones deshabilitadas que la demostración necesita..." | Un Administrador deshabilitó una transición que los tickets de demostración recorren. | Habilítala en **Administración → Estados y transiciones** y vuelve a intentarlo. No se cargó ningún ticket. |
| `seed-demo-tickets` termina con `Aviso: Categoría «...» no encontrada` (o `Ubicación`) | La categoría o ubicación no existe con ese nombre exacto. | Los tickets se cargaron igual, con `Sin clasificar` o sin ubicación. Para corregirlo, crea el valor con el nombre exacto ([Configurar categorías y ubicaciones](#configurar-categorías-y-ubicaciones)) y recrea la base de desarrollo, o edita esos tickets a mano. |
| `seed-demo-tickets` dice "Creados: 0. Actualizados (ya existían): 76" | Ya los habías cargado: el comando no duplica, solo refresca sus fechas respecto de hoy. | Es lo esperado. |
| `create-admin`: "Ya existe un usuario con rol ADMINISTRADOR." | El comando solo crea el Administrador inicial. | Entra con esa cuenta; los demás usuarios se crean en **Administración → Usuarios**. |
| Siempre aparece "Usuario o contraseña incorrectos." aunque los datos sean correctos | Tras 5 intentos fallidos la cuenta se bloquea 15 minutos, y el mensaje es el mismo a propósito para no revelar nada. | Espera esos 15 minutos (`LOGIN_LOCK_MINUTES`). Si es otra persona, un Administrador puede restablecerle la contraseña y eso levanta el bloqueo. |
| "Tu sesión expiró. Inicia sesión nuevamente." | Pasaron 30 minutos sin actividad o 8 horas desde que iniciaste sesión. | Es el comportamiento esperado; se ajusta con `SESSION_IDLE_MINUTES` y `SESSION_MAX_HOURS`. |
| Inicias sesión y vuelves a ver el login | Con `SESSION_COOKIE_SECURE=true` y HTTP, algunos navegadores no guardan la cookie de sesión. | En local usa `SESSION_COOKIE_SECURE=false` y reinicia WorkDesk. |
| En **Crear ticket** solo aparece `Sin clasificar` como categoría | Todavía no se crearon categorías. | **Administración → Categorías → Nueva categoría** (ver [Configurar categorías y ubicaciones](#configurar-categorías-y-ubicaciones)). |
| Las fechas aparecen en hora UTC | `APP_TIMEZONE` no es un nombre de zona válido. | Usa un nombre IANA, como `America/Santiago`, y reinicia WorkDesk. |
| El puerto 5000 está ocupado | Otro programa lo usa (en macOS, AirPlay). | Añade `--port 5001` al comando de arranque. |
| Tests: "Falta TEST_DATABASE_URL para ejecutar los tests." | `.env` no define `TEST_DATABASE_URL`. | Defínela apuntando a `workdesk_test`. |
| Tests: "Los tests solo pueden ejecutarse sobre workdesk_test." | `TEST_DATABASE_URL` apunta a otra base. | Corrígela. La protección es intencional: protege `workdesk_dev`. |
| Tests que fallan al azar con tablas que "no existen" | Hay dos ejecuciones de `pytest` a la vez sobre `workdesk_test`. | Ejecuta una sola cada vez: comparten la misma base y cada una recrea sus tablas. |

---

## Rutas actuales

Rutas registradas actualmente:

```text
GET       /
GET POST  /login
POST      /logout
GET       /dashboard
GET POST  /account
GET POST  /account/password
GET       /admin
GET       /users
GET POST  /users/new
GET       /users/<id>
GET POST  /users/<id>/edit
GET POST  /users/<id>/role
GET POST  /users/<id>/deactivate
GET POST  /users/<id>/activate
GET POST  /users/<id>/reset-password
GET       /admin/categories
GET POST  /admin/categories/new
GET POST  /admin/categories/<id>/edit
GET POST  /admin/categories/<id>/deactivate
GET POST  /admin/categories/<id>/activate
GET       /admin/priorities
GET POST  /admin/priorities/<id>/edit
GET POST  /admin/priorities/<id>/deactivate
GET POST  /admin/priorities/<id>/activate
GET       /admin/locations
GET POST  /admin/locations/new
GET POST  /admin/locations/<id>/edit
GET POST  /admin/locations/<id>/deactivate
GET POST  /admin/locations/<id>/activate
GET       /admin/wait-reasons
GET POST  /admin/wait-reasons/new
GET POST  /admin/wait-reasons/<id>/edit
GET POST  /admin/wait-reasons/<id>/deactivate
GET POST  /admin/wait-reasons/<id>/activate
GET       /admin/states
GET POST  /admin/states/<id>/edit
GET POST  /admin/transitions/<id>/deactivate
GET POST  /admin/transitions/<id>/activate
GET       /groups
GET POST  /groups/new
GET       /groups/<id>
GET POST  /groups/<id>/edit
GET POST  /groups/<id>/deactivate
GET POST  /groups/<id>/activate
POST      /groups/<id>/members/add
GET POST  /groups/<id>/members/<membership_id>/remove
POST      /groups/<id>/supervisors/add
GET POST  /groups/<id>/supervisors/<designation_id>/remove
GET       /tickets
GET POST  /tickets/new
GET       /tickets/<public_id>
GET POST  /tickets/<public_id>/edit
GET POST  /tickets/<public_id>/priority
GET POST  /tickets/<public_id>/status/<action_slug>
POST      /tickets/<public_id>/assign-me
POST      /tickets/<public_id>/unassign-me
GET       /tickets/<public_id>/assignment
POST      /tickets/<public_id>/assignment/technicians/add
POST      /tickets/<public_id>/assignment/technicians/<assignment_id>/remove
POST      /tickets/<public_id>/assignment/group
GET POST  /tickets/<public_id>/escalate
GET       /tickets/<public_id>/requesters
POST      /tickets/<public_id>/requesters/add
GET POST  /tickets/<public_id>/requesters/<participation_id>/remove
POST      /tickets/<public_id>/comments
GET POST  /tickets/<public_id>/comments/<comment_id>/edit
GET POST  /tickets/<public_id>/comments/<comment_id>/delete
POST      /tickets/<public_id>/attachments
GET       /tickets/<public_id>/attachments/<attachment_id>/download
GET POST  /tickets/<public_id>/attachments/<attachment_id>/delete
GET       /tickets/<public_id>/relations
POST      /tickets/<public_id>/relations/add
GET POST  /tickets/<public_id>/relations/<relation_id>/remove
GET POST  /tickets/<public_id>/duplicate
POST      /tickets/<public_id>/lock/renew
POST      /tickets/<public_id>/lock/release
GET       /health
```

`/dashboard`, `/tickets` (y todas sus rutas) y `/account/password` requieren una sesión autenticada. `/admin` (incluidas las pantallas de catálogos y de estados y transiciones) y todas las rutas `/users` requieren el rol Administrador; `/groups`, el rol Administrador o Supervisor.

El detalle de un ticket (`/tickets/<public_id>`) lo ve el personal en todos los casos, y el Solicitante solo si creó el ticket o es su solicitante. Si no tiene acceso, la respuesta es un **404** idéntica a la de un ticket inexistente: los números son correlativos y un 403 permitiría descubrir cuáles existen. Las rutas de edición, de prioridad y de solicitantes son solo del personal: quien ve el ticket pero no puede usarlas recibe un **403**. En los comentarios, una nota interna que el usuario no puede ver responde **404** (como si no existiera) y editar o eliminar un comentario ajeno, o uno propio fuera del plazo, responde **403**. Un test recorre todo el mapa de rutas y comprueba estas reglas por rol, así que una ruta nueva queda cubierta sin tocarlo.

Si el usuario tiene una contraseña temporal pendiente de cambio, el sistema solo le permite acceder a `/account/password` y cerrar sesión hasta que la cambie.

La pantalla actual de dashboard es temporal y será reemplazada progresivamente durante la implementación de los módulos funcionales.

---

## Health check

WorkDesk dispone de:

```text
GET /health
```

Cuando la aplicación y PostgreSQL se encuentran disponibles:

```json
{
  "application": "ok",
  "database": "ok",
  "status": "ok"
}
```

con respuesta HTTP:

```text
200 OK
```

Si PostgreSQL no se encuentra disponible, el endpoint responde de manera controlada:

```json
{
  "application": "ok",
  "database": "unavailable",
  "status": "degraded"
}
```

con:

```text
503 Service Unavailable
```

Los detalles técnicos del fallo no se exponen en la respuesta pública.

---

## Autenticación y seguridad actual

La base técnica de autenticación utiliza:

- Login por `username`.
- Contraseñas protegidas mediante Argon2id.
- Flask-Login para gestión de sesión.
- Protección de rutas autenticadas.
- CSRF mediante Flask-WTF.
- Cookie `HttpOnly`.
- `SameSite=Lax`.
- `Secure` configurable según entorno.
- Bloqueo temporal después de intentos fallidos.
- Usuario activo/inactivo.
- Invalidación de sesiones mediante `token_version`.
- Mensajes de autenticación genéricos para evitar revelar información innecesaria.

La autorización basada en roles se comprueba en backend (`security/authorization.py`) y se aplica a las rutas administrativas; la navegación se filtra por rol.

Una red de seguridad automática (`tests/test_route_protection.py`) recorre **todas** las rutas registradas y falla si alguna se puede abrir sin iniciar sesión (salvo las públicas: `/login`, `/health` y los archivos estáticos) o si alguna ruta POST acepta una petición sin token CSRF. Así, una ruta nueva no puede quedar desprotegida por olvido.

---

## Manejo de errores

WorkDesk dispone actualmente de respuestas controladas para:

```text
400 Bad Request
403 Forbidden
404 Not Found
500 Internal Server Error
```

Las páginas de error muestran mensajes comprensibles para el usuario sin exponer stack traces, consultas SQL, credenciales ni detalles internos de infraestructura.

---

## Logging

El logging técnico utiliza el módulo estándar `logging` de Python.

Los archivos se almacenan localmente en:

```text
instance/logs/
```

El archivo principal es:

```text
workdesk.log
```

La configuración predeterminada utiliza rotación por tamaño:

```text
5 MB por archivo
5 backups
```

Estos valores pueden modificarse mediante:

```env
LOG_LEVEL
LOG_MAX_BYTES
LOG_BACKUP_COUNT
```

No deben registrarse contraseñas, claves secretas, cookies, tokens ni URLs de base de datos con credenciales.

---

## Tests

WorkDesk utiliza `pytest`.

La suite dispone actualmente de:

```text
2508 tests
```

Los tests cubren principalmente:

- creación de la aplicación, configuración y manejo de errores;
- health check y conexión PostgreSQL de testing;
- autenticación: login, logout, bloqueo por intentos fallidos, invalidación de sesiones, límites de sesión y Argon2id;
- política de contraseñas, contraseñas temporales y cambio obligatorio;
- autorización por roles y navegación filtrada por rol;
- administración de usuarios (servicio y rutas) y "Mi cuenta";
- auditoría administrativa, incluida su inmutabilidad;
- datos de demostración: el equipo ficticio y los tickets de ejemplo (coherencia de los datos, que no duplica y refresca las fechas al volver a ejecutarlo, fechas relativas en tiempo laboral (días y horas configurables, feriados y fines de semana), ediciones hechas a mano que siguen en orden, historial de sus ajustes, avisos cuando falta una categoría o ubicación y que el historial sigue siendo inmutable);
- catálogos de tickets: datos iniciales, restricciones de base de datos y administración desde la interfaz;
- modelo de tickets: identificador público, solicitantes, historial inmutable y servicio de creación;
- creación y detalle de tickets: políticas de acceso por rol, formulario y sus validaciones, que un Solicitante no pueda registrar otros solicitantes, visibilidad del detalle (404 para lo ajeno) y formato de fechas en hora local;
- listado de tickets: visibilidad por rol aplicada en la consulta (y comprobada contra la política de acceso), búsqueda, pestañas con contadores, filtros, orden, paginación, ausencia de consultas por fila y parámetros inválidos;
- edición de tickets: permisos por rol (403 para quien ve pero no edita), cambios y su historial, valores de catálogo desactivados, tickets cerrados, motivo obligatorio de la prioridad, conflictos entre ediciones simultáneas y qué ve cada rol del historial;
- historial de los tickets: visibilidad por evento (el Solicitante nunca recibe un evento interno, y la condición SQL coincide con la política para todos los roles) y qué cuenta cada evento, sin repetir nunca un motivo;
- grupos, asignación, solicitantes del ticket y bloqueo temporal de edición, incluidas las carreras entre dos personas (pruebas con dos hilos que comprueban que solo una operación prospera);
- estados, transiciones y ciclo de vida: transiciones válidas e inválidas por estado y por rol, resolución, validación del solicitante, cierre directo y excepcional, reapertura y la regla «un ticket cerrado tiene fecha y motivo de cierre»;
- comentarios, notas internas y adjuntos: el filtro por tipo en la consulta, los plazos de edición, los nombres de archivo hostiles, la extensión falsa, los límites de tamaño y la descarga autenticada;
- relaciones y duplicados: el par simétrico, la ausencia de cadenas y ciclos y el cierre del duplicado;
- administración de estados y transiciones: renombrar sin repetir nombres, las transiciones esenciales, que ninguna deshabilitación rompa el flujo (también entre dos Administradores a la vez) y que el catálogo de acciones y las políticas de autorización no se separen;
- seguridad de las rutas: un recorrido automático de todo el mapa de rutas comprueba que cada una exige sesión, que las rutas POST exigen token CSRF y que cada ruta responde según quién la use (404 al ticket ajeno, 403 al rol sin permiso), con pruebas que confirman que ese recorrido realmente detecta una ruta abierta o mal protegida;
- tiempo laboral (`worktime.py`): días y jornadas, franjas distintas por día (una pausa de almuerzo, un martes de un solo minuto, una franja que empieza a medianoche), feriados, medir y sumar tiempo laboral como operaciones inversas, una comparación con un recuento minuto a minuto, fechas en otra zona horaria y un fin de semana con cambio de horario de verano. Son pruebas unitarias: no usan la base de datos;
- calendario laboral administrable: las restricciones de la base de datos (una sola versión vigente, franjas y feriados sin repetir), que guardar crea siempre una versión nueva y deja la anterior intacta, los conflictos entre dos personas (también con dos hilos a la vez), qué se audita, la lectura de los textos del horario y de los feriados, las pantallas (solo el Administrador, cada error junto a su campo, el formulario que conserva lo escrito) y que el seed de demostración respete el calendario guardado.

Para ejecutarlos hacen falta el entorno virtual activo, PostgreSQL en ejecución, la base `workdesk_test` creada y `TEST_DATABASE_URL` definida en `.env` (ver [Configuración de PostgreSQL](#configuración-de-postgresql) y [Variables de entorno](#variables-de-entorno)). No hace falta aplicar migraciones ni cargar datos: la suite crea sus propias tablas.

Ejecutar:

```bash
python -m pytest -q
```

La suite completa tarda varios minutos (unos 24 en el equipo de desarrollo del proyecto), porque cada test parte de una base recién creada. No es un cuelgue.

Ejecuta **una sola vez a la vez**: todas las ejecuciones comparten `workdesk_test` y cada test recrea las tablas, de modo que dos ejecuciones en paralelo se estorban y fallan de forma aleatoria.

Los tests utilizan exclusivamente:

```text
workdesk_test
```

La configuración incorpora una protección adicional para evitar que la suite pueda ejecutarse accidentalmente sobre `workdesk_dev`: si la base de `TEST_DATABASE_URL` no se llama `workdesk_test`, la suite se niega a ejecutarse.

---

## Calidad de código

WorkDesk utiliza Ruff para análisis estático.

Ejecutar:

```bash
ruff check src/workdesk tests
```

El objetivo es mantener el código libre de errores básicos de estilo, imports innecesarios y determinados problemas detectables de forma automática.

Ruff complementa, pero no sustituye, la revisión lógica del código.

---

## Comandos principales

```bash
# Ejecutar aplicación
python -m flask --app src.workdesk run --debug

# Aplicar migraciones
python -m flask --app src.workdesk db upgrade

# Consultar migración actual
python -m flask --app src.workdesk db current

# Verificar cambios pendientes de esquema
python -m flask --app src.workdesk db check

# Cargar roles
python -m flask --app src.workdesk seed-roles

# Cargar catálogos iniciales (estados, prioridades, categoría de respaldo, motivos de cierre y de espera)
python -m flask --app src.workdesk seed-catalogs

# Crear Administrador inicial
python -m flask --app src.workdesk create-admin

# Cargar datos de demostración (opcional)
python -m flask --app src.workdesk seed-demo

# Cargar tickets de demostración (opcional; requiere seed-demo y las categorías de la demo)
python -m flask --app src.workdesk seed-demo-tickets

# Ver rutas
python -m flask --app src.workdesk routes

# Ejecutar tests
python -m pytest -q

# Ejecutar Ruff
ruff check src/workdesk tests
```

---

## Documentación

La documentación técnica, funcional y visual se encuentra en [`docs/`](docs/).

1. [Visión del proyecto](docs/01_vision_del_proyecto.md)
2. [Objetivos](docs/02_objetivos.md)
3. [Roles y permisos](docs/03_roles_y_permisos.md)
4. [Requisitos funcionales](docs/04_requisitos_funcionales.md)
5. [Requisitos no funcionales](docs/05_requisitos_no_funcionales.md)
6. [Reglas de negocio](docs/06_reglas_de_negocio.md)
7. [Casos de uso](docs/07_casos_de_uso.md)
8. [Flujo de tickets](docs/08_flujo_de_tickets.md)
9. [Modelo de datos](docs/09_modelo_de_datos.md)
10. [Arquitectura](docs/10_arquitectura.md)
11. [Diseño de pantallas](docs/11_diseno_de_pantallas.md)
12. [Roadmap](docs/12_roadmap.md)
13. [Evolución posterior al MVP](docs/13_evolucion_post_mvp.md)

---

## Diseño

Los recursos definidos durante la etapa de diseño se encuentran en:

- [`docs/assets/wireframes/`](docs/assets/wireframes/)
- [`docs/assets/mockups/`](docs/assets/mockups/)

Los mockups constituyen la referencia visual para la implementación progresiva del frontend.

Las capturas definitivas del producto reemplazarán progresivamente estas referencias a medida que las pantallas reales sean implementadas.

### Identidad visual

La identidad visual oficial de WorkDesk se encuentra en:

[`src/workdesk/static/img/brand/`](src/workdesk/static/img/brand/)

Los recursos actuales incluyen:

- isotipo principal e inverso;
- logotipo horizontal principal e inverso;
- composición específica para la pantalla de login;
- favicon SVG, ICO y PNG;
- iconos de aplicación en 192 × 192 y 512 × 512;
- icono `maskable` de 512 × 512;
- `apple-touch-icon`;
- imagen de presentación `workdesk-social-preview.png`.

La interfaz actual utiliza la variante para tema claro. Las variantes inversas quedan preparadas para una futura implementación de modo oscuro.

Los favicons se encuentran integrados en los templates actuales de login, dashboard y páginas de error.

---

## Roadmap

El desarrollo se realiza mediante incrementos funcionales:

```text
v0.1.0  Fundación técnica
v0.2.0  Usuarios, autenticación completa y RBAC
v0.3.0  Núcleo de tickets
v0.4.0  Asignación, colaboración y ciclo de vida
v0.5.0  SLA y notificaciones
v0.6.0  Dashboards y carga de trabajo
v0.7.0  Administración y conocimiento
v0.8.0  Reportes, auditoría y backups
v0.9.0  Estabilización y UX
v1.0.0  MVP
```

El desarrollo prioriza mantener cada incremento ejecutable, probado y documentado antes de avanzar al siguiente.

El calendario laboral administrable (días, horarios y feriados, configurable por el Administrador) ya existe (`v0.5.0`, entrega 2); el SLA que lo usa llega en las entregas siguientes de la fase. Después del MVP están previstos el modo oscuro, la evaluación de actualizaciones en tiempo real y otras mejoras evaluadas (autoservicio, automatización, flujos ITSM y activos), además de un módulo secundario de proyectos y tareas, solo para el personal, que deja a los tickets como núcleo. El roadmap está en [`docs/12_roadmap.md`](docs/12_roadmap.md) y las mejoras posteriores en [`docs/13_evolucion_post_mvp.md`](docs/13_evolucion_post_mvp.md).

---

## Principios del proyecto

WorkDesk busca mantener un equilibrio entre:

```text
simplicidad
+
mantenibilidad
+
seguridad
+
trazabilidad
+
aprendizaje
+
calidad técnica
```

La arquitectura crecerá únicamente cuando exista una necesidad concreta.

El objetivo no es incorporar tecnologías por sofisticación, sino construir progresivamente un sistema funcional, comprensible, mantenible y presentable como proyecto profesional de portafolio.