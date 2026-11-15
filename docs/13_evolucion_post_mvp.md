# 13_evolucion_post_mvp.md

# WorkDesk — Evolución posterior al MVP

**Versión:** 1.1  
**Estado:** BACKLOG EVALUADO — no forma parte del alcance del MVP ni compromete fechas  
**Proyecto:** WorkDesk  
**Objetivo:** dejar definidas, evaluadas y ordenadas las mejoras previstas después de `v1.0.0`, sin interferir con el desarrollo del MVP  

---

## 1. Propósito y alcance de este documento

Este documento reúne las mejoras que se han considerado para después de `v1.0.0` y que superaron una primera evaluación de valor, coherencia con la arquitectura y esfuerzo. Cada una tiene un identificador `EVO-nn`.

- **No altera el MVP.** El alcance y el orden del MVP siguen en `12_roadmap.md` y sus requisitos en `04_requisitos_funcionales.md`.
- **No compromete fechas.** Las olas de la sección 3 indican el orden por dependencias, no un calendario.
- **No sustituye el análisis posterior.** Antes de implementar cualquier `EVO-nn` se hará su propio análisis (requisitos y reglas de negocio, modelo de datos, diseño de pantallas, pruebas y actualización de documentos), siguiendo los principios de priorización de `02_objetivos.md` (sección 12) y la mitigación del crecimiento descontrolado del alcance de `01_vision_del_proyecto.md` (sección 15).
- Las ideas marcadas **«a evaluar»** no están comprometidas: se decidirá si se hacen cuando las anteriores estén en uso y exista una necesidad real.

El modo oscuro y la evaluación de actualizaciones en tiempo real se documentan en `12_roadmap.md` (sección 32) y son independientes de este documento.

---

## 2. Principios

**P1. WorkDesk es una aplicación 100 % local o de intranet, de forma permanente.** No depende de Internet ni de servicios externos: no habrá correo electrónico, SMS, mensajería, nube, proveedores externos de autenticación (OAuth, autenticación social) ni APIs de terceros. Todas las notificaciones y comunicaciones son internas a la aplicación. WorkDesk se ejecuta en un equipo local o en un servidor propio de la organización. *(Decisión del 2026-11-15; sustituye a los textos anteriores que dejaban esos canales como posibilidad futura.)* Lo que funciona dentro de la propia intranet, por ejemplo un directorio LDAP o Active Directory, no se descarta y se evaluará cuando exista un caso real.

**P2. Los seis estados estructurales no cambian.** Los nuevos tipos y flujos se apoyan en atributos, relaciones y catálogos controlados, no en estados nuevos ni en workflows creados por usuarios (fuera del MVP según `04_requisitos_funcionales.md`, sección 33).

**P3. Ninguna idea de este documento requiere inteligencia artificial ni aprendizaje automático.** La asistencia inteligente (`02_objetivos.md`, sección 11.6) sigue siendo una decisión abierta y, si se evaluara, por P1 solo podría ser local.

**P4. La prioridad la decide siempre una persona.** Las matrices y las reglas sugieren, no imponen (`06_reglas_de_negocio.md`, RN-19 a RN-23).

**P5. Sin dependencias nuevas sin necesidad demostrada,** de Python o de JavaScript. Se prefieren PostgreSQL, Jinja2, Bootstrap y JavaScript nativo. *Excepción acordada (2026-11-15): una librería JavaScript local para el Gantt interactivo del módulo de proyectos (EVO-26), con las condiciones de la sección 8.*

**P6. Los datos personales y de evaluación** (satisfacción, activos, ausencias, carga y tiempos de trabajo) quedan sujetos a permisos por rol, a la política de retención (RF-110 y RF-111) y a auditoría.

**P7. Los registros históricos siguen el patrón append-only del proyecto:** una corrección es un registro nuevo, nunca una edición del anterior.

---

## 3. Olas y orden

| Ola | Tema | Ideas | Depende de (MVP) |
| --- | --- | --- | --- |
| 1 | Autoservicio y calidad de atención | EVO-01 a EVO-06 | Base de conocimiento (`v0.7.0`), cierre y validación del solicitante (`v0.4.0`), notificaciones (`v0.5.0`) |
| 2 | Automatización operativa | EVO-07 a EVO-11 | Grupos y asignación (`v0.4.0`), scheduler y calendario laboral (`v0.5.0`), carga de trabajo (`v0.6.0`), configuración (`v0.7.0`) |
| 3 | Flujos ITSM sobre el mismo flujo de tickets | EVO-12 a EVO-14 (a evaluar: EVO-15 y EVO-16) | Relaciones entre tickets (`v0.4.0`), notificaciones (`v0.5.0`), búsqueda de texto de la ola 1 |
| 4 | Activos tecnológicos (CMDB local mínima) | EVO-17 a EVO-19 (a evaluar: EVO-20 y EVO-21) | Usuarios, ubicaciones, exportación (`v0.8.0`), notificaciones (`v0.5.0`) |
| 5 | Gestión de proyectos y tareas (módulo secundario, solo para el personal) | EVO-22 a EVO-29 (a evaluar: EVO-30 a EVO-32) | Grupos, comentarios y adjuntos (`v0.4.0`), calendario laboral, notificaciones y scheduler (`v0.5.0`), carga de trabajo (`v0.6.0`), configuración (`v0.7.0`), exportación (`v0.8.0`) y, de la ola 2, EVO-08 y EVO-11 (entregas 5b y 5c) |

Las olas no llevan número de versión: la numeración se definirá cuando exista la necesidad (`12_roadmap.md`, sección 32). La ola 5 no depende de las olas 3 y 4, así que puede abordarse antes que ellas si la necesidad lo pide.

---

## 4. Ola 1 — Autoservicio y calidad de atención

### EVO-01 — Deflexión de tickets en tiempo real

**Qué es.** Mientras la persona escribe el título o la descripción en «Crear ticket», un panel lateral muestra los artículos más relevantes de la Base de Conocimiento. No bloquea el envío: es una ayuda.

**Actores.** Solicitante y personal que crea tickets.

**Diseño.**
- Búsqueda de texto completo de PostgreSQL con diccionario en español (`to_tsvector('spanish', ...)` y `websearch_to_tsquery`), con una columna generada y un índice GIN sobre el título (mayor peso) y el contenido de los artículos (`10_arquitectura.md`, sección 91).
- Un endpoint devuelve un fragmento HTML; JavaScript nativo lo consulta con un retardo corto y un mínimo de caracteres, y muestra de 3 a 5 resultados. Sin JavaScript el formulario funciona igual.
- Solo se ofrecen artículos publicados y visibles para el rol (el Solicitante ve los públicos). El texto tecleado no se guarda.
- Accesibilidad: región `aria-live` para los resultados.
- Reutiliza el mecanismo de detección de duplicados (RF-061, `10_arquitectura.md`, sección 92): la misma consulta puede sugerir tickets parecidos al personal.

