# 06. Reglas de Negocio

## WorkDesk

---

# 1. Propósito

Este documento define las reglas de negocio que gobiernan el comportamiento operativo de WorkDesk.

Las reglas aquí establecidas determinan cómo deben gestionarse los tickets, usuarios, asignaciones, prioridades, estados, tiempos de atención, información histórica, comunicaciones y demás elementos relevantes del dominio.

Estas reglas complementan los documentos:

* `01_vision_del_proyecto.md`
* `02_objetivos.md`
* `03_roles_y_permisos.md`
* `04_requisitos_funcionales.md`
* `05_requisitos_no_funcionales.md`

El objetivo es establecer criterios claros y consistentes que permitan:

* Mantener un comportamiento predecible.
* Evitar ambigüedades durante el desarrollo.
* Preservar la integridad de la información.
* Mantener la trazabilidad de las operaciones.
* Representar situaciones reales de operación de equipos de soporte.
* Facilitar la evolución futura de WorkDesk.

Las reglas de negocio establecen **qué condiciones deben respetarse**. Las decisiones relativas a su implementación técnica serán definidas posteriormente en los documentos correspondientes.

---

# 2. Principios generales

## RN-01 — Trazabilidad

Toda acción relevante realizada sobre un ticket debe quedar registrada.

Cuando corresponda, el historial deberá permitir conocer:

* Acción realizada.
* Usuario responsable.
* Fecha y hora.
* Valor anterior.
* Valor nuevo.
* Contexto adicional relevante.

---

## RN-02 — Integridad del historial

El historial de un ticket debe conservar la secuencia de acontecimientos relevantes de su ciclo de vida.

Los registros históricos no deben poder modificarse ni eliminarse mediante las operaciones normales de la aplicación.

Una modificación posterior debe generar un nuevo registro en lugar de sobrescribir el acontecimiento anterior.

---

## RN-03 — Integridad de la auditoría

Las operaciones administrativas relevantes deberán mantener un registro separado de auditoría.

Los registros de auditoría deberán tratarse como información histórica protegida y no podrán ser modificados por los usuarios mediante las operaciones normales del sistema.

---

## RN-04 — Flexibilidad operativa

WorkDesk debe apoyar la realidad operativa de los equipos de soporte sin imponer restricciones artificiales que impidan la gestión humana.

Las reglas de prioridad, asignación, carga de trabajo y flujo deben proporcionar control e información, pero no impedir que los usuarios autorizados tomen decisiones operativas legítimas.

---

## RN-05 — Parametrización

WorkDesk deberá mantener un alto nivel de parametrización para adaptarse a diferentes organizaciones y contextos operativos.

Podrán ser configurables, según corresponda:

* Categorías.
* Prioridades.
* Ubicaciones.
* Grupos.
* Parámetros de SLA.
* Horarios laborales.
* Días hábiles.
* Feriados.
* Motivos.
* Notificaciones.
* Políticas de retención.
* Restricciones de archivos.
* Parámetros de cierre y reapertura.
* Atributos visuales y operativos permitidos del flujo.

La parametrización no deberá permitir alterar elementos estructurales de manera que se comprometa:

* La integridad del ciclo de vida.
* La seguridad.
* La trazabilidad.
* La consistencia de los datos.
* Las relaciones fundamentales del dominio.

---

## RN-06 — Preservación histórica

La modificación, desactivación o reemplazo de elementos configurables no debe alterar retrospectivamente la información histórica.

Los tickets deberán conservar el contexto bajo el cual fueron gestionados.

---

# 3. Identificación y creación de tickets

## RN-07 — Identificador único y correlativo

Cada ticket debe poseer un identificador único y permanente.

Para el MVP se utilizará una numeración correlativa:

```text
#1
#2
#3
#4
...
```

El identificador no deberá reutilizarse.

---

## RN-08 — Búsqueda por identificador

Todo ticket deberá poder localizarse mediante su identificador.

También podrán utilizarse otros criterios definidos en los requisitos funcionales.

---

## RN-09 — Creación por todos los roles principales

Podrán crear tickets:

* Solicitante.
* Técnico.
* Supervisor.
* Administrador.

---

## RN-10 — Creación en nombre de otros usuarios

Los usuarios autorizados podrán crear tickets en nombre de otras personas.

El sistema deberá conservar:

* El usuario que creó originalmente el ticket.
* Los solicitantes asociados.

---

## RN-11 — Múltiples solicitantes

Un ticket puede tener uno o más solicitantes asociados.

Los solicitantes podrán ser agregados o retirados por usuarios autorizados.

---

## RN-12 — Ticket sin solicitante

Un ticket podrá existir sin solicitante asociado.

Este escenario permitirá representar:

* Mantenciones.
* Revisiones preventivas.
* Tareas internas.
* Tickets generados automáticamente.
* Otros procesos donde no exista un solicitante individual.

La ausencia de solicitante no impedirá gestionar, resolver o cerrar el ticket.

---

## RN-13 — Diferenciación entre creador y solicitante

