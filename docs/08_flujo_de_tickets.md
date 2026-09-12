# 08 — Flujo de Tickets

## WorkDesk

---

## 1. Información del documento

| Campo          | Valor                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------ |
| Proyecto       | WorkDesk                                                                                                           |
| Documento      | Flujo de Tickets                                                                                                   |
| Archivo        | `08_flujo_de_tickets.md`                                                                                           |
| Versión        | 1.2                                                                                                                |
| Estado         | Definitivo                                                                                                         |
| Alcance        | MVP                                                                                                                |
| Dependencias   | `04_requisitos_funcionales.md`, `05_requisitos_no_funcionales.md`, `06_reglas_de_negocio.md`, `07_casos_de_uso.md` |
| Idioma inicial | Español latinoamericano, con localización orientada a Chile                                                        |

---

# 2. Propósito

El presente documento define el flujo operacional de los tickets dentro de WorkDesk.

Su objetivo es establecer de manera clara y ordenada:

* Cómo nace un ticket.
* Cómo ingresa al ciclo operativo.
* Cómo se clasifica.
* Cómo se asigna.
* Cómo comienza el trabajo.
* Cómo se gestiona una espera.
* Cómo se resuelve.
* Cómo se cierra.
* Cómo puede reabrirse.
* Cómo se gestionan situaciones como duplicidad, escalamiento, reasignación y excepciones.
* Qué ocurre con el SLA durante las distintas etapas.
* Qué información debe quedar registrada en el historial.
* Qué actores pueden intervenir en cada etapa.

Este documento no define la implementación técnica interna de los flujos.

La implementación deberá respetar los requisitos funcionales, requisitos no funcionales y reglas de negocio previamente establecidos.

---

# 3. Relación con la documentación anterior

El flujo de tickets se construye sobre la siguiente relación:

```text
01_vision_del_proyecto.md
        │
        ▼
02_objetivos.md
        │
        ▼
03_roles_y_permisos.md
        │
        ▼
04_requisitos_funcionales.md
        │
        ├──────────────► 05_requisitos_no_funcionales.md
        │
        ▼
06_reglas_de_negocio.md
        │
        ▼
07_casos_de_uso.md
        │
        ▼
08_flujo_de_tickets.md
        │
        ├──────────────► 09_modelo_de_datos.md
        ├──────────────► 10_arquitectura.md
        ├──────────────► 11_diseno_de_pantallas.md
        └──────────────► 12_roadmap.md
```

La función de este documento es traducir las decisiones previas a una secuencia operacional coherente.

No deberá utilizarse para introducir nuevas reglas que contradigan los documentos anteriores.

---

# 4. Actores que participan en el flujo

Los principales actores operativos son:

| Actor         | Participación principal                                                                         |
| ------------- | ----------------------------------------------------------------------------------------------- |
| Solicitante   | Crea tickets, consulta, aporta información, valida soluciones y puede reabrir                   |
| Técnico       | Analiza, trabaja, espera, resuelve, comenta y participa en la gestión                           |
| Supervisor    | Supervisa, asigna, reasigna, escala, modifica estados e interviene en excepciones               |
| Administrador | Administra configuración y posee las capacidades operativas y administrativas más amplias       |
| Sistema       | Ejecuta acciones automáticas definidas, como cálculo de SLA, notificaciones y cierre automático |

Un usuario puede desempeñar distintas funciones según su rol y permisos.

---

# 5. Estados base del ticket

El MVP utilizará seis estados estructurales:

1. **Nuevo**
2. **Asignado**
3. **En progreso**
4. **En espera**
5. **Resuelto**
6. **Cerrado**

Estos estados forman la estructura fundamental del ciclo de vida.

No se utilizará un estado estructural denominado `Reabierto`.

La reapertura representa una **acción o transición** que devuelve el ticket a un estado operativo.

Tampoco se utilizarán como estados base:

* `Cancelado`
* `Duplicado`

Cuando corresponda, dichas situaciones se representarán mediante acciones, motivos o relaciones, manteniendo la integridad del flujo.

---

# 6. Significado de cada estado

## 6.1 Nuevo

Representa un ticket recientemente creado que todavía no ha comenzado su gestión operativa.

Puede existir durante este estado aunque todavía no se haya completado toda su configuración operativa.

Durante esta etapa pueden realizarse acciones como:

* Clasificación.
* Corrección de información.
* Definición de prioridad.
* Asociación de grupo.
* Asignación de técnicos.

Un ticket no deberá considerarse formalmente en ejecución mientras no posea la información operativa necesaria para comenzar el trabajo.

---

## 6.2 Asignado

Representa un ticket que ya posee uno o más técnicos asociados para su gestión.

El ticket puede permanecer en este estado mientras se prepara el inicio efectivo del trabajo.

Puede existir más de un técnico asociado al mismo ticket.

La asignación no queda limitada por la carga actual del técnico.

---

## 6.3 En progreso

Representa que el trabajo operativo sobre el ticket ha comenzado.

Antes de entrar formalmente en este estado deben encontrarse definidos los elementos operativos necesarios:

* Categoría.
* Prioridad.
* Grupo responsable.
* Técnico o técnicos responsables.

El estado `En progreso` representa el trabajo activo sobre la solicitud.

---

## 6.4 En espera

Representa una interrupción temporal del trabajo debido a una dependencia real que impide continuar.

Debe utilizarse únicamente cuando exista una causa concreta de espera.

El ticket puede registrar opcionalmente el motivo correspondiente. La ausencia de motivo no impide por sí sola utilizar este estado.

Ejemplos:

* Información pendiente.
* Espera de tercero.
* Aprobación.
* Recurso pendiente.
* Otro motivo definido por la organización.

