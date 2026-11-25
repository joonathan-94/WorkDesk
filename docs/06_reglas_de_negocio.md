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

Una vez creado el ticket, la modificación de la prioridad estará permitida a Técnico, Supervisor y Administrador. El Solicitante no puede modificarla después de la creación.

Toda modificación exige indicar un motivo y deberá quedar registrada con la prioridad anterior, la prioridad nueva, el usuario responsable, la fecha y el motivo.

No se puede modificar la prioridad de un ticket `Cerrado`; primero debe reabrirse. Establecer la misma prioridad que ya tiene el ticket no genera cambio ni registro.

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

Cuando cambie la prioridad se cierra el período de SLA vigente y se abre uno nuevo con la política de la nueva prioridad. El cambio nunca reinicia el reloj:

* **Continuidad del consumo.** El tiempo de SLA ya consumido se conserva. El nuevo vencimiento es el momento del cambio más la diferencia entre el objetivo de la nueva prioridad y el consumo acumulado, calculada en horario laboral.
* **Incumplimiento permanente.** Un vencimiento ya registrado (RN-91) no se borra por un cambio posterior de prioridad.
* **Subida de prioridad.** Si el consumo acumulado ya supera el nuevo objetivo, el ticket pasa de inmediato a vencido y se generan las notificaciones correspondientes.
* **Bajada de prioridad con SLA en riesgo.** Si el SLA está en "próximo a vencer" o "vencido", la bajada está permitida a los tres roles con motivo obligatorio y se notifica a los Supervisores.
* **Ticket en espera.** Si el SLA está pausado por `En espera`, el período nuevo nace pausado y no consume tiempo hasta reanudarse.
* **Primera respuesta.** Si ya se cumplió, no se vuelve a evaluar; si no, conserva su tiempo consumido.

El período nuevo registra como usuario y motivo del cambio los del cambio de prioridad. Estos cambios no son excepciones de SLA (RN-92) y no requieren permisos de Supervisor.

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

El Técnico podrá consultar la situación de SLA de los tickets sobre los que tenga acceso, pero no podrá alterar administrativamente el SLA. Cambiar la prioridad (RN-22) no es una alteración administrativa: sus efectos sobre el SLA están acotados por RN-88.

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

## RN-146 — Gestión de grupos por el Supervisor

Los grupos son opcionales: un ticket puede asignarse directamente a técnicos sin pertenecer a ningún grupo.

El Administrador crea, desactiva y configura los grupos y designa a sus supervisores responsables. Un grupo puede tener varios supervisores responsables.

Un Supervisor puede gestionar las membresías de técnicos y las asignaciones únicamente de los grupos en los que figura como supervisor responsable. No puede crear, desactivar ni configurar grupos, ni modificar los supervisores responsables.

Los grupos no se eliminan físicamente; se desactivan. Las membresías y designaciones finalizadas se conservan como histórico. Si un usuario deja de tener el rol Supervisor, sus designaciones vigentes finalizan.

**Implementación (`v0.4.0`, entrega 4).**

* **Acceso.** Las pantallas de grupos (`/groups`) son del Administrador y de los Supervisores; el Técnico y el Solicitante reciben 403. El Administrador ve todos los grupos. El Supervisor ve **solo los grupos de los que es responsable vigente**: cualquier otro responde 404, igual que uno inexistente, para no revelar qué grupos existen.
* **Quién hace qué.** Solo el Administrador crea, edita, activa y desactiva grupos, y designa o retira supervisores responsables. El Administrador y el Supervisor responsable agregan y retiran técnicos de sus grupos. Todo se comprueba en backend.
* **Técnicos.** Solo un Técnico activo puede ser miembro; una persona no puede figurar dos veces como miembro vigente del mismo grupo (puede volver a entrar tras ser retirada, con una membresía nueva). Un técnico puede estar en varios grupos y la pertenencia no limita lo que ve ni lo que hace (RN-43).
* **Supervisores responsables.** Solo un Supervisor activo puede ser designado. Un grupo puede tener varios y también ninguno: sin responsable, solo el Administrador gestiona sus técnicos.
* **Grupo desactivado.** Conserva sus miembros y responsables, pero no admite cambios en ellos hasta reactivarlo.
* **Cambios en las cuentas.** Si un usuario deja de ser Técnico, se cierran sus membresías; si deja de ser Supervisor, sus designaciones; si se desactiva, ambas. Reactivarlo no las restaura. Cada cierre se audita con su motivo y el historial se conserva.
* **Auditoría.** Cada acción queda en la auditoría administrativa con `entidad_tipo` `grupo`: `GRUPO_CREADO`, `GRUPO_MODIFICADO`, `GRUPO_ACTIVADO`, `GRUPO_DESACTIVADO`, `GRUPO_MIEMBRO_AGREGADO`, `GRUPO_MIEMBRO_RETIRADO`, `GRUPO_SUPERVISOR_DESIGNADO` y `GRUPO_SUPERVISOR_RETIRADO`. Retirar y desactivar admiten un motivo opcional.
* **Nombre único** sin distinguir mayúsculas. La asignación de un grupo a los tickets llega con la entrega de asignación.

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

## RN-147 — Contraseñas temporales y cambio obligatorio

El Administrador crea las cuentas y restablece contraseñas mediante una contraseña temporal, que puede escribir o solicitar que el sistema genere. Una contraseña generada se muestra una sola vez.

Una cuenta con contraseña temporal queda marcada para cambio obligatorio. Hasta que el usuario cambie su contraseña solo puede acceder a la pantalla de cambio de contraseña y cerrar sesión; el sistema lo aplica en backend.

Al crear o restablecer una contraseña, las sesiones anteriores del usuario quedan invalidadas. El restablecimiento además limpia los intentos fallidos y el bloqueo temporal.

Al cambiar su contraseña, el usuario debe indicar la actual; la nueva debe cumplir la política de contraseñas (longitud mínima configurada, 12 por defecto) y ser distinta de la actual. La sesión desde la que se realizó el cambio se mantiene y las demás se invalidan. Indicar una contraseña actual incorrecta cuenta como un intento fallido y respeta el bloqueo temporal: si se alcanza el máximo de intentos, la sesión se cierra, y mientras la cuenta esté bloqueada no se acepta ningún cambio de contraseña.

Las contraseñas, temporales o definitivas, nunca se almacenan en texto plano ni se registran en logs, auditoría ni historial. Los hechos (creación de cuenta, restablecimiento, cambio) sí se auditan sin incluir la contraseña.

---

## RN-148 — Identificadores de usuario

El **username** identifica al usuario en el inicio de sesión y en los registros históricos:

* Tiene entre 3 y 50 caracteres.
* Solo admite letras minúsculas, números, punto, guion y guion bajo, y empieza por una letra o un número.
* Se normaliza a minúsculas y es único.
* No se puede cambiar después de crear la cuenta.

El **correo electrónico** es único, se normaliza a minúsculas y se valida solo en su forma (`algo@dominio.tld`); no se comprueba que la dirección exista. Tiene un máximo de 254 caracteres.

Las comparaciones de unicidad ignoran mayúsculas y minúsculas. El nombre y el apellido son obligatorios; teléfono, cargo y departamento o área son opcionales.

Cuando el Administrador crea una cuenta, el usuario queda activo y con el cambio de contraseña pendiente (RN-147). Si la contraseña temporal fue generada por el sistema, se muestra una sola vez, en la respuesta de la creación: no se guarda ni se puede consultar después, y la respuesta no se almacena en caché del navegador.

---

## RN-149 — Administración de usuarios existentes

Solo el Administrador administra usuarios. Cada acción se comprueba en backend y deja un registro en la auditoría administrativa.

* **Edición de datos:** nombre, apellido, correo, teléfono, cargo y departamento o área. El username no se puede cambiar. Si no hay cambios, no se registra nada. La auditoría guarda el valor anterior y el nuevo de cada campo modificado.
* **Cambio de rol:** requiere una pantalla de confirmación explícita y admite un motivo opcional. Cierra las sesiones abiertas del usuario, que entra de nuevo con los permisos del nuevo rol. Cuando existan los grupos, un Técnico que cambie de rol dejará de ser miembro de sus grupos conservando el historial (`docs/09`, sección 9.2).
* **Desactivación:** requiere confirmación explícita y admite un motivo opcional. El usuario no puede iniciar sesión y se cierran sus sesiones abiertas. Su historial se conserva, y se registra quién desactivó la cuenta y cuándo. Nunca se elimina físicamente a un usuario.
* **Reactivación:** limpia los datos de la desactivación, los intentos fallidos y el bloqueo temporal. Conserva la contraseña anterior y las sesiones cerradas no reviven.
* **Restablecimiento de contraseña:** sigue la regla RN-147. No se aplica a la propia cuenta del Administrador, que usa el cambio de contraseña propio.

Salvaguardas:

* Un Administrador **no puede** cambiar su propio rol, desactivar su propia cuenta ni restablecer su propia contraseña desde la administración.
* **Siempre debe quedar al menos un Administrador activo.** No se permite desactivar a un Administrador ni cambiarle el rol si no quedaría otro activo; los Administradores inactivos no cuentan. La comprobación bloquea las filas de los Administradores activos para que dos Administradores no puedan dejar el sistema sin ninguno actuando a la vez.
* El correo no puede coincidir con el de otro usuario (sin distinguir mayúsculas).

---

## RN-150 — Mi cuenta

Todo usuario autenticado, sea cual sea su rol, dispone de una pantalla "Mi cuenta" donde:

* Consulta sus datos: nombre, usuario, correo y rol.
* Edita su **información de contacto**: teléfono, cargo y departamento o área.
* Accede al cambio de su contraseña (RN-147).

El nombre, el apellido, el correo, el username y el rol **solo los gestiona el Administrador**: aunque el envío del formulario incluya esos campos, se ignoran.

El usuario solo puede editar su propia cuenta; la pantalla no recibe el identificador de ningún usuario. Los cambios se validan igual que cuando los realiza el Administrador (RN-148) y quedan en la auditoría administrativa como una modificación de usuario realizada por el propio usuario, con los valores anteriores y nuevos de los campos que cambiaron. Si no hay cambios, no se registra nada.

"Mi cuenta" no muestra acciones administrativas ni permisos del rol. Mientras el usuario tenga un cambio de contraseña obligatorio pendiente (RN-147), no puede acceder a ella.

---

## RN-151 — Datos de demostración

