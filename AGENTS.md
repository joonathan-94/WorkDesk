# WorkDesk — Instrucciones para agentes y asistentes

## 1. Propósito

Este archivo define cómo debe trabajar cualquier IA, agente de programación o asistente que participe en WorkDesk.

Antes de modificar código, leer como mínimo:

1. `PROJECT_CONTEXT.md`
2. `README.md`
3. `docs/10_arquitectura.md`
4. `docs/12_roadmap.md`
5. los documentos funcionales relevantes para la tarea

`PROJECT_CONTEXT.md` describe el estado real actual del proyecto.

Los documentos dentro de `docs/` contienen la especificación funcional y técnica completa.

---

# 2. Regla principal

Antes de cambiar WorkDesk:

```text
comprender
→ revisar
→ proponer
→ implementar
→ probar
```

No asumir que una funcionalidad existe únicamente porque aparece en la documentación del MVP.

Distinguir siempre entre:

```text
implementado actualmente
```

y:

```text
planificado
```

---

# 3. Arquitectura que debe preservarse

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

No reemplazar estas decisiones sin una necesidad técnica demostrable y aprobación explícita.

---

# 4. Evitar sobrearquitectura

No introducir sin justificación:

- frameworks nuevos;
- ORMs alternativos;
- otra base de datos;
- microservicios;
- Redis;
- brokers;
- colas externas;
- SPA;
- React;
- Angular;
- Vue;
- Docker obligatorio;
- services innecesarios;
- repositories genéricos;
- patrones complejos;
- módulos vacíos;
- capas anticipadas;
- abstracciones que no resuelvan un problema actual.

La arquitectura debe crecer solamente cuando exista una necesidad real.

---

# 5. Antes de modificar código

Para cambios relevantes:

1. leer completos los archivos afectados;
2. revisar tests relacionados;
3. identificar la documentación aplicable;
4. explicar qué se pretende cambiar;
5. proponer la solución más pequeña y coherente;
6. preservar el estilo y la estructura existentes;
7. evitar refactors no relacionados;
8. verificar el resultado.

No reestructurar grandes áreas del proyecto por preferencia personal.

---

# 6. Python y Flask

Seguir la Application Factory existente.

No crear otra aplicación Flask paralela fuera de:

```python
create_app()
```

Utilizar los Blueprints y extensiones existentes.

Mantener las rutas razonablemente pequeñas.

No colocar reglas de negocio complejas en templates.

Utilizar nombres descriptivos.

Preferir código explícito, claro y mantenible.

No crear abstracciones antes de necesitarlas.

---

# 7. PostgreSQL y SQLAlchemy

PostgreSQL es la base oficial del proyecto.

Los cambios de esquema deben seguir:

```text
modelo
→ migración Alembic
→ revisión
→ aplicación
→ tests
```

No utilizar `db.create_all()` como estrategia normal de evolución.

Preservar:

- foreign keys;
- unique constraints;
- check constraints;
- índices;
- auditoría;
- integridad histórica.

No modificar migraciones ya aplicadas salvo que exista un problema histórico confirmado.

---

# 8. Seguridad

Nunca exponer, registrar ni versionar:

- `.env`;
- `SECRET_KEY`;
- credenciales de PostgreSQL;
- contraseñas;
- hashes sin necesidad;
- cookies;
- tokens;
- CSRF tokens;
- secretos.

No debilitar controles de seguridad para simplificar una tarea.

La autorización debe validarse en backend.

Ocultar elementos de interfaz NO constituye autorización.

Preservar:

- Argon2id;
- Flask-Login;
- CSRF;
- bloqueo por intentos fallidos;
- usuario activo/inactivo;
- `token_version`;
- configuración segura de cookies.

---

# 9. Testing

Los tests utilizan:

```text
workdesk_test
```

Nunca ejecutar tests destructivos sobre:

```text
workdesk_dev
```

No debilitar la protección existente en `tests/conftest.py`.

Después de cambios relevantes ejecutar:

```bash
ruff check src/workdesk tests
python -m pytest -q
```

No modificar un test únicamente para conseguir que pase.

Primero determinar si el problema está en:

