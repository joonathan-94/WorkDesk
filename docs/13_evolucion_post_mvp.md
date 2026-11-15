# 13_evolucion_post_mvp.md

# WorkDesk — Evolución posterior al MVP

**Versión:** 1.0  
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

**P5. Sin dependencias nuevas sin necesidad demostrada,** de Python o de JavaScript. Se prefieren PostgreSQL, Jinja2, Bootstrap y JavaScript nativo.

**P6. Los datos personales y de evaluación** (satisfacción, activos, ausencias) quedan sujetos a permisos por rol, a la política de retención (RF-110 y RF-111) y a auditoría.

**P7. Los registros históricos siguen el patrón append-only del proyecto:** una corrección es un registro nuevo, nunca una edición del anterior.

---

## 3. Olas y orden

| Ola | Tema | Ideas | Depende de (MVP) |
| --- | --- | --- | --- |
| 1 | Autoservicio y calidad de atención | EVO-01 a EVO-06 | Base de conocimiento (`v0.7.0`), cierre y validación del solicitante (`v0.4.0`), notificaciones (`v0.5.0`) |
| 2 | Automatización operativa | EVO-07 a EVO-11 | Grupos y asignación (`v0.4.0`), scheduler y calendario laboral (`v0.5.0`), carga de trabajo (`v0.6.0`), configuración (`v0.7.0`) |
| 3 | Flujos ITSM sobre el mismo flujo de tickets | EVO-12 a EVO-14 (a evaluar: EVO-15 y EVO-16) | Relaciones entre tickets (`v0.4.0`), notificaciones (`v0.5.0`), búsqueda de texto de la ola 1 |
| 4 | Activos tecnológicos (CMDB local mínima) | EVO-17 a EVO-19 (a evaluar: EVO-20 y EVO-21) | Usuarios, ubicaciones, exportación (`v0.8.0`), notificaciones (`v0.5.0`) |

Las olas no llevan número de versión: la numeración se definirá cuando exista la necesidad (`12_roadmap.md`, sección 32).

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

**Relación.** Prepara la evolución hacia la gestión de tareas y proyectos (`02_objetivos.md`, sección 11.1; `05_requisitos_no_funcionales.md`, RNF-096). **Esfuerzo:** medio a alto.

### EVO-11 — Calendario operativo y turnos de soporte

**Qué es.** Una vista de calendario con las guardias técnicas, las ausencias (EVO-08) y, si existen, las ventanas de mantenimiento (EVO-16).

**Reglas.** No es el calendario laboral del SLA (`v0.5.0`), que define las horas hábiles: este planifica personas y guardias. Las guardias pueden alimentar la asignación (EVO-07 y EVO-09).

**Diseño.** Vista mensual y lista renderizadas en el servidor. No se incorpora una librería de calendario hasta demostrar que hace falta (P5).

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

## 8. Qué tener presente durante el MVP (sin cambiar su alcance)

1. **Vocabulario de eventos del historial.** La restricción CHECK `ck_historial_ticket_tipo_evento` exige una migración por cada evento nuevo. Conviene decidir en `v0.4.0` si se mantiene, porque varias ideas añadirán eventos (reglas, satisfacción, tareas, incidentes).
2. **Búsqueda de la Base de conocimiento (`v0.7.0`).** Al diseñarla, dejar prevista la columna `tsvector` y el índice GIN de `10_arquitectura.md` (sección 91): EVO-01 y EVO-13 la reutilizan.
3. **Tabla `configuracion` (`v0.7.0`).** Allí se guardarán las reglas, los umbrales de satisfacción y de vida útil.
4. **Motor de tiempo laboral compartido (`v0.5.0`).** Lo usarán el SLA, los recordatorios por tiempo (EVO-07) y el calendario operativo (EVO-11).
5. **Eventos del sistema.** El actor SISTEMA ya está soportado en el historial y en la auditoría; las automatizaciones lo usarán.

---

## 9. Registro de decisiones

| Fecha | Decisión |
| --- | --- |
| 2026-11-15 | WorkDesk es 100 % local o de intranet, de forma permanente (P1): sin correo, SMS, mensajería, nube, autenticación externa ni APIs de terceros. |
| 2026-11-15 | Flujos ITSM: se comprometen EVO-12, EVO-13 y EVO-14; EVO-15 y EVO-16 quedan a evaluar. |
| 2026-11-15 | Activos: se comprometen EVO-17 a EVO-19; EVO-20 y EVO-21 quedan a evaluar. |
| 2026-11-15 | La ayuda contextual reutiliza la Base de Conocimiento (EVO-06). |
| 2026-11-15 | Las reglas de automatización usan un catálogo cerrado de condiciones y acciones, sin scripting (EVO-07). |

---

## 10. Documentos a actualizar al abordar cada idea

| Ola | Documentos |
| --- | --- |
| 1 | `04` (requisitos de la Base de conocimiento y de satisfacción), `09` (versiones, votos, tipos de artículo, satisfacción), `11` (panel de sugerencias, votación, ayuda), `12` |
| 2 | `04` y `06` (reglas de asignación y ausencias), `09` (reglas, ausencias, tareas, turnos), `10` (scheduler), `11`, `12` |
| 3 | `06` (prioridad sugerida y reglas de incidente masivo), `08` (tipos de ticket), `09` (tipo, plantillas de requerimiento), `11`, `12`; y `10` si EVO-14 cambia el flujo |
| 4 | `03` (permisos sobre activos), `04`, `09` (activos, asignaciones, vínculo con tickets), `11`, `12` |
