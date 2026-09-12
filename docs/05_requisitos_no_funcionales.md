# 05. Requisitos No Funcionales

## 1. Información del documento

| Campo             | Valor                                                                          |
| ----------------- | ------------------------------------------------------------------------------ |
| Proyecto          | WorkDesk                                                                       |
| Documento         | Requisitos No Funcionales                                                      |
| Archivo           | `05_requisitos_no_funcionales.md`                                              |
| Versión           | 2.1                                                                            |
| Estado            | Definición                                                                     |
| Alcance           | MVP                                                                            |
| Prioridad general | Seguridad, integridad, mantenibilidad, usabilidad, rendimiento y escalabilidad |
| Idioma inicial    | Español latinoamericano, con localización orientada a Chile                    |
| Entorno inicial   | Local                                                                          |

---

# 2. Propósito

El presente documento define los requisitos no funcionales de **WorkDesk**, estableciendo los atributos de calidad, restricciones técnicas, condiciones operativas y características transversales que deberán cumplirse durante el desarrollo del sistema.

Mientras los requisitos funcionales establecen **qué debe hacer WorkDesk**, los requisitos no funcionales establecen **cómo debe comportarse**, bajo qué condiciones deberá operar y qué características de calidad deberá mantener.

Estos requisitos deberán ser considerados durante el análisis, diseño, implementación, pruebas y evolución del sistema.

WorkDesk se concibe inicialmente como una aplicación web ejecutada localmente, orientada al desarrollo, demostración y validación de una plataforma de gestión de tickets de soporte TI.

Aunque el MVP tendrá un alcance controlado, la solución deberá evitar decisiones técnicas que dificulten innecesariamente su evolución futura.

---

# 3. Principios generales de calidad

Los requisitos no funcionales de WorkDesk deberán orientarse por los siguientes principios:

1. **Seguridad e integridad de la información.**
2. **Mantenibilidad y claridad técnica.**
3. **Usabilidad y accesibilidad.**
4. **Rendimiento adecuado.**
5. **Escalabilidad y capacidad de evolución.**
6. **Trazabilidad y capacidad de recuperación.**
7. **Simplicidad proporcional al alcance del MVP.**

Todos los atributos anteriores son relevantes para el sistema. La prioridad indicada no significa que un atributo pueda ser ignorado en favor de otro.

El objetivo del MVP es construir una base sólida y profesional, evitando incorporar complejidad técnica que no sea necesaria para cumplir los objetivos definidos.

---

# 4. Rendimiento

## RNF-001 — Tiempo de respuesta

WorkDesk deberá proporcionar tiempos de respuesta adecuados para mantener una experiencia de utilización fluida.

En condiciones normales de operación local se establecen los siguientes objetivos:

* Las páginas principales deberán cargar idealmente en menos de 2 segundos.
* Las operaciones frecuentes deberán responder aproximadamente en 1 segundo o menos cuando las condiciones del entorno lo permitan.
* Las operaciones principales no deberán presentar demoras perceptibles innecesarias.
* La creación y actualización de tickets deberán ejecutarse de forma ágil.
* Los cambios de estado deberán ejecutarse de forma ágil.
* Las búsquedas y filtros deberán presentar tiempos de respuesta razonables.

Los valores anteriores representan objetivos de calidad y no constituyen una garantía independiente del hardware, navegador, volumen de datos y entorno de ejecución.

---

## RNF-002 — Eficiencia de consultas

Las operaciones de lectura y búsqueda deberán implementarse procurando:

* Consultas optimizadas.
* Uso adecuado de índices.
* Evitar consultas redundantes.
* Evitar cargas innecesarias de información.
* Utilizar paginación cuando corresponda.
* Reducir consultas repetitivas.
* Mantener tiempos razonables conforme aumente el volumen de información.

---

## RNF-003 — Concurrencia inicial

El MVP deberá soportar como objetivo mínimo entre **10 y 20 usuarios concurrentes** en un escenario de utilización local razonable sin degradación significativa del rendimiento.

Este valor corresponde al escenario inicial de desarrollo, pruebas y demostración y no representa el límite arquitectónico definitivo del producto.

---

## RNF-004 — Preparación para crecimiento

