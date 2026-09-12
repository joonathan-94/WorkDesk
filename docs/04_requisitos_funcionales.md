# 04. Requisitos Funcionales

## 1. Propósito del documento

El presente documento define los requisitos funcionales de **WorkDesk**, estableciendo las capacidades que el sistema debe proporcionar para cumplir con los objetivos definidos para el proyecto.

Los requisitos aquí descritos representan el comportamiento funcional esperado del sistema y constituyen la base para las etapas posteriores de análisis, diseño, desarrollo, pruebas y validación.

Este documento complementa los documentos de:

* `01_vision_del_proyecto.md`
* `02_objetivos.md`
* `03_roles_y_permisos.md`
* `05_requisitos_no_funcionales.md`
* `06_reglas_de_negocio.md`

El documento define **qué debe hacer WorkDesk**. Las reglas que condicionan dichas funcionalidades se encuentran formalizadas principalmente en `06_reglas_de_negocio.md`, mientras que las decisiones relativas a calidad, seguridad, rendimiento, mantenibilidad y restricciones técnicas se encuentran en `05_requisitos_no_funcionales.md`.

---

# 2. Alcance

Los requisitos funcionales definidos corresponden principalmente al **MVP de WorkDesk**, cuyo núcleo es la gestión integral de tickets de soporte TI.

El alcance funcional contempla:

* Autenticación y gestión de sesiones.
* Gestión de usuarios.
* Gestión de roles y permisos.
* Gestión de grupos o colas.
* Gestión de tickets.
* Gestión de múltiples solicitantes.
* Gestión de múltiples técnicos por ticket.
* Clasificación de tickets.
* Gestión de prioridades.
* Gestión de estados y transiciones.
* Gestión de asignaciones y reasignaciones.
* Gestión de carga de trabajo.
* Reasignación masiva de tickets.
* Escalamiento manual.
* Comentarios públicos.
* Notas internas.
* Archivos adjuntos.
* SLA.
* Notificaciones internas.
* Búsqueda y filtros.
* Dashboards.
* Reportes y exportaciones.
* Base de conocimientos.
* Historial y auditoría.
* Configuración administrativa.
* Retención y administración de información histórica.
* Mecanismos de respaldo y mantenimiento, cuando corresponda al alcance funcional administrativo.

El documento distingue entre capacidades del **MVP**, capacidades posteriores y capacidades correspondientes a la evolución futura del producto.

---

# 3. Convenciones y nomenclatura

Los requisitos funcionales se identifican mediante el formato:

`RF-XXX`

Donde:

* `RF` corresponde a Requisito Funcional.
* `XXX` corresponde al número correlativo.

Cada requisito podrá indicar:

* Identificador.
* Nombre.
* Actor.
* Descripción.
* Alcance.

La numeración deberá mantenerse estable para facilitar la trazabilidad entre requisitos, casos de uso, diseño, implementación y pruebas.

---

# 4. Flujo funcional general

WorkDesk se estructura alrededor del ticket como unidad principal de trabajo.

El flujo general contempla:

```text
Usuario
   │
   ├── Autenticación
   │
   └── Crear / consultar ticket
               │
               ▼
        Clasificación
               │
               ▼
         Grupo / Cola
               │
               ▼
      Asignación manual
               │
               ▼
        Técnico(s)
               │
               ▼
       Gestión del ticket
       ├── Comentarios
       ├── Notas internas
       ├── Archivos
       ├── Prioridad
       ├── Estados
       ├── SLA
       └── Colaboración
               │
               ▼
            Resuelto
               │
        ┌──────┴────────┐
        ▼               ▼
 Validación        Rechazo / Reapertura
 solicitante            │
        │               ▼
        ▼          En Progreso
     Cerrado
        │
        ▼
   Reapertura posterior
```

El comportamiento concreto de cada transición se encuentra condicionado por los roles, permisos y reglas de negocio correspondientes.

---

# 5. Autenticación y acceso

## RF-001 — Inicio de sesión

**Actor:** Todos los usuarios.

El sistema debe permitir que los usuarios registrados inicien sesión utilizando sus credenciales.

La autenticación debe validar la identidad antes de permitir acceso a funcionalidades protegidas.

**Alcance:** MVP.

---

## RF-002 — Cierre de sesión

**Actor:** Todos los usuarios autenticados.

El sistema debe permitir cerrar la sesión de manera explícita.

**Alcance:** MVP.

---

## RF-003 — Gestión de sesiones

**Actor:** Sistema.

El sistema debe gestionar las sesiones de usuarios autenticados, aplicando las políticas de expiración, invalidación y seguridad definidas para el sistema.

**Alcance:** MVP.

---

## RF-004 — Control de acceso según rol

**Actor:** Sistema.

El sistema debe determinar las funcionalidades y recursos disponibles según el rol del usuario.

Los roles principales son:

* Solicitante.
* Técnico.
* Supervisor.
* Administrador.

**Alcance:** MVP.

---

# 6. Gestión de usuarios

## RF-005 — Gestión de usuarios

**Actor:** Administrador.

El sistema debe permitir:

* Crear usuarios.
* Consultar usuarios.
* Modificar información.
* Activar usuarios.
* Desactivar usuarios.
* Gestionar roles.

**Alcance:** MVP.

---

## RF-006 — Modificación de roles

**Actor:** Administrador.

El sistema debe permitir modificar el rol de un usuario.

El cambio deberá aplicarse al siguiente acceso u operación correspondiente de acuerdo con las reglas del sistema.

**Alcance:** MVP.

---

## RF-007 — Gestión del estado de usuario

**Actor:** Administrador.

El sistema debe permitir activar o desactivar usuarios.

Un usuario desactivado no podrá autenticarse normalmente.

Su información histórica deberá permanecer disponible cuando sea necesaria para conservar la trazabilidad.

**Alcance:** MVP.

---

# 7. Gestión de grupos y colas

## RF-008 — Gestión de grupos

**Actor:** Administrador.

El sistema debe permitir:

* Crear grupos.
* Modificar grupos.
* Activar grupos.
* Desactivar grupos.
* Consultar grupos.

Los grupos representan unidades organizativas de atención.

**Alcance:** MVP.

---

## RF-009 — Asociación de técnicos a grupos

**Actor:** Administrador.

El sistema debe permitir asociar un técnico a uno o más grupos.

**Alcance:** MVP.

---

## RF-010 — Asociación de tickets a grupos

**Actor:** Usuarios autorizados.

El sistema debe permitir asociar un ticket a un grupo de atención.

El solicitante no deberá depender de conocer la estructura interna de grupos para registrar una solicitud.

**Alcance:** MVP.

---

## RF-011 — Consulta y acceso operativo a tickets

**Actor:** Técnico, Supervisor, Administrador.

El sistema debe permitir consultar tickets de acuerdo con el rol y las políticas de acceso vigentes.

Como comportamiento predeterminado del MVP, el Técnico tendrá visibilidad operativa sobre los tickets del sistema aunque no pertenezca al grupo asociado ni se encuentre formalmente asignado al ticket. La pertenencia a grupos y la asignación se utilizarán como mecanismos de organización, responsabilidad y seguimiento, pero no constituirán por sí solas una condición obligatoria para el acceso operativo del Técnico.

El Administrador podrá configurar restricciones de visibilidad y operación cuando una organización requiera un alcance más limitado.

**Alcance:** MVP.

---

# 8. Creación de tickets

## RF-012 — Creación de tickets

**Actor:** Todos los usuarios.

El sistema debe permitir crear tickets.

La creación deberá registrar automáticamente como mínimo:

* Identificador.
* Fecha y hora de creación.
* Usuario creador.

**Alcance:** MVP.

---

## RF-013 — Creación de tickets en nombre de otros usuarios

**Actor:** Usuarios autorizados.

El sistema debe permitir crear un ticket en nombre de otro usuario.

Debe conservarse la información de:

* Usuario que creó el ticket.
* Solicitantes asociados.

**Alcance:** MVP.

---

## RF-014 — Gestión de múltiples solicitantes

**Actor:** Usuarios autorizados.

El sistema debe permitir asociar uno o más solicitantes a un ticket.

Debe permitir:

* Agregar solicitantes.
* Quitar solicitantes.
* Consultar solicitantes asociados.

Las modificaciones deben respetar los permisos correspondientes.

**Alcance:** MVP.

---

## RF-015 — Tickets sin solicitante

**Actor:** Usuarios autorizados / Sistema.

El sistema debe permitir que un ticket exista sin solicitante asociado.

Esta capacidad permitirá representar tickets internos y facilitar futuras funcionalidades de generación programada.

**Alcance:** MVP.

---

## RF-016 — Registro del creador original

**Actor:** Sistema.

El sistema debe conservar permanentemente la identidad del usuario que creó originalmente el ticket, aunque posteriormente cambien los solicitantes asociados.

**Alcance:** MVP.

---

# 9. Información y clasificación del ticket

## RF-017 — Información principal del ticket

Cada ticket debe permitir gestionar como mínimo:

* Identificador.
* Título.
* Descripción.
* Categoría.
* Impacto, cuando se utilice.
* Urgencia, cuando se utilice.
* Prioridad.
* Estado.
* Ubicación física cuando corresponda.
* Grupo.
* Técnico(s).
* Solicitante(s).
* Fechas relevantes.
* Comentarios.
* Notas internas.
* Archivos.
* Historial.

**Alcance:** MVP.

---

## RF-018 — Gestión de ubicación

**Actor:** Usuarios autorizados.

El sistema debe permitir asociar una ubicación física a un ticket.

La ubicación podrá representar:

* Sucursal.
* Oficina.
* Edificio.
* Piso.
* Área.
* Instalación.
* Otra ubicación configurada.

**Alcance:** MVP.

---

## RF-019 — Configuración de obligatoriedad de ubicación

**Actor:** Administrador.

El sistema debe permitir configurar si la ubicación física es obligatoria al crear un ticket.

**Alcance:** MVP.

---

## RF-020 — Gestión de categorías

**Actor:** Administrador.

El sistema debe permitir:

* Crear categorías.
* Modificar categorías.
* Activar categorías.
* Desactivar categorías.
* Consultar categorías.

Las categorías activas estarán disponibles para clasificación.

**Alcance:** MVP.

---

## RF-021 — Categoría inicial

**Actor:** Sistema.

Cuando un solicitante no posea conocimientos suficientes para clasificar correctamente un ticket, el sistema deberá permitir utilizar una categoría válida inicial, por ejemplo:

`Sin clasificar`

Posteriormente podrá ser reemplazada por una clasificación más específica.

**Alcance:** MVP.

---

## RF-022 — Corrección de clasificación

**Actor:** Usuarios autorizados.

El sistema debe permitir modificar posteriormente la clasificación de un ticket según los permisos correspondientes.

Los cambios deberán conservarse en el historial.

**Alcance:** MVP.

---

# 10. Gestión de prioridades

## RF-023 — Niveles de prioridad

WorkDesk deberá disponer inicialmente de:

* Baja.
* Media.
* Alta.
* Crítica.

Estos valores deberán poder ser administrados.

**Alcance:** MVP.

---

## RF-024 — Asignación manual de prioridad

**Actor:** Solicitante / usuarios autorizados.

El sistema debe permitir establecer una prioridad manualmente.

La prioridad inicial podrá ser indicada por el solicitante y posteriormente revisada por los usuarios autorizados.

**Alcance:** MVP.

---

## RF-025 — Modificación de prioridad

**Actor:** Supervisor / Administrador.

El sistema debe permitir modificar la prioridad durante el ciclo de vida del ticket.

El cambio debe quedar registrado en el historial.

**Alcance:** MVP.

---

## RF-026 — Configuración de prioridades

**Actor:** Administrador.

El sistema debe permitir configurar los parámetros asociados a las prioridades, incluyendo según corresponda:

* Nombre.
* Orden.
* Color.
* Activación.
* Parámetros de SLA relacionados.

**Alcance:** MVP.

---

## RF-027 — Atención fuera del orden de prioridad

El sistema no deberá impedir que un técnico gestione, resuelva o cierre un ticket de menor prioridad cuando existan otros tickets de mayor prioridad.

La prioridad será una referencia operativa y no una regla de bloqueo de trabajo.

**Alcance:** MVP.

---

# 11. Gestión de técnicos y asignaciones

## RF-028 — Asignación manual

**Actor:** Usuarios autorizados.

El sistema debe permitir:

* Autoasignación.
* Asignación manual.
* Reasignación.
* Adición de técnicos.
* Eliminación de técnicos de la asignación.

**Alcance:** MVP.

---

## RF-029 — Múltiples técnicos por ticket

**Actor:** Usuarios autorizados.

Un ticket podrá tener uno o más técnicos asociados.

El sistema debe mostrar los técnicos participantes y mantener el historial de sus intervenciones.

**Alcance:** MVP.

---

## RF-030 — Historial de asignaciones

**Actor:** Sistema.

Toda modificación de asignación deberá registrar:

* Usuario que realizó la modificación.
* Técnicos anteriores.
* Técnicos posteriores.
* Fecha y hora.
* Tipo de acción.

**Alcance:** MVP.

---

## RF-031 — Autoasignación

**Actor:** Técnico.

El sistema debe permitir que un Técnico autorizado se asigne un ticket.

La acción deberá actualizar el estado de acuerdo con las reglas definidas.

**Alcance:** MVP.

---

## RF-032 — Reasignación de tickets

**Actor:** Supervisor / Administrador.

El sistema debe permitir modificar los técnicos responsables de un ticket.

**Alcance:** MVP.

---

## RF-033 — Reasignación por equilibrio de carga

**Actor:** Supervisor / Administrador.

El sistema debe permitir utilizar la información de carga de trabajo para apoyar decisiones de reasignación.

**Alcance:** MVP.

---

## RF-034 — Reasignación masiva por indisponibilidad

**Actor:** Supervisor / Administrador.

El sistema debe permitir transferir múltiples tickets asociados a un técnico hacia uno o más nuevos técnicos mediante una operación centralizada.

La funcionalidad deberá considerar situaciones como:

* Vacaciones.
* Licencias.
* Renuncias.
* Desvinculaciones.
* Cambios de funciones.
* Otras indisponibilidades.

La operación deberá evitar la necesidad de reasignar manualmente cada ticket uno por uno.

**Alcance:** MVP.

---

## RF-035 — Conservación de historial durante reasignación masiva

La reasignación masiva debe mantener:

* Técnico anterior.
* Técnico nuevo.
* Fecha y hora.
* Usuario que ejecutó la operación.
* Tickets afectados.

**Alcance:** MVP.

---

# 12. Carga de trabajo

## RF-036 — Visualización de carga de trabajo

**Actor:** Técnico / Supervisor / Administrador.

El sistema debe proporcionar información sobre la carga de trabajo de los técnicos.

Como mínimo podrá incluir:

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

**Alcance:** MVP.

---

## RF-037 — Indicador de sobrecarga

**Actor:** Sistema.

El sistema debe poder identificar una carga elevada de acuerdo con parámetros configurados y reflejarla visualmente o mediante notificaciones.

La sobrecarga no deberá bloquear automáticamente nuevas asignaciones.

La identificación de sobrecarga tendrá carácter informativo y nunca deberá impedir por sí misma la asignación, resolución o cierre de tickets.

**Alcance:** MVP.

---

## RF-038 — Información consolidada para Supervisores

**Actor:** Supervisor / Administrador.

El sistema debe permitir consultar la carga de múltiples técnicos de forma consolidada para facilitar la distribución del trabajo.

**Alcance:** MVP.

---

# 13. Escalamiento

## RF-039 — Escalamiento manual de tickets

**Actor:** Supervisor / Administrador.

El sistema debe permitir escalar manualmente un ticket a:

* Otro grupo.
* Otro técnico.
* Un nivel superior de atención.

La operación debe conservar la trazabilidad.

El escalamiento será una acción manual y no deberá modificar automáticamente la prioridad ni reasignar automáticamente el ticket a partir de reglas de SLA durante el MVP.

**Alcance:** MVP.

---

## RF-040 — Historial de escalamiento

El sistema debe registrar:

* Grupo anterior.
* Grupo nuevo.
* Técnicos anteriores.
* Técnicos nuevos.
* Usuario que realizó el escalamiento.
* Fecha y hora.

**Alcance:** MVP.

---

# 14. Ciclo de vida del ticket

## RF-041 — Estados principales

El sistema deberá utilizar inicialmente los siguientes estados:

1. Nuevo.
2. Asignado.
3. En progreso.
4. En espera.
5. Resuelto.
6. Cerrado.

**Alcance:** MVP.

---

## RF-042 — Cambio de estado

**Actor:** Usuarios autorizados.

El sistema debe permitir cambiar el estado respetando:

* Rol.
* Permisos.
* Estado actual.
* Transición permitida.
* Reglas de negocio.

Cada cambio deberá registrarse en el historial.

**Alcance:** MVP.

---

## RF-043 — Estado En espera

El sistema debe permitir colocar un ticket en estado **En espera** cuando se encuentre asignado y la continuidad del trabajo dependa de una condición externa.

**Alcance:** MVP.

---

## RF-044 — Motivo de espera

El sistema debe permitir registrar opcionalmente el motivo de una espera.

La ausencia de motivo no deberá impedir por sí sola la transición a `En espera`.

Los motivos deberán poder ser configurados administrativamente mediante un catálogo, incluyendo una alternativa genérica cuando corresponda.

**Alcance:** MVP.

---

## RF-045 — Reactivación de ticket en espera

El sistema debe permitir reactivar tickets que estén en espera.

La reactivación deberá devolver el ticket a un estado operativo y generar la trazabilidad y notificaciones correspondientes.

