# 07. Casos de Uso

## 1. Propósito del documento

El presente documento define los **casos de uso de WorkDesk**, describiendo las interacciones entre los actores del sistema y las principales funcionalidades del MVP.

Los casos de uso representan escenarios concretos de utilización derivados de los requisitos funcionales definidos en:

* `04_requisitos_funcionales.md`
* `05_requisitos_no_funcionales.md`
* `06_reglas_de_negocio.md`

Su objetivo es transformar los requisitos y reglas del sistema en comportamientos operativos comprensibles, verificables y trazables.

Los casos de uso servirán como base para:

* Diseño funcional.
* Diseño de pantallas.
* Diseño de flujos.
* Modelo de datos.
* Arquitectura.
* Implementación.
* Pruebas funcionales.
* Validación del MVP.

Este documento describe **cómo interactúan los actores con WorkDesk**, pero no define detalles técnicos de implementación.

---

# 2. Alcance

Los casos de uso definidos en este documento corresponden al **MVP de WorkDesk**.

El alcance contempla las siguientes áreas:

* Autenticación y sesiones.
* Gestión de usuarios.
* Gestión de grupos.
* Gestión de tickets.
* Solicitantes múltiples.
* Técnicos múltiples.
* Clasificación.
* Prioridades.
* Estados y transiciones.
* Asignación y reasignación.
* Reasignación masiva.
* Carga de trabajo.
* Escalamiento manual.
* Resolución.
* Cierre.
* Reapertura.
* Tickets duplicados y relacionados.
* Comentarios y notas internas.
* Archivos adjuntos.
* SLA.
* Notificaciones internas.
* Búsqueda y filtros.
* Dashboards.
* Reportes y exportaciones.
* Base de conocimientos.
* Historial y auditoría.
* Retención.
* Configuración administrativa.
* Inicialización.
* Respaldo y restauración.
* Estado y diagnóstico básico del sistema.

Las capacidades avanzadas expresamente excluidas del MVP continúan fuera del alcance de este documento.

---

# 3. Actores

## 3.1. Solicitante

Usuario que registra solicitudes, consulta tickets en los que participa y puede intervenir sobre ellos de acuerdo con sus permisos.

Entre sus principales interacciones se encuentran:

* Crear tickets.
* Crear tickets para sí mismo.
* Consultar tickets autorizados.
* Agregar comentarios públicos.
* Adjuntar archivos cuando corresponda.
* Revisar resoluciones.
* Confirmar una resolución.
* Reabrir tickets cuando corresponda.
* Consultar notificaciones.

---

## 3.2. Técnico

Usuario encargado de la atención y resolución operativa de tickets.

Entre sus principales interacciones se encuentran:

* Consultar tickets autorizados.
* Autoasignarse tickets cuando corresponda.
* Trabajar, como comportamiento predeterminado del MVP, sobre tickets de cualquier grupo aunque no esté formalmente asignado a ellos, dentro de las capacidades operativas de su rol.
* Modificar estados permitidos.
* Utilizar `En espera`.
* Agregar comentarios públicos.
* Registrar notas internas.
* Adjuntar archivos.
* Marcar tickets como `Resuelto`.
* Cerrar directamente tickets cuando corresponda.
* Consultar información de SLA.
* Colaborar con otros técnicos.

---

## 3.3. Supervisor

Usuario con capacidad de supervisión y gestión operacional ampliada.

Entre sus principales interacciones se encuentran:

* Supervisar tickets.
* Modificar prioridades.
* Reasignar tickets.
* Redistribuir carga.
* Realizar reasignaciones masivas.
* Escalar tickets.
* Gestionar estados.
* Gestionar excepciones de SLA.
* Intervenir en cierres y reaperturas.
* Consultar dashboards y reportes.
* Supervisar situaciones operativas.

---

## 3.4. Administrador

Usuario con privilegios administrativos globales.

Entre sus principales interacciones se encuentran:

* Gestionar usuarios.
* Gestionar roles.
* Gestionar grupos.
* Gestionar categorías.
* Gestionar prioridades.
* Gestionar ubicaciones.
* Configurar estados y transiciones permitidas.
* Configurar SLA.
* Configurar cierre y reapertura.
* Configurar notificaciones.
* Configurar archivos.
* Configurar retención.
* Consultar auditoría.
* Gestionar respaldos y restauraciones.
* Administrar la configuración general del sistema.

---

## 3.5. Sistema

Actor lógico que representa procesos automáticos de WorkDesk.

Entre sus principales responsabilidades se encuentran:

* Gestionar sesiones.
* Generar identificadores.
* Registrar historial.
* Calcular SLA.
* Generar notificaciones internas.
* Ejecutar cierres automáticos cuando corresponda.
* Registrar errores.
* Proporcionar información de estado.
* Ejecutar otras automatizaciones básicas contempladas por el MVP.

---

# 4. Convenciones de casos de uso

Cada caso de uso se identifica mediante:

`CU-XXX`

Cada caso de uso podrá contener:

* Identificador.
* Nombre.
* Actores.
* Objetivo.
* Precondiciones.
* Disparador.
* Flujo principal.
* Flujos alternativos y excepciones.
* Postcondiciones.
* Reglas de negocio relacionadas.
* Requisitos funcionales relacionados.
* Alcance.

Los casos de uso representan comportamiento funcional y no describen tecnologías concretas.

---

# 5. Casos de uso de autenticación y acceso

## CU-001 — Iniciar sesión

**Actores:** Solicitante, Técnico, Supervisor, Administrador.

**Objetivo:** Permitir que un usuario registrado acceda a WorkDesk de forma autenticada.

**Precondiciones:**

* El usuario debe estar registrado.
* El usuario debe encontrarse habilitado.
* WorkDesk debe encontrarse disponible.

**Disparador:**

El usuario intenta acceder al sistema.

### Flujo principal

1. El usuario ingresa sus credenciales.
2. WorkDesk recibe la solicitud de autenticación.
3. El sistema valida las credenciales.
4. El sistema valida que la cuenta pueda utilizarse.
5. El sistema establece la sesión.
6. El sistema identifica el rol del usuario.
7. WorkDesk permite el acceso a las funcionalidades autorizadas.
8. El usuario accede a su vista principal.

### Flujos alternativos y excepciones

**A1. Credenciales incorrectas**

1. WorkDesk rechaza la autenticación.
2. Se registra el intento fallido.
3. Se informa al usuario que las credenciales no son válidas.

**A2. Límite de intentos alcanzado**

1. WorkDesk aplica la política de bloqueo temporal configurada.
2. Se informa al usuario que no puede autenticarse temporalmente.

**A3. Usuario desactivado**

1. WorkDesk rechaza el acceso.
2. El sistema conserva la información histórica del usuario.

**A4. Error interno**

1. WorkDesk informa una falla controlada.
2. El error queda registrado.

**Postcondiciones:**

* Se crea una sesión válida cuando la autenticación es correcta.
* El usuario obtiene únicamente los permisos correspondientes a su rol.

**RF relacionados:** RF-001, RF-003, RF-004.

**RN relacionadas:** RN-83, RN-87.

**Alcance:** MVP.

---

## CU-002 — Cerrar sesión

**Actores:** Solicitante, Técnico, Supervisor, Administrador.

**Objetivo:** Finalizar explícitamente la sesión actual.

### Flujo principal