La solución deberá diseñarse de modo que el crecimiento de:

* Usuarios.
* Tickets.
* Comentarios.
* Archivos.
* Registros históricos.
* Logs.
* Configuraciones.

no obligue a reconstruir completamente la aplicación.

No se exige que el MVP soporte grandes volúmenes de información, pero su diseño no deberá introducir obstáculos innecesarios para su crecimiento posterior.

---

# 5. Disponibilidad y confiabilidad

## RNF-005 — Disponibilidad del MVP

El MVP no requerirá disponibilidad permanente ni operación continua 24/7.

La disponibilidad estará orientada principalmente a:

* Desarrollo.
* Pruebas.
* Demostraciones.
* Utilización local controlada.

Durante estos escenarios el sistema deberá mantener estabilidad y evitar fallos inesperados durante la utilización normal.

---

## RNF-006 — Tolerancia ante errores no críticos

Un error no crítico no deberá provocar innecesariamente la caída completa de la aplicación.

Cuando sea técnicamente posible, WorkDesk deberá:

1. Aislar el fallo.
2. Informar al usuario.
3. Registrar internamente el error.
4. Mantener disponibles las funcionalidades no afectadas.

---

## RNF-007 — Fallos de componentes internos

Ante una pérdida temporal de comunicación entre componentes internos, especialmente con la base de datos, el sistema deberá:

* Informar al usuario mediante un mensaje comprensible.
* Evitar mostrar detalles técnicos internos.
* Registrar el incidente.
* Evitar operaciones parciales que produzcan información inconsistente.
* Evitar duplicaciones o pérdidas de información.

---

# 6. Seguridad

## RNF-008 — Autenticación segura

Las credenciales deberán almacenarse utilizando un mecanismo moderno y seguro específicamente diseñado para almacenamiento de contraseñas.

Las contraseñas:

* No deberán almacenarse en texto plano.
* No deberán almacenarse mediante algoritmos criptográficos inadecuados para contraseñas.
* Deberán utilizar mecanismos resistentes a ataques de fuerza bruta.

La selección concreta del algoritmo será definida durante la arquitectura, manteniendo como requisito la utilización de una solución apropiada para contraseñas.

---

## RNF-009 — Política de contraseñas

WorkDesk deberá permitir establecer políticas mínimas de seguridad para las contraseñas.

Como referencia inicial podrá establecerse:

* Longitud mínima.
* Uso de mayúsculas.
* Uso de minúsculas.
* Uso de números.
* Uso de caracteres especiales.

Los parámetros deberán poder evolucionar hacia una configuración administrativa cuando corresponda.

---

## RNF-010 — Control de acceso basado en roles

WorkDesk deberá implementar control de acceso basado en roles (RBAC).

Los roles base son:

* Solicitante.
* Técnico.
* Supervisor.
* Administrador.

Los permisos deberán aplicarse tanto en la interfaz como en el backend.

La ocultación de elementos de interfaz nunca deberá considerarse una medida de seguridad suficiente.

---

## RNF-011 — Autorización en backend

Toda operación protegida deberá validarse en el servidor antes de ejecutarse.

El sistema deberá impedir el acceso no autorizado mediante:

* Manipulación de URLs.
* Alteración de parámetros.
* Acceso directo a endpoints.
* Manipulación de solicitudes.
* Acceso directo a recursos protegidos.

---

## RNF-012 — Principio de mínimo privilegio

Cada usuario deberá poseer únicamente los permisos necesarios para desempeñar las funciones correspondientes a su rol.

Las funcionalidades administrativas deberán mantenerse separadas de las operaciones cotidianas de soporte.

---

## RNF-013 — Gestión segura de sesiones

WorkDesk deberá utilizar mecanismos seguros para gestionar sesiones.

Deberá considerar:

* Expiración por inactividad.
* Duración máxima.
* Invalidación de sesiones.
* Identificadores de sesión seguros.
* Protección adecuada de cookies.
* Protección de credenciales de sesión.

Como referencia inicial se consideran:

* 30 minutos de inactividad.
* 8 horas de duración máxima.

Los valores podrán parametrizarse posteriormente.

---

## RNF-014 — Invalidación de sesiones después de cambios de credenciales