Los datos de demostración son opcionales y nunca forman parte de la instalación normal. Se cargan con un comando explícito (`seed-demo`) y:

* Son personas ficticias, con correos en el dominio reservado `workdesk.local`.
* No incluyen ningún Administrador: el Administrador real lo crea la instalación (`create-admin`).
* Comparten una contraseña que se indica al ejecutar el comando; no se guarda en el repositorio, ni se muestra, ni se registra.
* Se cargan de forma idempotente: quien ya existe se omite sin modificarse.
* No se pueden cargar cuando el entorno es de producción.
* Cada creación se audita como una acción del sistema.
* **No incluyen datos de configuración** de la organización: las categorías y las ubicaciones se crean a mano desde la interfaz (RN-152), no con un seed. Los tickets de ejemplo y, para poder mostrar el trabajo por grupos, **tres grupos de ejemplo con el equipo ficticio** (RN-146) se cargan con comandos de demostración explícitos.

---

## RN-152 — Administración de catálogos de tickets

Solo el Administrador administra las categorías, las prioridades, las ubicaciones y los motivos de espera (RN-121), y cada acción se comprueba en backend. Todo cambio relevante queda en la auditoría administrativa (RN-123) con el tipo de catálogo, el nombre del registro y los valores anterior y nuevo de los campos modificados; si no hay cambios, no se registra nada. Desactivar y reactivar admiten un motivo opcional.

* **Nombre único:** dentro de cada catálogo el nombre no puede repetirse, sin distinguir mayúsculas. Evita opciones indistinguibles en los desplegables; si dos edificios tienen un "Piso 2", se nombran, por ejemplo, "Edificio A - Piso 2".
* **Desactivar, no eliminar:** los registros de catálogo no se eliminan. Un registro desactivado deja de poder elegirse en tickets nuevos, pero los tickets que ya lo usan lo conservan y no se modifican. Se puede reactivar.
* **Categorías:** el Administrador crea y edita nombre, descripción y orden. La categoría de respaldo `Sin clasificar` puede renombrarse, pero **no desactivarse**: todo ticket necesita una categoría válida (RN-16). Las categorías creadas desde la interfaz no tienen código interno.
* **Prioridades:** son exactamente cuatro (Baja, Media, Alta y Crítica). No se crean prioridades nuevas desde la interfaz, y su nivel y su color son fijos porque forman parte de la semántica visual del Design System. El Administrador puede cambiar el nombre y la descripción, y activarlas o desactivarlas. **Siempre debe quedar al menos una prioridad activa**: la comprobación bloquea las prioridades activas para que dos Administradores no dejen el sistema sin ninguna actuando a la vez. Una prioridad solo puede reactivarse si ninguna otra activa tiene su mismo nivel.
* **Ubicaciones:** el Administrador crea y edita nombre, descripción y tipo. El tipo es opcional y se elige de una lista controlada por la aplicación: Sucursal, Oficina, Edificio, Piso, Área, Instalación u Otra.
* **Motivos de espera:** el Administrador crea y edita nombre, descripción y orden, y decide si el motivo permite añadir un texto libre (la opción genérica "Otro motivo"). Como el motivo de espera es opcional (RN-49), ninguno está protegido: pueden desactivarse todos sin impedir que un ticket pase a `En espera`. Un motivo desactivado deja de poder elegirse al poner tickets en espera, pero los eventos del historial que ya lo registran lo conservan.
* **Datos iniciales:** los seeds cargan solo lo estructural (los seis estados, las cuatro prioridades, la categoría `Sin clasificar`, los motivos de cierre y los motivos de espera). Las demás categorías y las ubicaciones las define cada organización desde la interfaz.
* Los **estados** y sus transiciones no se administran con estas pantallas, sino con la suya (RN-164): sus códigos son estructurales, así que no se crean ni se eliminan, y solo se editan su nombre visible y su descripción y se habilitan o deshabilitan las transiciones opcionales.

---

## RN-153 — Creación y visibilidad de tickets

Aplica y precisa RN-09 a RN-13 y RN-16 en la implementación inicial de la creación de tickets.

**Quién puede crear.** Los cuatro roles (Solicitante, Técnico, Supervisor y Administrador), siempre que la cuenta esté activa. Se comprueba en backend.

**Datos del ticket.**

* **Título:** obligatorio, hasta 200 caracteres.
* **Descripción:** obligatoria, hasta 2000 caracteres. Los saltos de línea cuentan como un solo carácter, igual que en el contador que ve la persona.
* **Categoría:** obligatoria. Solo pueden elegirse categorías activas. Quien no sabe cuál elegir usa `Sin clasificar`, que se ofrece siempre al final de la lista y nunca viene preseleccionada.
* **Prioridad:** obligatoria. Solo pueden elegirse prioridades activas. El formulario ofrece `Media` preseleccionada, pero la prioridad debe llegar en el envío: no se asume una por omisión.
* **Ubicación:** opcional. Solo pueden elegirse ubicaciones activas.
* El ticket nace siempre en estado `Nuevo`, con un identificador público correlativo que no se reutiliza (RN-07), y se registra su creación en el historial.

**Creador y solicitantes** (RN-10, RN-12 y RN-13).

* El usuario que crea el ticket queda registrado como **creador** y ese dato no cambia nunca.
* Si crea un **Solicitante**, queda como el único solicitante del ticket. No puede registrar a otras personas: cualquier solicitante enviado en el formulario se ignora.
* Si crea un **Técnico, Supervisor o Administrador**, puede asociar ningún, uno o varios solicitantes. El creador no se convierte en solicitante por sí mismo. Un ticket sin solicitantes es válido (por ejemplo, una mantención interna).
* Solo pueden ser solicitantes los usuarios **activos con rol Solicitante**.

**Quién ve un ticket.**

* El personal (Técnico, Supervisor y Administrador) ve todos los tickets (RF-011).
* El Solicitante ve los tickets que **creó** y aquellos en los que es **solicitante vigente**. Quien fue retirado como solicitante deja de verlos, salvo que además sea el creador.
* Un usuario sin acceso a un ticket recibe la misma respuesta que si el ticket no existiera (**404, no 403**). Los identificadores son correlativos y fáciles de adivinar: un 403 permitiría descubrir cuáles existen.
* El Solicitante no ve quién creó el ticket ni los demás solicitantes; el personal sí (docs/11, UI-005).

---

## RN-154 — Listado y búsqueda de tickets

Aplica RF-088 a RF-092 en la implementación inicial del listado.

**Visibilidad.** El listado solo contiene los tickets que el usuario puede ver según RN-153. Esa restricción se aplica **en la propia consulta a la base de datos**, no después de cargar los tickets, y es siempre el mismo criterio que se usa para abrir un ticket individual. El resultado, los contadores y los enlaces de paginación nunca incluyen tickets no visibles.

**Pestañas.** *Todos*, *Abiertos* y *Cerrados*. Un ticket está **abierto** mientras su estado no sea `Cerrado`: un ticket `Resuelto` sigue abierto porque espera la validación del solicitante y puede reabrirse (docs/08). *Abiertos* es la vista por defecto. Los contadores de cada pestaña respetan la búsqueda y los filtros activos.

**Búsqueda.** Un único texto que coincide con cualquiera de estos criterios:

* el **número** exacto del ticket (con o sin `#`);
* una parte del **título** o de la **descripción**, sin distinguir mayúsculas y tratando `%` y `_` como caracteres normales;
* solo para el **personal**: el nombre, el apellido, el nombre completo o el usuario de un **solicitante vigente**. El Solicitante no puede buscar por otras personas, para no revelar quiénes más figuran en un ticket; un solicitante retirado deja de encontrarse.

El texto se limita a 100 caracteres.

**Filtros** (combinables entre sí y con la búsqueda): estado, prioridad, categoría, ubicación y rango de fechas de creación. Un valor desactivado del catálogo sigue pudiendo filtrarse, porque los tickets antiguos lo conservan. Las fechas son días de la zona horaria de la aplicación y "hasta" incluye el día completo. Los filtros por técnico, grupo y SLA se incorporan cuando existan esos datos. Un valor inválido recibido en la URL se ignora en lugar de producir un error.

**Orden.** Más recientes (por defecto), más antiguos, mayor prioridad primero (por nivel) y recién actualizados (última modificación o, si nunca se modificó, la creación). En todos los casos el desempate es la antigüedad, de modo que el orden es estable entre páginas.

**Paginación.** De 20 tickets por página, realizada en PostgreSQL. Una página inexistente devuelve una lista vacía, no un error.

---

## RN-155 — Edición de tickets

Aplica RF-022, RF-025 y RN-17 y RN-22 en la implementación inicial de la edición.

**Quién edita.** Solo el personal (Técnico, Supervisor y Administrador). El Solicitante solo lee, incluso en sus propios tickets. Se comprueba en backend: quien puede ver un ticket pero no editarlo recibe un **403**; quien no puede verlo recibe el mismo **404** que un ticket inexistente (RN-153).

**Qué se edita.**

* **Datos:** título, descripción, categoría y ubicación, con las mismas reglas y límites que al crear (RN-153). La categoría y la ubicación nuevas deben estar activas; el valor que el ticket ya tiene puede conservarse aunque se haya desactivado después, porque desactivar un valor no obliga a modificar los tickets que lo usan.
* **Prioridad:** se cambia aparte y **exige un motivo** (obligatorio, hasta 500 caracteres). La nueva prioridad debe estar activa. Establecer la misma prioridad que ya tiene el ticket no genera cambio ni registro.
* Cada cambio se aplica y se registra solo en lo que cambió; una edición sin cambios no hace nada.

**Ticket cerrado.** Un ticket `Cerrado` no se edita ni se le cambia la prioridad: primero debe reabrirse.

**Historial.** Cada cambio queda en el historial del ticket (RN-02) con quién, cuándo y los valores anterior y nuevo: `TICKET_MODIFICADO` (título, descripción y ubicación), `CATEGORIA_CAMBIADA` y `PRIORIDAD_CAMBIADA`, esta última con el motivo. El historial no repite la descripción completa: indica que fue modificada.

**Visibilidad del historial.** El personal ve qué cambió y el motivo de un cambio de prioridad. El Solicitante ve **qué cambió, quién y cuándo, pero no el motivo**: los motivos son notas internas del equipo.