**Dependencias.** Base de conocimiento (`v0.7.0`). **Esfuerzo:** medio.

**Riesgos.** Con pocos artículos los resultados son pobres; con un umbral bajo hay ruido. El valor depende del contenido.

### EVO-02 — Votos y métricas de efectividad

**Qué es.** En cada artículo, «¿Te sirvió esta guía? Sí / No», con contadores de vistas y de votos. Además, una estimación de **posibles deflexiones**: la persona abrió un artículo sugerido desde el formulario y no creó ticket en esa sesión.

**Reglas.**
- Un voto por usuario y artículo, modificable.
- La deflexión es una estimación y se rotula así: cerrar la pestaña no se distingue de haber resuelto el problema. No se mide la «cancelación» como señal única.
- Métricas agregadas por artículo y por periodo para Supervisor y Administrador. Nunca un ranking de personas.

**Dependencias.** EVO-01. **Esfuerzo:** bajo a medio. La valoración de artículos ya figuraba como posterior al MVP (`12_roadmap.md`, sección 6.1).

### EVO-03 — Guías y runbooks

**Qué es.** Dos tipos de artículo: **Guía paso a paso** (para usuarios) y **Runbook de diagnóstico** (para técnicos).

**Reglas.**
- Los runbooks son siempre privados (solo personal).
- Plantilla con secciones: síntomas, precondiciones, pasos, verificación y reversión.
- Comandos y rutas internas en bloques de código con botón para copiar (JavaScript nativo).
- Las listas de verificación son texto estático en esta etapa: marcar pasos por ejecución requeriría una entidad nueva.
- Advertencia visible de no escribir contraseñas ni secretos en un artículo.

**Dependencias.** Base de conocimiento. **Esfuerzo:** bajo a medio.

### EVO-04 — Historial de versiones de artículos

**Qué es.** Cada guardado de un artículo crea una versión inmutable (título, contenido, visibilidad, autor, fecha y motivo opcional), con vista de diferencias y restauración.

**Reglas.** Restaurar crea una versión nueva con el contenido anterior; nunca se reescribe una versión (P7). Queda registrado quién cambió qué y cuándo. Las versiones se rigen por la política de retención.

**Dependencias.** Base de conocimiento. **Esfuerzo:** medio. Lo reutiliza EVO-06 para restaurar la ayuda original.

### EVO-05 — Encuesta de satisfacción (CSAT)

**Qué es.** Al confirmar el cierre de un ticket resuelto, una valoración de 1 a 5 con comentario opcional, en la misma pantalla.

**Reglas.**
- Una respuesta por ticket, solo de quien valida la solución; se puede omitir. No cambia el flujo de cierre.
- Visible para Supervisor y Administrador.
- Los indicadores por categoría y por técnico solo se muestran con un mínimo de respuestas, para no sacar conclusiones de muestras pequeñas ni usarlos de forma punitiva.
- Los comentarios son datos personales (P6).

**Dependencias.** Validación del solicitante (`v0.4.0`) y dashboards (`v0.6.0`). **Esfuerzo:** bajo a medio. Las encuestas de satisfacción figuraban fuera del MVP (`04_requisitos_funcionales.md`, sección 33).

### EVO-06 — Ayuda contextual y manual interactivo por rol

**Qué es.** Un botón «?» en la barra superior abre un panel lateral (`offcanvas` de Bootstrap) con la ayuda de la pantalla actual y de la persona según su rol, sin salir de la vista. Incluye guías de referencia, glosario (estados, prioridades, semáforos de SLA) y preguntas frecuentes.

**Diseño.**
- **No es un módulo paralelo:** los textos son artículos de la Base de Conocimiento de un tipo `AYUDA` con audiencia por rol (y, si corresponde, la pantalla a la que se asocian). Así se reutilizan el editor, las versiones (EVO-04), la búsqueda y los permisos.
- El backend filtra el contenido por el rol activo, igual que la navegación: nunca se muestra ayuda de funciones que el rol no tiene.
- El contenido de fábrica, en español, vive en archivos del repositorio y lo carga un seed idempotente, de modo que toda instalación tiene ayuda desde el primer arranque.
- El Administrador edita los textos desde el editor de la Base de Conocimiento sin tocar el código, y puede restaurar la versión original gracias a EVO-04.
- Accesible (foco y etiquetas `aria`); sin JavaScript, enlaza a una página de ayuda.

**Contenido por rol.**

| Rol | Contenido |
| --- | --- |
| Solicitante | Crear tickets bien descritos, agregar solicitantes y archivos, qué significa cada estado, validar o reabrir una solución |
| Técnico | Notas internas, estados, asignación, uso de la Base de Conocimiento, consulta de activos |
| Supervisor | Reasignación, balanceo de carga, seguimiento de SLA, grupos |
| Administrador | Usuarios, parámetros globales, retención, respaldos |

**Dependencias.** Base de conocimiento (`v0.7.0`); EVO-04 recomendado. **Esfuerzo:** medio, sobre todo por la redacción del contenido.

---

## 5. Ola 2 — Automatización operativa

### EVO-07 — Reglas de enrutamiento y recordatorios

**Qué es.** Reglas que configura el Administrador dentro de la aplicación. Ejemplos: «Si Categoría = Redes, asignar al Grupo Infraestructura»; «Si un ticket lleva más de 72 horas hábiles En espera, enviar un recordatorio interno al solicitante».

**Diseño.**
- **Catálogo cerrado** de condiciones (categoría, prioridad, ubicación, grupo, tipo, tiempo en un estado) y de acciones (asignar a un grupo o técnico, notificar, sugerir prioridad). Sin scripting ni expresiones libres.
- Orden explícito y evaluación determinista: una sola acción de asignación por evento y un límite de ejecuciones, para evitar contradicciones y bucles.
- Cada ejecución queda en el historial del ticket con actor SISTEMA y la regla que la originó.
- Modo de prueba que muestra qué haría una regla sin ejecutarla.
- Las reglas por tiempo usan el scheduler (APScheduler, proceso separado, `10_arquitectura.md`, sección 85) y el calendario laboral (`v0.5.0`).

**Dependencias.** Grupos y asignación (`v0.4.0`), notificaciones y calendario (`v0.5.0`), tabla `configuracion` (`v0.7.0`). **Esfuerzo:** alto. La asignación automática avanzada figuraba fuera del MVP (`04_requisitos_funcionales.md`, sección 33).

