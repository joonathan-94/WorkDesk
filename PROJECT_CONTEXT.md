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

- gestión de usuarios;
- autorización basada en roles;
- políticas de acceso;
- navegación según rol;
- restricciones administrativas;
- cuenta propia básica;
- datos demo relacionados con usuarios;
- pruebas específicas de autorización.

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

Bootstrap forma parte de la arquitectura prevista para el MVP y podrá incorporarse progresivamente cuando corresponda.

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
├── tests/
│   ├── conftest.py
│   ├── test_app.py
│   ├── test_auth.py
│   ├── test_passwords.py
│   └── test_system.py
├── .env.example
├── .gitignore
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
SESSION_COOKIE_SECURE
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
SESSION_COOKIE_SECURE=false
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

Existen actualmente dos migraciones principales:

```text
create_roles_table
create_users_table
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
GET        /health
GET        /static/<path:filename>
```

`/dashboard` requiere autenticación.

El dashboard actual es temporal.

No representa todavía los dashboards finales del MVP.

---

# 18. Login visual

Existe una primera interfaz visual de login.

Características:

- texto `WorkDesk`;
- username;
- contraseña;
- botón principal;
- mostrar/ocultar contraseña;
- mensajes de error;
- conservación de username después de fallo;
- protección CSRF;
- diseño responsive básico.

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
- exige contraseña mínima de 12 caracteres.

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
- login visual;
- tests de autenticación base.

## Pendiente principal

- políticas RBAC;
- control de acceso por rol;
- navegación adaptada por rol;
- rutas administrativas protegidas;
- gestión de usuarios;
- cuenta propia básica;
- datos demo;
- pruebas específicas de autorización;
- completar UI correspondiente a esta fase.

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
4. actualizar `docs/12_roadmap.md`;
5. ejecutar Ruff;
6. ejecutar pytest;
7. revisar Git;
8. crear Pull Request;
9. mergear;
10. volver a `main` limpia.

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