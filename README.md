# WorkDesk

> Plataforma web para la gestión y seguimiento de tickets de soporte TI, diseñada para evolucionar progresivamente hacia una solución más amplia de gestión del trabajo.

WorkDesk es un proyecto personal de desarrollo de software orientado inicialmente a la gestión integral de solicitudes de soporte TI.

El sistema busca centralizar el ciclo de vida de los tickets, facilitar la colaboración entre solicitantes y equipos técnicos, controlar prioridades y SLA, mantener trazabilidad de las acciones y proporcionar herramientas de seguimiento, conocimiento y análisis operacional.

---

## Estado del proyecto

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
- Interfaz visual de login.
- Manejo controlado de errores HTTP.
- Health check de aplicación y PostgreSQL.
- Logging persistente con rotación configurable.
- Base PostgreSQL independiente para pruebas.
- Suite inicial automatizada con `pytest`.
- Análisis estático mediante Ruff.

La suite de fundación cuenta actualmente con **20 tests automatizados**.

### Próximo hito

`v0.2.0 — Usuarios, autenticación completa y RBAC`

Parte de la base técnica de autenticación prevista originalmente para `v0.2.0` fue adelantada durante la fundación para consolidar desde el inicio la seguridad, las sesiones y las pruebas.

La siguiente versión completará principalmente:

- gestión de usuarios;
- autorización basada en roles;
- políticas de acceso;
- navegación según rol;
- cuenta propia básica;
- restricciones de acceso administrativas;
- datos de demostración relacionados con usuarios.

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

La arquitectura del MVP contempla además Bootstrap para la construcción progresiva de los componentes principales de la interfaz.

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
│       ├── auth/
│       ├── main/
│       ├── models/
│       ├── security/
│       ├── seeds/
│       ├── static/
│       ├── system/
│       ├── templates/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── errors.py
│       ├── extensions.py
│       └── logging_config.py
│
├── tests/
│   ├── conftest.py
│   ├── test_app.py
│   ├── test_auth.py
│   ├── test_passwords.py
│   └── test_system.py
│
├── .env.example
├── .gitignore
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

### Aplicar migraciones

```bash
python -m flask --app src.workdesk db upgrade
```

Actualmente las migraciones iniciales crean:

- `roles`
- `usuarios`

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

La contraseña debe contener al menos 12 caracteres y se almacena utilizando Argon2id.

El comando impide crear accidentalmente más de un Administrador inicial mediante este mecanismo de bootstrap.

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

---

## Rutas actuales

La fundación técnica registra actualmente:

```text
GET       /
GET POST  /login
POST      /logout
GET       /dashboard
GET       /health
```

`/dashboard` requiere una sesión autenticada.

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

La autorización completa basada en roles y políticas de acceso forma parte de `v0.2.0`.

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

La suite de fundación dispone actualmente de:

```text
20 tests
```

Los tests cubren principalmente:

- creación de la aplicación;
- configuración de testing;
- rutas públicas;
- rutas protegidas;
- errores controlados;
- health check;
- conexión PostgreSQL de testing;
- login válido;
- login inválido;
- usuario inactivo;
- logout;
- bloqueo por intentos fallidos;
- invalidación mediante `token_version`;
- hashing Argon2id;
- verificación de contraseñas;
- configuración obligatoria.

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

# Crear Administrador inicial
python -m flask --app src.workdesk create-admin

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