El comportamiento del SLA durante este estado dependerá de la configuración vigente.

---

## 6.5 Resuelto

Representa que la solución ha sido aplicada y que el ticket puede quedar pendiente de validación.

Este estado activa el mecanismo de validación correspondiente cuando el ticket utiliza el flujo normal de resolución.

El solicitante podrá:

* Confirmar la solución.
* Reabrir el ticket si el problema persiste.

Un ticket en `Resuelto` puede cerrarse automáticamente después del período configurado de inactividad.

---

## 6.6 Cerrado

Representa el término operativo del ciclo de vida.

El ticket cerrado conserva su historial.

Dependiendo de las políticas configuradas, un ticket cerrado puede ser reabierto durante el período permitido.

---

# 7. Flujo general del ticket

El flujo normal del MVP es:

```text
                         ┌───────────────┐
                         │     NUEVO     │
                         └───────┬───────┘
                                 │
                         Asignación / gestión
                                 │
                                 ▼
                         ┌───────────────┐
                         │   ASIGNADO    │
                         └───────┬───────┘
                                 │
                            Inicio trabajo
                                 │
                                 ▼
                         ┌───────────────┐
                         │  EN PROGRESO  │
                         └───┬───────┬───┘
                             │       │
                      Espera │       │ Resolver
                             │       │
                             ▼       ▼
                      ┌───────────┐  ┌───────────────┐
                      │EN ESPERA  │  │    RESUELTO   │
                      └─────┬─────┘  └───────┬───────┘
                            │                │
                    Reactivación             │
                            │          ┌─────┴─────────┐
                            │          │               │
                            ▼       Validación    Auto-cierre
                      EN PROGRESO        │               │
                                         ▼               ▼
                                  ┌────────────────────────┐
                                  │        CERRADO          │
                                  └───────────┬─────────────┘
                                              │
                                         Reapertura
                                              │
                                              ▼
                                         EN PROGRESO
```

Este flujo representa el comportamiento estándar.

Las transiciones excepcionales y administrativas se describen posteriormente.

---

# 8. Flujo de creación

## 8.1 Inicio

El flujo comienza cuando un usuario autorizado crea un ticket.

Todos los roles habilitados pueden generar tickets.

Un usuario autorizado también puede crear un ticket en representación de otro usuario.

El creador y el solicitante son conceptos independientes.

---

## 8.2 Solicitantes

Un ticket puede:

* Tener un solicitante.
* Tener múltiples solicitantes.
* No tener solicitantes.

Cuando existen múltiples solicitantes, cualquiera de los solicitantes autorizados puede validar positivamente la solución para permitir el cierre.

La ausencia de solicitante no impide la gestión del ticket.

---

## 8.3 Información inicial

El ticket deberá registrar como mínimo:

* Título.
* Descripción.
* Categoría.
* Prioridad.

`Impacto` y `Urgencia` serán opcionales en el MVP y podrán completarse cuando resulten útiles para clasificación, análisis o métricas.

La ubicación física podrá ser obligatoria u opcional según la configuración administrativa.

La categoría no deberá quedar vacía.

Cuando el usuario no conozca la clasificación adecuada podrá utilizar la categoría válida configurada para estos casos, por ejemplo:

```text
Sin clasificar
```

La clasificación podrá corregirse posteriormente por usuarios autorizados.

---

## 8.4 Registro de creación

La creación deberá registrar, cuando corresponda:

* Usuario creador.
* Fecha y hora.
* Solicitantes asociados.
* Información inicial.
* Clasificación.
* Prioridad.
* Grupo.
* Otros datos relevantes definidos por el sistema.

La acción deberá quedar incorporada al historial.

---

# 9. Flujo de clasificación y preparación operativa

Después de la creación, el ticket podrá requerir preparación antes del inicio efectivo del trabajo.

Esta preparación puede incluir:

```text
Ticket creado
      │
      ▼
Revisión de información
      │
      ├──► Corrección de categoría
      │
      ├──► Definición de prioridad
      │
      ├──► Asociación a grupo
      │
      └──► Asignación de técnico(s)
                    │
                    ▼
                Listo para trabajar
```

La configuración puede realizarse progresivamente.

Sin embargo, el ticket no debe considerarse formalmente `En progreso` mientras falten los elementos operativos necesarios.

---

# 10. Flujo de asignación

## 10.1 Asignación manual

En el MVP la asignación será principalmente manual.

La asignación puede realizarse a:

* Un técnico.
* Varios técnicos.

El sistema no deberá impedir una asignación únicamente por la carga de trabajo actual del técnico.

---

## 10.2 Cambio de asignación

Un usuario autorizado puede:

* Agregar técnicos.
* Retirar técnicos.
* Reasignar técnicos.
* Cambiar el grupo asociado.

Los cambios deben conservar historial.

---

## 10.3 Reasignación masiva

Supervisor y Administrador podrán realizar reasignaciones masivas autorizadas.

El uso esperado incluye situaciones como:

* Vacaciones.
* Licencias.
* Renuncia.
* Desvinculación.
* Cambio de funciones.
* Redistribución operativa.

Una reasignación masiva no debe eliminar la evidencia de las asignaciones anteriores.

Debe quedar registrado:

* Quién realizó la reasignación.
* Cuándo.
* Qué tickets fueron afectados.
* Asignación anterior.
* Nueva asignación.

---

# 11. Flujo de inicio del trabajo

Un ticket en `Nuevo` o `Asignado` puede pasar a `En progreso` cuando un usuario autorizado inicia formalmente el trabajo.

La transición requiere disponer de la información operativa necesaria.

El flujo general es:

```text
Nuevo
  │
  │ preparación / asignación
  ▼
Asignado
  │
  │ inicio del trabajo
  ▼
En progreso
```

