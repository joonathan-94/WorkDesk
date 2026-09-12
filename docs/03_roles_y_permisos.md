# 03 — Roles y Permisos

> **Proyecto:** WorkDesk
> **Documento:** Roles y Permisos
> **Versión:** 1.0
> **Estado:** Definición inicial
> **Última actualización:** 2026-08-26

---

## 1. Propósito

Este documento define los roles de usuario y el modelo general de permisos de WorkDesk para su etapa inicial.

Su objetivo es establecer de manera clara:

* Los roles contemplados en el MVP.
* La responsabilidad general asociada a cada rol.
* El nivel de acceso de cada tipo de usuario.
* Las principales acciones que cada rol puede realizar.
* Las restricciones aplicables a cada rol.
* Los principios que deberán orientar la gestión de autorizaciones.

Este documento establece **quién puede realizar determinadas acciones**, pero no define todavía el comportamiento funcional detallado de cada funcionalidad ni su implementación técnica.

La especificación detallada del comportamiento de las funcionalidades será desarrollada posteriormente en los documentos de requisitos funcionales y requisitos no funcionales.

---

## 2. Alcance

El modelo de roles y permisos definido en este documento corresponde al MVP de WorkDesk.

El MVP contempla inicialmente cuatro roles:

1. **Solicitante**
2. **Técnico**
3. **Supervisor**
4. **Administrador**

La definición de estos cuatro roles busca cubrir los principales perfiles involucrados en la gestión de tickets dentro del escenario inicial de soporte TI, evitando introducir una cantidad innecesaria de roles o niveles de autorización.

La estructura deberá permitir evolucionar posteriormente hacia modelos de autorización más avanzados si las necesidades del producto lo justifican.

---

## 3. Principios de autorización

El modelo de permisos de WorkDesk se regirá por los siguientes principios.

### 3.1. Mínimo privilegio

Cada usuario deberá disponer únicamente de los permisos necesarios para cumplir las responsabilidades asociadas a su rol.

Un usuario no deberá obtener permisos administrativos simplemente por necesitar acceso a determinada información.

### 3.2. Separación de responsabilidades

Las capacidades de consulta, gestión operativa y administración del sistema deberán diferenciarse de acuerdo con las responsabilidades de cada rol.

Esto permitirá evitar que un usuario tenga acceso innecesario a funciones que no forman parte de sus responsabilidades.

### 3.3. Permisos asociados al rol

Durante el MVP, los permisos estarán determinados principalmente por el rol asignado al usuario.

No se contempla inicialmente un sistema excesivamente granular de permisos personalizados por usuario.

Esto mantiene el modelo comprensible y evita complejidad innecesaria durante la primera etapa del proyecto.

### 3.4. La interfaz no constituye la seguridad

La ocultación o deshabilitación de botones y elementos de interfaz no deberá considerarse suficiente para proteger una operación.

Las restricciones de permisos deberán ser respetadas por el sistema independientemente de cómo se acceda a una funcionalidad.

La definición técnica de estos mecanismos será abordada posteriormente.

### 3.5. Trazabilidad

Las acciones relevantes realizadas sobre información gestionada por WorkDesk deberán poder asociarse al usuario que las ejecutó.

La autorización y la trazabilidad deberán considerarse conceptos complementarios: permitir una acción no elimina la necesidad de conocer quién la realizó.

---

# 4. Roles del sistema

## 4.1. Solicitante

### Descripción

El Solicitante es el usuario que utiliza WorkDesk principalmente para registrar solicitudes, incidencias o requerimientos y realizar seguimiento de ellos.

Representa al usuario que necesita asistencia o requiere que un trabajo sea gestionado por el equipo correspondiente.

### Responsabilidades principales

* Registrar tickets.
* Entregar la información necesaria para solicitar asistencia.
* Consultar el estado de sus tickets.
* Realizar seguimiento de las solicitudes realizadas.
* Participar en la comunicación relacionada con sus tickets.
* Revisar las soluciones proporcionadas.
* Aceptar una solución cuando corresponda.
* Solicitar la reapertura de un ticket cuando el problema persista.