### EVO-08 — Disponibilidad y ausencias del personal

**Qué es.** Registrar las ausencias del personal técnico (vacaciones, licencias, permisos) con fechas y motivo, y que el sistema las considere al asignar. Hoy la continuidad ante la ausencia de un técnico se resuelve manualmente (`06_reglas_de_negocio.md`, RN-137).

**Reglas.** Una persona ausente no recibe asignaciones automáticas; sus tickets activos siguen disponibles para redistribución; el Supervisor ve las ausencias de su equipo.

**Dependencias.** Usuarios y grupos. **Esfuerzo:** medio. Es la base de EVO-09 y EVO-11.

### EVO-09 — Balanceo automático por menor carga

**Qué es.** Una opción por grupo para asignar los tickets entrantes al técnico disponible con menos tickets activos (o por turnos rotativos).

**Reglas.**
- Considera las ausencias (EVO-08).
- La asignación es atómica, con bloqueo de filas, para no asignar dos veces el mismo cupo.
- Quien está autorizado puede reasignar manualmente siempre.
- Queda registrada con actor SISTEMA.
- La «carga» es la misma que ya calcula el dashboard de carga de trabajo (`v0.6.0`). La especialidad por categoría se evaluará después.

**Dependencias.** EVO-07 y EVO-08. **Esfuerzo:** medio. La reasignación basada en carga figuraba fuera del MVP.

### EVO-10 — Tareas internas de un ticket

**Qué es.** Dividir un ticket complejo en tareas asignables a distintas personas o grupos (por ejemplo, preparar un puesto de trabajo: una tarea de hardware y otra de cuentas), sin perder el control del ticket padre.

**Diseño.** Tareas ligeras (título, responsable, estado simple pendiente o hecha, fecha opcional), **no** tickets completos: así no se duplican SLA, estados ni permisos. Opcionalmente, impedir resolver el ticket con tareas pendientes. Cada tarea tiene su historial.

**Relación.** Prepara la evolución hacia la gestión de tareas y proyectos (`02_objetivos.md`, sección 11.1; `05_requisitos_no_funcionales.md`, RNF-096) y comparte entidad con las tareas de proyecto de la ola 5 (EVO-23): la misma tabla `tareas`, con un contenedor que es un ticket o un proyecto. Los campos propios de proyecto (jerarquía, avance, fechas planificadas, dependencias) son opcionales y estas tareas no los usan. Quien se implemente primero, EVO-10 o EVO-23, debe diseñar la tabla para los dos usos (sección 8). **Esfuerzo:** medio a alto.

### EVO-11 — Calendario operativo y turnos de soporte

**Qué es.** Una vista de calendario con las guardias técnicas, las ausencias (EVO-08) y, si existen, las ventanas de mantenimiento (EVO-16).

**Reglas.** No es el calendario laboral del SLA (`v0.5.0`), que define las horas hábiles: este planifica personas y guardias. Las guardias pueden alimentar la asignación (EVO-07 y EVO-09).

**Diseño.** Vista mensual y lista renderizadas en el servidor. No se incorpora una librería de calendario hasta demostrar que hace falta (P5).

**Capas.** Es el calendario único de la aplicación: además de las guardias, las ausencias y las ventanas de mantenimiento, ofrece una capa de tareas e hitos de proyecto (EVO-26) que cada persona activa o desactiva y que respeta la visibilidad de cada proyecto. No habrá un segundo calendario para proyectos.

**Dependencias.** EVO-08. **Esfuerzo:** medio.

---

## 6. Ola 3 — Flujos ITSM sobre el mismo flujo de tickets

Todos los tipos comparten los seis estados estructurales (P2).

### EVO-12 — Tipo de ticket

**Qué es.** Un atributo que distingue **Incidente** y **Requerimiento**. Los filtros, las métricas y los formularios pueden variar según el tipo.

**Reglas.** No crea estados nuevos. Los tickets existentes pasan a un tipo por defecto. El catálogo de tipos es controlado, no creado por usuarios.

**Esfuerzo:** bajo a medio. Es el cimiento de EVO-13 y EVO-14.

### EVO-13 — Incidentes e incidente masivo

**Qué es.**
- **Prioridad sugerida:** el impacto y la urgencia (ya opcionales en el MVP) alimentan una matriz configurable que **sugiere** la prioridad. La persona autorizada la confirma o la cambia con motivo (P4). Hoy no existe matriz obligatoria (`06_reglas_de_negocio.md`).
- **Incidente masivo:** el personal marca un incidente como masivo y se muestra un aviso interno visible para los usuarios autenticados, para que no se creen decenas de tickets por la misma caída.

**Reglas.**
- Al crear un ticket con un texto parecido al de un incidente masivo activo, se sugiere asociarlo (misma búsqueda que EVO-01 y RF-061).
- Los tickets asociados se vinculan (RF-062) y pueden resolverse en lote con confirmación explícita.
- El aviso se retira al resolver el incidente. Todo queda en el historial y en notificaciones internas.

**Dependencias.** EVO-12, relaciones entre tickets (`v0.4.0`), notificaciones (`v0.5.0`), búsqueda de EVO-01. **Esfuerzo:** medio a alto.

### EVO-14 — Catálogo de requerimientos de servicio

**Qué es.** Solicitudes estándar con su propio formulario (por ejemplo, creación de una cuenta local, acceso a una carpeta compartida, solicitud de un periférico).

**Diseño en dos pasos.**
1. Plantillas con campos de un conjunto controlado (texto, lista, fecha, sí o no), guardados como datos validados dentro del ticket, y administrables por el Administrador.
2. Aprobación interna por un Supervisor antes de pasar a la cola técnica.

**Decisión previa obligatoria.** La aprobación afecta a los estados y las transiciones, y los workflows creados por usuarios están fuera del alcance (P2). Antes de implementarla se presentará una propuesta arquitectónica formal (limitación, alternativa, impacto y documentos a actualizar) y se decidirá cómo representar «pendiente de aprobación» sin añadir estados estructurales (por ejemplo, un atributo con una regla de entrada a la cola).

**Dependencias.** EVO-12. **Esfuerzo:** alto.

### Ideas a evaluar (no comprometidas)

**EVO-15 — Problemas y análisis de causa raíz.** Un registro padre que agrupa incidentes recurrentes, documenta la causa raíz y las soluciones temporales (visibles solo para el personal) y permite resolver en cascada los incidentes asociados, con confirmación. Se decidirá cuando EVO-13 esté en uso y existan incidentes recurrentes reales.