Una vez iniciado el trabajo:

* Se registra la transición.
* Se conserva la fecha y hora.
* Se registra el usuario responsable.
* Se mantienen las métricas y trazabilidad correspondientes.
* Se aplican las reglas de SLA vigentes.

---

# 12. Flujo de trabajo en progreso

Mientras el ticket está `En progreso`, los técnicos autorizados pueden realizar las actividades relacionadas con su gestión.

Estas actividades pueden incluir:

* Comentarios públicos.
* Notas internas.
* Adjuntar archivos.
* Modificar clasificación cuando corresponda.
* Modificar información operativa permitida.
* Agregar o modificar participantes.
* Cambiar estado según permisos.

Las modificaciones relevantes deben quedar registradas.

---

# 13. Flujo de espera

Cuando el trabajo no pueda continuar temporalmente por una dependencia real, el ticket puede pasar a `En espera`.

El flujo es:

```text
En progreso
     │
     │ dependencia temporal
     ▼
En espera
```

Al entrar en `En espera`:

1. El usuario puede registrar opcionalmente un motivo desde el catálogo disponible.
2. Debe registrarse la transición.
3. El sistema debe aplicar la política de SLA correspondiente.
4. Deben generarse las notificaciones internas configuradas.

La ausencia de motivo no invalida la transición.

---

# 14. Reactivación desde espera

Cuando desaparece la causa que generó la espera, el ticket puede volver a un estado operativo.

El flujo principal es:

```text
En espera
    │
    │ dependencia resuelta
    ▼
En progreso
```

La reactivación deberá:

* Registrar el evento.
* Registrar fecha y hora.
* Registrar usuario responsable.
* Conservar el motivo de espera cuando haya sido registrado.
* Aplicar el comportamiento de SLA correspondiente.
* Notificar a los participantes relevantes cuando corresponda.

---

# 15. Flujo de resolución

Cuando el trabajo haya terminado, el técnico o usuario autorizado puede marcar el ticket como `Resuelto`.

Flujo:

```text
En progreso
     │
     │ solución aplicada
     ▼
Resuelto
```

Como comportamiento predeterminado del MVP, la resolución podrá producirse desde `Nuevo`, `Asignado`, `En progreso` o `En espera`, siempre que las reglas de negocio y permisos lo permitan. En particular, `En espera → Resuelto` está permitida sin exigir una reactivación previa a `En progreso`.

Marcar un ticket como `Resuelto` activa el mecanismo de validación correspondiente.

La inclusión de una explicación textual de resolución no es obligatoria.

No obstante, el sistema deberá permitir incorporar información de resolución cuando resulte útil.

---

# 16. Validación de la solución

Cuando un ticket está `Resuelto`, el solicitante autorizado puede interactuar con la solución.

El flujo normal es:

```text
                  ┌──────────────────┐
                  │     RESUELTO     │
                  └────────┬─────────┘
                           │
                  ┌────────┴─────────┐
                  │                  │
             Confirmar           Rechazar
                  │                  │
                  ▼                  ▼
              CERRADO          REAPERTURA
                                     │
                                     ▼
                                EN PROGRESO
```

---

## 16.1 Confirmación positiva

Cuando el solicitante confirma que la solución es correcta:

```text
Resuelto → Cerrado
```

La confirmación debe quedar registrada.

Cuando existen múltiples solicitantes, una validación positiva de cualquiera de los solicitantes autorizados es suficiente para permitir el cierre.

---

## 16.2 Rechazo de la solución

Cuando la solución no sea satisfactoria, el solicitante puede iniciar la reapertura.

Debe poder incorporar información pública adicional que explique la situación.

El flujo es:

```text
Resuelto
   │
   │ solución rechazada
   ▼
En progreso
```

La reapertura debe registrar la transición y notificar a los participantes relevantes.

---

# 17. Cierre automático

Un ticket en `Resuelto` puede cerrarse automáticamente después de permanecer sin interacción durante el período configurado.

Flujo:

```text
Resuelto
   │
   │ período de inactividad cumplido
   ▼
Cerrado
```

El cierre automático:

* Solo se ejecuta cuando la política correspondiente está habilitada.
* Respeta el período configurado.
* Debe quedar identificado como acción realizada por el sistema.
* Debe conservar trazabilidad.
* Debe generar las notificaciones configuradas.

La ausencia de interacción no debe interpretarse como cierre inmediato.

---

# 18. Tickets sin solicitante

Un ticket puede existir sin solicitante asociado.

Esto permite representar:

* Mantenciones.
* Revisiones preventivas.
* Tareas periódicas.
* Solicitudes internas.
* Otros escenarios operativos.

Estos tickets pueden ser:

* Gestionados.
* Asignados.
* Puestos en espera.
* Resueltos.
* Cerrados.

Cuando no existen solicitantes, no se requerirá validación de usuario para finalizar el ticket.

Sin embargo, si el ticket utiliza el flujo `Resuelto`, deberá respetarse igualmente el período de espera configurado para el cierre automático.

La ausencia de solicitantes no debe provocar el cierre automático inmediato.

Cuando corresponda, puede utilizarse el mecanismo de cierre directo.

---

# 19. Cierre directo

El cierre directo constituye un mecanismo distinto de la resolución pendiente de validación.

Permite finalizar un ticket directamente desde una situación operativa autorizada.

Ejemplos de utilización:

* Mantenciones.
* Tickets internos.
* Tickets sin solicitante.
* Casos validados previamente por otro medio.
* Tareas rutinarias.
* Casos donde no corresponda esperar confirmación.

Flujo:

```text
Nuevo / Asignado / En progreso / En espera
                    │
                    │ cierre directo autorizado
                    ▼
                  Cerrado
```

El cierre directo:

* No pasa por `Resuelto`.
* No activa el mecanismo de validación del solicitante.
* Debe quedar registrado de manera diferenciada.
* Debe mantener la trazabilidad correspondiente.

---

# 20. Cierre excepcional

Supervisor y Administrador pueden realizar cierres excepcionales cuando las reglas operativas lo autoricen.

El flujo puede producirse desde un estado anterior a `Cerrado` cuando corresponda.

La acción debe registrar:

* Usuario responsable.
* Fecha y hora.
* Estado anterior.
* Estado nuevo.
* Motivo o información contextual disponible.
* Identificación de que se trata de una operación excepcional.

---

# 21. Reapertura

La reapertura es una acción, no un estado.

Puede aplicarse a tickets:

* `Resuelto`.
* `Cerrado`.

Su destino predeterminado es:

```text
En progreso
```

La configuración podrá permitir alternativas siempre que estas pertenezcan al conjunto de transiciones estructuralmente válidas.

---

# 22. Flujo de reapertura

```text
             ┌─────────────┐
             │   RESUELTO  │
             └──────┬──────┘
                    │
                    │ reapertura
                    ▼
             ┌─────────────┐
             │ EN PROGRESO │
             └─────────────┘


             ┌─────────────┐
             │   CERRADO   │
             └──────┬──────┘
                    │
                    │ reapertura
                    ▼
             ┌─────────────┐
             │ EN PROGRESO │
             └─────────────┘
```

Cuando un ticket es reabierto:

1. Se registra la reapertura.
2. Se conserva el historial anterior.
3. Se registra el estado anterior.
4. Se registra el nuevo estado.
5. Se conserva inicialmente la participación de los técnicos anteriores.
6. Se notifican los participantes relevantes.
7. Los usuarios autorizados pueden modificar posteriormente la asignación.

---

# 23. Reapertura por solicitante

El solicitante autorizado dispone de una acción explícita de:

```text
Reabrir ticket
```

La secuencia principal es:

```text
Ticket Resuelto/Cerrado
          │
          │ Reabrir ticket
          ▼
     En progreso
          │
          │ comentario público
          ▼
    Información adicional
```

El comentario posterior a la reapertura no constituye por sí mismo una nueva reapertura.

---

# 24. Reapertura y técnicos participantes

Al reabrirse un ticket, los técnicos que participaron anteriormente deben conservarse inicialmente como participantes.

Esto permite mantener el contexto del trabajo.

Posteriormente, un usuario autorizado puede:

* Mantener la misma asignación.
* Agregar técnicos.
* Retirar técnicos.
* Reasignar el ticket.

Los cambios deben quedar registrados.

---

# 25. Duplicados

WorkDesk debe permitir identificar posibles tickets duplicados.

La detección puede producir una advertencia antes o durante la creación.

La advertencia no obliga necesariamente a cancelar la creación.

Cuando dos tickets representan la misma situación, pueden vincularse.

El flujo recomendado es:

```text
Posible duplicado
       │
       ▼
Revisión
       │
 ┌─────┴──────┐
 │            │
No duplicado  Duplicado
 │            │
 ▼            ▼
Continuar    Vincular
             │
             ▼
       Cerrar con motivo
         "Duplicado"
```

`Duplicado` no constituye un estado.

La relación con el ticket principal debe mantenerse para conservar la trazabilidad.

---

# 26. Escalamiento manual

Supervisor y Administrador pueden escalar manualmente un ticket cuando la situación lo requiera.

El escalamiento puede implicar:

* Cambio de grupo.
* Incorporación de nuevos técnicos.
* Reasignación.
* Intervención de otro nivel de soporte.

En el MVP no se requiere escalamiento automático avanzado.

Flujo general:

```text
Ticket en gestión
      │
      │ necesidad de escalamiento
      ▼
Intervención Supervisor/Admin
      │
      ├──► Cambio de grupo
      ├──► Cambio de técnicos
      ├──► Agregar técnicos
      └──► Cambio de nivel operativo
              │
              ▼
       Continuación del flujo
```

Toda intervención debe conservar trazabilidad.

---

# 27. Reasignación y continuidad

Una reasignación no reinicia el ciclo de vida del ticket.

El estado del ticket se conserva salvo que la operación realizada implique explícitamente una transición válida.

Por ejemplo:

```text
En progreso
     │
     │ reasignación
     ▼
En progreso
```

La reasignación modifica quién trabaja el ticket, pero no implica por sí misma que el trabajo haya comenzado nuevamente.

---

# 28. Prioridad dentro del flujo

La prioridad orienta la gestión, pero no constituye una restricción automática del flujo.

Los niveles iniciales son:

* Crítica.
* Alta.
* Media.
* Baja.

La prioridad puede modificarse durante el ciclo de vida por usuarios autorizados.

Una prioridad inferior no impide:

* Iniciar el trabajo.
* Resolver.
* Cerrar.

No existe una regla que obligue al sistema a atender automáticamente los tickets en estricto orden de prioridad.

---

# 29. SLA dentro del flujo

El SLA pertenece al ticket y acompaña su ciclo de vida.

El comportamiento específico dependerá de la configuración.

De manera general:

```text
Creación
   │
   ▼
Inicio SLA
   │
   ├──► En progreso ───────► SLA activo
   │
   ├──► En espera ─────────► Pausa o continuidad
   │                          según configuración
   │
   ├──► Resuelto ──────────► cierre/validación
   │
   └──► Cerrado ───────────► finalización
```

Cuando el ticket se encuentre en `En espera`, el SLA podrá:

* Pausarse.
* Mantenerse activo.

