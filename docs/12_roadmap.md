# 12_roadmap.md

# WorkDesk — Roadmap de implementación

**Versión:** 1.0  
**Estado:** DEFINITIVO — planificación inicial de implementación  
**Proyecto:** WorkDesk  
**Horizonte objetivo del MVP:** máximo 3 meses  
**Modalidad inicial:** desarrollo local, sin despliegue externo  
**Objetivo principal:** equilibrar aprendizaje técnico con la entrega de un MVP profesional y presentable para portafolio  

---

## 1. Propósito del roadmap

Este documento define el orden recomendado para implementar WorkDesk una vez finalizada la documentación inicial del proyecto.

Su objetivo es transformar las decisiones funcionales, de arquitectura, datos y diseño ya aprobadas en un plan de ejecución claro, incremental y verificable.

El roadmap debe servir para:

- evitar comenzar módulos sin sus dependencias;
- dividir el proyecto en entregas alcanzables;
- mantener control de alcance;
- facilitar aprendizaje progresivo;
- versionar el proyecto desde el inicio;
- establecer criterios objetivos para decidir cuándo una fase está terminada;
- llegar a un MVP funcional y profesional sin intentar implementar simultáneamente todo el sistema.

Este roadmap no reemplaza los documentos anteriores. La implementación de cada fase debe respetar las definiciones aprobadas en requisitos, reglas de negocio, casos de uso, flujo de tickets, modelo de datos, arquitectura y diseño de pantallas.

---

# 2. Contexto de ejecución

El proyecto será desarrollado inicialmente por una sola persona, con un objetivo doble:

1. aprender y consolidar conocimientos de desarrollo web;
2. construir un producto funcional y profesional para portafolio.

El nivel técnico inicial es principalmente básico en desarrollo web y Python, con una base intermedia en SQL.

La disponibilidad estimada es de aproximadamente:

```text
3–4 horas de trabajo por día
```

Como no se definió un número exacto de días semanales, este roadmap utiliza como referencia:

```text
5 días por semana
≈ 15–20 horas semanales
```

Esta cifra es una **base de planificación**, no una obligación. Si temporalmente existe mayor disponibilidad, puede adelantarse trabajo sin alterar el orden de dependencias.

El horizonte máximo deseado para el MVP es:

```text
12 semanas
```

La prioridad será cumplir hitos funcionales, no perseguir fechas a costa de calidad o comprensión.

---

# 3. Estrategia general

La estrategia elegida combina:

```text
desarrollo funcional por módulos
+
implementación vertical
+
versionado incremental
+
aprendizaje progresivo
```

Cada funcionalidad debe construirse de forma vertical siempre que sea posible:

```text
Modelo de datos
↓
Migración
↓
Backend
↓
Autorización
↓
Frontend
↓
Validación
↓
Prueba
↓
Refactor
↓
Commit
```

Esto permite que el proyecto permanezca utilizable durante su crecimiento y evita construir primero una gran cantidad de frontend desconectado o backend sin interfaz.

---

# 4. Principios de implementación

## 4.1. Una funcionalidad antes de la siguiente

No se debe comenzar simultáneamente con múltiples módulos complejos.

Ejemplo:

```text
Autenticación
→ completar
→ validar
→ versionar
→ avanzar a tickets
```

Se permiten pequeños ajustes transversales cuando una funcionalidad lo requiera, pero cada fase debe tener un objetivo principal.

## 4.2. Comprender antes de consolidar

Durante las primeras fases se priorizará avanzar de forma práctica, revisando y comprendiendo progresivamente el código incorporado al proyecto.

Flujo recomendado:

```text
1. Explicación conceptual
2. Diseño técnico
3. Implementación
4. Ejecución
5. Pruebas
6. Debugging
7. Refactor
8. Commit
```

La profundidad de estudio podrá aumentar a medida que avance el proyecto, procurando que cada módulo quede suficientemente comprendido antes de consolidarlo como parte estable de WorkDesk.


## 4.3. Evitar sobrearquitectura

WorkDesk debe respetar su arquitectura aprobada, pero no incorporar complejidad que el MVP no necesita.

Evitar inicialmente:

- microservicios;
- Redis;
- WebSockets;
- Elasticsearch;
- infraestructura cloud;
- múltiples entornos de despliegue;
- colas externas;
- integración con correo;
- sistemas distribuidos.