Cuando un usuario cambie su contraseña, el sistema deberá invalidar las sesiones activas anteriores cuando resulte necesario para preservar la seguridad de la cuenta.

El cambio de contraseña deberá provocar la invalidación de las sesiones activas anteriores asociadas al usuario, salvo la sesión utilizada para realizar el cambio cuando la política de seguridad establecida lo permita.

---

## RNF-015 — Limitación de intentos de autenticación

WorkDesk deberá contemplar protección frente a intentos reiterados de autenticación fallida.

Como referencia podrán utilizarse:

* 5 intentos fallidos.
* Bloqueo temporal de 15 minutos.

Los valores deberán poder parametrizarse posteriormente.

Los intentos fallidos deberán quedar registrados para fines de seguridad.

---

## RNF-016 — Protección frente a exposición de información sensible

El sistema no deberá exponer innecesariamente:

* Contraseñas.
* Tokens.
* Credenciales.
* Información interna.
* Stack traces.
* Consultas SQL.
* Rutas internas.
* Secretos de configuración.

Los datos sensibles deberán permanecer protegidos en almacenamiento, transmisión y registros.

---

# 7. Privacidad y protección de datos

## RNF-017 — Protección de información

La información administrada por WorkDesk deberá tratarse como potencialmente sensible.

La protección deberá considerar:

* Datos de usuarios.
* Tickets.
* Comentarios.
* Notas internas.
* Archivos.
* Historial.
* Auditoría.
* Configuración.

---

## RNF-018 — Privacidad por diseño

La privacidad deberá considerarse desde:

* Modelo de datos.
* Backend.
* API.
* Interfaz.
* Almacenamiento.
* Mecanismos de autorización.

La solución deberá aplicar el principio de mínima visibilidad.

---

## RNF-019 — Separación de información pública e interna

Los comentarios públicos y las notas internas deberán mantenerse técnicamente diferenciados.

Las notas internas nunca deberán exponerse a los Solicitantes.

---

## RNF-020 — Visibilidad según permisos

El acceso a tickets, comentarios, archivos y demás información deberá estar restringido según los permisos correspondientes.

Como principio general:

* Los Solicitantes solo accederán a tickets en los que estén autorizados.
* Los Técnicos tendrán, como comportamiento predeterminado del MVP, acceso operacional global a los tickets, independientemente del grupo o de la asignación formal, dentro de las capacidades definidas para su rol.
* La pertenencia a grupos y la asignación servirán para organización y seguimiento, sin constituir por sí solas una barrera de acceso para el Técnico.
* El Administrador podrá configurar restricciones adicionales de visibilidad u operación cuando el contexto organizacional lo requiera.
* Los Supervisores tendrán acceso operacional global.
* Los Administradores tendrán acceso administrativo global.

---

## RNF-021 — Protección de archivos adjuntos

Los archivos no deberán exponerse mediante rutas públicas directas.

El acceso deberá validarse antes de permitir:

* Descarga.
* Visualización.
* Eliminación.
* Otras operaciones.

Los archivos deberán almacenarse fuera de directorios públicamente accesibles cuando sea técnicamente posible.

---

# 8. Integridad y trazabilidad

## RNF-022 — Registro de eventos relevantes

WorkDesk deberá mantener información suficiente para reconstruir las operaciones relevantes realizadas sobre el sistema.

Los registros deberán poder identificar:

* Usuario.
* Fecha y hora.
* Acción.
* Elemento afectado.
* Valor anterior.
* Valor nuevo.
* Resultado.
* Contexto adicional cuando corresponda.

---

## RNF-023 — Integridad del historial

El historial de tickets y los registros de auditoría deberán protegerse contra modificaciones no autorizadas.

Los registros históricos deberán seguir una estrategia de tipo **append-only** dentro del funcionamiento normal de la aplicación.

---

## RNF-024 — Auditoría administrativa

Deberán registrarse las operaciones administrativas relevantes, incluyendo cuando corresponda:

* Cambios de rol.
* Gestión de usuarios.
* Activación y desactivación.
* Cambios de configuración.
* Eliminaciones.
* Restauraciones.
* Cambios relevantes de seguridad.
* Operaciones administrativas de alto impacto.

---

## RNF-025 — Acceso restringido a auditoría

