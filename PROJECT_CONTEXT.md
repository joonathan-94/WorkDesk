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

Esa evolución futura no debe introducir complejidad prematura en el MVP actual.

---

# 3. Estado actual

## Versión estable

```text
v0.1.0 — Fundación técnica
```

La versión `v0.1.0` está:

- implementada;
- revisada técnicamente;
- testeada;
- documentada;
- mergeada en `main`.

## Rama estable

```text
main
```

`main` debe representar siempre el estado estable del proyecto.

## Rama de trabajo actual

```text
feature/users-manage
```

Paso 4.4 de `v0.2.0` (último de la entrega "Usuarios y contraseñas"): administración de usuarios existentes por el Administrador — detalle, edición de datos, cambio de rol, desactivación y reactivación, y restablecimiento de contraseña, con sus salvaguardas. No incluye migraciones.

Ya integradas en `main`: la sincronización documental (PR #4), la base RBAC (PR #5), los límites de sesión (PR #6), la auditoría administrativa (PR #7), la base de seguridad de contraseñas (PR #8), el cambio de contraseña propio y obligatorio (PR #9) y el listado y creación de usuarios (PR #10). El tag `v0.1.0` existe.

Paso siguiente: la entrega 5 (interfaz administrativa: Bootstrap local, sidebar y navegación por rol, "Mi cuenta", datos demo y cierre de `v0.2.0`).

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

## Próximo hito

```text
v0.2.0 — Usuarios, autenticación completa y RBAC
```

Durante `v0.1.0` se adelantó intencionalmente parte de la base técnica de autenticación para consolidar desde el comienzo:

- sesiones;
- seguridad;
- protección de rutas;
- bloqueo de intentos;
- invalidación de sesiones;
- testing automatizado.

La fase `v0.2.0` debe completar especialmente:

- gestión de usuarios (listado, creación, detalle, edición, cambio de rol, desactivación y reactivación, y restablecimiento de contraseña) — implementada;
- autorización basada en roles;
- políticas de acceso;
- navegación según rol;
- restricciones administrativas;
- cuenta propia básica;
- datos demo relacionados con usuarios;
- pruebas específicas de autorización;
- límites de sesión (30 minutos de inactividad y 8 horas máximo, por variables de entorno) — implementado;
- contraseñas: creación de cuentas y restablecimiento por el Administrador con contraseña temporal, cambio propio y cambio obligatorio en el primer inicio de sesión (`usuarios.debe_cambiar_password`) — implementados la política, el generador, la columna, las operaciones de dominio, la pantalla de cambio propio y la guardia de cambio obligatorio; el Administrador crea usuarios con contraseña temporal y restablece contraseñas desde la interfaz;
- tabla `auditoria_administrativa` mínima para las acciones sobre usuarios — implementada (modelo, migración y servicio), y todas las acciones sobre usuarios ya registran su evento.

`docs/12_roadmap.md` divide `v0.2.0` en cinco entregas incrementales, cada una con su rama y Pull Request.

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

## Frontend

- HTML5
- CSS3
- JavaScript
- Jinja2

Bootstrap forma parte de la arquitectura prevista para el MVP y **todavía no está integrado**: el Login actual usa CSS propio. Se incorporará, servido localmente (sin CDN), con las primeras pantallas administrativas de `v0.2.0`, respetando el Design System.

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
├── scripts/
├── src/
│   └── workdesk/
│       ├── account/
│       ├── admin/
│       ├── audit/
│       ├── auth/
│       ├── main/
│       ├── models/
│       ├── security/
│       ├── seeds/
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
│       │   └── js/
│       ├── system/
│       ├── templates/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── errors.py
│       ├── extensions.py
│       └── logging_config.py
├── tests/
│   ├── conftest.py
│   ├── test_account_password.py
│   ├── test_app.py
│   ├── test_audit.py
│   ├── test_auth.py
│   ├── test_authorization.py
│   ├── test_cli.py
│   ├── test_credentials.py
│   ├── test_password_policy.py
│   ├── test_passwords.py
│   ├── test_session_limits.py
│   ├── test_system.py
│   ├── test_users_manage_routes.py
│   ├── test_users_manage_service.py
│   ├── test_users_routes.py
│   └── test_users_service.py
├── .github/
│   └── copilot-instructions.md
├── .env.example
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

Existen actualmente cuatro migraciones:

```text
create_roles_table
create_users_table
create_admin_audit_log_table
add_must_change_password_flag_to_users
```

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

Se invoca desde todas las acciones sobre usuarios: creación (`USUARIO_CREADO`), edición de datos (`USUARIO_MODIFICADO`, con los valores anteriores y nuevos de los campos cambiados), cambio de rol (`CAMBIO_ROL`), desactivación y reactivación (`USUARIO_DESACTIVADO`, `USUARIO_ACTIVADO`) y contraseñas (`PASSWORD_CAMBIADA`, `PASSWORD_RESTABLECIDA`). Las acciones críticas admiten un motivo opcional.

## Gestión de usuarios (Administrador)

Módulo `src/workdesk/users/` (blueprint `users`, prefijo `/users`), accesible solo para el rol Administrador mediante `roles_required`.

- **Listado** (`GET /users`): búsqueda por nombre, apellido, nombre completo, usuario o correo (sin distinguir mayúsculas; `%`, `_` y `\` se buscan literalmente); filtros por rol y estado; orden por apellido y nombre; paginación de 20 en PostgreSQL. El rol se carga con el mismo JOIN del filtro (`contains_eager`), sin una consulta por fila. Los filtros y páginas inválidos se ignoran.
- **Creación** (`GET, POST /users/new`): formulario Flask-WTF con CSRF. `users/service.py` concentra las reglas (`create_user`): normaliza username y correo a minúsculas, comprueba rol existente y unicidad, aplica la política de contraseñas, crea el usuario activo y con el cambio de contraseña pendiente, y audita `USUARIO_CREADO`. No hace commit.
- **Carreras de unicidad:** si dos altas pasan la comprobación a la vez, gana la restricción UNIQUE; un savepoint (`begin_nested`) deshace solo ese intento y se informa como duplicado.
- **Contraseña temporal:** se genera automáticamente (por defecto) o la escribe el Administrador. La generada se muestra una sola vez en la propia respuesta del POST (no se redirige): no se guarda en la sesión (cookie firmada pero legible), en la base de datos ni en la auditoría, y la respuesta lleva `Cache-Control: no-store`.
- **Reglas de datos:** formato del username y del correo en `docs/06` (RN-148). El username no se puede cambiar después de crearlo.
- **Formularios:** el rol y el modo de contraseña se validan en el formulario sin usar `SelectField` ni `RadioField` de WTForms (sus opciones como tuplas están obsoletas en WTForms 3.3); las opciones se pasan como atributo (`role_choices`).
- **Presentación:** `templates/base_admin.html` (cabecera con navegación, mensajes y bloques), `templates/_form_macros.html` y `static/css/admin.css`. Son provisionales: la entrega 5 los reemplaza por el layout con Bootstrap y sidebar por rol. Los estilos de formulario comunes viven ahora en `app.css`.
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
- La pantalla muestra el modo obligatorio (aviso de contraseña temporal, sin enlace de retorno y con opción de cerrar sesión) o el modo normal (con enlace al dashboard).
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
GET        /health
GET        /static/<path:filename>
```

`/dashboard` y `/account/password` requieren autenticación.

`/account/password` permite al usuario cambiar su propia contraseña (ver "Cambio de contraseña propio y cambio obligatorio").

`/admin` y todas las rutas `/users` requieren el rol Administrador (403 para otros roles autenticados y redirección al login para anónimos). `/admin` es todavía una página mínima con un enlace a Usuarios; el hub de administración definitivo llegará con las siguientes entregas de `v0.2.0`.

El dashboard actual es temporal.

No representa todavía los dashboards finales del MVP.

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
python -m flask --app src.workdesk create-admin
```

`create-admin`:

- crea el Administrador inicial;
- valida datos básicos;
- exige la longitud mínima de contraseña configurada (`PASSWORD_MIN_LENGTH`, 12 por defecto).

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

# 30. Próxima fase — v0.2.0

Objetivo:

```text
Usuarios, autenticación completa y RBAC
```

## Ya implementado

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
- administración de usuarios existentes: detalle, edición de datos, cambio de rol, desactivación y reactivación, y restablecimiento de contraseña, con salvaguardas (nadie actúa sobre sí mismo, siempre queda un Administrador activo) y auditoría.

## Pendiente principal

- políticas RBAC adicionales según se incorporen los módulos;
- navegación adaptada por rol;
- hub de administración y rutas administrativas definitivas;
- cuenta propia básica ("Mi cuenta", con cambio de contraseña);
- incorporación local de Bootstrap con las primeras pantallas administrativas;
- datos demo;
- pruebas específicas de autorización;
- completar UI correspondiente a esta fase.

Orden propuesto de entregas en `docs/12_roadmap.md`.

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