La prioridad será un **monolito modular local, mantenible y bien estructurado**.

## 4.4. Desarrollo local

El MVP será exclusivamente local.

No forma parte del alcance:

- hosting;
- cloud;
- dominio;
- CI/CD de despliegue;
- publicación pública;
- configuración de servidores externos.

Podrán utilizarse herramientas locales para desarrollo, pruebas y demostración.

---

# 5. Alcance recomendado del MVP

El MVP debe incluir las capacidades necesarias para demostrar el ciclo completo de WorkDesk sin intentar implementar todas las posibles evoluciones futuras.

## 5.1. Incluido en MVP

### Fundación

- estructura de proyecto;
- configuración;
- base de datos PostgreSQL;
- migraciones;
- logging;
- manejo básico de errores;
- datos iniciales.

### Usuarios y seguridad

- login por username;
- logout;
- sesiones;
- usuarios;
- roles;
- RBAC;
- protección de rutas;
- contraseñas seguras;
- control de visibilidad por rol.

### Tickets

- creación;
- listado;
- búsqueda;
- filtros;
- detalle;
- estados;
- prioridades;
- categorías;
- ubicaciones;
- solicitantes;
- técnicos;
- grupos;
- asignación múltiple;
- comentarios públicos;
- notas internas;
- adjuntos;
- historial;
- resolución;
- cierre;
- validación por solicitante;
- reapertura;
- relaciones esenciales cuando correspondan.

### SLA

- políticas por prioridad;
- primera respuesta opcional;
- resolución;
- umbral de aviso;
- calendario laboral;
- pausa en `En espera`;
- reanudación con tiempo restante;
- próximo a vencer;
- vencido;
- avisos internos;
- configuración administrativa básica.

### Notificaciones

- únicamente notificaciones internas;
- leído/no leído;
- navegación al recurso asociado.

### Dashboards

- Dashboard Solicitante;
- Dashboard Técnico/Supervisor;
- indicadores básicos;
- tickets prioritarios;
- actividad reciente.

### Carga de trabajo

- carga por técnico;
- carga por grupo;
- tickets sin asignar;
- acceso al listado filtrado;
- indicadores de criticidad y SLA.

### Base de conocimiento

- listado;
- categorías;
- búsqueda;
- artículo;
- creación/edición según permisos;
- publicación según permisos;
- visualización para Solicitante.

### Reportes

El MVP incluirá los reportes definidos para la primera versión, evitando construir un diseñador dinámico de reportes.

Como mínimo:

- tickets creados;
- tickets resueltos;
- tiempo medio de resolución;
- fuera de SLA;
- tickets por estado;
- tickets por categoría;
- tickets por prioridad;
- resumen por técnico;
- filtros principales;
- exportación básica si queda estable dentro del plazo.

### Administración

- usuarios;
- grupos;
- categorías;
- prioridades;
- ubicaciones;
- estados/transiciones según alcance definido;
- SLA;
- cierre/reapertura;
- configuración de notificaciones internas;
- configuración de archivos;
- retención básica;
- auditoría;
- estado del sistema.

### Calidad

- responsive;
- accesibilidad base;
- validaciones;
- manejo de estados vacíos;
- loading;
- errores;
- datos demo;
- README profesional;
- capturas del sistema;
- versionado Git.

---

# 6. Elementos recomendados para post-MVP

Para mantener el objetivo de tres meses, las siguientes capacidades deberán considerarse evoluciones posteriores salvo que el proyecto avance con suficiente margen.

## 6.1. Fuera del MVP prioritario

- despliegue externo;
- notificaciones por correo;
- SMS;
- integraciones externas;
- modo oscuro;
- fotografías de perfil;
- diseñador avanzado de reportes;
- dashboards altamente configurables;
- sistema de favoritos de artículos;
- valoración de artículos;
- comentarios en artículos;
- recuperación automática de contraseña por correo;
- autenticación social;
- WebSockets;
- actualizaciones en tiempo real;
- multi-tenant;
- facturación;
- API pública completa;
- automatizaciones avanzadas;
- reglas complejas de reasignación automática.

---

# 7. Backups y restauración

Para el MVP se recomienda:

```text
scripts/herramientas primero
```

antes que una interfaz administrativa completa.

La primera versión debe permitir respaldar:

- PostgreSQL;
- archivos adjuntos;
- manifiesto o información necesaria para restauración.

El mecanismo puede apoyarse en:

```text
pg_dump
+
copiado de uploads
+
manifest
```

La UI de backup/restore puede implementarse posteriormente si existe tiempo suficiente.

La prioridad del MVP es que el respaldo **funcione realmente**, no disponer primero de una pantalla visual que todavía no restaure correctamente.

---

# 8. Estrategia de pruebas

Aunque inicialmente se prefiera desarrollar primero y agregar pruebas posteriormente, no se recomienda postergar **todas** las pruebas hasta el final.

Se utilizará un enfoque híbrido.

## 8.1. Durante cada fase

Antes de considerar una funcionalidad terminada debe realizarse:

- prueba manual del flujo principal;
- prueba manual de errores previsibles;
- prueba de permisos;
- una cantidad pequeña de tests automatizados para reglas críticas.

## 8.2. Fase de estabilización

Posteriormente se ampliará la cobertura mediante:

- tests unitarios;
- tests de servicios;
- tests de autorización;
- tests de reglas de negocio;
- tests de integración;
- regresión de flujos críticos.

No es necesario adoptar TDD como metodología obligatoria.

El objetivo es evitar llegar a la semana final con una aplicación grande sin ningún mecanismo de regresión.

---

# 9. Estrategia Git y GitHub

El repositorio debe crearse inmediatamente después de finalizar:

1. documentación inicial;
2. estructura base de carpetas;
3. `.gitignore`;
4. README inicial.

## 9.1. Repositorio

Se recomienda un repositorio:

```text
WorkDesk
```

en el perfil personal de GitHub.

Debe mantenerse libre de:

- contraseñas;
- secretos;
- `.env`;
- bases de datos exportadas;
- archivos personales;
- uploads reales;
- claves privadas.

## 9.2. Estrategia de ramas

Para un proyecto individual no es necesario mantener permanentemente una rama `develop`.

Se recomienda:

```text
main
```

como rama estable, más ramas cortas:

```text
feature/auth
feature/tickets
feature/sla
feature/knowledge-base
feature/reports

fix/...
refactor/...
docs/...
```

Flujo:

```text
main
 ↓
feature/x
 ↓
desarrollo
 ↓
pruebas
 ↓
merge
 ↓
main estable
```

GitHub Pull Requests pueden utilizarse incluso trabajando solo, principalmente para:

- revisar cambios;
- documentar decisiones;
- practicar un flujo profesional.

No son obligatorias para cada cambio trivial.

---

# 10. Convención de commits

Los commits deben ser:

- pequeños;
- coherentes;
- descriptivos;
- relacionados con una única intención.

Ejemplos:

```text
feat: add user authentication
feat: implement ticket creation
feat: add ticket assignment service
fix: prevent requester from viewing internal notes
fix: resume SLA after waiting state
refactor: extract ticket state service
test: add authorization tests for ticket detail
docs: update roadmap
```

No utilizar como práctica habitual:

```text
cambios
fix
actualizacion
cosas nuevas
final
final2
```

---

# 11. Versionado

Se utilizará versionado incremental.

Propuesta:

```text
v0.1.0   Fundación técnica
v0.2.0   Autenticación y RBAC
v0.3.0   Núcleo de tickets
v0.4.0   Colaboración y adjuntos
v0.5.0   SLA y notificaciones
v0.6.0   Dashboards y carga de trabajo
v0.7.0   Administración y conocimiento
v0.8.0   Reportes, auditoría y backups
v0.9.0   Estabilización y UX
v1.0.0   MVP
```

Los tags deben representar hitos funcionales relevantes.

---

# 12. Definition of Done general

Una funcionalidad no se considera terminada únicamente porque “se ve en pantalla”.

Como mínimo debe cumplir:

```text
✓ modelo de datos correcto
✓ migración aplicada
✓ backend funcional
✓ permisos verificados
✓ frontend integrado
✓ validaciones
✓ errores controlados
✓ flujo principal probado
✓ reglas críticas testeadas
✓ responsive razonable
✓ código revisado
✓ documentación actualizada cuando corresponda
✓ commit descriptivo
```

---

# 13. Plan de implementación — 12 semanas

El calendario se plantea como referencia para cumplir el objetivo máximo de tres meses.