**Alcance:** MVP.

---

# 15. Resolución

## RF-046 — Marcar ticket como resuelto

**Actor:** Técnico / Supervisor / Administrador.

El sistema debe permitir marcar un ticket como **Resuelto** cuando corresponda.

Como comportamiento predeterminado del MVP, la resolución podrá ejecutarse desde `Nuevo`, `Asignado`, `En progreso` o `En espera`, siempre que el usuario posea permisos y se respeten las reglas de integridad del flujo. El Administrador podrá restringir transiciones dentro del conjunto estructuralmente válido.

La operación debe registrar la fecha y usuario responsable.

**Alcance:** MVP.

---

## RF-047 — Resolución sin comentario obligatorio

El sistema no deberá exigir obligatoriamente un comentario o nota para permitir cambiar el ticket a **Resuelto**.

Podrá configurarse posteriormente si una organización desea exigir contenido adicional.

**Alcance:** MVP.

---

## RF-048 — Resolución con validación del solicitante

El sistema debe permitir que un ticket pase a **Resuelto** y quede pendiente de validación por parte de los solicitantes correspondientes.

El sistema debe informar al solicitante que debe:

* Revisar la solución.
* Confirmar el cierre.
* Reabrir el ticket si la solución no es satisfactoria.

**Alcance:** MVP.

---

## RF-049 — Resolución con cierre directo

**Actor:** Técnico / Supervisor / Administrador.

El sistema debe permitir cerrar directamente un ticket sin requerir que previamente haya sido marcado como "Resuelto", siempre que el usuario tenga permisos para realizar dicha acción.

El cierre directo estará permitido desde `Nuevo`, `Asignado`, `En progreso` y `En espera`, de acuerdo con las reglas de acceso establecidas. No se utilizará como mecanismo de cierre directo desde `Resuelto`, ya que dicho estado posee su propio flujo de validación, cierre automático y cierre excepcional autorizado.

Esta modalidad permitirá atender situaciones como:

- Mantenciones.
- Tickets generados automáticamente.
- Tareas rutinarias.
- Solicitudes internas.
- Casos previamente validados por otro medio.
- Situaciones en las que no resulte necesario esperar una validación formal del solicitante.

El cierre directo deberá registrar en el historial:

- Usuario responsable.
- Fecha y hora.
- Estado anterior.
- Estado nuevo.
- Modalidad de cierre.
- Motivo de cierre, cuando corresponda.

El cierre directo finaliza el ticket inmediatamente y no activa el mecanismo de validación asociado al estado Resuelto.

Cuando un ticket sea marcado como "Resuelto", deberá aplicarse siempre el mecanismo de validación definido para dicho estado.

**Alcance:** MVP.

---

## RF-050 — Confirmación de cierre por solicitante

**Actor:** Solicitante.

Cuando un ticket se encuentre en estado "Resuelto", cualquiera de los solicitantes autorizados asociados al ticket podrá confirmar la solución.

La confirmación de uno de los solicitantes será suficiente para cerrar el ticket completo.

El sistema deberá registrar:

- Solicitante que realizó la confirmación.
- Fecha y hora.
- Estado anterior.
- Cierre resultante.

**Alcance:** MVP.

---

## RF-051 — Rechazo de resolución

**Actor:** Solicitante.

Cuando una solución no sea satisfactoria, el solicitante debe poder iniciar la reapertura del ticket.

El sistema debe permitir agregar información pública que explique la situación.

**Alcance:** MVP.

---

## RF-052 — Cierre automático por inactividad

**Actor:** Sistema.

El sistema debe poder cerrar automáticamente un ticket cuando se cumplan las condiciones de inactividad configuradas.

Cuando un ticket haya sido marcado como "Resuelto":

- Si existen solicitantes asociados, el sistema deberá esperar su validación durante el período configurado.
- Si ningún solicitante valida positiva o negativamente la resolución dentro del período configurado, el sistema deberá cerrar automáticamente el ticket.
- Si no existen solicitantes asociados, el sistema deberá esperar igualmente el período configurado antes de efectuar el cierre automático.

El valor predeterminado será de 24 horas.

El Administrador podrá modificar el período y las condiciones de aplicación.

El cierre automático deberá quedar registrado como una acción realizada por el sistema.

**Alcance:** MVP.

---

## RF-053 — Configuración de validación y cierre automático

**Actor:** Administrador.

El sistema debe permitir configurar:

- Activación o desactivación del cierre automático.
- Período de espera para validación.
- Unidad de tiempo.
- Condiciones de aplicación.
- Notificaciones relacionadas.

Cuando no existan solicitantes asociados, el ticket no requerirá validación humana, pero deberá respetar igualmente el período configurado antes del cierre automático.

El comportamiento configurable no deberá permitir eliminar este período de espera para los tickets que hayan sido marcados como Resuelto.

El valor inicial del período de espera será de 24 horas.

**Alcance:** MVP.

---

## RF-054 — Cierre excepcional

**Actor:** Supervisor / Administrador.

El sistema debe permitir realizar cierres excepcionales cuando las reglas de negocio lo autoricen.

La operación debe quedar claramente identificada en el historial.

**Alcance:** MVP.

---

# 17. Reapertura

## RF-055 — Reapertura de tickets

**Actor:** Solicitante / Técnico / Supervisor / Administrador según permisos.

El sistema debe permitir reabrir tickets cerrados o resueltos de acuerdo con las reglas establecidas.

La reapertura no constituye un estado independiente.

**Alcance:** MVP.

---

## RF-056 — Estado posterior a reapertura

Como comportamiento predeterminado, un ticket reabierto deberá regresar al estado **En progreso**.

La configuración administrativa podrá habilitar alternativas de destino para la reapertura únicamente cuando dichas alternativas formen parte de las transiciones estructuralmente válidas definidas por WorkDesk.

La configuración no deberá permitir que una reapertura conduzca a un estado incompatible con el ciclo de vida fundamental del ticket.

La reapertura continuará siendo una acción y no constituirá un estado independiente.