La política aplicable debe ser coherente con la configuración administrativa.

El cambio de estado no debe eliminar la trazabilidad del tiempo acumulado.

---

# 30. Notificaciones del flujo

Las notificaciones internas se generarán de acuerdo con los eventos configurados.

Entre los eventos relevantes se encuentran:

* Creación.
* Asignación.
* Reasignación.
* Cambio de estado.
* Entrada en espera.
* Reactivación.
* Comentarios.
* Notas internas cuando corresponda.
* Resolución.
* Cierre.
* Cierre automático.
* Reapertura.
* Eventos relevantes de SLA.

Las notificaciones no modifican por sí mismas el estado del ticket salvo cuando una regla explícita de automatización básica lo determine.

El MVP no requiere integración obligatoria con:

* Correo externo.
* SMS.
* WhatsApp.
* Otros canales externos.

---

# 31. Historial del flujo

Toda transición o acción relevante debe generar información histórica.

Como mínimo, cuando corresponda, el historial deberá permitir comprender:

* Qué ocurrió.
* Quién realizó la acción.
* Cuándo ocurrió.
* Estado anterior.
* Estado nuevo.
* Información adicional relevante.

Ejemplos de eventos:

```text
Ticket creado
Asignado a Técnico A
Asignado a Técnico B
Prioridad modificada
Estado cambiado: Nuevo → Asignado
Estado cambiado: Asignado → En progreso
Estado cambiado: En progreso → En espera
Motivo de espera registrado
Estado cambiado: En espera → En progreso
Estado cambiado: En progreso → Resuelto
Solicitante confirmó solución
Estado cambiado: Resuelto → Cerrado
Ticket reabierto
Estado cambiado: Cerrado → En progreso
```

La información histórica no debe ser reemplazada por modificaciones posteriores.

---

# 32. Trazabilidad de acciones

El principio fundamental del flujo es:

> Toda acción relevante debe poder comprenderse y reconstruirse posteriormente.

Por lo tanto, el flujo debe conservar evidencia suficiente para conocer la evolución del ticket.

La flexibilidad operativa no debe comprometer la trazabilidad.

---

# 33. Control de permisos durante las transiciones

Las transiciones no están disponibles para todos los usuarios.

## Solicitante

Puede principalmente:

* Confirmar una solución.
* Reabrir un ticket según las políticas.
* Agregar información pública relacionada con su solicitud.

No debe poder modificar arbitrariamente los estados operativos.

---

## Técnico

Como comportamiento predeterminado del MVP, puede intervenir operativamente en tickets de cualquier grupo aunque no pertenezca a él y aunque no esté formalmente asignado al ticket. La asignación se utiliza para organización, seguimiento y carga de trabajo, no como requisito previo para actuar.

Puede participar en:

* Asignación y autoasignación.
* Inicio del trabajo.
* Espera.
* Reactivación.
* Resolución.
* Cierre directo desde estados autorizados.
* Reapertura cuando corresponda.
* Comentarios, notas internas y archivos.

El Administrador podrá configurar restricciones adicionales cuando el contexto organizacional lo requiera.

---

## Supervisor

Posee una capacidad de intervención operativa más amplia.

Puede:

* Modificar estados cuando corresponda.
* Reasignar.
* Escalar.
* Intervenir en situaciones excepcionales.
* Modificar prioridades.
* Redistribuir trabajo.

---

## Administrador

Posee las capacidades administrativas y operativas más amplias.

Puede:

* Intervenir en estados.
* Realizar cierres excepcionales.
* Configurar políticas del flujo.
* Configurar SLA.
* Configurar cierre automático.
* Configurar políticas de reapertura.
* Gestionar grupos.
* Gestionar usuarios.
* Administrar parámetros del sistema.

---

# 34. Matriz principal de transiciones

La siguiente matriz representa las transiciones estructuralmente válidas del flujo base.

| Estado origen | Acción / condición           | Destino     | Participantes principales                                 |
| ------------- | ---------------------------- | ----------- | --------------------------------------------------------- |
| Nuevo         | Asignación                   | Asignado    | Técnico / Supervisor / Admin                              |
| Nuevo         | Inicio de trabajo autorizado | En progreso | Técnico / Supervisor / Admin                              |
| Nuevo         | Resolver                     | Resuelto    | Técnico / Supervisor / Admin                              |
| Nuevo         | Cierre directo autorizado    | Cerrado     | Técnico / Supervisor / Admin                              |
| Asignado      | Inicio del trabajo           | En progreso | Técnico / Supervisor / Admin                              |
| Asignado      | Resolver                     | Resuelto    | Técnico / Supervisor / Admin                              |
| Asignado      | Cierre directo autorizado    | Cerrado     | Técnico / Supervisor / Admin                              |
| En progreso   | Poner en espera              | En espera   | Técnico / Supervisor / Admin                              |
| En progreso   | Resolver                     | Resuelto    | Técnico / Supervisor / Admin                              |
| En progreso   | Cierre directo autorizado    | Cerrado     | Técnico / Supervisor / Admin                              |
| En espera     | Reactivar                    | En progreso | Técnico / Supervisor / Admin                              |
| En espera     | Resolver cuando corresponda  | Resuelto    | Técnico / Supervisor / Admin                              |
| En espera     | Cierre directo autorizado    | Cerrado     | Técnico / Supervisor / Admin                              |
| Resuelto      | Confirmación positiva        | Cerrado     | Solicitante                                               |
| Resuelto      | Rechazo / reapertura         | En progreso | Solicitante / usuarios autorizados                        |
| Resuelto      | Cierre automático            | Cerrado     | Sistema                                                   |
| Resuelto      | Cierre excepcional           | Cerrado     | Supervisor / Admin                                        |
| Cerrado       | Reapertura                   | En progreso | Solicitante / Técnico / Supervisor / Admin según permisos |