### Alcance general

El Solicitante tendrá acceso principalmente a la información relacionada con sus propios tickets.

No deberá tener acceso a información interna de otros usuarios ni a información reservada para los equipos responsables de la gestión.

### Restricciones principales

El Solicitante no podrá:

* Administrar usuarios.
* Administrar roles.
* Modificar configuraciones generales del sistema.
* Asignar técnicos.
* Reasignar tickets.
* Modificar la prioridad de un ticket.
* Acceder a notas internas.
* Administrar otros tickets que no le correspondan.

Los permisos específicos podrán ampliarse o restringirse posteriormente mediante los requisitos funcionales, siempre respetando el principio de mínimo privilegio.

---

## 4.2. Técnico

### Descripción

El Técnico es el usuario responsable de participar directamente en la gestión, análisis y resolución de tickets.

Representa al personal encargado de proporcionar soporte y ejecutar las actividades necesarias para resolver las solicitudes recibidas.

Un ticket podrá contar con la participación de **uno o varios técnicos**, debido a que determinadas incidencias o solicitudes pueden requerir colaboración entre diferentes personas o especialidades.

### Responsabilidades principales

* Revisar tickets que tenga disponibles para su gestión.
* Participar en la resolución de tickets.
* Asignarse tickets cuando corresponda.
* Participar en tickets asignados a otros técnicos.
* Actualizar información permitida de los tickets.
* Modificar la prioridad cuando corresponda.
* Cambiar el estado de los tickets según sus permisos.
* Registrar comentarios públicos.
* Registrar notas internas.
* Documentar acciones y observaciones relacionadas con la resolución.
* Marcar tickets como resueltos cuando corresponda.

### Alcance general

El Técnico tendrá acceso a los tickets necesarios para desarrollar sus funciones operativas.

La participación de múltiples técnicos en un mismo ticket estará permitida.

La asignación de un ticket a varios técnicos no implica necesariamente que todos posean responsabilidades idénticas sobre su resolución, pero sí representa su participación en la gestión del trabajo.

### Restricciones principales

El Técnico no podrá:

* Administrar usuarios.
* Administrar roles.
* Modificar configuraciones generales reservadas al Administrador.
* Gestionar permisos de otros usuarios.
* Acceder a información administrativa que no corresponda a sus funciones.

---

## 4.3. Supervisor

### Descripción

El Supervisor es el usuario responsable de supervisar la gestión operativa de los tickets y coordinar el trabajo realizado por los técnicos.

Representa un nivel de responsabilidad superior al Técnico dentro de la operación del sistema, especialmente en materia de asignación, supervisión y control de la gestión.

### Responsabilidades principales

* Supervisar tickets.
* Consultar información global necesaria para la operación.
* Asignar tickets a uno o varios técnicos.
* Reasignar tickets.
* Modificar prioridades.
* Supervisar estados y evolución de tickets.
* Participar en la gestión de tickets.
* Registrar comentarios públicos.
* Registrar notas internas.
* Intervenir cuando una situación requiera coordinación o supervisión.
* Revisar información necesaria para controlar la operación.

### Alcance general

El Supervisor tendrá una visión amplia sobre los tickets gestionados por WorkDesk y podrá intervenir sobre ellos de acuerdo con sus responsabilidades.

Su nivel de acceso será superior al de un Técnico, pero no incluirá las capacidades administrativas reservadas al Administrador.

### Restricciones principales

El Supervisor no podrá:

* Gestionar roles del sistema.
* Administrar globalmente los usuarios.
* Modificar configuraciones administrativas reservadas al Administrador.
* Administrar los permisos estructurales del sistema.

---

## 4.4. Administrador

### Descripción

El Administrador es el rol con mayor nivel de privilegio dentro de WorkDesk.

Es responsable de la administración general de la plataforma y posee las capacidades necesarias para gestionar usuarios, configuración y funcionamiento administrativo del sistema.