El usuario que crea un ticket y los solicitantes asociados son conceptos independientes.

Cambiar los solicitantes no debe modificar la identidad del creador original.

---

# 4. Información y clasificación del ticket

## RN-14 — Información mínima

Todo ticket deberá contener la información mínima requerida para representar correctamente la solicitud.

Como información obligatoria de creación se consideran:

* Título.
* Descripción.
* Categoría.
* Prioridad.

`Impacto` y `Urgencia` serán atributos opcionales en el MVP. Podrán utilizarse cuando aporten valor para análisis, métricas o clasificación, pero su ausencia no impedirá crear ni gestionar un ticket.

La ubicación física podrá ser obligatoria u opcional según la configuración.

---

## RN-15 — Ubicación física configurable

El sistema deberá permitir asociar una ubicación física cuando corresponda.

Podrá representar:

* Sucursal.
* Oficina.
* Edificio.
* Piso.
* Área.
* Instalación.
* Otra ubicación definida por la organización.

---

## RN-16 — Categoría válida

Todo ticket deberá disponer de una categoría válida.

Cuando el solicitante no pueda determinar la clasificación adecuada, podrá utilizarse una categoría genérica como:

> `Sin clasificar`

Posteriormente, un usuario autorizado podrá corregirla.

---

## RN-17 — Corrección de clasificación

Los usuarios autorizados podrán modificar:

* Categoría.
* Impacto.
* Urgencia.
* Otros atributos de clasificación.

Todo cambio deberá conservar trazabilidad.

---

## RN-18 — Condiciones mínimas para iniciar el trabajo

Antes de que un ticket sea considerado formalmente listo para trabajo deberán encontrarse definidos los elementos operativos requeridos por el flujo.

Como mínimo:

* Categoría.
* Prioridad.
* Grupo responsable.
* Técnico o técnicos responsables, cuando corresponda.

---

# 5. Prioridad

## RN-19 — Asignación manual

La prioridad será establecida manualmente.

No existirá una matriz obligatoria que calcule automáticamente la prioridad a partir de impacto y urgencia.

---

## RN-20 — Niveles iniciales

El MVP considerará inicialmente:

* Baja.
* Media.
* Alta.
* Crítica.

Estos valores deberán ser administrables.

---

## RN-21 — Prioridad como guía operativa

La prioridad representa una referencia para organizar el trabajo.

No constituye una obligación de atender tickets en un orden estricto.

---

## RN-22 — Modificación de prioridad

La prioridad inicial podrá ser establecida durante la creación de acuerdo con los permisos definidos.

Una vez creado el ticket, la modificación de la prioridad quedará reservada a Supervisor y Administrador. El Técnico podrá consultarla y utilizarla como referencia operativa, pero no modificarla.

Toda modificación deberá quedar registrada.

---

## RN-23 — Atención fuera del orden de prioridad

Un ticket de prioridad menor podrá ser atendido, resuelto o cerrado aunque existan otros tickets de mayor prioridad pendientes.

El sistema no deberá bloquear estas acciones únicamente por diferencia de prioridad.

---

# 6. Carga de trabajo

## RN-24 — Múltiples tickets por técnico

Un técnico podrá tener múltiples tickets asignados simultáneamente.

No existirá un límite obligatorio de tickets asignados por técnico.

---

## RN-25 — Múltiples técnicos por ticket

Un ticket podrá tener múltiples técnicos asociados.

La colaboración de varios técnicos deberá conservar la trazabilidad individual de sus intervenciones.

---

## RN-26 — La carga de trabajo no bloquea nuevas asignaciones

Una carga elevada no impedirá automáticamente asignar nuevos tickets.

La gestión de la sobrecarga deberá realizarse mediante información, supervisión y decisiones operativas.

---

## RN-27 — Información de carga

WorkDesk deberá proporcionar información relevante para comprender la carga de trabajo.

Podrá incluir:

* Tickets asignados.
* Tickets activos.
* Tickets en progreso.
* Tickets en espera.
* Tickets críticos.
* Tickets próximos a vencer.
* Tickets fuera de SLA.
* Tickets resueltos.
* Distribución por prioridad.
* Tickets sin actividad reciente.

---

## RN-28 — Advertencias de sobrecarga

Cuando la carga alcance los parámetros definidos como elevados, el sistema podrá informar:

* Al técnico.
* Al Supervisor.
* Mediante dashboards.
* Mediante notificaciones internas.

La advertencia no deberá bloquear nuevas asignaciones.

---

## RN-29 — Redistribución de carga

El Supervisor y el Administrador podrán redistribuir tickets para equilibrar la carga de trabajo.

Toda modificación de asignación deberá conservar historial.

---

## RN-30 — Reasignación masiva por indisponibilidad

Cuando un técnico deje temporal o permanentemente de estar disponible, WorkDesk deberá permitir redistribuir sus tickets mediante una operación centralizada.

Se consideran, entre otros:

* Vacaciones.
* Licencia.
* Renuncia.
* Desvinculación.
* Cambio de funciones.
* Otras causas de indisponibilidad.