Debe conservarse el orden aunque una semana se extienda.

---

## FASE 0 — Preparación del proyecto

**Duración orientativa:** 2–3 días  
**Versión objetivo:** inicio de `v0.1.0`

### Objetivos

- estructurar carpetas;
- revisar documentación completa;
- crear README inicial;
- crear repositorio Git;
- configurar `.gitignore`;
- preparar entorno virtual;
- instalar dependencias iniciales;
- configurar VS Code;
- definir `.env.example`.

### Resultado esperado

```text
WorkDesk/
├── docs/
├── src/
├── tests/
├── migrations/
├── scripts/
├── README.md
├── requirements.txt / equivalente
├── .gitignore
└── .env.example
```

La estructura concreta debe respetar `10_arquitectura.md`.

### Criterio de salida

El proyecto puede clonarse, configurarse localmente e iniciar su entorno de desarrollo sin contener funcionalidad de negocio todavía.

---

# 14. FASE 1 — Fundación técnica

**Semana:** 1  
**Versión:** `v0.1.0`

### Aprendizaje principal

- Flask;
- application factory;
- configuración;
- blueprints;
- SQLAlchemy;
- PostgreSQL;
- migraciones;
- variables de entorno.

### Implementación

- inicialización Flask;
- configuración Development/Test;
- conexión PostgreSQL;
- SQLAlchemy;
- Flask-Migrate/Alembic;
- manejo base de errores;
- logging;
- estructura modular;
- página inicial temporal;
- health/status básico.

### Criterio de salida

```text
✓ aplicación inicia
✓ PostgreSQL conecta
✓ migraciones funcionan
✓ configuración no contiene secretos
✓ estructura modular creada
✓ página de prueba responde
✓ tests pueden ejecutarse
```

---

# 15. FASE 2 — Usuarios, autenticación y RBAC

**Semana:** 2  
**Versión:** `v0.2.0`

### Aprendizaje

- hashing;
- sesiones;
- Flask-Login;
- decorators;
- autorización;
- formularios;
- CSRF.

### Implementación

- modelo Usuario;
- roles;
- login por username;
- logout;
- sesión;
- contraseña Argon2id;
- protección de rutas;
- navegación según rol;
- usuarios activos/inactivos;
- cuenta propia básica;
- datos demo de usuarios.

### Roles

```text
Solicitante
Técnico
Supervisor
Administrador
```

### Criterio de salida

```text
✓ usuario válido inicia sesión
✓ inválido no entra
✓ logout funciona
✓ rutas privadas están protegidas
✓ rol controla acceso
✓ sidebar cambia según rol
✓ Solicitante no puede abrir rutas administrativas
✓ tests mínimos de autenticación y autorización
```

---

# 16. FASE 3 — Núcleo de tickets

**Semanas:** 3 y 4  
**Versión:** `v0.3.0`

Esta es la fase central del MVP.

### Implementación

- modelo Ticket;
- ID público;
- solicitante;
- creador;
- categoría;
- prioridad;
- ubicación;
- descripción;
- estados;
- creación;
- listado;
- detalle;
- edición autorizada;
- búsqueda;
- filtros;
- paginación;
- ordenamiento.

### Estados

```text
Nuevo
Asignado
En progreso
En espera
Resuelto
Cerrado
```

### Reglas críticas

- Solicitante solo accede a tickets autorizados;
- prioridad modificable según permisos;
- eliminación física reservada;
- Cancelar no equivale a eliminar;
- Reabierto no se implementa como estado estructural.

### Criterio de salida

Un usuario puede:

```text
crear ticket
→ verlo
→ encontrarlo
→ filtrarlo
→ abrir detalle
```

y cada rol ve únicamente lo autorizado.

---

# 17. FASE 4 — Asignación, colaboración y ciclo de vida

**Semana:** 5  
**Versión:** `v0.4.0`

### Implementación

- grupos;
- múltiples técnicos;
- asignación;
- cambio de estado;
- comentarios públicos;
- notas internas;
- adjuntos;
- historial;
- relaciones esenciales;
- resolución;
- cierre manual;
- confirmación por solicitante;
- rechazo;
- reapertura.

### Regla crítica

```text
Nota interna
→ Técnico / Supervisor / Administrador

Solicitante
→ nunca
```

### Validación de resolución