1. El usuario solicita cerrar sesión.
2. WorkDesk invalida la sesión actual.
3. El sistema devuelve al usuario al acceso de autenticación.

**Postcondiciones:**

* La sesión deja de estar disponible.

**RF relacionados:** RF-002, RF-003.

**Alcance:** MVP.

---

## CU-003 — Gestionar expiración e invalidación de sesión

**Actor:** Sistema.

**Objetivo:** Mantener las sesiones dentro de las políticas de seguridad definidas.

### Flujo principal

1. WorkDesk mantiene activa la sesión mientras sea válida.
2. El sistema controla el tiempo de inactividad.
3. El sistema controla la duración máxima de la sesión.
4. Cuando una política obliga a invalidar la sesión, WorkDesk la invalida.
5. El usuario deberá autenticarse nuevamente.

### Casos relacionados

* Expiración por inactividad.
* Duración máxima.
* Invalidación posterior a cambio de credenciales.
* Invalidación administrativa cuando corresponda.

**RF relacionados:** RF-003.

**RNF relacionados:** RNF-013, RNF-014, RNF-015.

**Alcance:** MVP.

---

# 6. Casos de uso de administración de usuarios

## CU-004 — Gestionar usuarios

**Actor:** Administrador.

**Objetivo:** Crear y administrar las cuentas de usuario de WorkDesk.

### Flujo principal

1. El Administrador accede a la gestión de usuarios.
2. Consulta usuarios existentes.
3. Puede crear un nuevo usuario.
4. Ingresa la información requerida.
5. Asigna el rol correspondiente.
6. Guarda la información.
7. WorkDesk registra la operación.
8. El nuevo usuario queda disponible según su estado.

El Administrador también puede:

* Modificar información.
* Activar usuarios.
* Desactivar usuarios.
* Gestionar roles.

### Flujos alternativos

**A1. Desactivación de usuario**

1. El Administrador desactiva la cuenta.
2. WorkDesk impide nuevos accesos normales.
3. La información histórica permanece disponible.

**A2. Usuario desactivado con tickets activos**

1. WorkDesk identifica los tickets afectados.
2. El Supervisor o Administrador puede iniciar su redistribución.
3. Las asignaciones anteriores se conservan en el historial.

**RF relacionados:** RF-005, RF-006, RF-007.

**RN relacionadas:** RN-05, RN-83, RN-84, RN-85, RN-86, RN-87.

**Alcance:** MVP.

---

# 7. Casos de uso de grupos y clasificación

## CU-005 — Gestionar grupos

**Actor:** Administrador.

**Objetivo:** Administrar las unidades organizativas de atención.

### Flujo principal

1. El Administrador accede a grupos.
2. Consulta los grupos existentes.
3. Puede crear un grupo.
4. Puede modificar un grupo.
5. Puede activar o desactivar un grupo.
6. Puede asociar técnicos a uno o más grupos.
7. WorkDesk registra los cambios relevantes.

**RF relacionados:** RF-008, RF-009, RF-117.

**RN relacionadas:** RN-04, RN-05, RN-85, RN-86.

**Alcance:** MVP.

---

## CU-006 — Gestionar categorías

**Actor:** Administrador.

**Objetivo:** Mantener el catálogo de categorías utilizado para clasificar tickets.

### Flujo principal

1. El Administrador consulta las categorías.
2. Puede crear nuevas categorías.
3. Puede modificar categorías.
4. Puede activar o desactivar categorías.
5. WorkDesk mantiene disponibles las categorías activas.
6. Los cambios relevantes quedan registrados.

**RF relacionados:** RF-020, RF-021, RF-114.

**RN relacionadas:** RN-04, RN-05, RN-15, RN-16, RN-85.

**Alcance:** MVP.

---

## CU-007 — Gestionar ubicaciones

**Actor:** Administrador.

**Objetivo:** Administrar las ubicaciones físicas disponibles y su obligatoriedad.

### Flujo principal

1. El Administrador consulta las ubicaciones.
2. Crea, modifica, activa o desactiva ubicaciones.
3. Define la política de obligatoriedad.
4. WorkDesk aplica la configuración a la creación de tickets.

**RF relacionados:** RF-018, RF-019, RF-116.

**RN relacionadas:** RN-13, RN-14.

**Alcance:** MVP.

---

# 8. Casos de uso de creación y gestión de tickets

## CU-008 — Crear ticket

**Actores:** Solicitante, Técnico, Supervisor, Administrador.

**Objetivo:** Registrar una nueva solicitud en WorkDesk.

**Precondiciones:**

* El usuario está autenticado.
* Posee permiso para crear tickets.

### Flujo principal

1. El usuario selecciona la opción de crear ticket.
2. WorkDesk presenta el formulario correspondiente.
3. El usuario ingresa el título.
4. Ingresa la descripción.
5. Selecciona o utiliza una categoría válida.
6. Indica la prioridad.
7. Puede informar impacto y urgencia de manera opcional.
8. Informa ubicación si es requerida.
9. Puede asociar solicitantes.
10. Puede adjuntar archivos.
11. El usuario confirma la creación.
12. WorkDesk genera el identificador único.
13. Registra la fecha y hora.
14. Registra al usuario creador.
15. Establece el estado inicial correspondiente.
16. Registra el evento en el historial.
17. Genera las notificaciones correspondientes.
18. El ticket queda disponible según los permisos definidos.

### Flujos alternativos

**A1. El solicitante no conoce la categoría**

1. Se utiliza una categoría válida inicial como `Sin clasificar`.
2. El ticket puede ser corregido posteriormente.

**A2. Ticket sin solicitante**

1. Se crea el ticket sin solicitantes asociados.
2. El creador original sigue registrado.
3. El ticket puede continuar normalmente su ciclo de vida.

**A3. Creación en nombre de otro usuario**

1. Un usuario autorizado selecciona uno o más solicitantes.
2. WorkDesk registra separadamente al creador y a los solicitantes.

**RF relacionados:** RF-012 a RF-022.

**RN relacionadas:** RN-06 a RN-17.

**Alcance:** MVP.

---

## CU-009 — Consultar y gestionar un ticket

**Actores:** Solicitante, Técnico, Supervisor, Administrador.

**Objetivo:** Permitir consultar y trabajar sobre la información autorizada de un ticket.

### Flujo principal

1. El usuario localiza un ticket.
2. WorkDesk valida que tenga autorización para acceder.
3. El sistema muestra la información disponible.
4. El usuario consulta el estado actual, prioridad, clasificación, solicitantes, técnicos, comentarios, archivos, SLA e historial según sus permisos.
5. El usuario puede ejecutar acciones permitidas por su rol.
6. WorkDesk valida las reglas de negocio antes de cada operación.
7. Los cambios relevantes quedan registrados.

**RF relacionados:** RF-017, RF-022, RF-042 y los correspondientes a cada operación específica.

**RN relacionadas:** RN-01, RN-02, RN-64, RN-79, RN-80, RN-81, RN-82.

**Alcance:** MVP.

---

## CU-010 — Gestionar solicitantes de un ticket

**Actores:** Usuarios autorizados.

**Objetivo:** Asociar múltiples solicitantes a un ticket.

### Flujo principal

1. El usuario abre el ticket.
2. Solicita agregar o eliminar solicitantes.
3. WorkDesk valida los permisos.
4. El sistema actualiza las asociaciones.
5. Los cambios quedan registrados.
6. Las reglas de visibilidad se actualizan según corresponda.