La finalidad es evitar que el responsable de la redistribución deba modificar manualmente ticket por ticket.

La operación deberá conservar la información de asignación anterior y nueva.

---

# 7. Escalamiento

## RN-31 — Escalamiento manual

El Supervisor o Administrador podrá escalar un ticket hacia:

* Otro grupo.
* Otro técnico.
* Un nivel superior de atención.

---

## RN-32 — Trazabilidad del escalamiento

El escalamiento deberá registrar, cuando corresponda:

* Grupo anterior.
* Grupo nuevo.
* Técnicos anteriores.
* Técnicos nuevos.
* Usuario que realizó el escalamiento.
* Fecha y hora.

---

## RN-33 — Escalamiento no automático en el MVP

El escalamiento automático provocado por SLA, prioridad, carga u otras reglas complejas no constituye una capacidad obligatoria del MVP.

---

# 8. Estados del ticket

## RN-34 — Estados estructurales

El MVP contará con seis estados estructurales:

1. Nuevo.
2. Asignado.
3. En progreso.
4. En espera.
5. Resuelto.
6. Cerrado.

Estos estados conforman el ciclo de vida base de WorkDesk.

---

## RN-35 — Configuración controlada de estados

Los seis estados estructurales del MVP no podrán:

* Ser eliminados.
* Ser reemplazados.
* Ser multiplicados mediante la creación de nuevos estados estructurales.
* Ser transformados en otro modelo de flujo.

La configuración administrativa podrá modificar únicamente atributos que no rompan la estructura fundamental del ciclo, tales como:

* Nombre visible.
* Color.
* Orden visual.
* Descripción.
* Ayuda contextual.
* Transiciones permitidas dentro del conjunto de estados existentes.

La configuración no deberá permitir:

* Crear nuevos estados estructurales.
* Eliminar estados fundamentales.
* Convertir `Reabierto` en un estado.
* Eliminar `Resuelto`.
* Eliminar `Cerrado`.
* Romper las etapas fundamentales del flujo.
* Crear transiciones que contradigan reglas esenciales de WorkDesk.

---

## RN-36 — Nuevo

`Nuevo` representa un ticket creado que todavía no ha sido formalmente asignado o iniciado.

---

## RN-37 — Asignado

`Asignado` representa un ticket asociado a uno o más técnicos responsables o disponible para ser gestionado por el grupo correspondiente.

---

## RN-38 — En progreso

`En progreso` representa un ticket que está siendo trabajado activamente.

---

## RN-39 — En espera

`En espera` representa un ticket cuya continuidad depende temporalmente de una condición externa.

---

## RN-40 — Resuelto

`Resuelto` representa un ticket cuya solución ha sido aplicada y que queda pendiente del proceso de validación correspondiente.

---

## RN-41 — Cerrado

`Cerrado` representa el término operativo del ticket.

El cierre no elimina la información ni el historial.

---

## RN-42 — Reapertura no es un estado

La reapertura es una acción que devuelve un ticket a un estado operativo.

`Reabierto` no constituye un estado independiente dentro del modelo base del MVP.

---

# 9. Transiciones de estados

## RN-43 — Transiciones controladas

Las transiciones deberán respetar:

* Rol.
* Permisos.
* Estado actual.
* Reglas de negocio.
* Integridad del flujo.

Como comportamiento predeterminado del MVP, un usuario Técnico autorizado podrá operar sobre tickets aunque no esté asignado formalmente a ellos. La asignación y la pertenencia a grupos son mecanismos de organización y trazabilidad, no prerrequisitos obligatorios para ejecutar acciones operativas.

La resolución podrá producirse desde `Nuevo`, `Asignado`, `En progreso` o `En espera`. El cierre directo podrá producirse desde esos mismos estados. Las restricciones administrativas podrán limitar estas transiciones, pero no crear estados ni combinaciones que rompan la integridad estructural.

---

## RN-44 — Flujo operativo principal

El flujo habitual podrá seguir:

```text
Nuevo
  ↓
Asignado
  ↓
En progreso
  ↓
En espera
  ↓
En progreso
  ↓
Resuelto
  ↓
Cerrado
```

No todas las etapas serán obligatorias en todos los tickets.

---

## RN-45 — Reapertura desde Resuelto

Cuando un solicitante rechace una resolución, el ticket deberá reabrirse y regresar a un estado operativo, normalmente:

> En progreso

---

## RN-46 — Reapertura desde Cerrado

Un ticket cerrado podrá ser reabierto por usuarios autorizados según las políticas correspondientes.

Como comportamiento general regresará a:

> En progreso

---

## RN-47 — Conservación de contexto

La reapertura no debe eliminar información existente.

Deberá conservar:

* Historial.
* Técnicos participantes.
* Solicitantes.
* Comentarios.
* Archivos.
* Resoluciones anteriores.

---

# 10. Estado En espera

## RN-48 — Uso legítimo

`En espera` deberá utilizarse cuando exista una dependencia real que impida continuar temporalmente el trabajo.

Ejemplos:

* Información del solicitante.
* Respuesta de terceros.
* Aprobación.
* Repuestos.
* Disponibilidad.
* Dependencias externas.

---

## RN-49 — Motivo de espera

El sistema deberá permitir registrar un motivo de espera mediante un catálogo configurable.

En el MVP, el motivo será opcional: la ausencia de motivo no impedirá por sí sola pasar el ticket a `En espera`. Cuando se registre un motivo, deberá conservarse como parte del contexto histórico de la espera.

---

## RN-50 — Efecto sobre SLA

El comportamiento del SLA durante `En espera` dependerá de la política configurada.

Podrá establecerse que determinados motivos:

* Pausen el SLA.
* Mantengan el SLA activo.

---

## RN-51 — Tickets sin solicitante

Cuando un ticket no tenga solicitantes asociados, no se requerirá validación de usuario para su cierre.

Si el ticket es marcado como Resuelto, deberá respetarse igualmente el período de espera configurado para el cierre automático.

La ausencia de solicitantes no deberá provocar el cierre automático inmediato.

Los tickets sin solicitante podrán utilizar el mecanismo de cierre directo cuando corresponda a la situación operativa.

---

# 11. Resolución

## RN-52 — Resolución

Un usuario técnico autorizado podrá marcar un ticket como:

> Resuelto

cuando considere que la solución ha sido aplicada.

---

## RN-53 — Resolución siempre sujeta a validación

Todo ticket marcado como `Resuelto` deberá entrar en el mecanismo de validación correspondiente.

La validación podrá ser realizada por cualquiera de los solicitantes autorizados asociados al ticket.

---

## RN-54 — Validación positiva

Cuando cualquiera de los solicitantes autorizados confirme que la solución es satisfactoria, el ticket podrá pasar a:

> Cerrado

La confirmación de un solicitante será suficiente para cerrar el ticket completo.

---

## RN-55 — Rechazo de resolución

Si un solicitante considera que la solución no es satisfactoria, podrá rechazarla y reabrir el ticket.

El solicitante deberá disponer de la posibilidad de agregar un comentario público describiendo la situación.

---

## RN-56 — Ticket resuelto sin solicitante

Cuando un ticket haya sido marcado como `Resuelto` y no tenga solicitantes asociados, el sistema deberá aplicar igualmente el mecanismo de espera configurado antes del cierre automático.

No deberá suponerse que la ausencia de solicitante equivale a aprobación inmediata.

---

# 12. Cierre

## RN-57 — Cierre normal por validación

El cierre normal podrá producirse cuando un solicitante confirme satisfactoriamente una resolución.

---

## RN-58 — Cierre automático por falta de validación

Si un ticket se encuentra en `Resuelto` y ningún solicitante acepta ni rechaza la resolución durante el período configurado, el sistema podrá cerrarlo automáticamente.

El período predeterminado será de:

> **24 horas**

Este valor deberá poder modificarse mediante configuración administrativa.

---

## RN-59 — Cierre automático para tickets sin solicitante

Cuando un ticket se encuentre en `Resuelto` y no tenga solicitantes asociados, deberá aplicarse igualmente el período de espera configurado antes del cierre automático.

El valor predeterminado será de 24 horas.

---

## RN-60 — Cierre directo por Técnico

Un Técnico autorizado podrá cerrar directamente un ticket sin necesidad de que previamente haya pasado por `Resuelto`.

El Técnico podrá realizar este cierre desde `Nuevo`, `Asignado`, `En progreso` o `En espera`, cuando corresponda operativamente.

No se aplicará cierre directo desde `Resuelto`; dicho estado seguirá su mecanismo de validación, cierre automático o cierre excepcional autorizado.

Esta capacidad permitirá gestionar situaciones como:

* Mantenciones.
* Tickets automáticos.
* Tareas rutinarias.
* Solicitudes internas.
* Casos previamente validados por otros medios.

El cierre directo no requerirá autorización previa del Supervisor.

---

## RN-61 — Cierre directo por Supervisor y Administrador

Los Supervisores y Administradores también podrán cerrar directamente tickets dentro del alcance de sus permisos.

Los cierres excepcionales deberán mantener trazabilidad.

---

## RN-62 — Diferencia entre Resuelto y Cerrado directamente

`Resuelto` y `Cerrado` representan acciones diferentes.

Cuando un usuario marque un ticket como `Resuelto`:

* Debe iniciarse el proceso de validación.
* Debe notificarse al solicitante cuando exista.
* Debe aplicarse el período de espera configurado.

Cuando un usuario autorizado cierre directamente:

* El ticket pasa a `Cerrado`.
* No requiere pasar previamente por `Resuelto`.
* Debe registrarse como cierre directo.

---

## RN-63 — Cierre como finalización operativa

`Cerrado` representa el término operativo del ticket, pero no implica eliminación de la información histórica.

---

## RN-64 — Motivo de cierre

El sistema deberá permitir registrar el motivo del cierre.

Los motivos podrán incluir, entre otros:

* Resuelto.
* Duplicado.
* Cancelación administrativa.
* Otro motivo configurado.

El motivo de cierre no constituye un estado independiente.

---

## RN-65 — Cancelación sin estado propio

El MVP no incorporará `Cancelado` como estado.

Las situaciones de cancelación se gestionarán mediante cierre con el motivo correspondiente.

---

# 13. Reapertura

## RN-66 — Reapertura por solicitante

Un solicitante autorizado podrá reabrir un ticket cuando la política de reapertura lo permita.

La acción deberá ser explícita.

---

## RN-67 — Comentario posterior a reapertura

Después de reabrir un ticket, el solicitante podrá agregar un comentario público explicando la situación.

El comentario deberá notificar a los técnicos correspondientes.

---

## RN-68 — Ticket antiguo no validado

Cuando un ticket antiguo no haya sido validado oportunamente, el solicitante podrá utilizar la acción:

> Reabrir ticket

para retomarlo.

Después podrá agregar un comentario público que permita contextualizar la necesidad de reanudar el trabajo.

---

## RN-69 — Reapertura por Técnico

Un Técnico autorizado podrá reabrir un ticket cuando sea necesario continuar el trabajo o corregir una resolución anterior.

---

## RN-70 — Reapertura por Supervisor y Administrador

El Supervisor y el Administrador podrán reabrir tickets dentro de sus atribuciones.

---

## RN-71 — Conservación de técnicos

Al reabrir un ticket, los técnicos que participaron anteriormente deberán conservarse inicialmente.

La asignación podrá modificarse posteriormente.

---

## RN-72 — Notificación de reapertura

La reapertura deberá generar las notificaciones internas correspondientes.

---

## RN-73 — Período de reapertura configurable

El período durante el cual un ticket podrá reabrirse será configurable por el Administrador.

---

# 14. Tickets duplicados y relacionados

## RN-74 — Detección de posibles duplicados

WorkDesk podrá advertir sobre posibles tickets duplicados mediante coincidencias relevantes.

La advertencia no deberá impedir necesariamente la creación.

---

## RN-75 — Vinculación de tickets

Los tickets duplicados o relacionados deberán poder vincularse.

---

## RN-76 — Identificación del ticket original

La relación deberá permitir identificar:

* Ticket original.
* Ticket duplicado.
* Relación existente.

---

## RN-77 — Cierre por duplicidad

Un ticket identificado como duplicado podrá cerrarse utilizando el correspondiente motivo de cierre.

No se requiere un estado independiente `Duplicado`.

---

# 15. Comentarios y notas internas

## RN-78 — Comentarios públicos

Los comentarios públicos forman parte de la comunicación del ticket y deben conservarse cronológicamente.

---

## RN-79 — Notas internas

Las notas internas están destinadas exclusivamente a la comunicación del equipo autorizado.

No podrán ser vistas por los Solicitantes.

---

## RN-80 — Colaboración técnica

Los Técnicos autorizados podrán colaborar sobre tickets aun cuando no hayan sido quienes los crearon o los tomaron inicialmente.

Las intervenciones individuales deberán mantenerse identificadas.

---

# 16. Archivos adjuntos

## RN-81 — Archivos asociados

Los archivos adjuntos forman parte de la información del ticket.

---

## RN-82 — Acceso controlado

Los archivos solo podrán ser consultados por usuarios autorizados para acceder al ticket correspondiente.

---

## RN-83 — Restricciones configurables

Los límites de:

* Tamaño.
* Cantidad.
* Tipos de archivo.

deberán poder configurarse.

---

## RN-84 — Trazabilidad de archivos

Las operaciones relevantes sobre archivos deberán conservar trazabilidad.

---

# 17. SLA

## RN-85 — SLA asociado al ticket

El SLA pertenece al ticket y no al Técnico individual.

---

## RN-86 — SLA no bloqueante

El incumplimiento de un SLA no impedirá:

* Continuar trabajando.
* Resolver.
* Cerrar.

---

## RN-87 — Carga de trabajo y SLA

La existencia de múltiples tickets asignados a un Técnico no detendrá automáticamente el SLA de ninguno de ellos.

---

## RN-88 — SLA y prioridad

El SLA podrá estar asociado a la prioridad configurada.

Cuando cambie la prioridad, el comportamiento del SLA deberá seguir la política configurada.

---

## RN-89 — SLA en espera

El comportamiento del SLA durante `En espera` deberá seguir la configuración correspondiente.

---

## RN-90 — Horario del SLA

El cálculo del SLA podrá considerar:

* Horario laboral.
* Días hábiles.
* Feriados.

Estos elementos deberán ser configurables.

---

## RN-91 — Vencimiento de SLA

Cuando un ticket alcance o supere el límite configurado, WorkDesk deberá poder:

* Informar visualmente la condición.
* Generar una notificación.
* Registrar el incumplimiento.

Las acciones automáticas avanzadas no serán obligatorias en el MVP.

---

## RN-92 — Gestión del SLA por rol