**EVO-16 — Cambios y ventanas de mantenimiento.** Registro de intervenciones planificadas con ventana de fecha y hora, nivel de riesgo, plan de reversión y aviso interno al personal afectado. Se decidirá junto con EVO-11.

---

## 7. Ola 4 — Activos tecnológicos (CMDB local mínima)

Alcance: **sin descubrimiento automático** de equipos ni agentes. Los datos se cargan a mano o por importación.

### EVO-17 — Activos y asignación

**Qué es.** Una ficha de activo con código de inventario, tipo, marca y modelo, número de serie, sistema operativo, memoria y procesador (como texto), IP local, fecha de entrega, estado y vida útil estimada, asignada a una persona, con historial inmutable de asignaciones.

**Reglas.**
- Alta y edición por el personal.
- **Importación desde CSV** con validación y vista previa: sin ella el inventario no se llena y pierde valor.
- Los datos se ven solo por el personal y por la persona asignada (P6).
- Se desactiva en lugar de borrar. Todo queda auditado.

**Dependencias.** Usuarios y ubicaciones. **Esfuerzo:** alto, por la importación y el historial.

### EVO-18 — Ficha del solicitante en el ticket y vínculo ticket-activo

**Qué es.** Al abrir un ticket, el personal ve en un panel lateral los equipos asignados a quien lo reporta y puede vincular el ticket a uno o más activos.

**Reglas.** El panel es solo para el personal. El vínculo es N:M con unicidad por par. El solicitante ve únicamente sus propios equipos.

**Dependencias.** EVO-17. **Esfuerzo:** medio.

### EVO-19 — Historial por activo y ciclo de vida

**Qué es.** Una vista por activo con todos los tickets vinculados, la frecuencia de reparaciones y una marca de «revisar reemplazo» según un umbral configurable. Un aviso interno a Supervisores y Administradores cuando el activo supera su vida útil estimada.

**Dependencias.** EVO-17, EVO-18 y notificaciones (`v0.5.0`). **Esfuerzo:** medio.

### Ideas a evaluar (no comprometidas)

**EVO-20 — Control de stock de repuestos y periféricos.** Inventario de insumos (mouse, teclado, fuentes, módulos de memoria) que se descuenta al vincularlos a un ticket y registra cada movimiento. Es un dominio de inventario con movimientos inmutables, mínimos y concurrencia: se evaluará como módulo separado cuando los activos estén en uso.

**EVO-21 — Alertas de stock crítico.** Aviso interno cuando un insumo baja del mínimo configurado. Depende de EVO-20.

---

## 8. Ola 5 — Gestión de proyectos y tareas

Un módulo secundario, **«Proyectos»**, para planificar y dar seguimiento al trabajo que no es un ticket: proyectos de TI (renovación de equipos, migración de un servidor), logísticos (apertura de una sucursal, mudanza de una oficina) o personales (la lista de tareas de una persona). Es solo para el personal y se apoya en lo que WorkDesk ya tiene: usuarios y roles, grupos, calendario laboral, ausencias, comentarios, adjuntos y notificaciones internas.

Concreta las secciones 11.1 a 11.3 de `02_objetivos.md` y **cierra la decisión que ese documento (sección 13) dejaba abierta sobre el modelo de relación entre tickets, tareas y proyectos**. No generaliza el ticket: `01_vision_del_proyecto.md` (sección 10.5) advierte contra una generalización excesiva. Un ticket es trabajo *reactivo* (alguien pide algo y corre un SLA); un proyecto es trabajo *planificado* (objetivo, fechas, tareas y dependencias). Se enlazan, no se mezclan.

**Ejemplo.** «Renovación de equipos de la sucursal»: un proyecto de equipo cuyo Responsable es un Supervisor, con tareas por fase (inventario, compra, instalación, migración de datos), un hito «Entrega a los usuarios», dependencias entre fases y varios Técnicos con tareas asignadas. Al instalar un equipo aparece un ticket de ajuste («no puedo imprimir desde el equipo nuevo»): se crea desde la tarea y queda vinculado a ella. El Gantt dibuja el cronograma sobre los días laborales y la carga de cada Técnico suma esos tickets y sus tareas.

### Principios del módulo

1. **Los tickets siguen siendo el núcleo.** «Proyectos» es una opción secundaria del menú y no cambia el flujo de tickets, sus seis estados (P2) ni el SLA. Las métricas de proyectos no se mezclan en los dashboards ni en los reportes de tickets. El Administrador puede habilitar o deshabilitar el módulo (un parámetro de `configuracion`): deshabilitado, desaparece del menú y del ticket, sus rutas responden 404 y los datos se conservan.
2. **Una sola entidad de tarea.** Las tareas internas de un ticket (EVO-10) y las de un proyecto (EVO-23) son la misma tabla, `tareas`, con un contenedor que es un ticket o un proyecto (exactamente uno). Los campos propios de proyecto (jerarquía, avance, fechas planificadas, dependencias) son opcionales y las tareas de un ticket no los usan. No habrá un segundo modelo de tarea.
3. **Un solo motor de tiempo laboral y de disponibilidad.** Las fechas de las tareas se calculan con el calendario laboral y el motor compartido de `v0.5.0` (días, jornadas y feriados), y la disponibilidad se toma de las ausencias (EVO-08) y los turnos (EVO-11). No habrá un calendario propio de proyectos.
4. **Solo para el personal.** El Solicitante no accede al módulo ni ve vínculos de un ticket con tareas: el panel «Proyecto» del ticket y los eventos de historial del vínculo son solo para el personal.
5. **Historial inmutable y archivar en lugar de borrar.** Proyectos y tareas tienen historial append-only (P7). Un proyecto que ya tiene tareas, tickets vinculados, comentarios o adjuntos no se elimina: se **archiva** o se **cancela**, de forma reversible y consultable. Solo el Administrador puede eliminar físicamente un proyecto **vacío** (que nunca tuvo nada de lo anterior), y toda acción queda auditada.
6. **Excepción acordada a P5: una librería JavaScript local para el Gantt interactivo (EVO-26).** Se sirve como Bootstrap (en `static/vendor/`, sin CDN) y el servidor sigue siendo la fuente de verdad: la librería solo dibuja y captura gestos, y cada cambio de fechas lo valida el servidor contra el calendario laboral, las dependencias y los permisos. Sin JavaScript queda una tabla con las tareas y sus fechas. Las condiciones están en EVO-26.

### Roles y permisos

Propuesta de partida, que se confirmará al analizar EVO-22 (`03_roles_y_permisos.md`). La autorización se aplica siempre en backend: 404 si no se puede ver el proyecto o la tarea y 403 si se ve pero no se puede modificar, como en los tickets.