### Responsabilidades principales

* Administrar usuarios.
* Crear usuarios.
* Editar usuarios.
* Activar o desactivar usuarios.
* Asignar roles.
* Gestionar información administrativa.
* Gestionar configuraciones disponibles para el Administrador.
* Gestionar tickets cuando sea necesario.
* Asignar y reasignar tickets.
* Modificar prioridades.
* Participar en la gestión de tickets.
* Consultar información global del sistema.
* Acceder a información de auditoría disponible para su rol.

### Alcance general

El Administrador tendrá acceso global a WorkDesk y podrá realizar las operaciones necesarias para administrar la plataforma.

El hecho de que el Administrador posea privilegios superiores no elimina la necesidad de registrar sus acciones relevantes para mantener la trazabilidad del sistema.

### Principio de responsabilidad administrativa

Las acciones administrativas relevantes deberán poder asociarse al Administrador que las ejecutó.

El privilegio administrativo no deberá interpretarse como ausencia de controles o trazabilidad.

---

# 5. Matriz general de permisos

La siguiente matriz establece el modelo inicial de autorización para las principales acciones contempladas en WorkDesk.

| Acción                                    |   Solicitante  | Técnico | Supervisor | Administrador |
| ----------------------------------------- | :------------: | :-----: | :--------: | :-----------: |
| Iniciar sesión                            |        ✅       |    ✅    |      ✅     |       ✅       |
| Crear ticket                              |        ✅       |    ✅    |      ✅     |       ✅       |
| Ver tickets propios                       |        ✅       |    ✅    |      ✅     |       ✅       |
| Ver otros tickets                         |        ❌       |    ✅    |      ✅     |       ✅       |
| Participar en ticket                      |        ❌       |    ✅    |      ✅     |       ✅       |
| Asignarse un ticket                       |        ❌       |    ✅    |      ✅     |       ✅       |
| Asignar técnicos                          |        ❌       |    ❌    |      ✅     |       ✅       |
| Reasignar técnicos                        |        ❌       |    ❌    |      ✅     |       ✅       |
| Asignar múltiples técnicos                |        ❌       |    ❌    |      ✅     |       ✅       |
| Cambiar prioridad                         |        ❌       |    ✅    |      ✅     |       ✅       |
| Cambiar estado                            | ⚠️ Según flujo |    ✅    |      ✅     |       ✅       |
| Agregar comentario público                |        ✅       |    ✅    |      ✅     |       ✅       |
| Agregar nota interna                      |        ❌       |    ✅    |      ✅     |       ✅       |
| Consultar notas internas                  |        ❌       |    ✅    |      ✅     |       ✅       |
| Resolver ticket                           |        ❌       |    ✅    |      ✅     |       ✅       |
| Solicitar/cambiar cierre como solicitante |        ✅       |    —    |      —     |       —       |
| Reabrir ticket propio                     |        ✅       |    —    |      —     |       —       |
| Gestionar usuarios                        |        ❌       |    ❌    |      ❌     |       ✅       |
| Asignar roles                             |        ❌       |    ❌    |      ❌     |       ✅       |
| Activar/desactivar usuarios               |        ❌       |    ❌    |      ❌     |       ✅       |
| Gestionar configuración administrativa    |        ❌       |    ❌    |      ❌     |       ✅       |
| Consultar auditoría                       |        ❌       |    ❌    |      ❌     |       ✅       |

> **Nota:** La matriz representa la autorización general. Las condiciones exactas bajo las cuales una acción puede ejecutarse serán especificadas posteriormente en los requisitos funcionales.

---

# 6. Visibilidad de la información

Los permisos de WorkDesk no deberán limitarse únicamente a determinar qué acciones puede ejecutar un usuario.

También deberán considerar **qué información puede visualizar**.

### 6.1. Solicitante

El Solicitante deberá tener acceso principalmente a:

* Sus propios tickets.
* El estado de sus tickets.
* Información pública asociada a sus tickets.
* Comentarios públicos.
* Información necesaria para realizar seguimiento.

No deberá visualizar notas internas ni información reservada para el personal de gestión.

### 6.2. Técnico

El Técnico deberá poder acceder a la información necesaria para participar en los tickets que gestione.

Esto incluye:

* Información del ticket.
* Historial necesario para comprender su evolución.
* Comentarios públicos.
* Notas internas.
* Información relacionada con otros técnicos participantes cuando corresponda.

### 6.3. Supervisor

El Supervisor deberá disponer de una visión suficientemente amplia para supervisar la operación y coordinar la gestión de tickets.

### 6.4. Administrador

El Administrador tendrá acceso global a la información necesaria para cumplir sus responsabilidades administrativas y operativas.

---

# 7. Comentarios públicos y notas internas

WorkDesk diferenciará dos tipos principales de comunicación asociada a los tickets.

## 7.1. Comentario público

El comentario público corresponde a información que puede ser compartida con el Solicitante y los usuarios autorizados que participen en la gestión del ticket.

Los comentarios públicos deberán utilizarse para:

* Comunicar avances.
* Solicitar información.
* Informar acciones realizadas.
* Comunicar soluciones.
* Mantener una comunicación transparente con el Solicitante.

Los Solicitantes podrán utilizar comentarios públicos en sus propios tickets.

## 7.2. Nota interna

La nota interna corresponde a información destinada exclusivamente al personal autorizado que participa en la gestión interna del ticket.

Podrá utilizarse para:

* Registrar observaciones técnicas.
* Documentar diagnósticos.
* Compartir información operativa interna.
* Registrar antecedentes que no deban exponerse al Solicitante.
* Facilitar la colaboración entre técnicos y supervisores.

Las notas internas no deberán ser visibles para los Solicitantes.

---

# 8. Asignación de múltiples técnicos

WorkDesk permitirá que un mismo ticket pueda estar asociado a más de un Técnico.

Esta decisión responde a la posibilidad de que determinados problemas requieran la participación coordinada de diferentes personas, conocimientos técnicos o áreas de especialización.

Por lo tanto:

* Un ticket no estará limitado necesariamente a un único Técnico.
* Un Supervisor podrá asignar múltiples técnicos.
* Un Administrador podrá gestionar estas asignaciones.
* Los técnicos asignados podrán participar en la gestión del ticket.
* La participación de múltiples técnicos deberá mantener la trazabilidad individual de las acciones realizadas.

La asignación múltiple representa **participación en el trabajo**, y no elimina la necesidad de identificar individualmente quién realizó cada acción.

Las reglas detalladas sobre asignación, incorporación, eliminación y gestión de participantes serán definidas posteriormente en los requisitos funcionales.

---

# 9. Gestión de prioridad

La modificación de la prioridad de un ticket estará restringida a los siguientes roles:

* Técnico.
* Supervisor.
* Administrador.

El Solicitante no podrá modificar directamente la prioridad de un ticket después de su creación.

Esta restricción busca evitar modificaciones arbitrarias de la prioridad y mantener un criterio de gestión controlado.

Las reglas detalladas relacionadas con niveles de prioridad, impacto, urgencia y cálculo de prioridad serán definidas posteriormente.

---

# 10. Gestión del ciclo de vida

Los roles tendrán diferentes responsabilidades respecto al ciclo de vida de los tickets.

El modelo conceptual adoptado para el MVP mantiene una separación entre:

```text
Ticket
  ↓
Gestión
  ↓
Resolución
  ↓
Cierre
  ↓
Posible reapertura
```

El Técnico podrá participar en la gestión y resolución.

El Supervisor podrá intervenir y supervisar el proceso.

El Administrador podrá intervenir cuando sea necesario.

El Solicitante tendrá participación especialmente en la validación de la solución y en la eventual reapertura de un ticket propio.

La definición exacta de estados, transiciones y condiciones será desarrollada posteriormente en los requisitos funcionales.

