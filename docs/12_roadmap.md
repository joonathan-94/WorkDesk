# 12_roadmap.md

# WorkDesk — Roadmap de implementación

**Versión:** 1.2  
**Estado:** ACTUALIZADO — `v0.1.0`, `v0.2.0`, `v0.3.0` (núcleo de tickets) y `v0.4.0` (asignación, colaboración y ciclo de vida) implementados, integrados en `main` y etiquetados; la siguiente fase es `v0.5.0`  
**Proyecto:** WorkDesk  
**Horizonte objetivo del MVP:** máximo 3 meses  
**Modalidad inicial:** desarrollo local, sin despliegue externo  
**Objetivo principal:** equilibrar aprendizaje técnico con la entrega de un MVP profesional y presentable para portafolio  

---

## 1. Propósito del roadmap

Este documento define el orden recomendado para implementar WorkDesk una vez finalizada la documentación inicial del proyecto.

Su objetivo es transformar las decisiones funcionales, de arquitectura, datos y diseño ya aprobadas en un plan de ejecución claro, incremental y verificable.

El roadmap debe servir para:

- evitar comenzar módulos sin sus dependencias;
- dividir el proyecto en entregas alcanzables;
- mantener control de alcance;
- facilitar aprendizaje progresivo;
- versionar el proyecto desde el inicio;
- establecer criterios objetivos para decidir cuándo una fase está terminada;
- llegar a un MVP funcional y profesional sin intentar implementar simultáneamente todo el sistema.

Este roadmap no reemplaza los documentos anteriores. La implementación de cada fase debe respetar las definiciones aprobadas en requisitos, reglas de negocio, casos de uso, flujo de tickets, modelo de datos, arquitectura y diseño de pantallas.

## 1.1. Estado actual de ejecución

La primera versión técnica del proyecto está implementada, validada e integrada en `main` mediante el Pull Request #1 (rama `feature/flask-foundation`). Posteriormente se integraron la documentación de contexto (PR #2) y la identidad visual oficial con su integración inicial en el Login (PR #3, rama `feature/branding-login`). El hito `v0.1.0` todavía no tiene tag Git.

El alcance ejecutado para `v0.1.0` incluye la fundación Flask, PostgreSQL, migraciones, configuración por entorno, manejo de errores, health check, logging, pruebas automatizadas y una base técnica de autenticación adelantada respecto de la planificación inicial.

La validación actual incluye:

```text
✓ Ruff sin errores
✓ 20 tests automatizados aprobados
✓ modelos y migraciones sincronizados
✓ PostgreSQL de desarrollo operativo
✓ PostgreSQL de testing aislado
✓ rutas y comandos CLI verificados
✓ revisión técnica final completada
```

