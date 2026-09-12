# Documento de Objetivos — WorkDesk

> **Estado:** En elaboración
> **Versión:** 0.1.0
> **Última actualización:** 26 de agosto de 2026

---

## 1. Propósito del documento

El presente documento establece los objetivos que orientarán la definición, desarrollo y evolución de WorkDesk.

Su propósito es transformar la visión general del producto en objetivos concretos que permitan mantener una dirección clara durante las distintas etapas del proyecto, establecer prioridades, delimitar el alcance de cada versión y evaluar posteriormente el grado de cumplimiento alcanzado.

Los objetivos definidos en este documento representan resultados y capacidades que WorkDesk busca alcanzar. No constituyen una especificación técnica ni definen por sí mismos la implementación concreta del sistema.

Los requisitos funcionales, requisitos no funcionales, reglas de negocio, arquitectura, modelo de datos y decisiones técnicas serán definidos posteriormente en los documentos correspondientes.

---

## 2. Relación con el Documento de Visión

WorkDesk se concibe como una plataforma orientada a la gestión centralizada, estructurada y trazable del trabajo, cuyo punto de partida será un núcleo avanzado de gestión de tickets.

La primera etapa estará enfocada en consolidar dicho núcleo antes de ampliar progresivamente el producto hacia capacidades relacionadas con tareas, proyectos, coordinación del trabajo y otros escenarios organizacionales.

Los objetivos establecidos en este documento deben interpretarse como una evolución y concreción de la dirección definida en `vision.md`, manteniendo sus principios de desarrollo progresivo, control del alcance, simplicidad, mantenibilidad, escalabilidad y orientación a necesidades reales.

---

## 3. Objetivo general

### 3.1. Objetivo

Desarrollar WorkDesk como una plataforma web para centralizar, organizar, asignar, gestionar y realizar seguimiento de incidencias, solicitudes y requerimientos, proporcionando trazabilidad sobre su ciclo de vida y facilitando la coordinación entre los usuarios y equipos responsables.

El sistema tendrá como núcleo inicial la gestión de tickets de soporte TI y deberá establecer una base funcional y técnica que permita evolucionar progresivamente hacia una plataforma más amplia para la gestión del trabajo.

### 3.2. Resultado esperado

WorkDesk deberá transformar un escenario caracterizado por solicitudes dispersas, falta de seguimiento, ausencia de responsables claros y pérdida de conocimiento, en un entorno centralizado donde el trabajo pueda ser registrado, organizado, atendido, supervisado y consultado de manera estructurada.

El objetivo no consiste únicamente en registrar tickets, sino en proporcionar un sistema que permita comprender qué trabajo existe, quién es responsable, cuál es su estado, qué acciones se han realizado y qué conocimiento puede reutilizarse.

---

## 4. Objetivos estratégicos

### 4.1. Centralizar la gestión del trabajo

Establecer un punto centralizado para registrar y gestionar las incidencias, solicitudes y requerimientos que sean atendidos por los equipos responsables.

WorkDesk deberá reducir la dependencia de canales informales o dispersos como correos electrónicos, mensajería instantánea, llamadas o conversaciones personales para el seguimiento del trabajo.

---

### 4.2. Gestionar integralmente el ciclo de vida de las solicitudes

Permitir que una solicitud pueda ser administrada de forma estructurada desde su creación hasta su resolución y cierre.

El ciclo de vida deberá permitir representar de manera coherente las diferentes etapas por las que puede atravesar una solicitud y proporcionar visibilidad sobre su situación actual.

---

### 4.3. Garantizar trazabilidad sobre el trabajo

Mantener información suficiente para reconstruir la evolución de cada elemento gestionado.

Como objetivo transversal, WorkDesk deberá permitir conocer, al menos, quién creó una solicitud, quién participó en su gestión, qué cambios se realizaron, cuándo ocurrieron y cómo evolucionó hasta su resolución o cierre.