---

# 11. Gestión de usuarios

La administración de usuarios estará reservada al Administrador.

El Administrador podrá gestionar, como mínimo:

* Creación de usuarios.
* Edición de usuarios.
* Activación de usuarios.
* Desactivación de usuarios.
* Asignación de roles.

Un usuario desactivado no deberá poder utilizar WorkDesk como usuario activo.

La gestión detallada de usuarios, autenticación, recuperación de credenciales y sesiones será especificada posteriormente.

---

# 12. Administración y privilegios elevados

El Administrador tendrá privilegios superiores a los demás roles.

Estos privilegios permitirán administrar elementos estructurales del sistema que no deberán estar disponibles para usuarios operativos.

Sin embargo, el privilegio administrativo no deberá utilizarse como justificación para eliminar controles de trazabilidad.

Las acciones administrativas relevantes deberán poder ser identificadas posteriormente mediante mecanismos de auditoría.

---

# 13. Auditoría y trazabilidad

La trazabilidad constituye un principio fundamental de WorkDesk.

Las acciones relevantes relacionadas con la gestión de tickets deberán poder asociarse a un usuario y a un momento determinado.

Como mínimo, el sistema deberá permitir identificar:

* Quién realizó una acción.
* Cuándo fue realizada.
* Sobre qué elemento se realizó.
* Qué tipo de acción se ejecutó.

Este documento no define todavía el mecanismo técnico mediante el cual se almacenará dicha información.

La especificación detallada del historial y auditoría será abordada posteriormente.

---

# 14. Usuarios inactivos

Los usuarios que se encuentren en estado inactivo no deberán disponer de acceso operativo al sistema.

La condición de usuario activo o inactivo deberá ser independiente del rol que posea.

Por ejemplo:

```text
Administrador + Inactivo
        ↓
No puede iniciar sesión

Técnico + Inactivo
        ↓
No puede iniciar sesión
```

La administración de este estado estará reservada al Administrador.

---

# 15. Modelo de autorización del MVP

Para el MVP, WorkDesk utilizará conceptualmente un modelo de autorización basado en roles.

```text
Usuario
   │
   └── Rol
        │
        ├── Permisos de consulta
        ├── Permisos de creación
        ├── Permisos de modificación
        ├── Permisos de gestión
        └── Permisos administrativos
```

Los cuatro roles iniciales serán:

```text
Solicitante
    ↓
Técnico
    ↓
Supervisor
    ↓
Administrador
```

Esta representación indica un aumento general del nivel de responsabilidad, pero **no significa necesariamente que cada rol superior herede automáticamente todos los permisos del rol inferior**.

Los permisos deberán definirse explícitamente para evitar ambigüedades.

---

# 16. Roles fuera del alcance del MVP

No se incorporarán inicialmente roles adicionales como:

* Auditor.
* Gerente.
* Jefe de TI.
* Responsable de área.
* Cliente externo.
* Administrador de seguridad.
* Otros perfiles especializados.

Estos roles podrán evaluarse posteriormente si aparecen necesidades reales que justifiquen su incorporación.

La incorporación de nuevos roles deberá realizarse evitando aumentar innecesariamente la complejidad del modelo de autorización.

---

# 17. Evolución futura

El modelo inicial deberá permitir que WorkDesk evolucione posteriormente hacia escenarios más complejos sin obligar a rediseñar completamente el concepto de autorización.

Entre las posibilidades futuras podrían encontrarse:

* Nuevos roles.
* Permisos más específicos.
* Ámbitos de acceso por organización.
* Equipos o áreas.
* Diferentes niveles de administración.
* Permisos asociados a módulos.
* Modelos multiempresa o multi-tenant.
* Reglas de autorización más avanzadas.

Estas capacidades no forman parte del MVP.

La evolución deberá realizarse únicamente cuando exista una necesidad real que justifique la complejidad adicional.