El Técnico podrá consultar la situación de SLA de los tickets sobre los que tenga acceso, pero no podrá alterar administrativamente el SLA.

El Supervisor podrá:

* Gestionar excepciones operativas.
* Aplicar acciones autorizadas sobre situaciones particulares.

El Administrador podrá:

* Configurar políticas.
* Definir tiempos.
* Configurar horarios.
* Definir días hábiles.
* Definir feriados.
* Gestionar excepciones administrativas.
* Modificar parámetros generales.
* Habilitar o deshabilitar comportamientos configurables.

Las acciones manuales relacionadas con SLA deberán quedar registradas.

---

# 18. Notificaciones

## RN-93 — Notificaciones internas

El MVP utilizará notificaciones internas dentro de WorkDesk.

---

## RN-94 — Eventos relevantes

Podrán generar notificaciones:

* Creación.
* Asignación.
* Reasignación.
* Cambio de estado.
* Resolución.
* Reapertura.
* Comentarios.
* Eventos relevantes de SLA.
* Otros eventos configurados.

---

## RN-95 — Notificación de resolución

Cuando un ticket pase a `Resuelto`, los solicitantes asociados deberán recibir una notificación que les permita acceder al ticket y revisar la resolución.

---

## RN-96 — Notificación posterior a reapertura

Cuando un solicitante reabra un ticket, los técnicos correspondientes deberán recibir una notificación para informar que el trabajo debe retomarse.

---

## RN-97 — Configuración de notificaciones

El Administrador podrá configurar los eventos y destinatarios permitidos por el sistema.

---

# 19. Visibilidad y colaboración

## RN-98 — Acceso del Solicitante

El Solicitante podrá acceder únicamente a tickets donde se encuentre autorizado como participante.

---

## RN-99 — Acceso del Técnico

Como comportamiento predeterminado del MVP, el Técnico podrá acceder y operar sobre tickets de cualquier grupo, incluso cuando no pertenezca al grupo asociado ni se encuentre formalmente asignado al ticket.

Un Técnico con acceso podrá realizar las mismas acciones operativas permitidas a un Técnico asignado, incluyendo consultar, comentar, registrar notas internas, adjuntar archivos, cambiar estados permitidos, resolver y cerrar directamente cuando corresponda.

La asignación y la pertenencia a grupos se conservarán como mecanismos de organización, responsabilidad, carga de trabajo y trazabilidad. El Administrador podrá configurar restricciones de visibilidad u operación cuando la organización lo requiera.

---

## RN-100 — Acceso del Supervisor

El Supervisor deberá contar con visibilidad suficiente para:

* Supervisar tickets.
* Gestionar carga.
* Reasignar.
* Escalar.
* Gestionar excepciones.

---

## RN-101 — Acceso del Administrador

El Administrador contará con acceso administrativo amplio de acuerdo con sus privilegios.

---

# 20. Usuarios desactivados

## RN-102 — Conservación histórica

La desactivación de un usuario no debe eliminar su información histórica.

---

## RN-103 — Autor histórico

Un usuario desactivado deberá continuar apareciendo como autor de:

* Tickets.
* Comentarios.
* Acciones.
* Asignaciones.
* Registros históricos.

---

## RN-104 — Tickets de técnico desactivado

Los tickets activos de un Técnico desactivado deberán permanecer disponibles para su redistribución.

---

# 21. Retención de información

## RN-105 — Retención configurable

Las políticas de retención deberán ser configurables por el Administrador.

Podrán aplicarse a:

* Tickets.
* Historial.
* Auditoría.
* Notificaciones.
* Archivos.
* Logs.

---

## RN-106 — Habilitación explícita

Ninguna política de retención, archivo o eliminación deberá ejecutarse automáticamente sin una configuración administrativa previa que la habilite explícitamente.

---

## RN-107 — Parámetros de retención

El Administrador deberá poder definir, cuando corresponda:

* Información afectada.
* Período.
* Acción posterior.
* Condiciones de aplicación.

---

## RN-108 — Acciones posteriores

Las políticas podrán definir como acción:

* Mantener.
* Archivar.
* Eliminar.

---

## RN-109 — Auditoría de políticas

Toda creación, modificación, activación o desactivación de políticas de retención deberá quedar registrada en auditoría.

---

## RN-110 — Integridad durante retención

La ejecución de una política de retención no deberá producir referencias inconsistentes entre:

* Tickets.
* Historial.
* Usuarios.
* Archivos.
* Auditoría.
* Notificaciones.

---

# 22. Seguridad e integridad operativa

## RN-111 — Mínimo privilegio

Los usuarios solo podrán ejecutar operaciones autorizadas por su rol y permisos.

---

## RN-112 — Validación en backend

Las restricciones de negocio deberán validarse en backend.

No será suficiente ocultar acciones solamente en la interfaz.

---

## RN-113 — Confirmación de acciones críticas

Las acciones potencialmente destructivas o de alto impacto deberán requerir confirmación explícita cuando corresponda.

Entre ellas:

* Eliminación de tickets.
* Cambios de rol.
* Desactivación de usuarios.
* Restauraciones.
* Operaciones administrativas críticas.

