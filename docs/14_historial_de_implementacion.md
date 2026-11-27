# 14. HISTORIAL DE IMPLEMENTACIÓN

Este documento guarda el **relato por versión y por entrega** de cómo se construyó WorkDesk: qué se decidió en cada fase, qué errores reales se encontraron y se corrigieron, qué cubre cada prueba y cuántos tests tenía el proyecto al cerrar cada entrega.

No describe el estado actual del proyecto. Para eso están `PROJECT_CONTEXT.md` (qué existe hoy y cómo funciona), `docs/12_roadmap.md` (qué planificó y entregó cada fase) y el resto de la documentación funcional y técnica.

El texto se conserva tal como se escribió al cerrar cada entrega: las cifras y los nombres de módulos son los de ese momento.

---

# 1. Versiones

## Hito completado: v0.1.0 y v0.2.0

## Hito completado: v0.2.0

Durante `v0.1.0` se adelantó intencionalmente parte de la base técnica de autenticación para consolidar desde el comienzo:

- sesiones;
- seguridad;
- protección de rutas;
- bloqueo de intentos;
- invalidación de sesiones;
- testing automatizado.

La fase `v0.2.0` completó:

- gestión de usuarios (listado, creación, detalle, edición, cambio de rol, desactivación y reactivación, y restablecimiento de contraseña) — implementada;
- autorización basada en roles;
- políticas de acceso;
- navegación según rol;
- restricciones administrativas;
- cuenta propia ("Mi cuenta") — implementada;
- datos demo (comando `seed-demo`) — implementados;
- pruebas específicas de autorización;
- límites de sesión (30 minutos de inactividad y 8 horas máximo, por variables de entorno) — implementado;
- contraseñas: creación de cuentas y restablecimiento por el Administrador con contraseña temporal, cambio propio y cambio obligatorio en el primer inicio de sesión (`usuarios.debe_cambiar_password`) — implementados la política, el generador, la columna, las operaciones de dominio, la pantalla de cambio propio y la guardia de cambio obligatorio; el Administrador crea usuarios con contraseña temporal y restablece contraseñas desde la interfaz;
- tabla `auditoria_administrativa` mínima para las acciones sobre usuarios — implementada (modelo, migración y servicio), y todas las acciones sobre usuarios ya registran su evento.

`docs/12_roadmap.md` documenta las cinco entregas incrementales de `v0.2.0`, cada una con su rama y Pull Request.

## Implementado hasta `v0.2.0`

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
- administración de usuarios existentes: detalle, edición de datos, cambio de rol, desactivación y reactivación, y restablecimiento de contraseña, con salvaguardas (nadie actúa sobre sí mismo, siempre queda un Administrador activo) y auditoría;
- Bootstrap y Bootstrap Icons locales, app shell (sidebar, topbar, avatar), navegación por rol filtrada en backend y hub de administración;
- "Mi cuenta" (`/account`): datos propios, edición de la información de contacto y acceso al cambio de contraseña;
- comando `seed-demo`: equipo de soporte ficticio, sin Administrador.

## Implementado en `v0.3.0`

- catálogos de tickets (estados, prioridades, categorías, ubicaciones y motivos de cierre) y el comando `seed-catalogs`;
- modelo de tickets (`tickets`, `tickets_solicitantes` e `historial_ticket` inmutable) con identificador público generado por una secuencia de PostgreSQL;
- administración de categorías, prioridades y ubicaciones por el Administrador, con auditoría;
- creación de tickets para los cuatro roles, con solicitantes elegidos por el personal;
- detalle de ticket con historial, visible solo para quien corresponde (404 para lo ajeno);
- listado "Tickets" / "Mis tickets" con pestañas, búsqueda, filtros, orden y paginación, con la visibilidad aplicada en la propia consulta;
- edición de título, descripción, categoría y ubicación, y cambio de prioridad con motivo obligatorio, con control de versión para las ediciones simultáneas;
- políticas de autorización de tickets: `can_create_ticket`, `can_choose_requesters`, `can_view_ticket`, `can_edit_ticket` y `can_change_priority`;
- red de seguridad automática sobre todas las rutas (autenticación y CSRF);
- guía de primera configuración, recorrido de prueba y solución de problemas en el README.

## Añadido después de `v0.3.0`

- comando opcional `seed-demo-tickets`: unos 40 tickets de demostración realistas, con fechas relativas, historial de ajustes del personal y datos separados de la lógica (ver "22. CLI"); creció con cada entrega de `v0.4.0` hasta los 76 tickets actuales.

## Implementado en `v0.4.0`

- historial con el vocabulario de eventos solo en la aplicación, visibilidad (pública o interna) por evento filtrada en la consulta y un descriptor por evento;
- catálogo y administración de motivos de espera;
- estados y transiciones: la tabla `transiciones_estados`, los cambios de estado operativos y el motor `change_state` con control de versión y bloqueo de la fila;
- grupos, con membresías y supervisores responsables (`/groups`);
- asignación de técnicos, grupo del ticket y escalamiento manual, con el estado derivado (`Nuevo` ↔ `Asignado`);
- agregar y retirar solicitantes tras crear el ticket;
- comentarios públicos y notas internas, con edición y eliminación con plazo;
- archivos adjuntos: almacenamiento local, validación por extensión y contenido, y descarga autenticada;
- resolución, validación del solicitante, cierre directo y excepcional y reapertura, con la regla «un ticket cerrado tiene fecha y motivo de cierre»;
- relaciones entre tickets y duplicados;
- bloqueo temporal de edición;
- administración de estados y transiciones (nombre visible, descripción y transiciones opcionales, con protecciones para no romper el flujo);
- políticas de autorización por acción (`can_change_state`, `can_assign_self`, `can_manage_assignments`, `can_manage_requesters`, `can_write_internal_note`, `can_resolve_ticket`, `can_close_directly`, `can_close_exceptionally`, `can_validate_resolution`, `can_reopen_ticket`, `can_manage_relations`, `can_access_groups`...) y su red de seguridad sobre todas las rutas;
- migraciones: diez nuevas (de 7 a 17) y 23 eventos del historial.

## Implementado en `v0.5.0`

- motor de tiempo laboral compartido y calendario laboral administrable (versionado), con su pantalla en «SLA»;
- políticas de SLA por prioridad (objetivo de resolución, primera respuesta opcional, porcentaje de aviso y pausa en espera);
- períodos de SLA: pausa en `En espera`, detención al resolver, continuidad ante cambios de prioridad y reconstrucción desde el historial (`sla-rebuild`, `sla-status`);
- indicadores de SLA solo para el personal: insignias, filtro, orden «SLA más urgente», tarjeta del detalle y advertencia al bajar la prioridad con el SLA en riesgo;
- notificaciones internas: centro de notificaciones, campana con contador y avisos por los eventos de un ticket;
- planificador (`run-scheduler`): avisos de SLA próximo a vencer y vencido, una sola vez, con el incumplimiento registrado en el historial (`SLA_VENCIDO`), y cierre automático de los tickets resueltos que nadie valida;
- migraciones: seis nuevas (de 17 a 23) y 24 eventos del historial;
- la suite pasó de 2201 a 3965 tests, con pruebas de pantallas con datos reales, de migraciones y de una instalación limpia, de las reglas RN-85 a RN-87, de la sesión de la campana y de coherencia con los documentos (variables de entorno, comandos, migraciones y rutas).

## Implementado en `v0.6.0`

- un dashboard por rol: el del Solicitante (abiertos, en progreso, solicitudes por revisar, cerrados recientes y sus notificaciones) y el operacional del personal (contadores, tickets prioritarios, carga compacta, tickets por prioridad y actividad reciente), con «Mi trabajo» para el Técnico y un bloque de Administración;
- la carga de trabajo del equipo (`/workload`): por técnico (con distribución por prioridad), por grupo y sin asignar, con insignia de carga alta informativa;
- la reasignación masiva de tickets (`/reassign`): elegir, revisar y confirmar, con el rastro completo en el historial y la auditoría;
- los filtros del listado por técnico, grupo, «sin asignar», «en trabajo», «por revisar» y «cerrados desde», y `sla=riesgo`, que son el destino de los contadores;
- una forma única de error JSON y cabeceras de seguridad en todas las respuestas, el seed de tickets convertido en paquete y una migración (un índice del historial);
- la suite pasó de 3965 a 4175 tests y los tickets de demostración de 76 a 108.

---

## Implementado en `v0.7.0`

- la configuración administrable: 16 parámetros y 3 interruptores en la tabla `configuracion`, con cinco pantallas por tema, restablecer, auditoría y aviso de conflicto; las variables de entorno pasan a ser solo el valor inicial;
- el interruptor general del SLA y el del cierre automático, y la ubicación obligatoria al crear un ticket (RF-019);
- la configuración de los avisos internos: qué evento se avisa a quién, como un catálogo que se apaga y enciende;
- la base de conocimiento: artículos con borrador y publicación, público y privado, destacados, búsqueda en español sin depender de las tildes, vínculo con tickets y artículos nacidos de una resolución;
- la advertencia de posibles duplicados al crear un ticket, los adjuntos desde el formulario de creación y la liberación de un bloqueo de edición ajeno;
- tres migraciones (de 24 a 27) y la suite de 4175 a 4681 tests.

---

## En curso: `v0.8.0`

- la pantalla de auditoría (entrega 4): los tres registros en una pantalla con filtros, solo para el Administrador;
- los eventos de autenticación (entrega 3): cada intento de entrar y cada salida con su causa, el límite de intentos fallidos por equipo y la actividad de acceso en «Mi cuenta»; una migración (28);
- la velocidad de la suite (entrega 2): de 6 min 54 s a 4 min 12 s, sin cambios de comportamiento;
- la revisión previa (entrega 1): el bloqueo por intentos fallidos resistente a intentos en paralelo, una sola definición de la identidad de un usuario (también en `create-admin`, ahora auditado), un log por proceso, arranque seguro en producción, la cookie de sesión renombrada, páginas de error para cualquier código, cuatro cabeceras de seguridad más y dos guardianes del esquema; la suite pasa de 4681 a 4728 tests.

---

# 2. Hitos de v0.3.0 a v0.7.0

## Hito completado: v0.3.0

```text
v0.3.0 — Núcleo de tickets
```

Es la fase central del MVP: creación, listado, búsqueda, filtros, detalle y edición de tickets, con sus catálogos. Se dividió en entregas pequeñas, cada una con su rama, tests y Pull Request, como se hizo con `v0.2.0`. Reutiliza la infraestructura de `v0.2.0` (autorización por roles, auditoría, layout con Bootstrap, navegación por rol, formularios y patrones de servicio y listado).

