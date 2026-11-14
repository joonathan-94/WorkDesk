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

## Estado del proyecto

### `v0.3.0 — Núcleo de tickets` (en desarrollo)

Es la fase central del MVP. Se construye en entregas pequeñas, cada una con su rama, tests y Pull Request. Hasta ahora están integradas:

- **Catálogos de tickets:** estados (los seis estructurales), prioridades (Baja, Media, Alta y Crítica), categorías, ubicaciones y motivos de cierre, con el comando `seed-catalogs` para cargar los datos iniciales.
- **Modelo de datos de tickets:** tabla de tickets con identificador público generado por una secuencia de PostgreSQL, solicitantes de cada ticket (relación temporal N:M) e historial de eventos inmutable, más el servicio que crea tickets.
- **Administración de catálogos:** el Administrador gestiona categorías, prioridades y ubicaciones desde la interfaz (crear, editar, desactivar y reactivar), con auditoría de cada cambio.

Todavía **no se pueden crear ni listar tickets desde la interfaz**: la creación, el listado con búsqueda y filtros, y el detalle llegan en las próximas entregas.

La suite cuenta con **644 tests automatizados**.

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

Cuando se complete `v0.3.0`, la siguiente versión es `v0.4.0 — Asignación, colaboración y ciclo de vida` (asignación de técnicos, cambios de estado, comentarios, notas internas, adjuntos, resolución y cierre). El detalle de cada fase está en [`docs/12_roadmap.md`](docs/12_roadmap.md).

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

El MVP se ejecutará inicialmente de forma local y no requiere infraestructura cloud ni servicios externos obligatorios.

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
├── scripts/
│
├── src/
│   └── workdesk/
│       ├── account/
│       ├── admin/
│       ├── audit/
│       ├── auth/
│       ├── catalogs/
│       ├── main/
│       ├── models/
│       ├── security/
│       ├── seeds/
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
│       │   ├── layouts/
│       │   ├── main/
│       │   └── users/
│       ├── tickets/
│       ├── users/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── errors.py
│       ├── extensions.py
│       ├── logging_config.py
│       └── navigation.py
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
│   ├── test_layout.py
│   ├── test_password_policy.py
│   ├── test_passwords.py
│   ├── test_seed_demo.py
│   ├── test_session_limits.py
│   ├── test_system.py
│   ├── test_ticket_model.py
│   ├── test_tickets_service.py
│   ├── test_users_manage_routes.py
│   ├── test_users_manage_service.py
│   ├── test_users_routes.py
│   └── test_users_service.py
│
├── .env.example
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── PROJECT_CONTEXT.md
├── README.md
├── requirements.txt
└── requirements-dev.txt
```

`instance/`, los archivos `.env`, entornos virtuales, logs y caches de herramientas permanecen fuera del control de versiones.

---

## Requisitos

Para ejecutar WorkDesk localmente se requiere:

- Python instalado.
- PostgreSQL instalado y en ejecución.
- Git.
- Un entorno virtual de Python recomendado.

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/joonathan-94/WorkDesk.git
cd WorkDesk
```

---

### 2. Crear el entorno virtual

```bash
python -m venv .venv
```

En Git Bash para Windows:

```bash
source .venv/Scripts/activate
```

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

---

## Configuración de PostgreSQL

WorkDesk utiliza dos bases de datos locales separadas:

```text
workdesk_dev
workdesk_test
```

`workdesk_dev` corresponde al entorno normal de desarrollo.

`workdesk_test` se utiliza exclusivamente para los tests automatizados.

### Rol de aplicación

La configuración local puede utilizar un rol PostgreSQL dedicado:

```text
workdesk_app
```

Ejemplo conceptual de preparación:

```sql
CREATE ROLE workdesk_app
WITH LOGIN
PASSWORD 'change-me';
```

Crear la base de desarrollo:

```sql
CREATE DATABASE workdesk_dev
OWNER workdesk_app;
```

Crear la base exclusiva para testing:

```sql
CREATE DATABASE workdesk_test
OWNER workdesk_app;
```

Las credenciales reales deben definirse únicamente en el archivo `.env` local.

---