```text
Resuelto
↓
Solicitante confirma
↓
Cerrado
```

o:

```text
Resuelto
↓
Solicitante rechaza
↓
reapertura
↓
retorno al flujo activo
```

### Criterio de salida

El flujo completo de un ticket puede ejecutarse desde creación hasta cierre.

---

# 18. FASE 5 — SLA y notificaciones internas

**Semana:** 6  
**Versión:** `v0.5.0`

### SLA

Implementar:

- políticas por prioridad;
- primera respuesta opcional;
- objetivo de resolución;
- porcentaje de aviso;
- calendario laboral;
- pausa en `En espera`;
- reanudación;
- próximo a vencer;
- vencido;
- visualización;
- configuración básica.

### Notificaciones internas

Eventos iniciales recomendados:

- ticket creado;
- ticket asignado;
- cambio de estado;
- comentario público;
- resolución;
- solicitud pendiente de validación;
- reapertura;
- SLA próximo;
- SLA vencido.

No implementar correo.

### Criterio de salida

```text
✓ SLA se calcula
✓ cambia según prioridad
✓ puede pausarse
✓ vuelve a continuar
✓ genera indicadores
✓ notificaciones aparecen
✓ usuario puede marcarlas como leídas
```

---

# 19. FASE 6 — Dashboards y carga de trabajo

**Semana:** 7  
**Versión:** `v0.6.0`

### Dashboard Solicitante

- abiertos;
- en progreso;
- requiere revisión;
- cerrados recientes;
- tickets recientes;
- notificaciones.

### Dashboard operacional

- abiertos;
- sin asignar;
- críticos;
- fuera SLA;
- próximos SLA;
- en espera;
- tickets prioritarios;
- carga de trabajo;
- actividad reciente.

### Carga de trabajo

- tickets activos por técnico;
- grupo;
- críticos;
- SLA en riesgo;
- sin asignar.

### Consideración

Un ticket puede tener varios técnicos.

Por tanto:

```text
suma de carga por técnico
≠ necesariamente total de tickets únicos
```

### Criterio de salida

Los dashboards reflejan datos reales de la base de datos y permiten navegar hacia los listados relacionados.

---

# 20. FASE 7 — Administración y Base de conocimiento

**Semana:** 8 y primera mitad de 9  
**Versión:** `v0.7.0`

## 20.1. Administración

Implementar CRUD/configuración necesaria para:

- usuarios;
- grupos;
- categorías;
- prioridades;
- ubicaciones;
- SLA;
- archivos;
- cierre/reapertura;
- notificaciones internas.

Las configuraciones más avanzadas podrán incorporarse progresivamente.

## 20.2. Base de conocimiento

Implementar:

- categorías;
- artículos;
- búsqueda;
- destacados;
- recientes;
- detalle;
- borrador/publicado cuando corresponda;
- creación/edición según permiso;
- publicación según permiso.

### Criterio de salida

El Solicitante puede:

```text
buscar solución
→ leer artículo
→ si no resuelve
→ crear ticket
```

---

# 21. FASE 8 — Reportes, auditoría y backups

**Segunda mitad de semana 9 y semana 10**  
**Versión:** `v0.8.0`

## 21.1. Reportes

Implementar:

- KPIs;
- estado;
- categoría;
- prioridad;
- tiempo de resolución;
- resumen por técnico;
- filtros.

Evitar un diseñador dinámico de reportes.

## 21.2. Auditoría

Registrar y consultar como mínimo:

- cambios de estado;
- asignaciones;
- prioridad;
- notas/comentarios cuando corresponda;
- cambios administrativos relevantes.

## 21.3. Backups

Implementar scripts operativos para:

```text
PostgreSQL
+
uploads
+
manifest
```

La UI completa de restauración no es requisito prioritario de esta fase.

### Criterio de salida

```text
✓ métricas reales
✓ reportes responden a filtros
✓ auditoría consultable
✓ backup generado correctamente
✓ procedimiento de restauración documentado/probado
```

---

# 22. FASE 9 — Calidad visual, responsive y accesibilidad

**Semana:** 11  
**Versión:** `v0.9.0`

Aunque el Design System debe aplicarse durante todo el proyecto, esta fase realizará la revisión global.

### Revisar