**Alcance:** MVP.

---

## RF-057 — Reapertura por solicitante

**Actor:** Solicitante.

El sistema debe proporcionar al solicitante autorizado una acción explícita de "Reabrir ticket" cuando la política de reapertura lo permita.

Al reabrir un ticket:

1. El ticket deberá regresar a un estado operativo.
2. Se conservarán los técnicos participantes anteriores.
3. El solicitante podrá agregar un comentario público explicando la situación.
4. El comentario deberá notificar a los técnicos correspondientes.

La reapertura y el comentario posterior deberán quedar registrados en el historial.

**Alcance:** MVP.

---

## RF-058 — Conservación de técnicos tras reapertura

Cuando un ticket sea reabierto, el sistema debe conservar inicialmente los técnicos que participaron anteriormente.

Los usuarios autorizados podrán modificar posteriormente la asignación.

**Alcance:** MVP.

---

## RF-059 — Notificación de reapertura

Toda reapertura debe generar las notificaciones internas correspondientes.

**Alcance:** MVP.

---

## RF-060 — Configuración del período de reapertura

El Administrador debe poder establecer las políticas relacionadas con el período de reapertura.

**Alcance:** MVP.

---

# 18. Tickets duplicados y relacionados

## RF-061 — Detección de posibles duplicados

El sistema debe poder advertir sobre posibles tickets duplicados cuando existan coincidencias relevantes.

La advertencia no deberá necesariamente impedir la creación.

**Alcance:** MVP.

---

## RF-062 — Vinculación entre tickets

El sistema debe permitir vincular tickets relacionados.

Deberá ser posible identificar:

* Ticket original.
* Ticket duplicado.
* Tickets relacionados.

**Alcance:** MVP.

---

## RF-063 — Navegación entre tickets relacionados

El usuario autorizado debe poder navegar desde un ticket hacia los tickets relacionados.

**Alcance:** MVP.

---

## RF-064 — Cierre por duplicidad

El sistema debe permitir cerrar un ticket identificado como duplicado utilizando un motivo de cierre correspondiente.

No se requiere un estado independiente denominado **Duplicado**.

**Alcance:** MVP.

---

## RF-065 — Historial de duplicidad

El sistema debe registrar:

* Ticket original.
* Ticket marcado como duplicado.
* Usuario responsable.
* Fecha y hora.

**Alcance:** MVP.

---

# 19. Comentarios y notas internas

## RF-066 — Comentarios públicos

El sistema debe permitir agregar comentarios públicos a un ticket.

Los comentarios deberán permanecer asociados cronológicamente al ticket.

**Alcance:** MVP.

---

## RF-067 — Comentarios del solicitante

Los solicitantes autorizados podrán agregar comentarios públicos durante el ciclo de vida correspondiente.

**Alcance:** MVP.

---

## RF-068 — Comentario posterior a reapertura

Cuando un solicitante reabra un ticket, deberá poder utilizar el mecanismo de comentarios públicos para explicar la situación y proporcionar información adicional.

El comentario deberá generar las notificaciones correspondientes a los técnicos autorizados.

**Alcance:** MVP.

---

## RF-069 — Notas internas

**Actor:** Técnico / Supervisor / Administrador.

El sistema debe permitir registrar notas internas destinadas al personal de soporte.

Las notas internas no deberán ser visibles para los solicitantes.

**Alcance:** MVP.

---

## RF-070 — Visibilidad según permisos

El sistema debe aplicar las reglas de visibilidad correspondientes tanto a comentarios como a notas internas.

**Alcance:** MVP.

---

## RF-071 — Historial de comentarios y notas

Los comentarios y notas deberán quedar registrados como parte de la actividad del ticket.

**Alcance:** MVP.

---

# 20. Archivos adjuntos

## RF-072 — Carga de archivos

El sistema debe permitir adjuntar archivos a los tickets:

* Durante la creación.
* Durante la gestión posterior.

**Alcance:** MVP.

---

## RF-073 — Tipos de archivo

El sistema debe permitir configurar los tipos de archivo aceptados.

Los tipos potencialmente peligrosos deben permanecer restringidos.

**Alcance:** MVP.

---

## RF-074 — Límites de archivos

El Administrador debe poder configurar:

* Tamaño máximo.
* Cantidad máxima.
* Otros límites operativos.

**Alcance:** MVP.

---

## RF-075 — Validación de archivos

El sistema debe validar los archivos antes de almacenarlos según las restricciones configuradas.

**Alcance:** MVP.

---

## RF-076 — Descarga y visualización

Los usuarios autorizados deben poder consultar o descargar los archivos según sus permisos.

**Alcance:** MVP.

---

# 21. SLA

## RF-077 — Configuración de SLA

**Actor:** Administrador.

El sistema debe permitir configurar parámetros de SLA asociados al servicio de soporte.

Como mínimo deberá poder definirse el tiempo objetivo correspondiente a las prioridades.

**Alcance:** MVP.

---

## RF-078 — Cálculo del SLA

El sistema debe calcular el tiempo utilizado por un ticket de acuerdo con la configuración aplicable.

**Alcance:** MVP.

---

## RF-079 — Horarios y días hábiles

El sistema debe considerar horarios laborales, días hábiles y feriados configurados para el cálculo de SLA cuando corresponda.

**Alcance:** MVP.

---

## RF-080 — Pausa del SLA

El sistema debe contemplar la pausa del SLA durante períodos definidos como fuera del tiempo efectivo de atención, incluyendo el comportamiento correspondiente al estado **En espera** según la configuración.

**Alcance:** MVP.

---

## RF-081 — Indicador de estado del SLA

El sistema debe identificar si un ticket se encuentra:

* Dentro de SLA.
* Próximo a vencer.
* Fuera de SLA.

**Alcance:** MVP.

---

## RF-082 — Notificación de vencimiento

El sistema debe generar notificaciones internas cuando un ticket alcance las condiciones configuradas de advertencia o incumplimiento de SLA.

**Alcance:** MVP.

---