**Ediciones simultáneas** (RN-114). Cada ticket tiene una versión que sube con cada cambio. Quien guarda debe hacerlo sobre la versión que abrió: si otra persona modificó el ticket mientras tanto, el guardado se rechaza con un aviso y se muestran los datos actuales, de modo que ninguna edición pisa en silencio a otra. El bloqueo temporal que avisa de quién está editando (RN-115 a RN-117) se implementa en `v0.4.0`.


---

## RN-156 — Cambios de estado operativos

Aplica y precisa RN-34 a RN-50 en la implementación de `v0.4.0` (entrega 3). Cubre las acciones **iniciar el trabajo**, **poner en espera** y **reactivar**; asignar, resolver, cerrar y reabrir se añaden con su funcionalidad.

**Qué es una transición.** Una acción es válida solo si existe como fila **activa** en `transiciones_estados` para el estado actual del ticket (docs/09, 12.2). La tabla contiene las transiciones estructuralmente válidas del flujo (docs/08, sección 34): el Administrador podrá deshabilitar alguna, nunca crear otras ni romper el ciclo de vida. La tabla no guarda permisos: quién ejecuta cada acción lo decide la autorización de la aplicación.

**Quién.** Técnico, Supervisor y Administrador, comprobado en backend. El Solicitante no cambia estados operativos. Un técnico no necesita estar asignado al ticket (RN-43).

**Acciones.**

* **Iniciar trabajo:** `Nuevo` o `Asignado` → `En progreso`. No exige técnico ni grupo: los tickets pueden existir sin ellos (docs/09, 13.2).
* **Poner en espera:** `En progreso` → `En espera`. El **motivo es opcional** (RN-49): se elige entre los motivos activos del catálogo y, si el motivo admite texto libre (la opción genérica «Otro motivo»), puede añadirse una explicación de hasta 500 caracteres. Un texto sin un motivo que lo admita se rechaza. Cualquier otra acción rechaza motivo y texto.
* **Reactivar:** `En espera` → `En progreso`.

**Un ticket cerrado no cambia de estado**: primero debe reabrirse. Una acción que no corresponde al estado actual (por ejemplo, porque otra persona ya cambió el estado) se rechaza con un aviso, también al abrir la pantalla.

**Concurrencia.** Cada cambio de estado **sube la versión** del ticket, como la edición (RN-155). La pantalla lleva la versión con la que se abrió y el servidor bloquea la fila del ticket antes de validar: si dos personas actúan a la vez, la segunda espera y ve el resultado de la primera (conflicto de versión), de modo que nunca se aplican dos transiciones sobre el mismo estado.

**Historial y visibilidad.** Cada cambio queda como `ESTADO_CAMBIADO` con el estado anterior y el nuevo, quién y cuándo. El evento es público: el Solicitante ve el cambio de estado. El **motivo de espera y su texto son solo del personal**, igual que el motivo de un cambio de prioridad (RN-155): el Solicitante ve que el ticket está en espera, no por qué.

---

## RN-157 — Asignación, grupo y escalamiento de tickets

Aplica y precisa RN-24 a RN-33 en la implementación de `v0.4.0` (entrega 5).

**Técnicos.** Un ticket tiene 0..N técnicos a la vez y un técnico 0..N tickets. Solo puede asignarse a un **Técnico activo** (el Supervisor y el Administrador asignan a otras personas pero no figuran como técnicos). La asignación es organizativa: un técnico puede actuar sobre cualquier ticket, esté o no asignado y pertenezca o no al grupo (RN-43). Quitar a un técnico cierra su asignación y la conserva; puede volver a asignarse con una asignación nueva. Un técnico desactivado conserva sus asignaciones (RN-104) y se marca «(inactivo)» para el personal, que puede redistribuirlas.

**Quién.**

* El **Técnico** se asigna a sí mismo y deja el ticket con un clic desde el detalle (**Asignarme** / **Dejar ticket**), y puede quitarse solo a sí mismo.
* El **Supervisor** y el **Administrador** asignan, quitan y reasignan a cualquier técnico, fijan el grupo y escalan, desde la pantalla de **Asignación** (`/tickets/<n>/assignment`).
* El Solicitante no asigna nada. Todo se comprueba en backend.

**Efecto sobre el estado.** Asignar al primer técnico de un ticket `Nuevo` lo pasa a `Asignado` (transición `ASIGNAR`); quitar al último técnico de un ticket `Asignado` lo devuelve a `Nuevo` (transición `DESASIGNACION`, RN-37). En cualquier otro estado asignar o quitar no cambia el estado. Si el Administrador deshabilitó esa transición, el estado no cambia. El cambio de estado queda en el historial como `ESTADO_CAMBIADO` (marcado como derivado de la asignación).

**Grupo del ticket.** Es opcional (RN-146) y lo fijan el Supervisor y el Administrador. El grupo nuevo debe estar activo; el actual puede conservarse aunque se desactive. Cambiar el grupo no cambia el estado.

**Escalamiento manual** (RF-039 y RF-040). El Supervisor o el Administrador pasan el ticket a otro grupo y/o a otro técnico. Hay que cambiar al menos una de las dos cosas y el **motivo es obligatorio** (hasta 500 caracteres). Un técnico elegido **reemplaza** a los técnicos asignados (sus asignaciones se cierran y se conservan). Es una acción manual: no cambia la prioridad ni se dispara por reglas de SLA (RN-33). Queda como **un único evento interno** `TICKET_ESCALADO`, con el grupo y los técnicos anteriores y nuevos y el motivo.

**Concurrencia.** Cada operación bloquea la fila del ticket antes de validar, así que dos autoasignaciones simultáneas del mismo técnico producen una sola asignación (el índice único parcial es el respaldo), y dos técnicos que se asignan a la vez a un ticket `Nuevo` lo pasan a `Asignado` una sola vez. **Versión:** cambiar el grupo, escalar y el cambio de estado derivado suben la versión del ticket; asignar y quitar técnicos por sí solos no (son aditivos y no pisan datos). Fijar el grupo y escalar llevan la versión con la que se abrió la pantalla y avisan si otra persona modificó el ticket.

**Ticket cerrado.** No se asigna, no se cambia su grupo ni se escala: primero debe reabrirse.

**Historial y visibilidad.**

| Evento | Visible para |
| --- | --- |
| `TECNICO_ASIGNADO` y `TECNICO_DESASIGNADO` | Todos (el Solicitante lo ve como «Atendido por») |
| `GRUPO_CAMBIADO` y `TICKET_ESCALADO` | Solo el personal |

El Solicitante ve en el resumen **«Atendido por»** con los nombres de los técnicos asignados (o «Aún sin asignar») y **nunca** el grupo, el escalamiento ni su motivo (docs/11, UI-005). El personal ve los técnicos, el grupo y el motivo del escalamiento y de quitar a un técnico.

---

## RN-158 — Solicitantes de un ticket tras crearlo

Aplica y precisa RN-10 a RN-13 y RF-014 en la implementación de `v0.4.0` (entrega 6). Al crear el ticket se asocian los solicitantes iniciales (RN-153); aquí se describe cómo cambian después.

**Quién.** El personal (Técnico, Supervisor y Administrador) agrega y retira solicitantes desde la pantalla **Solicitantes** (`/tickets/<n>/requesters`), a la que llega con el enlace «Gestionar» del resumen del ticket. Es la misma regla que elegirlos al crear (RN-10): el Solicitante no decide quiénes más figuran en un ticket, ni siquiera en el suyo. Se comprueba en backend: quien puede ver el ticket pero no gestionarlo recibe un **403**; quien no puede verlo, el mismo **404** que un ticket inexistente (RN-153).

**Quién puede ser solicitante.** Un usuario **activo con rol Solicitante** que todavía no sea solicitante vigente del ticket. Quien creó el ticket puede agregarse como cualquier otro (por ejemplo, para volver a asociar a alguien que se retiró).

**Retirar.** Es una pantalla de confirmación con un motivo opcional (hasta 500 caracteres), no un clic suelto, porque retirar a alguien le **quita el acceso** al ticket (RN-153), salvo que además lo haya creado: el creador original no cambia nunca (RN-13) y sigue viéndolo en «Mis tickets». La participación no se elimina: se cierra con la fecha y quién la retiró, y la persona puede volver a agregarse más adelante con una participación nueva. Un ticket puede quedarse sin solicitantes (RN-12).

**Quien se agrega ve el ticket completo.** Pasa a ver el ticket y todo su historial público, también lo anterior a su incorporación: la visibilidad depende de ser solicitante vigente, no de cuándo se agregó.

**Ticket cerrado.** No se agregan ni se retiran solicitantes: primero debe reabrirse.

**Concurrencia y versión.** Cada operación bloquea la fila del ticket antes de validar: dos altas simultáneas de la misma persona producen una sola participación vigente (el índice único parcial es el respaldo) y dos retiros simultáneos, uno solo. Agregar y retirar solicitantes **no sube la versión** del ticket ni cuenta como una modificación (no cambia «Actualizado»): no toca ninguno de los datos que se editan, así que quien abrió la edición antes del cambio puede guardar sin conflicto.

**Historial y visibilidad.** `SOLICITANTE_AGREGADO` y `SOLICITANTE_RETIRADO` son **eventos internos**: solo el personal los ve (con el motivo del retiro, si lo hubo). El Solicitante no ve quiénes más figuran en el ticket ni estos cambios (docs/11, UI-005). El motivo del retiro se guarda en el historial; la tabla `tickets_solicitantes` no tiene una columna para él.

---

## RN-159 — Comentarios públicos y notas internas

Aplica y precisa RN-78 a RN-80, RF-066 a RF-071 y CU-025 y CU-026 en la implementación de `v0.4.0` (entrega 7). Una única entidad (`comentarios`) representa los dos tipos.

**Quién escribe.**

* **Comentario público:** el personal (Técnico, Supervisor y Administrador) en cualquier ticket y el Solicitante en los suyos, es decir, el creador y los solicitantes vigentes (RN-153). Quien fue retirado como solicitante ya no ve el ticket y por tanto no comenta.
* **Nota interna:** solo el personal. El Solicitante nunca puede escribirla, ni siquiera en un ticket propio ni enviando el formulario a mano: se comprueba en backend y responde **403**.
* Un ticket **cerrado** no admite comentarios nuevos: primero debe reabrirse. Un ticket `Resuelto` sigue abierto y sí los admite.