| Capacidad | Solicitante | Técnico | Supervisor | Administrador |
| --- | --- | --- | --- | --- |
| Acceder al módulo «Proyectos» | No | Sí | Sí | Sí |
| Ver proyectos | — | Aquellos de los que es miembro | Aquellos de los que es miembro y los de los grupos de los que es supervisor responsable | Todos, también los privados |
| Crear un proyecto privado (por ejemplo, uno personal) | — | Sí | Sí | Sí |
| Crear un proyecto de equipo | — | No | Sí | Sí |
| Editar el proyecto, sus miembros, su estructura de tareas, fechas y dependencias; guardar línea base | — | Solo sus proyectos privados | Como Responsable, o en los proyectos de sus grupos | Todos |
| Completar, pausar, cancelar o archivar un proyecto | — | Solo sus proyectos privados | Como Responsable, o en los proyectos de sus grupos | Todos |
| Actualizar las tareas que tiene asignadas (estado, avance, comentarios y adjuntos) | — | Sí | Sí | Sí |
| Crear y editar plantillas de proyecto (EVO-28) | — | No | Sí | Sí |
| Eliminar un proyecto vacío | — | No | No | Sí |
| Habilitar o deshabilitar el módulo y administrar los tipos de proyecto | — | No | No | Sí |

**Roles dentro del proyecto.** El *Responsable* (uno o varios) gestiona su estructura; el *Miembro* participa y actualiza sus tareas. El rol del proyecto no amplía lo que permite el rol global: un Técnico puede ser Responsable de un proyecto privado suyo, pero no de uno de equipo.

**Visibilidad.** *Privado*: lo ven sus miembros y los Administradores. *De equipo*: además lo ven los Supervisores de los grupos asociados al proyecto. El Administrador ve todos los proyectos, incluidos los privados, y la interfaz lo indica («Visible para sus miembros y Administradores»).

### Cómo se relacionan tickets, tareas y proyectos

| Relación | Qué significa | Cómo se representa |
| --- | --- | --- |
| Tarea de un ticket (EVO-10) | Parte del trabajo de resolver ese ticket | Una tarea cuyo contenedor es el ticket |
| Tarea de un proyecto (EVO-23) | Trabajo planificado dentro de un proyecto | Una tarea cuyo contenedor es el proyecto |
| Vínculo entre una tarea de proyecto y un ticket (EVO-24) | La tarea nace de uno o más tickets, o los afecta | Una relación N:M, independiente de las dos anteriores |

Un ticket nunca «está dentro» de un proyecto: conserva su flujo, su SLA y sus permisos, y el proyecto solo lo referencia.

### EVO-22 — Proyectos y miembros

**Qué es.** La ficha del proyecto y quién participa en él, con listado (búsqueda y filtros por estado, tipo, responsable, visibilidad y «Mis proyectos»), detalle y alta o edición.

**Datos.**
- Identificador público correlativo propio (secuencia de PostgreSQL, como los tickets) con el prefijo `P-` (`P-12`), para no confundirlo con el `#N` de los tickets.
- Nombre, objetivo o descripción, **tipo** (catálogo administrable: TI, Infraestructura, Desarrollo, Logística, Personal y Otro, con el patrón de los demás catálogos: se desactiva, no se borra), prioridad (el mismo catálogo de los tickets; aquí solo ordena y no activa ningún SLA), grupo o área responsable (opcional, `v0.4.0`) y visibilidad (privado o de equipo).
- Fechas planificadas de inicio y fin y fechas reales (estas se completan al cambiar de estado).
- Estado: Planificado, En curso, En pausa, Completado o Cancelado. Es un conjunto fijo, sin workflows configurables (P2). **Archivado** es un atributo aparte, no un estado: se puede archivar y desarchivar un proyecto en cualquier estado.

**Reglas.**
- Miembros: personal activo, con rol en el proyecto Responsable o Miembro (siempre al menos un Responsable). Quien se desactiva conserva su historia en el proyecto.
- Completar un proyecto con tareas pendientes pide una confirmación explícita; cancelarlo exige un motivo. El motivo y quién lo hizo quedan en el historial.
- Archivar y eliminar siguen el principio 5.
- Auditoría: las acciones del Administrador (crear, configurar, archivar, cancelar, eliminar) en la auditoría administrativa; la actividad del proyecto, en su historial inmutable.

**Dependencias.** Usuarios, grupos (`v0.4.0`) y la tabla `configuracion` (`v0.7.0`) para el interruptor del módulo. **Esfuerzo:** medio.

### EVO-23 — Tareas y subtareas

**Qué es.** Las unidades de trabajo de un proyecto y, con el ticket como contenedor, las tareas internas de EVO-10.

**Datos.** Identificador público propio (`T-N`), título, descripción, contenedor (proyecto o ticket), tarea padre (como máximo tres niveles: tarea, subtarea y subtarea de segundo nivel), posición dentro de su padre, estado, 0..N responsables, fechas planificadas (inicio y fin) y reales, esfuerzo estimado en horas (informativo), avance de 0 a 100 %, indicador de hito y versión (control de ediciones simultáneas, como en los tickets). Las fechas de las tareas son días, no instantes.

**Reglas.**
- Estados: Pendiente, En curso, Bloqueada (con motivo), Hecha y Cancelada. Las tareas de un ticket (EVO-10) usan solo Pendiente y Hecha.
- **Avance.** En una tarea sin subtareas lo informa su responsable (Hecha equivale a 100 %). En una tarea con subtareas se calcula a partir de ellas, ponderado por su duración planificada en días laborales, y no se edita; el avance del proyecto se calcula igual con sus tareas de primer nivel. Una tarea con subtareas solo pasa a Hecha cuando todas están Hechas o Canceladas.
- **Hito.** Una tarea de duración cero (una sola fecha) que marca un punto de control. No lleva esfuerzo ni avance parcial.
- **Responsables.** Varios por tarea. Asignar una tarea a alguien que no es miembro del proyecto lo agrega como Miembro y se le avisa.
- **Comentarios y adjuntos** (de tareas y de proyectos, solo para el personal): reutilizan los componentes de los tickets (`v0.4.0`), con las mismas validaciones y el mismo almacenamiento en `instance/uploads/`.
- **Notificaciones internas:** al ser asignado, cuando la tarea está por vencer y cuando vence sin terminar (scheduler de `v0.5.0`).
- **Historial inmutable por tarea:** estado, fechas, responsables, avance, dependencias y vínculos.

