# WorkDesk — Instrucciones para Claude Code

## Contexto obligatorio

Antes de analizar, proponer o modificar código de WorkDesk, carga y respeta:

@AGENTS.md
@PROJECT_CONTEXT.md

Estos dos archivos constituyen el punto de entrada al proyecto:

- `PROJECT_CONTEXT.md` describe el estado real actual de WorkDesk.
- `AGENTS.md` define las reglas generales de trabajo para asistentes y agentes.

No asumir el estado del proyecto a partir de conocimientos externos ni de conversaciones anteriores.

---

## Documentación del proyecto

La documentación completa se encuentra en `docs/`.

Antes de trabajar sobre una funcionalidad, consulta únicamente los documentos relevantes para esa tarea.

Referencias principales:

- `docs/03_roles_y_permisos.md` — roles y permisos.
- `docs/04_requisitos_funcionales.md` — requisitos funcionales.
- `docs/05_requisitos_no_funcionales.md` — requisitos no funcionales.
- `docs/06_reglas_de_negocio.md` — reglas de negocio.
- `docs/07_casos_de_uso.md` — casos de uso.
- `docs/08_flujo_de_tickets.md` — flujo y ciclo de vida de tickets.
- `docs/09_modelo_de_datos.md` — modelo de datos.
- `docs/10_arquitectura.md` — arquitectura.
- `docs/11_diseno_de_pantallas.md` — UI, UX y Design System.
- `docs/12_roadmap.md` — orden de implementación.

No cargar o reinterpretar toda la documentación si la tarea solo requiere una parte concreta.

---

## Forma de trabajo

Antes de realizar cambios relevantes:

1. inspecciona primero el código existente;
2. identifica los archivos involucrados;
3. revisa los tests relacionados;
4. consulta la documentación correspondiente;
5. explica brevemente qué propones modificar y por qué;
6. implementa el cambio mínimo coherente;
7. verifica el resultado.

No realizar refactors amplios que no sean necesarios para la tarea actual.

No modificar archivos no relacionados únicamente para reorganizar, modernizar o aplicar preferencias personales.

---

## Arquitectura

Preserva las decisiones existentes de WorkDesk.

Stack principal:

- Python;
- Flask;
- PostgreSQL;
- SQLAlchemy / Flask-SQLAlchemy;
- Alembic / Flask-Migrate;
- Flask-Login;
- Flask-WTF / CSRFProtect;
- Argon2id;
- Jinja2;
- HTML;
- CSS;
- JavaScript.

Arquitectura:

```text
Monolito modular
```

No sustituir tecnologías ni introducir nuevas dependencias sin una necesidad concreta.

No convertir WorkDesk en una SPA.

No introducir React, Vue, Angular, FastAPI, Django, Redis, Celery, Docker obligatorio, microservicios u otras tecnologías únicamente porque sean habituales en otros proyectos.

Si consideras que una decisión existente debe cambiar, primero explica:

1. qué limitación concreta existe;
2. por qué la solución actual es insuficiente;
3. qué alternativa propones;
4. qué impacto tendría;
5. qué documentación debería actualizarse.

No aplicar el cambio arquitectónico sin aprobación explícita.

---

## Código Python y Flask

Respeta la Application Factory existente:

```python
create_app()
```

Utiliza los Blueprints, extensiones y patrones existentes.

Antes de modificar un archivo, lee su contenido y contexto relevante.

Prefiere:

- nombres descriptivos;
- funciones comprensibles;
- código explícito;
- responsabilidades claras;
- soluciones proporcionales al problema.

Evita:

- abstracciones prematuras;
- clases innecesarias;
- repositories genéricos sin necesidad;
- services vacíos;
- duplicar utilidades ya existentes.

La lógica de negocio no debe quedar dispersa en templates.

---

## Base de datos

PostgreSQL es la base de datos oficial.

Los cambios de esquema deben utilizar:

```text
modelos SQLAlchemy
→ migración Alembic
→ revisión
→ aplicación
→ tests
```

No utilizar `db.create_all()` como mecanismo normal para evolucionar el esquema.

No modificar migraciones históricas ya aplicadas salvo que exista un problema confirmado.

Mantener las restricciones e integridad definidas por el proyecto.

---

## Seguridad

No exponer, imprimir, documentar ni versionar:

- `.env`;
- `SECRET_KEY`;
- credenciales PostgreSQL;
- contraseñas;
- hashes de contraseña innecesariamente;
- cookies;
- tokens;
- CSRF tokens;
- secretos.

No debilitar mecanismos existentes para facilitar una implementación.

Preservar especialmente:

- Argon2id;
- Flask-Login;
- CSRF;
- bloqueo por intentos fallidos;
- usuarios activos/inactivos;
- `token_version`;
- seguridad de cookies.

La autorización debe comprobarse en backend.

Ocultar un botón o elemento visual nunca constituye autorización suficiente.

---

## Testing

Los tests utilizan exclusivamente:

```text
workdesk_test
```

Nunca ejecutar operaciones destructivas de testing contra:

```text
workdesk_dev
```

No eliminar ni debilitar la protección existente en `tests/conftest.py`.

Después de cambios relevantes en Python/backend ejecutar:

```bash
ruff check src/workdesk tests
python -m pytest -q
```

Si existe una modificación de esquema, revisar también cuando corresponda:

```bash
python -m flask --app src.workdesk db current
python -m flask --app src.workdesk db heads
python -m flask --app src.workdesk db check
```

No modificar un test únicamente para conseguir que pase.

Analiza primero si el error pertenece al test o a la implementación.

---

## Git

`main` representa el estado estable.

Trabaja sobre la rama que el usuario haya preparado para la tarea.

No ejecutar sin autorización explícita:

- `git commit`;
- `git push`;
- merges;
- force push;
- eliminación de ramas;
- reescritura de historial.

Los commits del proyecto utilizan mensajes en inglés.

Antes de recomendar un commit, comprobar que:

- la implementación esté terminada;
- Ruff pase;
- pytest pase;
- el diff sea coherente.

---

## Frontend

WorkDesk utiliza renderizado server-side con Jinja2.

JavaScript debe utilizarse progresivamente donde mejore la experiencia.

Respeta el Design System definido en:

```text
docs/11_diseno_de_pantallas.md
```

No rediseñar componentes o pantallas ignorando los mockups y decisiones visuales existentes.

---

## Estado y roadmap

Antes de comenzar una nueva funcionalidad consulta:

```text
PROJECT_CONTEXT.md
docs/12_roadmap.md
```

`PROJECT_CONTEXT.md` indica qué existe actualmente.

`docs/12_roadmap.md` indica qué corresponde implementar después.

La documentación del MVP puede describir funcionalidades futuras que todavía no existen.

Nunca presentar una funcionalidad como implementada sin comprobar código, tests o migraciones.

---

## Objetivo de aprendizaje

WorkDesk es también un proyecto de aprendizaje.

Para cambios relevantes:

- explica qué se está haciendo;
- explica por qué;
- explica cómo encaja con el proyecto;
- identifica conceptos importantes de Python, Flask, PostgreSQL, JavaScript, seguridad o arquitectura cuando sean relevantes.

Evita entregar grandes modificaciones difíciles de comprender o justificar.

La solución debe quedar suficientemente clara para que su desarrollador pueda mantenerla y explicarla posteriormente.

---

## Regla final

> Primero comprende el estado real de WorkDesk. Después propón. Luego implementa.

No optimices, modernices ni reestructures el proyecto antes de comprender por qué está construido de la forma actual.