Los registros de auditoría deberán estar disponibles únicamente para usuarios autorizados.

En el MVP el Administrador será el principal perfil con acceso a esta información.

---

# 9. Concurrencia e integridad transaccional

## RNF-026 — Operaciones concurrentes

WorkDesk deberá manejar correctamente situaciones en las que múltiples usuarios interactúen simultáneamente con el mismo recurso.

Ejemplos:

* Dos técnicos intentando asignarse el mismo ticket.
* Dos usuarios modificando el mismo ticket.
* Dos usuarios cambiando la configuración simultáneamente.
* Operaciones simultáneas sobre asignaciones.

---

## RNF-027 — Consistencia de datos

Las operaciones concurrentes no deberán producir:

* Datos duplicados.
* Pérdida de información.
* Relaciones inconsistentes.
* Estados imposibles.
* Asignaciones contradictorias.

Los mecanismos concretos de control serán definidos en el modelo de datos y arquitectura.

---

## RNF-028 — Control de edición concurrente

Cuando un usuario esté modificando un ticket, WorkDesk deberá indicar a los demás usuarios que dicho recurso se encuentra temporalmente bloqueado para edición.

Mientras el bloqueo permanezca activo:

- Otros usuarios podrán consultar la información del recurso.
- No podrán modificar simultáneamente el mismo recurso.
- El sistema deberá informar quién mantiene el bloqueo cuando corresponda.
- Una vez liberado el recurso, otro usuario podrá iniciar su edición.

El bloqueo de edición no reemplaza los mecanismos de integridad y control de concurrencia implementados en backend.

**Alcance:** MVP.

---

## RNF-029 — Indicador visual de edición

Cuando un recurso se encuentre bloqueado para edición, WorkDesk deberá proporcionar una indicación visual a los usuarios que intenten modificarlo.

La indicación deberá permitir identificar, cuando corresponda, que otro usuario se encuentra editando el recurso.

**Alcance:** MVP.

---

# 10. Manejo de errores y excepciones

## RNF-030 — Manejo controlado de errores

Las excepciones deberán gestionarse de forma controlada.

La aplicación no deberá mostrar información técnica sensible al usuario final.

---

## RNF-031 — Mensajes comprensibles

Los mensajes visibles para usuarios deberán ser claros y estar orientados a la acción.

Deberán evitar términos técnicos innecesarios.

---

## RNF-032 — Registro de excepciones

Los errores internos y excepciones relevantes deberán registrarse en los logs correspondientes.

---

## RNF-033 — Errores críticos

Ante errores críticos, como pérdida de conexión con la base de datos, WorkDesk deberá proporcionar una respuesta controlada y evitar mostrar información interna de la infraestructura.

---

# 11. Logs y monitoreo

## RNF-034 — Logging técnico

WorkDesk deberá generar registros técnicos útiles para diagnóstico.

Los niveles podrán contemplar:

* DEBUG.
* INFO.
* WARNING.
* ERROR.
* CRITICAL.

El nivel de detalle deberá adaptarse al entorno.

---

## RNF-035 — Contexto de logs

Cuando corresponda, los logs podrán incluir:

* Usuario.
* IP.
* Endpoint.
* Operación.
* Tiempo de respuesta.
* Identificador de solicitud.
* Excepción.

No deberán registrarse datos sensibles innecesarios.

---

## RNF-036 — Rotación y retención de logs

Los logs no deberán crecer indefinidamente.

La estrategia de retención deberá poder configurarse.

---

## RNF-037 — Health check

WorkDesk deberá proporcionar mecanismos básicos para comprobar el estado de la aplicación y sus componentes principales.

Como mínimo deberá poder verificarse:

* Estado de la aplicación.
* Conectividad con la base de datos.
* Errores relevantes.

---

# 12. Respaldo y recuperación

## RNF-038 — Respaldo de información

WorkDesk deberá contemplar respaldo tanto de:

* Base de datos PostgreSQL.
* Archivos adjuntos.

Los archivos adjuntos forman parte de la información funcional del ticket y no deberán quedar excluidos de los respaldos.

---

## RNF-039 — Respaldo manual

El Administrador deberá disponer de un mecanismo para realizar respaldos manuales.