**Quién ve.** El personal ve todos los comentarios. El Solicitante ve **solo los públicos**: una nota interna no llega nunca a su pantalla, ni a su historial, ni en un conteo, y sus rutas responden **404** (como si no existiera). El filtro por tipo está en la propia consulta, nunca en la plantilla ni en JavaScript (docs/10, sección 57), y un test comprueba que la política `can_view_comment` y la condición SQL coinciden para todos los roles.

**Tipo inmutable.** El tipo se fija al crear. Editar nunca lo cambia: pasar un comentario de público a interno (o al revés) alteraría retroactivamente quién lo ve.

**Editar y eliminar.**

* El **autor** edita o elimina el suyo durante `COMMENT_EDIT_WINDOW_MINUTES` desde que lo publicó (30 por defecto, variable de entorno que pasará a la configuración administrable en `v0.7.0`; debe ser mayor que cero).
* El **Supervisor** y el **Administrador** editan o eliminan cualquier comentario que puedan ver, también los de otras personas y fuera de plazo (docs/09, 17.1).
* Un Técnico no edita lo de otra persona y un Solicitante tampoco (ni siquiera el comentario del personal en su ticket). Quien ve el comentario pero no puede editarlo recibe un **403**.
* La **eliminación es lógica**: el comentario se conserva con quién y cuándo lo eliminó y deja de mostrarse a todas las personas. Hoy sigue la misma regla que editar, por decisión de esta entrega: los documentos no distinguen quién elimina.
* La edición y la eliminación se piden en pantallas separadas (editar con el texto actual; eliminar con una confirmación), como el resto de acciones.

**Límites.** El contenido es obligatorio y admite hasta 5000 caracteres (los saltos de línea cuentan una vez, como el contador). Se muestra siempre como texto: el HTML se escapa y los saltos de línea se conservan.

**Historial y visibilidad.** Cada acción registra un evento con el identificador del comentario y su tipo: `COMENTARIO_AGREGADO`, `COMENTARIO_EDITADO` (con el contenido anterior y el nuevo) y `COMENTARIO_ELIMINADO` (con el contenido y el tipo anteriores). La visibilidad del evento sigue la del comentario: los de una nota interna son internos y los de un comentario público, públicos. **El historial nunca muestra el texto**, solo indica qué ocurrió y de qué tipo; el texto anterior queda guardado para auditoría y no sale en pantalla.

**Versión y concurrencia.** Comentar, editar y eliminar **no suben la versión** del ticket ni cambian «Actualizado»: no tocan ninguno de sus datos. Aun así cada operación bloquea la fila del ticket antes de validar y rechaza un ticket cerrado; dos ediciones simultáneas del mismo comentario se aplican una tras otra (el contenido anterior del segundo evento es el nuevo del primero) y dos eliminaciones, una sola.

**Fuera de esta entrega:** las notificaciones a los técnicos cuando comenta el Solicitante (RF-068, `v0.5.0`) y los adjuntos de una nota interna, que heredan su visibilidad (RN-160).

---

## RN-160 — Archivos adjuntos

Aplica y precisa RN-81 a RN-84 y RF-072 a RF-076 en la implementación de `v0.4.0` (entrega 8).

**Quién adjunta.** Quien puede comentar públicamente en el ticket: el personal en cualquiera y el Solicitante en los suyos. Se hace desde el detalle: en la tarjeta **Archivos** (archivos del ticket) o junto a un comentario o nota interna (el formulario de comentarios admite archivos). Un ticket cerrado no admite archivos nuevos. Adjuntar durante la creación del ticket queda fuera de esta entrega.

**Quién ve y descarga.** Un archivo del ticket lo ve quien ve el ticket. Un archivo que cuelga de un comentario **hereda su visibilidad**: el Solicitante no ve ni puede descargar los de una nota interna (404, como si no existieran), y si el comentario se elimina, sus archivos dejan de verse y descargarse para todos. El filtro está en la propia consulta (`visible_attachments_condition`) y un test comprueba que coincide con la política `can_view_attachment` para todos los roles. Para un archivo solo del equipo se adjunta a una nota interna.

**Validación.** Se valida antes de guardar y un archivo rechazado no queda disponible:

* **Extensión** de una lista blanca: `png`, `jpg`, `jpeg`, `gif`, `pdf`, `txt`, `log`, `csv`, `docx`, `xlsx` y `pptx`. Todo lo demás (ejecutables, scripts, HTML, SVG, archivos comprimidos...) se rechaza.
* **Contenido** coherente con la extensión (firma de bytes; los de texto no pueden contener bytes nulos). No se confía en el nombre ni en el tipo MIME que declara el cliente: el MIME se deduce de la extensión validada.
* **Tamaño** máximo por archivo (`UPLOAD_MAX_BYTES`, 10 MB), **cantidad** máxima de archivos activos por ticket (`UPLOAD_MAX_FILES_PER_TICKET`, 20) y hasta 5 archivos por envío. Una petición mayor que el total posible responde **413**. Son variables de entorno que pasarán a la configuración administrable en `v0.7.0`.

