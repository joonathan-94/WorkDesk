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

WorkDesk es un proyecto personal de desarrollo de software: una aplicación completa, construida por entregas pequeñas y documentadas, que se instala y funciona en la red de una organización sin depender de Internet.

---

## ¿Qué es WorkDesk? En dos minutos

En cualquier organización hay cosas que dejan de funcionar: la impresora no imprime, el correo no llega, la VPN no conecta, un programa pide una licencia. Alguien necesita ayuda y alguien del equipo de soporte tiene que dársela. Sin una herramienta, eso se pierde entre correos, llamadas y mensajes: nadie sabe quién lo está viendo, cuánto lleva esperando ni cómo se resolvió la vez anterior.

WorkDesk ordena ese ida y vuelta. Cada pedido de ayuda es un **ticket**: tiene un número, una prioridad, un responsable, una conversación y un historial que no se puede borrar. Cada persona ve lo que le corresponde según su rol:

| Rol | Qué hace en WorkDesk |
| --- | --- |
| **Solicitante** (quien pide ayuda) | Crea sus tickets, adjunta capturas, conversa con soporte, confirma si la solución funcionó y consulta la base de conocimiento para resolverlo por su cuenta. Nunca ve las notas internas del equipo. |
| **Técnico** (quien resuelve) | Toma tickets o los recibe asignados, los trabaja, deja notas internas para el equipo, ve cuánto plazo le queda a cada uno y documenta la solución. |
| **Supervisor** (quien coordina) | Ve la carga de todo el equipo, reparte y reasigna el trabajo, escala lo urgente y vigila los plazos. |
| **Administrador** (quien configura) | Gestiona personas, grupos, categorías, plazos, horarios laborales, avisos y todo lo configurable, siempre con registro de quién cambió qué. |

### Un ticket, de principio a fin

1. **Javiera no puede imprimir.** Entra a WorkDesk y busca «impresora» en la base de conocimiento. No encuentra nada que le sirva, así que crea un ticket. Si ella ya tuviera otro abierto parecido, WorkDesk se lo mostraría antes de crearlo, por si es el mismo problema.
2. **El ticket entra con prioridad Media.** Su plazo de resolución (el SLA) empieza a correr, pero solo en horario laboral: las noches, los fines de semana y los feriados no cuentan.
3. **Diego, técnico, se lo asigna.** Le pregunta a Javiera el modelo de la impresora y deja una nota interna para su equipo, que Javiera no ve. Mientras espera la respuesta pone el ticket «En espera», y el reloj del plazo se pausa.
4. **Diego lo resuelve** y escribe la solución. A Javiera le llega un aviso para que confirme si funcionó.
5. **Javiera confirma** y el ticket se cierra. Si no hubiera respondido, se habría cerrado solo pasado un día; si el problema vuelve, puede reabrirlo.
6. **La solución se convierte en conocimiento.** Diego crea desde el ticket un borrador de artículo con la solución, y Camila, su supervisora, lo publica. La próxima persona con el mismo problema lo encontrará antes de crear un ticket.

Cada paso queda en el historial del ticket con su fecha y su autor. Si el plazo hubiera estado por vencer, Diego habría recibido un aviso, y el dashboard de Camila lo habría mostrado entre los urgentes.

### ¿Por dónde empiezo a leer?