La configuración administrativa puede adaptar las transiciones dentro del conjunto estructuralmente válido.

No puede utilizarse para romper la estructura fundamental del flujo.

---

# 35. Reglas de transición configurables

El Administrador puede configurar determinados atributos de los estados base:

* Nombre visible.
* Color.
* Orden visual.
* Descripción.
* Ayuda contextual.
* Transiciones permitidas dentro del conjunto válido.

La configuración no podrá:

* Crear nuevos estados estructurales.
* Eliminar estados estructurales.
* Convertir `Reabierto` en un estado.
* Eliminar etapas fundamentales.
* Crear combinaciones incoherentes.
* Romper el ciclo de vida definido por WorkDesk.

Los seis estados base deben permanecer.

---

# 36. Flujo resumido de extremo a extremo

El recorrido estándar puede representarse así:

```text
┌────────────────────┐
│ CREACIÓN DEL TICKET│
└─────────┬──────────┘
          │
          ▼
┌──────────────────────┐
│        NUEVO         │
│ Clasificación        │
│ Prioridad            │
│ Grupo                │
│ Participantes        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      ASIGNADO        │
│ Uno o más técnicos   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    EN PROGRESO       │
│ Trabajo activo       │
└───────┬───────┬──────┘
        │       │
        │       │ Solución aplicada
        │       ▼
        │   ┌──────────────┐
        │   │   RESUELTO   │
        │   └──────┬───────┘
        │          │
        │    ┌─────┴─────┐
        │    │           │
        │ Confirmación   │ Inactividad
        │    │           │
        │    ▼           ▼
        │ CERRADO ← CERRADO
        │
        │ Dependencia
        ▼
┌──────────────────────┐
│      EN ESPERA       │
└──────────┬───────────┘
           │
           │ Reactivación
           ▼
      EN PROGRESO


       CERRADO
          │
          │ Reapertura
          ▼
     EN PROGRESO
```

---

# 37. Flujo alternativo de cierre directo

```text
Nuevo
  │
  ├───────────────┐
  │               │
  ▼               │
Asignado           │
  │               │
  ▼               │
En progreso        │
  │               │
  └───────┬───────┘
          │
          │ cierre directo autorizado
          ▼
       Cerrado
```

También puede originarse desde `En espera` cuando la situación operacional lo permita.

El cierre directo no pasa por `Resuelto`.

---

# 38. Flujo alternativo de reapertura

```text
Resuelto
   │
   │ rechazo
   ▼
En progreso


Cerrado
   │
   │ reapertura
   ▼
En progreso
   │
   ▼
Continuación del trabajo
```

La reapertura conserva:

* Historial.
* Técnicos participantes.
* Contexto del ticket.
* Información previamente registrada.

---

# 39. Flujo de ticket duplicado

```text
Nuevo ticket
     │
     ▼
Detección de coincidencia
     │
     ▼
Advertencia de posible duplicado
     │
 ┌───┴────────┐
 │            │
No            Sí
 │            │
 ▼            ▼
Continuar   Vincular
             │
             ▼
        Cerrar duplicado
```

El ticket duplicado conserva su relación con el ticket principal.

---

# 40. Flujo de escalamiento y reasignación

```text
Ticket en gestión
       │
       ▼
Necesidad de intervención
       │
       ▼
Supervisor / Administrador
       │
       ├──────────────┐
       │              │
       ▼              ▼
Reasignación       Escalamiento
       │              │
       └──────┬───────┘
              ▼
       Continuación
        del flujo
```

La intervención no altera automáticamente el estado del ticket.

---

# 41. Concurrencia durante la gestión

Mientras un usuario esté modificando un ticket:

* Otros usuarios pueden consultar la información.
* Otros usuarios no podrán modificar simultáneamente el mismo recurso.
* El sistema debe mostrar que existe un bloqueo de edición.
* Cuando corresponda, debe indicar quién está realizando la edición.
* Al liberarse el recurso, otro usuario podrá editarlo.

El bloqueo visual de edición no reemplaza los mecanismos de integridad y concurrencia del backend.

---

# 42. Manejo de errores durante el flujo

Las operaciones del flujo deben ejecutarse de manera controlada.

Ante errores:

* No deben generarse estados inválidos.
* No deben perderse los cambios confirmados.
* No debe corromperse el historial.
* El usuario debe recibir mensajes comprensibles.
* La información técnica sensible no debe exponerse.
* Las excepciones relevantes deben quedar registradas en los logs correspondientes.

Ante una operación fallida, el sistema debe conservar el último estado consistente conocido.

---

# 43. Integridad del flujo

WorkDesk debe impedir transiciones que produzcan situaciones inconsistentes.

No deben permitirse, por ejemplo:

* Estados inexistentes.
* Transiciones no autorizadas.
* Estados sin correspondencia estructural.
* Pérdida de historial.
* Reapertura convertida en un estado permanente.
* Eliminación de etapas fundamentales del ciclo de vida mediante configuración.
* Modificaciones que destruyan referencias históricas.

La flexibilidad de operación no debe comprometer la integridad del dominio.

---

# 44. Reglas sobre estados terminales

`Cerrado` representa el término operativo del ciclo de vida.

Sin embargo, un ticket cerrado no significa que la información desaparezca.

El ticket conserva:

* Historial.
* Comentarios.
* Archivos según políticas.
* Información de resolución.
* Participantes históricos.
* Eventos de reapertura.
* Trazabilidad administrativa y operativa.

Las políticas de retención determinan posteriormente qué ocurre con la información conservada.

---

# 45. Relación entre el flujo y el SLA