## RF-083 — Gestión de excepciones de SLA

**Actor:** Supervisor / Administrador.

El sistema debe permitir gestionar excepciones relacionadas con el SLA según el nivel de autorización correspondiente.

El Supervisor podrá:

- Gestionar excepciones operativas.
- Pausar o modificar el comportamiento del SLA cuando las reglas de negocio lo permitan.
- Realizar acciones necesarias para resolver situaciones excepcionales.

El Administrador tendrá privilegios superiores y podrá:

- Configurar políticas y parámetros generales de SLA.
- Configurar tiempos objetivo.
- Configurar horarios laborales y días no hábiles.
- Gestionar excepciones administrativas.
- Modificar parámetros globales.
- Administrar las políticas de SLA del sistema.

El Técnico no podrá modificar, reiniciar o alterar administrativamente el SLA.

Las acciones de gestión manual del SLA deberán quedar registradas en la trazabilidad correspondiente.

**Alcance:** MVP.

---

# 22. Notificaciones internas

## RF-084 — Generación de notificaciones

El sistema debe generar notificaciones internas para eventos relevantes, incluyendo:

* Creación.
* Asignación.
* Reasignación.
* Cambio de estado.
* Comentario.
* Nota interna.
* Espera.
* Resolución.
* Cierre.
* Reapertura.
* Vencimiento de SLA.
* Próximo vencimiento.

**Alcance:** MVP.

---

## RF-085 — Centro de notificaciones

El sistema debe proporcionar un centro de notificaciones.

Debe permitir:

* Ver notificaciones.
* Acceder al ticket relacionado.
* Identificar no leídas.

**Alcance:** MVP.

---

## RF-086 — Estado de lectura

El usuario debe poder:

* Marcar una notificación como leída.
* Marcar todas como leídas.

**Alcance:** MVP.

---

## RF-087 — Configuración de notificaciones

**Actor:** Administrador.

El sistema debe permitir configurar los eventos y destinatarios de las notificaciones según las políticas definidas.

**Alcance:** MVP.

---

# 23. Búsqueda, filtros y consultas

## RF-088 — Búsqueda por identificador

El sistema debe permitir localizar tickets mediante su identificador.

**Alcance:** MVP.

---

## RF-089 — Búsqueda por otros campos

El sistema debe permitir realizar búsquedas mediante campos relevantes, incluyendo cuando corresponda:

* Título.
* Descripción.
* Categoría.
* Solicitante.
* Técnico.
* Grupo.

**Alcance:** MVP.

---

## RF-090 — Filtros

El sistema debe permitir filtrar tickets por criterios tales como:

* Estado.
* Prioridad.
* Categoría.
* Solicitante.
* Técnico.
* Grupo.
* Fechas.
* SLA.

**Alcance:** MVP.

---

## RF-091 — Combinación de filtros

El usuario debe poder combinar distintos filtros simultáneamente.

**Alcance:** MVP.

---

## RF-092 — Ordenamiento

El sistema debe permitir ordenar los resultados según criterios relevantes.

**Alcance:** MVP.

---

# 24. Dashboards

## RF-093 — Dashboard adaptado al rol

El sistema debe proporcionar una vista principal adaptada al rol del usuario.

**Alcance:** MVP.

---

## RF-094 — Dashboard de Técnico

Debe permitir visualizar al menos:

* Tickets asignados.
* Tickets activos.
* Tickets en progreso.
* Tickets en espera.
* Tickets próximos a vencer.
* Tickets fuera de SLA.
* Indicadores básicos de productividad.

**Alcance:** MVP.

---

## RF-095 — Dashboard de Supervisor

Debe permitir visualizar:

* Tickets globales.
* Tickets sin asignar.
* Carga por técnico.
* Tickets por prioridad.
* Tickets fuera de SLA.
* Tickets próximos a vencer.
* Indicadores operativos.

**Alcance:** MVP.

---

## RF-096 — Dashboard de Administrador

Debe proporcionar información global del sistema y acceso a indicadores administrativos.

**Alcance:** MVP.

---

## RF-097 — Dashboard de Solicitante

Debe permitir consultar:

* Tickets propios.
* Tickets que requieren intervención.
* Tickets resueltos pendientes de validación.
* Notificaciones.
* Acceso a creación de tickets.

**Alcance:** MVP.

---

# 25. Reportes y exportación

## RF-098 — Reportes operativos

El sistema debe permitir generar reportes basados en la información disponible y en los permisos del usuario.

**Alcance:** MVP.

---

## RF-099 — Exportación CSV

El sistema debe permitir exportar información seleccionada en formato CSV.

**Alcance:** MVP.

---

## RF-100 — Exportación XLSX

El sistema debe permitir exportar información seleccionada en formato XLSX.

**Alcance:** MVP.

---

## RF-101 — Exportación utilizando filtros

Las exportaciones deben respetar los filtros utilizados por el usuario.

**Alcance:** MVP.

---

# 26. Base de conocimientos

## RF-102 — Gestión de artículos

El sistema debe permitir:

* Crear.
* Consultar.
* Modificar.
* Publicar.
* Desactivar o eliminar artículos.

**Alcance:** MVP.

---

## RF-103 — Artículos públicos y privados

El sistema debe permitir diferenciar entre información pública y privada.

**Alcance:** MVP.

---

## RF-104 — Vinculación con tickets

El sistema debe permitir asociar tickets con artículos de la Base de Conocimientos.

**Alcance:** MVP.

---

## RF-105 — Promoción de solución a conocimiento

El sistema debe permitir utilizar una resolución de ticket como base para generar un artículo de conocimiento.

**Alcance:** MVP.

---

# 27. Historial y auditoría

## RF-106 — Historial del ticket

El sistema debe mantener un historial cronológico de las acciones relevantes.

Debe incluir cuando corresponda:

* Creación.
* Cambios de estado.
* Asignaciones.
* Reasignaciones.
* Cambios de prioridad.
* Cambios de categoría.
* Comentarios.
* Notas.
* Adjuntos.
* Resolución.
* Cierre.
* Reapertura.
* Vinculación de duplicados.
* Escalamiento.