Este mecanismo podrá implementarse mediante scripts o herramientas administrativas.

---

## RNF-040 — Integridad del respaldo

Los respaldos deberán mantenerse de forma que permitan comprobar su integridad antes de intentar una restauración.

---

## RNF-041 — Restauración

WorkDesk deberá disponer de un procedimiento documentado para restaurar:

* Base de datos.
* Archivos adjuntos.

---

## RNF-042 — Control de restauración

Las operaciones de restauración deberán estar restringidas al Administrador.

Deberán registrar:

* Usuario.
* Fecha y hora.
* Respaldo utilizado.
* Resultado de la operación.

---

## RNF-043 — Protección de respaldos

Los respaldos deberán almacenarse en una ubicación que no quede expuesta públicamente desde la aplicación web.

Cuando sea posible, deberán mantenerse separados del almacenamiento principal del sistema.

---

# 13. Retención de información

## RNF-044 — Políticas de retención

WorkDesk deberá permitir establecer políticas de retención para información relevante, incluyendo:

* Tickets cerrados.
* Historial.
* Auditoría.
* Notificaciones.
* Archivos adjuntos.
* Logs.

---

## RNF-045 — Configuración administrativa de retención

El Administrador deberá poder configurar:

* Período de conservación.
* Elemento afectado.
* Acción posterior a la expiración.
* Retención diferenciada cuando corresponda.

Ninguna política de conservación, archivo o eliminación deberá aplicarse automáticamente si no existe una configuración administrativa que la habilite explícitamente.

---

## RNF-046 — Acciones de retención

Una vez alcanzado el período configurado, el sistema podrá aplicar una acción definida por la política, por ejemplo:

* Mantener.
* Archivar.
* Eliminar.

El comportamiento concreto deberá estar explícitamente definido por la configuración administrativa.

---

## RNF-047 — Integridad durante la retención

Las políticas de retención no deberán generar referencias rotas ni inconsistencias entre:

* Tickets.
* Historial.
* Archivos.
* Solicitantes.
* Técnicos.
* Auditoría.

---

# 14. Compatibilidad

## RNF-048 — Aplicación web

WorkDesk deberá ser una aplicación web.

No será necesario desarrollar una aplicación móvil nativa para el MVP.

---

## RNF-049 — Diseño responsive

La interfaz deberá adaptarse correctamente a:

* Computadores.
* Notebooks.
* Tablets.
* Smartphones.

---

## RNF-050 — Navegadores modernos

El MVP deberá priorizar navegadores modernos basados en estándares actuales.

Se considerarán principalmente:

* Google Chrome.
* Microsoft Edge.
* Mozilla Firefox.
* Safari.

No será necesario soportar Internet Explorer ni navegadores obsoletos.

---

# 15. Usabilidad

## RNF-051 — Facilidad de uso

WorkDesk deberá ser comprensible para usuarios sin conocimientos técnicos avanzados.

---

## RNF-052 — Eficiencia para soporte

Las operaciones frecuentes de Técnicos y Supervisores deberán poder ejecutarse con la menor cantidad razonable de pasos.

---

## RNF-053 — Consistencia de interfaz

La aplicación deberá mantener patrones coherentes en:

* Navegación.
* Formularios.
* Botones.
* Mensajes.
* Estados.
* Prioridades.
* Acciones.

---

## RNF-054 — Retroalimentación de acciones

Las operaciones importantes deberán informar claramente al usuario si:

* Fueron exitosas.
* Fallaron.
* Están procesándose.
* Requieren una acción adicional.

---

## RNF-055 — Confirmaciones para acciones críticas

Las operaciones potencialmente destructivas o de alto impacto deberán requerir confirmación explícita antes de ejecutarse.

Ejemplos:

* Eliminación de tickets.
* Cambios de rol.
* Desactivación de usuarios.
* Restauración de respaldos.
* Eliminaciones administrativas.
* Cambios críticos de configuración.

---

## RNF-056 — Indicadores de carga

Las operaciones que puedan tardar más de unos segundos deberán proporcionar una indicación visual de procesamiento cuando resulte necesario.

---

# 16. Accesibilidad

## RNF-057 — Accesibilidad inicial