---

# 23. Concurrencia y edición

## RN-114 — Integridad ante concurrencia

Cuando varios usuarios intenten operar simultáneamente sobre un mismo recurso, WorkDesk deberá impedir que la situación produzca:

* Pérdida de información.
* Datos inconsistentes.
* Estados inválidos.
* Asignaciones contradictorias.

---

## RN-115 — Exclusividad temporal de edición

Cuando un usuario esté modificando un ticket, ese recurso deberá quedar temporalmente bloqueado para edición por otros usuarios.

Los demás usuarios podrán consultar la información, pero no podrán modificar simultáneamente el mismo recurso mientras el bloqueo permanezca activo.

---

## RN-116 — Identificación del usuario editor

Cuando un recurso se encuentre bloqueado, WorkDesk deberá informar, cuando corresponda, qué usuario lo está editando.

---

## RN-117 — Liberación del bloqueo

Una vez finalizada la edición y liberado el recurso, otro usuario podrá modificarlo.

El mecanismo técnico utilizado para controlar la concurrencia se definirá posteriormente en arquitectura.

---

# 24. Auditoría administrativa

## RN-118 — Acciones administrativas

Deberán registrarse las operaciones administrativas relevantes, incluyendo cuando corresponda:

* Gestión de usuarios.
* Cambios de roles.
* Activación y desactivación.
* Configuración.
* Eliminaciones.
* Restauraciones.
* Cambios relevantes de seguridad.
* Cambios de políticas de retención.

---

## RN-119 — Inmutabilidad

Los registros de auditoría deberán mantenerse como información histórica protegida.

No podrán ser modificados mediante las operaciones normales de la aplicación.

---

# 25. Configuración administrativa

## RN-120 — Administración centralizada

Los elementos configurables deberán administrarse desde un área restringida a usuarios autorizados.

---

## RN-121 — Configuración de elementos operativos

Cuando corresponda, el Administrador podrá configurar:

* Categorías.
* Prioridades.
* Grupos.
* Ubicaciones.
* SLA.
* Horarios.
* Feriados.
* Notificaciones.
* Retención.
* Restricciones de archivos.
* Cierre.
* Reapertura.
* Atributos permitidos de los estados.

---

## RN-122 — Configuración sin alteración estructural

La configuración administrativa deberá adaptar el comportamiento permitido por WorkDesk, pero no permitirá reconstruir arbitrariamente el modelo fundamental del sistema.

---

## RN-123 — Auditoría de configuración

Los cambios relevantes de configuración deberán quedar registrados en auditoría.

---

# 26. Configuración inicial

## RN-124 — Inicialización del sistema

La instalación o primera ejecución de WorkDesk deberá contemplar un proceso de inicialización administrativa.

---

## RN-125 — Administrador inicial

El sistema deberá permitir establecer una cuenta inicial de Administrador.

Cuando se utilicen credenciales temporales, deberán cambiarse antes de finalizar la configuración inicial.

---

## RN-126 — Configuración inicial predeterminada

WorkDesk deberá disponer de una configuración inicial que permita comenzar a utilizar el sistema sin requerir configurar todos sus elementos manualmente.

Podrá incluir:

* Categorías iniciales.
* Prioridades.
* Estados.
* Parámetros básicos de SLA.
* Configuraciones esenciales.

---

# 27. Respaldos y recuperación

## RN-127 — Respaldo de información

Los respaldos deberán considerar:

* Base de datos.
* Archivos adjuntos.

---

## RN-128 — Gestión administrativa

La generación y restauración de respaldos deberá estar restringida a usuarios autorizados, principalmente el Administrador.

---

## RN-129 — Integridad de restauración

Una restauración deberá procurar conservar la consistencia entre:

* Tickets.
* Usuarios.
* Historial.
* Auditoría.
* Archivos.

---

# 28. Automatización

## RN-130 — Gestión manual como principio del MVP

La asignación, reasignación, priorización, escalamiento y distribución de carga serán principalmente procesos manuales durante el MVP.

---

## RN-131 — Automatizaciones básicas permitidas

Se permitirán automatizaciones simples necesarias para el funcionamiento del sistema, tales como:

* Cálculo de SLA.
* Notificaciones.
* Cierre automático por inactividad.
* Comportamientos derivados directamente de una acción explícita.

---

## RN-132 — Automatizaciones avanzadas fuera del MVP

No serán obligatorias en el MVP:

* Asignación automática avanzada.
* Reasignación automática por carga.
* Escalamiento automático.
* Cambio automático avanzado de prioridad.
* Workflows dinámicos.
* Reglas de negocio arbitrariamente creadas por usuarios.
* Inteligencia artificial para clasificación o gestión.

Estas capacidades podrán incorporarse posteriormente.

---

# 29. Experiencia y comunicación

## RN-133 — Lenguaje comprensible

Los mensajes destinados a usuarios deberán utilizar lenguaje claro y comprensible.

---

## RN-134 — Retroalimentación