**Alcance:** MVP.

---

## RF-107 — Información del evento histórico

Los eventos históricos deberán registrar cuando corresponda:

* Usuario.
* Fecha y hora.
* Acción.
* Valor anterior.
* Valor nuevo.

**Alcance:** MVP.

---

## RF-108 — Auditoría administrativa

El sistema debe mantener registros de operaciones administrativas relevantes, diferenciándolas del historial operativo del ticket.

**Alcance:** MVP.

---

## RF-109 — Consulta de auditoría

**Actor:** Administrador.

El Administrador debe poder consultar la información de auditoría a la que tenga acceso.

**Alcance:** MVP.

---

# 28. Retención y conservación de información

## RF-110 — Configuración de retención

**Actor:** Administrador.

El sistema debe permitir establecer políticas de retención para:

- Tickets cerrados.
- Historial.
- Auditoría.
- Notificaciones.
- Archivos adjuntos.
- Logs.

Ninguna política de retención deberá ejecutarse sin que exista una configuración administrativa explícita que la habilite.

Toda modificación de una política de retención deberá quedar registrada en la auditoría administrativa.

**Alcance:** MVP.

---

## RF-111 — Acción posterior a la retención

El sistema debe permitir definir qué ocurre cuando un registro supera su período de retención.

Las acciones configurables podrán incluir:

- Mantener.
- Archivar.
- Eliminar.

La ejecución deberá estar condicionada a una política de retención previamente habilitada por el Administrador.

Las operaciones ejecutadas como consecuencia de una política de retención deberán quedar registradas cuando corresponda.

**Alcance:** MVP.

---

## RF-112 — Protección de relaciones históricas

El sistema debe evitar que las políticas de retención produzcan referencias inconsistentes entre tickets y elementos asociados.

**Alcance:** MVP.

---

# 29. Configuración administrativa

## RF-113 — Configuración general

**Actor:** Administrador.

El sistema debe disponer de un área de configuración administrativa.

**Alcance:** MVP.

---

## RF-114 — Configuración de categorías

El Administrador debe poder gestionar las categorías sin modificar el código fuente.

**Alcance:** MVP.

---

## RF-115 — Configuración de prioridades

El Administrador debe poder gestionar niveles y parámetros de prioridad.

**Alcance:** MVP.

---

## RF-116 — Configuración de ubicaciones

El Administrador debe poder gestionar las ubicaciones disponibles y su obligatoriedad.

**Alcance:** MVP.

---

## RF-117 — Configuración de grupos

El Administrador debe poder gestionar grupos y asociaciones de técnicos.

**Alcance:** MVP.

---

## RF-118 — Configuración controlada de estados y transiciones

**Actor:** Administrador.

El sistema debe permitir configurar determinados atributos de los estados base del flujo de tickets sin alterar la estructura fundamental del ciclo de vida.

El Administrador podrá configurar:

* Nombre visible del estado.
* Color asociado al estado.
* Orden de visualización.
* Descripción o ayuda contextual.
* Transiciones permitidas entre los estados base, siempre que correspondan a transiciones estructuralmente válidas definidas por WorkDesk.

El sistema no deberá permitir mediante esta configuración:

* Crear estados estructurales nuevos.
* Eliminar estados estructurales del MVP.
* Convertir la reapertura en un estado independiente.
* Eliminar las etapas fundamentales del ciclo de vida.
* Configurar transiciones que contradigan las reglas fundamentales del flujo.
* Habilitar combinaciones de estados que generen un ciclo de vida incoherente o impidan las operaciones esenciales de WorkDesk.

Los seis estados base del MVP deberán mantenerse:

1. Nuevo.
2. Asignado.
3. En progreso.
4. En espera.
5. Resuelto.
6. Cerrado.

La configuración administrativa deberá limitarse a personalizar atributos y habilitar o deshabilitar transiciones dentro del conjunto de estados y restricciones estructurales definidos por WorkDesk.

La definición detallada de las transiciones válidas será desarrollada posteriormente en `08_flujo_de_tickets.md`.

**Alcance:** MVP.


---

## RF-119 — Configuración de SLA

El Administrador debe poder gestionar los parámetros relacionados con SLA.

**Alcance:** MVP.

---

## RF-120 — Configuración de cierre y reapertura

El Administrador debe poder configurar:

* Cierre automático.
* Períodos de inactividad.
* Políticas de reapertura.
* Parámetros relacionados.

**Alcance:** MVP.

---

## RF-121 — Configuración de notificaciones

El Administrador debe poder gestionar las reglas de notificación permitidas por WorkDesk.

**Alcance:** MVP.

---

## RF-122 — Configuración de archivos

El Administrador debe poder gestionar las restricciones relacionadas con archivos adjuntos.

**Alcance:** MVP.

---

## RF-123 — Configuración de retención

El Administrador debe poder gestionar las políticas de conservación, archivo o eliminación de información.

**Alcance:** MVP.

---

# 30. Inicialización del sistema

## RF-124 — Inicialización administrativa

Durante la instalación o primera ejecución, WorkDesk debe disponer de un mecanismo para establecer la cuenta Administrador inicial.

**Alcance:** MVP.

---

## RF-125 — Credenciales iniciales

Cuando se utilicen credenciales temporales para la cuenta Administrador inicial, el sistema deberá requerir su actualización antes de considerar completada la configuración inicial.

**Alcance:** MVP.

---

## RF-126 — Configuración inicial

WorkDesk debe proporcionar una configuración inicial que permita comenzar a utilizar el sistema sin requerir configurar manualmente todos sus componentes desde cero.

La configuración inicial podrá incluir:

* Categorías.
* Prioridades.
* Parámetros básicos de SLA.
* Estados.
* Configuraciones necesarias para el funcionamiento inicial.

**Alcance:** MVP.

---

# 31. Respaldo y mantenimiento administrativo

## RF-127 — Generación manual de respaldo