**Vistas.** Lista en árbol con subtareas plegables; **tablero Kanban** por estado (el estado se cambia con botones y, como mejora progresiva, arrastrando; el servidor valida cada cambio); y **«Mis tareas»**, con todas las tareas asignadas a la persona en todos los proyectos y en tickets (EVO-10), ordenadas por vencimiento. Que ambas formas de trabajo convivan en una misma lista es lo que justifica la entidad única.

**Dependencias.** EVO-22, comentarios y adjuntos (`v0.4.0`), notificaciones y scheduler (`v0.5.0`). **Esfuerzo:** alto.

### EVO-24 — Vínculo entre tareas y tickets

**Qué es.** Relacionar el trabajo planificado con los tickets que lo originan o lo afectan: una relación N:M entre tareas de proyecto y tickets, con unicidad por par y el patrón temporal de los solicitantes (al desvincular se conserva el registro, con su fecha de retiro).

**Cómo se usa.**
- **Crear un ticket desde una tarea.** Abre «Crear ticket» con el título y la descripción precargados y editables; al crearlo queda vinculado. Usa la misma pantalla y las mismas reglas de creación de siempre.
- **Crear una tarea desde un ticket,** o vincularlo a una existente: desde el panel lateral del ticket, en un proyecto que la persona pueda gestionar.
- **Panel «Proyecto» en el ticket,** solo para el personal: las tareas vinculadas con su proyecto, estado y avance, limitado a los proyectos que la persona puede ver. Desde la tarea se ven los tickets vinculados con su estado.

**Reglas.**
- Cerrar o resolver un ticket **no cambia** la tarea: el avance de un proyecto no lo decide el flujo de soporte. La tarea muestra un indicador «ticket cerrado» y, si todos sus tickets vinculados están cerrados, **sugiere** marcarla como Hecha; la decide una persona (en el espíritu de P4).
- El vínculo no altera el SLA, los estados ni los permisos del ticket.
- El Solicitante no ve el panel ni los eventos del vínculo (principio 4).
- Los eventos quedan en el historial de la tarea y, ocultos para el Solicitante, en el del ticket.

**Dependencias.** EVO-22 y EVO-23. **Esfuerzo:** medio.

### EVO-25 — Dependencias y programación con el calendario laboral

**Qué es.** Qué tarea debe terminar antes de que empiece otra, con las fechas calculadas en días laborales.

**Reglas.**
- Dependencias **fin-inicio** entre tareas del mismo proyecto, con un desfase en días laborales (cero por defecto). Otros tipos (inicio-inicio, fin-fin) se añadirán solo si hacen falta.
- **Sin ciclos:** el servicio rechaza una dependencia que cree uno, con un mensaje claro.
- **Programación automática con vista previa.** Al mover o alargar una tarea, el sistema calcula qué sucesoras se desplazarían y lo muestra (antes y después) para confirmarlo. Nunca mueve fechas sin confirmación. Una tarea puede tener sus fechas **fijadas** y no se desplaza sola.
- Todas las fechas salen del motor de tiempo laboral compartido: saltan fines de semana, feriados y las jornadas configuradas. Las ausencias (EVO-08) no cambian la duración de una tarea, pero se avisan (EVO-27).
- **Ruta crítica:** las tareas sin holgura, cuyo retraso retrasa el fin del proyecto, calculada en el servidor.
- Una reprogramación toca varias tareas en una sola transacción y con el proyecto bloqueado (`SELECT ... FOR UPDATE`), para que dos reprogramaciones simultáneas no se pisen.
- Pensado para proyectos de decenas a unos pocos cientos de tareas.

**Dependencias.** EVO-23 y el calendario laboral (`v0.5.0`). **Esfuerzo:** alto.

**Riesgos.** El cálculo (feriados, jornadas parciales, fechas fijadas) es la parte más delicada del módulo. Se cubre con pruebas sobre calendarios variados y con la vista previa obligatoria.

### EVO-26 — Gantt interactivo, calendario y línea base

**Qué es.** Ver y ajustar el cronograma de un proyecto.

**Gantt.**
- Una barra por tarea con jerarquía plegable, hitos como rombos, flechas de dependencia, línea de «hoy», avance dentro de la barra, ruta crítica resaltada, **días no laborales y feriados sombreados** (los del calendario laboral) y zoom (días, semanas y meses).
- **Interactivo:** arrastrar una barra la mueve, estirar un borde cambia su duración y unir dos barras crea una dependencia. Cada gesto se envía al servidor, que lo valida con las mismas reglas que los formularios (permisos, calendario, dependencias, versión) y devuelve las fechas resultantes; si el gesto desplazaría tareas sucesoras, muestra la vista previa de EVO-25 y espera la confirmación. **El navegador nunca decide una fecha.** Si el servidor lo rechaza, la barra vuelve a su lugar con un aviso. Quien no puede editar solo lo ve.
- **Sin JavaScript** hay una tabla con las tareas, sus fechas, duraciones y dependencias, editable con formularios. En pantallas pequeñas el Gantt es de solo lectura, con desplazamiento horizontal.

**Librería local.** Excepción acordada a P5, con estas condiciones:
- Se instala como Bootstrap: en `static/vendor/`, **versión fija**, sin modificar y con su licencia, con su origen, su versión y sus **huellas SHA-256 documentados** en `static/vendor/README.md` (`10_arquitectura.md`, sección 31). Sin CDN ni peticiones externas (P1). Las pruebas comprueban las huellas y que ninguna plantilla cargue recursos externos, como ya ocurre con Bootstrap.
- **Criterios de elección,** fijados desde ahora: licencia permisiva (MIT, BSD o Apache 2.0); sin dependencias de ejecución, o con las suyas incluidas en el mismo vendor; tamaño razonable; dependencias, hitos, línea base, días no laborales y zoom; arrastre y estirado de barras; navegación con teclado; colores personalizables solo con CSS y tokens `--wd-*` (para el tema oscuro); textos configurables en español; mantenimiento activo y API estable; y que no cargue fuentes ni otros recursos de terceros.
- **Alternativa** si ninguna librería cumple: un Gantt de solo lectura dibujado por el servidor (SVG o HTML) con la edición por formularios. La elección, o el recurso a la alternativa, se documenta al abordar EVO-26.

**Calendario.** Es el calendario operativo de EVO-11, que gana una capa de tareas e hitos (inicio y vencimiento): cada persona la activa o desactiva y respeta la visibilidad de cada proyecto. No habrá un segundo calendario para proyectos (principio 3).

**Línea base.** «Guardar línea base» (quien puede editar el proyecto) crea una instantánea inmutable de las fechas planificadas de cada tarea y del proyecto, con fecha, autor y nota (P7). Se pueden guardar varias, numeradas, y la desviación (en días laborales) se calcula respecto de la elegida. El Gantt dibuja la barra de la línea base bajo la actual.