```text
la implementación
```

o:

```text
el test
```

---

# 10. Migraciones

Cuando corresponda revisar:

```bash
python -m flask --app src.workdesk db current
python -m flask --app src.workdesk db heads
python -m flask --app src.workdesk db check
```

Toda migración nueva debe revisarse antes de considerarse terminada.

---

# 11. Frontend y JavaScript

WorkDesk utiliza renderizado server-side mediante Jinja2.

JavaScript debe utilizarse de forma progresiva para mejorar la interacción.

No convertir WorkDesk en SPA sin una decisión arquitectónica explícita.

Preferir JavaScript nativo cuando resuelva claramente la necesidad.

Respetar:

```text
docs/11_diseno_de_pantallas.md
```

---

# 12. Git

`main` representa el estado estable.

No desarrollar funcionalidades importantes directamente sobre `main`.

Flujo normal:

```text
main actualizada
→ feature branch
→ cambios
→ tests
→ Ruff
→ git diff
→ commit
→ push
→ Pull Request
→ merge
```

Los commits se escriben en inglés.

Ejemplos:

```text
feat: ...
fix: ...
test: ...
refactor: ...
docs: ...
chore: ...
```

No hacer sin autorización explícita del usuario:

- commit;
- push;
- merge;
- force push;
- borrar ramas;
- reescribir historial.

---

# 13. Archivos que no deben versionarse

No agregar:

- `.env`;
- `.venv/`;
- `venv/`;
- `instance/`;
- logs;
- caches;
- archivos temporales;
- secretos;
- credenciales.

Respetar `.gitignore`.

---

# 14. Documentación

Consultar la fuente adecuada según la tarea:

- visión: `docs/01_vision_del_proyecto.md`
- objetivos: `docs/02_objetivos.md`
- roles y permisos: `docs/03_roles_y_permisos.md`
- requisitos funcionales: `docs/04_requisitos_funcionales.md`
- requisitos no funcionales: `docs/05_requisitos_no_funcionales.md`
- reglas de negocio: `docs/06_reglas_de_negocio.md`
- casos de uso: `docs/07_casos_de_uso.md`
- flujo de tickets: `docs/08_flujo_de_tickets.md`
- modelo de datos: `docs/09_modelo_de_datos.md`
- arquitectura: `docs/10_arquitectura.md`
- UI/UX: `docs/11_diseno_de_pantallas.md`
- roadmap: `docs/12_roadmap.md`

No reinterpretar silenciosamente decisiones consolidadas.

Si se propone cambiar una decisión importante, explicar:

1. qué problema existe;
2. por qué la solución actual es insuficiente;
3. qué alternativa se propone;
4. qué impacto tendrá;
5. qué documentación debe actualizarse.

---

# 15. Forma de trabajar

Priorizar cambios:

- pequeños;
- coherentes;
- revisables;
- testeables;
- comprensibles.

Para tareas grandes, dividir el trabajo en bloques.

Antes de generar una cantidad importante de código, explicar el enfoque.

No modificar código no relacionado únicamente por preferencia estética.

---

# 16. Objetivo de aprendizaje

WorkDesk también tiene un objetivo de aprendizaje.

Para cambios relevantes:

- explicar qué se está haciendo;
- explicar por qué;
- explicar cómo encaja en el proyecto;
- señalar conceptos importantes;
- evitar grandes bloques de código sin explicación;
- mantener soluciones que el desarrollador pueda entender y defender.

El objetivo no es únicamente que WorkDesk funcione.

También debe seguir siendo comprensible y mantenible.

---

# 17. Estado actual

Consultar siempre:

```text
PROJECT_CONTEXT.md
```

para conocer:

- versión actual;
- funcionalidades implementadas;
- estructura real;
- estado de tests;
- decisiones vigentes;
- próximo hito.

No asumir el estado del proyecto desde conversaciones anteriores.

---

# 18. Regla final

> Antes de mejorar WorkDesk, comprender WorkDesk.

Toda propuesta debe respetar primero:

- contexto;
- arquitectura;
- reglas de negocio;
- roadmap;
- seguridad;
- estado real del repositorio.