### Flujos alternativos

**A1. Ticket sin solicitantes**

El ticket puede permanecer sin solicitantes asociados.

**A2. Solicitud de eliminación**

La eliminación de un solicitante no elimina la identidad del creador original ni la información histórica.

**RF relacionados:** RF-013, RF-014, RF-015, RF-016.

**RN relacionadas:** RN-08, RN-09, RN-10, RN-11, RN-83.

**Alcance:** MVP.

---

# 9. Casos de uso de prioridad

## CU-011 — Establecer o modificar prioridad

**Actores:** Solicitante, Supervisor, Administrador.

**Objetivo:** Establecer o corregir la prioridad de un ticket.

### Flujo principal

1. El usuario crea o abre un ticket.
2. WorkDesk determina si posee permisos para modificar la prioridad.
3. El usuario selecciona la prioridad.
4. WorkDesk valida que la prioridad esté activa.
5. Se actualiza el ticket.
6. El cambio queda registrado.

### Reglas especiales

* La prioridad es manual.
* Impacto y urgencia no determinan automáticamente la prioridad.
* La prioridad no impone un orden obligatorio de atención.
* La existencia de tickets de mayor prioridad no bloquea la gestión de otros tickets.

**RF relacionados:** RF-023 a RF-027.

**RN relacionadas:** RN-18 a RN-23.

**Alcance:** MVP.

---

# 10. Casos de uso de asignación y carga

## CU-012 — Asignar técnicos a un ticket

**Actores:** Técnico, Supervisor, Administrador.

**Objetivo:** Asociar uno o más técnicos a un ticket.

### Flujo principal

1. El usuario abre el ticket.
2. Selecciona la acción de asignación.
3. WorkDesk valida sus permisos.
4. Puede:

   * Autoasignarse.
   * Agregar técnicos.
   * Retirar técnicos.
   * Reasignar técnicos cuando posea permisos.
5. WorkDesk actualiza las asociaciones.
6. Registra el historial de asignación.
7. Genera las notificaciones correspondientes.

### Reglas especiales

* Un ticket puede tener múltiples técnicos.
* Un técnico puede tener múltiples tickets.
* No existe un límite obligatorio de tickets por técnico.
* La carga no bloquea una asignación.

**RF relacionados:** RF-028 a RF-032.

**RN relacionadas:** RN-24 a RN-26, RN-30.

**Alcance:** MVP.

---

## CU-013 — Consultar carga de trabajo

**Actores:** Técnico, Supervisor, Administrador.

**Objetivo:** Proporcionar información para apoyar la distribución del trabajo.

### Flujo principal

1. El usuario accede a la información de carga.
2. WorkDesk calcula o recupera los indicadores disponibles.
3. Se muestran métricas como:

   * Tickets asignados.
   * Tickets activos.
   * En progreso.
   * En espera.
   * Críticos.
   * Próximos a vencer.
   * Fuera de SLA.
   * Resueltos.
   * Distribución por prioridad.
   * Tickets sin actividad reciente.
4. Supervisor y Administrador pueden consultar información consolidada.

### Reglas especiales

La información es de apoyo y no bloquea asignaciones.

**RF relacionados:** RF-036, RF-037, RF-038.

**RN relacionadas:** RN-24 a RN-29.

**Alcance:** MVP.

---

## CU-014 — Realizar reasignación masiva

**Actores:** Supervisor, Administrador.

**Objetivo:** Redistribuir múltiples tickets de un técnico en una sola operación.

### Flujo principal

1. El usuario selecciona un técnico afectado.
2. WorkDesk identifica los tickets correspondientes.
3. El usuario selecciona los tickets a transferir.
4. Selecciona uno o más técnicos destino.
5. WorkDesk muestra la operación antes de confirmar.
6. El usuario confirma.
7. WorkDesk ejecuta las reasignaciones autorizadas.
8. Se actualizan las asociaciones.
9. Se registra el técnico anterior.
10. Se registra el técnico nuevo.
11. Se registra fecha, hora y usuario ejecutor.
12. Se generan las notificaciones correspondientes.

### Casos de uso

Esta operación puede utilizarse ante:

* Vacaciones.
* Licencias.
* Renuncias.
* Desvinculaciones.
* Cambios de funciones.
* Otras indisponibilidades.

**RF relacionados:** RF-034, RF-035.

**RN relacionadas:** RN-30, RN-83, RN-84.

**Alcance:** MVP.

---

# 11. Escalamiento

## CU-015 — Escalar ticket manualmente

**Actores:** Supervisor, Administrador.

**Objetivo:** Transferir o elevar un ticket manualmente según una necesidad operacional.

### Flujo principal

1. El Supervisor o Administrador abre el ticket.
2. Selecciona la acción de escalamiento.
3. Selecciona el destino:

   * Otro grupo.
   * Otro técnico.
   * Nivel superior de atención.
4. WorkDesk valida los permisos.
5. Se actualizan las asociaciones correspondientes.
6. Se registra la operación.
7. Se notifican los participantes correspondientes.

### Reglas especiales

* El escalamiento es manual.
* No produce automáticamente cambios de prioridad.
* No produce automáticamente una reasignación basada en SLA.
* Debe conservar la trazabilidad.

**RF relacionados:** RF-039, RF-040.

**RN relacionadas:** RN-88, RN-89.

**Alcance:** MVP.

---

# 12. Casos de uso del ciclo de vida

## CU-016 — Cambiar estado de un ticket

**Actores:** Solicitante, Técnico, Supervisor, Administrador, Sistema según la operación.

**Objetivo:** Modificar el estado del ticket respetando las transiciones autorizadas.

### Flujo principal

1. El usuario abre el ticket.
2. WorkDesk identifica el estado actual.
3. Identifica las transiciones disponibles.
4. El usuario selecciona una transición.
5. WorkDesk valida:

   * Rol.
   * Permisos.
   * Estado actual.
   * Transición permitida.
   * Reglas de negocio.
6. Se actualiza el estado.
7. Se registra el cambio en el historial.
8. Se generan las notificaciones correspondientes.

### Estados estructurales

1. Nuevo.
2. Asignado.
3. En progreso.
4. En espera.
5. Resuelto.
6. Cerrado.

La reapertura no constituye un estado independiente.

**RF relacionados:** RF-041, RF-042.

**RN relacionadas:** RN-31 a RN-42.

**Alcance:** MVP.

---

## CU-017 — Poner ticket en espera

**Actores:** Técnico, Supervisor, Administrador según permisos.

**Objetivo:** Indicar que la continuidad del trabajo depende temporalmente de una condición externa.

### Flujo principal

1. El usuario abre el ticket.
2. Selecciona `En espera`.
3. WorkDesk valida que la transición esté permitida.
4. El usuario puede seleccionar o registrar opcionalmente un motivo de espera.
5. El ticket pasa a `En espera` aunque no se haya informado un motivo.
6. Se registra la operación.
7. WorkDesk aplica la política de SLA configurada.
8. Se generan las notificaciones correspondientes.

### Flujos alternativos

**A1. Reactivación**

1. Desaparece la causa de la espera.
2. El usuario solicita reactivar el ticket.
3. WorkDesk lo devuelve a un estado operativo.
4. Se registra la acción.

**RF relacionados:** RF-043, RF-044, RF-045, RF-080.

**RN relacionadas:** RN-35, RN-43 a RN-46.

**Alcance:** MVP.

---