**Almacenamiento y descarga.** Los binarios van al sistema de archivos local, **fuera de `static/`** (`instance/uploads`, o `UPLOADS_DIR`), con un nombre interno UUID impredecible y organizados por año y mes; la base de datos guarda solo los metadatos y el SHA-256 (calculado por bloques). El nombre original se depura (sin directorios ni caracteres de control) y solo se usa como nombre sugerido al descargar. La descarga es siempre autenticada, comprueba el acceso al ticket y al archivo, resuelve la ruta contra la raíz configurada (una ruta que saliera de ella responde 404) y se envía **siempre como descarga** (`Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, sin caché). Si la base de datos falla después de guardar el archivo, se borra el físico.

**Eliminar.** La eliminación es lógica: el archivo deja de mostrarse y descargarse, pero el registro y el archivo físico se conservan (docs/10, sección 69). Sigue la misma regla que editar un comentario: el Supervisor y el Administrador, cualquier archivo que puedan ver; el resto, solo los que subieron ellos dentro de `COMMENT_EDIT_WINDOW_MINUTES`.

**Historial y visibilidad.** `ARCHIVO_ADJUNTADO` y `ARCHIVO_ELIMINADO` registran el nombre y el comentario del que cuelga; la visibilidad del evento sigue a la del comentario (internos si cuelga de una nota). Subir o eliminar archivos no sube la versión del ticket ni cambia «Actualizado». Cada operación bloquea la fila del ticket antes de validar.

**Fuera de esta entrega:** vista previa de imágenes, eliminación física y retención, y configuración desde la interfaz (`v0.7.0`).

---

## RN-161 — Resolución, validación, cierre y reapertura

Aplica y precisa RN-53 a RN-73 y RF-046 a RF-060 en la implementación de `v0.4.0` (entrega 9). Todas las acciones son cambios de estado (`tickets/lifecycle.py`, función `change_state`): validan la transición contra `transiciones_estados`, bloquean la fila del ticket, comprueban la versión y suben `version`.

**Quién ejecuta cada acción.**

| Acción | Quién | Desde | Hacia |
| --- | --- | --- | --- |
| Resolver | Técnico, Supervisor y Administrador | Nuevo, Asignado, En progreso, En espera | Resuelto |
| Cierre directo | Técnico, Supervisor y Administrador | Nuevo, Asignado, En progreso, En espera | Cerrado |
| Confirmar la solución | Un solicitante vigente del ticket | Resuelto | Cerrado |
| Rechazar la solución | Un solicitante vigente del ticket | Resuelto | En progreso |
| Cierre excepcional | Supervisor y Administrador | Resuelto | Cerrado |
| Reabrir | Personal sin límite; un solicitante vigente solo un ticket **Cerrado** dentro de `REOPEN_WINDOW_DAYS` (30) desde el cierre | Resuelto o Cerrado | En progreso |

El personal nunca confirma ni rechaza por el solicitante, y el Solicitante nunca resuelve ni cierra directamente. Un solicitante retirado del ticket deja de poder responder o reabrir. Las rutas responden 404 si no se ve el ticket y 403 si se ve pero no se puede ejecutar la acción; el servicio vuelve a comprobar la política tras bloquear el ticket.

**La regla del cierre.** Un ticket en estado `Cerrado` siempre tiene fecha de cierre y motivo de cierre. La base de datos solo garantiza que van juntos (`ck_tickets_cierre_coherente`); que existan cuando el estado es `Cerrado` lo aplica el servicio, porque depende del código del estado. Todo cierre pasa por un único lugar (`_closing_changes`), que fija en la misma operación el estado, `fecha_cierre`, `motivo_cierre_id`, `cerrado_por_usuario_id` y `cerrado_automaticamente = false`. Toda salida de `Resuelto` o `Cerrado` hacia el trabajo (rechazar o reabrir) limpia en la misma operación la resolución, la fecha de resolución y los cuatro datos del cierre. Los hechos anteriores no se pierden: quedan en el historial (la explicación de la solución viaja en el evento `TICKET_RESUELTO`).

**Motivos de cierre.**

* **Confirmación:** `RESOLUCION_VALIDADA`, fijado por el flujo (solo se puede llegar a él confirmando).
* **Cierre directo:** el personal elige entre `CIERRE_DIRECTO` (por defecto) y `CANCELACION`; una cancelación no es un estado, es un cierre con ese motivo. Deben estar activos.
* **Cierre excepcional:** `CIERRE_EXCEPCIONAL`, fijado por el flujo, con un motivo escrito obligatorio.
* `DUPLICADO` lo fijará el flujo de duplicados (entrega 10) e `INACTIVIDAD` el cierre automático (`v0.5.0`): no se pueden elegir al cerrar directamente.
* Los motivos que fija el flujo son estructurales: desactivarlos en el catálogo no impide que un solicitante confirme su ticket.

**Textos.** La explicación de la solución al resolver es opcional (máx. 2000 caracteres), se guarda en `tickets.resolucion` y la ve quien ve el ticket (es lo que el solicitante revisa). Rechazar exige explicar por qué (máx. 500) y esa explicación es del propio solicitante: la ve quien ve el ticket. El texto de un cierre directo o excepcional (máx. 500) es una nota del equipo: solo la ve el personal, como el motivo de un cambio de prioridad. Confirmar admite un comentario opcional.

**Validación del solicitante.** Cada respuesta queda en `validaciones` con su **ciclo de resolución**: cada entrada a `Resuelto` abre un ciclo nuevo (se deduce de los eventos `TICKET_RESUELTO`) y un solicitante responde una vez por ciclo. La confirmación de **cualquiera** de los solicitantes vigentes cierra el ticket completo. Tras un rechazo el ticket vuelve a En progreso y puede resolverse otra vez.

**Reapertura.** Siempre vuelve a **En progreso**, conservando a los técnicos que participaron (la asignación se puede cambiar después). El comentario que explica la situación es un comentario público normal, posterior a la reapertura; reabrir no pide texto. Un ticket cerrado sigue siendo de solo lectura hasta que se reabre: la reapertura es la única acción de estado que admite.

**Ticket resuelto sin solicitante.** Nadie puede confirmar; solo el Supervisor y el Administrador pueden cerrarlo mediante el cierre excepcional. El cierre automático por inactividad (RN-58 y RN-59) lo ejecuta el planificador desde `v0.5.0` (RN-170).

**Historial.** Cada acción deja su evento propio, con el estado anterior y el nuevo: `TICKET_RESUELTO` (con `ciclo` y la explicación), `VALIDACION_ACEPTADA` y `VALIDACION_RECHAZADA` (con `validacion_id`), `TICKET_CERRADO` (con el motivo de cierre y la acción) y `TICKET_REABIERTO` (con la acción y el estado del que viene). Confirmar deja `VALIDACION_ACEPTADA` y después `TICKET_CERRADO`; rechazar, `VALIDACION_RECHAZADA` y después `TICKET_REABIERTO`. Los cinco son públicos; los textos del personal viajan en `contexto["motivo"]`, que solo ve el personal.

**Interfaz.** Cada acción tiene su pantalla de confirmación (`/tickets/<n>/status/<resolve|close|confirm|reject|close-exceptional|reopen>`), que funciona sin JavaScript. Cuando un ticket está Resuelto, el solicitante ve el aviso «¿Tu solicitud quedó resuelta?» con **Sí, está resuelto** y **No, necesito más ayuda** (UI-005A), y la explicación de la solución en su tarjeta. Un ticket cerrado muestra la fecha y el motivo del cierre en el resumen.

**Fuera de esta entrega:** notificaciones de la resolución y la reapertura (`v0.5.0`), cierre automático (`v0.5.0`), duplicados (entrega 10), y configuración de `REOPEN_WINDOW_DAYS` desde la interfaz (`v0.7.0`; hasta entonces es una variable de entorno).

---

## RN-162 — Relaciones entre tickets y duplicados

Aplica y precisa RN-74 a RN-77 y RF-062 a RF-065 en la implementación de `v0.4.0` (entrega 10). Hay dos tipos de relación (`tipos_relacion_ticket`): **`DUPLICADO`**, con dirección (del ticket duplicado al principal), y **`RELACIONADO`**, simétrica.

**Quién.** Solo el personal (Técnico, Supervisor y Administrador) ve y gestiona las relaciones. El Solicitante no las ve: ni la tarjeta del detalle, ni las pantallas (responden 403, y 404 si ni siquiera ve el ticket), ni los eventos del historial. Siempre se comprueba en el backend (`can_manage_relations`).

**Relacionar.** Desde la tarjeta **Relaciones** del detalle, en `/tickets/<n>/relations`: se escribe el número del otro ticket (`12` o `#12`), que puede estar en cualquier estado; el ticket desde el que se actúa debe estar abierto. No se puede relacionar un ticket consigo mismo ni repetir una relación vigente, tampoco al revés: el par se guarda normalizado (id menor primero) y un índice único sobre el par vigente (`least`, `greatest` y el tipo) lo respalda en la base. Un comentario opcional (máx. 500) explica por qué. Quitar una relación es una eliminación lógica: se conserva con quién y cuándo, y puede volver a establecerse con una fila nueva.

**Marcar como duplicado.** En `/tickets/<n>/duplicate`: crea la relación `DUPLICADO` y **cierra el ticket duplicado** con el motivo de cierre «Duplicado» (no existe un estado «Duplicado», RN-77), todo en la misma transacción y por el mismo camino del cierre directo (`change_state`, ver RN-161). Por eso el ticket cerrado tiene fecha, motivo y quién cerró como cualquier otro cierre, y sube su versión (la pantalla lleva la versión como la edición). **No transfiere** comentarios, archivos ni solicitantes al principal: cada ticket conserva su historial. Reglas:

* el principal debe existir y ser otro ticket, en cualquier estado (se puede marcar un duplicado de un ticket ya cerrado);
* el principal no puede ser a su vez un duplicado, y un ticket que ya es el principal de otros no puede pasar a ser duplicado: **no hay cadenas ni ciclos**. Las dos filas se bloquean en orden de id, así que dos personas que marcan duplicados opuestos a la vez no se bloquean entre sí y solo una prospera;
* el ticket debe poder cerrarse directamente (Nuevo, Asignado, En progreso o En espera): un Resuelto no se cierra de forma directa (RN-60), y uno cerrado debe reabrirse antes;
* un ticket figura como duplicado de uno solo.

**Deshacerlo.** La relación de un duplicado que sigue cerrado no se quita: es el rastro del cierre. Si el ticket se reabre, la relación se conserva hasta que alguien la quite explícitamente (y reabrir ya conserva el cierre anterior en el historial).

**Historial y visibilidad.** Los eventos `RELACION_AGREGADA` y `RELACION_ELIMINADA` son **internos** y se registran en el ticket desde el que se actúa; el otro ticket muestra la relación en su tarjeta (con quién y cuándo, que salen de la propia tabla). El cierre de un duplicado es el evento público `TICKET_CERRADO` con el motivo «Duplicado» y el ticket principal en `contexto["duplicado_de"]`: el Solicitante ve que su ticket se cerró como duplicado, pero no de cuál. Agregar o quitar una relación no sube la versión del ticket ni cambia «Actualizado»; marcar un duplicado sí, porque lo cierra.

**Fuera de esta entrega:** la advertencia de posibles duplicados al crear un ticket (RN-74 y RF-061: «podrá advertir», con búsqueda textual simple, `docs/10`, sección 92) y la pestaña **Relaciones** del diseño (hoy es una tarjeta, como las demás).

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

## RN-163 — Bloqueo temporal de edición

Aplica y precisa RN-114 a RN-117 en la implementación de `v0.4.0` (entrega 11), junto con el control de versión de RN-155 (que sigue siendo la barrera final).

**Qué se bloquea.** La edición de los datos del ticket (`/tickets/<n>/edit`) y el cambio de su prioridad (`/tickets/<n>/priority`), que comparten **un único bloqueo por ticket**: quien tiene abierta una de las dos pantallas reserva el ticket para ambas. Los demás cambios (estado, asignación, solicitantes, comentarios, archivos, relaciones) son acciones puntuales y no se bloquean: confían en la versión del ticket o son aditivos. El Solicitante no edita, así que no bloquea ni ve quién edita.

**Cómo funciona.**

* **Al abrir** la pantalla se adquiere el bloqueo (se confirma en ese momento, también con un GET). Si otra persona lo tiene vigente, se muestra una pantalla de **solo lectura**: dice quién está editando (RN-116), desde cuándo y hasta cuándo como máximo, enseña los datos actuales del ticket y ofrece «Volver a intentar». No se puede editar.
* **Mientras la pantalla está abierta**, un script la renueva cada `EDIT_LOCK_HEARTBEAT_SECONDS` (45 s) y el bloqueo dura `EDIT_LOCK_TTL_SECONDS` (120 s) sin renovarse. Si el servidor responde que otra persona lo tiene ahora, el script avisa y desactiva el botón de guardar.
* **Se libera** al guardar, al cancelar o al salir de la pantalla (RN-117). Si el navegador se cierra o la conexión cae, el bloqueo **expira solo**. Un error de validación o un conflicto de versión no lo liberan: la persona sigue editando.
* **Al guardar:** si ya no tiene el bloqueo pero nadie más lo tomó (por ejemplo, el suyo expiró), lo vuelve a adquirir y guarda; si otra persona lo tiene vigente, no se guarda nada y se le avisa («No se guardó nada: otra persona está editando este ticket»).
* **En el detalle**, el personal que podría editar ve «X está editando este ticket» mientras otra persona tenga el bloqueo (nunca quien lo tiene, ni el Solicitante).
* La misma persona con el ticket abierto en dos pestañas comparte su bloqueo.

**Reglas.**

* Un bloqueo está **vigente** cuando no se liberó y su expiración es futura. Nunca hay dos bloqueos no liberados del mismo ticket (índice único parcial en la base de datos). Como ese índice no puede depender de la hora, quien adquiere primero **libera de forma lógica el bloqueo expirado** que estorba, en la misma transacción y con la fila del ticket bloqueada (`SELECT ... FOR UPDATE`), así que dos personas que abren la pantalla a la vez no se pisan.
* Los tiempos los toma la base de datos (`clock_timestamp()`), no el reloj del servidor web.
* **No es la garantía de integridad.** Es una mejora de la experiencia: si el mecanismo fallara (una pestaña olvidada, un script bloqueado), la versión del ticket sigue impidiendo sobrescribir un cambio ajeno sin verlo (RN-155).
* Sin JavaScript todo funciona igual: no se renueva ni se libera al salir, así que el bloqueo expira solo.
* El bloqueo es un estado transitorio, no un hecho del ticket: no deja evento en el historial ni en la auditoría. Los bloqueos expirados o liberados se conservan como registro.

**Configuración.** `EDIT_LOCK_TTL_SECONDS` y `EDIT_LOCK_HEARTBEAT_SECONDS` son variables de entorno, validadas al iniciar (enteros mayores que cero y el latido menor que la duración, para que no expire entre dos renovaciones). Pasarán a la configuración administrable en `v0.7.0`.

**Fuera de esta entrega:** la liberación manual de un bloqueo por el Supervisor o el Administrador (el bloqueo expira solo, como mucho a los 120 s) y la actualización en tiempo real de quién edita (`docs/12`, sección 32).

---

## RN-164 — Administración de estados y transiciones

Aplica y precisa RN-35, RN-43 y RF-118 en la implementación de `v0.4.0` (entrega 12). Es la pantalla **Estados y transiciones** (`/admin/states`, UI-021) del área de administración: solo la usa el Administrador, la autorización se comprueba en backend como en el resto de `/admin` y cada cambio queda en la auditoría administrativa (RN-123).

**Estados.** Los seis son estructurales: no se crean, no se eliminan y su **código no cambia**, porque es el que usa el código de la aplicación. Lo que el Administrador edita de cada uno es el **nombre visible** (hasta 50 caracteres) y la **descripción** (opcional, hasta 300), que se muestra como ayuda al pasar el cursor por la etiqueta del estado. La pantalla indica además cuántos tickets hay en cada estado.

* **Nombre único** entre los seis, sin distinguir mayúsculas. Se comprueba con las seis filas bloqueadas (`SELECT ... FOR UPDATE`): dos Administradores que renombran a la vez no pueden dejar dos estados con el mismo nombre.
* **Renombrar es solo visual.** Se aplica de inmediato y a todos los tickets, y no toca el historial: cada evento conserva el nombre que el estado tenía cuando ocurrió. Los textos de las acciones (avisos y confirmaciones) no escriben a mano el nombre de ningún estado, usan el vigente, y un test lo comprueba.
* **Color y orden** (también nombrados en RF-118) quedan fuera de esta entrega. El color forma parte del Design System y se revisa junto con el pulido visual (`v0.9.0`); el orden es el del flujo.

**Transiciones.** El Administrador puede **deshabilitar y volver a habilitar** una transición ya definida; nunca crea otras (RN-35). La pantalla las agrupa por estado de origen y muestra el destino, la acción y **quién la ejecuta**. Los roles salen del propio catálogo de acciones (`tickets/state_actions.py`), no de una tabla de permisos paralela que habría que mantener sincronizada, y un test comprueba que lo que la pantalla dice coincide con lo que las políticas permiten. Deshabilitar y habilitar piden una confirmación con motivo opcional. Una transición deshabilitada deja de ofrecerse y el servidor rechaza la acción desde ese estado (RN-156); los tickets que ya están en un estado no se tocan.

Dos protecciones evitan que la configuración deje el flujo incoherente (RF-118):

1. **Transiciones esenciales.** No pueden deshabilitarse las de la asignación (`ASIGNAR` y `DESASIGNACION`, RN-37), la validación del solicitante (`CONFIRMAR` y `RECHAZAR`, RN-53 a RN-55), el cierre excepcional (RF-054), el cierre automático (`AUTO_CIERRE`, RN-58) y la reapertura (`REABRIR`, RN-66 y RN-69). Son 8 de las 20 transiciones del seed; la pantalla muestra un candado con la razón. Las otras 12 (iniciar, poner en espera, reactivar, resolver y el cierre directo) no son esenciales, aunque la segunda protección puede impedir deshabilitar alguna: por ejemplo, la única que lleva a `En espera`.
2. **Flujo completo.** Ninguna deshabilitación puede dejar un estado **inalcanzable desde `Nuevo` avanzando** por el flujo ni impedir que desde cualquier estado se **llegue a `Cerrado`**. Las acciones que devuelven un ticket atrás (rechazar, reabrir y desasignar) no cuentan para avanzar: si se deshabilitaran las dos formas de iniciar el trabajo, un ticket solo llegaría a `En progreso` resolviéndolo y reabriéndolo, y eso no es un flujo. Es una comprobación sobre el grafo de transiciones activas (`catalogs/flow.py`) que casi no conoce acciones concretas, así que sigue valiendo si se añaden estados o acciones, y solo bloquea lo que *empeora* el flujo actual. Al deshabilitar se bloquean las filas de transiciones: dos Administradores que deshabilitan a la vez dos transiciones inofensivas por separado, pero que juntas romperían el flujo, no pueden saltarse la regla (el segundo espera y ve el resultado del primero). Lo mismo ocurre si dos Administradores cambian la misma transición a la vez: el segundo ve que ya está hecha y no repite el cambio ni su registro en la auditoría.

Habilitar una transición siempre se puede.

**Auditoría.** `ESTADO_MODIFICADO` (solo los campos que cambiaron, con su valor anterior y nuevo; sin cambios no se registra nada), `TRANSICION_DESACTIVADA` y `TRANSICION_ACTIVADA` (con «Origen → Destino (Acción)» y el motivo, si se escribió).

**Datos de demostración.** `seed-demo-tickets` ejecuta las acciones de estado de verdad. Si el Administrador dejó deshabilitada una transición que la demostración necesita, el comando se detiene antes de cargar nada y dice cuál habilitar, en lugar de fallar a la mitad.

**Fuera de esta entrega:** el color y el orden de los estados, que se evalúan con el pulido visual (`v0.9.0`).

---

## RN-165 — Configuración del SLA: calendario laboral y objetivos por prioridad

Aplica y precisa RN-85 a RN-92 y RF-077 a RF-080 en la implementación de `v0.5.0` (entregas 2 y 3). Es la pantalla **SLA** (`/admin/sla`, UI-022) del área de administración: solo la usa el Administrador (RN-92), la autorización se comprueba en backend como en el resto de `/admin` y cada cambio queda en la auditoría administrativa (RN-123).

**Calendario laboral (entrega 2).** Es global y está versionado. Guardarlo **nunca modifica una versión**: crea la siguiente y deja la anterior como histórica, de modo que lo que ya se calculó con una versión no cambia retroactivamente. Mientras no se guarde ninguno, todo el sistema usa el calendario por defecto (lunes a viernes de 09:00 a 18:00, sin feriados) y la pantalla lo indica. Quien guarda indica con qué versión abrió la pantalla: si otra persona guardó mientras tanto, no se guarda nada. Guardar un contenido idéntico al vigente no crea una versión. El horario de cada día admite varias franjas (una pausa de almuerzo son dos).

**Objetivos por prioridad (entrega 3).** Cada prioridad tiene como máximo **una política** con:

* **Objetivo de resolución** (obligatorio): el tiempo máximo para resolver el ticket.
* **Objetivo de primera respuesta** (opcional): el tiempo máximo hasta el primer comentario público del personal. Asignar el ticket o cambiar su estado no cuenta (fase 5 del roadmap).
* **Umbral de aviso** (opcional, de 1 a 100 %): el porcentaje del tiempo objetivo consumido a partir del cual el ticket pasa a «próximo a vencer» (RF-081).
* **Pausa en espera** (RN-89): si el reloj se detiene mientras el ticket está en `En espera`. Es por política y vale sí por defecto.

Los tiempos son **minutos laborales**: se miden con el calendario vigente, no con el reloj de pared, y se escriben como «30 min», «4 h» o «1 h 30 min» (no hay días porque su duración depende del calendario, ni decimales). Deben ser mayores que cero y no superar 1000 horas, y **la primera respuesta no puede tardar más que la resolución**.

* **Se edita en el sitio.** Una política no se versiona: cada ticket guarda su propia copia de los objetivos en el período de SLA que abre, así que cambiar una política no altera el SLA que un ticket ya tiene en curso, solo el de los tickets que reciban esa prioridad desde ese momento (RN-88).
* **Desactivar significa que esa prioridad no tiene SLA.** La política se conserva y puede reactivarse con los mismos objetivos. No se eliminan.
* **Edición simultánea.** Si otra persona cambió, activó o desactivó la política mientras la pantalla estaba abierta, no se guarda nada y se avisa; lo escrito se pierde a propósito, porque reenviarlo pisaría un cambio que no se vio. Las operaciones sobre una misma prioridad se serializan, así que dos Administradores que la definen a la vez no la crean dos veces.
* **Los datos iniciales** (los valores de ejemplo de UI-022) los carga `seed-catalogs`, de modo que el SLA funcione desde el primer uso. El seed no pisa lo que el Administrador haya editado ni reactiva lo que haya desactivado.

**Auditoría.** `CALENDARIO_LABORAL_GUARDADO` (con solo las secciones que cambiaron) y, para las políticas, `POLITICA_SLA_CREADA`, `POLITICA_SLA_MODIFICADA` (solo los campos que cambiaron, con su valor anterior y nuevo; sin cambios no se registra nada), `POLITICA_SLA_DESACTIVADA` y `POLITICA_SLA_ACTIVADA`, con el motivo si se escribió.

**Fuera de esta entrega:** el cálculo del SLA de cada ticket, los períodos y la pausa efectiva (entrega 4, ver RN-166), las excepciones de SLA (RF-083, fuera de la fase) y el interruptor general y los avisos configurables de UI-022, que dependen de la tabla `configuracion` de `v0.7.0`.

---

## RN-166 — Períodos de SLA de un ticket

Aplica y precisa RN-85 a RN-91 en la implementación de `v0.5.0` (entrega 4). Cada ticket con SLA acumula **períodos**: tramos de su vida bajo unas mismas condiciones (la política de su prioridad, con el reloj corriendo o en pausa). Cuando esas condiciones cambian se cierra el período vigente y se abre otro; un período cerrado nunca se sobrescribe. Es un cálculo del sistema, sin intervención del usuario, y lo disparan la creación del ticket, el cambio de prioridad y el cambio de estado.

* **Tiempo laboral.** Todo se mide con el calendario laboral vigente cuando se abre el período, que el período anota (RN-90, RN-165). Las noches, los fines de semana y los feriados no cuentan.
* **El reloj corre mientras el ticket está en trabajo** (`Nuevo`, `Asignado`, `En progreso`). Se **detiene al pasar a `Resuelto`** —la espera de la validación del solicitante no cuenta contra el técnico— y al cerrarse, y **sigue donde iba si el ticket se reabre**: el consumo ya acumulado se conserva y el vencimiento nuevo es el momento de la reapertura más lo que quedaba del objetivo.
* **Pausa en espera (RN-89).** Si la política de la prioridad pausa en espera, mientras el ticket está en `En espera` hay un período **pausado**: no consume tiempo y no tiene vencimiento. Al reanudar se abre otro con lo que quedaba. Si la política no pausa, la espera no cambia nada.
* **Un cambio de prioridad no reinicia el reloj (RN-88).** El período vigente se cierra con lo que consumió y se abre otro con la política de la prioridad nueva. El vencimiento nuevo es el momento del cambio más la diferencia entre el objetivo nuevo y el consumo acumulado; si el consumo ya lo supera, el período **nace vencido**. Si el ticket estaba en una espera con pausa, el período nuevo nace pausado. El período nuevo anota quién cambió la prioridad y el motivo, que son los del evento `PRIORIDAD_CAMBIADA`.
* **Un incumplimiento no se borra.** Si algún período del ticket llegó a su vencimiento, el ticket sigue vencido aunque después baje de prioridad y el objetivo nuevo sea mayor (RN-88).
* **Las condiciones se heredan.** Mientras la prioridad no cambie, los períodos nuevos (al reanudar una pausa o reabrir) copian los objetivos del anterior, así que editar una política no altera el SLA que un ticket ya tiene en curso (`docs/09`, 20.1). Solo un cambio de prioridad toma la política vigente de la prioridad nueva.
* **Sin política activa no hay SLA.** Un ticket cuya prioridad no tiene política activa no tiene períodos. Si más tarde pasa a una prioridad con política, el SLA empieza en ese momento: lo anterior no cuenta.
* **Primera respuesta** es el primer comentario público del personal que sigue visible. Es un objetivo aparte, con su propio vencimiento, que deja de evaluarse cuando se cumple; una nota interna, un comentario del solicitante o uno eliminado no cuentan.
* **Estado del SLA.** Dentro de plazo, próximo a vencer (el consumo alcanzó el umbral de aviso de la política), vencido (el consumo alcanzó o superó el objetivo, RN-91) o pausado. Que el SLA venza no impide trabajar, resolver ni cerrar (RN-86).

**Tickets anteriores al SLA y datos de demostración.** El comando `sla-rebuild` calcula los períodos de los tickets que no tienen ninguno repasando su historial (creación, cambios de prioridad y de estado). Es una aproximación: usa la política y el calendario vigentes hoy, porque el historial no guarda cuáles eran entonces. Por eso solo toca los tickets sin períodos y `--all` (que recalcula también los reales) no se ejecuta en producción. `seed-demo-tickets` lo usa para dejar los tickets de demostración en tiempo, por vencer, vencidos y pausados según su historia.

**Fuera de esta entrega:** mostrar el estado del SLA en el listado y el detalle y la advertencia al bajar la prioridad con el SLA en riesgo (entrega 7), las notificaciones de próximo a vencer y vencido y el cierre automático (entregas 6 y 8).

---

## RN-167 — Centro de notificaciones

Aplica y precisa RN-93 en la implementación de `v0.5.0` (entrega 5): la infraestructura de las notificaciones internas y el centro donde cada persona las ve. Qué eventos las generan y a quién (RN-94 a RN-96) llega con la entrega 6.

* **Son siempre internas.** WorkDesk no envía correo ni mensajes externos: la persona las ve en el centro de notificaciones y en el contador de la barra superior (la campana).
* **Cada quien ve solo las suyas.** Todas las consultas filtran por el usuario de la sesión. Una notificación de otra persona responde 404 igual que una inexistente, también al marcarla o abrirla: con un 403 cualquiera podría averiguar cuáles existen.
* **El contenido no se reescribe.** Título, mensaje, evento, ticket, destinatario y fecha de creación no cambian nunca (la aplicación lo rechaza); solo evoluciona la lectura. Marcar como leída fija la **primera** lectura y volver a marcarla no la cambia. Leer no elimina.
* **Vocabulario controlado.** Los eventos válidos (`NotificationEvent`: creación, asignación, reasignación, cambio de estado, comentario público, nota interna, espera, resolución, validación pendiente, cierre, reapertura, SLA próximo a vencer y SLA vencido) viven en la aplicación, no en la base de datos. Un evento nuevo obliga a decidir su nombre y su icono, y un test lo exige; no necesita migración.
* **Quien genera el aviso decide a quién.** Crear una notificación no comprueba si el destinatario puede ver el ticket ni si el evento es interno: esa decisión es de quien la genera y debe seguir las mismas reglas de visibilidad del historial (un Solicitante nunca recibe un aviso de una nota interna ni del SLA). Lo único que el servicio impone es que el destinatario esté activo: a un usuario desactivado no se le crea nada. Un aviso puede no tener ticket (aviso general).
* **La campana** muestra cuántas notificaciones sin leer tiene la persona (sin número si no hay; «99+» a partir de 100) y lleva al centro. El número lo calcula el servidor en cada página y, con JavaScript, se actualiza cada 30 segundos consultando `GET /notifications/unread-count` (sin caché). Es una mejora progresiva y no hay actualización en tiempo real: queda para después del MVP. Esa consulta automática **no cuenta como actividad** de la persona y no renueva la sesión: si contara, una pestaña abandonada mantendría viva la sesión y el límite de inactividad (RNF-013) nunca se aplicaría. Con la sesión ya expirada responde `401` y la campana deja de consultar; el aviso «Tu sesión expiró» lo recibe la persona en su siguiente acción.
* **El centro** (`/notifications`, los cuatro roles) lista las notificaciones de la más reciente a la más antigua, 20 por página, con las pestañas **Todas** y **No leídas** y sus contadores. Las no leídas se distinguen por un punto y un fondo suave (también para un lector de pantalla). Se puede marcar una como leída o todas a la vez.
* **Abrir** una notificación con ticket la marca como leída y lleva al ticket. Abrirla no es un permiso: si la persona ya no puede ver el ticket, el ticket responde 404 como siempre. Una notificación sin ticket solo se marca.
* **Una acción, un POST con CSRF.** Marcar y abrir cambian algo, así que nunca son un GET; los formularios conservan el filtro y la página para volver al mismo punto del listado.

**Datos de demostración.** Mientras ningún evento del sistema genera avisos (entrega 6), `seed-demo-notifications` deja notificaciones de ejemplo escritas para cada rol, apuntando a tickets que esa persona puede ver (ver `PROJECT_CONTEXT.md`, comando `seed-demo-notifications`).

**Fuera de esta entrega:** la generación de avisos por los eventos del sistema, incluidos RF-068 (el solicitante comenta), RN-95 y RN-96 (entrega 6); los avisos de SLA (entrega 8); la configuración de eventos y destinatarios (RN-97) y las preferencias de cada persona, que dependen de la configuración administrable de `v0.7.0`; y la política de retención de las leídas.

---

## RN-168 — Avisos por los eventos de un ticket

Aplica y precisa RN-94 a RN-96 y RF-068 en la implementación de `v0.5.0` (entrega 6): qué eventos de un ticket generan una notificación interna y a quién. Los avisos nacen dentro de la operación que los provoca y se confirman o se revierten con ella. Los de SLA (próximo a vencer y vencido) los genera el planificador (entrega 8).

* **Nunca se avisa a quien hizo el cambio.** Ya lo sabe.
* **Se avisa a las personas vigentes:** los solicitantes que no fueron retirados y los técnicos que siguen asignados. Un usuario inactivo no recibe nada (RN-167).
* **Un Solicitante solo recibe avisos de lo que también ve en el historial.** Una nota interna, un escalamiento, el grupo, el motivo de una espera o de un cierre, el texto de un comentario o de la solución y el ticket principal de un duplicado no llegan nunca a un Solicitante, ni en el título ni en el mensaje. Los avisos no copian el texto de los comentarios: dicen quién escribió y en qué ticket.

| Evento | Quién recibe el aviso |
| --- | --- |
| Crear un ticket | Nadie. Quien lo crea ya lo ve y el reparto del trabajo es de la asignación. |
| Asignar un técnico | El técnico asignado y los solicitantes (que saben quién los atiende). |
| Quitar a un técnico | El técnico que sale, si no se quitó él mismo. |
| Escalar (técnico nuevo) | El técnico nuevo y los que dejan el ticket. Los solicitantes no: es un evento interno. Escalar solo de grupo no avisa a nadie. |
| Iniciar, esperar, reactivar y cerrar (directo, confirmado o excepcional) | Los solicitantes y los técnicos asignados. |
| Resolver | Los solicitantes reciben una petición de revisar la solución (RN-95); los técnicos, el aviso de que se resolvió. |
| Rechazar la solución | Los técnicos, para retomar el trabajo; los demás solicitantes saben que sigue en progreso. |
| Reabrir | Los técnicos (RN-96) y los demás solicitantes. |
| Comentario público del personal | Los solicitantes. |
| Comentario público de un solicitante (RF-068) | Los técnicos asignados. |
| Nota interna | Los demás técnicos asignados. |

Asignar o desasignar pueden cambiar el estado entre `Nuevo` y `Asignado`: esos cambios derivados no se avisan aparte (los cubre el aviso de asignación). Editar el ticket, cambiar su prioridad o el grupo, las relaciones, los adjuntos y los cambios de solicitantes no generan avisos en esta entrega.

**Datos de demostración.** `seed-demo-tickets` ejecuta las operaciones reales, así que sus servicios también crean avisos; el comando los elimina al terminar, solo los de los tickets que creó, para que la historia de la demostración (que es del pasado) no llene a nadie de avisos nuevos. Los avisos de ejemplo se cargan con `seed-demo-notifications`.

---

## RN-169 — Indicadores de SLA

Aplica RN-91 y precisa RN-88 en la implementación de `v0.5.0` (entrega 7): cómo se muestra el estado del SLA y cómo se advierte al bajar la prioridad. El SLA es informativo y no bloquea ninguna operación (RN-86).

* **Solo lo ve el personal.** El Solicitante no ve el SLA en ningún sitio: ni la insignia, ni la tarjeta, ni el filtro y el orden del listado. Esos parámetros no existen para él: si los escribe en la dirección se ignoran, de modo que no puede deducir el SLA de un ticket probando filtros.
* **Estados** (docs/11, sección 29): *dentro de plazo*, *próximo a vencer* (el consumo alcanzó el umbral de aviso de la política), *vencido* (alcanzó o superó el objetivo, o venció alguna vez: un incumplimiento no se borra, RN-88), *pausado* (el reloj no corre por `En espera`) y *sin SLA* (nunca tuvo períodos o su prioridad no tiene una política activa). Un ticket resuelto o cerrado tiene el reloj detenido: queda *dentro de plazo* o *vencido* según cumplió, y nunca *próximo a vencer*.
* **El umbral de aviso se copia al período y se guarda cuándo se alcanza**, igual que el vencimiento, en tiempo laboral. Editar después el umbral de la política no altera el SLA que un ticket ya tiene en curso (RN-166).
* **Listado.** El personal ve una columna «SLA» con la insignia y el tiempo laboral que queda o que se pasó; en móvil, la insignia en la tarjeta. Puede **filtrar** por estado (dentro de plazo, próximo a vencer, vencido, pausado o sin SLA) y **ordenar por «SLA más urgente»**: primero el que vence antes (los ya vencidos, con su vencimiento en el pasado, van delante) y al final los que no tienen un reloj en marcha. El filtro y los contadores de las pestañas usan el mismo instante que las insignias.
* **Detalle.** El personal ve la tarjeta «SLA»: la insignia, el consumo («5 h 30 min de 6 h (91 %)») con su barra, cuándo vence (o que está detenido o en pausa), el estado de la primera respuesta y la lista de períodos con el motivo de cada cambio de prioridad.
* **Bajar la prioridad con el SLA en riesgo (RN-88).** Si el SLA está *próximo a vencer* o *vencido*, la pantalla de cambio de prioridad advierte antes de confirmar que el tiempo consumido se conserva y que el incumplimiento no se borra. Si de verdad se baja la prioridad (la nueva tiene un nivel menor), se avisa a los **Supervisores responsables del grupo del ticket**; si el ticket no tiene grupo, o ninguno de sus responsables está activo, a **todos los Supervisores activos**. No se avisa a quien hizo el cambio, ni cuando la prioridad sube, ni cuando el SLA está dentro de plazo, pausado o no existe. El aviso dice quién la bajó, de qué prioridad a cuál y en qué estado estaba el SLA, sin copiar el motivo (se lee en el historial). Evento: `SLA_PRIORIDAD_BAJADA`.

**Fuera de esta entrega:** los avisos de «próximo a vencer» y «vencido» que genera el planificador y el cierre automático (entrega 8, RN-170) y el dashboard de «fuera de SLA» (`v0.6.0`).

---

## RN-170 — Planificador: avisos de SLA y cierre automático

Aplica RN-58, RN-59 y RN-91 en la implementación de `v0.5.0` (entrega 8). Lo ejecuta el comando `run-scheduler` (docs/10, secciones 84 a 87); sus tareas se pueden repetir sin riesgo.

* **Avisos de SLA (RN-91).** Cuando el consumo de un período de SLA en marcha alcanza su umbral de aviso, se avisa **una sola vez** de que el ticket está *próximo a vencer*; cuando vence, una sola vez de que está *vencido*. Un ticket en pausa, resuelto o cerrado no avisa (no tiene reloj en marcha). Eventos: `SLA_PROXIMO_A_VENCER` y `SLA_VENCIDO`.
* **A quién se avisa.** *Próximo a vencer*: a los técnicos asignados y, si el ticket no tiene ninguno, a los Supervisores responsables del grupo del ticket (o a todos los Supervisores activos si no tiene grupo o ninguno está activo). *Vencido*: a los técnicos asignados **y** a esos Supervisores. **Nunca a los solicitantes:** el SLA es solo del personal (RN-169). El aviso nombra el ticket y no copia ningún texto.
* **Si se encuentra tarde.** Si cuando el planificador revisa el ticket ya venció (estuvo detenido o se creó vencido), solo se envía el aviso de *vencido*: el de *próximo a vencer* ya no tiene sentido.
* **Registro del incumplimiento (RN-91).** Al avisar de un vencimiento, el planificador registra en el historial del ticket el evento interno `SLA_VENCIDO` (actor Sistema; en el contexto, el período, el objetivo en minutos y el instante en que venció), en la misma transacción que el aviso, así que se registra una sola vez. Es interno: el Solicitante no lo ve, como no ve nada del SLA (RN-169).
* **Un aviso, una vez.** Cada período anota cuándo se enviaron los dos avisos. Un período nuevo de la misma prioridad (al reanudar tras una espera o reabrir) hereda esas marcas, porque el consumo nunca baja y no se repite lo ya avisado; un cambio de prioridad abre un SLA distinto (RN-88) y sus avisos empiezan de nuevo. Los períodos que ya habían alcanzado su umbral o vencido al instalar esta versión se dan por avisados: la primera ejecución no inunda a nadie. Los períodos que se crean después con `sla-rebuild` o con el seed de demostración empiezan sin marcas: el planificador avisa una vez de lo que ya esté vencido.
* **Cierre automático (RN-58 y RN-59).** Un ticket `Resuelto` que nadie valida en `AUTO_CLOSE_HOURS` horas (24 por defecto, horas corridas desde la resolución) se cierra solo, **tenga o no solicitantes**. Es la transición `AUTO_CIERRE`, con el motivo de cierre `INACTIVIDAD`, `cerrado_automaticamente` verdadero y sin usuario que cierra; en el historial el actor es el **Sistema** (el evento es público, como cualquier cierre). Pasa por el mismo camino de cierre que las personas, así que el ticket queda con fecha y motivo de cierre como siempre, sube su versión, detiene el SLA y se puede reabrir (el personal siempre; el solicitante dentro del plazo de reapertura, contado desde ese cierre).
* **El plazo se vuelve a comprobar al cerrar.** Entre que el planificador encuentra el ticket y lo cierra, el solicitante puede haberlo validado o rechazado, o el ticket haber sido reabierto y resuelto otra vez (la resolución nueva reinicia la espera): en la transacción del cierre se bloquea el ticket y se comprueban de nuevo el estado, el plazo y que la transición siga activa.
* **A quién se avisa del cierre.** A los solicitantes vigentes y a los técnicos asignados («Ticket cerrado automáticamente»), sin nombrar a nadie ni el motivo interno.
* **Configuración.** `AUTO_CLOSE_HOURS` y `SCHEDULER_INTERVAL_SECONDS` son variables de entorno (enteros mayores que cero; la aplicación no arranca con otro valor) hasta que la configuración administrable de `v0.7.0` (RN-58) las reemplace.

**Fuera de esta entrega:** las excepciones de SLA (RF-083) y los avisos de la *primera respuesta* vencida.

---

## RN-171 — Configuración administrable e interruptores

Aplica RF-053, RF-113, RF-119, RF-120 y RF-122 (`v0.7.0`). Solo el Administrador cambia la configuración, desde Administración.

* **Valor vigente.** El que el Administrador guardó; si no guardó ninguno, el inicial (variable de entorno o valor por defecto). Restablecer borra el valor propio.
* **Validación.** Cada parámetro tiene un rango; los que se relacionan (la renovación del bloqueo de edición debe ser menor que su duración) se validan juntos, con los valores vigentes. Un cambio inválido no guarda nada.
* **Auditoría y conflictos.** Cada valor que cambia deja un registro con el anterior, el nuevo y el motivo opcional. Si otra persona cambió algún valor de la pantalla mientras estaba abierta, no se guarda nada.
* **Aplicar SLA a los tickets.** Apagado, WorkDesk no muestra ni avisa nada del SLA a nadie (indicadores, filtros, orden, advertencias, dashboards, carga de trabajo y avisos del planificador), pero sigue calculando los períodos de cada ticket. Al encenderlo se muestran de nuevo, y los avisos pendientes (también de lo vencido mientras estaba apagado) se envían en la siguiente revisión.
* **Cierre automático.** Apagado, un ticket resuelto espera a que se confirme, se rechace o se cierre a mano.
* **Plazos que ya corren.** Un cambio de plazo rige para lo que se evalúe después: no reescribe lo ya ocurrido.

---

## RN-172 — Configuración de notificaciones

Aplica RN-97, RF-087 y RF-121 (`v0.7.0`). Solo el Administrador elige qué avisos internos se envían, desde Administración.

* **Catálogo cerrado.** Los avisos posibles son los de RN-168 y RN-170, cada uno para sus destinatarios (solicitantes, técnicos asignados o supervisores). Se pueden apagar y volver a encender, pero no crear: un Solicitante nunca recibe algo interno.
* **Obligatorios.** Siempre se envían la revisión de una solución resuelta a los solicitantes (RN-95) y la reapertura a los técnicos (RN-96).
* **Efecto.** Un aviso apagado deja de crearse desde ese momento; los ya enviados no se borran y los que se omitieron no se reenvían al volver a encenderlo. Lo que se registra en el historial (incluido un incumplimiento de SLA) no cambia.
* **Auditoría y conflictos.** Como el resto de la configuración (RN-171).

---

## RN-173 — Artículos de la base de conocimiento

Aplica RF-102 y RF-103 (`v0.7.0`).

* **Estados.** Un artículo es borrador o publicado y, aparte, público o privado. *Público* no significa abierto a Internet: lo lee cualquier persona con sesión; *privado*, solo el personal. Desactivar no borra.
* **Lectura.** El Solicitante lee los publicados y públicos. El Técnico lee los publicados y sus propios borradores. El Supervisor lee todos los activos; el Administrador, todos.
* **Escritura.** El personal crea borradores. El Técnico edita sus borradores; el Supervisor y el Administrador editan cualquiera y son quienes publican, retiran de publicación y destacan. Solo el Administrador desactiva y reactiva.
* **Categoría.** Se usa el catálogo de categorías de los tickets. Una categoría desactivada puede conservarse, pero no elegirse.
* **Destacados.** Solo puede destacarse un artículo publicado y activo; al retirarlo de publicación o desactivarlo deja de estarlo.
* **Concurrencia y trazabilidad.** Si otra persona cambió el artículo, no se guarda nada. Cada operación se audita; el texto del artículo no se copia.

---

## RN-174 — Artículos vinculados a un ticket

Aplica RF-104 y RF-105 (`v0.7.0`).

* El personal vincula artículos activos que puede leer y los desvincula; un mismo artículo, una sola vez por ticket. Se permite también en un ticket cerrado porque no lo modifica.
* El vínculo y su retirada quedan en el historial como eventos internos.
* Cada persona ve en el ticket solo los artículos que puede leer.
* Un artículo creado desde la resolución nace como borrador, con el título, la categoría y la resolución propuestos (nunca la descripción), y queda vinculado como origen en la misma operación.

---

## RN-175 — Posibles tickets duplicados

Aplica RF-061 (`v0.7.0`).

* Antes de crear un ticket se muestran los abiertos y recientes, de la misma categoría o sin clasificar, cuyo título comparte las palabras suficientes. La búsqueda entiende el español y no distingue tildes.
* La advertencia no impide crear: la persona puede crear el ticket de todos modos. Si cambia el título o la categoría, se comprueba otra vez.
* Nunca se muestra un ticket que la persona no pueda ver.
* El Administrador ajusta los días que se revisan (0 desactiva la advertencia) y las palabras que deben coincidir.

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
| Prioridad               | Manual; Técnico, Supervisor y Administrador pueden modificarla con motivo |
| SLA y prioridad         | Cambio de prioridad no reinicia el consumo       |
| Grupos                  | Opcionales; el Supervisor gestiona los suyos     |
| Contraseñas             | Temporal con cambio obligatorio al primer login  |
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
| SLA                     | Solo Supervisor/Admin gestionan excepciones      |
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