**Actor:** Administrador.

El sistema deberá proporcionar o integrarse con un mecanismo documentado para generar respaldos de:

* Base de datos.
* Archivos adjuntos.

**Alcance:** MVP.

---

## RF-128 — Restauración controlada

**Actor:** Administrador.

El sistema deberá contemplar un mecanismo documentado y controlado para restaurar información respaldada.

**Alcance:** MVP.

---

# 32. Gestión de errores y estado del sistema

## RF-129 — Registro de errores

El sistema debe permitir registrar errores y excepciones para diagnóstico interno.

**Alcance:** MVP.

---

## RF-130 — Indicadores de estado

El sistema debe proporcionar mecanismos básicos para conocer el estado de componentes relevantes de WorkDesk, como la aplicación y la base de datos.

**Alcance:** MVP.

---

# 33. Funcionalidades expresamente fuera del MVP

Las siguientes funcionalidades no forman parte de los requisitos funcionales obligatorios del MVP:

* Asignación automática avanzada.
* Reasignación automática basada en carga.
* Escalamiento automático complejo.
* Workflows dinámicos creados por usuarios.
* Inteligencia artificial.
* Machine Learning.
* Integraciones externas obligatorias.
* Correo electrónico.
* SMS.
* WhatsApp.
* Aplicaciones móviles nativas.
* Multiempresa operativo.
* Gestión completa de proyectos.
* Gestión completa de tareas.
* Gestión avanzada de activos.
* Inventario.
* Chat en tiempo real.
* Portal público no autenticado.
* Encuestas de satisfacción.
* Predicción de tiempos.
* Clasificación automática mediante IA.
* Dashboard ejecutivo avanzado.

Estas capacidades podrán incorporarse posteriormente de acuerdo con el roadmap y la evolución del producto.

---

# 34. Matriz de alcance del MVP

| Área                  | Requisito       | MVP |
| --------------------- | --------------- | --- |
| Autenticación         | RF-001 a RF-004 | Sí  |
| Usuarios              | RF-005 a RF-007 | Sí  |
| Grupos                | RF-008 a RF-011 | Sí  |
| Creación de tickets   | RF-012 a RF-016 | Sí  |
| Clasificación         | RF-017 a RF-022 | Sí  |
| Prioridades           | RF-023 a RF-027 | Sí  |
| Asignación            | RF-028 a RF-035 | Sí  |
| Carga de trabajo      | RF-036 a RF-038 | Sí  |
| Escalamiento          | RF-039 a RF-040 | Sí  |
| Estados               | RF-041 a RF-045 | Sí  |
| Resolución            | RF-046 a RF-049 | Sí  |
| Cierre                | RF-050 a RF-054 | Sí  |
| Reapertura            | RF-055 a RF-060 | Sí  |
| Duplicados            | RF-061 a RF-065 | Sí  |
| Comentarios           | RF-066 a RF-071 | Sí  |
| Archivos              | RF-072 a RF-076 | Sí  |
| SLA                   | RF-077 a RF-083 | Sí  |
| Notificaciones        | RF-084 a RF-087 | Sí  |
| Búsqueda              | RF-088 a RF-092 | Sí  |
| Dashboards            | RF-093 a RF-097 | Sí  |
| Reportes              | RF-098 a RF-101 | Sí  |
| Base de conocimientos | RF-102 a RF-105 | Sí  |
| Auditoría             | RF-106 a RF-109 | Sí  |
| Retención             | RF-110 a RF-112 | Sí  |
| Configuración         | RF-113 a RF-123 | Sí  |
| Inicialización        | RF-124 a RF-126 | Sí  |
| Respaldo              | RF-127 a RF-128 | Sí  |
| Estado del sistema    | RF-129 a RF-130 | Sí  |

---

# 35. Trazabilidad

Los requisitos funcionales definidos en este documento deberán servir como base para los siguientes artefactos:

```text
04_requisitos_funcionales.md
          │
          ├── 06_reglas_de_negocio.md
          │
          ├── 07_casos_de_uso.md
          │
          ├── 08_flujo_de_tickets.md
          │
          ├── 09_modelo_de_datos.md
          │
          ├── 10_arquitectura.md
          │
          ├── 11_diseno_de_pantallas.md
          │
          └── Pruebas
```

Cada requisito funcional deberá poder relacionarse posteriormente con uno o más casos de uso, componentes, elementos del modelo de datos y pruebas.

---

# 36. Consideraciones de diseño funcional

Los requisitos de este documento establecen **qué debe proporcionar WorkDesk**, pero no determinan cómo debe ser implementado técnicamente.

Las decisiones relacionadas con:

* Arquitectura.
* Base de datos.
* API.
* Seguridad técnica.
* Almacenamiento.
* Rendimiento.
* Concurrencia.
* Mecanismos de autenticación.
* Infraestructura.

se definirán en los documentos técnicos correspondientes.

Las reglas que determinan cuándo y bajo qué condiciones puede ejecutarse cada funcionalidad se encuentran en `06_reglas_de_negocio.md`.

Los escenarios detallados de interacción serán desarrollados en `07_casos_de_uso.md`.

El flujo visual y operacional de los tickets será desarrollado en `08_flujo_de_tickets.md`.

---

# 37. Principio funcional central

WorkDesk deberá proporcionar las herramientas necesarias para que los equipos de soporte puedan gestionar tickets de manera flexible, colaborativa y trazable.

El sistema no deberá reemplazar innecesariamente el criterio operativo humano.

La solución deberá:

* Centralizar la información.
* Facilitar la colaboración.
* Mantener la trazabilidad.
* Permitir flexibilidad operativa.
* Mostrar información suficiente para apoyar la toma de decisiones.
* Facilitar la redistribución del trabajo.
* Mantener la integridad de la información.
* Permitir evolución progresiva.

La prioridad del MVP será proporcionar un núcleo sólido de gestión de tickets antes que incorporar automatizaciones o capacidades avanzadas que aumenten innecesariamente su complejidad.

---

## Fin del documento