- consistencia con mockups;
- sidebar;
- topbar;
- cards;
- tablas;
- formularios;
- badges;
- estados;
- mensajes;
- responsive;
- mobile;
- focus;
- teclado;
- contraste;
- estados vacíos;
- loading;
- errores;
- feedback;
- toasts.

### Criterio de salida

Las pantallas principales se ven y comportan de forma consistente con `11_diseno_de_pantallas.md`.

---

# 23. FASE 10 — Estabilización y release del MVP

**Semana:** 12  
**Versión:** `v1.0.0`

Esta fase no debe utilizarse para agregar grandes funcionalidades nuevas.

### Actividades

- corregir bugs;
- ampliar pruebas;
- revisar permisos;
- revisar seguridad;
- revisar migraciones;
- limpiar código;
- ejecutar Ruff;
- ejecutar pytest;
- revisar logs;
- generar datos demo;
- revisar README;
- agregar capturas;
- documentar instalación;
- documentar ejecución;
- realizar prueba desde instalación limpia;
- preparar release `v1.0.0`.

### Criterio de salida

Una persona que clone el repositorio debe poder:

```text
seguir README
→ instalar
→ configurar PostgreSQL
→ aplicar migraciones
→ cargar datos demo
→ iniciar WorkDesk
→ utilizar el flujo principal
```

sin depender de conocimiento privado del autor.

---

# 24. Orden de prioridad si el calendario se retrasa

Si el proyecto se acerca al límite de tres meses, no se debe reducir calidad del núcleo del ticket para conservar funcionalidades secundarias.

Orden de prioridad:

```text
1. Autenticación y RBAC
2. Tickets
3. Ciclo de vida
4. Asignación
5. Comentarios / notas
6. Adjuntos
7. SLA
8. Notificaciones internas
9. Dashboards
10. Administración esencial
11. Carga de trabajo
12. Base de conocimiento
13. Reportes
14. Auditoría
15. UI avanzada de backup
```

Base de conocimiento, SLA y Reportes forman parte del MVP deseado, por lo que antes de eliminarlos se debe intentar reducir su profundidad y conservar una versión funcional básica.

---

# 25. Alcance mínimo aceptable de módulos grandes

## 25.1. Base de conocimiento mínima

```text
categorías
+
listado
+
búsqueda
+
artículo
+
publicación
```

## 25.2. Reportes mínimos

```text
KPIs
+
estado
+
categoría
+
prioridad
+
tiempo de resolución
+
resumen por técnico
```

## 25.3. SLA mínimo

```text
prioridad
+
resolución
+
primera respuesta opcional
+
aviso
+
pausa
+
calendario
```

---

# 26. Gestión de deuda técnica

Durante el desarrollo aparecerán mejoras que no deben interrumpir continuamente el roadmap.

Crear issues con etiquetas como:

```text
technical-debt
enhancement
post-mvp
```

Una mejora no urgente se registra; no se implementa inmediatamente si desvía la fase actual.

---

# 27. Uso de GitHub Issues

Se recomienda utilizar GitHub Issues desde el comienzo.

Ejemplos:

```text
[AUTH] Implementar login
[TICKET] Crear formulario de alta
[TICKET] Implementar filtros
[SLA] Calcular vencimiento
[KB] Crear búsqueda
[REPORT] Tickets por estado
```

Etiquetas recomendadas:

```text
feature
bug
documentation
test
refactor
technical-debt
post-mvp
```

---

# 28. Organización semanal recomendada

Con 3–4 horas diarias puede utilizarse una rutina aproximada:

```text
Primer bloque
30–45 min
→ comprender tarea / revisar documentación

Segundo bloque
1.5–2 h
→ implementación

Tercer bloque
45–60 min
→ pruebas / debugging / refactor

Cierre
15 min
→ commit / notas / siguiente tarea
```

---


# 29. Riesgos principales

## 29.1. Alcance excesivo

**Riesgo:** intentar implementar todos los detalles diseñados con la misma profundidad.

**Mitigación:** utilizar alcance mínimo por módulo y mover mejoras a post-MVP.

## 29.2. Curva de aprendizaje

**Riesgo:** detener el proyecto por intentar dominar completamente una tecnología antes de utilizarla.

**Mitigación:** aprender lo necesario para cada fase y profundizar progresivamente.

## 29.3. Acumulación de código poco comprendido