# 13. Casos de uso de resolución y cierre

## CU-018 — Marcar ticket como Resuelto

**Actores:** Técnico, Supervisor, Administrador.

**Objetivo:** Registrar que se aplicó una solución y activar el mecanismo de validación correspondiente.

### Flujo principal

1. El usuario abre el ticket.
2. Selecciona `Resuelto`.
3. WorkDesk valida que el estado actual sea `Nuevo`, `Asignado`, `En progreso` o `En espera`, o que exista una excepción estructuralmente válida autorizada.
4. Se registra al responsable y la fecha.
5. El ticket pasa a `Resuelto`.
6. Se activa el mecanismo de validación.
7. WorkDesk notifica a los solicitantes cuando corresponda.
8. El ticket queda pendiente de confirmación o de cierre automático.

### Reglas especiales

* No es obligatorio un comentario textual para marcar el ticket como `Resuelto`.
* Marcar como `Resuelto` siempre activa el mecanismo de validación.
* La existencia o ausencia de solicitantes no elimina el período configurado para el cierre automático.

**RF relacionados:** RF-046, RF-047, RF-048, RF-052, RF-053.

**RN relacionadas:** RN-47, RN-48, RN-49, RN-50, RN-51.

**Alcance:** MVP.

---

## CU-019 — Cerrar ticket directamente

**Actores:** Técnico, Supervisor, Administrador.

**Objetivo:** Finalizar un ticket sin pasar previamente por `Resuelto`.

### Flujo principal

1. El usuario abre el ticket.
2. Selecciona la acción de cierre directo.
3. WorkDesk valida los permisos.
4. El usuario selecciona o registra el motivo de cierre cuando corresponda.
5. WorkDesk cambia el estado a `Cerrado`.
6. Registra:

   * Usuario.
   * Fecha y hora.
   * Estado anterior.
   * Estado nuevo.
   * Modalidad de cierre.
   * Motivo de cierre cuando corresponda.
7. Se generan las notificaciones correspondientes.

### Reglas especiales

El cierre directo:

* Puede ejecutarse desde `Nuevo`, `Asignado`, `En progreso` o `En espera`.
* No se utiliza desde `Resuelto`, salvo que exista un cierre excepcional diferenciado autorizado para Supervisor o Administrador.
* No activa la validación asociada a `Resuelto`.
* No requiere pasar previamente por `Resuelto`.
* Puede utilizarse, entre otros casos, para mantenciones, tareas internas, tickets sin solicitante y situaciones previamente validadas por otros medios.

**RF relacionados:** RF-049, RF-054.

**RN relacionadas:** RN-48, RN-52.

**Alcance:** MVP.

---

## CU-020 — Confirmar resolución

**Actor:** Solicitante.

**Objetivo:** Confirmar una solución y cerrar el ticket.

### Flujo principal

1. El solicitante recibe una notificación de resolución.
2. Accede al ticket.
3. Revisa la solución.
4. Selecciona la confirmación.
5. WorkDesk valida que el ticket se encuentre en `Resuelto`.
6. El sistema registra:

   * Solicitante que confirmó.
   * Fecha y hora.
   * Estado anterior.
   * Resultado de cierre.
7. El ticket pasa a `Cerrado`.
8. Se generan las notificaciones correspondientes.

### Regla especial

Si existen múltiples solicitantes, **la confirmación positiva de uno de ellos es suficiente para cerrar el ticket completo**.

**RF relacionados:** RF-050.

**RN relacionadas:** RN-49.

**Alcance:** MVP.

---

## CU-021 — Cerrar automáticamente un ticket Resuelto

**Actor:** Sistema.

**Objetivo:** Cerrar automáticamente un ticket cuando finalice el período configurado sin validación humana.

### Flujo principal

1. Un ticket se encuentra en `Resuelto`.
2. WorkDesk inicia el período de espera configurado.
3. El sistema verifica periódicamente si existe una validación.
4. Si un solicitante confirma, el ticket se cierra por validación.
5. Si un solicitante reabre el ticket, no se ejecuta el cierre automático.
6. Si finaliza el período sin validación positiva ni negativa, WorkDesk cierra automáticamente el ticket.
7. El sistema registra la acción como realizada por el propio sistema.
8. Se generan las notificaciones correspondientes.

### Caso sin solicitantes

Cuando el ticket no posee solicitantes:

1. No se requiere validación humana.
2. El sistema debe respetar igualmente el período configurado.
3. No se realiza cierre inmediato por ausencia de solicitantes.
4. Finalizado el período correspondiente, puede ejecutarse el cierre automático.

**RF relacionados:** RF-052, RF-053.

**RN relacionadas:** RN-50, RN-51.

**Alcance:** MVP.

---

## CU-022 — Rechazar resolución y reabrir ticket

**Actor:** Solicitante.

**Objetivo:** Informar que la solución no fue satisfactoria y reactivar el ticket.

### Flujo principal

1. El solicitante accede al ticket `Resuelto`.
2. Selecciona `Reabrir ticket`.
3. WorkDesk valida que la política de reapertura lo permita.
4. El ticket retorna a un estado operativo.
5. Como comportamiento predeterminado pasa a `En progreso`.
6. Se conservan inicialmente los técnicos participantes.
7. El solicitante puede agregar un comentario público explicando la situación.
8. WorkDesk registra la reapertura.
9. Se notifica a los técnicos correspondientes.

**RF relacionados:** RF-051, RF-055 a RF-059.

**RN relacionadas:** RN-38, RN-49, RN-53 a RN-58.

**Alcance:** MVP.

---

## CU-023 — Reabrir ticket cerrado

**Actores:** Solicitante, Técnico, Supervisor, Administrador según permisos.

**Objetivo:** Reactivar un ticket cerrado dentro de la política de reapertura.

### Flujo principal

1. El usuario autorizado consulta el ticket cerrado.
2. Solicita la reapertura.
3. WorkDesk valida permisos y período de reapertura.
4. El sistema determina el estado operativo de destino.
5. Como comportamiento predeterminado, utiliza `En progreso`.
6. Se conservan los técnicos participantes anteriores.
7. Se registra la reapertura.
8. Se notifica a los participantes correspondientes.

**RF relacionados:** RF-055 a RF-060.

**RN relacionadas:** RN-53 a RN-58.

**Alcance:** MVP.

---

# 14. Casos de uso de duplicados

## CU-024 — Gestionar tickets duplicados y relacionados

**Actores:** Usuarios autorizados.

**Objetivo:** Identificar, relacionar y gestionar tickets duplicados.

### Flujo principal

1. WorkDesk detecta o permite identificar una posible coincidencia.
2. El usuario consulta los tickets relacionados.
3. Selecciona la vinculación correspondiente.
4. WorkDesk registra la relación.
5. Cuando un ticket sea duplicado, puede utilizarse un motivo de cierre de duplicidad.
6. El vínculo con el ticket original permanece disponible.
7. Se conserva la trazabilidad.

### Reglas especiales

* La advertencia de duplicidad no obliga necesariamente a cancelar la creación.
* `Duplicado` no es un estado.
* Un ticket duplicado puede cerrarse mediante un motivo de cierre correspondiente.

**RF relacionados:** RF-061 a RF-065.

**RN relacionadas:** RN-59 a RN-61.

**Alcance:** MVP.

---

# 15. Casos de uso de colaboración y comunicación

## CU-025 — Agregar comentario público