WorkDesk deberá incorporar buenas prácticas de accesibilidad desde su diseño.

Como objetivo general se buscará aproximar el sistema a un nivel **AA de WCAG** cuando resulte aplicable.

---

## RNF-058 — Contraste

La interfaz deberá proporcionar un contraste adecuado para favorecer la lectura.

La información no deberá depender exclusivamente del color.

---

## RNF-059 — Navegación por teclado

Las funcionalidades principales deberán poder utilizarse mediante teclado.

---

## RNF-060 — Formularios accesibles

Los controles de formulario deberán disponer de etiquetas claras y correctamente asociadas.

---

## RNF-061 — Foco visible

Los elementos interactivos deberán proporcionar indicadores de foco visibles.

---

## RNF-062 — Mensajes accesibles

Los mensajes de error, advertencia y confirmación deberán presentarse de manera comprensible y perceptible.

---

# 17. Creación de tickets y carga cognitiva

## RNF-063 — Simplicidad para solicitantes

El proceso de creación de tickets deberá requerir la menor cantidad posible de conocimientos técnicos.

El Solicitante no deberá necesitar conocer:

* Grupos internos.
* Estructura del soporte.
* Técnicos disponibles.
* Reglas internas de asignación.

---

## RNF-064 — Lenguaje comprensible

Las etiquetas y mensajes destinados a Solicitantes deberán utilizar lenguaje claro y apropiado para el contexto chileno.

---

## RNF-065 — Ayuda contextual

El sistema podrá proporcionar ejemplos o instrucciones breves para facilitar la creación correcta de tickets.

---

# 18. Mantenibilidad

## RNF-066 — Arquitectura modular

La implementación deberá mantener una estructura modular y reducir el acoplamiento innecesario.

---

## RNF-067 — Separación de responsabilidades

La solución deberá favorecer una separación clara entre:

* Presentación.
* Lógica de negocio.
* Acceso a datos.
* Servicios.
* Infraestructura.

La organización concreta será definida en `10_arquitectura.md`.

---

## RNF-068 — Código mantenible

El código deberá:

* Mantener nombres claros.
* Evitar duplicación innecesaria.
* Mantener responsabilidades bien delimitadas.
* Seguir convenciones consistentes.
* Facilitar la comprensión por otros desarrolladores.

---

## RNF-069 — Configuración externa al código

Los parámetros que deban variar entre entornos no deberán estar rígidamente codificados.

Deberán utilizarse mecanismos apropiados para separar configuración y código.

---

# 19. Control de versiones y calidad

## RNF-070 — Git

El proyecto deberá utilizar Git para control de versiones.

---

## RNF-071 — Versionado del producto

WorkDesk deberá utilizar un esquema coherente de versionado.

---

## RNF-072 — Registro de cambios

El proyecto deberá mantener un registro de cambios relevantes entre versiones.

---

## RNF-073 — Convenciones de desarrollo

El código deberá seguir convenciones consistentes de organización y estilo.

Podrán incorporarse herramientas automáticas de formato, análisis y validación para mantener la calidad.

---

# 20. Pruebas y aseguramiento de calidad

## RNF-074 — Pruebas automatizadas

WorkDesk deberá incorporar pruebas automatizadas para las funcionalidades críticas.

Se considerarán:

* Pruebas unitarias.
* Pruebas de integración.
* Pruebas de funcionalidades críticas.

Las pruebas end-to-end podrán incorporarse progresivamente.

---

## RNF-075 — Pruebas reproducibles

Las pruebas deberán poder ejecutarse mediante procedimientos documentados y reproducibles.

---

## RNF-076 — Cobertura de funcionalidades críticas

Las funcionalidades críticas deberán contar con pruebas suficientes para detectar regresiones.

Como mínimo:

* Autenticación.
* Permisos.
* Creación de tickets.
* Asignación.
* Cambio de estado.
* Resolución.
* Cierre.
* Reapertura.
* Búsquedas.
* Filtros.
* Notificaciones.

No se establece un porcentaje universal de cobertura para todo el código del MVP.

---

## RNF-077 — Validación final del MVP

Antes de considerar finalizado el MVP deberán validarse los principales flujos funcionales del sistema, incluyendo el ciclo completo de ticket.

---