`v0.1.0` está etiquetado. Antes de comenzar `v0.2.0` se sincronizó la documentación con las decisiones consolidadas (prioridad y SLA, grupos, contraseñas, sesiones, auditoría mínima, rutas y Bootstrap, PR #4). `v0.2.0` se completó después, mediante entregas incrementales (PR #5 a #13); ver la fase 2. `v0.3.0` (núcleo de tickets, PR #14 a #20) y `v0.4.0` (asignación, colaboración y ciclo de vida, PR #23 a #35) siguieron el mismo camino; ver las fases 3 y 4. Las cuatro versiones están etiquetadas.

---

# 2. Contexto de ejecución

El proyecto será desarrollado inicialmente por una sola persona, con un objetivo doble:

1. aprender y consolidar conocimientos de desarrollo web;
2. construir un producto funcional y profesional para portafolio.

El nivel técnico inicial es principalmente básico en desarrollo web y Python, con una base intermedia en SQL.

La disponibilidad estimada es de aproximadamente:

```text
3–4 horas de trabajo por día
```

Como no se definió un número exacto de días semanales, este roadmap utiliza como referencia:

```text
5 días por semana
≈ 15–20 horas semanales
```

Esta cifra es una **base de planificación**, no una obligación. Si temporalmente existe mayor disponibilidad, puede adelantarse trabajo sin alterar el orden de dependencias.

El horizonte máximo deseado para el MVP es:

```text
12 semanas
```

La prioridad será cumplir hitos funcionales, no perseguir fechas a costa de calidad o comprensión.

---

# 3. Estrategia general

La estrategia elegida combina:

```text
desarrollo funcional por módulos
+
implementación vertical
+
versionado incremental
+
aprendizaje progresivo
```

Cada funcionalidad debe construirse de forma vertical siempre que sea posible:

```text
Modelo de datos
↓
Migración
↓
Backend
↓
Autorización
↓
Frontend
↓
Validación
↓
Prueba
↓
Refactor
↓
Commit
```

Esto permite que el proyecto permanezca utilizable durante su crecimiento y evita construir primero una gran cantidad de frontend desconectado o backend sin interfaz.

---

# 4. Principios de implementación

## 4.1. Una funcionalidad antes de la siguiente

No se debe comenzar simultáneamente con múltiples módulos complejos.

Ejemplo:

```text
Autenticación
→ completar
→ validar
→ versionar
→ avanzar a tickets
```

Se permiten pequeños ajustes transversales cuando una funcionalidad lo requiera, pero cada fase debe tener un objetivo principal.

## 4.2. Comprender antes de consolidar

Durante las primeras fases se priorizará avanzar de forma práctica, revisando y comprendiendo progresivamente el código incorporado al proyecto.

Flujo recomendado:

```text
1. Explicación conceptual
2. Diseño técnico
3. Implementación
4. Ejecución
5. Pruebas
6. Debugging
7. Refactor
8. Commit
```

La profundidad de estudio podrá aumentar a medida que avance el proyecto, procurando que cada módulo quede suficientemente comprendido antes de consolidarlo como parte estable de WorkDesk.


## 4.3. Evitar sobrearquitectura

WorkDesk debe respetar su arquitectura aprobada, pero no incorporar complejidad que el MVP no necesita.

Evitar inicialmente:

- microservicios;
- Redis;
- WebSockets;
- Elasticsearch;
- infraestructura cloud;
- múltiples entornos de despliegue;
- colas externas;
- integración con correo;
- sistemas distribuidos.

La prioridad será un **monolito modular local, mantenible y bien estructurado**.

## 4.4. Desarrollo local

El MVP será exclusivamente local.

No forma parte del alcance:

- hosting;
- cloud;
- dominio;
- CI/CD de despliegue;
- publicación pública;
- configuración de servidores externos.

Podrán utilizarse herramientas locales para desarrollo, pruebas y demostración.

---

# 5. Alcance recomendado del MVP

El MVP debe incluir las capacidades necesarias para demostrar el ciclo completo de WorkDesk sin intentar implementar todas las posibles evoluciones futuras.

## 5.1. Incluido en MVP

### Fundación

- estructura de proyecto;
- configuración;
- base de datos PostgreSQL;
- migraciones;
- logging;
- manejo básico de errores;
- datos iniciales.

### Usuarios y seguridad

- login por username;
- logout;
- sesiones;
- usuarios;
- roles;
- RBAC;
- protección de rutas;
- contraseñas seguras;
- control de visibilidad por rol.

### Tickets

- creación;
- listado;
- búsqueda;
- filtros;
- detalle;
- estados;
- prioridades;
- categorías;
- ubicaciones;
- solicitantes;
- técnicos;
- grupos;
- asignación múltiple;
- comentarios públicos;
- notas internas;
- adjuntos;
- historial;
- resolución;
- cierre;
- validación por solicitante;
- reapertura;
- relaciones esenciales cuando correspondan.

### SLA

- políticas por prioridad;
- primera respuesta opcional;
- resolución;
- umbral de aviso;
- calendario laboral;
- pausa en `En espera`;
- reanudación con tiempo restante;
- próximo a vencer;
- vencido;
- avisos internos;
- configuración administrativa básica.

### Notificaciones

- únicamente notificaciones internas;
- leído/no leído;
- navegación al recurso asociado.

### Dashboards

- Dashboard Solicitante;
- Dashboard Técnico/Supervisor;
- indicadores básicos;
- tickets prioritarios;
- actividad reciente.

### Carga de trabajo

- carga por técnico;
- carga por grupo;
- tickets sin asignar;
- acceso al listado filtrado;
- indicadores de criticidad y SLA.

### Base de conocimiento

- listado;
- categorías;
- búsqueda;
- artículo;
- creación/edición según permisos;
- publicación según permisos;
- visualización para Solicitante.

### Reportes

El MVP incluirá los reportes definidos para la primera versión, evitando construir un diseñador dinámico de reportes.

Como mínimo:

- tickets creados;
- tickets resueltos;
- tiempo medio de resolución;
- fuera de SLA;
- tickets por estado;
- tickets por categoría;
- tickets por prioridad;
- resumen por técnico;
- filtros principales;
- exportación básica si queda estable dentro del plazo.

### Administración

- usuarios;
- grupos;
- categorías;
- prioridades;
- ubicaciones;
- estados/transiciones según alcance definido;
- SLA;
- cierre/reapertura;
- configuración de notificaciones internas;
- configuración de archivos;
- retención básica;
- auditoría;
- estado del sistema.

### Calidad

- responsive;
- accesibilidad base;
- validaciones;
- manejo de estados vacíos;
- loading;
- errores;
- datos demo;
- README profesional;
- capturas del sistema;
- versionado Git.

---

# 6. Elementos recomendados para post-MVP

Para mantener el objetivo de tres meses, las siguientes capacidades deberán considerarse evoluciones posteriores salvo que el proyecto avance con suficiente margen.

## 6.1. Fuera del MVP prioritario

- despliegue en la nube (el despliegue en un servidor propio de la intranet sí es posible);
- modo oscuro;
- fotografías de perfil;
- diseñador avanzado de reportes;
- dashboards altamente configurables;
- sistema de favoritos de artículos;
- valoración de artículos;
- comentarios en artículos;
- WebSockets;
- actualizaciones en tiempo real;
- multi-tenant;
- facturación;
- API pública completa;
- automatizaciones avanzadas;
- reglas complejas de reasignación automática.

**Descartadas por decisión (`docs/13_evolucion_post_mvp.md`, principio P1):** notificaciones por correo, SMS, integraciones externas, recuperación automática de contraseña por correo y autenticación social. WorkDesk es una aplicación 100 % local o de intranet; la recuperación de contraseña seguirá siendo un restablecimiento hecho por el Administrador.

---

# 7. Backups y restauración

Para el MVP se recomienda:

```text
scripts/herramientas primero
```

antes que una interfaz administrativa completa.

La primera versión debe permitir respaldar:

- PostgreSQL;
- archivos adjuntos;
- manifiesto o información necesaria para restauración.

El mecanismo puede apoyarse en:

```text
pg_dump
+
copiado de uploads
+
manifest
```

La UI de backup/restore puede implementarse posteriormente si existe tiempo suficiente.

La prioridad del MVP es que el respaldo **funcione realmente**, no disponer primero de una pantalla visual que todavía no restaure correctamente.

---

# 8. Estrategia de pruebas

Aunque inicialmente se prefiera desarrollar primero y agregar pruebas posteriormente, no se recomienda postergar **todas** las pruebas hasta el final.

Se utilizará un enfoque híbrido.

## 8.1. Durante cada fase

Antes de considerar una funcionalidad terminada debe realizarse:

- prueba manual del flujo principal;
- prueba manual de errores previsibles;
- prueba de permisos;
- una cantidad pequeña de tests automatizados para reglas críticas.

## 8.2. Fase de estabilización

Posteriormente se ampliará la cobertura mediante:

- tests unitarios;
- tests de servicios;
- tests de autorización;
- tests de reglas de negocio;
- tests de integración;
- regresión de flujos críticos.

No es necesario adoptar TDD como metodología obligatoria.

El objetivo es evitar llegar a la semana final con una aplicación grande sin ningún mecanismo de regresión.

---

# 9. Estrategia Git y GitHub

El repositorio debe crearse inmediatamente después de finalizar:

1. documentación inicial;
2. estructura base de carpetas;
3. `.gitignore`;
4. README inicial.

## 9.1. Repositorio

Se recomienda un repositorio:

```text
WorkDesk
```

en el perfil personal de GitHub.

Debe mantenerse libre de:

- contraseñas;
- secretos;
- `.env`;
- bases de datos exportadas;
- archivos personales;
- uploads reales;
- claves privadas.

## 9.2. Estrategia de ramas

Para un proyecto individual no es necesario mantener permanentemente una rama `develop`.

Se recomienda:

```text
main
```

como rama estable, más ramas cortas:

```text
feature/auth
feature/tickets
feature/sla
feature/knowledge-base
feature/reports

fix/...
refactor/...
docs/...
```

Flujo:

```text
main
 ↓
feature/x
 ↓
desarrollo
 ↓
pruebas
 ↓
merge
 ↓
main estable
```

GitHub Pull Requests pueden utilizarse incluso trabajando solo, principalmente para:

- revisar cambios;
- documentar decisiones;
- practicar un flujo profesional.

No son obligatorias para cada cambio trivial.

---

# 10. Convención de commits

Los commits deben ser:

- pequeños;
- coherentes;
- descriptivos;
- relacionados con una única intención.

Ejemplos:

```text
feat: add user authentication
feat: implement ticket creation
feat: add ticket assignment service
fix: prevent requester from viewing internal notes
fix: resume SLA after waiting state
refactor: extract ticket state service
test: add authorization tests for ticket detail
docs: update roadmap
```

No utilizar como práctica habitual:

```text
cambios
fix
actualizacion
cosas nuevas
final
final2
```

---

# 11. Versionado

Se utilizará versionado incremental.

Propuesta:

```text
v0.1.0   Fundación técnica
v0.2.0   Usuarios, autenticación completa y RBAC
v0.3.0   Núcleo de tickets
v0.4.0   Asignación, colaboración y ciclo de vida
v0.5.0   SLA y notificaciones
v0.6.0   Dashboards y carga de trabajo
v0.7.0   Administración y conocimiento
v0.8.0   Reportes, auditoría y backups
v0.9.0   Estabilización y UX
v1.0.0   MVP
```

Los tags deben representar hitos funcionales relevantes.

---

# 12. Definition of Done general

Una funcionalidad no se considera terminada únicamente porque “se ve en pantalla”.

Como mínimo debe cumplir:

```text
✓ modelo de datos correcto
✓ migración aplicada
✓ backend funcional
✓ permisos verificados
✓ frontend integrado
✓ validaciones
✓ errores controlados
✓ flujo principal probado
✓ reglas críticas testeadas
✓ responsive razonable
✓ código revisado
✓ documentación actualizada cuando corresponda
✓ commit descriptivo
```

---

# 13. Plan de implementación — 12 semanas

El calendario se plantea como referencia para cumplir el objetivo máximo de tres meses.

Debe conservarse el orden aunque una semana se extienda.

---

## FASE 0 — Preparación del proyecto

**Duración orientativa:** 2–3 días  
**Versión objetivo:** inicio de `v0.1.0`

### Objetivos

- estructurar carpetas;
- revisar documentación completa;
- crear README inicial;
- crear repositorio Git;
- configurar `.gitignore`;
- preparar entorno virtual;
- instalar dependencias iniciales;
- configurar VS Code;
- definir `.env.example`.

### Resultado esperado

```text
WorkDesk/
├── docs/
├── src/
├── tests/
├── migrations/
├── scripts/
├── README.md
├── requirements.txt / equivalente
├── .gitignore
└── .env.example
```

La estructura concreta debe respetar `10_arquitectura.md`.

### Criterio de salida

El proyecto puede clonarse, configurarse localmente e iniciar su entorno de desarrollo sin contener funcionalidad de negocio todavía.

---

# 14. FASE 1 — Fundación técnica

**Semana:** 1  
**Versión:** `v0.1.0`
**Estado de ejecución:** implementada, validada e integrada en `main` (PR #1)

### Aprendizaje principal

- Flask;
- application factory;
- configuración;
- blueprints;
- SQLAlchemy;
- PostgreSQL;
- migraciones;
- variables de entorno;
- testing con pytest;
- seguridad de sesión y autenticación básica.

### Implementación completada

- inicialización Flask mediante Application Factory;
- configuración Development/Test;
- conexión PostgreSQL;
- base independiente `workdesk_test`;
- SQLAlchemy y Flask-SQLAlchemy;
- Flask-Migrate/Alembic;
- migraciones iniciales de `roles` y `usuarios`;
- estructura modular proporcional al alcance actual;
- seed idempotente de roles estructurales;
- comando CLI para crear el Administrador inicial;
- modelo inicial de usuarios y roles;
- login por username;
- logout;
- Argon2id;
- Flask-Login;
- protección de rutas;
- CSRF;
- usuario activo/inactivo;
- bloqueo temporal por intentos fallidos;
- invalidación de sesiones mediante `token_version`;
- endurecimiento básico de cookies y sesión;
- interfaz visual de login;
- manejo controlado de errores `400`, `404` y `500`;
- health check de aplicación y PostgreSQL;
- logging persistente con rotación configurable;
- configuración sensible fuera del repositorio;
- suite inicial de 20 tests automatizados;
- análisis estático mediante Ruff.

### Ajuste respecto de la planificación inicial

Durante `v0.1.0` se adelantó parte de la base técnica prevista originalmente para la fase de autenticación. Esta decisión permitió validar tempranamente sesiones, hashing, CSRF, bloqueo de acceso, estructura modular y pruebas automatizadas antes de comenzar los módulos funcionales.

Este adelanto **no reemplaza `v0.2.0`**: la siguiente fase continúa siendo responsable de completar la gestión de usuarios y la autorización RBAC.

### Criterio de salida

```text
✓ aplicación inicia
✓ PostgreSQL conecta
✓ migraciones funcionan
✓ configuración no contiene secretos
✓ estructura modular creada
✓ autenticación base funciona
✓ errores se manejan de forma controlada
✓ health check responde
✓ logging funciona
✓ base de testing está aislada
✓ 20 tests automatizados pasan
✓ Ruff pasa sin errores
✓ revisión técnica final completada
```

---

# 15. FASE 2 — Usuarios, autenticación completa y RBAC

**Semana:** 2  
**Versión:** `v0.2.0`

### Aprendizaje

- decorators;
- autorización;
- políticas RBAC;
- gestión de usuarios;
- formularios administrativos;
- navegación condicionada por rol;
- cierre del ciclo de autenticación y sesión.

### Base ya disponible desde `v0.1.0`

- modelo Usuario;
- roles estructurales;
- login por username;
- logout;
- sesión mediante Flask-Login;
- contraseña Argon2id;
- protección inicial de rutas;
- CSRF;
- usuarios activos/inactivos;
- bloqueo temporal por intentos fallidos;
- `token_version` para invalidación de sesiones;
- tests básicos de autenticación y seguridad.

**Estado de ejecución:** implementada, validada e integrada en `main` (PR #4 a #13). 385 tests automatizados.

### Implementación de `v0.2.0` (completada)

- gestión administrativa de usuarios;
- autorización RBAC completa;
- políticas centralizadas de acceso;
- protección de rutas según rol;
- navegación y sidebar según rol;
- restricciones de acceso administrativo;
- cuenta propia básica ("Mi cuenta") con cambio de contraseña;
- creación de cuentas y restablecimiento de contraseña por el Administrador mediante contraseña temporal (escrita o generada), con cambio obligatorio en el primer inicio de sesión (`usuarios.debe_cambiar_password`);
- límites de sesión: 30 minutos de inactividad y 8 horas de duración máxima, configurables por variables de entorno (`SESSION_IDLE_MINUTES`, `SESSION_MAX_HOURS`);
- tabla `auditoria_administrativa` con el esquema completo de `09_modelo_de_datos.md` (sección 25.1), usada desde esta fase para las acciones sobre usuarios; la pantalla de consulta queda para `v0.8.0`;
- incorporación local de Bootstrap con las primeras pantallas administrativas, respetando el Design System;
- datos demo de usuarios;
- ampliar tests de autorización y permisos.

### Entregas de `v0.2.0`

Dado el tamaño de esta fase, se implementó en entregas incrementales, cada una en su propia rama, con tests y Pull Request:

1. **Base RBAC** ✓ (PR #5): políticas centralizadas, decorador de roles, manejador 403 y una ruta administrativa mínima protegida, con tests de autorización.
2. **Límites de sesión** ✓ (PR #6): inactividad y duración máxima por variables de entorno.
3. **Auditoría mínima** ✓ (PR #7): migración y modelo de `auditoria_administrativa` con su servicio de registro.
4. **Usuarios y contraseñas**, en cuatro pasos:
    1. ✓ (PR #8) política de contraseñas, generador de contraseñas temporales, columna `debe_cambiar_password` y operaciones de contraseña;
    2. ✓ (PR #9) cambio de contraseña propio y cambio obligatorio;
    3. ✓ (PR #10) listado y creación de usuarios;
    4. ✓ (PR #11) edición, cambio de rol, desactivación y reactivación, y restablecimiento de contraseña, con sus salvaguardas.
5. **Interfaz administrativa**, en dos pasos:
    1. ✓ (PR #12) Bootstrap local, app shell con sidebar y topbar, navegación por rol y hub de administración;
    2. ✓ (PR #13) "Mi cuenta", comando de datos demo y cierre de la fase.

La documentación de la fase se sincronizó previamente en el PR #4.

Las rutas internas se escriben en inglés (`/users`, `/account`, etc.) y la interfaz permanece en español.

### Roles

```text
Solicitante
Técnico
Supervisor
Administrador
```

### Criterio de salida

```text
✓ usuario válido inicia sesión
✓ inválido no entra
✓ logout funciona
✓ rutas privadas están protegidas
✓ rol controla acceso
✓ sidebar cambia según rol
✓ Solicitante no puede abrir rutas administrativas
✓ tests mínimos de autenticación y autorización
```

Todos los criterios se cumplen. Además de lo previsto, la fase cierra con salvaguardas de administración (nadie actúa sobre sí mismo y siempre queda un Administrador activo), auditoría de las acciones sobre usuarios y verificación automática de que los activos de frontend se sirven localmente.

---

# 16. FASE 3 — Núcleo de tickets

**Semanas:** 3 y 4  
**Versión:** `v0.3.0`

Esta es la fase central del MVP.

**Estado de ejecución:** implementada, validada e integrada en `main` (PR #14 a #20). 967 tests automatizados. Se implementó en entregas incrementales, cada una en su propia rama, con tests y Pull Request, igual que `v0.2.0`.

### Entregas de `v0.3.0`

1. **Catálogos** ✓ (PR #14): modelos de estados, prioridades, categorías, ubicaciones y motivos de cierre, su migración y el comando `seed-catalogs`.
2. **Modelo de tickets** ✓ (PR #15): tickets, solicitantes e historial inmutable, con el identificador público generado por una secuencia de PostgreSQL, y el servicio de creación.
3. **Administración de catálogos** ✓ (PR #16): pantallas para que el Administrador gestione categorías, prioridades y ubicaciones, con auditoría. Se adelantó respecto del plan inicial para poder crear los datos de prueba desde la propia interfaz en lugar de cargarlos con seeds.
4. **Creación de tickets** ✓ (PR #17): formulario, políticas de creación y de visibilidad, un detalle de solo lectura y la opción "Crear ticket" en la navegación.
5. **Listado** ✓ (PR #18): "Tickets" y "Mis tickets", con pestañas, búsqueda (también desde la barra superior), filtros, orden y paginación, y la visibilidad de cada rol aplicada en la propia consulta.
6. **Detalle y edición autorizada** ✓ (PR #19): edición de título, descripción, categoría y ubicación, y cambio de prioridad con motivo obligatorio; historial con el detalle de cada cambio (el motivo, solo para el personal) y control de versión para las ediciones simultáneas.
7. **Cierre de la versión** ✓ (PR #20): revisión final y documentación. Añade una red de seguridad automática que recorre todas las rutas (sesión obligatoria y token CSRF en las rutas POST) y la guía de primera configuración del README, con un recorrido de prueba por rol y una tabla de solución de problemas.

### Decisiones de la fase

- **Sin datos de ejemplo en los seeds.** Los seeds cargan solo lo estructural. Categorías, ubicaciones y tickets de ejemplo se crean a mano desde la interfaz, para que una instalación real no arranque con datos ficticios; el README explica cómo.
- **Visibilidad del Solicitante:** ve los tickets que creó o en los que es solicitante vigente. Técnico, Supervisor y Administrador ven todos (RF-011). Un ticket ajeno responde 404, igual que uno inexistente, para no revelar qué números existen.
- **Categoría al crear:** es obligatoria; `Sin clasificar` se ofrece siempre al final de la lista y nunca preseleccionada.
- **Solicitantes al crear:** si crea un Solicitante, queda como su propio solicitante; Técnico, Supervisor y Administrador eligen 0..N solicitantes. Agregar o quitar solicitantes después llegó en `v0.4.0` (entrega 6).
- **Edición:** Técnico, Supervisor y Administrador editan título, descripción, categoría y ubicación, y cambian la prioridad con motivo obligatorio. El Solicitante solo lee, y un ticket cerrado no se edita.
- **Fuera de esta fase:** grupo, impacto y urgencia (sus catálogos llegan más adelante) y la pantalla de Estados y transiciones (UI-021), que se implementó en `v0.4.0` (entrega 12) junto con el flujo de estados.

### Implementación

- modelo Ticket;
- ID público;
- solicitante;
- creador;
- categoría;
- prioridad;
- ubicación;
- descripción;
- estados;
- creación;
- listado;
- detalle;
- edición autorizada;
- búsqueda;
- filtros;
- paginación;
- ordenamiento.

### Estados

```text
Nuevo
Asignado
En progreso
En espera
Resuelto
Cerrado
```

### Reglas críticas

- Solicitante solo accede a tickets autorizados;
- prioridad modificable por Técnico, Supervisor y Administrador, con motivo obligatorio y registro en el historial (la política de continuidad del SLA se aplica en `v0.5.0`);
- no se modifica la prioridad de un ticket cerrado sin reabrirlo;
- eliminación física reservada;
- cancelar no equivale a eliminar: la cancelación se representa como motivo de cierre (`CANCELACION`), no como estado;
- Reabierto no se implementa como estado estructural.

### Criterio de salida

Un usuario puede:

```text
crear ticket
→ verlo
→ encontrarlo
→ filtrarlo
→ abrir detalle
```

y cada rol ve únicamente lo autorizado.

Todos los criterios se cumplen. Además de lo previsto, la fase cierra con la edición con control de versión para las ediciones simultáneas, el cambio de prioridad con motivo y su registro en el historial, la administración de catálogos desde la interfaz y una verificación automática de que ninguna ruta queda sin autenticación ni sin protección CSRF.

### Lo que `v0.3.0` deja para `v0.4.0`

- el bloqueo temporal de edición (RN-115 a RN-117), que se sumará al control de versión;
- la pantalla de Estados y transiciones (UI-021) y su tabla de transiciones;
- los eventos del historial que aún no existen (estado, asignación, comentarios, resolución y cierre): **decidido** al comenzar la fase, el vocabulario queda solo en la aplicación (se elimina el CHECK de `historial_ticket.tipo_evento`) y cada evento declara su visibilidad (público o interno), entrega 1;
- las columnas de grupo, impacto y urgencia de `tickets`, cuando existan sus catálogos;
- la regla "un ticket en estado `CERRADO` tiene fecha y motivo de cierre", que depende del código del estado y se aplicará en el servicio de cierre.

---

# 17. FASE 4 — Asignación, colaboración y ciclo de vida

**Semana:** 5  
**Versión:** `v0.4.0`

**Estado de ejecución:** implementada, validada e integrada en `main` (PR #23 a #35). 2201 tests automatizados (1034 al empezar la fase). Se implementó en 12 entregas, cada una en su propia rama, con tests y Pull Request, y cada una amplió el seed de demostración (de 40 a 76 tickets).

### Entregas de `v0.4.0`

La fase se divide en 12 entregas pequeñas, cada una en su propia rama, con tests y Pull Request, como `v0.2.0` y `v0.3.0`:

1. **Historial** ✓ (PR #23): el vocabulario de eventos pasa a la aplicación y cada evento lleva su visibilidad (público o interno).
2. **Motivos de espera** ✓ (PR #24): catálogo configurable, su administración y la referencia desde el historial.
3. **Estados y transiciones** ✓ (PR #25): tabla de transiciones y cambios de estado operativos (iniciar, poner en espera, reactivar), con el control de versión compartido y el seed ampliado.
4. **Grupos** ✓ (PR #26): grupos, membresías y supervisores responsables (`/groups`), con tres grupos de ejemplo en `seed-demo`.
5. **Asignación** ✓ (PR #27): técnicos, grupo del ticket y escalamiento manual, con el seed ampliado.
6. **Solicitantes del ticket** ✓ (PR #28): agregar y retirar después de la creación (solo el personal, eventos internos, sin migración), con el seed ampliado.
7. **Comentarios y notas internas** ✓ (PR #30): comentarios públicos y notas internas con el filtro por tipo en la consulta, edición y eliminación con plazo para el autor, y el seed ampliado.
8. **Adjuntos** ✓ (PR #31): almacenamiento local fuera de `static/`, validación por extensión y contenido, SHA-256, descarga autenticada y visibilidad heredada de la nota interna, con el seed ampliado.
9. **Resolución, validación del solicitante, cierre y reapertura** ✓ (PR #32): resolver, confirmar o rechazar la solución, cierre directo y excepcional y reapertura, con la regla «cerrado ⇒ fecha y motivo de cierre», la tabla `validaciones`, el plazo de reapertura `REOPEN_WINDOW_DAYS` y el seed ampliado.
10. **Relaciones y duplicados** ✓ (PR #33): relacionar tickets, marcar un ticket como duplicado de otro (lo cierra con el motivo «Duplicado»), solo para el personal, con el seed ampliado.
11. **Bloqueo temporal de edición** ✓ (PR #34, RN-115 a RN-117): el ticket queda reservado mientras alguien edita sus datos o su prioridad, con aviso de quién edita, renovación mientras la pantalla está abierta y expiración automática; la versión sigue siendo la barrera final.
12. **Pantalla de Estados y transiciones (UI-021) y cierre de la versión** ✓ (PR #35, RN-164): el Administrador renombra los estados y habilita o deshabilita las transiciones opcionales sin poder romper el flujo. Incluye una revisión de toda la fase: el catálogo de acciones separado del motor de estados, `tickets/routes/` como paquete, un descriptor por evento del historial, los ayudantes repetidos unificados y una red de seguridad que comprueba la autorización de todas las rutas; además de la documentación de cierre.

### Decisiones de la fase

- **El vocabulario del historial vive en la aplicación.** Se eliminó el `CHECK` de `historial_ticket.tipo_evento`: añadir un evento ya no necesita una migración, pero obliga a decidir tres cosas (cómo se llama, quién lo ve y qué cuenta su línea del historial) y un test lo exige. La fase terminó con 23 eventos.
- **Quién ve qué se decide en la consulta, nunca en la plantilla.** Cada evento declara si es público o interno y la consulta del historial filtra según el rol; los comentarios (`visible_comments_condition`) y los adjuntos (`visible_attachments_condition`) siguen el mismo patrón. Cada condición SQL tiene su política equivalente en Python y un test comprueba que coinciden para todos los roles. Una nota interna no llega al Solicitante por ninguna superficie: ni el detalle, ni el historial, ni los conteos, ni los archivos, ni las descargas.
- **Una acción, una pantalla.** Cada acción (cambiar el estado, asignar, comentar, relacionar...) es una pantalla de confirmación o un formulario de una línea, con CSRF, que funciona sin JavaScript. Los modales y los paneles laterales quedan como mejora progresiva para `v0.9.0`; el JavaScript de la fase es opcional (contadores, filtros de listas y el latido del bloqueo de edición).
- **404 si no lo ve, 403 si lo ve pero no puede.** La regla de `v0.3.0` se mantuvo en todas las rutas nuevas. La entrega 12 añadió una red de seguridad (`tests/test_route_authorization.py`) que recorre el mapa de rutas y comprueba la propiedad del ticket, el rol y las áreas de administración, igual que `test_route_protection.py` hace con la autenticación y el CSRF: una ruta nueva queda cubierta sin tocar el test.
- **Un único camino para cambiar el estado.** `change_state` es el único que escribe el estado y los datos de resolución y cierre, y por eso «cerrado ⇒ fecha y motivo de cierre» no puede romperse; marcar un duplicado lo reutiliza. La asignación también mueve el estado por esa vía: el primer técnico pasa un ticket `Nuevo` a `Asignado` y quitar al último lo devuelve (acción `DESASIGNACION`, que `08_flujo_de_tickets.md` no listaba).
- **Concurrencia con la fila del ticket bloqueada.** Toda operación que cambia un ticket lo bloquea (`SELECT ... FOR UPDATE`) antes de validar, y cada operación que compite por un recurso (asignarse, confirmar la solución, quitar una relación, tomar el bloqueo de edición, renombrar un estado, deshabilitar transiciones) tiene su test con dos hilos.
- **Lo aditivo no sube la versión.** Comentarios, notas, adjuntos, relaciones y cambios de solicitantes no tocan `tickets.version` ni «Actualizado»: una nota interna no se delata en el listado del Solicitante y quien abrió la edición antes no recibe un conflicto por algo que no tocó.
- **Parámetros por variable de entorno hasta `v0.7.0`.** El plazo de edición de comentarios, el de reapertura, los límites de los adjuntos y los tiempos del bloqueo de edición se leen de variables de entorno validadas al iniciar. Pasarán a la configuración administrable cuando exista su pantalla.
- **El seed de demostración creció con cada entrega.** Usa los servicios reales y escribe fechas relativas al día en que se ejecuta. Además de servir para probar y mostrar el sistema, destapó fallos que los tests de servicio no veían, como el refresco de fechas con escalamientos hechos a mano (PR #29).
- **La revisión final es parte de la entrega.** La entrega 12 no solo añade la pantalla: ordena lo que creció durante la fase. El catálogo de acciones de estado salió de `lifecycle.py`, `tickets/routes.py` (casi 1850 líneas) pasó a un paquete por áreas sin cambiar ninguna ruta, el historial dejó una cadena de condiciones por un descriptor por evento y los ayudantes repetidos se unificaron, con tests que impiden que el catálogo y las políticas se separen.

### Lo que cambió respecto del plan inicial

- **Entró alcance que el plan dejaba fuera.** Agregar y retirar solicitantes después de crear el ticket (la fase 3 lo daba por hecho y la lista de esta fase no lo recogía), el escalamiento manual (RN-31) como acción propia y el catálogo de motivos de espera (RN-49) se sumaron al alcance: el primero como la entrega 6 y los otros dos dentro de las entregas 5 y 2.
- **La documentación se fue corrigiendo sobre la marcha**, cada vez que el código obligaba a decidir algo que no estaba escrito o que estaba escrito de otra forma: el nombre de la fase en el README, la matriz de permisos de Grupos (`docs/11`), las rutas de bloqueo que sugerían los primeros borradores de `docs/10`, la acción `DESASIGNACION` que `docs/08` no listaba y, al cerrar, los rangos de reglas de negocio de `docs/07`, que seguían una numeración anterior a la de `docs/06`.
- **Los datos de demostración destaparon fallos que los tests de servicio no veían.** Refrescar las fechas de un ticket con un escalamiento hecho a mano violaba un `CHECK` de `tickets_tecnicos`: un fallo de la entrega 5 que se corrigió aparte (PR #29) y quedó cubierto por un test de regresión en la entrega 6. Desde entonces, cada entrega que añade fechas nuevas extiende el refresco y el test que compara un refresco con una carga nueva.

### Implementación

- grupos (opcionales) y supervisores responsables de cada grupo (`grupos_supervisores`), con gestión de membresías por el Administrador y por el Supervisor en sus grupos;
- múltiples técnicos;
- asignación directa a técnicos, con o sin grupo;
- solicitantes que se agregan y se retiran después de crear el ticket;
- cambio de estado;
- comentarios públicos;
- notas internas;
- adjuntos;
- historial;
- relaciones esenciales;
- resolución;
- cierre manual;
- confirmación por solicitante;
- rechazo;
- reapertura.

### Regla crítica

```text
Nota interna
→ Técnico / Supervisor / Administrador

Solicitante
→ nunca
```

### Validación de resolución

```text
Resuelto
↓
Solicitante confirma
↓
Cerrado
```

o:

```text
Resuelto
↓
Solicitante rechaza
↓
reapertura
↓
retorno al flujo activo
```

### Criterio de salida

El flujo completo de un ticket puede ejecutarse desde creación hasta cierre.

Todos los criterios se cumplen. Además de lo previsto, la fase cierra con el bloqueo temporal de edición, las relaciones y los duplicados, la administración de grupos, de los motivos de espera y de los estados y transiciones, y un recorrido automático de la autorización de todas las rutas.

### Lo que `v0.4.0` deja para las fases siguientes

- **`v0.5.0`:** el cierre automático por inactividad (la transición `AUTO_CIERRE` y el motivo `INACTIVIDAD` existían desde `v0.4.0` y el planificador de la entrega 8 los usa), el SLA con su calendario laboral y las notificaciones internas, entre ellas las que avisan a los técnicos cuando el Solicitante comenta (RF-068). Mientras tanto, un ticket resuelto sin solicitante solo lo cierra el Supervisor o el Administrador (cierre excepcional).
- **`v0.6.0`:** la reasignación masiva y la carga de trabajo (ver la fase 6).
- **`v0.7.0`:** los parámetros que hoy son variables de entorno (plazo de edición de comentarios, plazo de reapertura, límites de los adjuntos y tiempos del bloqueo de edición) pasan a la configuración administrable.
- **`v0.9.0`:** las pestañas del detalle (Actividad, Archivos, Historial y Relaciones; hoy son tarjetas apiladas), los modales y paneles laterales como mejora progresiva, y el color y el orden de los estados (RF-118).
- **`v0.7.0`:** la advertencia de posibles tickets duplicados al crear uno (RF-061), junto a la base de conocimiento, que comparte la búsqueda.
- **Sin fase asignada todavía:** los adjuntos desde el formulario de creación; las columnas de impacto y urgencia, cuando existan sus catálogos; y la liberación manual de un bloqueo de edición por el Supervisor o el Administrador.
- **Después del MVP:** la actualización en tiempo real de quién edita un ticket (sección 32), la vista previa de imágenes y la eliminación física de archivos con sus políticas de retención.

---

# 18. FASE 5 — SLA y notificaciones internas

**Semana:** 6  
**Versión:** `v0.5.0`

**Estado de ejecución:** implementada, validada e integrada en `main` (PR #36 a #45). 3965 tests automatizados (2201 al empezar la fase). Se implementó en 9 entregas pequeñas, cada una en su propia rama, con tests y Pull Request, como las fases anteriores (más una optimización de la suite de tests, PR #42); la novena fue una revisión de toda la fase.

### Entregas de `v0.5.0`

1. **Motor de tiempo laboral compartido** ✓ (PR #36): el motor del seed de demostración pasa a `worktime.py` y gana las dos operaciones que necesita el SLA (medir los segundos laborales entre dos momentos y sumarlos a un momento). Sin migración ni cambio funcional.
2. **Calendario laboral administrable** ✓ (PR #37): tablas `calendarios_laborales`, `horarios_laborales` y `feriados` (versionadas), el motor con franjas distintas por día, la función que resuelve el calendario vigente (el guardado o `DEMO_CALENDAR`), la pantalla «SLA» con la de «Configurar calendario» y el seed leyendo el calendario resuelto.
3. **Políticas de SLA por prioridad** ✓: `politicas_sla` (una por prioridad, editable en el sitio y sin columna de calendario: usa el vigente) y su pantalla (UI-022) dentro de «SLA», con las duraciones escritas como «4 h» o «1 h 30 min», la pausa en espera por política y el control de ediciones simultáneas; los valores iniciales los carga `seed-catalogs` (RN-165).
4. **Períodos de SLA** ✓ (PR #39): `tickets_sla_periodos`, el cálculo en tiempo laboral, la pausa en `En espera`, la detención al resolver (y la reanudación al reabrir) y la continuidad ante cambios de prioridad (RN-88 y RN-166); el comando `sla-rebuild` para los tickets anteriores y `sla-status` para ver un ticket. El seed de demostración deja los tickets en tiempo, por vencer, vencidos y pausados.
5. **Notificaciones internas, 1: infraestructura y centro de notificaciones** ✓: la tabla `notificaciones` (contenido inmutable, solo evoluciona la lectura), el servicio (`notify`, `notify_many`, consultar, contar y marcar), el centro (`/notifications`, con «Todas» y «No leídas») y la campana con contador que se actualiza cada 30 segundos (RN-167). Todavía **ningún evento genera avisos** (entrega 6): mientras tanto, el comando `seed-demo-notifications` deja avisos de ejemplo para verlo funcionar.
6. **Notificaciones internas, 2: eventos** ✓: asignación, cambios de estado (espera, resolución, cierre, rechazo y reapertura) y comentarios avisan a quien corresponde desde las propias operaciones de los tickets, con las reglas de RN-168 (incluye RF-068, RN-95 y RN-96). Crear un ticket no avisa a nadie, por decisión de la fase. Quién recibe cada aviso se decide en `notifications/events.py`.
7. **Indicadores de SLA en la interfaz** ✓: insignias en el listado y tarjeta en el detalle (solo para el personal), filtro por estado de SLA y orden «SLA más urgente», y la advertencia al bajar la prioridad con el SLA en riesgo, con el aviso a los Supervisores (RN-88 y RN-169). Los períodos guardan ahora cuándo alcanzan el umbral de aviso (una migración), lo que permite filtrar en la base de datos.
8. **Planificador** ✓: el comando `run-scheduler` (bucle o `--once`, sin dependencias nuevas) con los avisos de SLA (*próximo a vencer* y *vencido*, una sola vez por período) y el cierre automático de los tickets `Resuelto` sin validar (RN-58, RN-59 y RN-170). Una migración añade a los períodos las marcas de aviso enviado.
9. **Cierre de la versión** ✓: revisión de todo el código de la fase y documentación de cierre (ver «Cierre de la fase»).

### Decisiones de la fase

Se tomaron al planificarla y se reflejan en el resto de los documentos cuando cada entrega las implementa.

- **El planificador es un comando propio, sin dependencias nuevas.** `10_arquitectura.md` (secciones 84 y 85) preveía APScheduler. Como las tareas son idempotentes (sección 86), basta un comando (`run-scheduler`: un bucle simple que también puede ejecutarse una sola vez desde el Programador de tareas de Windows o desde `cron`) que se ejecuta como proceso separado del web, con el mismo código. Esas secciones se actualizaron en la entrega 8.
- **«Primera respuesta» es el primer comentario público del personal** (Técnico, Supervisor o Administrador). Asignar el ticket o cambiar su estado no cuenta: no garantizan que el solicitante haya recibido una respuesta. Sigue siendo un objetivo opcional de la política (`09_modelo_de_datos.md`, 20.2, que se completa en la entrega 3).
- **Las excepciones de SLA (RF-083, `sla_excepciones`) quedan fuera de la fase.** La lista de esta fase no las incluía; se decidirán con los dashboards de `v0.6.0` o con la configuración de `v0.7.0`. Cambiar la prioridad no es una excepción: tiene su propia política de continuidad (RN-88).
- **La pausa del SLA no necesita columnas nuevas.** Al entrar en `En espera` con una política que pausa, el período se cierra y, al reanudar, se abre otro que arrastra el consumo acumulado: «pausado» significa ticket en `En espera` cuya política pausa. Encaja con que un período cerrado nunca se sobrescribe (`09_modelo_de_datos.md`, 20.3).
- **El plazo del cierre automático es una variable de entorno** (24 horas por defecto, RN-58) hasta que exista la configuración administrable de `v0.7.0`, como los demás parámetros que dejó `v0.4.0`.

### SLA

Implementar:

- políticas por prioridad ✓ (entrega 3);
- primera respuesta opcional ✓ (entrega 3: se configura; la mide el cálculo de la entrega 4);
- objetivo de resolución ✓ (entrega 3);
- porcentaje de aviso ✓ (entrega 3);
- calendario laboral administrable (ver más abajo) ✓ (entrega 2);
- pausa en `En espera` ✓ (entregas 3 y 4);
- reanudación ✓ (entrega 4);
- próximo a vencer ✓ (entrega 4: el cálculo; los avisos, entregas 6 y 8);
- vencido ✓ (entrega 4: el cálculo; los avisos, entregas 6 y 8);
- visualización ✓ (entrega 7);
- configuración básica (el interruptor general «Aplicar SLA a los tickets» y los avisos configurables dependen de la tabla `configuracion`: `v0.7.0`, RN-165);
- política de continuidad ante cambios de prioridad (RN-88): el consumo ya acumulado se conserva, el incumplimiento registrado no se borra, un cambio nunca reinicia el reloj, y la bajada de prioridad con el SLA en riesgo exige motivo y avisa a los Supervisores.

### Calendario laboral administrable

El SLA se calcula en tiempo laboral, así que el calendario se construye en esta fase como parte del SLA y no como un dato de apoyo:

- tablas `calendarios_laborales`, `horarios_laborales` y `feriados` (`docs/09`, sección 21), con un único calendario global vigente y versionado: guardar un cambio crea una versión nueva y no altera las que ya usan períodos de SLA. ✓ Entrega 2: ninguna versión se modifica una vez guardada y quien guarda indica con qué versión abrió la pantalla, así que un guardado sobre una pantalla desactualizada se rechaza en lugar de pisar el cambio ajeno;
- **motor de tiempo laboral compartido** (medir y sumar tiempo laboral, contar días laborales, saltar noches, fines de semana y feriados). ✓ Entrega 1: el motor que tenía el seed `seed-demo-tickets` (`_BusinessClock`) pasó a `worktime.py`, con las dos operaciones que necesita el SLA, y lo usarán el SLA y el seed en lugar de duplicarlo (ver `10_arquitectura.md`, «Tiempo laboral»);
- **pantalla del Administrador** (RF-079; `docs/11`, «Configurar calendario»): días y franjas laborales, feriados, zona horaria y versión vigente, con auditoría de los cambios, enlazada desde la tarjeta «SLA» del hub de administración. ✓ Entrega 2 (`/admin/sla` y `/admin/sla/calendar`). El horario de cada día es un texto (`09:00-18:00` o `09:00-13:00, 14:00-18:00`) y los feriados otro, uno por línea: así el motor y la base admiten varias franjas por día sin filas dinámicas;
- **calendario por defecto:** mientras el Administrador no haya guardado ninguno, todo el sistema (el SLA y los datos de demostración) usa `DEMO_CALENDAR` (lunes a viernes de 09:00 a 18:00, sin feriados) y la pantalla lo indica. En cuanto se guarda uno, todos usan el guardado. Una única función resuelve el calendario vigente (`docs/09`, sección 40.8). ✓ Entrega 2: `resolve_work_calendar`;
- `seed-demo-tickets` pasa a leer el calendario resuelto (el guardado o el predeterminado): `DEMO_CALENDAR` y la configuración de la interfaz conviven. ✓ Entrega 2: con un calendario guardado, ningún evento de los tickets demo cae fuera de sus franjas ni en un feriado, y la hora de creación de cada ticket pasa al siguiente momento de trabajo si cae en una pausa.

### Cierre automático

El planificador que dispara los avisos de SLA (`docs/10`, secciones 84 a 87) ejecuta también el cierre automático de los tickets `Resuelto` que el solicitante no valida (RN-58) y de los resueltos sin solicitante (RN-59). Reutiliza lo que `v0.4.0` dejó preparado: la transición `AUTO_CIERRE` (cargada y marcada como esencial, pero que nada ejecuta todavía), el motivo de cierre `INACTIVIDAD` y la columna `tickets.cerrado_automaticamente`. Debe cerrar por el mismo camino que las demás acciones (`change_state`), de modo que el ticket quede con fecha y motivo de cierre como siempre, y el plazo debe ser configurable.

**Avance (entrega 8).** Hecho: `close_automatically` (`tickets/lifecycle.py`) cierra con la transición `AUTO_CIERRE`, el motivo `INACTIVIDAD` y `cerrado_automaticamente`, con el Sistema como actor; el plazo es `AUTO_CLOSE_HOURS` (24 por defecto) y se vuelve a comprobar con el ticket bloqueado (RN-170).

### Notificaciones internas

Eventos iniciales recomendados:

- ticket creado;
- ticket asignado;
- cambio de estado;
- comentario público;
- resolución;
- solicitud pendiente de validación;
- reapertura;
- SLA próximo;
- SLA vencido.

No implementar correo.

**Avance (entrega 8).** Los avisos de SLA ya los genera el planificador (RN-170). **Avance (entrega 6).** Los eventos de ticket ya generan avisos (RN-168); los de SLA llegaron con el planificador (entrega 8). **Entrega 5:** dejó el vocabulario de eventos (`NotificationEvent`, los nueve de la lista más reasignación, nota interna, espera y cierre), el servicio y el centro con la campana. La generación por eventos (entrega 6) y los avisos de SLA (entrega 8) las producirán con `notify` y `notify_many`; el servicio no decide a quién avisar (esa regla es de quien genera el aviso y sigue la visibilidad del historial; ver `10_arquitectura.md`, «Notificaciones internas»). La configuración de eventos y destinatarios (RN-97) llega con `v0.7.0`.

### Cierre de la fase

La última entrega no añadió una pantalla: revisó **toda** la fase, y empezó por medir en lugar de suponer (tamaño y complejidad de los módulos, código sin uso, comentarios que hablaban de lo hecho como futuro, consultas por pantalla y tiempos de la suite).

**Lo que cambió, y por qué:**

- **`cli.py` pasó a un paquete** (`src/workdesk/cli/`, con `setup`, `demo`, `sla` y `scheduling`): era una sola función con complejidad 33 y 105 sentencias donde se habían apilado los comandos de tres fases. Los comandos no cambiaron.
- **El incumplimiento del SLA queda registrado** (RN-91 pedía informarlo, avisar y registrarlo): el planificador deja el evento interno `SLA_VENCIDO` en el historial al avisar del vencimiento. Es el único cambio de comportamiento.
- **Un bloqueo mutuo** entre el planificador y un cambio de estado simultáneo sobre el mismo ticket (el planificador bloqueaba primero el período y los cambios de estado, el ticket): se reprodujo con un test de hilos y se corrigió bloqueando siempre el ticket primero.
- **La campana mantenía viva una sesión abandonada.** Su consulta automática cada 30 segundos pasaba por los límites de sesión como una petición más y renovaba la última actividad: una pestaña olvidada con la campana visible nunca expiraba por inactividad (solo por las 8 horas de duración máxima). Ninguna prueba lo veía, porque cada una comprobaba una cosa a la vez (la campana por un lado y la expiración por otro). Ahora las consultas pasivas se comprueban igual que cualquier petición (con la sesión expirada responden `401`) pero no cuentan como actividad (`auth/session.py`, `PASSIVE_ENDPOINTS`).
- **Pruebas nuevas:** las pantallas con los 76 tickets de demostración, con un presupuesto de consultas por petición; las migraciones (suben, coinciden con los modelos, bajan y vuelven a subir), que ninguna otra prueba comprobaba porque el esquema de la suite sale de los modelos; una **instalación limpia** que sigue los pasos del README sobre un esquema creado solo por las migraciones y revisa lo que deja en la base de datos (lo que `db check` no ve: secuencias, valores por defecto y restricciones; se comprobó quitando un valor por defecto de una migración: `db check` seguía pasando y esta prueba falló con el error real); la coherencia de los documentos con las variables de entorno, los comandos, las migraciones y la lista de rutas (el README no listaba cinco rutas de «SLA» y nadie lo había notado); las reglas RN-85, RN-86 y RN-87, que se cumplían por construcción pero no tenían una prueba que las defendiera (`test_sla_business_rules.py`); y que la consulta de la campana no renueve la sesión (con un reloj que se mueve a mano, sin esperar minutos). Los datos de demostración compartidos y la hora de las pruebas de SLA pasaron a `conftest.py` y `tests/demo_data.py`.
- **Documentación:** los textos que daban por futuro lo ya hecho se corrigieron.

**Medido y dejado como está:** no hay código muerto real; las consultas están acotadas (listado 14 o 15, detalle hasta 22 para el personal y 12 para el Solicitante, pantallas de acción hasta 23) y no hay una consulta por fila en ninguna pantalla; con **casi 20 000 tickets** (23 000 períodos de SLA, 54 000 eventos de historial y 12 000 notificaciones, medido en un esquema desechable de la base de pruebas) el número de consultas por pantalla no cambia, el listado responde en unos 30 ms (entre 80 y 230 ms con el filtro y el orden por SLA), el centro de notificaciones en 17 ms y la campana en 3 ms, muy por debajo de los 2 segundos de RNF-001, y el planificador encuentra 16 000 avisos pendientes en 17 ms y envía cada uno en unos 6 ms; la función `_refresh` del seed de tickets (complejidad 52) es una herramienta de desarrollo cubierta por 259 tests y se anota como deuda técnica antes que arriesgar su comportamiento; y las funciones con muchos argumentos son la API de palabras clave del proyecto.

**Trazabilidad de los requisitos de la fase.** Al cerrar se comprobó, uno por uno, cada requisito de `04_requisitos_funcionales.md` (RF-077 a RF-087) y de `06_reglas_de_negocio.md` (RN-58, RN-59 y RN-85 a RN-97) contra el código y las pruebas que lo cubren. Es la forma de responder «¿está todo lo que se prometió?» sin fiarse de la memoria de nadie:

| Requisito | Estado | Dónde vive | Quién lo prueba |
| --- | --- | --- | --- |
| RF-077 configurar el SLA · RN-92 (configura el Administrador) · RN-165 | Hecho (el interruptor general queda para `v0.7.0`) | `sla/policies.py` y la pantalla «SLA» (`/admin/sla`) | `test_sla_policies.py`, `test_sla_policy_forms.py`, `test_sla_policies_routes.py` |
| RF-078 cálculo del SLA · RN-166 | Hecho | `sla/periods.py` (`reconcile_sla`), `sla/evaluation.py` (`evaluate_ticket_sla`) | `test_sla_periods.py` |
| RF-079 horarios y feriados · RN-90 | Hecho | `worktime.py`, `sla/work_calendar.py` y `/admin/sla/calendar` | `test_worktime.py`, `test_work_calendar.py`, `test_work_calendar_routes.py` |
| RF-080 pausa del SLA · RN-89 | Hecho (la pausa es por política) | `sla/periods.py` | `test_sla_periods.py`, `test_sla_policies.py` |
| RF-081 indicador de estado · RN-91 (informar) | Hecho (solo para el personal, RN-169) | `sla/queries.py`, listado y detalle de tickets | `test_sla_indicators.py`, `test_sla_indicators_ui.py` |
| RF-082 aviso de vencimiento · RN-91 (avisar y registrar) | Hecho: un aviso por período y el evento `SLA_VENCIDO` en el historial | `scheduler.py`, `notifications/events.py` | `test_scheduler.py` |
| RF-083 excepciones de SLA · parte de RN-92 | **Fuera de la fase** (`v0.6.0` o `v0.7.0`) | — | — |
| RF-084 generación de avisos · RN-94, RN-95 y RN-96 | Hecho, con una decisión: crear un ticket no avisa a nadie (RN-168) | `notifications/events.py`, llamado desde los servicios de tickets | `test_notification_events.py` |
| RF-085 centro de notificaciones · RF-086 estado de lectura · RN-93 | Hecho | `notifications/` (servicio, rutas y campana) | `test_notifications.py`, `test_notifications_routes.py` |
| RF-087 configurar eventos y destinatarios · RN-97 | **Fuera de la fase** (`v0.7.0`) | — | — |
| RN-58 y RN-59 cierre automático | Hecho (el plazo es una variable de entorno hasta `v0.7.0`) | `scheduler.py`, `tickets/lifecycle.py` (`close_automatically`) | `test_scheduler.py` |
| RN-85, RN-86 y RN-87 el SLA es del ticket, no bloquea y no depende de la carga | Hecho, por construcción | los períodos cuelgan del ticket; ninguna operación consulta el SLA para permitirse | `test_sla_business_rules.py` |
| RN-88 prioridad y continuidad | Hecho | `sla/periods.py`, `tickets/editing.py`, `notifications/events.py` | `test_sla_periods.py`, `test_sla_indicators_ui.py` |

Las tres cosas que quedan fuera no se perdieron ni se olvidaron: se decidieron al planificar la fase (ver «Decisiones de la fase») y siguen escritas más abajo con su destino. Dos requisitos tenían una forma de cumplirse más estricta de la que se eligió y conviene decirlo: RN-91 pedía *registrar* el incumplimiento y la primera versión de la fase solo lo dejaba deducible de las fechas (se cerró en esta entrega con `SLA_VENCIDO`), y RF-084 lista la creación entre los eventos que avisan, pero un aviso al crear un ticket no le dice nada a nadie (quien lo crea ya lo ve y quien lo atiende lo conocerá al asignarlo), así que se decidió no generarlo.

**Lo que la fase deja para las siguientes** (cada cosa con su destino): las excepciones de SLA (RF-083, con los dashboards de `v0.6.0` o la configuración de `v0.7.0`), la configuración de eventos y destinatarios de las notificaciones (RF-087 y RN-97, `v0.7.0`), el interruptor general del SLA (RN-165, `v0.7.0`), los avisos de la primera respuesta vencida y la política de retención de las notificaciones leídas (sin fase asignada) y la actualización en tiempo real de las notificaciones (después del MVP; hoy es un contador que se consulta cada 30 segundos).

### Criterio de salida

```text
✓ SLA se calcula en tiempo laboral
✓ el Administrador configura el calendario laboral y el SLA lo respeta
✓ sin calendario guardado se usa el predeterminado
✓ cambia según prioridad
✓ puede pausarse
✓ vuelve a continuar
✓ genera indicadores
✓ un ticket resuelto que nadie valida se cierra solo
✓ notificaciones aparecen
✓ usuario puede marcarlas como leídas
```

---

# 19. FASE 6 — Dashboards y carga de trabajo

**Semana:** 7  
**Versión:** `v0.6.0`

**Estado de ejecución:** implementada, validada e integrada en `main` (PR #46 a #55). 4175 tests automatizados (3965 al empezar la fase). Se implementó en 10 entregas pequeñas, cada una en su propia rama, con tests y Pull Request; la décima fue la revisión de toda la fase. Los tickets de demostración pasaron de 76 a 108.

### Entregas de `v0.6.0`

1. **Revisión de lo construido: backend/API y tests** ✓: el seed de tickets pasa a un paquete y sus funciones complejas se descomponen; las consultas del listado salen de `tickets/service.py` a `tickets/queries.py`; los endpoints JSON comparten forma de error y todas las respuestas llevan cabeceras de seguridad; `ruff.toml` fija un límite de complejidad; y los tests se ordenan. Sin migraciones.
2. **Revisión: README, PROJECT_CONTEXT y docs** ✓: el relato por entrega pasa a `14_historial_de_implementacion.md` y el README y `PROJECT_CONTEXT.md` quedan centrados en el estado actual.
3. **Listado: filtros de asignación** ✓: filtros por técnico, grupo, «sin asignar», «activos», «pendientes de mi revisión» y «cerrados desde», `sla=riesgo`, y las columnas Técnico(s) y Grupo para el personal. Son el destino de los enlaces de los dashboards.
4. **Dashboard del Solicitante** ✓: abiertos, en progreso, requieren tu revisión, cerrados recientes, tickets y notificaciones recientes (UI-002, RF-097).
5. **Carga de trabajo: consultas** ✓: por técnico, por grupo y sin asignar, con el aviso de sobrecarga informativo (RF-036 a RF-038).
6. **Carga de trabajo: pantalla** ✓ (UI-006): `/workload` para Técnico, Supervisor y Administrador.
7. **Dashboard operacional** ✓: contadores, tickets prioritarios, carga compacta y actividad reciente para el personal; «Mi trabajo» para el Técnico y un bloque administrativo para el Administrador (RF-093 a RF-096).
8. **Reasignación masiva: servicio** ✓ (RF-034 y RF-035, RN-30): mover los tickets de un técnico a otros con historial, auditoría y avisos.
9. **Reasignación masiva: pantalla** ✓ (UI-007): selección, resumen y confirmación, con la carga de cada destino a la vista (RF-033).
10. **Cierre de la fase** ✓: revisión de todo lo anterior, comprobación de escala y matriz de trazabilidad.

### Decisiones de la fase

Se tomaron al planificarla:

- **La reasignación masiva entra en esta fase** (dos entregas). Es alcance MVP y la nota de `v0.4.0` ya la asignaba aquí, aunque el alcance de la fase no la listaba.
- **Definiciones de las métricas.** *Abierto* es todo ticket no cerrado (un `Resuelto` sigue abierto, como en el listado). *Activo* (carga de trabajo) es el que no está `Resuelto` ni `Cerrado`. *Sin asignar* es un ticket activo sin técnico vigente. *Crítico* es el de prioridad `CRITICA`. *SLA en riesgo* es próximo a vencer más vencido. *Cerrados recientes* son los de los últimos 7 días. Un ticket con varios técnicos cuenta en cada uno y una sola vez en los totales.
- **Cada cifra coincide con el total del listado al que enlaza**, y un test lo comprueba para cada rol con los tickets de demostración.
- **Dashboard del Técnico:** el operacional global más un bloque «Mi trabajo». El Administrador ve el operacional más un bloque breve de indicadores administrativos. El Técnico ve la carga de todo el equipo, sin ranking.
- **Sin gráficos ni librerías nuevas:** cifras exactas (por ejemplo «nuevos hoy») y barras con CSS. Los gráficos se deciden en los reportes (`v0.8.0`).
- **Sobrecarga (RF-037):** variable de entorno `WORKLOAD_HIGH_ACTIVE_TICKETS` (10 por defecto; 0 la desactiva) hasta `v0.7.0`; es una insignia con texto, nunca notifica ni bloquea una asignación (RN-26).
- **Sin migraciones previstas.** Solo se añadiría un índice por `historial_ticket(fecha_hora)` si se mide que la actividad reciente lo necesita; sin caché.
- **Fuera de la fase,** con su destino: las excepciones de SLA (RF-083) y los pendientes sin fase (adjuntos al crear un ticket, advertencia de duplicados, liberar un bloqueo de edición, primera respuesta vencida, retención de notificaciones, el interruptor general del SLA y los parámetros en variables de entorno) van a `v0.7.0`; impacto y urgencia, después del MVP.

### Cierre de la fase (entrega 10)

Se revisó todo lo de `v0.6.0` y se comparó cada requisito de la fase con el código. Lo que se encontró y se hizo:

- **La matriz de trazabilidad destapó tres huecos reales** que los tests de cada entrega no podían ver, porque cada uno comprobaba lo que se había construido y no lo que se había prometido: los tickets *resueltos* de cada técnico (RF-036) se calculaban y no se mostraban; el dashboard del Técnico no traía sus tickets *en progreso* y *en espera* (RF-094); y el del Supervisor no tenía los tickets *por prioridad* (RF-095). Se completaron los tres, con enlace a su listado y su test de «la cifra es el total del listado».
- **Un error en la reasignación masiva:** quien dejó de ser Técnico (cambio de rol) conservaba sus tickets pero la pantalla de origen lo ofrecía y el servicio lo rechazaba (RN-104 y RN-137 piden poder redistribuir su trabajo). El técnico de origen es ahora cualquier usuario que aún tenga tickets asignados.
- **Escala (RNF-001).** Con ~20 000 tickets y 66 000 eventos, en una base de pruebas: dashboard del personal ~350 ms, carga de trabajo ~260 ms, reasignación 270 a 360 ms, listado de 35 a 190 ms y dashboard del Solicitante 45 ms, con un número de consultas que no crece con los datos. Medir sirvió: la carga de trabajo calculaba el resumen con un segundo recorrido completo del SLA que repetía el de los grupos; ahora lo suma de ellos (610 → 260 ms). Reasignar 500 tickets a la vez tarda ~3,2 s y se deja así (operación rara, por ticket a propósito).
- **Medido en una tabla temporal** para decidir el índice del historial en la entrega 7: la actividad reciente pasó de 79 ms a 0,09 ms con 250 000 eventos.
- **Limpieza:** un campo calculado y nunca mostrado se eliminó (`unassigned_at_risk`) y los que no se mostraban se usan; las funciones privadas que importaba otro módulo pasaron a ser públicas; y ninguna función supera la complejidad 12.

#### Matriz de trazabilidad

| Requisito | Estado | Dónde | Pruebas |
| --- | --- | --- | --- |
| RF-033 reasignar según la carga | Hecho | `/reassign` muestra la carga de cada destino, solo como dato | `test_reassignment_screen` |
| RF-034 reasignación masiva | Hecho | `tickets/reassignment.py`, `/reassign` | `test_ticket_reassignment`, `test_reassignment_screen` |
| RF-035 conservar el historial | Hecho | asignación cerrada y conservada, eventos con lote y motivo, una auditoría | `test_ticket_reassignment` |
| RF-036 / RN-27 información de carga | Hecho, salvo «sin actividad reciente» | `workload/queries.py`, `/workload` (asignados y activos, en progreso, en espera, críticos, SLA, resueltos y distribución por prioridad) | `test_workload_queries`, `test_workload_screen` |
| RF-037 / RN-28 sobrecarga informativa | Hecho como insignia con texto; **los avisos internos quedan para `v0.7.0`** | `WORKLOAD_HIGH_ACTIVE_TICKETS` | `test_workload_queries` |
| RF-038 carga consolidada | Hecho | `/workload` (técnicos, grupos y sin asignar) | `test_workload_screen` |
| RF-093 dashboard según el rol | Hecho | `main/routes.py` | `test_dashboard_requester`, `test_dashboard_staff` |
| RF-094 dashboard del Técnico | Hecho | «Mi trabajo» (activos, en progreso, en espera, críticos, SLA y resueltos en 7 días) | `test_dashboard_staff` |
| RF-095 dashboard del Supervisor | Hecho | contadores globales, sin asignar, carga por técnico, tickets por prioridad, SLA | `test_dashboard_staff` |
| RF-096 dashboard del Administrador | Hecho | bloque «Administración» | `test_dashboard_staff` |
| RF-097 dashboard del Solicitante | Hecho | `dashboard/requester.py` | `test_dashboard_requester` |
| RN-24 y RN-25 varios tickets por técnico y varios técnicos por ticket | Hecho | la suma por técnico puede superar al total, y la pantalla lo explica | `test_workload_queries` |
| RN-26 la carga no bloquea | Hecho | ninguna asignación mira la carga | `test_high_load_never_blocks_an_assignment` |
| RN-29 y RN-30 redistribución y reasignación masiva | Hecho | asignación individual y `/reassign` | `test_ticket_reassignment` |
| RN-104, RN-137 a RN-139 continuidad ante la ausencia de un técnico | Hecho | origen desactivado o que dejó de ser Técnico; no se pierde historial, comentarios ni archivos | `test_ticket_reassignment` |

**Queda fuera de la fase,** con su destino: los tickets «sin actividad reciente» (RF-036, RN-27) y los avisos internos de sobrecarga (RN-28), que necesitan decidir qué es «reciente» y quién recibe el aviso, y se resuelven con la configuración de `v0.7.0`.

### Dashboard Solicitante

- abiertos;
- en progreso;
- requiere revisión;
- cerrados recientes;
- tickets recientes;
- notificaciones.

### Dashboard operacional

- abiertos;
- sin asignar;
- críticos;
- fuera SLA;
- próximos SLA;
- en espera;
- tickets prioritarios;
- carga de trabajo;
- actividad reciente.

### Carga de trabajo

- tickets activos por técnico;
- grupo;
- críticos;
- SLA en riesgo;
- sin asignar.

### Reasignación masiva

Mover varios tickets de un técnico (por vacaciones, licencia o desvinculación) a uno o más técnicos en una sola operación, conservando el técnico anterior, el nuevo, la fecha, quién la ejecutó y qué tickets se movieron (RF-034 y RF-035). Es una pantalla distinta de la carga de trabajo: la carga se analiza, la reasignación modifica la distribución.

### Consideración

Un ticket puede tener varios técnicos.

Por tanto:

```text
suma de carga por técnico
≠ necesariamente total de tickets únicos
```

### Criterio de salida

Los dashboards reflejan datos reales de la base de datos y permiten navegar hacia los listados relacionados.

---

# 20. FASE 7 — Administración y Base de conocimiento

**Semana:** 8 y primera mitad de 9  
**Versión:** `v0.7.0`

**Estado de ejecución:** completada. Diez entregas (PR #56 a #65).

### Entregas de `v0.7.0`

1. **Revisión previa** ✓: auditoría de lo construido en las fases anteriores. El login deja de delatar qué usuarios existen por el tiempo de respuesta y vacía la sesión anterior, una consulta menos en cada pantalla (el rol viaja con el usuario), una única definición de los 14 parámetros numéricos (`settings.py`), limpieza de las subidas cortadas y documentación alineada. Sin migraciones.
2. **Tabla `configuracion`** ✓: modelo, migración, lectura (una consulta por petición, sin caché entre peticiones, para que el servidor web y el planificador vean siempre el valor vigente), auditoría de cada cambio y las variables de entorno como valor inicial. El tope de subida de Flask debe seguir al valor vigente.
3. **Pantalla de configuración** ✓ de los parámetros de sesión, contraseñas, comentarios, reapertura, cierre automático, archivos, carga alta y bloqueo de edición, y el interruptor general del SLA y del cierre automático.
4. **Configuración de notificaciones** ✓: qué eventos se envían y a quién, sin un motor de reglas, respetando que un Solicitante nunca recibe lo interno.
5. **Base de conocimiento: modelo y migración** ✓: artículos, vínculo con tickets y la columna de búsqueda de texto completo (`tsvector` en español con índice GIN).
6. **Base de conocimiento: pantallas** ✓: listado, búsqueda, detalle, borrador y publicado, destacados, con la visibilidad por rol resuelta en la consulta.
7. **Vínculo con tickets, promoción de una resolución (RF-104 y RF-105) y advertencia de posibles duplicados al crear un ticket (RF-061)** ✓, que comparten la búsqueda.
8. **Adjuntos al crear un ticket y liberación manual de un bloqueo de edición** ✓.
9. **Estructura y protecciones** ✓: sin cambios de comportamiento. Las dos pantallas más grandes y los dos módulos más largos divididos por responsabilidad, el código duplicado reunido y cuatro protecciones nuevas (esquema de las migraciones igual al de los modelos, rutas de la base de conocimiento, reglas del frontend e interruptores documentados). Sin migraciones.
10. **Cierre de la fase** ✓: correcciones de la auditoría, ubicación obligatoria (RF-019), comprobación de escala (~20 000 tickets), matriz de trazabilidad, documentación y etiqueta.

### Decisiones de la fase

Se tomaron al planificarla:

- **La configuración se lee de la base de datos una vez por petición** y no se guarda entre peticiones: el planificador es otro proceso y una caché dentro del servidor web no vería los cambios del Administrador (ni a la inversa).
- **La búsqueda de la base de conocimiento usa el texto completo de PostgreSQL** (diccionario en español e índice GIN, sin dependencias nuevas). Es más de lo que pedía el plan (`ILIKE`) pero evita rehacerla cuando se reutilice en la deflexión de tickets (`docs/13`, EVO-01).
- **Entran** los pendientes pequeños (adjuntos al crear un ticket, liberar un bloqueo de edición y el interruptor del SLA). **Se difieren** las excepciones de SLA (RF-083), los tickets «sin actividad reciente» y los avisos de sobrecarga, que necesitan reglas por decidir, y la retención (RF-110 y RF-123), que irá con los backups en `v0.8.0`.

### Cierre de la fase (entrega 10)

Se revisó toda la fase: se midió a escala, se recorrieron las pantallas en busca de errores, se compararon los requisitos con el código y se corrigió lo que apareció. La entrega 9 ya había dejado el código ordenado, sin cambios de comportamiento.

- **La matriz de trazabilidad destapó un requisito sin hacer:** la ubicación obligatoria al crear un ticket (RF-019 y RF-116), que `docs/11` daba por «más adelante» y nadie había retomado. Ahora es un interruptor de la pantalla «Creación de tickets» (que reúne también la advertencia de duplicados), solo se exige mientras haya ubicaciones activas y no es retroactivo (RN-177).
- **Cuatro errores que ningún test veía:** el tamaño máximo de un archivo se mostraba como «0 MB» por debajo de 1 MB (y 1,5 MB como «2 MB»), porque había tres formas distintas de escribirlo; `sla-status` decía «la prioridad no tiene una política activa» con el SLA apagado; `sla-status` y el aviso de transiciones de `seed-demo-tickets` fallaban al redirigir su salida en Windows por un carácter (`→`) que la consola no sabe escribir; y en el detalle de un grupo los dos selectores compartían el mismo `id`, así que la etiqueta del segundo nombraba al primero.
- **Un hueco de diseño:** el editor de artículos no mostraba el estado editorial que pide UI-011.
- **Escala (RNF-001).** Con unos 20 000 tickets, 67 000 eventos, 5000 artículos y 24 000 avisos en una base de pruebas: el aviso de duplicados al crear un ticket tarda unos 410 ms para el personal (90 ms para un Solicitante, que ve menos tickets), el dashboard del personal 350 ms, la reasignación 275 ms, la carga de trabajo 270 ms, el listado entre 30 y 205 ms según el filtro, y la base de conocimiento (portada, búsqueda, detalle y gestión) menos de 20 ms. El número de consultas no crece con los datos. Se probó calcular el estado del SLA con una sola subconsulta por ticket y no mejoró, así que se dejó como estaba.
- **Recorrido automático de 162 pantallas** con los cuatro roles sobre esos datos: ningún error del servidor y un solo problema de accesibilidad (el de Grupos).
- **Protecciones nuevas:** que todo texto que escriben los comandos pueda salir por la consola de Windows y las pruebas de cada corrección. Como en cada entrega, se comprobaron con mutaciones.

#### Matriz de trazabilidad

| Requisito | Estado | Dónde | Pruebas |
| --- | --- | --- | --- |
| RF-019 / RF-116 ubicación obligatoria · RN-177 | Hecho en el cierre | `LOCATION_REQUIRED`, «Creación de tickets», `tickets/service.py` (`location_required`) | `test_phase7_closing` |
| RF-053 validación y cierre automático | Hecho: activación, plazo y avisos; la unidad es fija (horas corridas) y no hay «condiciones de aplicación» | «Cierre y reapertura», `scheduler.py` | `test_settings_screens`, `test_scheduler` |
| RF-061 posibles duplicados · RN-175 | Hecho | `tickets/similar.py`, «Creación de tickets» | `test_duplicate_warning` |
| RF-087 y RF-121 configuración de notificaciones · RN-97, RN-172 | Hecho como catálogo que se apaga y enciende | `notifications/preferences.py`, `/admin/notifications` | `test_notification_settings` |
| RF-102 gestión de artículos · RN-173 | Hecho; se desactivan, no se borran | `knowledge/service.py`, `/knowledge/...` | `test_knowledge_model`, `test_knowledge_screens` |
| RF-103 artículos públicos y privados | Hecho; la visibilidad se decide en la consulta | `knowledge/queries.py` | `test_knowledge_model` |
| RF-104 vínculo con tickets · RN-174 | Hecho | `tickets/knowledge_links.py` | `test_ticket_knowledge` |
| RF-105 solución convertida en conocimiento | Hecho (borrador desde la resolución) | `/knowledge/new?ticket=<n>` | `test_ticket_knowledge` |
| RF-113 área de configuración | Hecho | hub de administración y `/admin/settings/<grupo>` | `test_layout`, `test_settings_screens` |
| RF-114, RF-115 y RF-117 categorías, prioridades y grupos | Hecho en fases anteriores; nivel y color de las prioridades, fijos por diseño | `/admin/...`, `/groups` | `test_catalogs*`, `test_groups` |
| RF-118 estados y transiciones | Hecho, salvo color y orden de los estados (`v0.9.0`) | `/admin/states` | `test_states_admin` |
| RF-119 configuración de SLA · RN-165 | Hecho, con el interruptor general | `/admin/sla` | `test_sla_switch` |
| RF-120 cierre y reapertura | Hecho | «Cierre y reapertura» | `test_settings_screens` |
| RF-122 archivos | Hecho: tamaño y cantidad; los tipos permitidos son fijos por seguridad | «Archivos» | `test_settings_screens`, `test_ticket_create_uploads` |
| RF-126 configuración inicial | Hecho | `seed-catalogs`, valores por defecto de `settings.py` | `test_migrations` |
| RF-110 y RF-123 retención | **Fuera de la fase** (`v0.8.0`, con los backups) | — | — |
| RF-083 excepciones de SLA | **Fuera de la fase** (sin fase asignada) | — | — |

**Queda fuera de la fase,** con su destino: la retención (RF-110 y RF-123), con los backups de `v0.8.0`; las excepciones de SLA (RF-083), los tickets «sin actividad reciente» (RF-036, RN-27) y los avisos internos de sobrecarga (RN-28), que necesitan reglas que todavía no se han decidido y quedan sin fase asignada; y el color y el orden de los estados, con el pulido visual de `v0.9.0`.

## 20.1. Administración

Implementar CRUD/configuración necesaria para:

- usuarios;
- grupos;
- categorías;
- prioridades;
- ubicaciones;
- SLA;
- archivos;
- cierre/reapertura;
- notificaciones internas.

Las configuraciones más avanzadas podrán incorporarse progresivamente.

En esta fase se crea la tabla `configuracion`; los valores de sesión y autenticación que hasta entonces se leen de variables de entorno pasan a ser sus valores iniciales.

## 20.2. Base de conocimiento

Implementar:

- categorías;
- artículos;
- búsqueda;
- destacados;
- recientes;
- detalle;
- borrador/publicado cuando corresponda;
- creación/edición según permiso;
- publicación según permiso;
- advertencia de posibles tickets duplicados al crear uno (RF-061): sin bloquear la creación, muestra tickets abiertos parecidos (título y categoría, reciente) con búsqueda por palabras (`ILIKE`), la misma que usará la base de conocimiento. La sensibilidad se configura con la tabla `configuracion`.

### Criterio de salida

El Solicitante puede:

```text
buscar solución
→ leer artículo
→ si no resuelve
→ crear ticket
```

---

# 21. FASE 8 — Reportes, auditoría y backups

**Segunda mitad de semana 9 y semana 10**  
**Versión:** `v0.8.0`

**Estado de ejecución:** en curso. Doce entregas planificadas.

### Entregas de `v0.8.0`

1. **Revisión previa** ✓: auditoría de lo construido y refuerzo de seguridad. El bloqueo por intentos fallidos ya no se puede saltar con intentos en paralelo (la fila del usuario se bloquea). La forma de la identidad tiene una sola definición, que también aplica `create-admin`, ahora auditado. `sla-rebuild` deja rastro. El logout vacía la sesión. Hay un log por proceso (la rotación fallaba en Windows), arranque seguro en producción (clave larga y sin modo depuración), una cookie de sesión que no delata el framework, páginas de error para cualquier código y cuatro cabeceras más. Guardianes nuevos: claves foráneas sin cascada y tablas de eventos de solo añadir. Sin migraciones.
2. **Velocidad de la suite** ✓, sin cambios de comportamiento: conexiones reutilizadas entre tests, Argon2id barato solo en los tests (con sus parámetros de producción ahora explícitos y vigilados), el seed buscando sus tickets en una consulta y las pruebas monolíticas repartidas. De 6 min 54 s a 4 min 12 s (−39 %). La instantánea de los catálogos se midió y se descartó: unos 7 s a cambio de una restauración frágil.
3. **Eventos de autenticación** ✓ (`eventos_autenticacion`, docs/09 9.3; RN-178): inicio de sesión correcto y fallido (con su causa interna, nunca mostrada), bloqueo, cierre y expiración de la sesión y contraseña actual equivocada. Con ellos, un **límite de intentos fallidos por equipo** (`LOGIN_MAX_FAILED_PER_IP`) que frena a quien prueba pocas contraseñas en muchas cuentas, y la actividad de acceso de cada cuenta en «Mi cuenta». Migración `create_auth_events_table`.
4. **Pantalla de auditoría** ✓ (UI-027, RF-108, RF-109): tres pestañas (administrativa, accesos y tickets), con filtros validados, solo para el Administrador. Medida con unas 250 000 filas por registro, por debajo de 220 ms, sin índices nuevos.
5. **Reportes: consultas** ✓ (RF-098, UI-012, RN-179): cifras comparadas con el período anterior, desgloses por estado, categoría y prioridad, tiempo de resolución por semana (media y mediana, tiempo corrido) y resumen por técnico. Cada cifra se cuenta con las mismas condiciones del listado, y su enlace se lee de vuelta como los mismos filtros. El listado ganó el filtro por fecha de resolución. Medido con unos 20 000 tickets: un año en 310 ms, sin índices nuevos.
6. **Reportes: pantalla** (UI-012): gráficos dibujados en el servidor (CSS y SVG, sin librerías) con su tabla equivalente y sin rankings.
7. **Exportación CSV y XLSX** (RF-099 a RF-101) del listado, los reportes y la auditoría, con los mismos filtros y permisos que la pantalla y las fórmulas neutralizadas.
8. **Respaldos** (RF-127, RNF-038 a RNF-040): comandos `backup-create`, `backup-verify` y `backup-list`. Generan un `.zip` con `pg_dump`, los adjuntos y un manifiesto con hashes SHA-256.
9. **Restauración y estado del sistema** (RF-128, RF-130, UI-028, UI-029): `backup-restore` con todas sus comprobaciones y las pantallas de respaldos (solo lectura) y de estado del sistema.
10. **Retención** (RF-110 a RF-112, RF-123): políticas desactivadas por defecto y ejecutadas por el planificador.
11. **Tickets «sin actividad reciente»** (RN-27).
12. **Cierre de la fase:** revisión completa, escala con ~20 000 tickets, matriz de trazabilidad y etiqueta.

### Decisiones de la fase

Se tomaron al planificarla:

- **XLSX con `openpyxl`,** como preveía `docs/10` (sección 95), en modo de solo escritura. El CSV va en UTF-8 con BOM, separado por comas. En los dos se neutralizan las celdas que empiezan como una fórmula (`=`, `+`, `-`, `@`), para que abrir una exportación no ejecute nada.
- **Los reportes son del personal.** El Supervisor y el Administrador los ven completos. El Técnico ve la misma pantalla, pero en el resumen por técnico solo su propia fila: UI-012 pide no comparar personas. El Solicitante no tiene acceso.
- **Tiempo de resolución:** tiempo corrido desde la creación hasta la resolución, con media y mediana calculadas en SQL. La mirada en tiempo laboral ya la da el cumplimiento del SLA.
- **Eventos de autenticación:** se registran el inicio de sesión correcto y el fallido, el bloqueo, el cierre y la expiración de la sesión. El cambio de contraseña sigue en la auditoría, sin duplicarlo. El texto escrito como usuario solo se guarda si tiene forma de username (alguien pudo escribir ahí su contraseña). La retención sugerida es de 365 días, desactivada hasta que el Administrador la active (RN-106).
- **Los respaldos se crean y se restauran solo por comandos.** La web los consulta pero no los ejecuta. No hay tabla `historial_backups`: la carpeta de respaldos con sus manifiestos es la fuente de verdad, y la auditoría registra cada creación y restauración. Con la tabla, el propio volcado contendría su fila «en progreso» y al restaurarlo quedaría así para siempre. Se aparta de `docs/09` (29.1).
- **No hace falta un modo de mantenimiento para respaldar.** `pg_dump` saca una foto consistente de la base, y los adjuntos confirmados nunca se borran del disco: si se copian después del volcado, están todos los que la base referencia.
- **La retención se guarda en `configuracion`,** como los demás parámetros, sin la tabla `politicas_retencion`. Se aplica a las notificaciones leídas, los eventos de autenticación, los archivos de adjuntos ya eliminados y el número de respaldos que se conservan. Los tickets, el historial y la auditoría quedan en «Mantener» fijo durante el MVP (RN-110 y RN-141), y «Archivar» pasa a después del MVP. Se aparta de `docs/09` (27.1).
- **Las excepciones de SLA (RF-083) pasan a después del MVP.** Las acciones manuales sobre el SLA ya quedan registradas: el cambio de prioridad con su motivo, el interruptor, las políticas y `sla-rebuild`. Y el Supervisor puede pausar el reloj poniendo el ticket «En espera». Una pausa manual aparte tocaría el motor de períodos, la reconstrucción desde el historial y la equivalencia entre SQL y Python.
- **Los avisos de sobrecarga (RN-28)** se dan por cubiertos con la marca «Carga alta» de los dashboards y de la carga de trabajo (la regla dice «podrá informar»). Las notificaciones de sobrecarga pasan a después del MVP.

## 21.1. Reportes

Implementar:

- KPIs;
- estado;
- categoría;
- prioridad;
- tiempo de resolución;
- resumen por técnico;
- filtros.

Evitar un diseñador dinámico de reportes.

## 21.2. Auditoría

La tabla `auditoria_administrativa` ya existe desde `v0.2.0` y registra las acciones sobre usuarios. En esta fase se incorpora la pantalla de consulta, `eventos_autenticacion` y el registro del resto de acciones. Registrar y consultar como mínimo:

- cambios de estado;
- asignaciones;
- prioridad;
- notas/comentarios cuando corresponda;
- cambios administrativos relevantes.

## 21.3. Backups

Implementar scripts operativos para:

```text
PostgreSQL
+
uploads
+
manifest
```

La UI completa de restauración no es requisito prioritario de esta fase.

### Criterio de salida

```text
✓ métricas reales
✓ reportes responden a filtros
✓ auditoría consultable
✓ backup generado correctamente
✓ procedimiento de restauración documentado/probado
```

---

# 22. FASE 9 — Calidad visual, responsive y accesibilidad

**Semana:** 11  
**Versión:** `v0.9.0`

Aunque el Design System debe aplicarse durante todo el proyecto, esta fase realizará la revisión global.

### Revisar

- consistencia con mockups;
- sidebar;
- topbar;
- cards;
- tablas;
- formularios;
- badges;
- estados;
- mensajes;
- responsive;
- mobile;
- focus;
- teclado;
- contraste;
- estados vacíos;
- loading;
- errores;
- feedback;
- toasts.

### Preparación para el tema oscuro

El tema oscuro se desarrolla después del MVP (sección 32), pero esta fase deja el terreno listo sin cambiar el aspecto del tema claro:

- inventario de los colores escritos directamente en CSS y plantillas (hoy, alrededor de 80 valores hexadecimales en `theme.css`, `layout.css`, `auth.css` y `errors.css`);
- conversión de esos valores a tokens `--wd-*` y mapeo de las variables de Bootstrap a tokens, no a hexadecimales;
- ampliación del catálogo de tokens: superficies, bordes, estados, insignias de estado y prioridad, sidebar y topbar;
- decisión sobre los colores que hoy se guardan en la base de datos (estados y prioridades);
- comprobación de que el tema claro se ve exactamente igual (capturas antes y después).

Desde ahora, toda pantalla nueva usa tokens (`docs/11`, sección 41.1).

### Criterio de salida

Las pantallas principales se ven y comportan de forma consistente con `11_diseno_de_pantallas.md`.

---

# 23. FASE 10 — Estabilización y release del MVP

**Semana:** 12  
**Versión:** `v1.0.0`

Esta fase no debe utilizarse para agregar grandes funcionalidades nuevas.

### Actividades

- corregir bugs;
- ampliar pruebas;
- revisar permisos;
- revisar seguridad;
- revisar migraciones;
- limpiar código;
- ejecutar Ruff;
- ejecutar pytest;
- revisar logs;
- generar datos demo;
- revisar README;
- agregar capturas;
- documentar instalación;
- documentar ejecución;
- realizar prueba desde instalación limpia;
- preparar release `v1.0.0`.

### Criterio de salida

Una persona que clone el repositorio debe poder:

```text
seguir README
→ instalar
→ configurar PostgreSQL
→ aplicar migraciones
→ cargar datos demo
→ iniciar WorkDesk
→ utilizar el flujo principal
```

sin depender de conocimiento privado del autor.

---

# 24. Orden de prioridad si el calendario se retrasa

Si el proyecto se acerca al límite de tres meses, no se debe reducir calidad del núcleo del ticket para conservar funcionalidades secundarias.

Orden de prioridad:

```text
1. Autenticación y RBAC
2. Tickets
3. Ciclo de vida
4. Asignación
5. Comentarios / notas
6. Adjuntos
7. SLA
8. Notificaciones internas
9. Dashboards
10. Administración esencial
11. Carga de trabajo
12. Base de conocimiento
13. Reportes
14. Auditoría
15. UI avanzada de backup
```

Base de conocimiento, SLA y Reportes forman parte del MVP deseado, por lo que antes de eliminarlos se debe intentar reducir su profundidad y conservar una versión funcional básica.

---

# 25. Alcance mínimo aceptable de módulos grandes

## 25.1. Base de conocimiento mínima

```text
categorías
+
listado
+
búsqueda
+
artículo
+
publicación
```

## 25.2. Reportes mínimos

```text
KPIs
+
estado
+
categoría
+
prioridad
+
tiempo de resolución
+
resumen por técnico
```

## 25.3. SLA mínimo

```text
prioridad
+
resolución
+
primera respuesta opcional
+
aviso
+
pausa
+
calendario
```

---

# 26. Gestión de deuda técnica

Durante el desarrollo aparecerán mejoras que no deben interrumpir continuamente el roadmap.

Crear issues con etiquetas como:

```text
technical-debt
enhancement
post-mvp
```

Una mejora no urgente se registra; no se implementa inmediatamente si desvía la fase actual.

---

# 27. Uso de GitHub Issues

Se recomienda utilizar GitHub Issues desde el comienzo.

Ejemplos:

```text
[AUTH] Implementar login
[TICKET] Crear formulario de alta
[TICKET] Implementar filtros
[SLA] Calcular vencimiento
[KB] Crear búsqueda
[REPORT] Tickets por estado
```

Etiquetas recomendadas:

```text
feature
bug
documentation
test
refactor
technical-debt
post-mvp
```

---

# 28. Organización semanal recomendada

Con 3–4 horas diarias puede utilizarse una rutina aproximada:

```text
Primer bloque
30–45 min
→ comprender tarea / revisar documentación

Segundo bloque
1.5–2 h
→ implementación

Tercer bloque
45–60 min
→ pruebas / debugging / refactor

Cierre
15 min
→ commit / notas / siguiente tarea
```

---


# 29. Riesgos principales

## 29.1. Alcance excesivo

**Riesgo:** intentar implementar todos los detalles diseñados con la misma profundidad.

**Mitigación:** utilizar alcance mínimo por módulo y mover mejoras a post-MVP.

## 29.2. Curva de aprendizaje

**Riesgo:** detener el proyecto por intentar dominar completamente una tecnología antes de utilizarla.

**Mitigación:** aprender lo necesario para cada fase y profundizar progresivamente.

## 29.3. Acumulación de código poco comprendido

**Riesgo:** avanzar demasiado rápido y acumular código que funciona, pero que luego resulta difícil de mantener o explicar.

**Mitigación:** revisar cada módulo, documentar decisiones importantes, refactorizar progresivamente y mantener una estructura clara y consistente.


## 29.4. Postergar pruebas

**Riesgo:** descubrir regresiones graves cerca de `v1.0`.

**Mitigación:** tests mínimos de reglas críticas desde cada fase y ampliación en estabilización.

## 29.5. Perfeccionismo visual temprano

**Riesgo:** dedicar demasiado tiempo a ajustar CSS antes de cerrar funcionalidad.

**Mitigación:** respetar el Design System desde el comienzo, pero reservar pulido final para `v0.9.0`.

## 29.6. Falta de tiempo al conseguir empleo

**Riesgo:** reducirse significativamente la disponibilidad durante el proyecto.

**Mitigación:** roadmap basado en hitos, commits pequeños y versiones utilizables.

---

# 30. Definición de MVP terminado

WorkDesk se considerará MVP `v1.0.0` cuando pueda demostrarse de principio a fin:

```text
Usuario inicia sesión
↓
Solicitante crea ticket
↓
ticket se clasifica
↓
soporte lo visualiza
↓
se asignan técnicos
↓
se trabaja mediante comentarios/notas
↓
SLA se calcula
↓
ticket cambia de estado
↓
técnico resuelve
↓
solicitante valida
↓
ticket se cierra
↓
historial queda registrado
↓
dashboard y reportes reflejan los datos
```

Además:

```text
✓ permisos funcionan
✓ notas internas permanecen privadas
✓ adjuntos funcionan
✓ notificaciones internas funcionan
✓ Base de conocimiento funciona
✓ administración esencial funciona
✓ backup operativo existe
✓ responsive está revisado
✓ pruebas críticas pasan
✓ README permite ejecutar el proyecto
✓ repositorio Git está limpio
✓ release v1.0.0 creada
```

---

# 31. Presentación para portafolio

La versión `v1.0.0` debe ser presentable visual y técnicamente.

El repositorio deberá incluir como mínimo:

- descripción clara;
- objetivos;
- stack;
- arquitectura resumida;
- instrucciones de instalación;
- capturas;
- funcionalidades;
- roles;
- estructura del proyecto;
- estado del proyecto;
- tecnologías utilizadas;
- roadmap posterior;
- documentación técnica relevante.

Los mockups son referencia de diseño; las capturas finales del README deben mostrar la aplicación real implementada.

---

# 32. Qué ocurre después del MVP

Ejemplo de evolución:

```text
v1.1
Mejoras de UX y reportes

v1.2
Configuraciones administrativas avanzadas

v1.3
Dark mode

v1.4
Automatizaciones

v2.0
Evolución hacia gestión de trabajo/proyectos
```

La numeración exacta se definirá cuando exista una necesidad real.

El detalle de las mejoras previstas después del MVP (autoservicio y calidad de atención, automatización operativa, flujos ITSM, activos tecnológicos y gestión de proyectos y tareas), con su evaluación, dependencias y orden por olas, está en [`13_evolucion_post_mvp.md`](13_evolucion_post_mvp.md). Se suman a las evaluaciones de tiempo real y modo oscuro de esta sección.

La evolución «hacia gestión de trabajo/proyectos» (v2.0 en la lista anterior) es la ola 5 de ese documento: un módulo secundario, solo para el personal, que no cambia el núcleo de tickets.

### Tiempo real: evaluación posterior al MVP

El MVP no utiliza WebSockets (RNF-095 y ARQ-022): las notificaciones se actualizan por polling cada 30 segundos y al navegar entre páginas. Después de `v1.0.0` conviene evaluar si hace falta empujar eventos al navegador (comentarios, cambios de estado, avisos) y con qué mecanismo:

- **Server-Sent Events (SSE):** comunicación en un solo sentido (servidor → navegador) sobre HTTP normal. Cubre el caso real, que es avisar de eventos, y es la opción a evaluar primero.
- **WebSockets:** comunicación bidireccional. Solo se justificaría si aparecen necesidades que SSE no cubre, como un chat.

Lo que cualquiera de las dos exigiría, y por eso se pospone:

- **Un servidor con soporte para conexiones largas.** Waitress, el servidor previsto (ARQ-028), ejecuta cada petición en un hilo de un grupo reducido (4 por defecto), de modo que unas pocas conexiones abiertas lo agotarían.
- **Un canal entre procesos.** El scheduler (`run-scheduler`) corre en un proceso separado del web (`docs/10`, sección 85): para que un evento generado por él llegue a las conexiones abiertas haría falta un intermediario. Redis está excluido del MVP; `LISTEN/NOTIFY` de PostgreSQL es una alternativa a evaluar que no añade tecnologías.
- **Autorización por evento.** Autenticar la conexión no basta: cada evento debe comprobarse contra su destinatario (una nota interna nunca debe llegar a un Solicitante).
- **Cortar la conexión cuando cambia el contexto de seguridad**, por ejemplo al cambiar el rol o desactivar a la persona (`token_version`).

Los eventos de ticket ya pasan por un único punto, `record_ticket_event`, que sería el lugar natural desde el cual publicarlos.

Adoptar cualquiera de las dos cambia una decisión arquitectónica vigente, así que exige la propuesta formal habitual: limitación concreta, por qué la solución actual no basta, alternativa, impacto y documentación a actualizar.

### Modo oscuro (posterior al MVP)

El modo oscuro ya figura como evolución (v1.3 en la lista anterior) y el Design System está pensado para él (`docs/11`, secciones 9.1 y 41). Se desarrolla después de `v1.0.0`, sobre la preparación hecha en `v0.9.0` (tokens en lugar de colores fijos). Alcance:

- **Paleta:** valores oscuros de los tokens derivados del tema claro actual (azul `#1D4ED8`, fondo `#F1F5F9`, superficies `#FCFCFD`, texto, bordes y colores semánticos), conservando la jerarquía y el significado de cada color (rojo = destructivo, ámbar = advertencia...), sin negro puro en grandes superficies y con contraste AA.
- **Mecanismo:** `data-bs-theme="dark"` de Bootstrap 5.3 con los tokens redefinidos para ese tema; respeto de la preferencia del sistema (`prefers-color-scheme`) y elección manual del usuario guardada en el navegador (`localStorage`), aplicada antes de pintar para evitar el parpadeo.
- **Marca:** cambio dinámico a las variantes inversas del logotipo y del Login, que ya existen.
- **Colores guardados en la base de datos** (estados y prioridades): decidir si se deriva una variante oscura automáticamente o se guarda un segundo color.
- **Pantallas con color propio:** Login, cambio de contraseña, errores, gráficos de los dashboards e insignias de SLA.
- **Verificación:** recorrido de todas las pantallas en ambos temas y pruebas de contraste.

Mientras tanto, la regla para el desarrollo de interfaz es usar siempre tokens (`docs/11`, sección 41.1).

---

# 33. Próximo paso inmediato

`v0.1.0` a `v0.7.0` están integradas en `main` y etiquetadas:

```text
main
→ v0.1.0 integrado (PR #1) y etiquetado
→ documentación de contexto (PR #2) e identidad visual (PR #3)
→ v0.2.0 integrado (PR #4 a #13) y etiquetado
→ v0.3.0 integrado (PR #14 a #20) y etiquetado
→ v0.4.0 integrado (PR #23 a #35) y etiquetado
→ v0.5.0 integrado (PR #36 a #45) y etiquetado
→ v0.6.0 integrado (PR #46 a #55) y etiquetado
→ v0.7.0 integrado (PR #56 a #65) y etiquetado
```

El siguiente paso es `v0.8.0 — Reportes, auditoría y backups` (fase 8, sección 21). Antes de escribir código conviene:

```text
1. empezar, como en las dos fases anteriores, por una revisión de lo
   construido (medir antes de cambiar);
2. decidir lo que v0.7.0 dejó sin regla: la retención (RF-110 y RF-123),
   que va con los backups, y si los reportes absorben los tickets «sin
   actividad reciente» (RF-036, RN-27);
3. dividir la fase en entregas pequeñas, cada una con su rama, tests y
   Pull Request.
```

`v0.8.0` reutiliza lo que ya está validado: la auditoría administrativa (append-only, desde `v0.2.0`), las consultas con la visibilidad resuelta en SQL, la configuración administrable (`configuration.py`) y la prueba de pantallas con presupuesto de consultas.

---

# 34. Cierre

Este roadmap busca equilibrar:

```text
aprender
+
construir
+
terminar
```

WorkDesk debe crecer mediante incrementos funcionales, comprensibles y versionables.

El objetivo no es programar todas las posibilidades imaginables desde el comienzo, sino llegar a un MVP sólido que demuestre:

- arquitectura;
- backend;
- frontend;
- base de datos;
- seguridad;
- reglas de negocio;
- UX;
- testing;
- Git;
- documentación;
- capacidad para llevar un proyecto de software desde la idea hasta una primera versión funcional.