La trazabilidad deberá constituir una característica fundamental del producto y no una capacidad secundaria.

---

### 4.4. Establecer responsabilidades claras

Facilitar la identificación de las personas, equipos y áreas relacionadas con cada elemento de trabajo.

WorkDesk deberá reducir situaciones en las que una solicitud permanezca sin responsable definido, exista incertidumbre sobre quién debe atenderla o diferentes participantes asuman que otra persona se hará cargo.

La definición detallada de roles, permisos y reglas de asignación será desarrollada posteriormente durante el análisis funcional.

---

### 4.5. Facilitar la priorización y gestión del trabajo

Proporcionar mecanismos que permitan distinguir entre diferentes niveles de urgencia, impacto y prioridad, facilitando que los equipos concentren sus esfuerzos en las solicitudes que requieren mayor atención.

La priorización deberá contribuir a reducir la gestión basada exclusivamente en orden de llegada o presión informal y permitir una toma de decisiones más consistente.

Las reglas concretas mediante las cuales se calculará, modificará o validará la prioridad serán definidas posteriormente como reglas de negocio.

---

### 4.6. Facilitar la colaboración entre los participantes

Proporcionar un espacio común donde los participantes autorizados puedan intercambiar información relacionada con una solicitud sin perder el contexto del trabajo.

La colaboración deberá permitir diferenciar adecuadamente la información destinada al solicitante de aquella utilizada exclusivamente para coordinación interna entre los responsables.

---

### 4.7. Mejorar la visibilidad operativa

Proporcionar información clara sobre el trabajo pendiente, en curso, detenido, resuelto y cerrado.

La plataforma deberá permitir que cada perfil obtenga la información relevante para su función, evitando la necesidad de consultar múltiples fuentes para determinar la situación del trabajo.

---

### 4.8. Utilizar información para mejorar la gestión

Permitir recopilar y presentar información que ayude a comprender el volumen, distribución, tiempos y evolución de las solicitudes.

WorkDesk deberá facilitar el análisis de indicadores operativos como volumen de solicitudes, tiempos de resolución, cumplimiento de niveles de servicio, carga de trabajo, distribución por categorías y evolución temporal.

El propósito de las métricas será apoyar la toma de decisiones, identificar cuellos de botella, detectar problemas recurrentes y facilitar la mejora continua.

---

### 4.9. Construir y conservar conocimiento organizacional

Establecer una base de conocimientos que permita documentar, conservar, consultar y reutilizar soluciones asociadas a problemas recurrentes.

El conocimiento generado durante la resolución de incidencias deberá poder convertirse progresivamente en un activo reutilizable para técnicos y usuarios.

Este objetivo busca reducir la dependencia de conocimientos exclusivamente personales y facilitar la resolución consistente de problemas similares.

---

### 4.10. Mantener una experiencia de uso clara y comprensible

Diseñar los principales flujos de WorkDesk de forma que los usuarios puedan realizar las tareas correspondientes a su rol sin requerir conocimientos técnicos especializados ni capacitación extensa.

La interfaz deberá priorizar claridad, consistencia y facilidad de uso por sobre la incorporación innecesaria de complejidad visual o funcional.

---

### 4.11. Construir una base preparada para evolucionar

Establecer una base funcional y técnica que permita incorporar nuevas capacidades sin requerir una redefinición completa del producto.

La evolución futura deberá poder incorporar nuevos tipos de trabajo y módulos relacionados con las necesidades identificadas durante el desarrollo, manteniendo la coherencia del sistema.

Este objetivo no implica implementar anticipadamente funcionalidades futuras, sino evitar decisiones innecesariamente restrictivas.

---

## 5. Objetivos específicos del MVP

La primera versión de WorkDesk estará orientada exclusivamente a consolidar el núcleo de gestión de tickets.

El MVP deberá priorizar profundidad, coherencia y calidad por sobre cantidad de funcionalidades.

### 5.1. Gestión del ciclo de vida de tickets