**Actores:** Solicitante, Técnico, Supervisor, Administrador según permisos.

**Objetivo:** Incorporar información visible a los participantes autorizados.

### Flujo principal

1. El usuario abre el ticket.
2. Selecciona comentarios públicos.
3. Ingresa la información.
4. WorkDesk valida que tenga permisos.
5. El sistema registra el comentario.
6. El comentario queda asociado cronológicamente al ticket.
7. Se generan las notificaciones correspondientes cuando aplique.

**RF relacionados:** RF-066, RF-067.

**RN relacionadas:** RN-62, RN-64, RN-65.

**Alcance:** MVP.

---

## CU-026 — Registrar nota interna

**Actores:** Técnico, Supervisor, Administrador.

**Objetivo:** Compartir información operacional exclusivamente entre usuarios autorizados de soporte.

### Flujo principal

1. El usuario abre el ticket.
2. Selecciona la opción de nota interna.
3. Ingresa la información.
4. WorkDesk registra la nota.
5. La nota queda asociada al ticket.
6. Los Solicitantes no pueden visualizarla.

**RF relacionados:** RF-069, RF-070, RF-071.

**RN relacionadas:** RN-63, RN-64, RN-65.

**Alcance:** MVP.

---

## CU-027 — Agregar comentario posterior a reapertura

**Actor:** Solicitante.

**Objetivo:** Explicar el motivo de la reapertura y proporcionar información adicional.

### Flujo principal

1. El solicitante reabre el ticket.
2. El sistema devuelve el ticket a un estado operativo.
3. El solicitante agrega un comentario público.
4. WorkDesk registra el comentario.
5. Los técnicos correspondientes reciben una notificación.

**RF relacionados:** RF-057, RF-068.

**RN relacionadas:** RN-53, RN-57, RN-62.

**Alcance:** MVP.

---

# 16. Casos de uso de archivos

## CU-028 — Adjuntar archivo

**Actores:** Usuarios autorizados.

**Objetivo:** Incorporar archivos al contexto de un ticket.

### Flujo principal

1. El usuario abre el ticket.
2. Selecciona adjuntar archivo.
3. Selecciona el archivo.
4. WorkDesk valida:

   * Tipo.
   * Tamaño.
   * Cantidad.
   * Restricciones configuradas.
5. Si la validación es correcta, el archivo queda asociado al ticket.
6. La operación queda registrada cuando corresponda.

### Alternativas

**A1. Archivo no permitido**

1. WorkDesk rechaza el archivo.
2. Informa el motivo.
3. No almacena el archivo.

**RF relacionados:** RF-072 a RF-075.

**RN relacionadas:** RN-66 a RN-69.

**Alcance:** MVP.

---

## CU-029 — Consultar o descargar archivo

**Actores:** Usuarios autorizados.

**Objetivo:** Permitir acceder a archivos asociados a un ticket.

### Flujo principal

1. El usuario abre el ticket.
2. Selecciona un archivo.
3. WorkDesk valida sus permisos.
4. El sistema permite visualizar o descargar el archivo según corresponda.

**RF relacionados:** RF-076.

**RN relacionadas:** RN-64, RN-66, RN-67.

**Alcance:** MVP.

---

# 17. Casos de uso de SLA

## CU-030 — Calcular y consultar SLA

**Actores:** Sistema, usuarios autorizados.

**Objetivo:** Mantener y mostrar el estado temporal del ticket respecto de su SLA.

### Flujo principal

1. WorkDesk identifica la política aplicable.
2. El sistema determina el tiempo objetivo.
3. Considera horarios laborales, días hábiles y feriados configurados.
4. Calcula el tiempo utilizado.
5. Determina el estado del SLA:

   * Dentro de SLA.
   * Próximo a vencer.
   * Fuera de SLA.
6. Presenta la información a los usuarios autorizados.
7. Genera alertas cuando correspondan.

### Reglas especiales

* El SLA pertenece al ticket.
* La cantidad de tickets de un técnico no detiene el SLA.
* El SLA no obliga automáticamente un orden de atención.
* `En espera` puede pausar o mantener activo el SLA según la política configurada.

**RF relacionados:** RF-077 a RF-082.

**RN relacionadas:** RN-70 a RN-75.

**Alcance:** MVP.

---

## CU-031 — Gestionar excepción de SLA

**Actores:** Supervisor, Administrador.

**Objetivo:** Modificar manualmente el comportamiento de SLA en situaciones autorizadas.

### Flujo principal

1. El usuario autorizado consulta el ticket.
2. Selecciona la acción de excepción.
3. WorkDesk valida el nivel de autorización.
4. El Supervisor puede gestionar excepciones operativas.
5. El Administrador puede gestionar políticas y excepciones administrativas.
6. Se aplica el cambio autorizado.
7. La operación queda registrada.

### Regla especial

El Técnico puede consultar el SLA, pero no puede modificarlo, reiniciarlo ni alterarlo administrativamente.

**RF relacionados:** RF-083.

**RN relacionadas:** RN-74.

**Alcance:** MVP.

---

# 18. Casos de uso de notificaciones

## CU-032 — Gestionar notificaciones internas

**Actores:** Sistema, usuarios.

**Objetivo:** Informar eventos relevantes dentro de WorkDesk.

### Flujo principal

1. WorkDesk detecta un evento relevante.
2. El sistema determina los destinatarios.
3. Genera la notificación.
4. La notificación queda disponible en el centro de notificaciones.
5. El usuario puede acceder al ticket relacionado.
6. El usuario puede marcar la notificación como leída.

### Eventos relevantes

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
* Próximo vencimiento de SLA.
* Incumplimiento de SLA.

**RF relacionados:** RF-084 a RF-087.

**RN relacionadas:** RN-76 a RN-78.

**Alcance:** MVP.

---

# 19. Casos de uso de búsqueda y consulta

## CU-033 — Buscar y filtrar tickets

**Actores:** Usuarios autorizados.

**Objetivo:** Localizar tickets de manera eficiente.

### Flujo principal

1. El usuario accede a la búsqueda.
2. Puede buscar mediante:

   * Identificador.
   * Título.
   * Descripción.
   * Categoría.
   * Solicitante.
   * Técnico.
   * Grupo.
3. Puede aplicar filtros por:

   * Estado.
   * Prioridad.
   * Categoría.
   * Solicitante.
   * Técnico.
   * Grupo.
   * Fechas.
   * SLA.
4. Puede combinar múltiples filtros.
5. Puede ordenar los resultados.
6. WorkDesk muestra únicamente información para la que el usuario posee permisos.

**RF relacionados:** RF-088 a RF-092.

**RN relacionadas:** RN-07, RN-79, RN-80, RN-81, RN-82.

**Alcance:** MVP.

---

# 20. Casos de uso de dashboards

## CU-034 — Consultar dashboard

**Actores:** Solicitante, Técnico, Supervisor, Administrador.

**Objetivo:** Presentar información relevante adaptada al rol.

### Flujo principal

1. El usuario inicia sesión.
2. WorkDesk identifica su rol.
3. El sistema carga el dashboard correspondiente.
4. Muestra indicadores autorizados.

### Dashboard de Solicitante

Puede mostrar:

* Tickets propios.
* Tickets que requieren intervención.
* Tickets resueltos pendientes de validación.
* Notificaciones.
* Acceso a creación de tickets.

### Dashboard de Técnico

Puede mostrar:

* Tickets asignados.
* Tickets activos.
* En progreso.
* En espera.
* Próximos a vencer.
* Fuera de SLA.
* Indicadores básicos de productividad.

### Dashboard de Supervisor

Puede mostrar:

* Tickets globales.
* Tickets sin asignar.
* Carga por técnico.
* Tickets por prioridad.
* Fuera de SLA.
* Próximos a vencer.
* Indicadores operativos.

### Dashboard de Administrador

Puede mostrar:

* Información global.
* Indicadores administrativos.

**RF relacionados:** RF-093 a RF-097.

**RN relacionadas:** RN-27, RN-81, RN-82.

**Alcance:** MVP.

---

# 21. Casos de uso de reportes

## CU-035 — Generar y exportar reportes

**Actores:** Usuarios autorizados.

**Objetivo:** Obtener información operacional en formatos utilizables fuera de WorkDesk.

### Flujo principal

1. El usuario accede a reportes.
2. Selecciona el conjunto de información requerido.
3. Aplica filtros cuando corresponda.
4. WorkDesk valida sus permisos.
5. El sistema genera el resultado.
6. El usuario puede exportarlo.
7. El formato puede ser:

   * CSV.
   * XLSX.

Las exportaciones deben respetar los filtros y permisos aplicados.

**RF relacionados:** RF-098 a RF-101.

**Alcance:** MVP.

---

# 22. Casos de uso de Base de Conocimientos

## CU-036 — Gestionar artículo de conocimiento

**Actores:** Usuarios autorizados.

**Objetivo:** Crear, mantener y publicar información reutilizable.

### Flujo principal

1. El usuario autorizado accede a la Base de Conocimientos.
2. Crea o consulta un artículo.
3. Puede modificarlo.
4. Puede publicar el artículo.
5. Puede desactivarlo o eliminarlo según sus permisos.
6. El artículo puede clasificarse como público o privado.

**RF relacionados:** RF-102, RF-103.

**Alcance:** MVP.

---

## CU-037 — Vincular solución con conocimiento

**Actores:** Usuarios autorizados.

**Objetivo:** Relacionar un ticket con conocimiento reutilizable.

### Flujo principal

1. El usuario consulta un ticket.
2. Selecciona un artículo existente o genera uno a partir de la resolución.
3. WorkDesk registra la relación.
4. El conocimiento queda disponible según su configuración de visibilidad.

**RF relacionados:** RF-104, RF-105.

**Alcance:** MVP.

---

# 23. Casos de uso de historial y auditoría

## CU-038 — Consultar historial de ticket

**Actores:** Usuarios autorizados.

**Objetivo:** Reconstruir las acciones relevantes ocurridas durante la vida del ticket.

### Flujo principal

1. El usuario abre un ticket.
2. Accede al historial.
3. WorkDesk presenta los eventos cronológicamente.
4. Se muestran, cuando corresponda:

   * Acción.
   * Usuario.
   * Fecha y hora.
   * Valor anterior.
   * Valor nuevo.
   * Información adicional.

El historial no puede modificarse desde la interfaz.

**RF relacionados:** RF-106, RF-107.

**RN relacionadas:** RN-01, RN-02, RN-92.

**Alcance:** MVP.

---

## CU-039 — Consultar auditoría administrativa

**Actor:** Administrador.

**Objetivo:** Consultar operaciones administrativas relevantes.

### Flujo principal

1. El Administrador accede a la auditoría.
2. Consulta los eventos disponibles.
3. WorkDesk muestra la información según permisos.
4. El sistema conserva la diferenciación entre:

   * Historial operativo de tickets.
   * Auditoría administrativa.

**RF relacionados:** RF-108, RF-109.

**RN relacionadas:** RN-87.

**Alcance:** MVP.

---

# 24. Casos de uso de retención

## CU-040 — Configurar política de retención

**Actor:** Administrador.

**Objetivo:** Definir políticas de conservación, archivo o eliminación de información.

### Flujo principal

1. El Administrador accede a retención.
2. Selecciona el elemento afectado.
3. Define el período de conservación.
4. Define la acción posterior:

   * Mantener.
   * Archivar.
   * Eliminar.
5. Guarda la política.
6. WorkDesk registra el cambio en la auditoría.

### Elementos aplicables

* Tickets cerrados.
* Historial.
* Auditoría.
* Notificaciones.
* Archivos.
* Logs.

### Regla fundamental

Ninguna política de retención puede ejecutarse sin una configuración administrativa explícita que la habilite.

**RF relacionados:** RF-110 a RF-112, RF-123.

**RNF relacionados:** RNF-044 a RNF-047.

**Alcance:** MVP.

---

## CU-041 — Ejecutar política de retención

**Actor:** Sistema.

**Objetivo:** Aplicar una política de retención previamente habilitada.

### Flujo principal

1. WorkDesk identifica información que alcanzó el período configurado.
2. Verifica que exista una política habilitada.
3. Determina la acción configurada.
4. Aplica:

   * Mantener.
   * Archivar.
   * Eliminar.
5. Preserva las relaciones que deban mantenerse.
6. Registra la operación cuando corresponda.

**RF relacionados:** RF-110 a RF-112.

**RNF relacionados:** RNF-044 a RNF-047.

**Alcance:** MVP.

---

# 25. Casos de uso de configuración administrativa

## CU-042 — Administrar configuración del sistema

**Actor:** Administrador.

**Objetivo:** Adaptar WorkDesk a las necesidades de una organización sin modificar el código fuente.

### Flujo principal

1. El Administrador accede a configuración.
2. Selecciona el componente a administrar.
3. Modifica los parámetros permitidos.
4. WorkDesk valida las restricciones estructurales.
5. Guarda el cambio.
6. Registra la modificación en auditoría.

### Componentes principales

* Categorías.
* Prioridades.
* Ubicaciones.
* Grupos.
* Estados y transiciones.
* SLA.
* Cierre y reapertura.
* Notificaciones.
* Archivos.
* Retención.

### Regla especial

La configuración no puede:

* Crear estados estructurales nuevos.
* Eliminar estados estructurales del MVP.
* Convertir la reapertura en estado.
* Romper las restricciones fundamentales del ciclo de vida.
* Comprometer la integridad del sistema.

La personalización de estados deberá limitarse a atributos permitidos y a transiciones estructuralmente válidas.

**RF relacionados:** RF-113 a RF-123.

**RN relacionadas:** RN-04, RN-05, RN-85, RN-86.

**RNF relacionados:** RNF-081, RNF-082, RNF-083.

**Alcance:** MVP.

---

# 26. Casos de uso de reapertura y parámetros

## CU-043 — Configurar políticas de cierre y reapertura

**Actor:** Administrador.

**Objetivo:** Configurar las políticas relacionadas con cierre automático y reapertura.

### Flujo principal

1. El Administrador accede a la configuración.
2. Define el período de espera para validación.
3. Define la activación o desactivación del cierre automático.
4. Configura las políticas de reapertura.
5. Define el período permitido para reabrir.
6. Guarda la configuración.
7. WorkDesk registra los cambios.

### Restricciones

* La ausencia de solicitante no permite eliminar el período de espera del mecanismo de `Resuelto`.
* La reapertura no se convierte en un estado.
* Los destinos configurables de reapertura deben formar parte de las transiciones estructuralmente válidas.

**RF relacionados:** RF-053, RF-056, RF-060, RF-120.

**RN relacionadas:** RN-50, RN-53 a RN-58.