## Variables de entorno

Copiar el archivo de ejemplo:

```bash
cp .env.example .env
```

Configurar como mínimo:

```env
APP_ENV=development
APP_TIMEZONE=America/Santiago

SECRET_KEY=
SESSION_COOKIE_SECURE=false

DATABASE_URL=
TEST_DATABASE_URL=

LOGIN_MAX_FAILED_ATTEMPTS=5
LOGIN_LOCK_MINUTES=15

PASSWORD_MIN_LENGTH=12

SESSION_IDLE_MINUTES=30
SESSION_MAX_HOURS=8

LOG_LEVEL=DEBUG
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=5
```

Ejemplo de formato para PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://workdesk_app:password@localhost:5432/workdesk_dev

TEST_DATABASE_URL=postgresql+psycopg://workdesk_app:password@localhost:5432/workdesk_test
```

No deben versionarse credenciales reales.

Durante desarrollo local mediante HTTP:

```env
SESSION_COOKIE_SECURE=false
```

En una futura ejecución mediante HTTPS deberá utilizarse:

```env
SESSION_COOKIE_SECURE=true
```

---

## Preparación inicial

Con las bases de datos creadas y el archivo `.env` configurado (secciones anteriores), ejecuta estos pasos **en este orden**, con el entorno virtual activado y desde la carpeta del proyecto:

| Paso | Comando | Para qué sirve |
| --- | --- | --- |
| 1 | `db upgrade` | Crea las tablas en PostgreSQL. |
| 2 | `seed-roles` | Carga los cuatro roles del sistema. |
| 3 | `seed-catalogs` | Carga estados, prioridades, la categoría de respaldo y los motivos de cierre. |
| 4 | `create-admin` | Crea tu cuenta de Administrador. |
| 5 | `seed-demo` (opcional) | Carga un equipo de soporte ficticio para probar el sistema. |
| 6 | `run` | Arranca WorkDesk. |
| 7 | Desde la interfaz | Crea las categorías y ubicaciones de tu organización. |

Todos los comandos llevan el prefijo `python -m flask --app src.workdesk` (por ejemplo, `python -m flask --app src.workdesk seed-roles`). Cada paso se explica a continuación.

---

### Aplicar migraciones

```bash
python -m flask --app src.workdesk db upgrade
```

Las migraciones actuales crean estas tablas:

- `roles` y `usuarios`: identidad y roles.
- `auditoria_administrativa`: registro inmutable de las acciones administrativas.
- `estados`, `prioridades`, `categorias`, `ubicaciones` y `motivos_cierre`: catálogos de tickets.
- `tickets`, `tickets_solicitantes` e `historial_ticket`: los tickets, sus solicitantes y su historial.

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
Prioridades         Baja, Media, Alta, Crítica
Categoría           Sin clasificar (categoría de respaldo)
Motivos de cierre   Resolución validada, Cierre directo, Inactividad,
                    Duplicado, Cancelación, Cierre excepcional
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
- username;
- email;
- contraseña.

La contraseña debe cumplir la longitud mínima configurada (`PASSWORD_MIN_LENGTH`, 12 caracteres por defecto) y se almacena utilizando Argon2id.

El comando impide crear accidentalmente más de un Administrador inicial mediante este mecanismo de bootstrap.

---

### Cargar datos de demostración (opcional)

```bash
python -m flask --app src.workdesk seed-demo
```

Crea un equipo de soporte ficticio de 12 personas (2 supervisores, 4 técnicos y 6 solicitantes) con correos `@workdesk.local`, útil para mostrar el sistema. No crea ningún Administrador: usa `create-admin` para crear el tuyo.

- La contraseña común de los usuarios demo se pide al ejecutar el comando (oculta). Para ejecutarlo sin interacción se puede definir la variable de entorno `WORKDESK_DEMO_PASSWORD`. Nunca se muestra ni se guarda.
- Es idempotente: omite a quien ya exista, sin modificarlo.
- No se ejecuta con `APP_ENV=production`.
- Los usuarios quedan activos y sin cambio de contraseña obligatorio, para poder entrar directamente.

---

## Ejecutar WorkDesk

Con el entorno virtual activado:

```bash
python -m flask --app src.workdesk run --debug
```

La aplicación estará disponible normalmente en:

```text
http://127.0.0.1:5000
```

Inicia sesión con el Administrador que creaste en el paso 4.

---

## Configurar categorías y ubicaciones

Los tickets necesitan una categoría y, opcionalmente, una ubicación. WorkDesk solo trae la categoría de respaldo `Sin clasificar`; el resto lo define cada organización desde la interfaz, con la sesión del Administrador iniciada:

1. En el menú lateral, abre **Administración**.
2. **Categorías** → **Nueva categoría**. El nombre es obligatorio; la descripción y el orden son opcionales (las categorías con número menor aparecen primero). Para un equipo de soporte TI, por ejemplo: `Accesos y cuentas`, `Correo`, `Hardware`, `Software`, `Redes`, `Impresoras`.
3. **Ubicaciones** → **Nueva ubicación**. Indica el nombre y, si quieres, el tipo (Sucursal, Oficina, Edificio, Piso, Área, Instalación u Otra). Por ejemplo, `Casa matriz` (Sucursal) o `Edificio A - Piso 2` (Piso).
4. **Prioridades** (opcional): puedes cambiar el nombre y la descripción de las cuatro prioridades, o desactivar alguna. Su nivel y su color son fijos, y siempre debe quedar al menos una activa.

Reglas que conviene conocer:

- El nombre no puede repetirse dentro de un mismo catálogo, sin distinguir mayúsculas. Si dos edificios tienen un `Piso 2`, nómbralos `Edificio A - Piso 2` y `Edificio B - Piso 2`.
- **Desactivar** un valor no afecta a los tickets que ya lo usan: solo deja de poder elegirse en tickets nuevos. Se puede reactivar cuando quieras.
- `Sin clasificar` se puede renombrar, pero no desactivar.
- Cada cambio queda registrado en la auditoría administrativa.

Si solo quieres probar el sistema, bastan tres o cuatro categorías y una o dos ubicaciones.

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
GET       /health
```