El MVP deberá permitir gestionar de manera coherente las principales etapas del ciclo de vida de un ticket:

**Creación → asignación → atención → seguimiento → resolución → cierre**

El flujo deberá incluir los casos necesarios para situaciones como espera de información y disconformidad con la solución.

---

### 5.2. Gestión de usuarios y responsabilidades

El MVP deberá proporcionar una base de identificación de usuarios y una separación clara de responsabilidades.

Los perfiles principales considerados inicialmente serán:

* Solicitante.
* Técnico.
* Supervisor.
* Administrador.

Las capacidades concretas y permisos asociados a cada rol serán definidos posteriormente en los requisitos funcionales.

---

### 5.3. Asignación y organización del trabajo

El MVP deberá permitir organizar los tickets de acuerdo con los responsables y grupos involucrados.

Deberá ser posible identificar qué solicitudes están disponibles, cuáles se encuentran asignadas, quién es responsable de ellas y qué trabajo corresponde a cada equipo.

---

### 5.4. Seguimiento y trazabilidad

El MVP deberá registrar las acciones y cambios relevantes realizados sobre los tickets.

Como mínimo, deberá ser posible identificar:

* creador de la solicitud;
* responsables involucrados;
* cambios relevantes;
* fechas asociadas;
* evolución del ticket;
* resolución;
* cierre.

El historial deberá ser consultable y mantener consistencia con el estado real del ticket.

---

### 5.5. Priorización

El MVP deberá permitir diferenciar la importancia relativa de los tickets mediante criterios de impacto, urgencia y prioridad.

La solución deberá permitir posteriormente aplicar reglas de negocio que hagan que la clasificación sea consistente y que determinados perfiles autorizados puedan corregirla cuando sea necesario.

---

### 5.6. Gestión de comunicaciones y colaboración

El MVP deberá permitir mantener la comunicación asociada a cada ticket.

La información deberá poder diferenciarse entre:

* comunicación visible para el solicitante;
* información de coordinación interna entre responsables.

La información y los archivos asociados deberán permanecer vinculados al contexto de la solicitud correspondiente.

---

### 5.7. Notificaciones internas

El MVP deberá proporcionar un mecanismo de notificación dentro de la propia aplicación para informar sobre eventos relevantes relacionados con los tickets.

Las notificaciones internas forman parte del alcance del MVP.

No se considera necesario incorporar en esta etapa mecanismos de notificación externos tales como correo electrónico, SMS, servicios de mensajería o servicios de terceros.

---

### 5.8. Indicadores y paneles de control

El MVP deberá proporcionar una visión resumida del estado del trabajo mediante paneles e indicadores básicos.

Como mínimo deberá ser posible observar información relacionada con:

* tickets abiertos;
* tickets en progreso;
* tickets en espera;
* tickets resueltos o cerrados;
* tiempos de resolución;
* carga de trabajo;
* distribución de tickets;
* evolución temporal.

Los indicadores estarán orientados principalmente a la visibilidad operacional y a la demostración del funcionamiento del producto.

---

### 5.9. Búsqueda y organización de información

El MVP deberá permitir localizar y consultar tickets de manera eficiente mediante mecanismos básicos de búsqueda, filtrado y ordenamiento.

El objetivo es reducir el tiempo necesario para encontrar información relevante y facilitar la gestión diaria de las solicitudes.

---

### 5.10. Base de conocimientos inicial

El MVP deberá incluir una primera versión de la base de conocimientos.

Esta permitirá registrar información relacionada con problemas, procedimientos y soluciones que puedan reutilizarse durante la gestión de nuevas incidencias.

La profundidad, clasificación y mecanismos avanzados de búsqueda podrán evolucionar posteriormente.

---

### 5.11. Experiencia web adaptable

El MVP será desarrollado como una aplicación web y deberá mantener una experiencia usable en diferentes tamaños de pantalla.

No se considera parte del MVP el desarrollo de aplicaciones móviles nativas.