**Alcance:** MVP.

---

# 27. Casos de uso de inicialización

## CU-044 — Inicializar WorkDesk

**Actor:** Administrador / Sistema.

**Objetivo:** Preparar el sistema para su primera utilización.

### Flujo principal

1. WorkDesk detecta que corresponde realizar la inicialización.
2. Se establece la cuenta Administrador inicial.
3. Se configura la información inicial necesaria.
4. El sistema carga valores base.
5. Se habilitan los componentes mínimos.
6. El Administrador puede comenzar a utilizar el sistema.

### Configuración inicial

Puede contemplar:

* Categorías.
* Prioridades.
* Parámetros básicos de SLA.
* Estados.
* Configuraciones necesarias para el funcionamiento inicial.

**RF relacionados:** RF-124 a RF-126.

**Alcance:** MVP.

---

# 28. Casos de uso de respaldo y restauración

## CU-045 — Generar respaldo

**Actor:** Administrador.

**Objetivo:** Crear un respaldo utilizable de la información de WorkDesk.

### Flujo principal

1. El Administrador inicia la operación.
2. WorkDesk genera o integra el mecanismo de respaldo.
3. Se incluye la base de datos PostgreSQL.
4. Se incluyen los archivos adjuntos.
5. El respaldo queda almacenado en una ubicación no expuesta públicamente.
6. La operación se registra.

**RF relacionados:** RF-127.

**RNF relacionados:** RNF-038 a RNF-040, RNF-043.

**Alcance:** MVP.

---

## CU-046 — Restaurar respaldo

**Actor:** Administrador.

**Objetivo:** Recuperar información a partir de un respaldo válido.

### Flujo principal

1. El Administrador selecciona el respaldo.
2. WorkDesk verifica o permite comprobar su integridad.
3. El sistema ejecuta el procedimiento de restauración.
4. Se restaura la información estructurada.
5. Se restauran los archivos adjuntos.
6. Se registra:

   * Usuario.
   * Fecha y hora.
   * Respaldo utilizado.
   * Resultado.
7. El sistema informa el resultado de la operación.

**RF relacionados:** RF-128.

**RNF relacionados:** RNF-040 a RNF-043.

**Alcance:** MVP.

---

# 29. Casos de uso de errores y estado del sistema

## CU-047 — Registrar y gestionar error interno

**Actor:** Sistema.

**Objetivo:** Registrar errores sin comprometer innecesariamente la operación de WorkDesk.

### Flujo principal

1. WorkDesk detecta una excepción o error.
2. El sistema clasifica o registra el evento.
3. Se genera información para diagnóstico.
4. Se evita exponer información técnica sensible al usuario.
5. Cuando sea posible, las funcionalidades no afectadas continúan disponibles.

**RF relacionados:** RF-129.

**RNF relacionados:** RNF-006, RNF-007, RNF-030 a RNF-036.

**Alcance:** MVP.

---

## CU-048 — Consultar estado del sistema

**Actores:** Administrador / Sistema.

**Objetivo:** Conocer el estado básico de WorkDesk y sus componentes principales.

### Flujo principal

1. Se solicita el estado.
2. WorkDesk comprueba la aplicación.
3. Comprueba la conectividad con PostgreSQL.
4. Identifica errores relevantes.
5. Devuelve el resultado correspondiente.

**RF relacionados:** RF-130.

**RNF relacionados:** RNF-037.

**Alcance:** MVP.

---

# 30. Caso transversal de concurrencia

## CU-049 — Editar ticket con control de concurrencia

**Actores:** Usuarios autorizados.

**Objetivo:** Evitar modificaciones simultáneas incompatibles sobre el mismo ticket.

### Flujo principal

1. Un usuario abre un ticket para editarlo.
2. WorkDesk registra temporalmente el recurso como bloqueado para edición.
3. Otro usuario intenta editar el mismo ticket.
4. WorkDesk informa que el recurso está siendo editado.
5. El segundo usuario puede consultar la información, pero no modificarla mientras el bloqueo permanezca activo.
6. WorkDesk informa quién mantiene el bloqueo cuando corresponda.
7. Al liberarse el recurso, otro usuario puede iniciar la edición.

### Regla especial

El bloqueo visual de edición no sustituye los mecanismos backend de integridad y concurrencia.

**RF relacionados:** RF-042 y los requisitos funcionales que impliquen edición de tickets.

**RNF relacionados:** RNF-026, RNF-027, RNF-028, RNF-029.

**Alcance:** MVP.

---

# 31. Reglas transversales aplicables a todos los casos de uso

Todos los casos de uso de WorkDesk deberán respetar las siguientes condiciones generales.

## 31.1. Autorización

Toda operación deberá ejecutarse solamente cuando el actor posea los permisos correspondientes.

La interfaz no constituye por sí sola un mecanismo de seguridad.

---

## 31.2. Trazabilidad

Toda operación relevante deberá conservar la información necesaria para reconstruir posteriormente qué ocurrió, quién lo realizó y cuándo.

---

## 31.3. Integridad histórica

Las modificaciones posteriores no deberán destruir la información histórica necesaria para comprender la evolución del ticket.

---

## 31.4. Flexibilidad operativa

Las prioridades, carga, SLA y demás indicadores operativos deben apoyar la toma de decisiones, pero no bloquear innecesariamente la operación autorizada.

---

## 31.5. Protección de información

La información debe mostrarse únicamente a los usuarios autorizados.

Las notas internas no son visibles para los Solicitantes.

---

## 31.6. Parametrización controlada

La configuración administrativa debe facilitar la adaptación del sistema sin permitir modificaciones que comprometan la integridad estructural del dominio.

---

## 31.7. Estado del ticket

WorkDesk utilizará los seis estados estructurales:

```text
Nuevo
Asignado
En progreso
En espera
Resuelto
Cerrado
```

`Reabierto` constituye una acción y no un estado.

`Cancelado` no constituye un estado del MVP.

`Duplicado` no constituye un estado del MVP.

---

# 32. Flujos principales de alto nivel

## 32.1. Flujo estándar de un ticket

```text
Crear ticket
     │
     ▼
   Nuevo
     │
     ▼
 Asignación
     │
     ▼
  Asignado
     │
     ▼
 En progreso
     │
     ├───────────────┐
     │               │
     ▼               ▼
En espera       Continuar trabajo
     │               │
     └───────┬───────┘
             ▼
       En progreso
             │
             ▼
          Resuelto
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
 Confirmación   Sin respuesta
       │           │
       ▼           ▼
    Cerrado    Cierre automático
       │
       ▼
    Cerrado
```

---

## 32.2. Flujo de cierre directo

```text
Nuevo
  │
  ├──> Cerrado
  │
Asignado
  │
  ├──> Cerrado
  │
En progreso
  │
  ├──> Cerrado
  │
En espera
  │
  └──> Cerrado
```

El cierre directo es independiente de la transición a `Resuelto`.

---

## 32.3. Flujo de reapertura

```text
Resuelto / Cerrado
       │
       │ Reabrir
       ▼
  Estado operativo
       │
       ▼
 En progreso
```

La reapertura conserva inicialmente los técnicos participantes y registra la operación en el historial.

---

# 33. Relación general entre casos de uso y requisitos