Las operaciones relevantes deberán informar adecuadamente su resultado.

---

## RN-135 — Comunicación sobre resolución

Cuando una resolución requiera validación, el solicitante deberá recibir información suficiente para:

* Revisar la solución.
* Aceptarla.
* Rechazarla.
* Reabrir el ticket.

---

## RN-136 — Comunicación sobre reapertura

Cuando un ticket sea reabierto, los participantes técnicos correspondientes deberán ser informados para permitir la continuidad del trabajo.

---

# 30. Reglas derivadas de situaciones operativas reales

## RN-137 — Continuidad ante ausencia de técnicos

La indisponibilidad de un Técnico no deberá provocar pérdida de tickets ni impedir continuar con su atención.

---

## RN-138 — Redistribución eficiente

Cuando sea necesario transferir múltiples tickets de un Técnico a otro, WorkDesk deberá proporcionar mecanismos que reduzcan la intervención repetitiva.

---

## RN-139 — Conservación de contexto durante transferencia

Una transferencia o reasignación, individual o masiva, no deberá eliminar:

* Historial.
* Comentarios.
* Archivos.
* Soluciones.
* Participantes anteriores.
* Información relevante.

---

# 31. Principios fundamentales del MVP

## RN-140 — Integridad sobre conveniencia

Ninguna operación o configuración deberá comprometer la integridad de la información para simplificar una tarea administrativa.

---

## RN-141 — Trazabilidad permanente

Toda acción relevante deberá poder ser reconstruida posteriormente mediante información histórica confiable.

---

## RN-142 — Flexibilidad operativa

WorkDesk no deberá obligar al equipo de soporte a trabajar siguiendo un único criterio rígido cuando la realidad operacional requiera una decisión diferente.

---

## RN-143 — Seguridad transversal

Las reglas de seguridad deberán aplicarse a todas las funcionalidades.

---

## RN-144 — Configuración responsable

La alta parametrización de WorkDesk debe utilizarse para adaptar el sistema a distintas organizaciones, pero nunca para permitir configuraciones que destruyan las reglas fundamentales de integridad, seguridad o trazabilidad.

---

## RN-145 — Evolución controlada

La evolución futura del producto deberá realizarse sin sacrificar la estabilidad, integridad y mantenibilidad del núcleo existente.

---

# 32. Resumen de reglas principales

| Área                    | Regla principal                                  |
| ----------------------- | ------------------------------------------------ |
| Identificación          | Numeración correlativa única                     |
| Solicitantes            | Uno o más solicitantes por ticket                |
| Ticket sin solicitante  | Permitido                                        |
| Técnicos                | Uno o más técnicos por ticket                    |
| Carga                   | Sin límite obligatorio                           |
| Reasignación masiva     | Permitida y parte del MVP                        |
| Prioridad               | Manual y modificable                             |
| Orden de atención       | Flexible                                         |
| Estados                 | Seis estados estructurales                       |
| Estados configurables   | Solo atributos no estructurales                  |
| Reapertura              | Acción, no estado                                |
| Resolución              | Siempre entra en validación                      |
| Validación              | Cualquier solicitante autorizado puede confirmar |
| Validación positiva     | Cierra el ticket                                 |
| Falta de respuesta      | Cierre automático configurable                   |
| Tiempo predeterminado   | 24 horas                                         |
| Sin solicitante         | También aplica período de espera                 |
| Cierre directo          | Técnico puede cerrar desde estados anteriores    |
| Cierre directo          | No requiere autorización de Supervisor           |
| Cancelación             | Se maneja mediante motivo de cierre              |
| Duplicados              | Vinculación + motivo de cierre                   |
| En espera               | Dependencia externa                              |
| SLA                     | Asociado al ticket                               |
| SLA                     | Solo Supervisor/Admin pueden gestionarlo         |
| SLA en espera           | Comportamiento configurable                      |
| Notificaciones          | Internas                                         |
| Auditoría               | Protegida e histórica                            |
| Retención               | Configurable y explícitamente habilitada         |
| Concurrencia            | Edición exclusiva temporal                       |
| Configuración           | Amplia pero con límites estructurales            |
| Automatización avanzada | Fuera del MVP                                    |
| Principio central       | Integridad + trazabilidad + flexibilidad         |

---

# 33. Criterio rector de WorkDesk

Todas las reglas anteriores pueden resumirse en el siguiente principio:

> **WorkDesk debe proporcionar flexibilidad para gestionar situaciones reales de soporte sin sacrificar la integridad, seguridad y trazabilidad de la información.**

El sistema debe permitir que los equipos operen de acuerdo con sus necesidades reales, manteniendo al mismo tiempo suficiente información para comprender posteriormente:

* Qué ocurrió.
* Quién participó.
* Qué decisiones se tomaron.
* Cuándo ocurrieron.
* Cómo evolucionó el ticket.
* Qué información fue modificada.
* Cómo terminó el proceso.

La flexibilidad operativa y la trazabilidad constituyen principios complementarios del diseño de WorkDesk.

---

## Fin del documento