El cambio de estado no elimina los tiempos previamente registrados.

El sistema debe poder reconstruir cómo transcurrió el tiempo del ticket.

La medición podrá considerar:

* Inicio de atención.
* Tiempo en progreso.
* Tiempo en espera.
* Tiempo acumulado.
* Cumplimiento o incumplimiento.
* Pausas según política.
* Eventos relevantes.

La implementación técnica del cálculo se definirá posteriormente.

---

# 46. Relación entre el flujo y las notificaciones

Las notificaciones acompañan el flujo, pero no reemplazan el historial.

Cuando corresponda a la configuración:

```text
Evento de flujo
      │
      ├──► Registro histórico
      │
      ├──► Actualización del estado
      │
      ├──► Actualización SLA
      │
      └──► Notificación interna
```

La información histórica debe existir aunque una notificación no pueda entregarse.

---

# 47. Relación entre el flujo y la auditoría

Las operaciones administrativas relevantes pueden registrarse adicionalmente en la auditoría administrativa.

Esto aplica especialmente a:

* Cambios de configuración.
* Cambios de políticas.
* Reasignaciones administrativas.
* Cambios de retención.
* Modificaciones de comportamiento del sistema.
* Otras acciones administrativas relevantes.

El historial operativo del ticket y la auditoría administrativa cumplen funciones complementarias.

---

# 48. Criterios para una transición válida

Una transición solo debe ejecutarse cuando:

1. El estado origen sea válido.
2. El estado destino sea estructuralmente válido.
3. El actor tenga permisos.
4. Se cumplan las condiciones de negocio.
5. Se respeten las condiciones de configuración aplicables.
6. No exista una incompatibilidad con el estado actual.
7. La operación pueda registrarse correctamente.
8. La integridad del ticket pueda mantenerse.

Cuando alguna condición no se cumpla, la transición debe rechazarse de forma controlada.

---

# 49. Eventos fundamentales del flujo

Los siguientes eventos deben considerarse fundamentales para seguimiento y trazabilidad:

```text
CREACIÓN
ASIGNACIÓN
REASIGNACIÓN
CAMBIO DE PRIORIDAD
CAMBIO DE CATEGORÍA
INICIO DE TRABAJO
ENTRADA EN ESPERA
REACTIVACIÓN
RESOLUCIÓN
CONFIRMACIÓN
RECHAZO
CIERRE
CIERRE DIRECTO
CIERRE EXCEPCIONAL
CIERRE AUTOMÁTICO
REAPERTURA
ESCALAMIENTO
VINCULACIÓN DE DUPLICADO
```

Los eventos relevantes deben quedar registrados según las reglas de historial y auditoría.

---

# 50. Matriz de escenarios principales

| Escenario              | Flujo                                                                         |
| ---------------------- | ----------------------------------------------------------------------------- |
| Ticket estándar        | Nuevo → Asignado → En progreso → Resuelto → Cerrado                           |
| Ticket con espera      | Nuevo → Asignado → En progreso → En espera → En progreso → Resuelto → Cerrado |
| Ticket sin solicitante | Nuevo → Asignado → En progreso → Resuelto → Cerrado / Cierre directo          |
| Mantención             | Nuevo → Asignado → En progreso → Cierre directo                               |
| Cierre automático      | En progreso → Resuelto → espera configurada → Cerrado                         |
| Rechazo de solución    | Resuelto → En progreso                                                        |
| Reapertura de cerrado  | Cerrado → En progreso                                                         |
| Duplicado              | Nuevo → vinculación → Cerrado con motivo de duplicidad                        |
| Escalamiento           | Estado actual → intervención → continuidad del mismo flujo                    |
| Reasignación           | Estado actual → cambio de asignación → continuidad del mismo flujo            |
| Cierre excepcional     | Estado operativo → Cerrado                                                    |
| Espera prolongada      | En progreso → En espera → reactivación según causa                            |

---

# 51. Trazabilidad con requisitos funcionales

El flujo de tickets utiliza principalmente los siguientes requisitos:

| Área                        | Requisitos      |
| --------------------------- | --------------- |
| Creación                    | RF-012 a RF-016 |
| Información y clasificación | RF-017 a RF-022 |
| Prioridad                   | RF-023 a RF-027 |
| Asignación                  | RF-028 a RF-035 |
| Carga de trabajo            | RF-036 a RF-038 |
| Escalamiento                | RF-039 a RF-040 |
| Estados                     | RF-041 a RF-045 |
| Resolución y cierre         | RF-046 a RF-054 |
| Reapertura                  | RF-055 a RF-060 |
| Duplicados                  | RF-061 a RF-065 |
| Comentarios y notas         | RF-066 a RF-071 |
| Archivos                    | RF-072 a RF-076 |
| SLA                         | RF-077 a RF-083 |
| Notificaciones              | RF-084 a RF-087 |
| Historial y auditoría       | RF-106 a RF-109 |
| Configuración               | RF-113 a RF-123 |

---

# 52. Trazabilidad con reglas de negocio

El flujo se apoya especialmente en:

| Área                                      | Reglas          |
| ----------------------------------------- | --------------- |
| Principios generales y trazabilidad       | RN-01 a RN-06   |
| Identificación y creación                 | RN-07 a RN-13   |
| Información y clasificación               | RN-14 a RN-18   |
| Prioridad                                 | RN-19 a RN-23   |
| Carga de trabajo                          | RN-24 a RN-30   |
| Escalamiento                              | RN-31 a RN-33   |
| Estados                                   | RN-34 a RN-42   |
| Transiciones                              | RN-43 a RN-47   |
| Estado En espera                          | RN-48 a RN-51   |
| Resolución                                | RN-52 a RN-56   |
| Cierre                                    | RN-57 a RN-65   |
| Reapertura                                | RN-66 a RN-73   |
| Duplicados y relaciones                   | RN-74 a RN-77   |
| Comentarios y notas                       | RN-78 a RN-80   |
| Archivos                                  | RN-81 a RN-84   |
| SLA                                       | RN-85 a RN-92   |
| Notificaciones                            | RN-93 a RN-97   |
| Visibilidad y colaboración                | RN-98 a RN-101  |
| Usuarios desactivados                     | RN-102 a RN-104 |
| Retención de información                  | RN-105 a RN-110 |
| Seguridad e integridad operativa          | RN-111 a RN-113 |
| Concurrencia y edición                    | RN-114 a RN-117 |
| Auditoría administrativa                  | RN-118 a RN-119 |
| Configuración administrativa              | RN-120 a RN-123 |
| Configuración inicial                     | RN-124 a RN-126 |
| Respaldos y recuperación                  | RN-127 a RN-129 |
| Automatización                            | RN-130 a RN-132 |
| Experiencia y comunicación                | RN-133 a RN-136 |
| Situaciones operativas reales             | RN-137 a RN-139 |
| Principios fundamentales del MVP          | RN-140 a RN-145 |

---

# 53. Relación con requisitos no funcionales

El flujo deberá respetar especialmente los siguientes atributos:

* Integridad de información.
* Trazabilidad.
* Control de concurrencia.
* Manejo controlado de errores.
* Logging.
* Respaldo y recuperación.
* Control de acceso.
* Retención.
* Usabilidad.
* Mantenibilidad.
* Parametrización.
* Evolución futura.

Las decisiones técnicas que materialicen estas condiciones serán desarrolladas posteriormente en `10_arquitectura.md` y `09_modelo_de_datos.md`.

---

# 54. Criterios de aceptación del flujo

El flujo de tickets podrá considerarse correctamente implementado cuando:

* Existan los seis estados estructurales definidos.
* Las transiciones respeten permisos y reglas.
* Un ticket pueda atravesar el flujo estándar completo.
* Se pueda utilizar `En espera` con o sin motivo registrado.
* El SLA se comporte según configuración.
* Un ticket pueda pasar a `Resuelto`.
* Un solicitante pueda confirmar o rechazar la solución.
* El cierre automático respete el período configurado.
* Los tickets sin solicitante no se cierren automáticamente por su sola ausencia.
* El cierre directo funcione como mecanismo independiente.
* La reapertura no sea un estado.
* La reapertura devuelva normalmente a `En progreso`.
* Los técnicos anteriores se conserven inicialmente al reabrir.
* Los duplicados puedan vincularse y cerrarse por motivo.
* Las reasignaciones y escalaciones preserven el historial.
* Las acciones relevantes generen trazabilidad.
* La concurrencia impida modificaciones simultáneas sobre el mismo recurso.
* No puedan configurarse transiciones estructuralmente inválidas.

---

# 55. Principio fundamental del flujo

El flujo de WorkDesk debe equilibrar dos objetivos:

```text
             FLEXIBILIDAD OPERATIVA
                      +
               CONTROL DEL SISTEMA
                      │
                      ▼
             FLUJO COHERENTE Y
                TRAZABLE
```

El sistema debe permitir que los equipos adapten su forma de trabajar a situaciones reales, pero sin perder la coherencia del ciclo de vida ni la capacidad de reconstruir posteriormente lo ocurrido.

El flujo puede ser flexible.

Los estados fundamentales permanecen controlados.

Las acciones pueden variar según el contexto.

La trazabilidad no debe desaparecer.

---

# 56. Alcance del documento

Este documento define el flujo funcional y operacional del ciclo de vida de los tickets del MVP.

No define todavía:

* Tablas de base de datos.
* Relaciones físicas.
* API.
* Estructura de código.
* Controladores.
* Servicios.
* Componentes frontend.
* Diseño visual final.
* Infraestructura de despliegue.

Estos aspectos serán definidos en documentos posteriores.

---

# 57. Próximos documentos relacionados

La definición de este flujo servirá como entrada para:

```text
08_flujo_de_tickets.md
        │
        ├──► 09_modelo_de_datos.md
        │
        ├──► 10_arquitectura.md
        │
        ├──► 11_diseno_de_pantallas.md
        │
        └──► 12_roadmap.md
```

Particularmente:

### `09_modelo_de_datos.md`

Deberá representar:

* Tickets.
* Estados.
* Transiciones.
* Usuarios.
* Solicitantes.
* Técnicos.
* Grupos.
* Historial.
* Comentarios.
* Notas.
* Archivos.
* SLA.
* Notificaciones.
* Relaciones entre tickets.

### `10_arquitectura.md`

Deberá definir cómo implementar:

* Reglas de negocio.
* Control de permisos.
* Flujo de estados.
* Concurrencia.
* SLA.
* Notificaciones.
* Auditoría.
* Persistencia.

### `11_diseno_de_pantallas.md`

Deberá representar visualmente:

* Creación.
* Bandejas.
* Detalle.
* Historial.
* Asignación.
* Estados.
* Resolución.
* Cierre.
* Reapertura.
* SLA.
* Dashboard.

---

# 58. Estado del documento

**Estado:** Definitivo para el MVP.

Este documento deberá considerarse una referencia funcional para las siguientes etapas del diseño y desarrollo.

Cualquier modificación posterior que altere:

* Estados.
* Transiciones.
* Reapertura.
* Cierre.
* SLA.
* Permisos.
* Comportamiento del flujo.

deberá reflejarse también en los documentos relacionados para preservar la consistencia documental de WorkDesk.

---

## Fin del documento