`/dashboard` y `/account/password` requieren una sesión autenticada. `/admin` (incluidas las pantallas de categorías, prioridades y ubicaciones) y todas las rutas `/users` requieren el rol Administrador.

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

---

## Manejo de errores

WorkDesk dispone actualmente de respuestas controladas para:

```text
400 Bad Request
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
644 tests
```

Los tests cubren principalmente:

- creación de la aplicación, configuración y manejo de errores;
- health check y conexión PostgreSQL de testing;
- autenticación: login, logout, bloqueo por intentos fallidos, invalidación de sesiones, límites de sesión y Argon2id;
- política de contraseñas, contraseñas temporales y cambio obligatorio;
- autorización por roles y navegación filtrada por rol;
- administración de usuarios (servicio y rutas) y "Mi cuenta";
- auditoría administrativa, incluida su inmutabilidad;
- datos de demostración;
- catálogos de tickets: datos iniciales, restricciones de base de datos y administración desde la interfaz;
- modelo de tickets: identificador público, solicitantes, historial inmutable y servicio de creación.

Ejecutar:

```bash
python -m pytest -q
```

Los tests utilizan exclusivamente:

```text
workdesk_test
```

La configuración incorpora una protección adicional para evitar que la suite pueda ejecutarse accidentalmente sobre `workdesk_dev`.

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

# Cargar catálogos iniciales (estados, prioridades, categoría de respaldo, motivos de cierre)
python -m flask --app src.workdesk seed-catalogs

# Crear Administrador inicial
python -m flask --app src.workdesk create-admin

# Cargar datos de demostración (opcional)
python -m flask --app src.workdesk seed-demo

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
v0.4.0  Colaboración y adjuntos
v0.5.0  SLA y notificaciones
v0.6.0  Dashboards y carga de trabajo
v0.7.0  Administración y conocimiento
v0.8.0  Reportes, auditoría y backups
v0.9.0  Estabilización y UX
v1.0.0  MVP
```

El desarrollo prioriza mantener cada incremento ejecutable, probado y documentado antes de avanzar al siguiente.

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