**Dependencias.** EVO-25 y el calendario laboral (`v0.5.0`); la capa de calendario requiere EVO-11. **Esfuerzo:** alto.

**Riesgos.** El encaje y la accesibilidad de la librería elegida, y el arrastre en pantallas táctiles. Los acotan la alternativa de solo lectura y que el servidor sea la fuente de verdad.

### EVO-27 — Carga y disponibilidad combinadas

**Qué es.** Ver cuánto trabajo tiene cada persona sumando tickets y tareas, y recibir avisos al asignar.

**Reglas.**
- La carga combina los tickets activos (el cálculo del dashboard de `v0.6.0`) y las horas estimadas de las tareas abiertas, repartidas entre sus días laborales y sus responsables. Es una **estimación** y se rotula así.
- Al asignar una tarea se avisa si la persona está ausente en esas fechas (EVO-08), fuera de turno (EVO-11) o ya tiene mucha carga en el periodo.
- **Informativo, nunca bloquea** (RF-037): no impide asignar, programar ni completar.
- El Supervisor y el Administrador ven la del equipo y el Técnico, la suya (P6). Nunca un ranking de personas.
- No hay nivelación automática de recursos (ver «Descartado»): las personas deciden.

**Dependencias.** EVO-23, EVO-08, EVO-11 y la carga de trabajo (`v0.6.0`). **Esfuerzo:** medio.

### EVO-28 — Plantillas de proyecto

**Qué es.** Crear proyectos repetitivos (alta de una sucursal, renovación de equipos, migración de un servidor, mudanza) a partir de una estructura probada.

**Reglas.**
- Una plantilla guarda la estructura (tareas, subtareas, hitos, dependencias, duraciones y esfuerzo), pero **no** fechas, personas ni vínculos con tickets. Se puede crear desde un proyecto existente.
- Al crear un proyecto desde una plantilla se elige la fecha de inicio, las fechas se calculan con el calendario laboral y los responsables se asignan después. La plantilla es una copia de partida: modificarla no cambia los proyectos ya creados.
- Las crean y editan el Supervisor y el Administrador, y las ve todo el personal. Las plantillas de ejemplo viven en un seed de demostración opcional, no en la carga inicial.

**Dependencias.** EVO-22, EVO-23 y EVO-25. **Esfuerzo:** medio.

### EVO-29 — Panel e informes de proyectos

**Qué es.** Una pantalla propia dentro del módulo (no en el dashboard principal) para el Supervisor y el Administrador, y un resumen por proyecto.

**Contenido.**
- **Panel:** proyectos por estado, avance, próximos hitos, tareas vencidas, tareas sin responsable y proyectos sin actividad en un periodo.
- **Salud del proyecto:** un semáforo (en plazo, en riesgo, atrasado) con reglas simples y umbrales configurables (`configuracion`), a partir de las tareas vencidas y de la desviación respecto de la línea base.
- **Exportación a CSV** de proyectos y tareas, reutilizando la exportación de `v0.8.0`, y una **vista imprimible** del proyecto (CSS de impresión) para reuniones.

**Dependencias.** EVO-22 a EVO-26 y la exportación (`v0.8.0`). **Esfuerzo:** medio.

### Ideas a evaluar (no comprometidas)

**EVO-30 — Seguimiento de horas reales.** Registrar las horas trabajadas por tarea para compararlas con la estimación. Se evaluará cuando haya estimaciones en uso: el riesgo es la percepción de vigilancia y la carga administrativa para el personal. Si se hace, son datos personales (P6): solo agregados para el Supervisor, nunca un ranking de personas.

**EVO-31 — Riesgos y presupuesto del proyecto.** Un registro de riesgos (descripción, probabilidad, impacto, mitigación, responsable y estado) es barato y útil. El **presupuesto** roza la contabilidad, excluida por `02_objetivos.md` (sección 10): se limitaría a un monto estimado y otro ejecutado por partida, sin facturación. Se decidirá cuando el núcleo esté en uso.

**EVO-32 — Tareas recurrentes y portafolios.** Tareas periódicas (por ejemplo, «revisar los respaldos cada lunes») generadas por el scheduler, y agrupar proyectos en programas o portafolios con avance consolidado. Se solapa con los recordatorios (EVO-07) y con las ventanas de mantenimiento (EVO-16), así que se decidirá junto con ellos.

### Descartado

| Idea | Motivo |
| --- | --- |
| Nivelación automática de recursos y optimización de cronogramas | Es una optimización compleja y la carga es informativa (RF-037): las personas deciden. |
| Valor ganado, costos y finanzas del proyecto | La contabilidad y la facturación están excluidas (`02_objetivos.md`, sección 10). |
| Edición colaborativa del Gantt en tiempo real | Exige conexiones persistentes, que se evalúan aparte (`12_roadmap.md`, sección 32). El control de versión resuelve la concurrencia. |
| Sincronización con herramientas externas (Microsoft Project, Jira, calendarios en la nube) | P1. |
| Proyectos o vínculos visibles para el Solicitante | Principio 4: el módulo es interno del personal. |
| Un segundo modelo de tarea o de calendario | Principios 2 y 3. |
| Métricas de proyectos dentro de los dashboards y reportes de tickets | Principio 1. |

### Entregas internas

La ola se divide en tres entregas, cada una utilizable por sí sola y con su propia rama, pruebas y Pull Request, como en el MVP:

| Entrega | Contenido | Resultado |
| --- | --- | --- |
| 5a — Núcleo | EVO-22, EVO-23 y EVO-24 | Proyectos con tareas, tablero, «Mis tareas» y vínculo con tickets, sin planificación automática |
| 5b — Planificación | EVO-25 y EVO-26 | Dependencias, programación sobre el calendario laboral, Gantt interactivo, calendario y línea base |
| 5c — Recursos y colaboración | EVO-27, EVO-28 y EVO-29 | Carga combinada, plantillas, panel e informes |

### Entidades previstas (orientativo)

Lista para el análisis posterior; no se incorpora a `09_modelo_de_datos.md` hasta abordar la ola.

| Entidad | Para qué |
| --- | --- |
| `proyectos` | Ficha del proyecto (EVO-22) |
| `tipos_proyecto` | Catálogo administrable de tipos de proyecto |
| `proyectos_miembros` | Miembros con su rol (Responsable o Miembro) y su vigencia |
| `tareas` | Tareas y subtareas, con contenedor ticket o proyecto (EVO-10 y EVO-23) |
| `tareas_responsables` | Responsables de una tarea (N:M) |
| `tareas_dependencias` | Dependencias fin-inicio con desfase (EVO-25) |
| `tareas_tickets` | Vínculo entre tareas y tickets, con vigencia (EVO-24) |
| `historial_proyecto` y `historial_tarea` | Historiales inmutables |
| `lineas_base` y `lineas_base_tareas` | Instantáneas de las fechas planificadas (EVO-26) |
| `plantillas_proyecto` y sus tareas | Plantillas (EVO-28) |
| Comentarios y adjuntos | Se reutilizan o adaptan los de los tickets |