# 21. Internacionalización y localización

## RNF-078 — Idioma inicial

El idioma inicial será español latinoamericano.

La terminología deberá orientarse al contexto chileno.

---

## RNF-079 — Preparación multidioma

La estructura del sistema deberá evitar dependencias rígidas del idioma para facilitar una futura incorporación de:

* Inglés.
* Otros idiomas.

La internacionalización completa no constituye un requisito obligatorio del MVP.

---

## RNF-080 — Localización chilena

El MVP deberá considerar apropiadamente:

* Formatos de fecha.
* Formatos numéricos.
* Zona horaria.
* Convenciones regionales.

La zona horaria inicial de referencia será la de Santiago de Chile.

---

# 22. Parametrización

## RNF-081 — Parametrización de elementos del dominio

WorkDesk deberá permitir modificar determinados parámetros del sistema sin requerir cambios en el código fuente.

Entre los principales elementos configurables podrán encontrarse:

* Categorías.
* Prioridades.
* Ubicaciones.
* Grupos.
* SLA.
* Horarios laborales.
* Feriados.
* Notificaciones.
* Políticas de retención.
* Restricciones de archivos.
* Parámetros de cierre y reapertura.

---

## RNF-082 — Límites de parametrización

La parametrización no deberá permitir alterar arbitrariamente reglas estructurales que comprometan la integridad del sistema.

Los parámetros configurables deberán respetar las restricciones fundamentales definidas por las reglas de negocio.

---

## RNF-083 — Auditoría de configuraciones

Los cambios de configuración relevantes deberán quedar registrados en la auditoría.

Deberá poder identificarse:

* Usuario.
* Fecha y hora.
* Parámetro modificado.
* Valor anterior.
* Valor nuevo.

---

# 23. Despliegue y portabilidad

## RNF-084 — Ejecución local

El MVP deberá ejecutarse completamente en un entorno local.

No deberá depender obligatoriamente de:

* Servicios cloud de pago.
* Hosting externo.
* APIs externas.
* Servicios de terceros obligatorios.

---

## RNF-085 — Funcionamiento sin Internet

Las funcionalidades principales del MVP no deberán requerir una conexión permanente a Internet.

---

## RNF-086 — Separación de entornos

El proyecto deberá permitir trabajar de manera diferenciada en:

* Desarrollo.
* Pruebas.
* Producción futura.

Las configuraciones específicas de cada entorno deberán poder mantenerse separadas.

---

## RNF-087 — Instalación documentada

El procedimiento de instalación y ejecución deberá quedar documentado para permitir preparar el entorno de desarrollo siguiendo instrucciones claras.

---

# 24. Restricciones tecnológicas iniciales

## RNF-088 — Stack base

El MVP utilizará como base:

* HTML.
* CSS.
* Bootstrap.
* JavaScript.
* Python.
* PostgreSQL.

---

## RNF-089 — Tecnologías adicionales

La incorporación de tecnologías adicionales deberá justificarse en función de una necesidad real del proyecto.

No deberán introducirse herramientas únicamente por complejidad o novedad tecnológica.

---

## RNF-090 — Frontend

El frontend inicial deberá mantener una aproximación liviana basada principalmente en HTML, CSS, Bootstrap y JavaScript.

No será obligatorio incorporar frameworks frontend complejos.

---

## RNF-091 — Base de datos

PostgreSQL será el sistema de base de datos del MVP.

---

## RNF-092 — Almacenamiento de archivos

Los archivos adjuntos serán almacenados localmente durante el MVP.

La arquitectura deberá permitir evaluar posteriormente alternativas de almacenamiento externo.

---

# 25. Notificaciones

## RNF-093 — Notificaciones internas

Las notificaciones del MVP deberán funcionar dentro de WorkDesk.

---

## RNF-094 — Independencia de correo

El funcionamiento del MVP no deberá depender de:

* SMTP.
* Correo electrónico.
* SMS.
* WhatsApp.
* Servicios externos de mensajería.

---

## RNF-095 — Notificaciones en tiempo real

El MVP no requerirá WebSockets.

Podrán utilizarse mecanismos más simples de actualización periódica cuando sean suficientes.

---

# 26. Funcionalidades excluidas del alcance no funcional del MVP