Esto es consistente con la visión de WorkDesk como una plataforma que podrá evolucionar posteriormente hacia diferentes contextos organizacionales y eventualmente soportar escenarios multiempresa.

---

# 18. Fuera del alcance de este documento

Este documento **no define**:

* Arquitectura de seguridad.
* Implementación de autenticación.
* Implementación de sesiones.
* Estructura de tablas de usuarios y roles.
* Endpoints de la API.
* Decoradores o middleware de autorización.
* Hashing de contraseñas.
* Estados detallados de los tickets.
* Reglas completas del ciclo de vida.
* Cálculo de prioridades.
* Reglas detalladas de SLA.
* Requisitos de rendimiento.
* Requisitos de disponibilidad.
* Requisitos de infraestructura.
* Diseño de la interfaz.

Estos aspectos serán tratados en documentos posteriores cuando corresponda.

---

# 19. Decisiones adoptadas

Para el MVP de WorkDesk se establecen las siguientes decisiones:

| #  | Decisión                                                                                      |
| -- | --------------------------------------------------------------------------------------------- |
| 1  | El MVP tendrá cuatro roles principales: Solicitante, Técnico, Supervisor y Administrador.     |
| 2  | No se incorporarán grupos o colas de técnicos en el MVP.                                      |
| 3  | Un ticket podrá tener múltiples técnicos asignados.                                           |
| 4  | Los técnicos podrán participar en tickets asignados a otros técnicos.                         |
| 5  | Técnicos, Supervisores y Administradores podrán modificar la prioridad.                       |
| 6  | Se mantendrá el modelo conceptual de resolución, cierre y reapertura.                         |
| 7  | El Administrador será el rol con mayor nivel de privilegio.                                   |
| 8  | Existirán comentarios públicos y notas internas.                                              |
| 9  | Las notas internas no serán visibles para los Solicitantes.                                   |
| 10 | La gestión de usuarios estará reservada al Administrador.                                     |
| 11 | La asignación múltiple deberá mantener trazabilidad individual de las acciones realizadas.    |
| 12 | El modelo inicial de autorización estará basado en roles.                                     |
| 13 | No se implementará inicialmente un sistema excesivamente granular de permisos personalizados. |
| 14 | Las acciones relevantes deberán mantener trazabilidad.                                        |
| 15 | Un usuario inactivo no tendrá acceso operativo al sistema.                                    |

---

# 20. Relación con la documentación posterior

Este documento constituye una base para la definición posterior de requisitos, pero no reemplaza dichos documentos.

La relación esperada será:

```text
01 — Documentación inicial
        │
        ├── Visión
        ├── Objetivos
        │
        ▼
03 — Roles y Permisos
        │
        │ ¿Quién puede hacer qué?
        │
        ▼
04 — Requisitos Funcionales
        │
        │ ¿Qué debe hacer el sistema?
        │
        ▼
05 — Requisitos No Funcionales
        │
        │ ¿Cómo debe comportarse?
        │
        ▼
Diseño / Arquitectura
        │
        ▼
Implementación
```

Los requisitos funcionales deberán utilizar las definiciones establecidas en este documento cuando una funcionalidad dependa del rol del usuario.

De esta manera se evita duplicar definiciones y se mantiene una separación clara entre **roles y permisos**, **comportamiento funcional** y **características de calidad del sistema**.

---

## 21. Estado del documento

Este documento representa la definición inicial de roles y permisos para el MVP de WorkDesk.

Las modificaciones posteriores deberán registrarse cuando impliquen cambios relevantes en el modelo de autorización.

Las nuevas necesidades deberán evaluarse considerando:

1. El valor que aportan al producto.
2. La necesidad real que buscan resolver.
3. El impacto sobre la simplicidad del modelo.
4. La coherencia con la visión de WorkDesk.
5. La posibilidad de evolución futura.

El objetivo no es construir el sistema de permisos más complejo posible, sino establecer un modelo **claro, seguro, comprensible y suficiente para el MVP**, que pueda evolucionar junto con WorkDesk.