**Riesgo:** avanzar demasiado rápido y acumular código que funciona, pero que luego resulta difícil de mantener o explicar.

**Mitigación:** revisar cada módulo, documentar decisiones importantes, refactorizar progresivamente y mantener una estructura clara y consistente.


## 29.4. Postergar pruebas

**Riesgo:** descubrir regresiones graves cerca de `v1.0`.

**Mitigación:** tests mínimos de reglas críticas desde cada fase y ampliación en estabilización.

## 29.5. Perfeccionismo visual temprano

**Riesgo:** dedicar demasiado tiempo a ajustar CSS antes de cerrar funcionalidad.

**Mitigación:** respetar el Design System desde el comienzo, pero reservar pulido final para `v0.9.0`.

## 29.6. Falta de tiempo al conseguir empleo

**Riesgo:** reducirse significativamente la disponibilidad durante el proyecto.

**Mitigación:** roadmap basado en hitos, commits pequeños y versiones utilizables.

---

# 29. Definición de MVP terminado

WorkDesk se considerará MVP `v1.0.0` cuando pueda demostrarse de principio a fin:

```text
Usuario inicia sesión
↓
Solicitante crea ticket
↓
ticket se clasifica
↓
soporte lo visualiza
↓
se asignan técnicos
↓
se trabaja mediante comentarios/notas
↓
SLA se calcula
↓
ticket cambia de estado
↓
técnico resuelve
↓
solicitante valida
↓
ticket se cierra
↓
historial queda registrado
↓
dashboard y reportes reflejan los datos
```

Además:

```text
✓ permisos funcionan
✓ notas internas permanecen privadas
✓ adjuntos funcionan
✓ notificaciones internas funcionan
✓ Base de conocimiento funciona
✓ administración esencial funciona
✓ backup operativo existe
✓ responsive está revisado
✓ pruebas críticas pasan
✓ README permite ejecutar el proyecto
✓ repositorio Git está limpio
✓ release v1.0.0 creada
```

---

# 29. Presentación para portafolio

La versión `v1.0.0` debe ser presentable visual y técnicamente.

El repositorio deberá incluir como mínimo:

- descripción clara;
- objetivos;
- stack;
- arquitectura resumida;
- instrucciones de instalación;
- capturas;
- funcionalidades;
- roles;
- estructura del proyecto;
- estado del proyecto;
- tecnologías utilizadas;
- roadmap posterior;
- documentación técnica relevante.

Los mockups son referencia de diseño; las capturas finales del README deben mostrar la aplicación real implementada.

---

# 29. Qué ocurre después del MVP

Ejemplo de evolución:

```text
v1.1
Mejoras de UX y reportes

v1.2
Configuraciones administrativas avanzadas

v1.3
Dark mode

v1.4
Automatizaciones

v2.0
Evolución hacia gestión de trabajo/proyectos
```

La numeración exacta se definirá cuando exista una necesidad real.

---

# 29. Próximo paso inmediato

Con la aprobación de este documento queda finalizada la documentación inicial:

```text
01_vision_del_proyecto.md
02_objetivos.md
03_roles_y_permisos.md
04_requisitos_funcionales.md
05_requisitos_no_funcionales.md
06_reglas_de_negocio.md
07_casos_de_uso.md
08_flujo_de_tickets.md
09_modelo_de_datos.md
10_arquitectura.md
11_diseno_de_pantallas.md
12_roadmap.md
```

El siguiente paso del proyecto será:

```text
1. revisar estructura del repositorio;
2. crear estructura definitiva de carpetas;
3. preparar README inicial;
4. crear .gitignore;
5. crear .env.example;
6. inicializar Git;
7. crear repositorio GitHub;
8. realizar commit inicial de documentación;
9. comenzar FASE 0;
10. iniciar v0.1.0.
```

---

# 29. Cierre

Este roadmap busca equilibrar:

```text
aprender
+
construir
+
terminar
```

WorkDesk debe crecer mediante incrementos funcionales, comprensibles y versionables.

El objetivo no es programar todas las posibilidades imaginables desde el comienzo, sino llegar a un MVP sólido que demuestre:

- arquitectura;
- backend;
- frontend;
- base de datos;
- seguridad;
- reglas de negocio;
- UX;
- testing;
- Git;
- documentación;
- capacidad para llevar un proyecto de software desde la idea hasta una primera versión funcional.