| Caso de uso | Requisitos funcionales principales                     |
| ----------- | ------------------------------------------------------ |
| CU-001      | RF-001, RF-003, RF-004                                 |
| CU-002      | RF-002, RF-003                                         |
| CU-003      | RF-003                                                 |
| CU-004      | RF-005, RF-006, RF-007                                 |
| CU-005      | RF-008, RF-009, RF-117                                 |
| CU-006      | RF-020, RF-021, RF-114                                 |
| CU-007      | RF-018, RF-019, RF-116                                 |
| CU-008      | RF-012 a RF-022                                        |
| CU-009      | RF-017, RF-042 y operaciones asociadas                 |
| CU-010      | RF-013 a RF-016                                        |
| CU-011      | RF-023 a RF-027                                        |
| CU-012      | RF-028 a RF-032                                        |
| CU-013      | RF-036 a RF-038                                        |
| CU-014      | RF-034, RF-035                                         |
| CU-015      | RF-039, RF-040                                         |
| CU-016      | RF-041, RF-042                                         |
| CU-017      | RF-043 a RF-045                                        |
| CU-018      | RF-046 a RF-048, RF-052, RF-053                        |
| CU-019      | RF-049, RF-054                                         |
| CU-020      | RF-050                                                 |
| CU-021      | RF-052, RF-053                                         |
| CU-022      | RF-051, RF-055 a RF-059                                |
| CU-023      | RF-055 a RF-060                                        |
| CU-024      | RF-061 a RF-065                                        |
| CU-025      | RF-066, RF-067                                         |
| CU-026      | RF-069 a RF-071                                        |
| CU-027      | RF-057, RF-068                                         |
| CU-028      | RF-072 a RF-075                                        |
| CU-029      | RF-076                                                 |
| CU-030      | RF-077 a RF-082                                        |
| CU-031      | RF-083                                                 |
| CU-032      | RF-084 a RF-087                                        |
| CU-033      | RF-088 a RF-092                                        |
| CU-034      | RF-093 a RF-097                                        |
| CU-035      | RF-098 a RF-101                                        |
| CU-036      | RF-102, RF-103                                         |
| CU-037      | RF-104, RF-105                                         |
| CU-038      | RF-106, RF-107                                         |
| CU-039      | RF-108, RF-109                                         |
| CU-040      | RF-110 a RF-112, RF-123                                |
| CU-041      | RF-110 a RF-112                                        |
| CU-042      | RF-113 a RF-123                                        |
| CU-043      | RF-053, RF-056, RF-060, RF-120                         |
| CU-044      | RF-124 a RF-126                                        |
| CU-045      | RF-127                                                 |
| CU-046      | RF-128                                                 |
| CU-047      | RF-129                                                 |
| CU-048      | RF-130                                                 |
| CU-049      | Requisitos funcionales aplicables a edición de tickets |

---

# 34. Trazabilidad con reglas de negocio

Los casos de uso deberán considerar las reglas de negocio definidas en `06_reglas_de_negocio.md`, especialmente:

| Área                    | Reglas relevantes |
| ----------------------- | ----------------- |
| Identificación          | RN-06 a RN-07     |
| Creación                | RN-08 a RN-12     |
| Clasificación           | RN-13 a RN-17     |
| Prioridades             | RN-18 a RN-23     |
| Carga                   | RN-24 a RN-30     |
| Estados                 | RN-31 a RN-42     |
| En espera               | RN-43 a RN-46     |
| Resolución y cierre     | RN-47 a RN-52     |
| Reapertura              | RN-53 a RN-58     |
| Duplicados              | RN-59 a RN-61     |
| Comentarios             | RN-62 a RN-65     |
| Archivos                | RN-66 a RN-69     |
| SLA                     | RN-70 a RN-75     |
| Notificaciones          | RN-76 a RN-78     |
| Visibilidad             | RN-79 a RN-82     |
| Usuarios desactivados   | RN-83 a RN-84     |
| Configuración histórica | RN-85 a RN-87     |
| Operación del MVP       | RN-88 a RN-90     |
| Evolución futura        | RN-91             |
| Principio fundamental   | RN-92             |

---

# 35. Trazabilidad con requisitos no funcionales

Los casos de uso deberán ejecutarse considerando los requisitos no funcionales definidos en `05_requisitos_no_funcionales.md`.

Especialmente:

* Seguridad y RBAC.
* Autorización en backend.
* Mínimo privilegio.
* Gestión segura de sesiones.
* Protección de información.
* Auditoría.
* Integridad histórica.
* Concurrencia.
* Bloqueo de edición.
* Manejo controlado de errores.
* Respaldo y restauración.
* Retención.
* Accesibilidad.
* Usabilidad.
* Parametrización.
* Ejecución local.
* Pruebas automatizadas.
* Capacidad de evolución.

Los requisitos no funcionales condicionan la ejecución de los casos de uso, pero no sustituyen sus reglas funcionales.

---

# 36. Criterios generales de aceptación de los casos de uso

Un caso de uso se considerará correctamente implementado cuando:

1. El actor pueda iniciar la interacción cuando posea autorización.
2. Las precondiciones y permisos sean validados.
3. El flujo principal produzca el resultado definido.
4. Los flujos alternativos sean tratados correctamente.
5. Las reglas de negocio aplicables sean respetadas.
6. Las operaciones relevantes queden registradas.
7. La información permanezca consistente.
8. Las restricciones de visibilidad sean respetadas.
9. Las notificaciones correspondientes se generen cuando aplique.
10. Las condiciones de cierre o finalización se respeten.
11. Las operaciones protegidas sean validadas en backend.
12. Los errores sean tratados de manera controlada.
13. El comportamiento pueda ser validado mediante pruebas.

---

# 37. Trazabilidad hacia documentos posteriores

Los casos de uso servirán como entrada para los siguientes documentos:

```text
04_requisitos_funcionales.md
             │
             ▼
06_reglas_de_negocio.md
             │
             ▼
07_casos_de_uso.md
             │
      ┌──────┼────────┐
      ▼      ▼        ▼
08_flujo   09_modelo  10_arquitectura
tickets    de datos
      │       │        │
      └───────┼────────┘
              ▼
    11_diseño_de_pantallas
              │
              ▼
           Pruebas
```

Cada caso de uso deberá poder relacionarse posteriormente con:

* Uno o más requisitos funcionales.
* Una o más reglas de negocio.
* Entidades del modelo de datos.
* Componentes de arquitectura.
* Pantallas.
* Pruebas funcionales.

---

# 38. Consideraciones de alcance

Los casos de uso de este documento describen el comportamiento del **MVP definido actualmente**.

No forman parte de estos casos de uso las funcionalidades avanzadas excluidas del MVP, entre ellas:

* Asignación automática avanzada.
* Reasignación automática basada en carga.
* Escalamiento automático complejo.
* Workflows dinámicos creados por usuarios.
* Inteligencia artificial.
* Machine Learning.
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

Estas capacidades podrán desarrollarse posteriormente sin formar parte de los flujos obligatorios del MVP.

---

# 39. Principio general de los casos de uso

Los casos de uso de WorkDesk deberán mantener el siguiente principio:

> **El sistema debe proporcionar herramientas claras para que los usuarios autorizados puedan gestionar tickets de manera flexible, colaborativa y trazable, manteniendo siempre la integridad de la información y respetando las reglas de negocio.**

Los casos de uso no deberán introducir restricciones que no estén respaldadas por los requisitos funcionales, requisitos no funcionales o reglas de negocio definidos previamente.

---

## Fin del documento
