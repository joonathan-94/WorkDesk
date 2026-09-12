# WorkDesk

> Plataforma web para la gestión y seguimiento de tickets de soporte TI, diseñada para evolucionar progresivamente hacia una solución más amplia de gestión del trabajo.

WorkDesk es un proyecto personal de desarrollo de software orientado inicialmente a la gestión integral de solicitudes de soporte TI.

El sistema busca centralizar el ciclo de vida de los tickets, facilitar la colaboración entre solicitantes y equipos técnicos, controlar prioridades y SLA, mantener trazabilidad de las acciones y proporcionar herramientas de seguimiento, conocimiento y análisis operacional.

## Estado del proyecto

📋 **Documentación inicial completada.**

El proyecto se encuentra actualmente en preparación para comenzar la fase de implementación.

Próximo hito:

`v0.1.0 — Fundación técnica`

## Características planificadas

- Gestión completa de tickets.
- Roles y permisos.
- Asignación de múltiples técnicos.
- Comentarios públicos y notas internas.
- Adjuntos.
- Estados y prioridades configurables.
- Gestión de SLA.
- Notificaciones internas.
- Dashboards por rol.
- Carga de trabajo.
- Base de conocimiento.
- Reportes.
- Administración.
- Auditoría.
- Backups locales.
- Diseño responsive.

## Stack previsto

### Backend

- Python
- Flask
- SQLAlchemy
- PostgreSQL

### Frontend

- HTML5
- CSS3
- Bootstrap
- JavaScript
- Jinja2
- Bootstrap Icons

### Herramientas

- Git
- GitHub
- VS Code
- Alembic / Flask-Migrate
- pytest
- Ruff

## Arquitectura

WorkDesk utilizará inicialmente una arquitectura de **monolito modular**, organizada por responsabilidades y funcionalidades.

La aplicación funcionará inicialmente de manera local.

No se contempla despliegue externo para el MVP.

## Documentación

La documentación técnica y funcional del proyecto se encuentra en [`docs/`](docs/).

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

## Diseño

Los recursos utilizados durante el diseño se encuentran en:

- [`docs/assets/wireframes/`](docs/assets/wireframes/)
- [`docs/assets/mockups/`](docs/assets/mockups/)

Los mockups constituyen la referencia visual para la implementación del frontend.

## Roadmap

El desarrollo se realizará de manera incremental.

```text
v0.1.0  Fundación técnica
v0.2.0  Autenticación y RBAC
v0.3.0  Núcleo de tickets
v0.4.0  Colaboración y adjuntos
v0.5.0  SLA y notificaciones
v0.6.0  Dashboards y carga de trabajo
v0.7.0  Administración y conocimiento
v0.8.0  Reportes, auditoría y backups
v0.9.0  Estabilización y UX
v1.0.0  MVP