---

### 5.12. Demostrabilidad y reproducibilidad

El MVP deberá poder ejecutarse y demostrarse de forma reproducible en el entorno definido para la primera etapa.

La solución deberá incluir los elementos necesarios para levantar el sistema, disponer de datos de demostración y recorrer los principales escenarios del producto.

---

## 6. Prioridades del MVP

Las prioridades principales de la primera versión serán:

### Prioridad 1 — Gestión completa del ciclo de vida

El flujo principal de creación, asignación, atención, resolución y cierre deberá funcionar de manera coherente.

### Prioridad 2 — Trazabilidad

Los cambios y acciones relevantes deberán quedar registrados de forma confiable y poder consultarse posteriormente.

### Prioridad 3 — Usabilidad

Los principales flujos deberán resultar claros y comprensibles para los diferentes perfiles de usuario.

Estas prioridades prevalecerán frente a la incorporación de funcionalidades secundarias.

---

## 7. Criterios generales de éxito del MVP

El MVP podrá considerarse exitoso cuando:

1. Un usuario autorizado pueda iniciar sesión y acceder únicamente a las capacidades correspondientes a su rol.

2. Un solicitante pueda crear una solicitud y consultar posteriormente su evolución.

3. Un técnico pueda identificar trabajo disponible, asumir o recibir un ticket y gestionarlo hasta su resolución.

4. Un supervisor pueda supervisar el trabajo, reasignar responsabilidades y consultar información operacional.

5. Un administrador pueda gestionar los elementos de configuración contemplados para el MVP.

6. El ciclo principal de un ticket pueda ejecutarse de principio a fin sin inconsistencias.

7. Los cambios relevantes realizados sobre un ticket queden registrados y puedan reconstruirse posteriormente.

8. Las comunicaciones y archivos asociados permanezcan vinculados al ticket correspondiente.

9. Las notificaciones internas permitan informar adecuadamente sobre los principales eventos del sistema.

10. Los paneles proporcionen información consistente con los datos almacenados.

11. La base de conocimientos pueda almacenar y reutilizar soluciones.

12. El sistema pueda ejecutarse localmente y ser utilizado para demostración sin depender de servicios externos de pago.

13. La documentación permita comprender cómo instalar, configurar, ejecutar y utilizar el proyecto.

---

## 8. Criterios de calidad

Los objetivos de calidad de WorkDesk deberán considerar la siguiente prioridad:

### 8.1. Trazabilidad — Prioridad estratégica

La información relevante sobre el ciclo de vida del trabajo deberá mantenerse consistente, disponible y consultable.

La pérdida de trazabilidad será considerada un defecto que afecta directamente al propósito central del producto.

### 8.2. Usabilidad — Prioridad crítica

Los principales flujos deberán poder realizarse de manera clara, predecible y comprensible.

### 8.3. Confiabilidad — Prioridad crítica

El sistema deberá mantener consistencia entre las acciones realizadas y la información almacenada.

### 8.4. Mantenibilidad — Prioridad crítica

La solución deberá favorecer una estructura comprensible y modificable, especialmente considerando que WorkDesk será desarrollado y evolucionará durante un período prolongado.

### 8.5. Escalabilidad evolutiva — Prioridad crítica

La solución deberá poder incorporar nuevas capacidades sin generar restricciones innecesarias.

La escalabilidad se entenderá tanto desde el punto de vista técnico como funcional.

### 8.6. Rendimiento — Prioridad alta

Las operaciones habituales deberán presentar tiempos de respuesta adecuados para el contexto del MVP y no generar una experiencia perceptiblemente lenta.

### 8.7. Seguridad — Prioridad alta

La información y las operaciones deberán estar protegidas mediante mecanismos adecuados de autenticación, autorización, gestión de sesiones y protección de credenciales.

### 8.8. Disponibilidad — Prioridad alta

Durante la primera etapa, la disponibilidad estará orientada a garantizar estabilidad durante desarrollo, pruebas y demostraciones.