| Si eres... | Empieza por |
| --- | --- |
| Alguien que quiere entender qué hace, sin ser técnico | Esta sección, el [alcance](#alcance-del-mvp) y el [ciclo de vida de un ticket](#el-ciclo-de-vida-de-un-ticket) |
| Product manager o evaluador funcional | El [estado del proyecto](#estado-del-proyecto), el [alcance](#alcance-del-mvp), el [roadmap](#roadmap) y los [requisitos](docs/04_requisitos_funcionales.md) |
| Técnico de soporte que lo va a usar | El [recorrido de prueba](#recorrido-de-prueba), que muestra cada pantalla con los usuarios de demostración |
| Desarrollador que lo quiere ejecutar | La [guía rápida](#guía-rápida), la [arquitectura](#arquitectura) y los [tests](#tests) |
| Revisor técnico | [Lo que hay detrás](#lo-que-hay-detrás), la [seguridad](#autenticación-y-seguridad-actual) y el [historial de implementación](docs/14_historial_de_implementacion.md), con las decisiones y los errores encontrados en cada entrega |

### Lo que hay detrás

WorkDesk es pequeño en tecnologías y exigente en cómo las usa:

- **Un monolito modular con Flask y PostgreSQL**, renderizado en el servidor con Jinja2 y JavaScript solo donde mejora la experiencia. Funciona entero en la red local: sin nube, sin correo, sin servicios de terceros y sin nada cargado de Internet.
- **Quién ve qué se decide en la base de datos, no en la pantalla.** Cada regla de visibilidad es una condición SQL con su equivalente en Python, y una prueba comprueba que coinciden para cada rol y cada caso.
- **Concurrencia tomada en serio.** Dos personas que actúan a la vez sobre el mismo ticket no se pisan: control de versión optimista, bloqueo de filas en un orden fijo para evitar bloqueos mutuos y pruebas con varios hilos simultáneos.
- **El SLA se mide en tiempo laboral**, con un motor propio que respeta horarios distintos por día, pausas y feriados. Cada estado del SLA calculado en SQL se compara con el de Python en más de 150 momentos, incluidos los bordes de un segundo.
- **Medido a escala:** con unos 20 000 tickets, todas las pantallas responden en menos de medio segundo, y el número de consultas de cada una no crece con los datos (hay una prueba que lo vigila).
- **4970 pruebas automáticas**, que corren en unos 4 minutos en paralelo. Las que protegen algo importante se comprueban con mutaciones: se rompe a propósito lo que protegen y deben fallar. Seis redes de seguridad cubren solas cualquier ruta, pantalla o tabla nueva.
- **Documentado como un proyecto real:** catorce documentos de requisitos, reglas de negocio, casos de uso, modelo de datos, arquitectura y diseño, y una matriz de trazabilidad que compara cada requisito con el código al cerrar cada fase.

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

## Contenido

**Para empezar:** [Guía rápida](#guía-rápida) · [Requisitos](#requisitos) · [Instalación](#instalación) · [PostgreSQL](#configuración-de-postgresql) · [Variables de entorno](#variables-de-entorno) · [Preparación inicial](#preparación-inicial) · [Actualizar una instalación](#actualizar-una-instalación-existente)

**Usar WorkDesk:** [Ejecutar WorkDesk](#ejecutar-workdesk) · [Ejecutar el planificador](#ejecutar-el-planificador) · [Respaldos](#respaldos) · [Crear un ticket](#crear-un-ticket) · [El ciclo de vida de un ticket](#el-ciclo-de-vida-de-un-ticket) · [Recorrido de prueba](#recorrido-de-prueba) · [Solución de problemas](#solución-de-problemas)

**Entender WorkDesk:** [Qué es, en dos minutos](#qué-es-workdesk-en-dos-minutos) · [Un ticket de principio a fin](#un-ticket-de-principio-a-fin) · [Por dónde empezar a leer](#por-dónde-empiezo-a-leer) · [Lo que hay detrás](#lo-que-hay-detrás)

**Conocer el proyecto:** [Estado del proyecto](#estado-del-proyecto) · [Alcance del MVP](#alcance-del-mvp) · [Stack](#stack-tecnológico) · [Arquitectura](#arquitectura) · [Estructura](#estructura-actual) · [Rutas](#rutas-actuales) · [Autenticación y seguridad](#autenticación-y-seguridad-actual)

**Desarrollar:** [Tests](#tests) · [Calidad de código](#calidad-de-código) · [Comandos principales](#comandos-principales) · [Documentación](#documentación) · [Roadmap](#roadmap)

---

## Estado del proyecto

La última versión estable es **`v0.7.0 — Administración y base de conocimiento`** y la fase siguiente es **`v0.8.0 — Reportes, auditoría y backups`**. Cada versión se construyó en entregas pequeñas, con su rama, sus tests y su Pull Request.

| Versión | Qué hace WorkDesk con ella | Tests al cerrar |
| --- | --- | --- |
| `v0.1.0` | Fundación técnica: Flask, PostgreSQL, autenticación con Argon2id, sesiones, CSRF, logging y health check | 20 |
| `v0.2.0` | Usuarios, roles y permisos, límites de sesión, contraseñas temporales, auditoría y «Mi cuenta» | 385 |
| `v0.3.0` | Núcleo de tickets: catálogos, creación, listado con búsqueda y filtros, detalle y edición | 967 |
| `v0.4.0` | Se trabaja en equipo: grupos, asignación, comentarios y notas internas, adjuntos, resolución y cierre, relaciones y bloqueo de edición | 2201 |
| `v0.5.0` | Mide el tiempo y avisa: SLA en tiempo laboral, calendario administrable, notificaciones internas y planificador | 3965 |
| `v0.6.0` | Da la vista de conjunto: un dashboard por rol, la carga de trabajo del equipo y la reasignación masiva de tickets | 4175 |
| `v0.7.0` | Se administra desde la web y guarda lo aprendido: configuración sin tocar el `.env`, avisos configurables, base de conocimiento y advertencia de duplicados | 4681 |

`v0.8.0` está en curso y tiene hechas sus nueve primeras entregas: la revisión previa con el refuerzo de seguridad, una suite de tests un 39 % más rápida, el registro de accesos, la pantalla de auditoría, los reportes con sus gráficos, la exportación a CSV y Excel, los respaldos firmados de la base y los adjuntos, y su restauración con la pantalla de estado del sistema. Hoy la suite cuenta con **5099 tests automatizados**. El relato completo de cada versión (qué se decidió, qué errores se encontraron y cómo se corrigieron) está en [`docs/14_historial_de_implementacion.md`](docs/14_historial_de_implementacion.md). Si vienes de una versión anterior, mira cómo [actualizar una instalación existente](#actualizar-una-instalación-existente) y el [recorrido de prueba](#recorrido-de-prueba).

### Próximo hito

`v0.8.0 — Reportes, auditoría y backups`: reportes con filtros, la pantalla de auditoría con los eventos de autenticación y los backups locales de la base de datos y los archivos, con su restauración probada. El detalle está en [`docs/12_roadmap.md`](docs/12_roadmap.md) (fase 8).

---

## Alcance del MVP

WorkDesk se construye por fases hasta completar un MVP (la primera versión completa, `v1.0.0`) orientado a soporte TI. Este es su estado real, comprobado en el código y en los tests:

| Capacidad | Estado | Desde |
| --- | --- | --- |
| Inicio de sesión seguro, roles y permisos | ✅ Hecho | `v0.1.0` y `v0.2.0` |
| Administración de usuarios, con auditoría | ✅ Hecho | `v0.2.0` |
| Tickets: crear, listar, buscar, filtrar y editar | ✅ Hecho | `v0.3.0` |
| Categorías, prioridades, ubicaciones, estados y transiciones | ✅ Hecho | `v0.3.0` y `v0.4.0` |
| Grupos y asignación a uno o varios técnicos, escalamiento | ✅ Hecho | `v0.4.0` |
| Comentarios públicos, notas internas y archivos adjuntos | ✅ Hecho | `v0.4.0` |
| Resolución, validación del solicitante, cierre y reapertura | ✅ Hecho | `v0.4.0` |
| Relaciones entre tickets y duplicados | ✅ Hecho | `v0.4.0` |
| SLA en tiempo laboral, con calendario y feriados | ✅ Hecho | `v0.5.0` |
| Notificaciones internas y planificador (avisos y cierre automático) | ✅ Hecho | `v0.5.0` |
| Dashboards por rol, carga de trabajo y reasignación masiva | ✅ Hecho | `v0.6.0` |
| Configuración desde la web y avisos configurables | ✅ Hecho | `v0.7.0` |
| Base de conocimiento y advertencia de duplicados | ✅ Hecho | `v0.7.0` |
| Reportes, con exportación a CSV y Excel | ✅ Hecho | `v0.8.0` |
| Pantalla de auditoría y registro de accesos | ✅ Hecho | `v0.8.0` |
| Respaldos locales y su restauración | 🔨 En curso | `v0.8.0` |
| Retención de datos | 🔨 En curso | `v0.8.0` |
| Revisión visual, responsive y accesibilidad | ⏳ Pendiente | `v0.9.0` |
| Estabilización y versión 1.0 | ⏳ Pendiente | `v1.0.0` |

Lo que viene después del MVP (autoservicio, automatización, activos, gestión de proyectos) está evaluado en [`docs/13_evolucion_post_mvp.md`](docs/13_evolucion_post_mvp.md).

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
- openpyxl `3.1.5` (exportación a Excel)

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
│   ├── 12_roadmap.md
│   ├── 13_evolucion_post_mvp.md
│   └── 14_historial_de_implementacion.md
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
│       ├── backups/
│       ├── catalogs/
│       ├── groups/
│       ├── main/
│       ├── models/
│       ├── notifications/
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
│       │   ├── notifications/
│       │   ├── sla/
│       │   ├── tickets/
│       │   └── users/
│       ├── tickets/
│       │   └── routes/
│       ├── users/
│       ├── __init__.py
│       ├── cleaning.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── demo.py
│       │   ├── scheduling.py
│       │   ├── setup.py
│       │   └── sla.py
│       ├── config.py
│       ├── errors.py
│       ├── extensions.py
│       ├── formatting.py
│       ├── logging_config.py
│       ├── navigation.py
│       ├── query_params.py
│       ├── responses.py
│       ├── scheduler.py
│       ├── search.py
│       ├── status_filter.py
│       └── worktime.py
│
├── tests/
│   ├── conftest.py            # fixtures: app, client, make_user, instantáneas de datos de demostración
│   ├── database.py            # protección de workdesk_test, esquemas por proceso, limpieza e instantáneas
│   ├── areas.py               # qué módulo de tests pertenece a qué área (marcadores de pytest)
│   ├── demo_data.py           # los 108 tickets de demostración compartidos por los tests
│   ├── seed_helpers.py, sla_helpers.py, ticket_helpers.py   # ayudantes compartidos
│   └── test_*.py              # un módulo por tema (autenticación, tickets, SLA, notificaciones, seeds...)
│
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
| `LOGIN_MAX_FAILED_PER_IP` | `20` | Intentos fallidos desde un mismo equipo (IP), en cualquier cuenta y dentro de `LOGIN_LOCK_MINUTES`, antes de rechazar los siguientes desde ese equipo. Frena a quien prueba pocas contraseñas en muchas cuentas. `0` lo desactiva: hazlo si todas las peticiones llegan a través de un mismo proxy. |
| `PASSWORD_MIN_LENGTH` | `12` | Longitud mínima de las contraseñas (entre 8 y 128). |
| `SESSION_IDLE_MINUTES` | `30` | Minutos de inactividad tras los cuales se cierra la sesión. Solo cuenta lo que hace la persona: la consulta automática de la campana de notificaciones no renueva la sesión. |
| `SESSION_MAX_HOURS` | `8` | Duración máxima de una sesión, aunque se use todo el tiempo. |
| `UPLOAD_MAX_BYTES` | `10485760` (10 MB) | Tamaño máximo de cada archivo adjunto, en bytes. Debe ser mayor que cero. |
| `UPLOAD_MAX_FILES_PER_TICKET` | `20` | Cantidad máxima de archivos activos por ticket. Debe ser mayor que cero. |
| `UPLOADS_DIR` | `instance/uploads` | Carpeta donde se guardan los adjuntos (fuera de `static/`, no se versiona). |
| `BACKUPS_DIR` | `instance/backups` | Carpeta de los [respaldos](#respaldos). Conviene que esté en otro disco que la base y los adjuntos. No puede estar dentro de `static/` ni de `UPLOADS_DIR` (ni al revés): WorkDesk no arranca así. |
| `PG_BIN_DIR` | — | Carpeta de `pg_dump`, `pg_restore` y `psql` si no están en el `PATH` (en Windows, por ejemplo, `C:\Program Files\PostgreSQL\18\bin`). |
| `SCHEDULER_HEARTBEAT_FILE` | `instance/scheduler-heartbeat.json` | Dónde deja el planificador la hora de su última pasada, que muestra **Estado del sistema**. |
| `LOG_DIR` | `instance/logs` | Carpeta de los archivos de log. |
| `COMMENT_EDIT_WINDOW_MINUTES` | `30` | Minutos durante los que el autor de un comentario puede editarlo o eliminarlo (el Supervisor y el Administrador pueden siempre). Debe ser mayor que cero. |
| `REOPEN_WINDOW_DAYS` | `30` | Días, desde el cierre, durante los que un solicitante puede reabrir su ticket (el personal puede siempre). Debe ser mayor que cero. |
| `AUTO_CLOSE_HOURS` | `24` | Horas que un ticket puede estar Resuelto sin que su solicitante lo valide antes de que el planificador lo cierre solo (también si no tiene solicitantes). Debe ser mayor que cero. |
| `DUPLICATE_WINDOW_DAYS` | `30` | Días hacia atrás en los que se buscan tickets parecidos al crear uno. `0` desactiva la advertencia. Máximo 365. |
| `DUPLICATE_MIN_WORDS` | `2` | Palabras del título que deben coincidir para considerarlos parecidos (1 a 5). |
| `SLA_ENABLED` | `true` | Si el SLA se muestra y avisa. Se puede cambiar desde Administración → SLA (el valor guardado reemplaza a esta variable). |
| `AUTO_CLOSE_ENABLED` | `true` | Si el planificador cierra solo los tickets resueltos que nadie valida. Se puede cambiar desde Administración → Cierre y reapertura. |
| `LOCATION_REQUIRED` | `false` | Si la ubicación es obligatoria al crear un ticket. Solo se exige mientras haya alguna ubicación activa. Se puede cambiar desde Administración → Creación de tickets. |
| `SCHEDULER_INTERVAL_SECONDS` | `60` | Cada cuántos segundos revisa el planificador (`run-scheduler`) los avisos de SLA y los cierres automáticos cuando se deja en marcha. Debe ser mayor que cero. |
| `WORKLOAD_HIGH_ACTIVE_TICKETS` | `10` | A partir de cuántos tickets activos (ni Resueltos ni Cerrados) se marca a un técnico con «carga alta» en la carga de trabajo. Solo informa: nunca bloquea una asignación. `0` desactiva la marca. Debe ser un entero mayor o igual que cero. |
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
| 3 | `seed-catalogs` | Carga estados y sus transiciones, prioridades con sus objetivos de SLA, la categoría de respaldo, los motivos de cierre, los motivos de espera y los tipos de relación entre tickets. |
| 4 | `create-admin` | Crea tu cuenta de Administrador. |
| 5 | `seed-demo` (opcional) | Carga un equipo de soporte ficticio para probar el sistema. |
| 6 | `run` | Arranca WorkDesk. |
| 7 | Desde la interfaz | Crea las categorías y ubicaciones de tu organización. |
| 8 | `seed-demo-tickets` (opcional) | Carga 108 tickets de ejemplo, escritos como los escribiría gente real. Necesita los pasos 3, 5 y 7 (ver [Tickets de demostración](#tener-tickets-con-los-que-probar)). |
| 8 bis | `seed-demo-articles` (opcional) | Carga 11 artículos de ejemplo en la base de conocimiento y vincula cinco con sus tickets (ver [Artículos de demostración](#artículos-de-demostración)). |
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
- `politicas_sla`: los objetivos de SLA de cada prioridad (primera respuesta, resolución, umbral de aviso y pausa en espera).
- `tickets_sla_periodos`: los períodos de SLA de cada ticket (los tramos de su vida bajo unas mismas condiciones de SLA, con lo consumido, los vencimientos y cuándo se alcanza el umbral de aviso).
- `notificaciones`: los avisos internos de cada usuario (su contenido no se reescribe; solo cambia si ya los leyó).

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
- username (es lo que escribirás para iniciar sesión): entre 3 y 50 caracteres, solo letras minúsculas, números, punto, guion y guion bajo, empezando por una letra o un número (las mayúsculas se pasan a minúsculas);
- email, con forma de dirección (`algo@dominio.tld`);
- contraseña (no se muestra al escribirla y se pide dos veces).

Son las mismas reglas que aplica la pantalla de alta de usuarios: el comando usa el mismo servicio. La contraseña debe cumplir la longitud mínima configurada (`PASSWORD_MIN_LENGTH`, 12 caracteres por defecto) y se almacena con Argon2id. Al terminar, el comando responde `Administrador '...' creado correctamente.` y la creación queda en la auditoría como acción del sistema. Si un dato no cumple una regla, el comando dice cuál (por ejemplo, `Username: Usa solo letras minúsculas...`) y no crea nada.

El comando impide crear más de un Administrador inicial: si ya existe uno, responde `Ya existe un usuario con rol ADMINISTRADOR.` Los demás usuarios se crean desde la interfaz, en **Administración → Usuarios**.

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
| 3 | `python -m flask --app src.workdesk seed-catalogs` | Carga lo estructural que las versiones nuevas necesitan: las transiciones entre estados, los motivos de espera, los tipos de relación entre tickets y los objetivos de SLA de cada prioridad. No duplica nada ni pisa lo que hayas renombrado, editado o desactivado. |
| 4 | `python -m flask --app src.workdesk sla-rebuild` | Calcula el SLA de los tickets que ya tenías (los anteriores al SLA no lo tienen) y completa la fecha de aviso («próximo a vencer») de los períodos que ya estaban en marcha. Solo toca lo que falta y se puede repetir sin riesgo. |
| 5 | `python -m flask --app src.workdesk run --debug` | Reinicia WorkDesk. |
| 6 | `python -m flask --app src.workdesk run-scheduler` | En otra terminal: deja en marcha el planificador (avisos de SLA y cierre automático). |

Si vienes de una versión anterior a la que incluye el planificador, la migración marca como ya avisado lo que los SLA en marcha habían alcanzado, así que la primera ejecución de `run-scheduler` no te avisa de todo lo atrasado. Lo contrario ocurre con `sla-rebuild` (paso 4): los períodos que crea para tickets antiguos empiezan sin marcas, y el planificador avisará una sola vez de los que ya estén vencidos. Las variables nuevas (`AUTO_CLOSE_HOURS` y `SCHEDULER_INTERVAL_SECONDS`) tienen valor por defecto: no hace falta tocar tu `.env`.

Para comprobarlo, `db current` debe terminar en `(head)` y `db check` no debe encontrar cambios pendientes.

Al pasar de `v0.7.0` a `v0.8.0` conviene saber que:

- **Todos tendrán que iniciar sesión una vez más.** La cookie de sesión cambió de nombre (antes se llamaba `session`, que delataba con qué está hecha la aplicación), así que las sesiones abiertas dejan de valer. No se pierde nada más.
- **En producción, la `SECRET_KEY` debe tener al menos 32 caracteres** y no se puede arrancar con `--debug`. Si la tuya es más corta, genera una nueva como se explica en [Variables de entorno](#2-generar-la-secret_key); en desarrollo solo verás un aviso en el log.
- **El planificador escribe su propio log**, `instance/logs/scheduler.log`, en lugar de `workdesk.log`.
- **Una migración nueva** (`create_auth_events_table`, el registro de accesos): el paso 2 la aplica y no toca datos. La variable nueva `LOGIN_MAX_FAILED_PER_IP` tiene valor por defecto (20).
- **Una dependencia nueva,** `openpyxl` (la exportación a Excel): el paso 1 la instala.
- **Los [respaldos](#respaldos) necesitan `pg_dump`, `pg_restore` y `psql`,** que vienen con PostgreSQL. Si no están en el `PATH`, indica su carpeta en `PG_BIN_DIR`. Las variables nuevas (`BACKUPS_DIR`, `PG_BIN_DIR`, `SCHEDULER_HEARTBEAT_FILE` y `LOG_DIR`) son opcionales.
- **Administración → Estado del sistema** dirá que el planificador «no hay constancia de que se haya ejecutado» hasta su primera pasada con esta versión.

Al pasar de `v0.6.0` a `v0.7.0` conviene saber que:

- Hay tres migraciones nuevas (la configuración, la base de conocimiento y la liberación de bloqueos): el paso 2 las aplica. No cambian datos que ya tengas.
- Las variables de entorno nuevas (`SLA_ENABLED`, `AUTO_CLOSE_ENABLED`, `LOCATION_REQUIRED`, `DUPLICATE_WINDOW_DAYS` y `DUPLICATE_MIN_WORDS`) tienen valor por defecto. Desde esta versión **todas las de plazos y límites son solo el valor inicial**: el Administrador las cambia desde **Administración**, y lo que guarda manda sobre el `.env`.
- Para ver la base de conocimiento con contenido, carga los [artículos de demostración](#artículos-de-demostración) (`seed-demo-articles`).

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

## Ejecutar el planificador

Los avisos de SLA («próximo a vencer» y «vencido») y el cierre automático de los tickets Resueltos que nadie valida los hace un proceso aparte, `run-scheduler`: **la aplicación web no los hace sola**. Es un comando de WorkDesk, sin instalar nada más. Ábrelo en **otra terminal**, con el entorno virtual activado y desde la raíz del proyecto, y déjalo abierto mientras uses WorkDesk:

```bash
python -m flask --app src.workdesk run-scheduler
```

Cada 60 segundos (`SCHEDULER_INTERVAL_SECONDS`) revisa la base de datos y escribe una línea solo cuando hizo algo. Para detenerlo, `Ctrl+C`. Su registro técnico va a `instance/logs/scheduler.log`, separado del de la aplicación web (ver [Logging](#logging)).

- **Una sola pasada:** `python -m flask --app src.workdesk run-scheduler --once` revisa una vez y termina. Es lo que se programa en el Programador de tareas de Windows o en `cron` si prefieres no dejar una terminal abierta (por ejemplo, cada 5 minutos).
- **Se puede repetir sin riesgo:** un aviso se envía una sola vez y un ticket se cierra una sola vez, aunque ejecutes el comando varias veces o tengas dos planificadores a la vez.
- **Qué avisa:** cuando un SLA alcanza su umbral, a los técnicos asignados (o a los Supervisores, si no hay técnicos); cuando vence, a los técnicos y a los Supervisores. Los solicitantes nunca reciben avisos de SLA.
- **Qué cierra:** un ticket Resuelto que lleva más de `AUTO_CLOSE_HOURS` horas (24 por defecto) sin que el solicitante lo confirme ni lo rechace. Queda Cerrado con el motivo «Inactividad», el historial lo atribuye al Sistema y avisa al solicitante y a los técnicos. Se puede reabrir como cualquier otro.

---

## Respaldos

Un respaldo guarda **en un solo archivo** todo lo necesario para recuperar WorkDesk: la base de datos y los archivos adjuntos. Se crea con un comando, con el entorno virtual activado y desde la raíz del proyecto:

```bash
python -m flask --app src.workdesk backup-create
```

Necesita `pg_dump`, que viene con PostgreSQL (si no está en el `PATH`, indica su carpeta en `PG_BIN_DIR`). Escribe algo como:

```text
Respaldo creado: ...\instance\backups\workdesk-respaldo-20261127-183522Z.zip
Contenido: 108 tickets, 17 usuarios y 3 adjuntos (1 KB).
Tamaño: 186 KB.
SHA-256: ba627f3a...
```

- **WorkDesk puede seguir en uso mientras tanto.** La base y la lista de adjuntos se leen en un mismo instante, así que el respaldo trae exactamente los archivos que la base conoce, ni uno más ni uno menos.
- **Dónde queda:** en `instance/backups` (o en `BACKUPS_DIR`), con un `.sha256` al lado. El nombre lleva la hora en UTC (la `Z`). Guárdalo también **fuera de este equipo** (otro disco, otro servidor): un respaldo en el mismo disco no sirve si el disco falla.
- **Trata un respaldo como la base misma.** Contiene todo, también las contraseñas cifradas de los usuarios. Ponlo donde solo lo lea quien administra el servidor.
- **Si algo no cuadra, te avisa** (`Aviso: ...`) y crea el respaldo igual: un adjunto cuyo archivo no está en el disco, o uno que cambió desde que se subió.
- **Queda en la auditoría,** con la cuenta del equipo que lo ejecutó, también si falla.

### Comprobar un respaldo

```bash
python -m flask --app src.workdesk backup-verify
```

Comprueba el más reciente (o el que indiques por su nombre) **sin restaurarlo y sin necesitar la base de datos**, así que también sirve cuando la base se cayó. Revisa:

- la huella del paquete;
- que cada archivo esté entero;
- que no sobre ni falte nada;
- que el volcado de la base se pueda leer;
- y la **firma**: cada respaldo va firmado con una clave que sale de tu `SECRET_KEY`.

Así distingue un respaldo creado por esta instalación de uno alterado o fabricado por otra persona. Termina con `Resultado: el respaldo está completo y es de esta instalación.`, o con la lista de problemas y un error.

Si cambias la `SECRET_KEY`, los respaldos anteriores dirán que su firma «no corresponde». El contenido no cambió, pero WorkDesk ya no puede confirmar que sean suyos. Guarda tu `.env` en un lugar seguro y **aparte de los respaldos**: un respaldo nunca incluye el `.env` ni sus secretos.

### Ver los respaldos

```bash
python -m flask --app src.workdesk backup-list
```

Lista los respaldos del más reciente al más antiguo, con su fecha, tamaño, contenido y firma. Si un `backup-create` se cortó a la mitad, señala lo que dejó para que lo borres.

**Programarlos:** `backup-create` se puede programar en el Programador de tareas de Windows o en `cron` (por ejemplo, cada noche), igual que `run-scheduler --once`. Si dos coinciden, el segundo se rechaza sin hacer nada.

### Restaurar un respaldo

Restaurar **reemplaza la base de datos y los adjuntos** por los del respaldo: se pierde todo lo que se hizo después. Primero **detén WorkDesk y el planificador**, y después:

```bash
python -m flask --app src.workdesk backup-restore workdesk-respaldo-20261127-183522Z.zip
```

Antes de tocar nada, el comando:

1. **Comprueba el respaldo entero,** como `backup-verify`. No restaura uno alterado, sin firma o firmado con otra clave (salvo que añadas `--accept-other-key`; ver abajo).
2. **Comprueba que encaja con el código.** Un respaldo de una versión anterior de WorkDesk se restaura y después te pide `db upgrade`. Uno de una versión más nueva, que este código no conoce, no se restaura.
3. **Comprueba que no haya nadie más conectado** a la base: el servidor web, el planificador o un pgAdmin abierto. Si sabes de qué son esas conexiones, `--ignore-connections` sigue adelante.
4. **Te muestra qué se va a reemplazar** y te pide escribir el nombre de la base para confirmar.
5. **Guarda antes un respaldo de lo que hay ahora,** por si te equivocaste de respaldo.

Después restaura la base **en una sola transacción**: si cualquier cosa falla a mitad, PostgreSQL deshace todo y la base queda exactamente como estaba. Luego cambia la carpeta de adjuntos por la del respaldo y **cierra todas las sesiones**: cada persona vuelve a iniciar sesión, con las cuentas y los permisos del respaldo. Queda en la auditoría, también si falla. Al terminar, vuelve a iniciar WorkDesk y el planificador.

- **`--accept-other-key`:** para un respaldo cuya firma «no corresponde» porque cambiaste la `SECRET_KEY` o viene de otra instalación tuya. El contenido se comprueba igual, archivo por archivo; lo que no se puede confirmar es de dónde viene, así que úsalo solo si lo sabes.
- **`--skip-safety-backup`:** no guarda antes lo actual. Úsalo solo si la base está tan dañada que no se puede respaldar; entonces los adjuntos que había quedan en una carpeta aparte, junto a la de adjuntos.
- **En otro equipo** (por ejemplo, tras perder el servidor): instala WorkDesk, crea la base vacía, copia tu `.env` (con la misma `SECRET_KEY`) y ejecuta `db upgrade` antes de restaurar, para que el respaldo encaje con el esquema.

### Verlos desde la web

**Administración → Respaldos** muestra los respaldos guardados (fecha, tamaño, contenido, firma y si encajan con el código) y las últimas creaciones y restauraciones de la auditoría, también las fallidas. **Administración → Estado del sistema** muestra cómo están la aplicación, la base de datos, las migraciones, el planificador (cuándo pasó por última vez), el espacio en disco, el último respaldo y los errores del log en las últimas 24 horas. Las dos son solo para el Administrador y solo muestran: crear y restaurar respaldos se hace siempre con los comandos, en el servidor.

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

## El dashboard del Solicitante

Al iniciar sesión como **Solicitante** se abre un resumen de tus solicitudes:

- **Cuatro contadores**, cada uno un enlace al listado que lo explica: *Tickets abiertos*, *En progreso*, *Requieren tu revisión* (resueltos que esperan que confirmes o rechaces la solución) y *Cerrados recientemente* (los últimos 7 días).
- **Un aviso** cuando tienes soluciones por revisar: con una sola, el botón abre ese ticket; con varias, abre el listado filtrado.
- **Mis tickets recientes** (los 5 con actividad más reciente, con quién los atiende) y **Notificaciones recientes**.

No muestra SLA, grupos, carga de técnicos ni métricas globales: solo lo tuyo. Con los datos de demostración, cada Solicitante tiene al menos una solución por revisar.

---

## El dashboard del personal

Técnico, Supervisor y Administrador abren, al iniciar sesión, un resumen operativo del equipo:

- **Seis contadores**, cada uno un enlace al listado que lo explica: *Tickets abiertos*, *Sin asignar*, *Críticos*, *Fuera de SLA*, *Próximos a vencer* y *En espera*. Si hay tickets críticos sin asignar aparece además un aviso.
- **Tickets abiertos prioritarios:** los 8 en trabajo con mayor prioridad y, dentro de cada prioridad, el que vence antes, con su SLA.
- **Carga de trabajo** compacta (los técnicos con más tickets activos y los sin asignar), con enlace a la pantalla completa.
- **Actividad reciente:** los últimos 10 eventos de los tickets, con quién y cuándo. Solo dice qué pasó: nunca copia el texto de un comentario o de una nota.
- El **Técnico** ve además *Mi trabajo* (sus tickets activos, críticos, con SLA en riesgo y los que resolvió en 7 días) y el **Administrador** un bloque con los usuarios activos por rol, el calendario laboral y las políticas de SLA.

Las definiciones son las de la carga de trabajo (un ticket *activo* no está Resuelto ni Cerrado), así que las cifras coinciden entre las dos pantallas.

**Si vienes de una versión anterior**, esta entrega incluye una migración (un índice del historial para la actividad reciente): ejecuta `python -m flask --app src.workdesk db upgrade`.

---

## La carga de trabajo

El personal (Técnico, Supervisor y Administrador) tiene la opción **Carga de trabajo** del menú (`/workload`). Es una pantalla para *analizar* cómo está repartido el trabajo, no un ranking:

- **Cuatro indicadores** enlazados al listado que los explica: *Tickets activos* (ni Resueltos ni Cerrados), *Sin asignar*, *Críticos* y *SLA en riesgo* (próximos a vencer más vencidos).
- **Carga por técnico:** activos, en progreso, en espera, críticos y SLA en riesgo, con una barra de distribución por prioridad (comparativa, con su texto equivalente). Cada número abre el listado de esos tickets.
- **Carga por grupo**, con una fila «Sin grupo».
- **Filtros** por grupo, prioridad, estado y técnico, búsqueda por nombre y orden de la tabla.
- Un ticket con varios técnicos cuenta en cada uno: la suma de la tabla puede superar al total, y la pantalla lo explica.
- **Carga alta:** si un técnico llega a `WORKLOAD_HIGH_ACTIVE_TICKETS` tickets activos (10 por defecto, `0` lo desactiva) aparece una insignia con texto. Solo informa: no impide asignarle más tickets.

Con los datos de demostración, Valentina Pizarro aparece con carga alta. Un Solicitante que abre `/workload` recibe un error 403.

---

## La reasignación masiva

Cuando un técnico no está disponible (vacaciones, licencia, renuncia...), el **Supervisor** o el **Administrador** pueden pasar sus tickets a otros técnicos en una sola operación, desde **Reasignación** del menú (`/reassign`) o desde el botón «Ir a reasignación» de la carga de trabajo:

1. **Elegir.** Se escoge al técnico de origen (también uno desactivado que aún tenga trabajo), se ven sus tickets en trabajo —con filtros por prioridad, estado y grupo, y todos marcados— y se eligen los técnicos de destino (con su carga actual, solo como información) y el motivo.
2. **Revisar.** Un resumen muestra cuántos tickets recibe cada técnico, con cuántos quedaría y a quién pasa cada ticket. **Todavía no se cambió nada.**
3. **Confirmar.** Se ejecuta y se muestra lo reasignado y lo omitido (por ejemplo, un ticket que mientras tanto se cerró o que otra persona ya movió), cada uno con su motivo.

Con varios destinos, los tickets se reparten por turnos. La asignación anterior queda registrada (no se sobrescribe), cada ticket anota en su historial el cambio de técnico y hay una única entrada de auditoría con el resumen. Los solicitantes reciben un aviso por ticket y cada técnico un resumen; ninguno incluye el motivo. Todo funciona sin JavaScript.

---

## Los reportes

El personal tiene la opción **Reportes** del menú (`/reports`). Responde qué pasó en un período: cuántos tickets entraron, cuántos se resolvieron y en cuánto tiempo.

- **Período:** los últimos 7, 30 (por defecto) o 90 días, el último año o unas fechas a elección (como mucho un año). Cada cifra se compara con el período anterior de la misma duración.
- **Filtros** por grupo, técnico, categoría y prioridad.
- **Cuatro cifras:** tickets creados, tickets resueltos, tiempo medio de resolución (con su mediana, que no se deja arrastrar por un caso excepcional) y tickets fuera de SLA.
- **Gráficos:** los creados por estado, por categoría y por prioridad, y el tiempo de resolución semana a semana. El gráfico semanal tiene su tabla equivalente.
- **Resumen por técnico:** cuántos tickets gestionó cada uno, cuántos siguen en trabajo, cuántos resolvió y cuánto tardó, más una fila con los tickets sin asignar.
- **Cada número abre el listado de esos tickets**, y el listado muestra exactamente esa cifra.
- **No es un ranking:** los técnicos se ordenan por apellido y nada califica a una persona. Un Técnico ve las cifras del equipo, pero en la tabla solo su propia fila. Un Solicitante no tiene acceso (error 403).

Los gráficos se dibujan en el servidor, sin librerías ni JavaScript. Las definiciones exactas (qué cuenta como resuelto, cómo se mide el tiempo) están en `docs/06_reglas_de_negocio.md` (RN-179).

---

## Exportar a CSV y Excel

El listado de tickets, los reportes y la auditoría tienen dos botones, **CSV** y **Excel**, que descargan **exactamente lo que se ve**: los mismos filtros, la misma pestaña, el mismo orden y solo lo que tu rol puede ver. Un Solicitante exporta sus tickets, sin datos internos; un Técnico exporta los reportes con solo su fila en la tabla por técnico; solo el Administrador exporta la auditoría.

- **Excel (XLSX)** se abre directamente, con las fechas como fechas y una hoja por sección en los reportes.
- **CSV** va en UTF-8 y separado por comas, para importarlo en otra herramienta. En una hoja de cálculo configurada en español, abrirlo con doble clic puede dejar todo en una columna: usa Excel o la opción «Importar» de tu hoja de cálculo.
- **Nada se ejecuta al abrir el archivo:** un texto que parece una fórmula (por ejemplo, un título que empieza por `=`) llega como texto. Es una defensa contra la inyección de fórmulas, un ataque conocido con las exportaciones.
- **Cada exportación queda en la auditoría,** con quién la hizo, qué, en qué formato, cuántas filas y con qué filtros.
- **Como mucho 50 000 filas.** Si son más, WorkDesk te pide acotar los filtros.

---

## La configuración

Desde **Administración**, el Administrador cambia sin tocar el `.env` los plazos, límites e interruptores de WorkDesk. Cada pantalla agrupa un tema:

| Pantalla | Qué se cambia |
| --- | --- |
| Seguridad y sesión | Intentos fallidos antes de bloquear, tiempo de bloqueo, longitud mínima de contraseña, inactividad y duración de la sesión |
| Cierre y reapertura | Si se cierran solos los tickets resueltos sin validar, su plazo y el plazo para reabrir |
| Archivos | Tamaño máximo por archivo (en KB) y archivos por ticket |
| Comentarios y edición | Tiempo para corregir un comentario propio y la reserva de un ticket mientras se edita |
| Creación de tickets | Si la ubicación es obligatoria y la sensibilidad de la advertencia de duplicados |
| Carga y planificador | La marca de «carga alta» y la frecuencia del planificador |
| SLA | Los objetivos por prioridad, el calendario laboral y el interruptor general del SLA |
| Notificaciones | Qué aviso interno recibe cada destinatario |
| Auditoría | No cambia nada: consulta quién hizo qué, los accesos y la historia de cada ticket (ver más abajo) |

- **El `.env` es solo el valor inicial:** mientras nadie guarde otro, rige el de la variable de entorno (o el de fábrica). Cada valor guardado se marca «Valor propio» y se puede **Restablecer**.
- Los valores se validan juntos (por ejemplo, la renovación del bloqueo debe ser menor que su duración), con el error junto a su campo, y cada cambio queda en la auditoría con un motivo opcional.
- Si otra persona cambió la misma pantalla mientras la editabas, no se guarda nada y se avisa.
- **Con el SLA apagado** no se muestra ni se avisa nada del SLA, pero se sigue calculando: al encenderlo, todo está al día.
- **La auditoría** (**Administración → Auditoría**, solo el Administrador) reúne tres registros que nadie puede modificar ni borrar. **Administrativa** muestra quién cambió qué, con el antes y el después y el motivo. **Accesos** muestra cada inicio de sesión, cada intento fallido con su causa y cada cierre de sesión, con la IP. **Tickets** muestra todo lo que pasó en cada ticket, también lo interno. Se filtra por fechas, persona, tipo de acción, entidad, resultado, IP o número de ticket.
- **Los avisos se apagan, no se inventan:** la pantalla de notificaciones solo permite apagar o encender los avisos que WorkDesk ya sabe enviar, así que ningún ajuste puede mandar algo interno a un Solicitante. Dos avisos son obligatorios.

---

## La base de conocimiento

**Base de conocimiento**, en el menú lateral, la ven los cuatro roles:

- **Portada:** búsqueda, categorías, destacados y recientes. La búsqueda entiende el español («impresoras» encuentra «impresora») y no distingue tildes.
- **Quién ve qué:** el Solicitante, los artículos publicados y públicos; el Técnico, además sus propios borradores y los privados; el Supervisor y el Administrador, todo. Un artículo que no puedes leer responde como si no existiera.
- **Quién escribe:** el personal crea borradores; el Técnico edita los suyos mientras sean borradores; el Supervisor y el Administrador publican, retiran de publicación y destacan; solo el Administrador desactiva (no se borra nada). Cada acción tiene su confirmación y queda auditada.
- **En los tickets:** el personal vincula artículos a un ticket (también a uno cerrado) y crea un borrador a partir de la resolución, con el enlace **Crear artículo desde la resolución**. El Solicitante ve en su ticket los artículos públicos vinculados.
- **Posibles duplicados:** al crear un ticket, si hay tickets abiertos y recientes que parecen tratar de lo mismo, se muestran antes de crearlo. Nunca impide crear ni enseña tickets que no puedes ver.

---

## Consultar y buscar tickets

La opción **Tickets** (para el personal) o **Mis tickets** (para el Solicitante), en el menú lateral, lista los tickets que cada persona puede ver:

- **Pestañas:** Todos, Abiertos y Cerrados, cada una con su contador. Se abre en **Abiertos**, que incluye todo lo que no está Cerrado (un ticket Resuelto sigue abierto porque espera la confirmación del solicitante).
- **Buscador:** acepta el número (`12` o `#12`), parte del título o de la descripción. El personal también puede escribir el nombre de un solicitante. La barra superior busca igual, en todas las pestañas.
- **Filtros:** estado y prioridad (y, para el personal, el SLA, incluida la opción «En riesgo»); y, en "Más filtros", categoría, ubicación, fechas de creación, de cierre y de resolución, «Solo en trabajo» (ni resueltos ni cerrados) y, para el personal, técnico («Sin asignar» incluido) y grupo; el Solicitante tiene además «Solo los que esperan tu revisión». Se pueden combinar entre sí y con el buscador. La tabla del personal muestra también los técnicos y el grupo de cada ticket.
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

Una lista de comprobación, de media hora si la sigues entera, para ver con tus propios ojos lo que hace WorkDesk hasta `v0.7.0`. Parte de una instalación terminada: los pasos 1 a 8 de la [preparación inicial](#preparación-inicial), es decir, con los usuarios de demostración (personas de cada rol), las categorías y ubicaciones de la demostración y los tickets de ejemplo ya cargados. Si prefieres no cargar los tickets de ejemplo, crea algunos a mano desde **Crear ticket**.

### Tener tickets con los que probar

Para ver la paginación, la búsqueda, los filtros y los historiales hacen falta muchos tickets. WorkDesk incluye un comando opcional que carga 108 tickets de demostración:

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

- **Puedes ejecutarlo de nuevo cuando quieras y no duplica nada.** Cada ticket de la lista tiene una `clave` estable, así que los que ya existen no se vuelven a crear: se **refrescan**. Sus fechas (creación, historial, solicitantes y última modificación) se recalculan respecto del día en que lo ejecutas, de modo que la demostración siempre parece reciente. Responde `Tickets demo creados: 0. Actualizados (ya existían): 108.`
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

### Artículos de demostración

```bash
python -m flask --app src.workdesk seed-demo-articles
```

Carga 11 artículos de ejemplo con los servicios reales: publicados y borradores, públicos y privados, destacados y de distintas categorías. Si ya cargaste los tickets de demostración, vincula cinco artículos con su ticket. Necesita `seed-catalogs` y `seed-demo`, usa las categorías `Redes`, `Hardware`, `Correo` e `Impresoras` si existen (si no, la de respaldo, y te avisa), no repite un artículo ya cargado y no se ejecuta con `APP_ENV=production`.

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
14. **Objetivos de SLA:** en **Administración → SLA** ves, sobre el calendario, la tarjeta **Objetivos por prioridad** con una fila por prioridad: primera respuesta, resolución, umbral de aviso y si el reloj se pausa mientras el ticket está en espera. Si ejecutaste `seed-catalogs`, ya traen los valores iniciales (por ejemplo, Crítica: 30 min / 4 h / 75 %); si la tarjeta dice **Sin definir** en alguna, usa **Definir** o ejecuta `seed-catalogs` (no pisa nada). Pulsa **Editar** en `Alta`. Las duraciones se escriben como las dirías: `30 min`, `4 h` o `1 h 30 min` (son horas laborales: solo cuentan dentro del calendario). Cámbiale la resolución a `1 h 30 min` y guarda: pasa a mostrarse así en la tabla. Prueba a escribir `4` (te pide la unidad), `1,5 h` (no admite decimales), `2 días` (no admite días), una primera respuesta mayor que la resolución, o un umbral de `0` o de `101`: cada error aparece junto a su campo y todos a la vez, y lo escrito no se pierde. Vacía **Primera respuesta** para dejarla sin objetivo (la tabla dice «Sin objetivo») y desmarca la pausa para ver «No». Pulsa **Desactivar** en `Baja`: pide confirmación con un motivo opcional y la fila queda atenuada como **Inactiva** (esa prioridad ya no tiene SLA); **Reactivar** la devuelve con los mismos objetivos. Para ver el control de ediciones simultáneas, abre **Editar** en dos pestañas, guarda en una y luego en la otra: la segunda avisa de que otra persona modificó los objetivos y no pisa el cambio. Cada cambio queda en la auditoría administrativa. Los objetivos se aplican a los tickets de forma automática (ver el paso siguiente).
15. **SLA de un ticket:** además de verlo en la interfaz (paso 18), puedes comprobarlo con un comando. Crea un ticket de prioridad **Alta** y apunta su número. En la terminal ejecuta `python -m flask --app src.workdesk sla-status 12` (cambia 12 por el número). Verás la prioridad, `SLA: dentro de plazo`, lo consumido (`0 min de 6 h`), cuándo vence y la lista de períodos con uno solo, **vigente**. Después prueba, volviendo a ejecutar el comando tras cada paso: **Iniciar trabajo** y **Poner en espera** (aparece un período nuevo y `SLA: pausado`: el tiempo en espera no cuenta), **Reactivar** (otro período, otra vez corriendo), **Cambiar prioridad** a Crítica con un motivo (se cierra el período y se abre otro con el objetivo de 4 h, descontando lo ya consumido: el reloj no se reinicia) y **Resolver** (el último período se cierra y el reloj se detiene). Si **Reabres** el ticket, sigue contando donde iba. El SLA corre solo en horario laboral del calendario: de noche y en fin de semana el consumo no avanza. Si cargaste tickets de demostración, `sla-status` también funciona con ellos (los de más días suelen salir vencidos).
16. **Notificaciones:** en la barra superior, a la izquierda de tu nombre, hay una **campana**. Los avisos reales los generan los eventos de un ticket (ver el paso 17); para ver el centro sin provocar nada, carga avisos de ejemplo: con tickets ya cargados, ejecuta en la terminal `python -m flask --app src.workdesk seed-demo-notifications --username TU_USUARIO` (cambia `TU_USUARIO` por el usuario con el que entraste) y recarga la página: la campana muestra un **número azul** con los avisos sin leer. Púlsala: abre **Notificaciones** (también está en el menú lateral). Las no leídas tienen un punto y un fondo azul suave. Prueba **No leídas** (solo esas), **Marcar como leída** en una (el número baja), el título de una que tenga ticket (la marca como leída y abre el ticket) y **Marcar todas como leídas** (el número desaparece). Con la página abierta el número se actualiza solo cada 30 segundos. Cada persona ve solo los suyos: los avisos de ejemplo se crean por persona y el contador de cada una es independiente (los del personal hablan de asignaciones y SLA; los de un Solicitante, de cambios de estado y de la solución de su ticket). **La campana no mantiene viva una sesión abandonada:** su consulta automática no cuenta como actividad. Para verlo sin esperar media hora, pon `SESSION_IDLE_MINUTES=1` en tu `.env`, reinicia WorkDesk, entra y deja una página abierta, sin tocar nada, durante más de un minuto (la campana seguirá consultando sola); al pulsar cualquier enlace vuelves al login con «Tu sesión expiró». Devuelve el valor a `30` al terminar.
17. **Avisos reales:** necesitas dos personas a la vez (un navegador normal y una ventana de incógnito). Como Administrador (o Supervisor), abre un ticket de `paula.contreras` y pulsa **Asignar**: asígnalo a `diego.soto`. En la otra ventana, entra como `paula.contreras`: la campana muestra un **1** y el aviso dice que el ticket ya tiene técnico. Entra como `diego.soto`: tiene el aviso «Ticket asignado». Ahora, como `diego.soto`, pulsa **Iniciar trabajo** y **Resolver**: `paula.contreras` recibe «Ticket en progreso» y después «Revisa la solución»; tú, que no hiciste esos cambios, ya no recibes nada. Como `paula.contreras`, comenta en el ticket: `diego.soto` recibe «Respuesta del solicitante». Escribe una **nota interna** como Administrador: la recibe `diego.soto` y `paula.contreras` no recibe nada (ni el texto de la nota). Los avisos nunca copian el contenido de los comentarios: dicen quién escribió y en qué ticket.
18. **Indicadores de SLA:** abre **Tickets**. Junto a Estado y Prioridad hay un filtro **SLA** y la tabla tiene una columna **SLA** con una insignia por ticket (verde «Dentro de SLA», ámbar «Próximo a vencer», roja «Vencido», gris «Pausado» o «Sin SLA») y, debajo, el tiempo laboral que queda o que se pasó. Elige **Vencido** en el filtro y pulsa **Filtrar**: quedan solo los vencidos y los contadores de las pestañas cambian con ellos. En **Ordenar por** elige **SLA más urgente**: primero los que vencen antes. Abre un ticket: bajo el **Resumen** hay una tarjeta **SLA** con la barra de consumo, cuándo vence y, plegados, sus **Períodos**. Ahora **Cambiar prioridad** en uno con el SLA vencido o próximo a vencer: arriba aparece una **alerta** que avisa antes de confirmar. Bájale la prioridad (con un motivo): los Supervisores del grupo del ticket (o todos, si no tiene grupo) reciben el aviso «Prioridad bajada con el SLA en riesgo». Si tus tickets de ejemplo son anteriores a esta versión y no ves «Próximo a vencer», ejecuta antes `sla-rebuild`.
19. **Planificador (avisos de SLA y cierre automático):** se prueba en una segunda terminal y tiene un detalle: si tu base ya tenía tickets antes de actualizar a esta versión, la migración dejó como «ya avisados» los SLA que entonces estaban vencidos (para que la primera ejecución no te llene de avisos atrasados), así que el comando diría `0` en todo. Para ver los avisos hay que reiniciar esa marca en unos pocos períodos. Con `seed-demo-tickets` cargado:

    1. Abre `psql` conectado a `workdesk_dev` y ejecuta, una tras otra, estas dos sentencias (la primera elige hasta 3 SLA vencidos de tickets con técnico asignado; la segunda, hasta 2 próximos a vencer):

       ```sql
       UPDATE tickets_sla_periodos
       SET fecha_aviso_umbral_enviado = NULL, fecha_aviso_vencimiento_enviado = NULL
       WHERE id IN (
           SELECT p.id FROM tickets_sla_periodos p
           WHERE p.fecha_fin IS NULL AND p.fecha_vencimiento_resolucion <= now()
             AND EXISTS (SELECT 1 FROM tickets_tecnicos tt
                         WHERE tt.ticket_id = p.ticket_id AND tt.fecha_desasignacion IS NULL)
           ORDER BY p.id LIMIT 3
       );

       UPDATE tickets_sla_periodos
       SET fecha_aviso_umbral_enviado = NULL, fecha_aviso_vencimiento_enviado = NULL
       WHERE id IN (
           SELECT id FROM tickets_sla_periodos
           WHERE fecha_fin IS NULL AND fecha_umbral_aviso <= now()
             AND fecha_vencimiento_resolucion > now()
           ORDER BY id LIMIT 2
       );
       ```

       Responden `UPDATE 3` y `UPDATE 2` (menos si tu demostración tiene menos casos de cada tipo).
    2. En otra terminal (carpeta del proyecto, entorno virtual activado) ejecuta `python -m flask --app src.workdesk run-scheduler --once`. Imprime una línea como `SLA próximo a vencer: 2. SLA vencido: 3. Tickets cerrados automáticamente: 0. Errores: 0.` (los números son los de los dos `UPDATE`).
    3. Ejecútalo otra vez: todo `0`, porque ya avisó y no repite.
    4. Entra como `camila.rojas` (Supervisor) y abre **Notificaciones**: están los avisos «SLA vencido» y «SLA próximo a vencer» con el nombre de cada ticket. Abre uno de los vencidos: en su historial aparece **SLA vencido**, hecho por **Sistema** (el incumplimiento queda registrado; solo lo ve el personal). Entra como el técnico asignado a uno de esos tickets (por ejemplo `diego.soto`): solo ve el de su ticket. Un Solicitante no recibe ninguno.
    5. **Cierre automático:** como Técnico, abre un ticket y pulsa **Resolver**. En `psql`: `UPDATE tickets SET fecha_resolucion = now() - interval '25 hours' WHERE public_id = '12';` (cambia `12` por su número; responde `UPDATE 1`). Ejecuta de nuevo el comando: ahora dice `Tickets cerrados automáticamente: 1`. El ticket queda **Cerrado** con motivo «Inactividad», el historial dice «Ticket cerrado» hecho por **Sistema** y su solicitante y su técnico reciben «Ticket cerrado automáticamente». Se puede reabrir como cualquier otro.

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
13. **SLA:** no hay columna, filtro ni orden de SLA, y el detalle no tiene la tarjeta: el SLA es solo del personal. Si escribes `?sla=vencido` en la dirección del listado, se ignora.
14. **Notificaciones:** la barra lateral incluye **Notificaciones** y, arriba, la campana. Si cargaste avisos de ejemplo para esta persona (`seed-demo-notifications --username paula.contreras`, ver el paso 16 del Administrador), ves los suyos: un cambio de estado, una respuesta del equipo, la revisión de la solución de un ticket, un cierre y la creación de un ticket. No hay avisos de SLA ni de notas internas: eso es solo del personal.

### 3. Como Técnico

Entra, por ejemplo, como `diego.soto`.

1. **Tickets** muestra todos los tickets (con los datos de demostración, los 108), incluidos los que crearon otras personas.
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

### 5. Dashboards, carga de trabajo y reasignación

1. **Dashboard del Solicitante.** Entra como `javiera.torres`: cuatro tarjetas (abiertos, en progreso, requieren tu revisión y cerrados recientes), un aviso con las soluciones por revisar, tus tickets y notificaciones recientes. Haz clic en cada tarjeta: el listado se abre filtrado y su total es la cifra de la tarjeta. No hay SLA, grupos ni carga.
2. **Dashboard del personal.** Entra como `camila.rojas`: seis contadores (abiertos, sin asignar, críticos, fuera de SLA, próximos a vencer y en espera), los tickets prioritarios con su SLA, la carga compacta, los tickets por prioridad y la actividad reciente. Un aviso te dice si hay críticos sin asignar. Como `diego.soto` ves además **Mi trabajo**; como Administrador, un bloque de **Administración**.
3. **Carga de trabajo.** Abre **Carga de trabajo** (técnicos, supervisores y administradores): por técnico y por grupo, con una barra de distribución por prioridad y la insignia **Carga alta** (Valentina Pizarro con los datos de demostración). Filtra por grupo o prioridad: las cifras y los enlaces siguen coincidiendo con el listado. Un solicitante que abre `/workload` recibe **Acceso denegado**.
4. **Reportes.** Como `camila.rojas`, abre **Reportes** y elige «Últimos 90 días»: las cuatro cifras, los gráficos y la tabla por técnico. Haz clic en cualquier número: el listado se abre filtrado y su pestaña «Todos» muestra esa cifra. Despliega «Ver como tabla» bajo el gráfico semanal. Pulsa **Excel**: el archivo trae las mismas cifras, una hoja por sección. En **Tickets**, filtra por una prioridad y pulsa **CSV**: el archivo trae exactamente esas filas, en ese orden. Como `diego.soto`, la tabla muestra solo su fila; un solicitante que abre `/reports` recibe **Acceso denegado**.
5. **Reasignación masiva.** Como `camila.rojas`, abre **Reasignación**, elige a Valentina Pizarro, marca como destino a Diego Soto y a Felipe Araya, escribe un motivo y pulsa **Revisar la reasignación**: ves quién recibe cuántos tickets y todavía no cambió nada. **Confirmar** ejecuta (esto sí modifica tus datos de demostración) y muestra lo reasignado y lo omitido. Un técnico que abre `/reassign` recibe **Acceso denegado**.

### 6. Configuración y base de conocimiento

1. **Configuración.** Como Administrador abre **Administración → Archivos**, baja el tamaño máximo a `512` KB y guarda: el campo queda como «Valor propio» y, en **Crear ticket**, la ayuda dice «archivos de 512 KB». Pulsa **Restablecer** para volver al inicial.
2. **Ubicación obligatoria.** En **Creación de tickets** activa «Exigir la ubicación». Como `javiera.torres`, **Crear ticket** ya no ofrece «Sin ubicación» y no deja crearlo sin elegir una. Desactívala al terminar (los tickets de demostración tienen tickets sin ubicación).
3. **SLA apagado.** En **SLA** pulsa **Desactivar SLA** (con un motivo): el listado, el detalle y los dashboards dejan de mostrar el SLA. Actívalo de nuevo y todo vuelve, al día.
4. **Avisos.** En **Notificaciones** desmarca la casilla «Comentario nuevo» de la columna Solicitantes y guarda. Como `diego.soto` comenta un ticket de `javiera.torres`: ella ya no recibe el aviso. Enciéndelo de nuevo.
5. **Base de conocimiento.** Con los [artículos de demostración](#artículos-de-demostración) cargados, busca `impresora` como `javiera.torres`: solo ve los publicados y públicos. Como `diego.soto` abre **Gestionar artículos**, crea un borrador y comprueba que la solicitante no lo encuentra; como `camila.rojas`, publícalo.
6. **Conocimiento en un ticket.** Como `diego.soto`, abre un ticket resuelto y pulsa **Crear artículo desde la resolución**: el borrador se propone con su título, categoría y solución, y queda vinculado al ticket.
7. **Posibles duplicados.** Como `javiera.torres`, crea un ticket titulado `la impresora no imprime`: antes de crearlo ves los tickets parecidos y **Crear de todos modos**.
8. **Liberar un bloqueo.** Con `diego.soto` editando un ticket, entra como `camila.rojas` en ese ticket y pulsa **Liberar bloqueo**: la pantalla de Diego avisa que perdió la reserva.
9. **Auditoría.** Como Administrador abre **Administración → Auditoría**. En **Administrativa** verás lo que hiciste en los pasos anteriores (el tamaño de archivo, el SLA, los avisos), con el antes y el después en «Detalle». En **Accesos**, tus inicios de sesión. Si antes te equivocaste de contraseña, también ese intento fallido con su causa. En **Tickets**, filtra por un número para ver toda su historia, notas internas incluidas.

### Lo que todavía no verás

- Los avisos de SLA y el cierre automático solo ocurren mientras `run-scheduler` está en marcha (ver [Ejecutar el planificador](#ejecutar-el-planificador)). Crear un ticket no avisa a nadie.
- El aviso de quién edita no se actualiza solo: aparece al abrir o recargar la pantalla (la actualización en tiempo real es posterior al MVP).
- La pantalla de Estados y transiciones cambia el nombre, la descripción y las transiciones; el color y el orden de los estados no se editan todavía (llegan con el pulido visual, `v0.9.0`).
- El detalle de un ticket muestra sus secciones (actividad, archivos, relaciones e historial) una debajo de otra; las pestañas llegan con el pulido visual.
- Los dashboards muestran solo cifras exactas: los gráficos y las comparaciones con el período anterior están en **Reportes**.
- Las excepciones de SLA, los tickets «sin actividad reciente» y los avisos internos de sobrecarga todavía no tienen fase: necesitan reglas que no se han decidido.
- La retención (cuánto tiempo se conservan las notificaciones leídas, los accesos y los respaldos) llega en la próxima entrega de `v0.8.0`.

---

## Solución de problemas

| Síntoma | Causa probable | Qué hacer |
| --- | --- | --- |
| `Falta configuración obligatoria: SECRET_KEY` (o `SQLALCHEMY_DATABASE_URI`) | `.env` no existe, no está en la raíz del proyecto o tiene la variable vacía. `SQLALCHEMY_DATABASE_URI` se toma de `DATABASE_URL`. | Comprueba que `.env` está junto a `README.md` y que `SECRET_KEY` y `DATABASE_URL` tienen valor. |
| `SECRET_KEY tiene el valor de ejemplo` | Copiaste en `.env` el texto de ejemplo de este README en lugar de una clave. | Genera una con `python -c "import secrets; print(secrets.token_hex(32))"` y pégala en `SECRET_KEY`. |
| `En producción SECRET_KEY debe tener al menos 32 caracteres` | Con `APP_ENV=production` la clave es demasiado corta para firmar sesiones con seguridad. | Genera una nueva con el mismo comando (da 64 caracteres). Todos tendrán que iniciar sesión otra vez. |
| `El modo depuración no se puede usar en producción` | Arrancaste con `--debug` o `FLASK_DEBUG=1` y `APP_ENV=production`. | Quita `--debug` y `FLASK_DEBUG`. El depurador solo es para desarrollo. |
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
| **Administración → SLA** muestra «Sin definir» en las prioridades | Cargaste los catálogos antes de que existieran los objetivos de SLA (`v0.5.0`, entrega 3). | Ejecuta `seed-catalogs`: crea los objetivos que faltan (`políticas de SLA: 4`) y no pisa nada. También puedes definirlos a mano con **Definir**. |
| `seed-demo-tickets`: "Hay transiciones deshabilitadas que la demostración necesita..." | Un Administrador deshabilitó una transición que los tickets de demostración recorren. | Habilítala en **Administración → Estados y transiciones** y vuelve a intentarlo. No se cargó ningún ticket. |
| La campana no muestra número y **Notificaciones** está vacío | Los avisos aparecen cuando pasa algo en un ticket (asignarlo, cambiar su estado, comentar), y crear un ticket no avisa a nadie: una instalación nueva no tiene ninguno. | Para ver el centro funcionando, ejecuta `python -m flask --app src.workdesk seed-demo-notifications --username TU_USUARIO` (necesita tickets que esa cuenta pueda ver, por ejemplo los de `seed-demo-tickets`). |
| `seed-demo-notifications`: "No existe el usuario: ..." o "Faltan los usuarios de demostración..." | El usuario de `--username` está mal escrito, o ejecutaste el comando sin opciones y falta `seed-demo`. | Revisa el nombre de usuario, o ejecuta antes `seed-demo`. |
| `seed-demo-tickets` termina con `Aviso: Categoría «...» no encontrada` (o `Ubicación`) | La categoría o ubicación no existe con ese nombre exacto. | Los tickets se cargaron igual, con `Sin clasificar` o sin ubicación. Para corregirlo, crea el valor con el nombre exacto ([Configurar categorías y ubicaciones](#configurar-categorías-y-ubicaciones)) y recrea la base de desarrollo, o edita esos tickets a mano. |
| `seed-demo-tickets` dice "Creados: 0. Actualizados (ya existían): 108" | Ya los habías cargado: el comando no duplica, solo refresca sus fechas respecto de hoy. | Es lo esperado. |
| `create-admin`: "Ya existe un usuario con rol ADMINISTRADOR." | El comando solo crea el Administrador inicial. | Entra con esa cuenta; los demás usuarios se crean en **Administración → Usuarios**. |
| `create-admin`: "Username: Usa solo letras minúsculas..." (o `Email: ...`) | El username o el correo no cumplen las reglas de la pantalla de alta. | Vuelve a ejecutarlo con un username de 3 a 50 caracteres (letras minúsculas, números, `.`, `-` y `_`) y un correo con forma `algo@dominio.tld`. No se creó nada. |
| "Hubo demasiados intentos fallidos desde este equipo" | Desde esa IP se alcanzó el límite de intentos fallidos (`LOGIN_MAX_FAILED_PER_IP`, 20 por defecto) dentro del tiempo de bloqueo. | Espera ese tiempo (`LOGIN_LOCK_MINUTES`). Si todas las personas llegan a WorkDesk a través de un mismo proxy, desactiva el límite con 0 en **Administración → Seguridad y sesión**. |
| Tras actualizar a `v0.8.0` todos vuelven a ver el login | La cookie de sesión cambió de nombre, así que las sesiones anteriores dejan de valer. | Es esperado y ocurre una sola vez: inicia sesión de nuevo. |
| Siempre aparece "Usuario o contraseña incorrectos." aunque los datos sean correctos | Tras 5 intentos fallidos la cuenta se bloquea 15 minutos, y el mensaje es el mismo a propósito para no revelar nada. | Espera esos 15 minutos (`LOGIN_LOCK_MINUTES`). Si es otra persona, un Administrador puede restablecerle la contraseña y eso levanta el bloqueo. |
| "Tu sesión expiró. Inicia sesión nuevamente." | Pasaron 30 minutos sin actividad o 8 horas desde que iniciaste sesión. | Es el comportamiento esperado; se ajusta con `SESSION_IDLE_MINUTES` y `SESSION_MAX_HOURS`. |
| Inicias sesión y vuelves a ver el login | Con `SESSION_COOKIE_SECURE=true` y HTTP, algunos navegadores no guardan la cookie de sesión. | En local usa `SESSION_COOKIE_SECURE=false` y reinicia WorkDesk. |
| En **Crear ticket** solo aparece `Sin clasificar` como categoría | Todavía no se crearon categorías. | **Administración → Categorías → Nueva categoría** (ver [Configurar categorías y ubicaciones](#configurar-categorías-y-ubicaciones)). |
| Las fechas aparecen en hora UTC | `APP_TIMEZONE` no es un nombre de zona válido. | Usa un nombre IANA, como `America/Santiago`, y reinicia WorkDesk. |
| El puerto 5000 está ocupado | Otro programa lo usa (en macOS, AirPlay). | Añade `--port 5001` al comando de arranque. |
| Tests: "Falta TEST_DATABASE_URL para ejecutar los tests." | `.env` no define `TEST_DATABASE_URL`. | Defínela apuntando a `workdesk_test`. |
| Tests: "Los tests solo pueden ejecutarse sobre workdesk_test." | `TEST_DATABASE_URL` apunta a otra base. | Corrígela. La protección es intencional: protege `workdesk_dev`. |
| Tests que fallan al azar con tablas que "no existen" | Hay dos ejecuciones de `pytest` a la vez sobre `workdesk_test`. | Ejecuta una sola cada vez: comparten la misma base y, al terminar, cada una elimina el esquema que usa. |
| Tests: `unrecognized arguments: -n` | No está instalado `pytest-xdist` (entorno anterior a esta versión). | Ejecuta `python -m pip install -r requirements-dev.txt`, o corre la suite en serie sin `-n`. |
| `backup-create`: «No se encontró pg_dump» | Las herramientas de cliente de PostgreSQL no están en el `PATH`. | Define `PG_BIN_DIR` con su carpeta (en Windows, `C:\Program Files\PostgreSQL\18\bin`, con tu versión). |
| `backup-create`: «pg_dump falló: ... server version mismatch» (o «versión del servidor no coincide») | El `pg_dump` del `PATH` es más antiguo que el servidor. | Apunta `PG_BIN_DIR` a la carpeta `bin` de la misma versión que el servidor. |
| `backup-create`: «Ya hay un respaldo en curso de esta base de datos.» | Otro `backup-create` está trabajando (quizá uno programado). | Espera a que termine. No se creó nada. |
| `backup-verify`: «La firma no corresponde a esta instalación» | Se cambió la `SECRET_KEY` después de crear el respaldo, viene de otra instalación o alguien modificó su manifiesto. | Si sabes de dónde viene (por ejemplo, de antes de cambiar la clave), está bien guardarlo; si no, no lo restaures. |
| `backup-restore`: «Hay N conexiones más a la base de datos» | WorkDesk, el planificador u otro programa (pgAdmin) siguen conectados. | Detenlos y vuelve a intentarlo. Si sabes de qué son, `--ignore-connections`. No se restauró nada. |
| `backup-restore`: «...que este código no conoce» | El respaldo es de una versión más nueva de WorkDesk. | Actualiza el código (`git pull`) a esa versión o una posterior y vuelve a intentarlo. |
| `backup-restore`: «No se pudo crear el respaldo de lo actual» | `pg_dump` no puede leer la base actual (dañada, o le faltan tablas). | Si de verdad no hay nada que conservar, repite con `--skip-safety-backup`. |
| `backup-restore` termina con «...El respaldo es de una versión anterior» | El respaldo es de una versión anterior del esquema. | Ejecuta `python -m flask --app src.workdesk db upgrade` antes de volver a iniciar WorkDesk. |
| **Estado del sistema**: el planificador «parece detenido» | `run-scheduler` no está en marcha (o la tarea programada no corre). | Ábrelo como se explica en [Ejecutar el planificador](#ejecutar-el-planificador). |
| `backup-list` señala «Restos de respaldos interrumpidos» | Un `backup-create` se cortó a la mitad (se apagó el equipo, se cerró la terminal). | Borra esas carpetas `.tmp-respaldo-*` y crea un respaldo nuevo. |
| Tests: «El módulo de tests ... no pertenece a ningún área» | Se añadió un archivo `tests/test_*.py` sin registrarlo. | Añádelo a `AREAS` en `tests/areas.py`. |

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
GET       /admin/sla
GET POST  /admin/sla/calendar
GET POST  /admin/sla/priorities/<id>/edit
GET POST  /admin/sla/priorities/<id>/deactivate
GET POST  /admin/sla/priorities/<id>/activate
GET POST  /admin/sla/activate
GET POST  /admin/sla/deactivate
GET POST  /admin/settings/<grupo>
POST      /admin/settings/<grupo>/reset/<variable>
GET POST  /admin/notifications
GET       /admin/audit
GET       /reports
GET       /reports/export
GET       /tickets/export
GET       /admin/audit/export
GET       /admin/backups
GET       /admin/system
GET       /knowledge
GET       /knowledge/<id>
GET       /knowledge/manage
GET POST  /knowledge/new
GET POST  /knowledge/<id>/edit
GET POST  /knowledge/<id>/actions/<accion>
GET       /tickets/<id>/knowledge
POST      /tickets/<id>/knowledge/add
GET POST  /tickets/<id>/knowledge/<link_id>/remove
GET POST  /tickets/<id>/lock/revoke
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
GET       /workload
GET       /reassign
POST      /reassign/review
POST      /reassign/confirm
GET       /notifications
POST      /notifications/<id>/read
POST      /notifications/<id>/open
POST      /notifications/read-all
GET       /notifications/unread-count
GET       /health
```

`/dashboard`, `/tickets` (y todas sus rutas), `/notifications` (y todas sus rutas) y `/account/password` requieren una sesión autenticada. Cada persona ve solo sus notificaciones: la de otra responde 404. `/admin` (incluidas las pantallas de catálogos y de estados y transiciones) y todas las rutas `/users` requieren el rol Administrador; `/groups`, el rol Administrador o Supervisor.

El detalle de un ticket (`/tickets/<public_id>`) lo ve el personal en todos los casos, y el Solicitante solo si creó el ticket o es su solicitante. Si no tiene acceso, la respuesta es un **404** idéntica a la de un ticket inexistente: los números son correlativos y un 403 permitiría descubrir cuáles existen. Las rutas de edición, de prioridad y de solicitantes son solo del personal: quien ve el ticket pero no puede usarlas recibe un **403**. En los comentarios, una nota interna que el usuario no puede ver responde **404** (como si no existiera) y editar o eliminar un comentario ajeno, o uno propio fuera del plazo, responde **403**. Un test recorre todo el mapa de rutas y comprueba estas reglas por rol, así que una ruta nueva queda cubierta sin tocarlo.

Si el usuario tiene una contraseña temporal pendiente de cambio, el sistema solo le permite acceder a `/account/password` y cerrar sesión hasta que la cambie.

`/dashboard` muestra un resumen distinto según el rol (el Solicitante, el del personal con «Mi trabajo» para el Técnico y un bloque más para el Administrador). `/workload` es solo del personal y `/reassign`, solo del Supervisor y el Administrador: los demás roles reciben un 403.

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

La seguridad no es una capa que se añadió al final: cada entrega la revisa, y las defensas importantes tienen una prueba automática que falla si alguien las debilita.

**Identidad y contraseñas**

- Inicio de sesión con `username` y contraseña. Sin registro público, sin recuperación por correo (WorkDesk es local) y sin «recordarme».
- Contraseñas guardadas con **Argon2id** (64 MiB y 3 pasadas, por encima del mínimo que recomienda OWASP; una prueba impide bajarlos). Si los parámetros cambian, el hash se recalcula al iniciar sesión.
- Política de contraseñas única (largo mínimo configurable, 12 por defecto) para el alta, el cambio propio, el restablecimiento y `create-admin`.
- **Bloqueo temporal** tras 5 intentos fallidos (15 minutos, configurables). La fila del usuario se bloquea en la base de datos durante cada intento: ni siquiera muchos intentos enviados en paralelo consiguen más oportunidades de las permitidas.
- **Límite por equipo:** tras 20 intentos fallidos desde una misma IP, en cualquier cuenta (configurable, 0 lo apaga), ese equipo no puede seguir probando durante el tiempo de bloqueo. Frena a quien prueba pocas contraseñas en muchas cuentas.
- **Registro de accesos:** cada intento de entrar y cada salida queda en `eventos_autenticacion`, con su causa interna, la IP y el navegador, nunca con la contraseña. Cada persona ve en «Mi cuenta» los últimos accesos de su cuenta.
- **El mensaje de error no delata nada:** es el mismo para un usuario inexistente, inactivo, bloqueado o con la contraseña equivocada, y el **tiempo de respuesta** también (los caminos sin cuenta que verificar gastan una verificación de relleno).
- Las contraseñas temporales se muestran una sola vez y obligan a cambiarlas al entrar.

**Sesión**

- Cookie `HttpOnly`, `SameSite=Lax` y `Secure` por HTTPS, con un nombre que no delata el framework (`workdesk_session`; por HTTPS, `__Host-workdesk_session`, que el navegador solo acepta segura y sin dominio).
- Límite de inactividad (30 minutos) y de duración (8 horas). La consulta automática de la campana no cuenta como actividad.
- El inicio y el cierre de sesión vacían la sesión entera.
- Cambiar el rol, desactivar una cuenta o cambiar la contraseña invalida al instante todas sus sesiones (`token_version`).

**Cada petición**

- **Autorización en el servidor**, nunca solo ocultando botones (`security/authorization.py`). Quién ve qué se decide en la consulta SQL, y cada condición SQL tiene su equivalente en Python con una prueba que compara los dos.
- Un ticket que no puedes ver responde **404**, igual que uno que no existe: así no se puede descubrir qué números existen.
- **CSRF** en todo lo que cambia algo.
- **Cabeceras de seguridad en todas las respuestas** (`security/headers.py`):
  - una política de contenido (CSP) que solo permite lo que sirve WorkDesk, sin JavaScript en línea;
  - no se puede incrustar en otra página;
  - aislamiento entre orígenes (`Cross-Origin-Opener-Policy` y `Cross-Origin-Resource-Policy`);
  - sin acceso a cámara, micrófono, ubicación ni pagos (`Permissions-Policy`);
  - `nosniff`, `Referrer-Policy`;
  - nada en caché si tiene datos de la sesión.
- Los archivos adjuntos se comprueban por su contenido (no por lo que dice el navegador), se guardan con un nombre interno aleatorio y se descargan siempre como archivo.

**Al arrancar**

- En producción, WorkDesk **no arranca** con una `SECRET_KEY` de menos de 32 caracteres (firma la cookie de sesión) ni con el modo depuración (el depurador permite ejecutar código desde el navegador). En cualquier entorno rechaza el texto de ejemplo de este README como clave.

**Trazabilidad**

- Toda acción administrativa queda en una **auditoría de solo añadir**: quién, cuándo, qué cambió (antes y después) y por qué, sin contraseñas ni secretos. También el Administrador inicial y los recálculos de SLA, como acciones del sistema.
- El historial de cada ticket también es de solo añadir. Ninguna clave foránea borra en cascada, así que nada desaparece en silencio (hay una prueba para cada regla).

**Redes de seguridad automáticas.** `tests/test_route_protection.py` recorre **todas** las rutas registradas y falla si alguna se puede abrir sin iniciar sesión (salvo `/login`, `/health` y los archivos estáticos) o si alguna ruta POST acepta una petición sin token CSRF. `tests/test_route_authorization.py` comprueba el rol y la propiedad del ticket en cada ruta. Una ruta nueva queda cubierta sin tocar los tests.

---

## Manejo de errores

Cualquier error recibe una página de WorkDesk con un mensaje comprensible, nunca la página técnica del framework: 400, 403, 404, 405 (una acción que la dirección no admite), 413 (archivo demasiado grande) y 500 tienen su texto, y cualquier otro uno genérico.

Ninguna página de error muestra la excepción, la pila, consultas SQL, rutas internas ni credenciales: eso queda solo en el log.

---

## Logging

El logging técnico utiliza el módulo estándar `logging` de Python. Los archivos se guardan en `instance/logs/` (o en `LOG_DIR`), **uno por proceso**:

| Archivo | Quién escribe |
| --- | --- |
| `workdesk.log` | La aplicación web y los comandos |
| `scheduler.log` | El planificador (`run-scheduler`) |

Están separados porque el servidor web y el planificador funcionan a la vez: si escribieran el mismo archivo, en Windows la rotación fallaría (no se puede renombrar un archivo que otro programa tiene abierto) y el log crecería sin control.

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
4970 tests
```

Los tests cubren, por área (la tabla de más abajo las lista): autenticación y sesiones; usuarios y autorización; catálogos; el núcleo de tickets y todo su ciclo de vida (con las carreras entre dos personas probadas con dos hilos); SLA, calendario laboral y planificador; notificaciones internas; los comandos que cargan datos de demostración; y la plataforma.

Hay seis redes de seguridad que no dependen de recordar nada al añadir código:

- **`tests/test_route_protection.py` y `tests/test_route_authorization.py`** recorren el mapa de rutas real: toda ruta exige sesión, toda ruta POST exige token CSRF, el ticket ajeno responde 404 y el rol sin permiso, 403. Una ruta nueva queda cubierta sin tocar el test.
- **`tests/test_pages_smoke.py`** abre todas las pantallas con los 108 tickets de demostración para cada rol y vigila un **presupuesto de consultas** por petición: si una pantalla empieza a hacer una consulta por fila, falla aunque funcione bien con pocos datos.
- **`tests/test_migrations.py`** comprueba que las migraciones suben, coinciden con los modelos (`db check`), bajan y vuelven a subir, y que una instalación construida **solo con ellas** sigue los pasos de este README y deja lo esperado en la base de datos (secuencias, valores por defecto y restricciones, que `db check` no ve).
- **`tests/test_docs_coherence.py`** exige que cada variable de entorno, comando propio, migración y ruta figuren en el README, `.env.example` y `PROJECT_CONTEXT.md`.
- **`tests/test_security_headers.py`** vigila las cabeceras de seguridad de todas las respuestas y la forma común de los errores JSON.
- **`tests/test_data_integrity.py`** recorre el esquema: ninguna clave foránea borra en cascada y toda tabla de eventos (auditoría, historial y las que vengan) rechaza que se modifiquen o borren sus filas. Una tabla nueva queda cubierta sin tocar el test.

El detalle de qué cubre cada módulo y cuántos tests aportó cada entrega está en [`docs/14_historial_de_implementacion.md`](docs/14_historial_de_implementacion.md).

Para ejecutarlos hacen falta el entorno virtual activo, PostgreSQL en ejecución, la base `workdesk_test` creada y `TEST_DATABASE_URL` definida en `.env` (ver [Configuración de PostgreSQL](#configuración-de-postgresql) y [Variables de entorno](#variables-de-entorno)). No hace falta aplicar migraciones ni cargar datos: la suite crea sus propias tablas. `requirements-dev.txt` trae lo necesario, incluido `pytest-xdist` para ejecutarla en paralelo.

### Ejecutar los tests

| Qué quieres | Comando |
| --- | --- |
| **La suite completa** (antes de un commit o de un Pull Request), en paralelo | `python -m pytest -n 6` |
| La suite completa, en serie | `python -m pytest` |
| Solo un área | `python -m pytest -m sla` |
| Varias áreas | `python -m pytest -m "tickets or notifications"` |
| Solo los tests que no usan la base de datos (segundos) | `python -m pytest -m unit` |
| Un archivo o un solo test | `python -m pytest tests/test_worktime.py` · `python -m pytest tests/test_worktime.py::nombre_del_test` |
| Solo lo que falló la última vez | `python -m pytest --lf` |
| Los 10 tests más lentos | `python -m pytest --durations=10` |

Cada test lleva el marcador de su **área** (la lista de módulos de cada una está en `tests/areas.py`):

| Área | Qué cubre |
| --- | --- |
| `platform` | La aplicación, las rutas, el layout, el formato, los comandos, la auditoría y la propia suite |
| `auth` | Autenticación, sesiones, contraseñas, roles y «Mi cuenta» |
| `users` | Administración de usuarios |
| `groups` | Grupos, miembros y supervisores responsables |
| `catalogs` | Catálogos de tickets, motivos de espera, estados y transiciones |
| `tickets` | El núcleo de tickets y todo su ciclo de vida |
| `knowledge` | La base de conocimiento: artículos, permisos y búsqueda |
| `dashboards` | Los dashboards por rol y la carga de trabajo |
| `reports` | Los reportes operativos y sus definiciones |
| `sla` | Tiempo laboral, calendario, políticas y períodos de SLA |
| `notifications` | Notificaciones internas y los avisos por eventos |
| `seeds` | Los comandos que cargan datos de demostración |
| `unit` | Se asigna sola a los tests que no usan la base de datos |

**Qué correr mientras desarrollas.** Las áreas se apoyan unas en otras (los servicios de tickets alimentan al SLA, a los avisos y a los datos de demostración), así que según lo que toques basta con:

| Si tocas | Corre |
| --- | --- |
| `tickets/` | `-m "tickets or sla or notifications or seeds"` |
| `sla/` o `worktime.py` | `-m "sla or tickets or seeds"` |
| `notifications/` | `-m "notifications or tickets"` |
| `auth/`, `security/` o `account/` | `-m "auth or platform"` |
| `users/`, `groups/` o `catalogs/` | `-m "users or groups or catalogs"` |
| `seeds/` | `-m seeds` |
| Una plantilla, CSS o JavaScript | El área de esa pantalla y `-m platform` |
| Modelos o migraciones | La suite completa |

Esto acorta el ciclo de desarrollo, pero **antes de un commit o de un Pull Request se ejecuta siempre la suite completa**.

**Cuánto tarda la suite completa** (medido en el equipo de desarrollo del proyecto, con 6 núcleos físicos): unos **4 min 12 s en paralelo** (`-n 6`) con los 4746 tests de `v0.8.0`; varía con lo que esté haciendo el equipo a la vez. Ha tenido dos optimizaciones medidas. La primera, con unos 3000 tests, la bajó de unos 34 minutos a unos 4 en paralelo. Después creció con las pruebas de pantallas con datos reales, de migraciones y de instalación limpia, hasta 6 min 54 s con 4728 tests. La segunda (`v0.8.0`, entrega 2) la devolvió a 4 min 12 s reutilizando las conexiones entre tests y abaratando Argon2id solo en la suite (ver [Cómo se aísla cada test](#cómo-se-aísla-cada-test)). La prueba más larga es la de instalación limpia (unos 30 s), porque lanza los comandos reales. El número de procesos de `-n` conviene que sea el de núcleos físicos de tu equipo: con más no se gana tiempo (medido al optimizar: 4 procesos: 5 min; 6: 4,3 min; 8: 4,2 min; 12: 4,5 min). Con `pytest-xdist` el reparto por defecto es el mejor (`--dist worksteal` no mejoró nada).

Un módulo de tests nuevo debe añadirse a `tests/areas.py`: si no pertenece a ningún área, la recolección de pytest falla diciéndolo (así ninguno queda fuera de las ejecuciones por área).

### Cómo se aísla cada test

Los tests utilizan exclusivamente:

```text
workdesk_test
```

La protección es `checked_database_url` (en `tests/database.py`): si la base de `TEST_DATABASE_URL` no se llama `workdesk_test`, la suite se niega a ejecutarse, y todo lo que crea o vacía tablas la llama antes de tocar nada. `tests/test_suite_infrastructure.py` comprueba que rechaza cualquier otra base (por ejemplo, `workdesk_dev`).

Preparar una base limpia para cada uno de los miles de tests era lo que más tiempo consumía (el 83 % del total en una muestra medida), así que la suite trabaja así:

- **El esquema se crea una vez** por sesión (una vez por proceso al ejecutar en paralelo) y se elimina al terminar.
- **Entre un test y el siguiente solo se vacían las tablas que quedaron con filas** y se reinician las secuencias: cada test sigue empezando con la base vacía y los identificadores en 1. No se envuelve cada test en una transacción que se deshace, porque la aplicación y los tests dependen de confirmaciones reales (`now()` cambia entre transacciones y los tests con hilos usan conexiones distintas).
- **Los estados caros de construir se guardan en una instantánea.** Los 108 tickets de demostración se cargan una vez por proceso (unos 6 s) y cada test restaura una copia exacta en milisegundos.
- **En paralelo, cada proceso trabaja en su propio esquema de PostgreSQL** (`wd_test_gw0`, `wd_test_gw1`...) dentro de la misma base `workdesk_test`: no hay que crear bases nuevas y la protección sigue valiendo.
- **Las conexiones a PostgreSQL se reutilizan entre tests.** Cada test tiene su aplicación y su motor de SQLAlchemy, pero toma las conexiones de una reserva del proceso: en Windows, abrir una cuesta unos 54 ms (PostgreSQL crea un proceso por conexión). Al terminar el test, cada conexión vuelve a la reserva limpia: sin transacción abierta, con la configuración de sesión restablecida y sin bloqueos. Una prueba comprueba que el test siguiente la encuentra así.
- **Argon2id barato, solo en la suite.** Los tests inician sesión miles de veces, y con los parámetros de producción (64 MiB, 3 pasadas y 4 hilos) en seis procesos a la vez los hilos competían por los núcleos. La suite usa Argon2id con parámetros mínimos: sigue siendo el mismo algoritmo y el mismo código de login, pero cuesta milisegundos. La producción no cambia: una prueba comprueba los parámetros reales (`build_password_hasher`) contra el mínimo de OWASP, y los comandos que las pruebas de migraciones lanzan en otro proceso usan los reales.
- **El hash de la contraseña de prueba se calcula una sola vez** por proceso.

Ejecuta **una sola suite a la vez**: todas comparten `workdesk_test` (y, en paralelo, los mismos nombres de esquema), de modo que dos ejecuciones simultáneas se estorban y fallan de forma aleatoria.

---

## Calidad de código

WorkDesk utiliza Ruff para análisis estático.

Ejecutar:

```bash
ruff check src/workdesk tests
```

El objetivo es mantener el código libre de errores básicos de estilo, imports innecesarios y determinados problemas detectables de forma automática.

`ruff.toml` conserva las reglas por defecto de Ruff y añade un límite de complejidad para `src/workdesk`: ninguna función supera 12 de complejidad ciclomática, 12 ramas ni 50 sentencias. Si Ruff señala una función, la solución es partirla en piezas con nombre, no subir el límite.

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

# Cargar notificaciones de ejemplo (opcional; requiere tickets visibles; --username para una cuenta concreta)
python -m flask --app src.workdesk seed-demo-notifications

# Cargar artículos de ejemplo en la base de conocimiento (opcional; requiere seed-demo y seed-catalogs)
python -m flask --app src.workdesk seed-demo-articles

# Ejecutar el planificador: avisos de SLA y cierre automático (en otra terminal; --once = una pasada)
python -m flask --app src.workdesk run-scheduler

# Crear un respaldo de la base y los adjuntos, comprobarlo (el más reciente o uno por nombre) y listarlos
python -m flask --app src.workdesk backup-create
python -m flask --app src.workdesk backup-verify
python -m flask --app src.workdesk backup-list

# Restaurar un respaldo (reemplaza la base y los adjuntos; detén antes WorkDesk y el planificador)
python -m flask --app src.workdesk backup-restore NOMBRE

# Ver rutas
python -m flask --app src.workdesk routes

# Ejecutar la suite completa en paralelo (antes de un commit o un Pull Request)
python -m pytest -n 6

# Ejecutar solo un área (por ejemplo, SLA) o los tests sin base de datos
python -m pytest -m sla
python -m pytest -m unit

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
14. [Historial de implementación](docs/14_historial_de_implementacion.md)

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

`v0.1.0` a `v0.7.0` están terminadas; la siguiente es `v0.8.0`. Después del MVP están previstos el modo oscuro, la evaluación de actualizaciones en tiempo real y otras mejoras evaluadas (autoservicio, automatización, flujos ITSM y activos), además de un módulo secundario de proyectos y tareas, solo para el personal, que deja a los tickets como núcleo. El roadmap está en [`docs/12_roadmap.md`](docs/12_roadmap.md) y las mejoras posteriores en [`docs/13_evolucion_post_mvp.md`](docs/13_evolucion_post_mvp.md).

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