| # | Entrega | Estado |
| --- | --- | --- |
| 1 | Catálogos: estados, prioridades, categorías, ubicaciones y motivos de cierre (modelos, migración y `seed-catalogs`) | Integrada (PR #14) |
| 2 | Modelo de tickets (tickets, solicitantes e historial) y servicio de creación | Integrada (PR #15) |
| 3 | Administración de catálogos desde la interfaz | Integrada (PR #16) |
| 4 | Creación de tickets | Integrada (PR #17) |
| 5 | Listado con búsqueda, filtros, orden y paginación | Integrada (PR #18) |
| 6 | Detalle y edición autorizada | Integrada (PR #19) |
| 7 | Cierre de la versión: red de seguridad de rutas, guía de primera configuración y documentación | Integrada (PR #20) |

Decisiones de la fase:

- **Sin datos de ejemplo en los seeds.** Categorías, ubicaciones y tickets de ejemplo se crean a mano desde la interfaz; ningún seed los incluye, para que una instalación real no arranque con datos ficticios. El README documenta cómo hacerlo.
- **Visibilidad del Solicitante:** ve los tickets que creó o donde es solicitante vigente. Técnico, Supervisor y Administrador ven todos. Un ticket al que no se tiene acceso responde 404, igual que uno inexistente.
- **Edición:** Técnico, Supervisor y Administrador editan título, descripción, categoría y ubicación y cambian la prioridad con motivo obligatorio; el Solicitante solo lee. El Solicitante ve en el historial qué cambió, pero no el motivo.
- **Concurrencia:** en esta fase solo existe el control de versión (`tickets.version`). El bloqueo temporal de edición (RN-115 a RN-117: aviso de quién edita, expiración y renovación) se difirió a `v0.4.0`, donde se implementó.
- **Estados y transiciones** (UI-021) se difirieron a `v0.4.0`, cuando existió el flujo de estados y la tabla de transiciones; están implementados.

Cierre de la versión (entrega 7), sin migraciones ni cambios de funcionalidad:

- `tests/test_route_protection.py` recorre el mapa de rutas real y comprueba que todas redirigen al login sin sesión, salvo las públicas (`auth.login`, `system.health` y `static`, listadas en `PUBLIC_ENDPOINTS`), y que toda ruta POST responde 400 sin token CSRF. Una ruta nueva queda cubierta automáticamente: si el test falla al añadirla, no se arregla el test; o se protege la ruta o, si de verdad es pública, se añade de forma consciente a `PUBLIC_ENDPOINTS`.
- El README incorpora la guía de primera configuración paso a paso (requisitos, PostgreSQL, `.env` y preparación inicial), un recorrido de prueba por rol con un fragmento opcional que genera 25 tickets de ejemplo desde `flask shell`, y una tabla de solución de problemas.

## Hito completado: v0.4.0

```text
v0.4.0 — Asignación, colaboración y ciclo de vida
```

Es la fase en que el ticket pasa a trabajarse en equipo: grupos, asignación, estados, comentarios y notas internas, adjuntos, resolución, cierre y reapertura, relaciones, bloqueo de edición y la administración de los estados. Se dividió en 12 entregas, cada una con su rama, tests, Pull Request y ampliación del seed de demostración:

| # | Entrega | Estado |
| --- | --- | --- |
| 1 | Historial: vocabulario en la aplicación y visibilidad por evento | Integrada (PR #23) |
| 2 | Catálogo de motivos de espera y su administración | Integrada (PR #24) |
| 3 | Estados y transiciones (`transiciones_estados`) y cambios de estado operativos | Integrada (PR #25) |
| 4 | Grupos (`/groups`), con membresías y supervisores responsables | Integrada (PR #26) |
| 5 | Asignación de técnicos, grupo del ticket y escalamiento manual | Integrada (PR #27) |
| 6 | Agregar y retirar solicitantes tras crear el ticket | Integrada (PR #28) |
| 7 | Comentarios públicos y notas internas | Integrada (PR #30) |
| 8 | Adjuntos | Integrada (PR #31) |
| 9 | Resolución, validación del solicitante, cierre y reapertura | Integrada (PR #32) |
| 10 | Relaciones y duplicados | Integrada (PR #33) |
| 11 | Bloqueo temporal de edición | Integrada (PR #34) |
| 12 | Pantalla de Estados y transiciones (UI-021) y cierre de la versión | Integrada (PR #35) |

Sus reglas están en `docs/06` (RN-146 y RN-156 a RN-164) y su alcance en `docs/12_roadmap.md` (fase 4, con las decisiones de la fase).

Decisiones de la fase:

- **El vocabulario de eventos del historial vive solo en la aplicación** (se eliminó el CHECK de `tipo_evento`). Un evento nuevo obliga a decidir su nombre, su visibilidad y su descriptor, y un test lo exige. Hoy son 24 (`SLA_VENCIDO` llegó en `v0.5.0`).
- **Quién ve qué se decide en la consulta**, nunca en la plantilla: lo mismo para el historial, los comentarios y los adjuntos. Cada condición SQL tiene su política Python equivalente y un test comprueba que coinciden para todos los roles.
- **Una acción, una pantalla** (sin modales, y funcionan sin JavaScript): 404 si no se ve el ticket y 403 si se ve y no se puede actuar.
- **`change_state` es el único camino que escribe el estado** y los datos de resolución y cierre, así que «cerrado ⇒ fecha y motivo de cierre» no puede romperse; marcar un duplicado y la asignación lo reutilizan.
- **Lo aditivo no sube la versión del ticket:** comentarios, notas, adjuntos, relaciones y cambios de solicitantes.
- **Los parámetros que serán configuración** (plazos de edición y de reapertura, límites de adjuntos y tiempos del bloqueo) son variables de entorno hasta `v0.7.0`.

## Hito completado: v0.5.0

```text
v0.5.0 — SLA y notificaciones internas
```

Es la fase en que WorkDesk empieza a **medir el tiempo y a avisar**: SLA por prioridad calculado en tiempo laboral con un calendario administrable, indicadores en la interfaz, notificaciones internas y un planificador que avisa de los vencimientos y cierra solo los tickets resueltos que nadie valida. Se dividió en 9 entregas, cada una con su rama, tests y Pull Request (y una optimización de la suite de tests, PR #42, entre la 6 y la 7):

| # | Entrega | Estado |
| --- | --- | --- |
| 1 | Motor de tiempo laboral compartido (`worktime.py`) | Integrada (PR #36) |
| 2 | Calendario laboral administrable | Integrada (PR #37) |
| 3 | Políticas de SLA por prioridad | Integrada (PR #38) |
| 4 | Períodos de SLA: pausa, continuidad y cambios de prioridad | Integrada (PR #39) |
| 5 | Notificaciones internas: infraestructura y centro de notificaciones | Integrada (PR #40) |
| 6 | Notificaciones internas: generación por eventos | Integrada (PR #41) |
| 7 | Indicadores de SLA en el listado y el detalle | Integrada (PR #43) |
| 8 | Planificador: avisos de SLA y cierre automático | Integrada (PR #44) |
| 9 | Cierre de la versión: revisión de toda la fase y documentación | Integrada (PR #45) |

Sus reglas están en `docs/06` (RN-165 a RN-170, más RN-58, RN-59, RN-88 y RN-91) y su alcance en `docs/12_roadmap.md` (fase 5, con las decisiones de la fase). Los detalles de cada pieza están en las secciones "Tiempo laboral", "Calendario laboral administrable", "Políticas de SLA", "Períodos de SLA", "Notificaciones internas", "Avisos por los eventos de un ticket", "Indicadores de SLA" y "Planificador".

Decisiones de la fase:

- **Un único motor de tiempo laboral** (`worktime.py`) para el SLA y el seed, y **un único lugar que decide el calendario vigente** (`resolve_work_calendar`). El calendario es global y versionado: una versión guardada nunca se modifica, así que lo ya calculado no cambia con retroactividad.
- **La pausa del SLA no usa columnas nuevas:** al entrar en `En espera` se cierra el período y, al reanudar, se abre otro que arrastra el consumo. **Un cambio de prioridad nunca reinicia el reloj ni borra un incumplimiento** (RN-88).
- **El SLA es solo del personal** (RN-169): el Solicitante no lo ve en pantallas, filtros ni avisos, y sus parámetros en la URL se ignoran.
- **Crear un ticket no avisa a nadie** (decisión de la fase) y **los avisos nunca copian contenido**: dicen qué pasó y en qué ticket. Un Solicitante solo recibe lo que vería en el historial.
- **El planificador es un comando propio** (`run-scheduler`), sin APScheduler ni dependencias nuevas, con tareas idempotentes. **Un aviso se envía una sola vez** (las marcas viven en el período) y cada elemento se procesa en su propia transacción, **bloqueando siempre el ticket primero** (como los cambios de estado).
- **El cierre automático reutiliza el camino de cierre** (`_closing_changes`): «cerrado ⇒ fecha y motivo» sigue sin poder romperse. El plazo (`AUTO_CLOSE_HOURS`, 24 horas corridas) y el intervalo (`SCHEDULER_INTERVAL_SECONDS`) son variables de entorno hasta `v0.7.0`.
- **El incumplimiento queda registrado** (RN-91): al avisar del vencimiento, el planificador deja el evento interno `SLA_VENCIDO` en el historial (actor Sistema).
- **Quedan fuera de la fase,** con su destino: las excepciones de SLA (RF-083) y la configuración de eventos y destinatarios de las notificaciones (RF-087 y RN-97), el interruptor general del SLA (RN-165, «configuración básica»), los avisos de la primera respuesta vencida y la política de retención de notificaciones leídas.

Cierre de la versión (entrega 9). Se midió antes de cambiar nada (tamaño y complejidad de los módulos, código sin uso, comentarios desfasados, consultas por pantalla y tiempos de la suite) y se actuó solo donde la medida lo justificaba:

- **`cli.py` pasó a un paquete** (`src/workdesk/cli/`: `setup`, `demo`, `sla` y `scheduling`, más `register_commands`). Era una sola función con complejidad 33 y 105 sentencias donde se habían ido apilando los comandos; ahora ninguna función de registro pasa de 12. Los comandos, sus nombres, opciones y salidas no cambiaron.
- **El incumplimiento del SLA queda en el historial** (`SLA_VENCIDO`): RN-91 pedía informarlo, avisar y registrarlo, y lo último solo se deducía de las fechas de los períodos. Es el único cambio de comportamiento de la entrega.
- **Un error real** que la revisión encontró en el planificador (entrega 8): bloqueaba primero el período y después, al guardar la notificación, el ticket (por su clave foránea); los cambios de estado bloquean al revés, así que un aviso y un cambio de estado simultáneos sobre el mismo ticket podían esperarse mutuamente y PostgreSQL abortaba a uno (`DeadlockDetected`). Se reprodujo con un test de hilos que fallaba y se corrigió.
- **La campana mantenía viva una sesión abandonada** (entrega 5): su consulta automática cada 30 segundos pasaba por los límites de sesión como una petición más y renovaba la última actividad, así que una pestaña olvidada nunca expiraba por inactividad (solo por las 8 horas de duración máxima, RNF-013). Ahora `auth/session.py` distingue las rutas **pasivas** (`PASSIVE_ENDPOINTS`): se comprueban como cualquier petición (con la sesión expirada responden `401` en JSON, sin cerrarla ni gastar el aviso «Tu sesión expiró») pero no cuentan como actividad. Ver "15. Sesiones".
- **Pruebas nuevas:** pantallas con datos reales y presupuesto de consultas, migraciones, una instalación limpia que sigue el README sobre un esquema creado solo por las migraciones, las reglas RN-85, RN-86 y RN-87 (que se cumplían por construcción pero no tenían una prueba que las defendiera), la sesión de la campana y coherencia con los documentos, incluida la lista de rutas (ver "23. Testing"). Los fixtures de los 76 tickets de demostración y `clock` pasaron a `conftest.py` y `tests/demo_data.py` para que los dashboards de `v0.6.0` los reutilicen.
- **Medido y dejado como está,** con su porqué: no hay código muerto real (los candidatos eran un registro de secuencia en el metadata y el «oráculo» en Python del test que compara SQL y Python); las consultas por pantalla están acotadas (listado 14 o 15, detalle hasta 22 para el personal y 12 para el Solicitante, pantallas de acción hasta 23) y no hay N+1; con casi 20 000 tickets (23 000 períodos de SLA, 54 000 eventos de historial y 12 000 notificaciones, medido en un esquema desechable de la base de pruebas) el número de consultas no cambia, el listado responde en unos 30 ms (entre 80 y 230 ms con el filtro y el orden por SLA), el centro de notificaciones en 17 ms, la campana en 3 ms y el planificador envía cada aviso en unos 6 ms; `seeds/demo_tickets.py::_refresh` (complejidad 52) es una herramienta de desarrollo cubierta por 259 tests de seeds, y dividirla arriesga el comportamiento sin beneficio para el producto: queda anotada como deuda técnica; las funciones con muchos argumentos (18) son la API de palabras clave del proyecto, una decisión deliberada.
- **Documentación:** se corrigieron comentarios y textos que hablaban de lo ya hecho como futuro, se completaron las cinco rutas de «SLA» que faltaban en el README y las cuatro columnas de `tickets_sla_periodos` que faltaban en `docs/09`, se añadieron los guardianes de coherencia con el README y `docs/12` incorpora la matriz de trazabilidad (cada requisito de la fase con su código y sus pruebas).

## Hito completado: v0.6.0

```text
v0.6.0 — Dashboards y carga de trabajo
```

Es la fase en que WorkDesk pasa de listar tickets a **dar una vista de conjunto**: cada rol abre un dashboard con lo suyo, el personal ve cómo está repartido el trabajo y el Supervisor puede redistribuirlo. Se construyó en diez entregas, cada una con su rama, sus tests y su Pull Request.

| # | Entrega | Estado | Tests al cerrar |
| --- | --- | --- | --- |
| 1 | Revisión de lo construido: backend/API y tests | Integrada (PR #46) | 3975 |
| 2 | Revisión: README, PROJECT_CONTEXT y documentación | Integrada (PR #47) | 3975 |
| 3 | Listado: filtros de asignación | Integrada (PR #48) | 3997 |
| 4 | Dashboard del Solicitante | Integrada (PR #49) | 4022 |
| 5 | Carga de trabajo: consultas | Integrada (PR #50) | 4052 |
| 6 | Carga de trabajo: pantalla | Integrada (PR #51) | 4075 |
| 7 | Dashboard operacional | Integrada (PR #52) | 4098 |
| 8 | Reasignación masiva: servicio | Integrada (PR #53) | 4130 |
| 9 | Reasignación masiva: pantallas | Integrada (PR #54) | 4170 |
| 10 | Cierre de la fase | Integrada (PR #55) | 4175 |

Decisiones de la fase:

- **Cada cifra es el total del listado al que enlaza,** y un test lo comprueba leyendo los enlaces de la propia página. Es lo que impide que un dashboard diga una cosa y el listado otra.
- **Las definiciones se escriben una sola vez** (`workload/queries.py`): *activo* es el ticket que no está Resuelto ni Cerrado, *sin asignar* el activo sin técnico vigente, *crítico* el de prioridad `CRITICA`, *SLA en riesgo* la suma de próximo a vencer y vencido. El dashboard operacional toma sus cifras de la carga de trabajo, así que las dos pantallas coinciden.
- **Un ticket con varios técnicos cuenta en cada uno y una vez en los totales;** la pantalla lo explica para que la suma no parezca un error.
- **La sobrecarga solo informa** (RN-26): una insignia con texto, nunca un bloqueo. Su umbral es una variable de entorno hasta `v0.7.0`.
- **El SLA sigue siendo solo del personal:** el Solicitante no ve carga, grupos ni SLA en su dashboard, y `/workload` y `/reassign` le responden 403.
- **La reasignación masiva es de tres pasos y no cambia nada hasta confirmar,** cada ticket se procesa por separado (uno cerrado se omite sin frenar a los demás), se bloquea siempre el ticket primero y en orden de id, y el servidor revalida todo al confirmar porque no confía en los campos ocultos del resumen.
- **Sin gráficos ni librerías nuevas:** cifras exactas y barras con CSS. La única migración es un índice, creado después de medir su efecto.

Errores reales que aparecieron por el camino:

- Entrega 7: un test mío no detectaba que se invirtiera el orden de prioridad (los ocho tickets más bajos tenían la misma prioridad); se reforzó. Y el nombre «Mis tickets activos» chocaba con un test que buscaba esa frase en el menú.
- Entrega 9: se creó la rama sobre una base sin la entrega anterior (su Pull Request aún no estaba mergeado); se detectó al fallar un import y se reubicó la rama sin perder nada.
- Entrega 10: la matriz de trazabilidad encontró tres cosas prometidas y no mostradas (los resueltos por técnico, los tickets en progreso y en espera del Técnico y los tickets por prioridad del Supervisor) y un error de la reasignación con quien dejó de ser Técnico.

Cierre de la fase (entrega 10). Se midió antes de cambiar nada, se comprobó la escala con ~20 000 tickets, se compararon los requisitos con el código y se actuó donde hacía falta: lo detallado está en `docs/12_roadmap.md` (fase 6, «Cierre de la fase»), con su matriz de trazabilidad, y en `PROJECT_CONTEXT.md` («Cierre de `v0.6.0`»).

---

## Hito completado: v0.7.0

```text
v0.7.0 — Administración y base de conocimiento
```

Es la fase en que el Administrador deja de depender del `.env`: lo que antes era una variable de entorno se cambia desde la web, con su rango, su auditoría y su aviso si otra persona lo cambió a la vez. Y es la fase en que el conocimiento del equipo empieza a quedarse escrito, cerca de los tickets que lo originan. Se construyó en diez entregas, cada una con su rama, sus tests y su Pull Request.

| # | Entrega | Estado | Tests al cerrar |
| --- | --- | --- | --- |
| 1 | Revisión previa | Integrada (PR #56) | 4234 |
| 2 | Tabla `configuracion` | Integrada (PR #57) | 4288 |
| 3 | Pantallas de configuración e interruptores | Integrada (PR #58) | 4382 |
| 4 | Configuración de notificaciones | Integrada (PR #59) | 4416 |
| 5 | Base de conocimiento: modelo y búsqueda | Integrada (PR #60) | 4484 |
| 6 | Base de conocimiento: pantallas | Integrada (PR #61) | 4543 |
| 7 | Conocimiento en los tickets y posibles duplicados | Integrada (PR #62) | 4604 |
| 8 | Adjuntos al crear y liberación de bloqueos | Integrada (PR #63) | 4642 |
| 9 | Estructura y protecciones | Integrada (PR #64) | 4657 |
| 10 | Cierre de la fase | Integrada (PR #65) | 4681 |

Decisiones de la fase:

- **Una fila es un valor elegido; sin fila rige el inicial.** Así la aplicación arranca sin cargar nada y «restablecer» es borrar la fila. Las definiciones (claves, rangos, valores por defecto) siguen en el código, en un único lugar (`settings.py`).
- **La configuración se lee una vez por petición, sin caché entre peticiones,** porque el planificador es otro proceso y una caché en el servidor web no vería los cambios del Administrador. Cuesta una consulta sobre una tabla de pocas filas, y está medida.
- **Los avisos se configuran apagando, no creando.** Un motor de reglas habría permitido mandar algo interno a un Solicitante por error; un catálogo cerrado lo impide por construcción.
- **La búsqueda es la de PostgreSQL**, en español y además sin tildes, sin extensiones ni dependencias. Se mide en milisegundos con 20 000 artículos.
- **Un artículo que no se puede leer responde 404 como uno que no existe,** igual que los tickets, y quién ve qué se decide en la consulta.
- **Nada que no deba bloquear bloquea:** la advertencia de duplicados nunca impide crear, la ubicación obligatoria no es retroactiva y liberar un bloqueo no borra el trabajo de nadie.

Errores reales que aparecieron por el camino:

- Entrega 1: el login respondía más rápido a un usuario inexistente que a uno con la contraseña equivocada, lo que permitía adivinar quién existe.
- Entrega 2: el tope de subida de Flask se fijaba al iniciar y no habría seguido al valor que elige el Administrador; y un ciclo de importación entre `settings` y `security`.
- Entrega 3: un número desmesurado habría hecho fallar el cálculo de fechas de todas las pantallas, y la tecla Enter pulsaba «Restablecer».
- Entrega 8: el latido de la pantalla de edición habría recuperado un bloqueo recién liberado (por eso hizo falta una migración).
- Entrega 10: un requisito sin hacer (RF-019), el tamaño de archivo mostrado como «0 MB», `sla-status` equivocado con el SLA apagado, dos comandos que fallaban al redirigir su salida en Windows y dos selectores con el mismo `id`.

Entrega por entrega:

- **Entrega 1, revisión previa:** se auditó lo construido buscando lo arrastrado de las fases anteriores. El login ya no delata qué usuarios existen por el tiempo de respuesta (un usuario inexistente, inactivo o bloqueado no calculaba ningún hash y respondía mucho más rápido que uno que existe con la contraseña equivocada) y vacía la sesión anterior al autenticarse. Cada pantalla pasó de tres consultas previas a dos al traer el rol junto con el usuario. Los 14 parámetros numéricos tienen ahora una única definición (`settings.py`) en lugar de repartirse entre `config.py` y seis validaciones. El planificador limpia los restos de subidas cortadas. La suite pasó de 4175 a 4234 tests. Medido y dejado como está: los índices de las claves «quién lo hizo» (12 ms contra 1,3 ms con 250 000 eventos para «resueltos por mí», que no justifica encarecer cada escritura del historial) y el tamaño de los módulos (ninguna función supera la complejidad 12).

- **Entrega 2, tabla `configuracion`:** los 14 parámetros numéricos pueden tener ahora un valor elegido por el Administrador, guardado en la base de datos (sin fila rige la variable de entorno o el valor por defecto). Todo el código lee por `value_of`, con una sola consulta por petición y sin caché entre peticiones porque el planificador es otro proceso; cada cambio se valida (también las relaciones entre dos parámetros), se audita y se serializa con un bloqueo de PostgreSQL. Por el camino aparecieron dos interacciones que ningún test de la entrega 1 podía ver: el tope de subida de Flask se fijaba al iniciar y no habría seguido al valor vigente (ahora lo fija una comprobación previa, registrada antes de la protección CSRF, que es quien lee el cuerpo), y un ciclo de importación entre `settings` y `security`. La suite pasó de 4234 a 4288 tests; cada petición autenticada pasó de dos a tres consultas.

- **Entrega 3, pantallas de configuración:** el Administrador edita desde la web los parámetros (cinco pantallas por tema, con restablecer, auditoría y aviso de conflicto) y apaga o enciende el SLA y el cierre automático. Con el SLA apagado nada lo muestra ni avisa, pero los períodos se siguen calculando para que encenderlo no obligue a reconstruir nada; ese es el motivo de la decisión. Aparecieron dos riesgos que solo existen cuando una persona escribe los valores: un número desmesurado habría hecho fallar el cálculo de fechas de cada pantalla (ahora todos tienen máximo) y la tecla Enter habría pulsado un «Restablecer». La suite pasó de 4288 a 4382 tests.

- **Entrega 4, configuración de notificaciones:** el Administrador apaga y enciende avisos concretos (evento y destinatarios) desde una tabla. Se evitó un motor de reglas: los avisos posibles son un catálogo cerrado y solo se pueden apagar, así que ningún ajuste puede enviar algo interno a un Solicitante; dos avisos que exigen las reglas de negocio quedan fijos. Para que fuera verificable, todo envío pasa por una única función y un test impide saltársela. La suite pasó de 4382 a 4416 tests.

- **Entrega 5, base de conocimiento (modelo):** artículos con borrador y publicación, público y privado, destacados, permisos por rol resueltos en la consulta y búsqueda en español. El hallazgo que decidió el diseño: el diccionario español de PostgreSQL no encuentra «configuración» cuando se escribe sin tilde, así que se indexa además el texto sin tildes, sin extensiones. Se reutiliza el catálogo de categorías de los tickets. La suite pasó de 4416 a 4484 tests.

- **Entrega 6, base de conocimiento (pantallas):** portada con búsqueda, categorías, destacados y recientes; detalle de lectura; gestión y editor para el personal, y cada acción editorial con su confirmación. Decisión que se aparta del patrón de los tickets: ante un conflicto al editar se conserva el texto escrito (un artículo puede ser largo) sin permitir pisar el cambio ajeno. La suite pasó de 4484 a 4543 tests.

- **Entrega 7, conocimiento en los tickets y duplicados:** artículos vinculados a tickets, artículo creado desde la resolución y aviso de posibles duplicados al crear un ticket, que nunca impide crearlo ni enseña tickets ajenos. La medición a escala destapó que la comparación calculaba el vector de cada título una vez por palabra; calculándolo una sola vez pasó de 1,3 s a 0,5 s con 20 000 candidatos. La suite pasó de 4543 a 4604 tests.

- **Entrega 8, adjuntos al crear y liberación de bloqueos:** se pueden adjuntar archivos al crear un ticket (todo o nada) y el Supervisor o el Administrador pueden liberar el bloqueo de edición de otra persona, con auditoría. Lo que obligó a una migración: el latido de la pantalla volvía a adquirir el bloqueo, así que la liberación no habría durado. La suite pasó de 4604 a 4642 tests.
- **Entrega 9, estructura y protecciones:** sin cambios de comportamiento, para llegar al cierre con el código ordenado. El detalle del ticket (924 líneas) y el listado (647) pasaron a parciales; se comprobó que 484 pantallas generadas antes y después son idénticas. `sla/periods.py` se partió en escritura (`periods.py`), lectura (`evaluation.py`) y reconstrucción (`rebuild.py`), y lo que un cambio de estado deja escrito salió de `lifecycle.py` a `lifecycle_history.py`. Se reunió lo que estaba copiado: la limpieza de motivos (seis copias de su largo máximo), la lectura de un id de la URL, el filtro Activos / Inactivos, la lista de estados y `mark_modified`. Cuatro protecciones nuevas, probadas con diez mutaciones: las migraciones y los modelos crean el mismo esquema (también los `CHECK`, que `db check` no mira), el Solicitante solo lee la base de conocimiento, el frontend no escribe colores ni JavaScript en línea ni carga nada de Internet, y los interruptores deben estar documentados. Medido y dejado como está: con 20 000 tickets todas las pantallas responden en menos de medio segundo; se probó resolver el estado del SLA con una sola subconsulta y no mejoró.

- **Entrega 10, cierre de la fase:** se midió a escala (unos 20 000 tickets, 5000 artículos y 24 000 avisos: ninguna pantalla pasa del medio segundo), se recorrieron 162 pantallas con los cuatro roles buscando errores del servidor y de accesibilidad, y se comparó cada requisito con el código. La matriz encontró la ubicación obligatoria (RF-019), que se hizo; el recorrido, dos selectores de Grupos con el mismo `id`; y la revisión, tres formas distintas de escribir un tamaño de archivo (una mostraba «0 MB»), `sla-status` equivocado con el SLA apagado y dos comandos que fallaban en Windows al redirigir su salida. Todo con su prueba, y la documentación cerrada con la matriz de trazabilidad (`docs/12`, fase 7). La suite pasó de 4657 a 4681 tests.

## Hito en curso: v0.8.0

```text
v0.8.0 — Reportes, auditoría y backups
```

Se planificó en doce entregas (`docs/12`, fase 8). Como en las dos fases anteriores, la primera revisa lo construido antes de construir encima, y esta vez con un foco especial en la seguridad.

| # | Entrega | Estado | Tests al cerrar |
| --- | --- | --- | --- |
| 1 | Revisión previa | Integrada (PR #66) | 4728 |
| 2 | Velocidad de la suite | Integrada (PR #67) | 4746 |
| 3 | Eventos de autenticación | Integrada (PR #68) | 4775 |
| 4 | Pantalla de auditoría | En revisión (`feature/audit-screen`) | 4807 |

- **Entrega 1, revisión previa.** Primero se midió.
  - **Velocidad de la suite.** 4681 tests en 7 min 23 s, con los 6 procesos equilibrados (de 424 a 437 s cada uno). El 55 % del trabajo eran la preparación y la limpieza de los tests, no los tests. Cada test con base de datos estrenaba una conexión (54 ms: PostgreSQL en Windows crea un proceso por conexión) y cada login pagaba Argon2id con 4 hilos y 64 MiB en seis procesos a la vez. Se dejó para la entrega 2, con un prototipo que la baja a 4 min 26 s.
  - **Errores reales en el código.**
    - Una sonda con 20 intentos de login simultáneos dejó el contador de fallos en 2 y la cuenta sin bloquear: con ráfagas en paralelo se probaban muchas más contraseñas de las permitidas. Ahora el login y el cambio de contraseña bloquean la fila del usuario.
    - Dos procesos escribiendo el mismo log reprodujeron 16 rotaciones fallidas en Windows. Ahora el planificador escribe su propio archivo.
    - `create-admin` aceptaba usernames que la pantalla rechaza y no se auditaba. Las reglas de identidad se juntaron en un módulo que usan el formulario, el servicio y el comando.
  - **Refuerzo de seguridad.**
    - En producción, la aplicación no arranca con una clave corta ni con el depurador.
    - La cookie de sesión deja de delatar el framework.
    - El logout vacía la sesión.
    - Cualquier error tiene la página de WorkDesk.
    - Hay cuatro cabeceras de aislamiento más.
  - **Comprobado sin cambios:** no hay redirecciones abiertas, SQL armado con texto del usuario ni `|safe`.
  - **Guardianes nuevos**, probados con 17 mutaciones que mueren todas:
    - ninguna clave foránea borra en cascada (hoy son 93);
    - toda tabla de eventos es de solo añadir, detectada sola, así que la de autenticación de la entrega 3 quedará cubierta sin tocar la prueba;
    - los parámetros de Argon2id de producción no bajan del mínimo de OWASP.

    El módulo de tests del cierre de `v0.7.0`, agrupado por fecha, se repartió por tema. La suite pasó de 4681 a 4728 tests.

- **Entrega 2, velocidad de la suite.** Se midió con un plugin que anota el tiempo de preparar, ejecutar y limpiar cada test y el proceso que lo corrió. Partida: 4728 tests en 6 min 54 s, con el 54,5 % del trabajo en preparar y limpiar. Primero se probaron prototipos fuera del repositorio sobre cinco áreas. Compartir la caché de SQL compilado no ganó nada. Reutilizar las conexiones bajó un 26 % y abaratar Argon2id en la suite, un 50 %: sus 4 hilos por verificación en seis procesos a la vez competían por los núcleos.

  Lo que se hizo, sin cambiar el comportamiento:
  - una reserva de conexiones en `tests/database.py` que las devuelve limpias (`ROLLBACK`, `RESET ALL` y suelta los bloqueos consultivos);
  - Argon2id mínimo en la suite, con los parámetros de producción ahora explícitos y vigilados;
  - el seed busca sus tickets en una consulta;
  - las dos pruebas monolíticas, repartidas;
  - tres tests del seed que solo miran un ticket cargan solo ese.

  Resultado: 4746 tests en 4 min 12 s (−39 %). Medido y descartado: una instantánea de los catálogos (unos 7 s reales a cambio de una restauración que depende del orden de los fixtures). Seis mutaciones, todas detectadas; una de ellas confirma que la equivalencia del SLA, ahora con una consulta por momento, sigue viendo un borde de un segundo.

- **Entrega 3, eventos de autenticación.** La tabla `eventos_autenticacion` registra cada intento de entrar y cada salida: inicio de sesión correcto y fallido, bloqueo, cierre y expiración de la sesión, y la contraseña actual equivocada al cambiarla.
  - **La causa de un rechazo queda como código interno** y nunca se muestra. Cada camino de rechazo del login pasa ahora por un único ayudante, así que ninguno puede olvidar registrar su intento ni romper la igualdad de tiempos.
  - **Lo escrito como usuario solo se guarda si tiene forma de username:** alguien pudo escribir ahí su contraseña. Un test comprueba que ninguna contraseña llega a ninguna columna.
  - **Límite de intentos por equipo.** Con el registro se pudo atacar algo que el bloqueo por cuenta no ve: quien prueba cuatro contraseñas en cada una de cien cuentas. Pasados `LOGIN_MAX_FAILED_PER_IP` fallos desde una IP (20 por defecto, configurable en «Seguridad y sesión», 0 lo apaga), los intentos siguientes se rechazan antes de mirar la cuenta. El recuento se serializa con un bloqueo consultivo por IP: doce intentos simultáneos con un límite de tres dejan exactamente tres que miran una cuenta.
  - **«Mi cuenta» muestra los últimos diez accesos de la propia cuenta.** Es la forma más simple de que alguien detecte intentos que no reconoce.
  - **Una decisión al probar.** El rechazo por el límite del equipo ocurre antes de buscar la cuenta, así que el evento guarda lo escrito como usuario (qué cuenta estaban atacando) en lugar de enlazarla. Se dejó así y se documentó.
  - **Un guardián que hubo que ajustar con intención.** El coste mínimo por petición se medía en «Mi cuenta», que ahora hace una consulta más a propósito; pasó a medirse en «Cambiar contraseña», que sigue costando tres.
  - **Integridad automática.** La tabla nueva quedó cubierta sola por las pruebas de integridad: tiene `fecha_hora`, así que se le exigió ser de solo añadir.

  Doce mutaciones, todas detectadas. La suite pasó de 4746 a 4775 tests.

- **Entrega 4, pantalla de auditoría.** Una sola pantalla para el Administrador reúne los tres registros de solo añadir: la auditoría administrativa, los accesos y el historial de todos los tickets.
  - **Filtros validados.** Cada filtro se comprueba contra su vocabulario (la acción, el tipo de evento, la IP con `ipaddress`, el número de ticket); un valor que no corresponde se ignora y nunca llega a la consulta.
  - **Coste fijo.** Las personas y los tickets de la página se cargan en lote, así que cuesta lo mismo con una fila que con cincuenta.
  - **Nombres legibles obligatorios.** Las 39 acciones y todos los tipos de entidad tienen su nombre, y dos tests lo exigen; el de las entidades lee los tipos del propio código.
  - **Medido antes de decidir.** Con 250 000 filas por registro todo responde por debajo de 220 ms, así que no se creó ningún índice ni migración.
  - **La prueba de mutación encontró un hueco en un test.** El de fechas comprobaba «desde ayer hasta mañana» pero nunca «hasta hoy», justo el caso en que «hasta» debe abarcar el día entero: se añadió.
  - **Una mutación sobrevive a propósito.** Quitar una de las dos capas de autorización (la ruta y la política) no cambia nada, porque la otra sigue bloqueando; sin las dos, el test falla.

  La suite pasó de 4775 a 4807 tests.

---

# 3. Revisión final de la fase de v0.4.0 (entrega 12)

## Revisión final de la fase (entrega 12 de `v0.4.0`)

La entrega 12 cerró la versión con una revisión de todo el código de la fase. Los cambios de estructura no alteraron ninguna ruta ni comportamiento previo (los tests existentes lo siguen verificando), salvo los dos textos que se indican más abajo. Lo que cambió y por qué:

- **`tickets/state_actions.py` (nuevo):** el catálogo de acciones de estado (textos, roles, esenciales) salió de `tickets/lifecycle.py`, que ahora es solo el motor (`change_state`, `available_actions` y `apply_derived_transition`). La pantalla de administración lee el mismo catálogo, así que lo que muestra no puede separarse de lo que el código hace.
- **`tickets/routes/` (paquete):** `tickets/routes.py` había llegado a casi 1850 líneas. Ahora hay un módulo por área (`listing`, `creation`, `detail`, `editing`, `states`, `assignment`, `requesters`, `comments`, `attachments` y `relations`) más `common.py` con lo que comparten. Todos registran sus rutas en el mismo blueprint, así que los endpoints y las URL no cambiaron (se comprobó comparando el mapa de rutas antes y después). `render_detail` se dividió en piezas pequeñas.
- **`tickets/history.py` (nuevo):** `describe_history_changes` era una cadena de condiciones que crecía con cada evento. Ahora cada evento tiene una función registrada con `@describes(...)`, y `tests/test_ticket_history.py` exige que todo evento del vocabulario tenga la suya y que ninguna línea repita un motivo.
- **Ayudantes unificados:** `cleaning.py` (`blank_to_none` y `strip_text`) sustituye a las copias de los servicios y formularios de catálogos, grupos, usuarios y tickets; `current_actor()` y `admin_only` viven en `security/` en lugar de repetirse en cada módulo de rutas; en los tests, `ticket_by_public_id` y `person` pasaron de ocho y tres archivos a `tests/ticket_helpers.py`.
- **Textos sin nombres de estado escritos a mano:** como el Administrador puede renombrar los estados, el resumen del detalle usa «Fecha de resolución» y «Fecha de cierre», y las pantallas de cambio de estado y de duplicado usan el nombre vigente del estado de destino.
- **Red de seguridad de autorización:** `tests/test_route_authorization.py` recorre el mapa de rutas, como `test_route_protection.py`, y comprueba la propiedad del ticket (404 al ajeno), el rol (403 en las rutas del personal y en las áreas de administración) y que lo que un Solicitante sí puede usar está declarado a propósito (`REQUESTER_ENDPOINTS`). Una ruta nueva queda cubierta sin tocar el test.

---

# 4. Los tests, entrega por entrega

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

Estado tras la entrega 10 de `v0.6.0` (cierre de la versión):

```text
4175 tests passing
```

Los 5 tests nuevos cubren:

- `tests/test_ticket_reassignment.py` (+1): quien dejó de ser Técnico puede quedarse sin tickets (RN-104).
- `tests/test_dashboard_staff.py` (+3): el recuento por prioridad coincide con su listado (Supervisor y Técnico) y suma los tickets activos.
- `tests/test_security_headers.py` (+1): `/workload` y `/reassign` no se guardan en caché.
- Ajustes sin cambiar lo que comprueban: «Mi trabajo» tiene cinco cifras enlazadas y la consulta de la carga de trabajo cuesta siete consultas (antes ocho).
- **Mediciones:** la suite completa tarda unos 6 minutos en paralelo (`-n 6`; 6 min 19 s con los 4175 tests); la escala se midió con ~20 000 tickets en una base de pruebas, sin dejar rastro.

Estado tras la entrega 9 de `v0.6.0` (reasignación masiva, pantallas):

```text
4170 tests passing
```

`tests/test_reassignment_screen.py` (38 tests): permisos (403 a Técnico y Solicitante, también en los POST), los tres pasos, lo que se conserva al fallar la validación, tickets que cambian entre el resumen y la confirmación, envíos manipulados, doble envío, avisos sin el motivo, el recorrido completo con los datos de demostración y un número de consultas que no crece con la cantidad de tickets. Mutaciones: quitar el control de rol de la confirmación (4 fallos) y no revalidar los tickets (2).

Estado tras la entrega 8 de `v0.6.0` (reasignación masiva, servicio):

```text
4130 tests passing
```

`tests/test_ticket_reassignment.py` (32 tests): el reparto, el rastro completo (asignación anterior cerrada y conservada, eventos con lote y motivo, una auditoría), lo que no cambia (versión, estado, SLA), las omisiones, los errores que detienen todo, permisos y un test con dos hilos y órdenes contrarios que falla si se quita el bloqueo en orden de id. Mutaciones: sin orden de bloqueo (1 fallo), sin permiso (3) y sin cerrar la asignación anterior (5).

Estado tras la entrega 7 de `v0.6.0` (dashboard operacional):

```text
4098 tests passing
```

`tests/test_dashboard_staff.py` (23 tests): cada contador contra su listado, coincidencia con la carga de trabajo, qué ve cada rol, el orden de los tickets prioritarios, que la actividad no copie el contenido de un comentario y un número de consultas que no crece con el equipo. La migración del índice se aplicó tras medirlo (79 ms contra 0,09 ms con 250 000 eventos).

Estado tras la entrega 6 de `v0.6.0` (carga de trabajo, pantalla):

```text
4075 tests passing
```

`tests/test_workload_screen.py` (23 tests): los enlaces se leen de la propia página y se resuelven con los filtros del listado para exigir que su total sea la cifra mostrada, también con filtros.

Estado tras la entrega 5 de `v0.6.0` (carga de trabajo, consultas):

```text
4052 tests passing
```

`tests/test_workload_queries.py` (30 tests): cada cifra contra su listado, un ticket con dos técnicos, quién aparece, la carga alta, solo el personal y el número de consultas.

Estado tras la entrega 4 de `v0.6.0` (dashboard del Solicitante):

```text
4022 tests passing
```

`tests/test_dashboard_requester.py` (25 tests).

Estado tras la entrega 3 de `v0.6.0` (filtros de asignación del listado):

```text
3997 tests passing
```

Estado tras las entregas 1 y 2 de `v0.6.0` (revisión de lo construido):

```text
3975 tests passing
```

Estado tras la entrega 9 de `v0.5.0` (cierre de la versión):

```text
3965 tests passing
```

Los 40 tests nuevos cubren:

- `tests/test_pages_smoke.py` (11): **cada rol abre lo que le corresponde con datos reales** (los 76 tickets de demostración): las pantallas generales dan 200 o 403 según el rol y, para el personal, el detalle de los 76 tickets y las 14 pantallas de acción de cada uno (1064 peticiones) abren o vuelven al detalle con un aviso, nunca un error ni el login; el Solicitante abre **exactamente** los tickets que creó o donde es solicitante vigente (calculados con SQL propio) y recibe 404 en el resto; y los adjuntos se descargan como archivo. Cada petición tiene un **presupuesto de consultas** (20 en las pantallas, 30 en el detalle del personal, 18 en el del Solicitante y 30 en las de acción, con margen sobre lo medido), y el listado hace las mismas consultas en la primera y la segunda página. Las excepciones de la aplicación no se esconden detrás de una página de error en las pruebas, así que una plantilla que falla con una combinación poco común hace fallar el test.
- `tests/test_migrations.py` (2), los dos en un esquema desechable de `workdesk_test` y en un subproceso (el `env.py` de Alembic reconfigura el logging): **(1) las migraciones son coherentes**: suben todas, hay una sola cabeza, `db check` no encuentra diferencias con los modelos, bajan hasta dejar solo `alembic_version` (ninguna tabla ni secuencia) y vuelven a subir (se comprobó que falla de verdad: añadir una columna a un modelo sin migración rompe el paso de `db check` con «Detected added column»; unos 12 s, cada comando `flask db` unos 1,5 s); **(2) una instalación limpia funciona**: sobre un esquema creado solo por las migraciones sigue los pasos del README (`seed-roles`, `seed-catalogs`, `seed-demo`, `seed-demo-tickets`, `seed-demo-notifications`, `sla-status` y dos veces `run-scheduler --once`) y revisa lo que deja en la base: los 76 tickets, un período de SLA por cada uno, un único `SLA_VENCIDO` por cada vencimiento avisado y nada duplicado al repetir. Cubre lo que `db check` no ve (secuencias, valores por defecto y restricciones `CHECK`): se comprobó quitando el valor por defecto de `fecha_creacion` en la migración de notificaciones, con lo que `db check` siguió pasando y esta prueba falló con el error real (`NotNullViolation`). `create-admin` queda fuera porque pide la contraseña con `getpass`, que en Windows lee la consola y no una tubería (lo cubre `test_cli.py`). Usa un directorio temporal para los adjuntos. Tarda unos 17 s.
- `tests/test_docs_coherence.py` (9): cada variable de entorno que lee el código está en `.env.example`, el README y este archivo; cada comando propio tiene un ejemplo ejecutable en el README y aquí; cada migración figura en la lista de este archivo; **la lista «Rutas actuales» del README y de este archivo es el mapa de rutas real** (ni falta una, ni sobra una que ya no existe, ni se equivoca de métodos; `/static` queda fuera porque es el servidor de archivos de Flask); y el propio recorrido encuentra lo que debe (no pasa en vacío). Se comprobó que una variable sin documentar lo hace fallar nombrándola y que el guardián de rutas detecta una ruta quitada, una inventada y un método equivocado (el README no listaba cinco rutas de `/admin/sla`, y así se descubrió).
- `tests/test_sla_business_rules.py` (7): **las reglas del SLA que protegen el trabajo.** RN-85 (el SLA es del ticket, no del técnico): asignar, reasignar, quitar a un técnico, cambiar el grupo y escalar no tocan los períodos (mismos ids y mismas fechas), y cambiar de técnico no cambia lo consumido. RN-86 (el incumplimiento no bloquea nada): con el SLA vencido se sigue comentando, esperando, reanudando, resolviendo, cerrando y reabriendo, resolver o reabrir no borra el incumplimiento, y la pantalla sigue ofreciendo y aceptando resolver. RN-87 (la carga no detiene el reloj): tres tickets de un mismo técnico consumen cada uno su propio tiempo laboral desde su propio inicio. Se comprobó que detectan una violación real alterando temporalmente el código.
- `tests/test_session_limits.py` (+3): **la consulta de la campana no cuenta como actividad.** No renueva la última actividad; una pestaña abandonada que consulta cada 30 segundos no mantiene viva la sesión (con un reloj que se mueve a mano: la campana responde poco antes del límite y, dos minutos después, la sesión ya expiró y la siguiente acción de la persona recibe «Tu sesión expiró»); y una sesión pasada de la duración máxima no recibe datos (`401`). Se comprobó con tres mutaciones (renovar en la consulta pasiva, cerrar la sesión en ella en vez de responder `401` y no tener rutas pasivas): las tres se detectan.
- **El incumplimiento registrado** (`tests/test_scheduler.py`, +6, y `tests/test_ticket_history.py`, +2: el texto del evento y su caso en la prueba que recorre todo el vocabulario): el vencimiento deja un único evento `SLA_VENCIDO` interno, con el Sistema como actor y el período, el objetivo y el instante en el contexto; el aviso de umbral no lo registra; volver a ejecutar no lo duplica; un vencimiento hallado tras un aviso también se registra; el personal lo lee con su objetivo y el Solicitante nunca lo ve; y un aviso que falla no deja el evento. Las pruebas que recorren todo el vocabulario (descriptor, nombre, visibilidad, motivos y texto de comentarios) ya lo cubren sin cambios.
- Ajustes sin cambiar lo que comprueban: los fixtures y constantes de la demostración salieron de `tests/test_seed_demo_tickets.py` a `tests/demo_data.py` y `tests/conftest.py`; la fixture `clock`, que tres módulos tenían copiada, es una sola; y `tests/areas.py` incluye los módulos nuevos en `platform`.
- **Mediciones:** la suite completa tarda unos 6 minutos en paralelo (`-n 6`; 6 min 12 s con los 3965 tests); el recorrido de pantallas, unos 27 s; las dos pruebas de migraciones, unos 30 s; Ruff y `db check`, limpios. **Prueba de mutación** de los cambios del planificador: 33 mutaciones, 2 supervivientes equivalentes (documentados en la entrega 8).

Estado tras la entrega 8 de `v0.5.0` (planificador):

```text
3925 tests passing
```

Los 50 tests nuevos (`tests/test_scheduler.py`) cubren:

- **avisos de SLA:** el umbral avisa al llegar (y no un instante antes), una sola vez, a los técnicos asignados y nunca al solicitante; sin técnicos, a todos los Supervisores; el vencimiento avisa al técnico y a los Supervisores, una sola vez; un vencido encontrado tarde no envía también el aviso de umbral; la secuencia umbral y luego vencido; las marcas quedan en el período; un técnico inactivo no recibe nada; un ticket en pausa, resuelto o reanudado tras un aviso no repite avisos; un cambio de prioridad abre un SLA que puede avisar otra vez; la lista de candidatos solo trae períodos abiertos con algo pendiente; **un período cerrado o ya avisado por otro planificador se omite al volver a comprobarlo bajo bloqueo; dos planificadores a la vez envían un solo aviso (hilos); un aviso y un cambio de estado del mismo ticket a la vez no se bloquean entre sí (hilos)**; y un fallo no detiene los demás ni deja marca (se reintenta);
- **cierre automático:** cierra pasado el plazo y no antes, con el plazo de la configuración, con y sin solicitantes y solo tickets `Resuelto`; deja el ticket cerrado con motivo `INACTIVIDAD`, `cerrado_automaticamente`, sin usuario que cierra y sin usuario de modificación; dos pasadas cierran una vez; el historial lo registra como el Sistema con su contexto; avisa a solicitante y técnico («Ticket cerrado automáticamente») sin datos internos y no a los demás; detiene el SLA; se puede reabrir (y limpia la bandera); el detalle lo muestra; **el plazo se comprueba dentro del cierre** (rechazado después de encontrarlo, resuelto de nuevo, resuelto hace menos de 24 h, una transición deshabilitada); los candidatos excluyen a los ya cerrados; y un fallo no detiene los demás cierres;
- **`run_once`, el bucle y la configuración:** ejecuta las dos tareas, espera entre pasadas, una pasada fallida no lo detiene, la aplicación no arranca con `AUTO_CLOSE_HOURS` o `SCHEDULER_INTERVAL_SECONDS` menores o iguales que cero y los valores por defecto;
- **el comando:** `--once` informa lo hecho, se puede repetir sin efecto, falla si un elemento falló y rechaza un intervalo no positivo.
- **Prueba de mutación** (script desechable): 33 mutaciones del planificador, el cierre automático, la herencia de las marcas, los destinatarios, el comando y el control de versión. En la primera pasada sobrevivieron 8: 6 señalaron huecos reales (las listas de candidatos, el plazo dentro del cierre y la herencia de avisos al cambiar de prioridad, entre otros) y se añadieron sus tests; quedan **2 equivalentes** (comprobar el estado dentro de `close_automatically` es defensa en profundidad, porque sin él la falta de una transición `AUTO_CIERRE` desde ese estado ya impide cerrar; y detener el SLA al cerrar no cambia nada porque el período ya se cerró al resolver).
- **Un error que encontró la revisión posterior** (no la mutación): el aviso bloqueaba primero el período y, al guardar la notificación, el ticket (por su clave foránea); los cambios de estado bloquean al revés. Un aviso y un cambio de estado del mismo ticket a la vez podían bloquearse entre sí y PostgreSQL abortaba a uno (`DeadlockDetected`), con lo que la persona que estaba trabajando recibía un error. Se reprodujo con un test de hilos que fallaba, y se corrigió bloqueando siempre **el ticket primero**; la mutación que vuelve al orden antiguo ahora hace fallar ese test.
- Ajustes sin cambiar lo que comprueban: `tests/areas.py` incluye `test_scheduler` en el área `sla`.

Estado tras la entrega 7 de `v0.5.0` (indicadores de SLA):

```text
3875 tests passing
```

Los 869 tests nuevos cubren:

- `tests/test_sla_indicators.py` (832; 800 son la comprobación del umbral exacto para ocho objetivos y los porcentajes de 1 a 100): **la fecha de aviso al abrir el período** (Media y Alta con sus fechas, paridad con el vencimiento, pausado sin fecha, al reanudar con lo que queda, el umbral heredado aunque se edite la política y tomado de la política nueva al cambiar de prioridad, sin umbral no avisa nunca, nacer ya pasado el umbral); **el umbral exacto** (el primer segundo que alcanza el porcentaje, redondeo hacia arriba, aviso y vencimiento al segundo, un ticket detenido que consumió el 88 % no está «próximo», un período sin fecha de aviso no avisa); **las restricciones de la base** (umbral fuera de 1 a 100, fecha de aviso después del vencimiento o antes del inicio o en un período pausado, y los bordes que sí se aceptan); **la evaluación por lotes** (igual que ticket a ticket, un ticket sin SLA o desconocido, las mismas consultas para 14 tickets que para uno, y cada ticket con el calendario con que se calculó); **las condiciones SQL** (en catorce escenarios y más de 150 momentos, con los bordes de un segundo, seleccionan exactamente lo que dice la evaluación; cada ticket está en una sola opción; el orden por urgencia); y **el relleno** (restaura la fecha calculada al abrir, con lo ya consumido, es idempotente y no toca períodos cerrados, pausados ni sin umbral).
- `tests/test_sla_indicators_ui.py` (36): **el listado** (columna e insignias para el personal, nada para el Solicitante, el filtro por cada estado, las cuentas de las pestañas, un valor desconocido, el Solicitante no puede filtrar ni ordenar, el orden por urgencia, un ticket sin política, y las mismas consultas con una o con quince filas); **el detalle** (tarjeta, consumo, lo excedido, pausa, detenido, sin SLA, los períodos con su motivo, y nada de esto para el Solicitante); **la advertencia** (con el SLA en riesgo sí, dentro de plazo o pausado no, el Solicitante 403, y el servicio del listado ignora el filtro y el orden por SLA para un Solicitante); **el aviso a los Supervisores** (los del grupo, todos si no hay grupo o ninguno activo, nunca quien lo hizo ni los inactivos, ni al subir (tampoco con el SLA en riesgo) ni con el SLA dentro de plazo o sin SLA, también desde la pantalla, y se revierte con el cambio); y **los comandos** (`sla-rebuild` completa las fechas, `sla-status` muestra el aviso).
- `tests/test_seed_demo_tickets.py` (+1): todo período en marcha de la demostración tiene su fecha de aviso.
- Ajustes sin cambiar lo que comprueban: `tests/sla_helpers.py` reúne las ayudas que `test_sla_periods.py` tenía copiadas.
- **Prueba de mutación** (script desechable): 30 mutaciones de los períodos, las consultas SQL, el servicio del listado, la ruta, la advertencia, `change_priority`, los destinatarios y el comando; 24 se detectaron a la primera; de las 6 que sobrevivían, 3 señalaban huecos reales (el servicio del listado frente a un Solicitante y subir la prioridad con el SLA en riesgo) y se añadieron sus tests, y 3 son equivalentes (el período abierto aporta 0 segundos consumidos, el instante por defecto coincide con el que pasa la ruta y el servicio de avisos ya omite a los usuarios inactivos).

Estado tras la optimización de la suite (entre las entregas 6 y 7 de `v0.5.0`):

```text
3006 tests passing
```

Los 23 tests nuevos están en `tests/test_suite_infrastructure.py` y cubren: **la protección de `workdesk_test`** (rechaza `workdesk_dev`, `workdesk`, `postgres`, nombres parecidos como `workdesk_test2` o `workdesk_testing`, otra capitalización y una URL que contiene `workdesk_test` solo en el usuario o el servidor; exige la variable y devuelve la URL sin cambios cuando es la correcta); **el esquema por proceso** (sin paralelismo se usa el de por defecto; cada worker de `pytest-xdist` el suyo); **la limpieza entre tests** (`empty_tables` deja todas las tablas sin filas y las secuencias en 1, también si ya estaba vacía); **las instantáneas** (restauran filas y secuencias exactamente, devuelven lo que se guardó con ellas y se pueden restaurar dos veces); y **las áreas** (todo módulo de tests pertenece a una, ninguna lista un módulo que no existe, ninguno está en dos, todas están declaradas como marcador en `pytest.ini` y cada test recibe el suyo, y `unit` solo si no usa la base).

Medido: la suite completa tarda unos 13 minutos en serie y unos 4 en paralelo (`-n 6`), frente a unos 34 antes. En una muestra de 237 tests, el 83 % del tiempo era preparar y limpiar fixtures y solo el 17 % los tests; ahora la preparación y la limpieza son unos 200 ms por test (antes 665 ms) y el seed de tickets de demostración, que era la mitad del tiempo restante, bajó de unos 10 minutos a 2. No hay cambios de comportamiento: los mismos tests pasan sin modificar lo que comprueban (solo `tests/test_seed_demo_tickets.py` cambia sus fixtures y dos tests, que recreaban el esquema a mitad del test, usan ahora la limpieza rápida).

Estado tras la entrega 6 de `v0.5.0` (avisos por los eventos de un ticket):

```text
2983 tests passing
```

Los 28 tests nuevos cubren:

- `tests/test_notification_events.py` (26): **crear un ticket no avisa a nadie**; **asignar** (avisa al técnico y a los solicitantes, nombra al técnico, el técnico que se autoasigna no se avisa a sí mismo, el aviso apunta al ticket); **quitar a un técnico** (lo avisa salvo que se vaya él mismo, y un técnico quitado no recibe más avisos de estado); **escalar** (avisa al técnico que entra y al que sale, nunca a los solicitantes y sin copiar el motivo); **cambios de estado** (iniciar, esperar, reactivar, resolver —el solicitante recibe la petición de revisar, los técnicos el aviso de resuelto—, confirmar, rechazar, reabrir por un solicitante, cierre directo, un ticket sin técnicos, que el actor nunca se avise y que las asignaciones derivadas no avisen dos veces); que toda acción de estado figure en la tabla de avisos; **comentarios** (público del personal a los solicitantes, de un solicitante a los técnicos asignados, nota interna solo a los demás técnicos y sin copiar nunca el texto); un solicitante retirado no recibe nada; **un Solicitante nunca recibe actividad interna** (nota interna, escalamiento ni sus motivos); los avisos se revierten con la operación; y un título muy largo cabe en el aviso.
- `tests/test_seed_demo_tickets.py` (+2): `seed-demo-tickets` no deja avisos de la carga y no borra los de tickets que no creó.
- **Prueba de mutación** (script desechable): 26 mutaciones de `events.py`, los cuatro enganches y el seed (a quién se avisa, el actor, retirados y desasignados, la visibilidad de las notas, cada evento de la tabla, el recorte del título...). 24 se detectaron a la primera; las 2 que sobrevivían (un técnico desasignado que seguía recibiendo avisos y un seed que borraba avisos ajenos) señalaron huecos reales y se añadió su test.

Estado tras la entrega 5 de `v0.5.0` (centro de notificaciones):

```text
2955 tests passing
```

Los 123 tests nuevos cubren:

- `tests/test_notifications.py` (53): **el vocabulario** (todo evento tiene nombre e icono, los trece eventos que pide la fase, nombres distintos y qué se muestra de un evento que el vocabulario ya no tiene); **la base de datos** (un aviso nuevo nace sin leer y con fecha, lectura coherente, mensaje vacío o de solo espacios y saltos de línea, destinatario y ticket existentes, un aviso general sin ticket, que un usuario o un ticket con avisos no se eliminen y que exista el índice del listado); **el contenido no se reescribe** (ninguna columna de contenido se puede modificar por el ORM y la lectura sí); **crear** (`notify` guarda lo que recibe, acepta el evento como texto, devuelve el aviso ya volcado a la base, no hace commit, rechaza un evento desconocido, exige mensaje, los límites exactos de mensaje y título, un título en blanco queda vacío, un aviso rechazado no deja nada y un destinatario inactivo no recibe nada; `notify_many` avisa una sola vez a cada persona y omite a los inactivos); **consultar** (los contadores son por usuario, el listado muestra solo las propias de la más reciente a la más antigua, el desempate por id cuando comparten la fecha —también cuando el orden físico de las filas no coincide con el de los ids, para que un orden sin desempate no acierte por casualidad—, el filtro de no leídas, una página de veinte y el número de consultas fijo con tickets, y que la notificación de otra persona no existe); y **la lectura** (se fija la primera fecha y marcar de nuevo no la cambia, el contenido sobrevive a leerla, nadie marca la de otra persona, marcar todas toca solo las propias y **dos pestañas que marcan a la vez dejan una sola fecha de lectura**, con hilos).
- `tests/test_notifications_routes.py` (52): **acceso** (anónimo al login, los cuatro roles tienen el centro, la campana y la opción de menú, activa en sus pantallas); **el listado** (solo las propias, el estado visual y textual de las no leídas, evento, título, mensaje, fecha y ticket, el título que abre el ticket y el botón que solo marca, un aviso general sin nada que abrir, el HTML escapado, las pestañas con sus contadores y la activa marcada, cada formulario que conserva la pestaña y la página, filtro y página inválidos ignorados, una página más allá de la última, la paginación que conserva el filtro y «Marcar todas» solo si hay algo sin leer); **marcar como leída** (vuelve a donde estaba, 404 con la notificación de otra persona sin cambiar nada y con una inexistente, un GET no marca, la fecha es la de la primera vez y marcar todas toca solo las propias); **CSRF** (cada formulario lleva su token y las tres rutas lo exigen); **abrir** (marca y lleva al ticket, un aviso general vuelve al listado y abrir no concede acceso a un ticket que la persona no ve); **la campana** (JSON sin caché, sigue lo que se lee, sin número si no hay nada, «99+», solo las propias y actualizada en cada página) y **el script** (se sirve sin dependencias externas y la página lo carga).
- `tests/test_seed_demo_notifications.py` (18): los avisos de ejemplo respetan el vocabulario y el rol (el SLA no llega a un Solicitante), se crean para el equipo demo, apuntan solo a tickets que la persona ve, mezclan leídos y no leídos con fechas coherentes y antigüedades de minutos a días, volver a ejecutarlo no repite nada, una cuenta concreta sin distinguir mayúsculas ni espacios (y una que `seed-demo` no incluye), quien no ve tickets se informa y no recibe nada, una cuenta inexistente es un error que no crea nada, falta `seed-demo`, los avisos aparecen en el centro de esa persona y el comando informa lo que creó, acepta varias cuentas, avisa de quien no ve tickets, falla con una cuenta inexistente y se niega a ejecutarse en producción.
- `tests/test_layout.py`: las cuatro comprobaciones de la navegación por rol incluyen ahora **Notificaciones** (todos los roles la ven); se ajustaron porque describían el menú anterior, no para que pasen. `tests/test_route_protection.py` cubre las cinco rutas nuevas sin cambios (sesión obligatoria y CSRF en todas las POST); que la notificación de otra persona responda 404 lo comprueban los tests de `test_notifications_routes.py`.
- **Prueba de mutación** (un script desechable, no versionado): 87 mutaciones del modelo, el servicio, las rutas, las dos plantillas, el seed, el comando y la navegación —el filtro por usuario de cada consulta, la primera fecha de lectura, el guard de inmutabilidad columna por columna, los `CHECK`, los límites, el desempate del orden, el CSRF, los formularios que conservan el filtro, el contador de la campana...—. 78 se detectaron a la primera; las 8 que sobrevivían señalaron huecos reales (el volcado de `notify`, el desempate por id, el tamaño de página, la acción de abrir, el filtro y la página que conservan los formularios, la pestaña activa y el recorte de espacios en `--username`) y se añadieron los tests que las cubren. Queda **una equivalente**: usar el nombre de usuario sin pasarlo a minúsculas en la consulta del seed no cambia nada, porque la aplicación guarda siempre los usernames en minúsculas.

Estado tras la entrega 4 de `v0.5.0` (períodos de SLA):

```text
2832 tests passing
```

Los 64 tests nuevos cubren:

- `tests/test_sla_periods.py` (59): **al crear el ticket** (el período con los objetivos de la política, sus vencimientos en tiempo laboral —también un viernes por la tarde y fuera de horario—, una prioridad sin política, un ticket que gana SLA al pasar a una prioridad con política, que reconciliar de nuevo no cambia nada y que una creación fallida no deja períodos); **la pausa** (poner en espera cierra el período y abre uno pausado, reanudar abre otro con lo que queda, el tiempo en espera no cuenta ni en varios días, una política que no pausa y que los períodos nuevos heredan los objetivos aunque se edite la política); **cambios de prioridad (RN-88)** (se conserva lo consumido, quién y por qué, nacer vencido al subir, que un incumplimiento no se borra al bajar, nacer pausado, una prioridad sin política, cambiar la prioridad de un ticket resuelto y que un cambio posterior toma la política editada); **resolver, cerrar y reabrir** (el reloj se detiene, la reapertura sigue donde iba, cerrar directamente, resolver desde la espera y que las noches y fines de semana no consumen); **el calendario** (cada período se cierra con el reloj de su propio calendario); **la primera respuesta** (solo un comentario público del personal que sigue visible, no una nota interna, no el solicitante ni uno eliminado, y qué pasa con el vencimiento una vez respondida); **el estado del SLA** (dentro, próximo con el umbral exacto, vencido, pausado, sin umbral, la primera respuesta vencida por separado y un ticket sin SLA); **reconstrucción desde el historial** (da lo mismo que el cálculo en vivo para un recorrido de siete pasos, crea los períodos de un ticket que no tiene, reemplaza los existentes, el ticket manda si su estado no se explica por el historial, la selección por defecto y `--all`/`--ticket`, y que una respuesta posterior al inicio del período conserve su vencimiento); **restricciones de la base de datos** (un solo período vigente, los cerrados no cuentan, fin anterior al inicio, consumo negativo, objetivos no positivos y que una política con períodos no se elimine); **una carrera con hilos** (dos cambios de prioridad a la vez: uno cambia, el otro recibe el conflicto y quedan los períodos coherentes); y **los comandos** (`sla-status` con y sin SLA y con un ticket inexistente; `sla-rebuild` por defecto, con `--all`, con `--ticket` y rechazado en producción).
- `tests/test_seed_demo_tickets.py` (+5): todos los tickets demo tienen períodos que siguen su estado (resuelto o cerrado sin período vigente, en espera con uno pausado), la demostración muestra tickets dentro de plazo, vencidos y pausados, el primer período empieza cuando se creó el ticket, volver a ejecutar el seed deja los mismos períodos y estos siguen a los tickets a otro día.
- Los tests de tickets, de estados y de edición que ya existían no cambiaron: pasan con los períodos activos.
- **Prueba de mutación** (un script desechable, no versionado): 39 mutaciones del modelo, el servicio, los tres enganches, los comandos y el seed —el vencimiento que reinicia el reloj, la pausa, la herencia de condiciones, quién cuenta como respuesta, el incumplimiento que se borra, el umbral exacto, el calendario de cada período, la reconstrucción...— y los tests detectaron las 39. Una sobrevivió al principio (una respuesta posterior al inicio del período al reconstruir) y se añadió el test que la cubre.

Estado tras la entrega 3 de `v0.5.0` (políticas de SLA por prioridad):

```text
2768 tests passing
```

Los 260 tests nuevos cubren:

- `tests/test_sla_policies.py` (91): **los valores iniciales** (una política por prioridad con los valores documentados, que sigan las reglas de una política, que las prioridades más altas tengan objetivos más ajustados, que el seed informe lo que crea y sea idempotente, que no pise lo que el Administrador cambió ni reactive o duplique una política desactivada, que cree solo las que faltan y siga a la prioridad por su código y no por su nombre); **restricciones de la base de datos** (resolución y respuesta positivas, la respuesta que no supera la resolución, el umbral entre 1 y 100 con sus límites exactos, una sola política activa por prioridad pero con una desactivada conviviendo con otra activa, prioridad obligatoria y que una prioridad con política no se elimina); **las reglas de los valores** (`policy_problems`: la resolución obligatoria, mayor que cero y con su tope inclusivo; la primera respuesta, que no se compara con una resolución que ya está mal; el umbral; todos los problemas a la vez); **consultas** (las filas por nivel y no por orden de inserción, una prioridad sin política o inactiva, una sola consulta, el nombre vigente del estado en espera, la marca de la política); **definir y editar** (qué se crea y audita, solo se aplican y auditan los campos que cambiaron, sin cambios no se audita, un motivo en blanco, editar una política desactivada, que el servicio no hace commit y que un valor inválido no deja nada); **ediciones simultáneas** (una marca vieja, una desactivación o una definición ocurridas mientras la pantalla estaba abierta, una marca vacía o falsa, una copia de la sesión que otra transacción dejó vieja —se relee bajo el bloqueo—, y el índice único como última defensa); **desactivar y reactivar**; y **tres carreras con hilos** (dos Administradores que definen la misma política a la vez, que editan desde la misma pantalla y que desactivan: queda un solo resultado y una sola auditoría).
- `tests/test_sla_policy_forms.py` (87): **las duraciones** (treinta formas válidas, los números sueltos que piden la unidad, los decimales, lo que no es una duración, que los días no se admiten, que un número enorme se lee y se rechaza después y que escribir y leer son operaciones inversas hasta 60 001 minutos) y **el formulario** (conversión, todos los errores a la vez y junto a su campo, sin repetir un error, el texto demasiado largo que no se intenta leer, la marca de la política obligatoria, el motivo opcional, y los valores con que se abre, que vuelven a enviarse sin cambios).
- `tests/test_sla_policies_routes.py` (68): **acceso** (anónimo al login, los tres roles sin permiso reciben 403 en GET y POST en las tres pantallas sin cambiar nada, 404 con una prioridad inexistente, «Administración» sigue marcada); **la tabla en «SLA»** (los valores iniciales, el orden, los enlaces de cada fila, «Sin objetivo» y «Sin aviso», una prioridad sin política, una política desactivada atenuada, una prioridad inactiva, el título de la columna que sigue al renombrado del estado, sin prioridades y los nombres escapados); **el formulario** (abierto con lo vigente, para definir, de una política desactivada, la etiqueta de la pausa con el nombre vigente del estado) y **guardar** (editar con su auditoría, cada campo, sin cambios, definir, una política desactivada que sigue desactivada); **trece errores distintos señalados junto a su campo** que no guardan nada, que conserva lo escrito y todos a la vez; **una pantalla desactualizada** (vuelve con lo vigente y no guarda; una petición sin marca no se completa sola; una política definida mientras tanto no se crea dos veces) y los errores de regla del servicio; y **desactivar y reactivar** (la confirmación, el motivo opcional y su límite, y las acciones que ya no corresponden o sin política, también desde el GET).
- `tests/test_formatting.py` (+14): las duraciones («30 min», «1 h», «1 h 30 min», «1000 h»), «—» sin valor, que una duración negativa es un error y que el filtro `duration` está disponible en las plantillas.
- Ajustes por diseño, sin cambiar lo que comprueban: `tests/test_catalogs.py` (el diccionario de `seed_catalogs` incluye `politicas_sla` y el comando informa `políticas de SLA: N`) y `tests/test_route_authorization.py` (el recorrido de las áreas de administración ahora incluye `sla.`, que ya eran del Administrador pero no estaban cubiertas). `tests/test_route_protection.py` cubre las tres rutas nuevas sin cambios (sesión obligatoria y CSRF).
- **Prueba de mutación** (un script desechable, no versionado): 46 mutaciones del modelo, el servicio, el formulario, las rutas, las plantillas, el seed y el formateo —el conflicto de edición, el bloqueo de la prioridad, la relectura bajo el bloqueo, los límites, la auditoría, la autorización de cada pantalla, los valores del seed...— y los tests detectaron las 46. Antes de correrla se reforzaron dos tests que habrían dejado pasar un orden por id en lugar de por nivel y un texto largo ilegible señalado dos veces.

Estado tras la entrega 2 de `v0.5.0` (calendario laboral administrable):

```text
2508 tests passing
```

Los 207 tests nuevos cubren:

- `tests/test_worktime.py` (+67, 167 en total; unitarios, sin base de datos): **el motor con franjas por día**. `schedule_problems` y `from_schedule` (franjas sin ninguna, de un día que no existe, que terminan antes de empezar o solapadas; contiguas válidas; el orden en que llegan no importa), que una franja por día se comporta igual que un `WorkCalendar`, `is_working_time`, y cada operación con una pausa de almuerzo (pasar al horario laboral, el último minuto, avanzar horas, medir y sumar, con los bordes en el inicio y el fin de cada franja). Además, dos horarios (uno con almuerzo y otro deliberadamente incómodo, con un martes de un solo minuto, un día sin trabajo, una franja que empieza a medianoche y feriados) se comparan con el recuento minuto a minuto y cumplen que medir y sumar son operaciones inversas, que nada cae fuera de las franjas y que las mediciones suman igual sin importar cómo se divida el intervalo.
- `tests/test_work_calendar.py` (96): **el calendario por defecto** (qué se usa sin nada guardado y que sigue la zona de la aplicación); **guardar** (la versión 1, que cada guardado crea una versión nueva y deja la anterior exactamente como estaba, que una versión antigua sigue construyendo su reloj, los días ISO en la base, que guardar tal cual el calendario por defecto es válido, feriados ordenados y recortados, que el servicio no hace commit); **sin cambios, conflicto y reglas** (guardar lo mismo no crea nada, el orden de franjas y feriados no es un cambio y cualquier diferencia sí, una versión base obsoleta o del futuro es un conflicto, once datos inválidos que no dejan nada pendiente, los límites exactos, un usuario inactivo); **auditoría** (la primera versión se compara con el calendario por defecto y las siguientes solo registran las secciones que cambiaron); **descripciones** (días seguidos que comparten horas, el resumen, el historial de versiones en tres consultas); **restricciones de la base de datos** (una sola versión vigente, versión única y positiva, día de la semana de 1 a 7, inicio anterior al fin, sin repetir franja ni feriado, nombre de feriado no vacío, una versión con filas no se elimina); **los textos del formulario** (franjas de un día y feriados, con sus formas válidas y cada error con su línea) y **dos carreras con hilos** (dos Administradores que guardan la primera versión a la vez, y dos que guardan sobre la misma versión: en ambos casos queda una sola versión nueva y el otro recibe el conflicto).
- `tests/test_work_calendar_routes.py` (37): **acceso** (anónimo al login, los tres roles sin permiso reciben 403 en GET y POST sin guardar nada, el hub enlaza la pantalla y «Administración» sigue marcada); **«SLA»** (el calendario por defecto, uno guardado con su horario, su zona y sus feriados, solo los cinco próximos, el historial de versiones, el HTML de un nombre de feriado escapado); **el formulario** (abierto con lo por defecto y con lo guardado, abrirlo no guarda nada, la lista de zonas, guardar la primera versión y las siguientes, la auditoría con quién y por qué, sin cambios no se crea nada, una pantalla desactualizada vuelve con lo vigente y no guarda, una petición sin versión se rechaza en lugar de completarse sola, doce errores distintos señalados junto a su campo, que conserva lo escrito, que rechaza un calendario sin días laborales y que informa todos los errores a la vez).
- `tests/test_seed_demo_tickets.py` (+7): el seed respeta un calendario guardado (franjas, feriados y días sin trabajo), usa su zona horaria y cuenta «hoy» en ella (con una hora de referencia en la que Santiago y Bogotá no coinciden en la fecha), un calendario explícito sigue ganando, una hora de creación que cae en una pausa pasa al siguiente momento de trabajo, refrescar con un calendario guardado mantiene todo en horario laboral y la validación no compara la hora de cada ticket con una jornada única cuando no la hay.
- Ajustes por diseño, sin cambiar lo que comprueban: `tests/test_layout.py` (la tarjeta «SLA» del hub ya está enlazada) y `tests/test_worktime.py` (los atributos `start` y `end` del reloj desaparecieron: un test usa ahora `is_working_time` y el recuento minuto a minuto entiende franjas). `tests/test_route_protection.py` y `tests/test_route_authorization.py` cubren las dos rutas nuevas sin cambios (sesión obligatoria, CSRF y solo Administrador).

Estado tras la entrega 1 de `v0.5.0` (motor de tiempo laboral compartido):

```text
2301 tests passing
```

Los 100 tests nuevos están en `tests/test_worktime.py`, son unitarios y no usan la base de datos. Cubren:

- **el calendario:** el calendario por defecto, el formato HH:MM, cada problema que detecta `calendar_problems` y que `BusinessClock` se niega a construirse con un calendario inválido;
- **los días:** los días laborales, los feriados, otro día de la semana como laboral y `workdays_before` (fines de semana, contando desde un domingo y con feriados);
- **pasar al horario laboral** (`into_business` y `latest_before`): dentro de la jornada, justo al abrir y al cerrar, antes de abrir, por la noche y en fin de semana;
- **avanzar horas** (`add_hours`): terminar justo al cierre pasa a la apertura siguiente, empezar fuera de la jornada, fines de semana, feriados, la fracción de segundo y que el resultado nunca cae fuera del horario;
- **medir** (`business_seconds_between`): las noches, los fines de semana y los feriados no suman, la fracción de segundo se descarta, tres años enteros de días laborales, una comparación con un recuento minuto a minuto (con dos calendarios) que no comparte ninguna idea con el motor, y que las mediciones suman lo mismo sin importar cómo se divida el intervalo;
- **sumar** (`add_business_seconds`): un plazo que se cumple justo al cierre vence a la hora de cierre (a diferencia de `add_hours`), con 0 segundos no se mueve, no admite cantidades negativas, sumar en dos pasos equivale a sumar de una vez y medir y sumar son operaciones inversas (el resultado es además el primer instante en que se cumple);
- **zonas horarias:** las fechas en UTC se convierten a la zona del calendario, el resultado queda en esa zona, las fechas sin zona se rechazan y un fin de semana con cambio de horario de verano no mueve la jornada.

`tests/test_seed_demo_tickets.py` cambia una sola línea (importa `WorkCalendar` desde `worktime`) y ninguna comprobación se tocó: el seed sigue produciendo las mismas fechas.

Estado tras la entrega 12 de `v0.4.0` (estados y transiciones, y cierre de la versión):

```text
2201 tests passing
```

Los 160 tests nuevos cubren:

- `tests/test_states_admin.py` (69): **estados** (los seis en el orden del flujo, cuántos tickets hay en cada uno, renombrar cambia solo lo visible y audita solo los campos que cambiaron, guardar sin cambios no audita, una descripción en blanco queda vacía, el nombre no puede repetirse sin distinguir mayúsculas pero un estado conserva el suyo con otra capitalización, los límites exactos, que el servicio no hace commit y **dos Administradores que renombran al mismo nombre a la vez dejan uno solo**); **transiciones** (agrupadas por origen en el orden del flujo, cuáles son esenciales y cuáles opcionales, quién ejecuta cada acción, deshabilitar y volver a habilitar, la razón de cada protección, que la única entrada a un estado y la última salida no se pueden deshabilitar, que llegar a un estado solo volviendo atrás no cuenta, que un flujo ya roto no bloquea cambios ajenos, **dos Administradores que a la vez rompen el flujo entre los dos**, **dos que cambian la misma transición a la vez y solo uno la cambia y la audita**, que una transición deshabilitada deja de ofrecerse a los tickets y el servidor la rechaza, y que listarlas no consulta por fila); y **pantallas** (solo el Administrador, 404 con ids desconocidos, el hub enlaza la pantalla, el formulario precargado y sus validaciones, que no acepta un código ni un orden, que un estado renombrado se ve en todas partes menos en el historial antiguo, que la descripción es la ayuda de la etiqueta, las confirmaciones con los nombres vigentes, las protegidas no se pueden deshabilitar ni por la pantalla y que «Administración» sigue marcada en el menú).
- `tests/test_state_actions.py` (15): el catálogo de acciones es coherente: cada acción está descrita exactamente una vez, tiene un nombre neutro y un identificador de URL único, las esenciales y las que devuelven atrás pertenecen al vocabulario, los textos no escriben a mano ningún nombre de estado, una descripción se completa con el nombre del destino y **los roles declarados de cada acción coinciden con su política de autorización** (los cuatro roles).
- `tests/test_route_authorization.py` (13): recorre el mapa de rutas real. Un Solicitante ajeno recibe 404 en cualquier ruta de un ticket, con cualquier método; un solicitante del ticket solo usa las rutas declaradas en `REQUESTER_ENDPOINTS` (el resto responde 403) y esas sí responden; las áreas de administración son del Administrador, y `/groups` del Administrador y el Supervisor. Tres pruebas comprueban que el propio recorrido detecta una ruta sin comprobar la propiedad, una del personal abierta a Solicitantes y una de administración sin comprobar el rol.
- `tests/test_ticket_history.py` (61): todo evento del vocabulario tiene su descriptor, un evento desconocido no dice nada, qué cuenta cada uno de los 23 y que ninguna línea repite un motivo ni el texto de un comentario.
- `tests/test_seed_demo_tickets.py` (+2): el comando se detiene antes de cargar nada si hay transiciones deshabilitadas que la demostración necesita, y renombrar los estados no la afecta. `tests/test_layout.py` actualiza la prueba del hub (la tarjeta «Estados y transiciones» ya está enlazada).
- Ajustes sin cambiar lo que comprueban: `tests/test_ticket_state_transitions.py` y `tests/test_ticket_resolution.py` importan el catálogo desde `tickets/state_actions.py`; `tests/test_tickets_routes.py` apunta al módulo `routes.creation`; y ocho archivos de tests usan `ticket_by_public_id` (y tres, `person`) de `tests/ticket_helpers.py` en lugar de sus copias.

Estado tras la entrega 11 de `v0.4.0` (bloqueo temporal de edición):

```text
2041 tests passing
```

Los 59 tests nuevos (`tests/test_ticket_edit_lock.py`) cubren: **configuración** (120 s y 45 s por defecto; la aplicación no arranca con tiempos cero o negativos ni con un latido igual o mayor que la duración); **base de datos** (un solo bloqueo no liberado por ticket, los liberados no cuentan, y los `CHECK` de tiempos); **adquirir** (crea el bloqueo por el tiempo configurado, renovar es adquirir otra vez, otra persona no puede tomar uno vigente, uno expirado se libera de forma lógica y se reemplaza, el propio expirado que nadie tomó se renueva, un bloqueo por ticket, usuario inactivo, el servicio no hace commit); **liberar** (libera para otra persona, nunca toca el de otra, sin bloqueo no es error); **consultar** (solo cuenta el vigente y no modifica nada); **concurrencia con hilos** (dos personas que abren a la vez obtienen un único bloqueo, y dos que toman uno expirado también); y **pantallas** (abrir bloquea y trae lo que necesita el script, otra persona ve quién edita en una pantalla de solo lectura, guardar mientras otra edita no cambia nada, guardar libera, guardar tras expirar sin que nadie lo tome funciona y tras tomarlo otra persona se rechaza, un conflicto de versión o un error de validación no liberan, editar y cambiar la prioridad comparten el bloqueo, los demás cambios no se bloquean, un ticket cerrado y un Solicitante no bloquean, 404 sin acceso; los endpoints de renovar y liberar —JSON, 409 si es de otra persona o está cerrado, 403 al Solicitante, solo POST, nunca liberan el de otra persona—; el aviso del detalle solo para el personal que podría editar y que desaparece al expirar; y el script, servido y sin dependencias externas). `tests/test_route_protection.py` cubre las dos rutas nuevas sin cambios (sesión obligatoria y CSRF).

Estado tras la entrega 10 de `v0.4.0` (relaciones y duplicados):

```text
1982 tests passing
```

Los 116 tests nuevos cubren:

- `tests/test_ticket_relations.py` (95): **catálogo y políticas** (los dos tipos, simétrica o no; los eventos son internos y tienen nombre; solo el personal gestiona relaciones y un usuario inactivo no); **base de datos** (rechaza un ticket relacionado consigo mismo, un par repetido **también invertido**, y una desactivación incoherente; tipos distintos pueden unir el mismo par y una relación quitada admite una nueva); **número de ticket** (`12`, `#12`, espacios y ceros; todo lo demás se rechaza); **relacionar** (par normalizado desde cualquier lado, un evento interno solo en el ticket que actúa, no sube la versión ni «Actualizado», se lista desde los dos tickets, no consigo mismo ni dos veces ni a la inversa, ticket inexistente, comentario con límite exacto, un ticket cerrado no actúa pero puede ser el otro lado, actor inactivo, el servicio no hace commit); **quitar** (eliminación lógica con quién y cuándo, se puede volver a establecer, desde cualquiera de los dos tickets, ids ajenos o ya quitados, ticket cerrado, **dos personas que la quitan a la vez la quitan una sola vez**); **marcar un duplicado** (cierra con `DUPLICADO` con fecha, motivo y quién, el principal queda intacto, el historial deja la relación y luego el cierre, desde los cuatro estados abiertos, no desde Resuelto ni Cerrado, el principal puede estar en cualquier estado, no consigo mismo ni ticket inexistente, **sin cadenas ni ciclos** en ningún sentido, no se marca dos veces, un principal con varios duplicados, no transfiere nada, versión caducada, nada queda a medias si falla, **dos duplicados opuestos a la vez no se bloquean y solo uno prospera**, la relación de un duplicado cerrado no se quita y la de uno reabierto sí); **historial** (el Solicitante nunca recibe los eventos, líneas legibles); y **pantallas** (el Solicitante recibe 403 en todas y 404 si no ve el ticket, la tarjeta y la pantalla solo para el personal, relacionar con sus avisos, confirmación para quitar, la pantalla de duplicado, conservar lo escrito ante un error, conflicto de versión, qué ve el Solicitante de un duplicado cerrado —que se cerró como duplicado, pero no de cuál ni la nota—, ticket cerrado, ticket Resuelto, menú «Tickets» y que cargar las relaciones es **una sola consulta**).
- `tests/test_seed_demo_tickets.py` (+21): validación de los pasos nuevos (claves anteriores y más antiguas, no repetir, duplicado solo y sin `estado`, un ticket cerrado solo admite reabrirlo, no cadenas, solo el personal), que los datos cubran duplicados, un principal con dos duplicados y una relación, el historial igual al de la aplicación, el principal intacto, las fechas de cada relación con las de su evento (y el cierre del duplicado con el suyo), lo que ve cada rol, el refresco y una eliminación hecha a mano, y que el comando pida `seed-catalogs` si faltan los tipos. Las instantáneas incluyen ahora las relaciones.
- `tests/test_catalogs.py`: el diccionario de `seed_catalogs` incluye `tipos_relacion`.

Estado tras la entrega 9 de `v0.4.0` (resolución, cierre y reapertura):

```text
1866 tests passing
```

Los 136 tests nuevos cubren:

- `tests/test_ticket_resolution.py` (107): **constantes y configuración** (los códigos de estado de las políticas coinciden con el catálogo, `REOPEN_WINDOW_DAYS` vale 30 y la aplicación no arranca con 0 o negativo, los cinco eventos son públicos y tienen nombre); **políticas** (resolver y cerrar por rol, solo Supervisor y Administrador cierran de forma excepcional, solo un solicitante vigente valida —no otro Solicitante, ni el creador que no figura como solicitante, ni uno retirado, ni el personal—, la reapertura del personal sin límite y la del solicitante solo con el ticket Cerrado y dentro del plazo, con el límite exacto y la configuración); **base de datos** (`validaciones` rechaza un tipo inválido, un ciclo 0, un rechazo sin motivo y un duplicado en el mismo ciclo, pero admite el ciclo siguiente); **resolver** (desde los cuatro estados abiertos, evento público con el ciclo, texto opcional con límite de 2000 exacto, no se resuelve dos veces, conserva a los técnicos, conflicto de versión); **cierre directo** (desde los cuatro estados, evento propio con la acción y el motivo, cancelación, motivos de otros caminos rechazados, motivos inactivos o desconocidos, no desde Resuelto, el motivo solo en el cierre directo); **confirmar** (cierra con `RESOLUCION_VALIDADA`, registra la validación y los dos eventos en orden, basta uno de varios solicitantes, solo un solicitante vigente, funciona aunque el motivo esté desactivado, **dos solicitantes a la vez cierran una sola vez**); **rechazar** (exige explicar, limpia la resolución, deja la validación y los dos eventos, conserva a los técnicos, cada resolución abre un ciclo nuevo y la primera explicación sobrevive); **cierre excepcional** (Supervisor, motivo obligatorio, solo desde Resuelto, un Técnico no, y el ticket sin solicitante); **reabrir** (limpia el cierre y conserva el historial y los técnicos, el personal sin límite, el solicitante solo dentro del plazo, un ticket abierto no se reabre, un ticket cerrado rechaza todo lo demás, se puede resolver y cerrar de nuevo); la **regla del cierre en los tres caminos** (cerrado siempre con fecha y motivo, abierto nunca con datos de cierre); el **historial** (el Solicitante recibe los cinco eventos, líneas legibles); y las **pantallas** (botones del Técnico, resolver con su tarjeta y su fecha, límite del texto, los dos motivos del cierre directo, cancelación, aviso de validación solo para un solicitante vigente, confirmar, rechazar con su explicación, qué ve cada rol del motivo del rechazo y de las notas de cierre, 403 y 404 en cada pantalla, cierre excepcional, reapertura por el personal y por el solicitante dentro y fuera del plazo, conflicto de versión).
- `tests/test_seed_demo_tickets.py` (+31): validación de los pasos nuevos (quién ejecuta cada acción, textos obligatorios y límites, motivos de cierre, transiciones inexistentes, un ticket cerrado solo admite reabrirlo), que los datos cubran los seis caminos, el historial de cada ticket nuevo, las fechas de resolución, cierre y validación con las de sus eventos, lo que ve cada rol, y el refresco de esas fechas (también un cierre y una reapertura hechos a mano). Las instantáneas incluyen ahora la resolución, el cierre y las validaciones.
- `tests/test_ticket_state_transitions.py` (-2, ajustes por diseño): las acciones disponibles por estado incluyen resolver y cerrar y un ticket Resuelto o Cerrado ofrece reabrir; ahora están implementadas todas las acciones salvo las derivadas y la del sistema; el detalle de un ticket Resuelto o Cerrado ofrece solo reabrir. Se cambiaron esas comprobaciones porque describían el alcance anterior, no para que pasen.

Estado tras la entrega 8 de `v0.4.0` (adjuntos):

```text
1730 tests passing
```

Los 95 tests nuevos cubren:

- `tests/test_ticket_attachments.py` (83): **almacenamiento** (nombres depurados que nunca son una ruta, lista blanca de extensiones, contenido que debe coincidir con la extensión, MIME declarado ignorado, nombre físico UUID y SHA-256 por bloques, límite de tamaño exacto sin dejar restos, archivo vacío, rutas que no pueden salir de la raíz); **modelo y configuración** (límites mayores que cero, valores por defecto y almacenamiento fuera de `static/`, eventos internos por defecto, restricciones de la base de datos); **servicio** (metadatos y evento público o interno según el comentario, partes vacías del formulario, máximo por envío y por ticket contando solo los activos, un archivo malo no deja restos, ticket cerrado, actor inactivo, compensación con `discard_files`, eliminación lógica que conserva el archivo); **visibilidad** (el Solicitante nunca recibe el adjunto de una nota, un comentario eliminado oculta los suyos, **la condición SQL coincide con la política `can_view_attachment`** para todos los perfiles, y los eventos de archivos de una nota no llegan al Solicitante); y **pantallas** (subir y descargar con `attachment`, `nosniff` y sin caché, avisos, tamaño excedido, 413, 404 sin acceso o entre tickets, archivo físico ausente o ruta manipulada, comentario con archivos y comentario con un archivo malo que conserva el texto, ticket cerrado, nombres escapados y eliminar con su plazo).
- `tests/test_seed_demo_tickets.py` (+11): validación del `adjunto`, que cuelgue del comentario correcto y exista en disco con su hash, la descarga del Solicitante, las fechas de cada archivo con las de su evento y tras un refresco, que volver a ejecutar no duplique archivos y que una eliminación hecha a mano siga al refresco. Las instantáneas incluyen los adjuntos.
- `tests/test_layout.py` (+1 caso). `tests/conftest.py`: la fixture `app` usa un directorio temporal para `UPLOADS_DIR`, sin tocar la protección de `workdesk_test`.

Estado tras la entrega 7 de `v0.4.0` (comentarios y notas internas):

```text
1635 tests passing
```

Los 130 tests nuevos cubren:

- `tests/test_ticket_comments.py` (86): **vocabulario y configuración** (los tres eventos son internos por defecto y tienen nombre; la aplicación no arranca con un plazo de edición menor o igual a cero; el plazo por defecto es 30 minutos); **base de datos** (rechaza un tipo desconocido, un contenido vacío, un comentario activo con datos de eliminación, uno eliminado sin fecha y uno editado sin fecha de modificación); **servicio** (comentario público con su evento público y nota interna con su evento interno, sin subir la versión ni tocar «Actualizado», contenido recortado y con los saltos de línea unificados, vacío y de más de 5000 caracteres, tipo desconocido, ticket cerrado, actor inactivo, que no hace commit; editar con el contenido anterior en el historial, sin cambios, el tipo que no cambia, ids inexistentes, de otro ticket o eliminados; eliminar de forma lógica, que ya no se lista a nadie y que no se puede eliminar dos veces); **consultas y visibilidad** (orden, el Solicitante nunca recibe las notas, `get_comment` oculta notas y comentarios de otros tickets, **la condición SQL coincide con la política `can_view_comment`** para los seis perfiles más un usuario inactivo y uno anónimo, y una sola consulta por lista); **historial** (el Solicitante solo recibe los eventos del comentario público, las líneas indican el tipo y nunca el texto); **concurrencia con hilos** (dos ediciones se aplican una tras otra y dos eliminaciones, una sola); y **pantallas** (publicar como Solicitante y como personal, avisos por tipo, tipo por defecto, **un Solicitante no puede escribir una nota interna ni enviándola a mano (403)**, 404 sin acceso o para tickets inexistentes, errores del formulario con lo escrito conservado, HTML escapado y saltos de línea conservados, ticket cerrado sin formulario, que el Solicitante no recibe la nota en ninguna forma —ni texto, ni marcas, ni historial, ni conteo, ni sus pantallas—, que el personal la ve marcada, que el historial no filtra el texto anterior, el selector de tipo según el rol, editar y eliminar con sus plazos, la configuración del plazo, quién puede abrir la edición de comentarios ajenos y los enlaces según los permisos).
- `tests/test_ticket_policies.py` (+25): `can_write_internal_note`, `can_comment_publicly`, `can_view_comment`, `can_edit_comment` (plazo, límite exacto, configuración, autor y terceros, Supervisor y Administrador sin plazo, nota interna del Solicitante) y `can_delete_comment`, que sigue la misma regla; y que `INTERNAL_COMMENT_TYPE` coincida con el modelo.
- `tests/test_seed_demo_tickets.py` (+17): validación de los pasos de comentarios (quién puede comentar, límites, texto), que los datos cubran los casos, el historial de una conversación igual que el de la aplicación, que los comentarios no modifiquen el ticket, la fecha de cada comentario con la de su evento, lo que ven el Solicitante y el personal, el refresco de esas fechas y que una edición y una eliminación hechas a mano sigan al refresco en orden. Las instantáneas de fechas y de contenido incluyen ahora los comentarios.
- `tests/test_layout.py` (+2 casos): las pantallas de editar y eliminar un comentario marcan «Tickets». `tests/test_route_protection.py` cubre las tres rutas nuevas sin cambios.

Estado tras la entrega 6 de `v0.4.0` (solicitantes del ticket):

```text
1505 tests passing
```

Los 73 tests nuevos cubren:

- `tests/test_ticket_requesters.py` (45): **vocabulario** (los dos eventos son internos y tienen nombre); **servicio** (agregar con su evento interno y sin subir la versión ni tocar «Actualizado», el personal de cada rol, solo usuarios activos con rol Solicitante, duplicados, ticket cerrado, actor inactivo, que no hace commit, que agregar y retirar en una misma transacción respeta el `CHECK` de fechas, que quien abrió la edición antes del cambio guarda sin conflicto y los candidatos; retirar conserva la participación con quién y cuándo, con y sin motivo, dejar un ticket sin solicitantes, volver a agregar con una fila nueva, ids inexistentes, de otro ticket o ya retirados, motivo de 500 y 501 caracteres); **concurrencia con hilos** (dos altas de la misma persona producen una sola participación vigente y dos retiros, uno solo); **quién ve el ticket** (quien se agrega lo ve —con su historial público completo— y quien se retira deja de verlo en el detalle y en el listado, el creador lo conserva, **la condición SQL coincide con la política `can_view_ticket` tras agregar, retirar y volver a agregar** para los seis perfiles, y la búsqueda del personal por solicitante sigue a los cambios); **historial** (el Solicitante no recibe los eventos ni los nombres de otros solicitantes ni el motivo, tampoco en la consulta; el personal los ve con su motivo; líneas de `describe_history_changes` sin el motivo); y **pantallas** (403 al Solicitante en las cuatro rutas, 404 para tickets ajenos o inexistentes, la pantalla por rol, mensajes cuando no hay solicitantes o nadie que agregar, agregar y sus validaciones, confirmación antes de retirar, aviso del creador, motivo largo, ticket cerrado, solicitante inactivo marcado y aun así retirable, enlace «Gestionar» solo para el personal y con el ticket abierto).
- `tests/test_seed_demo_tickets.py` (+20; uno de ellos es la regresión de un escalamiento hecho a mano cuyo refresco violaba el `CHECK` de fechas de `tickets_tecnicos`, un fallo de la entrega 5): validación de los pasos de solicitantes (roles, quién es solicitante en cada momento, retirar y agregar a la misma persona, motivo del retiro), que los datos cubran los cuatro casos, el historial de cada ticket nuevo igual que el de la aplicación (retirar antes de agregar, marca del seed, sin versión ni fecha de modificación), las fechas de asociación y retiro con las de sus eventos, el creador que sigue viendo su ticket, el solicitante retirado que lo pierde, los eventos solo para el personal, el refresco de esas fechas y que los cambios hechos a mano sigan al refresco en orden. Ajustes por diseño de tests existentes: las instantáneas de fechas y de contenido incluyen el retiro; «los tickets siguen las reglas de creación» y «un solicitante demo solo ve sus tickets» calculan los solicitantes con los cambios de cada ticket; y la comprobación de la fecha de modificación pasó de «existe si hay ajustes» a la regla de la aplicación (`version > 1` si y solo si hay fecha de modificación, que es la de uno de sus eventos).
- `tests/test_ticket_policies.py` (+6): `can_manage_requesters` por rol, usuarios inactivos y anónimos, y que siga la misma regla que `can_choose_requesters`. `tests/test_layout.py` (+2 casos): las dos pantallas marcan «Tickets».
- `tests/test_route_protection.py` cubre las tres rutas nuevas sin cambios (sesión obligatoria y CSRF).

Estado tras la entrega 5 de `v0.4.0` (asignación):

```text
1432 tests passing
```

Los 92 tests nuevos cubren:

- `tests/test_ticket_assignment.py` (68): **servicio** (asignar mueve un ticket `Nuevo` a `Asignado` con su evento derivado, más técnicos y otros estados no cambian el estado ni la versión, transición deshabilitada, autoasignación, solo Técnicos activos, duplicados, ticket cerrado, usuario inactivo, que no hace commit, candidatos; quitar conserva la asignación, el último técnico devuelve a `Nuevo`, ids ajenos o ya quitados, motivo largo; grupo: fijar, quitar, mismo grupo, grupos inactivos y desconocidos, el actual desactivado se conserva, versión caduca y ticket cerrado; escalar: grupo, técnico que reemplaza, ambos, necesidad de un cambio real y de motivo, grupos y técnicos inválidos, versión y ticket cerrado) y **concurrencia con hilos** (dos autoasignaciones del mismo técnico producen una sola, y dos técnicos a la vez pasan el ticket a `Asignado` una sola vez); **visibilidad** (el Solicitante ve «Atendido por» y el técnico asignado pero ni el grupo ni el escalamiento ni su motivo; el personal lo ve todo; sin asignar; técnico inactivo); y **pantallas** (autoasignarse y dejar el ticket, solo Técnicos, un Técnico solo se quita a sí mismo, 403 a Técnicos y Solicitantes en las pantallas de gestión, 404 para tickets ajenos en todas las rutas, asignar y quitar como Supervisor y Administrador, validaciones, grupo con conflicto de versión, ticket cerrado, botones por rol, opción «Tickets» marcada y la pantalla y el formulario de escalamiento).
- `tests/test_seed_demo_tickets.py` (+16): validación de `grupo` y `asignar` (grupo desconocido, quién fija el grupo, técnico inválido, quién asigna a otra persona), la simulación del estado derivado, que los datos cubran grupo sin técnico, dos técnicos, autoasignación y asignación por un Supervisor, el historial igual al de la aplicación, que cada asignación lleve la fecha de su evento, lo que ven el Solicitante y el personal, un grupo que falta solo avisa, el refresco de fechas de las asignaciones (incluida una desasignación hecha a mano) y que refrescar no toca grupo ni técnicos. `final_state` tiene en cuenta que asignar pasa el ticket a `Asignado`, ya alcanzable en los datos, y `prepare` carga los grupos de `seed-demo`.
- `tests/test_ticket_policies.py` (+6): `can_assign_self` y `can_manage_assignments` por rol, usuarios inactivos y anónimos. `tests/test_layout.py` (+2 casos): asignación y escalamiento marcan «Tickets».

Estado tras la entrega 4 de `v0.4.0` (grupos):

```text
1340 tests passing
```

Los 116 tests nuevos cubren:

- `tests/test_groups.py` (109): **base de datos** (nombre único sin distinguir mayúsculas, miembro y responsable únicos mientras estén vigentes pero con posibilidad de volver, y que un cierre no preceda al inicio); **políticas** por rol, para anónimos e inactivos, el supervisor responsable (vigente, retirado, otro supervisor, otro grupo) y **la condición SQL equivalente a la política** para los cinco perfiles; **servicio** (alta con auditoría, nombre obligatorio y repetido, carrera de nombre con savepoint, edición de solo lo cambiado, sin cambios sin auditar, desactivar y reactivar conservando miembros y responsables, agregar y retirar técnicos con su historial, solo técnicos y supervisores activos, duplicados y carreras, grupos desactivados, candidatos, listados por rol y por estado y que el listado no consulte por grupo); **ganchos de usuarios** (cambio de rol de técnico y de supervisor, desactivación, que reactivar no restaure y el contador de cierres); y **pantallas** (403 al Técnico y al Solicitante, 404 a un Supervisor ante grupos ajenos, el Supervisor sin acceso a editar, desactivar ni a los responsables, ids de otro grupo que no sirven para retirar, alta y edición con sus validaciones, confirmaciones con motivo, formularios de agregar y designar, grupo sin responsable ni técnicos, escape de HTML, filtros, navegación del Supervisor y tarjeta del hub).
- `tests/test_seed_demo.py` (+5): los tres grupos de demostración con sus miembros y responsables, que usen solo técnicos y supervisores del equipo, auditoría como acción del sistema, idempotencia sin tocar un grupo existente y que un supervisor demo vea solo los suyos. El test que comprobaba que toda la auditoría de `seed-demo` eran altas de usuario se acotó a las entradas de usuario, porque el comando ahora también crea grupos.
- `tests/test_layout.py` (+2 casos y un test dividido): el Supervisor ve **Grupos** en su menú, los grupos cuelgan de Administración para el Administrador y el hub enlaza con `/groups`.
- `tests/test_route_protection.py` cubre las rutas nuevas sin cambios.

Estado tras la entrega 3 de `v0.4.0` (estados y transiciones):

```text
1224 tests passing
```

Los 103 tests nuevos cubren:

- `tests/test_ticket_state_transitions.py` (75): **tabla y seed** (20 transiciones, la matriz de `docs/08` comprobada por propiedades —cierre directo nunca desde Resuelto, Cerrado solo sale reabriendo, la espera solo se entra desde En progreso, solo los seis estados—, todas las acciones del vocabulario presentes, idempotencia sin pisar una transición deshabilitada, salida del comando, unicidad por (origen, destino, acción) y que una transición no vaya de un estado a sí mismo); **acciones disponibles** por estado y por rol, destino, transición deshabilitada y que solo estén implementadas las tres operativas; **servicio** (iniciar, el ciclo completo con la versión subiendo cada vez, esperar con y sin motivo, con texto libre y sus reglas, motivo inactivo o inexistente, acciones que no admiten motivo, transiciones inválidas desde cada estado, acciones sin implementar, ticket cerrado, versión caduca, usuario inactivo, que no hace commit y **dos hilos que actúan a la vez producen una sola transición**); **pantallas** (los tres roles del personal, pantalla de confirmación, motivos activos en la de espera, motivo y texto visibles solo para el personal, 403 al Solicitante, 404 para tickets ajenos, acciones desconocidas, acción que ya no corresponde, ticket cerrado, conflicto de versión, versión ausente, validaciones del formulario y que se conserve lo escrito); y **detalle** (el botón correcto por estado y ninguno para Resuelto, Cerrado ni el Solicitante, y la opción "Tickets" marcada).
- `tests/test_seed_demo_tickets.py` (+20 netos): validación de los pasos de estado y de los motivos, los datos cubren los tres estados alcanzables hoy, los cinco motivos de espera, un ciclo completo y un texto libre; el historial queda igual que el de la aplicación (versión, actor, marca, motivo y texto); el Solicitante no ve el motivo y el personal sí; falta de transiciones o de un motivo de espera; y que refrescar no toca estado ni versión. `test_tickets_follow_the_creation_rules` ya no espera `Nuevo` en todos: calcula el estado final de cada ticket demo a partir de sus ajustes.
- `tests/test_ticket_policies.py` (+5): `can_change_state` en las tres comprobaciones que ya cubrían editar y cambiar la prioridad. `tests/test_layout.py` (+3 casos): Editar, Cambiar prioridad y Cambiar estado marcan "Tickets". `tests/test_catalogs.py`: el diccionario de `seed_catalogs` incluye `transiciones`.
- `tests/test_tickets_edit_service.py`: solo cambia el módulo desde el que importa `TicketClosedError` y `TicketConflictError` (ahora `tickets/versioning.py`), sin tocar ninguna comprobación.

Estado tras la entrega 2 de `v0.4.0` (catálogo de motivos de espera):

```text
1121 tests passing
```

Los 72 tests nuevos están en `tests/test_wait_reasons.py` (más dos ajustes por diseño: el diccionario que devuelve `seed_catalogs` en `test_catalogs.py` y la lista de tarjetas enlazadas del hub en `test_layout.py`). Cubren:

- **Seed y modelo:** los cinco motivos en orden, solo `OTRO` admite texto libre, idempotencia sin pisar cambios de un Administrador, salida del comando `seed-catalogs`, nombre único sin distinguir mayúsculas, código opcional y único, y valores por defecto.
- **Servicio:** alta (recorte, creador y auditoría con `entidad_tipo` `motivo_espera`), nombre repetido, edición de solo lo cambiado, edición sin cambios sin auditar, que ningún motivo esté protegido (se pueden desactivar todos), desactivar y reactivar con auditoría, y orden y filtro del listado.
- **Historial:** un evento puede referenciar un motivo (`wait_reason`), los demás eventos lo dejan vacío, desactivar un motivo no afecta a lo ya registrado y la base impide eliminar uno en uso.
- **Pantallas:** acceso (anónimo a login, los tres roles sin permiso reciben 403 en GET y no pueden cambiar nada por POST, ids inexistentes 404, CSRF), enlace en el hub, listado con la columna "Texto libre" y sin acciones protegidas, filtro, escape de HTML, alta con y sin la casilla, validaciones (nombre obligatorio y repetido, orden y largos), edición precargada, edición que desmarca la casilla, edición sin cambios, y desactivar/reactivar.

Estado tras la entrega 1 de `v0.4.0` (visibilidad y vocabulario del historial):

```text
1049 tests passing
```

Los 15 tests nuevos cubren:

- `tests/test_ticket_history_visibility.py` (13): todo evento del vocabulario declara su visibilidad por defecto; el servicio usa ese valor, admite indicar otra y rechaza (sin dejar nada pendiente) un evento fuera del vocabulario o una visibilidad desconocida; el personal ve los eventos internos y el Solicitante no; **la condición SQL coincide con la política `can_view_internal_activity` para los cuatro roles**; un conteo construido con la condición excluye lo interno; anónimos y usuarios inactivos no ven nada; y el detalle no muestra al Solicitante ni el evento interno ni su motivo, mientras el personal sí los ve.
- `tests/test_ticket_model.py` (+2 netos): la visibilidad por defecto es `PUBLICO`, la base rechaza una visibilidad desconocida y ya no restringe el vocabulario de `tipo_evento`. El test que comprobaba el CHECK de `tipo_evento` se sustituyó a propósito: esa restricción se eliminó por decisión de la fase y el rechazo de eventos desconocidos se prueba ahora en el servicio.
- `tests/test_tickets_service.py`: el test del historial pasa ahora el `viewer`, que `list_ticket_history` exige.

Estado tras el seed de tickets de demostración (entre `v0.3.0` y `v0.4.0`):

```text
1034 tests passing
```

Los 67 tests nuevos (`tests/test_seed_demo_tickets.py`) cubren:

- **los datos** (`DEMO_TICKETS`): son válidos, hay unos 40 con claves y títulos distintos, cubren todas las categorías, prioridades y ubicaciones (incluido «sin ubicación»), a todas las personas solicitantes y a buena parte del personal, con 0, 1 y 2 solicitantes, historias con ajustes, antigüedades repartidas, descripciones de largos distintos y un texto con caracteres que HTML interpretaría; y `validate_demo_tickets` rechaza datos incoherentes (clave o título repetidos o mal formados, usuario, categoría, prioridad o ubicación desconocidos, hora mal formada, Solicitante con `solicitantes`, ajustes sin cambio, sin motivo o hechos por alguien que no es personal);
- **el comando:** crea todos los tickets, se niega a ejecutarse en producción y pide `seed-demo` o `seed-catalogs` si faltan, sin cargar nada;
- **lo que crea:** creadores y solicitantes según las reglas de creación, categoría, prioridad y ubicación resueltas por nombre y código, una persona demo que solo ve los suyos (404 para el resto) y textos que se muestran escapados;
- **la marca:** todos los eventos de un ticket demo llevan su clave y su paso, el motivo de la prioridad convive con la marca y la marca no se ve en la interfaz;
- **volver a ejecutarlo:** no crea tickets ni eventos nuevos y responde `Actualizados (ya existían)`; el mismo día deja exactamente las mismas fechas; refrescar no toca el contenido ni las versiones; **un refresco da las mismas fechas que una carga nueva en el día nuevo** (se comparan las historias completas de los 40 tickets); los tickets se mueven al nuevo día; y las ediciones hechas a mano sobre un ticket demo siguen al ticket, en orden y sin quedar nunca en el futuro;
- **identidad:** mejorar un título en la lista no duplica el ticket ni sobrescribe el contenido ya cargado, añadir un ticket a la lista crea solo el nuevo, cambiar la antigüedad en la lista mueve el ticket, y nunca se toca un ticket creado a mano, ni siquiera uno con el mismo título y autor;
- **catálogos que faltan:** `Aviso:` y alternativa (`Sin clasificar` o sin ubicación), sin fallar;
- **fechas:** relativas al día de carga y medidas en días laborales, con ejemplos exactos, historial en orden cronológico, `fecha_modificacion` igual al último ajuste y solicitantes asociados en la fecha de creación;
- **tiempo laboral:** nada cae fuera de la jornada ni en fin de semana, en ejecuciones de mañana temprano, de noche y de domingo; los ajustes avanzan en horas laborales y saltan la noche y el fin de semana; un feriado se salta al contar días y horas; el calendario es configurable (otros días, otra jornada) y validado; y un refresco da lo mismo que una carga nueva incluso con un calendario distinto y feriados;
- **ajustes:** el historial queda igual que el de la aplicación (eventos, motivo en `contexto`, actor y versión) y el guard de inmutabilidad del ORM sigue rechazando una modificación normal.

Estado tras el cierre de `v0.3.0` (entrega 7):

```text
967 tests passing
```

Los 9 tests nuevos (`tests/test_route_protection.py`) recorren el mapa de rutas real en lugar de una lista escrita a mano:

- el recorrido encuentra rutas (no pasa en vacío) y cada ruta pública declarada (`auth.login`, `system.health` y `static`) existe y responde sin pedir sesión;
- **toda ruta, con cada método (GET y POST), redirige al login sin sesión** salvo las públicas, de modo que una ruta nueva no puede quedar sin autenticación por olvido;
- **toda ruta POST responde 400 sin token CSRF**, incluida la del login;
- dos pruebas de la propia red de seguridad: añaden una ruta abierta y una ruta POST exenta de CSRF, y comprueban que el recorrido las señala.

Estado tras la edición de tickets (entrega 6 de `v0.3.0`):

```text
958 tests passing
```

Los 112 tests nuevos cubren:

- `tests/test_tickets_edit_service.py` (35): cambios de título, descripción, categoría y ubicación y qué eventos registran (solo lo que cambió, un evento por tipo, una sola subida de versión), edición sin cambios, que no confirma, las mismas validaciones que la creación y sus límites exactos, valores de catálogo desactivados (rechazados si son nuevos, aceptados si el ticket ya los tenía), usuario inactivo, ticket cerrado, **conflicto de versión** (el cambio ajeno se conserva y el rechazado no deja rastro), prioridad con motivo (obligatorio, recortado, límite de 500), la misma prioridad sin efecto, prioridad inactiva o inexistente, y la descripción del historial sin el motivo.
- `tests/test_tickets_edit_routes.py` (67): acceso (anónimo, el personal, el Solicitante con 403 en GET y POST sin cambiar nada, 404 para tickets ajenos idénticos a los inexistentes, identificadores inválidos y ticket cerrado con su aviso), botones del detalle por rol y estado, formulario precargado, edición correcta con su historial visible, sin cambios, cada validación, que el formulario conserve lo escrito, categoría actual desactivada, CSRF, **conflicto entre dos ediciones** y su recarga con los datos actuales, cambio de prioridad (opciones, motivo, misma prioridad, prioridad inactiva), que el Solicitante vea qué cambió pero no el motivo, y escape de HTML.
- `tests/test_ticket_policies.py` (+10): `can_edit_ticket` y `can_change_priority`.

Estado tras el listado de tickets (entrega 5 de `v0.3.0`):

```text
846 tests passing
```

Los 86 tests nuevos cubren:

- `tests/test_tickets_list_service.py` (30): visibilidad (personal, Solicitante, solicitante retirado y usuario inactivo), **equivalencia entre la condición SQL y la política `can_view_ticket`** para todos los roles y casos, búsqueda (número con y sin `#`, número exacto y no prefijo, título y descripción sin distinguir mayúsculas, comodines literales, texto muy largo, solicitantes solo para el personal y solicitantes retirados), pestañas y contadores, filtros (estado, prioridad, categoría, ubicación y fechas por día local, incluido el límite entre días), los cuatro órdenes, paginación y que mostrar la lista no genere consultas por fila.
- `tests/test_tickets_list_routes.py` (55): acceso, cabecera y menú según el rol, lo que ve cada rol, columna de solicitantes solo para el personal, pestañas y contadores, buscador de la barra superior, filtros por URL, "Más filtros" que se abre solo si hay uno aplicado, valores inválidos ignorados, valores de catálogo desactivados, orden, paginación con los parámetros conservados, estados vacíos, tarjetas móviles, escape de HTML, y la ruta de navegación del detalle y el "Cancelar" del formulario.
- `tests/test_layout.py` (+1 caso): "Tickets" para el personal, "Mis tickets" para el Solicitante, y activas en el listado y el detalle.
- `tests/ticket_helpers.py` y la fixture `catalog` (en `tests/conftest.py`) concentran lo que comparten los tests de tickets.

Estado tras la creación de tickets (entrega 4 de `v0.3.0`):

```text
760 tests passing
```

Los 116 tests nuevos cubren:

- `tests/test_ticket_policies.py` (19): `can_create_ticket`, `can_choose_requesters` y `can_view_ticket` por rol, el Solicitante creador, solicitante vigente, solicitante retirado y ajeno, y usuarios inactivos o anónimos.
- `tests/test_tickets_routes.py` (82): acceso (anónimo, los cuatro roles); contenido del formulario por rol (la sección de solicitantes solo para el personal), solo valores activos, `Sin clasificar` al final y `Media` preseleccionada; creación como Solicitante (queda como su solicitante, historial, aviso y redirección) y como personal con 0, 1 y varios solicitantes; un Solicitante que manipula el envío para registrar otros solicitantes; solicitantes inválidos (inactivo, otro rol, inexistente); validaciones de cada campo y límites (los saltos de línea cuentan una vez); valores de catálogo inactivos o inexistentes; que el formulario conserve lo escrito; error de regla del servicio; CSRF; visibilidad del detalle (creador, solicitante vigente, retirado, ajeno, personal, inexistente e identificadores no numéricos, con la misma respuesta 404); y contenido del detalle (resumen, fechas en hora local, historial, datos solo para el personal y escape de HTML).
- `tests/test_formatting.py` (5): el filtro `local_datetime` (verano e invierno, fecha sin zona, zona desconocida y uso en plantillas).
- `tests/test_tickets_service.py` (+8): límite de la descripción, candidatos a solicitante, categorías para el selector, búsqueda por identificador público e historial.
- `tests/test_layout.py` (+2 casos): todos los roles ven ahora "Crear ticket" en el menú (antes solo Dashboard), y la opción solo se marca activa en el formulario, no en el detalle.
- `tests/conftest.py`: `make_user` admite sobrescribir cualquier valor por defecto (nombre, apellido, estado...).

Estado tras las tres primeras entregas de `v0.3.0` (catálogos, modelo de tickets y administración de catálogos):

```text
644 tests passing
```

- **Catálogos** (`tests/test_catalogs.py`, 17 tests; 402 en total): datos iniciales de `seed-catalogs` (estados en orden, prioridades con nivel creciente, categoría de respaldo y motivos de cierre), que no crea ubicaciones, idempotencia, que no pisa cambios de un Administrador, restricciones de base de datos (códigos únicos, nivel positivo y único entre activas, nombre de categoría único sin distinguir mayúsculas) y el comando CLI.
- **Modelo de tickets** (`tests/test_ticket_model.py` y `tests/test_tickets_service.py`, 44 tests; 446 en total): valores por defecto, `public_id` consecutivo y único, restricciones del cierre, solicitantes vigentes (índice parcial, retiro y nueva asociación), historial inmutable y con actor coherente, y el servicio `create_ticket` (datos, normalización, que el creador no sea solicitante por defecto, historial, validaciones, valores de catálogo inactivos o inexistentes y que no hace commit).
- **Administración de catálogos** (198 tests nuevos; 644 en total):
  - `tests/test_catalogs_service.py` (41): alta, edición (solo lo cambiado), duplicados sin distinguir mayúsculas y carrera de unicidad, desactivar y reactivar con auditoría y motivo, categoría de respaldo y última prioridad activa protegidas, conflicto al reactivar una prioridad, que desactivar no afecta a tickets existentes pero impide elegir el valor en tickets nuevos, y orden de los listados.
  - `tests/test_catalogs_routes.py` (154): control de acceso en todas las rutas (anónimo, roles sin permiso por GET y POST, ids inexistentes, CSRF), listados con filtro y estado vacío, formularios con sus validaciones, prioridades que ignoran nivel y color enviados y no se pueden crear, confirmaciones y protecciones, y escape de HTML.
  - `tests/test_layout.py`: el hub enlaza ahora cuatro secciones (antes solo Usuarios) y la navegación marca Administración como activa en las pantallas de catálogos.

Estado tras "Mi cuenta" y los datos demo (paso 5.2, cierre de `v0.2.0`):

```text
385 tests passing
```

Los 40 tests nuevos cubren:

- `tests/test_account_profile.py` (24): acceso (anónimo, todos los roles, bloqueo mientras haya un cambio de contraseña pendiente), contenido (datos propios, campos precargados, enlace al cambio de contraseña, sin acciones administrativas), edición (actualiza el contacto, auditoría por el propio usuario con solo los campos cambiados, sin cambios, vaciado de opcionales, los campos que gestiona el Administrador no se pueden cambiar, solo se edita la propia cuenta, validaciones y CSRF), navegación (Mi cuenta activa, menú del avatar) y las dos modalidades de la pantalla de contraseña (con layout en modo normal y aislada en modo obligatorio);
- `tests/test_seed_demo.py` (16): coherencia de los datos con las reglas de username, correo y longitudes, solo roles operativos, creación del equipo y carga de roles, la contraseña nunca se muestra, usuarios activos que pueden entrar sin cambio obligatorio, ningún Administrador, auditoría como acción del sistema, idempotencia, no modifica a quien ya existe, correo ocupado, ejecución sin interacción por variable de entorno, rechazo en producción, contraseña débil o con confirmación distinta, y respeto de un Administrador existente.

Dos tests existentes se ajustaron por el cambio de diseño: en modo normal, la pantalla de cambio de contraseña ya no ofrece "Volver al dashboard" sino "Volver a Mi cuenta".

Estado tras la base de la interfaz administrativa (paso 5.1):

```text
345 tests passing
```

Los 46 tests nuevos (`tests/test_layout.py`) cubren:

- la navegación por rol (opciones por rol, usuarios inactivos y anónimos, opción activa según el endpoint, que todos los endpoints existan) y las iniciales del avatar;
- el layout renderizado (sidebar filtrada por rol, sección activa, avatar, nombre y rol en la topbar, enlace para saltar al contenido, menú móvil, correspondencia de las categorías de aviso con las alertas de Bootstrap);
- el hub de administración (todas las secciones, solo Usuarios enlazada, el resto como "Próximamente", endpoints válidos);
- los activos locales: Bootstrap y sus iconos se sirven desde el propio servidor, **las huellas SHA-256 de los archivos coinciden con las documentadas**, ninguna plantilla ni hoja de estilo propia carga recursos externos, y el login sigue usando su CSS propio sin Bootstrap.

Un test existente se ajustó por el cambio de diseño: el dashboard ya no muestra un enlace directo a `/users` para el Administrador, sino a `/admin` (el hub), según `docs/11` sección 5.4.

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