No se considera objetivo del MVP proporcionar disponibilidad continua de nivel productivo.

---

## 9. Criterios medibles iniciales

Los objetivos de WorkDesk podrán apoyarse en indicadores medibles cuando resulte conveniente.

Para el MVP se consideran especialmente relevantes:

* correcta ejecución del ciclo completo de un ticket;
* consistencia entre estado e historial;
* tiempo de respuesta de las operaciones principales;
* capacidad para trabajar con un conjunto mínimo de datos de prueba;
* consistencia de los indicadores mostrados por el dashboard;
* ausencia de pérdida de información en operaciones habituales.

Como referencia inicial para las pruebas internas, podrá utilizarse un conjunto de al menos 100 tickets de prueba para validar comportamiento y rendimiento básico.

Los valores definitivos de rendimiento, capacidad y tiempos de respuesta deberán establecerse posteriormente durante la definición de requisitos no funcionales y estrategia de pruebas.

---

## 10. Alcance excluido del MVP

Para preservar el foco de la primera etapa, quedan fuera del MVP:

* integración con correo electrónico;
* Active Directory, LDAP u otros mecanismos externos de identidad;
* OAuth u otros proveedores externos de autenticación;
* aplicaciones móviles nativas;
* integraciones con sistemas de terceros;
* automatizaciones avanzadas;
* workflows configurables por usuarios;
* gestión avanzada de proyectos;
* cartas Gantt;
* calendarios avanzados;
* asistencia mediante inteligencia artificial;
* analítica predictiva;
* multiempresa o arquitectura multi-tenant como capacidad operativa;
* infraestructura cloud o despliegue productivo;
* mecanismos avanzados de almacenamiento externo;
* funcionalidades propias de CRM, RR.HH., contabilidad o facturación;
* gestión avanzada de inventario físico;
* comunicación instantánea general como sustituto de herramientas de colaboración.

Las exclusiones anteriores no representan necesariamente una prohibición permanente para futuras versiones, sino una delimitación del alcance inicial.

---

## 11. Evolución futura

La evolución de WorkDesk deberá realizarse progresivamente a partir de las capacidades consolidadas del MVP.

### 11.1. Gestión de tareas

Incorporar capacidades que permitan representar actividades de trabajo más pequeñas o específicas y relacionarlas con tickets u otros elementos.

### 11.2. Gestión de proyectos

Incorporar capacidades para planificar, organizar y realizar seguimiento de proyectos e iniciativas, incluyendo eventualmente dependencias, calendarios y representaciones visuales como diagramas de Gantt.

### 11.3. Gestión del trabajo

Evolucionar desde la gestión de tickets hacia una plataforma capaz de coordinar diferentes tipos de trabajo, responsabilidades, actividades y equipos.

### 11.4. Gestión de activos e inventario

Explorar posteriormente capacidades relacionadas con la administración de equipamiento y recursos tecnológicos, tales como computadores, monitores, periféricos y otros activos, siempre que esta línea aporte valor al producto y sea compatible con su propósito central.

### 11.5. Gestión del conocimiento avanzada

Ampliar progresivamente la base de conocimientos mediante mejores mecanismos de búsqueda, clasificación, reutilización y autoservicio.

### 11.6. Asistencia inteligente

Evaluar posteriormente la incorporación de mecanismos de inteligencia artificial orientados a consultar y utilizar el conocimiento existente, especialmente como apoyo para resolver incidencias y responder consultas.

La incorporación de IA deberá estar sustentada en una necesidad real y no utilizarse únicamente para incrementar la complejidad del producto.

### 11.7. Automatización

Incorporar progresivamente reglas y automatizaciones para reducir tareas repetitivas, mejorar la asignación, gestionar vencimientos, facilitar escalaciones y optimizar procesos.

### 11.8. Analítica avanzada

Evolucionar desde indicadores básicos hacia capacidades analíticas más avanzadas cuando exista suficiente información y una necesidad justificada.