Los siguientes elementos no constituyen requisitos de calidad o infraestructura obligatorios del MVP:

* Alta disponibilidad 24/7.
* Balanceo de carga.
* Escalabilidad horizontal.
* Cloud obligatorio.
* Redis o caché distribuida.
* RabbitMQ o Kafka.
* Plataforma centralizada de logs.
* Aplicaciones móviles nativas.
* Infraestructura multiempresa operativa.
* Arquitectura SaaS.
* Integraciones externas obligatorias.
* Auditoría forense avanzada.

La posibilidad de incorporar estas capacidades posteriormente no deberá verse limitada por la arquitectura inicial.

---

# 27. Preparación para evolución futura

## RNF-096 — Evolución modular

La arquitectura deberá permitir incorporar progresivamente:

* Gestión de tareas.
* Gestión de proyectos.
* Calendarios.
* Diagramas de Gantt.
* Gestión de activos.
* Integraciones externas.
* Multiempresa.
* Automatizaciones.
* Aplicaciones móviles.

---

## RNF-097 — Preparación para multiempresa

Aunque el MVP funcionará bajo una única organización, el modelo técnico deberá evitar bloquear una evolución posterior hacia múltiples organizaciones.

La implementación operativa multiempresa queda fuera del MVP.

---

## RNF-098 — Evolución de comunicaciones

La solución deberá permitir incorporar posteriormente otros canales de comunicación, tales como correo electrónico o integraciones externas.

---

# 28. Datos de desarrollo y demostración

## RNF-099 — Datos ficticios

Durante desarrollo, pruebas y demostraciones deberán utilizarse datos ficticios.

No deberán introducirse innecesariamente:

* Datos personales reales.
* Información confidencial.
* Información perteneciente a organizaciones externas.

---

## RNF-100 — Datos de demostración

El proyecto deberá disponer de mecanismos para generar datos de demostración suficientes para validar las funcionalidades principales.

---

# 29. Consideraciones legales y de cumplimiento

## RNF-101 — Privacidad

WorkDesk deberá incorporar principios generales de privacidad y protección de información desde su diseño.

---

## RNF-102 — Cumplimiento específico

El MVP no estará obligado a obtener certificaciones formales ni a cumplir de manera integral normativas específicas como:

* ISO 27001.
* HIPAA.
* GDPR.

No obstante, la arquitectura deberá evitar decisiones que imposibiliten posteriormente adaptar el sistema a requisitos legales o regulatorios aplicables.

---

# 30. Principios de calidad del MVP

WorkDesk deberá mantener durante el desarrollo los siguientes principios:

1. La seguridad no deberá depender únicamente del entorno local.
2. La integridad de la información deberá mantenerse durante todo el ciclo de vida.
3. Las operaciones importantes deberán ser trazables.
4. Los errores deberán manejarse de forma controlada.
5. La interfaz deberá ser comprensible.
6. Las funcionalidades críticas deberán poder probarse.
7. Los datos deberán estar protegidos según los permisos correspondientes.
8. Los archivos deberán gestionarse con controles adecuados.
9. Los respaldos deberán considerar tanto datos estructurados como archivos.
10. La parametrización deberá facilitar la adaptación del sistema sin comprometer su integridad.
11. La complejidad técnica deberá mantenerse proporcional al alcance del MVP.
12. La arquitectura deberá permitir evolución futura.

---

# 31. Resumen

Los requisitos no funcionales de WorkDesk establecen que el MVP deberá ser una aplicación web local, segura, estable, mantenible, usable y suficientemente rápida para el contexto inicial.

La solución deberá proteger adecuadamente la información, aplicar control de acceso basado en roles, mantener la integridad de la trazabilidad, manejar correctamente situaciones de concurrencia, proporcionar mecanismos de respaldo y recuperación y facilitar la adaptación mediante parametrización administrativa.

El MVP priorizará un núcleo sólido de gestión de tickets por sobre la incorporación prematura de automatizaciones avanzadas, infraestructura distribuida o integraciones externas.

Al mismo tiempo, el diseño deberá permitir que WorkDesk evolucione progresivamente hacia una plataforma más amplia de gestión y coordinación del trabajo.

---

## Fin del documento
