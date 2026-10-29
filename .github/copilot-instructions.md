# WorkDesk — Instrucciones para GitHub Copilot

WorkDesk es una aplicación web de gestión de tickets de soporte TI desarrollada con Python, Flask y PostgreSQL.

Antes de proponer cambios relevantes, utiliza como contexto del proyecto:

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `README.md`
- la documentación relevante dentro de `docs/`

`PROJECT_CONTEXT.md` describe el estado real actual.

Los documentos de `docs/` pueden describir funcionalidades del MVP que todavía no están implementadas.

---

## Arquitectura

Preserva el stack actual:

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

WorkDesk utiliza una arquitectura de:

```text
Monolito modular
```

No sugerir cambios de framework, ORM, base de datos o arquitectura sin una necesidad concreta.

Evitar sobrearquitectura y dependencias innecesarias.

No convertir WorkDesk en SPA.

---

## Sugerencias de código

Al completar o generar código:

- respeta el estilo del archivo existente;
- utiliza nombres descriptivos;
- prioriza claridad y mantenibilidad;
- evita modificar código no relacionado;
- reutiliza componentes existentes antes de crear otros;
- evita abstracciones prematuras;
- mantén las funciones enfocadas;
- no dupliques lógica existente.

Cuando el desarrollador esté escribiendo código manualmente, completa siguiendo su intención actual en lugar de rediseñar otras partes del archivo.

---

## Flask

Respeta el patrón Application Factory existente.

No crear una segunda instancia Flask independiente.

Utiliza los Blueprints y extensiones existentes.

Mantén la lógica compleja fuera de templates.

Las rutas deben permanecer razonablemente pequeñas a medida que crece la aplicación.

---

## PostgreSQL y SQLAlchemy

PostgreSQL es la base oficial del proyecto.

Los cambios de esquema requieren migraciones Alembic / Flask-Migrate.

No utilizar `db.create_all()` como mecanismo normal de evolución del esquema.

Preservar:

- claves foráneas;
- restricciones únicas;
- check constraints;
- índices;
- campos de auditoría;
- integridad histórica.

---

## Seguridad

No sugerir hardcodear ni versionar:

- secretos;
- `.env`;
- credenciales;
- contraseñas;
- tokens;
- cookies;
- CSRF tokens.

Preservar los mecanismos existentes:

- Argon2id;
- Flask-Login;
- CSRF;
- bloqueo temporal por intentos fallidos;
- validación de usuario activo;
- `token_version`;
- configuración segura de cookies.

La autorización se valida en backend.

La visibilidad de elementos en la interfaz no reemplaza una autorización backend.

---

## Frontend y JavaScript

WorkDesk utiliza Jinja2 y renderizado server-side.

JavaScript debe incorporarse progresivamente cuando aporte interacción útil.

Preferir JavaScript nativo cuando resulte suficiente.

No introducir frameworks frontend sin una decisión explícita.

Seguir las definiciones visuales de:

```text
docs/11_diseno_de_pantallas.md
```

---

## Testing y calidad

Los tests utilizan:

```text
workdesk_test
```

Nunca sugerir ejecutar tests destructivos contra:

```text
workdesk_dev
```

Después de cambios relevantes en backend, las validaciones habituales son:

```bash
ruff check src/workdesk tests
python -m pytest -q
```

No eliminar ni debilitar tests existentes únicamente para conseguir que el código pase.

---

## Git

`main` representa el estado estable.

El desarrollo de nuevas funcionalidades debe realizarse normalmente en ramas específicas.

Los mensajes de commit se escriben en inglés.

No incluir en Git:

- `.env`;
- `instance/`;
- entornos virtuales;
- logs;
- caches;
- credenciales.

---

## Estado del proyecto

Antes de asumir qué funcionalidad debe implementarse a continuación, consultar:

```text
PROJECT_CONTEXT.md
docs/12_roadmap.md
```

No asumir que todo lo descrito en la documentación del MVP ya existe.

Priorizar siempre soluciones compatibles con el estado real y la arquitectura actual de WorkDesk.