### 11.9. Integraciones

Evaluar posteriormente integraciones con servicios externos, herramientas corporativas y mecanismos de identidad, siempre considerando su valor, dependencia, complejidad y costo.

### 11.10. Expansión a nuevos contextos

Explorar la aplicación de WorkDesk en áreas distintas del soporte TI cuando se identifiquen escenarios donde sus capacidades de centralización, asignación, seguimiento y trazabilidad aporten valor.

---

## 12. Principios para priorizar nuevos objetivos

Toda nueva capacidad propuesta para WorkDesk deberá evaluarse considerando:

1. **Problema real:** ¿qué problema concreto resuelve?

2. **Valor:** ¿qué beneficio aporta al usuario o a la organización?

3. **Coherencia:** ¿está relacionada con el propósito de WorkDesk?

4. **Prioridad:** ¿es más importante que otras necesidades pendientes?

5. **Complejidad:** ¿qué esfuerzo y complejidad introduce?

6. **Mantenibilidad:** ¿su incorporación dificulta la evolución del producto?

7. **Evolución:** ¿facilita o restringe capacidades futuras?

8. **Necesidad real:** ¿existe evidencia suficiente para justificarla?

La capacidad de implementar una funcionalidad no será, por sí sola, suficiente para justificar su incorporación.

---

## 13. Decisiones deliberadamente abiertas

Las siguientes decisiones no se consideran cerradas en esta etapa y deberán definirse posteriormente:

* definición detallada de roles y permisos;
* reglas definitivas de prioridad;
* modelo exacto de SLA;
* reglas de transición entre estados;
* reglas de escalamiento;
* definición detallada de grupos y colas;
* profundidad de la auditoría;
* estrategia definitiva de búsqueda;
* comportamiento de automatizaciones;
* modelo de relación entre tickets, tareas y proyectos;
* alcance definitivo de gestión de activos e inventario;
* modelo multiempresa;
* integraciones externas;
* inteligencia artificial y fuentes de conocimiento;
* estrategia de despliegue productivo;
* evolución de la arquitectura;
* modelo de negocio o eventual comercialización.

Estas decisiones deberán resolverse durante las etapas posteriores de análisis, requisitos y arquitectura.

---

## 14. Regla de control del alcance

La amplitud de la visión futura de WorkDesk no deberá utilizarse como justificación para incorporar prematuramente nuevas funcionalidades al MVP.

La primera prioridad será consolidar un núcleo de gestión de tickets completo, coherente, trazable, usable y técnicamente sostenible.

Una funcionalidad futura podrá incorporarse cuando:

* exista una necesidad definida;
* aporte valor al producto;
* tenga prioridad suficiente;
* pueda integrarse de manera coherente;
* y su complejidad esté justificada.

---

## 15. Definición de éxito del producto

El éxito de WorkDesk no será determinado por la cantidad de módulos o funcionalidades implementadas.

Se considerará más importante que el sistema pueda responder de manera confiable preguntas como:

> ¿Qué solicitudes existen?

> ¿Cuál es su estado?

> ¿Quién es responsable?

> ¿Qué se ha hecho?

> ¿Cuánto tiempo ha tomado?

> ¿Qué problemas se repiten?

> ¿Cómo fueron resueltos?

> ¿Qué conocimiento podemos reutilizar?

> ¿Dónde se concentra el trabajo?

La respuesta a estas preguntas deberá encontrarse dentro de WorkDesk sin depender de información dispersa en diferentes canales.

En última instancia, el objetivo es que WorkDesk pueda convertirse en el punto central de referencia para la gestión del trabajo que administra, comenzando por las incidencias y requerimientos de soporte TI.

---

## 16. Principio rector

> **WorkDesk debe resolver un problema real mediante una solución coherente, útil, trazable y evolutiva; no convertirse en un conjunto de funcionalidades desarrolladas únicamente por su complejidad técnica.**