### Puntos de diseño que quedan abiertos

1. **Eliminar un proyecto vacío con un historial inmutable.** El historial del proyecto es append-only (P7) y no puede borrarse con él. Al analizar EVO-22 se decidirá cómo conciliarlo; por ejemplo, registrar la creación y la eliminación en la auditoría administrativa y hacer que el historial del proyecto empiece con su primera tarea o vínculo.
2. **Elección de la librería del Gantt.** Se hace al abordar EVO-26, con los criterios fijados allí y con su alternativa de respaldo.
3. **Cambios en el calendario laboral con tareas ya programadas.** Si el Administrador modifica el calendario (por ejemplo, un feriado nuevo), las fechas de las tareas ya programadas no se mueven solas: se avisa de las tareas afectadas y se ofrece reprogramarlas con la vista previa de EVO-25.

---

## 9. Qué tener presente durante el MVP (sin cambiar su alcance)

1. **Vocabulario de eventos del historial.** *Resuelto en `v0.4.0` (entrega 1):* se eliminó la restricción CHECK `ck_historial_ticket_tipo_evento` y el vocabulario (`TicketEvent`) vive solo en la aplicación, así que las ideas que añadan eventos (reglas, satisfacción, tareas y vínculos con proyectos, incidentes) no necesitan migración por ello.
2. **Búsqueda de la Base de conocimiento (`v0.7.0`).** Al diseñarla, dejar prevista la columna `tsvector` y el índice GIN de `10_arquitectura.md` (sección 91): EVO-01 y EVO-13 la reutilizan.
3. **Tabla `configuracion` (`v0.7.0`).** Allí se guardarán las reglas, los umbrales de satisfacción y de vida útil, el interruptor del módulo de proyectos y sus umbrales.
4. **Motor de tiempo laboral compartido (`v0.5.0`).** Lo usarán el SLA, los recordatorios por tiempo (EVO-07), el calendario operativo (EVO-11) y la programación de tareas de proyecto (EVO-25 y EVO-26). Conviene que ofrezca operaciones de calendario (si una fecha es un día laboral, sumar días laborales, contar los días laborales entre dos fechas) y no solo el cálculo de plazos del SLA.
5. **Eventos del sistema.** El actor SISTEMA ya está soportado en el historial y en la auditoría; las automatizaciones lo usarán.
6. **Eventos del historial internos.** *Resuelto en `v0.4.0` (entrega 1):* `historial_ticket.visibilidad` (`PUBLICO` o `INTERNO`) y un filtro único en la consulta (`visible_history_condition`). Los vínculos con tareas de proyecto (EVO-24) lo reutilizarán: bastará declarar la visibilidad por defecto de cada evento nuevo.
7. **No generalizar por anticipado.** Los comentarios y los adjuntos de `v0.4.0` se diseñan para los tickets. No se generalizan ahora para las tareas (`01_vision_del_proyecto.md`, sección 10.5): se adaptarán al abordar EVO-23.

---

## 10. Registro de decisiones

| Fecha | Decisión |
| --- | --- |
| 2026-11-15 | WorkDesk es 100 % local o de intranet, de forma permanente (P1): sin correo, SMS, mensajería, nube, autenticación externa ni APIs de terceros. |
| 2026-11-15 | Flujos ITSM: se comprometen EVO-12, EVO-13 y EVO-14; EVO-15 y EVO-16 quedan a evaluar. |
| 2026-11-15 | Activos: se comprometen EVO-17 a EVO-19; EVO-20 y EVO-21 quedan a evaluar. |
| 2026-11-15 | La ayuda contextual reutiliza la Base de Conocimiento (EVO-06). |
| 2026-11-15 | Las reglas de automatización usan un catálogo cerrado de condiciones y acciones, sin scripting (EVO-07). |
| 2026-11-15 | Se incorpora la ola 5, «Gestión de proyectos y tareas», como módulo secundario solo para el personal: se comprometen EVO-22 a EVO-29 y quedan a evaluar EVO-30 a EVO-32. |
| 2026-11-15 | Los tickets siguen siendo el núcleo: los proyectos no alteran su flujo, sus estados ni el SLA, no se mezclan en sus dashboards y el módulo puede deshabilitarse (ola 5). |
| 2026-11-15 | Una sola entidad de tarea para las tareas de un ticket (EVO-10) y de un proyecto (EVO-23), y un solo motor de tiempo laboral y de disponibilidad. |
| 2026-11-15 | El Administrador ve todos los proyectos, incluidos los privados. |
| 2026-11-15 | Un proyecto con tareas, vínculos, comentarios o adjuntos se archiva o se cancela; solo el Administrador elimina un proyecto vacío. |
| 2026-11-15 | El Gantt es interactivo y usa una librería JavaScript local (excepción acordada a P5): el servidor es la fuente de verdad y existe una alternativa sin JavaScript (EVO-26). |

---

## 11. Documentos a actualizar al abordar cada idea

| Ola | Documentos |
| --- | --- |
| 1 | `04` (requisitos de la Base de conocimiento y de satisfacción), `09` (versiones, votos, tipos de artículo, satisfacción), `11` (panel de sugerencias, votación, ayuda), `12` |
| 2 | `04` y `06` (reglas de asignación y ausencias), `09` (reglas, ausencias, tareas, turnos), `10` (scheduler), `11`, `12` |
| 3 | `06` (prioridad sugerida y reglas de incidente masivo), `08` (tipos de ticket), `09` (tipo, plantillas de requerimiento), `11`, `12`; y `10` si EVO-14 cambia el flujo |
| 4 | `03` (permisos sobre activos), `04`, `09` (activos, asignaciones, vínculo con tickets), `11`, `12` |
| 5 | `03` (permisos del módulo y roles dentro del proyecto), `04` y `06` (requisitos y reglas de proyectos y tareas), `07` (casos de uso), `08` si el vínculo con tickets lo requiere, `09` (proyectos, tareas, dependencias, líneas base y plantillas), `10` (la librería del Gantt y `static/vendor/`), `11` (pantallas de proyectos, tablero, Gantt y calendario), `12`; además `static/vendor/README.md` y `PROJECT_CONTEXT.md` |
