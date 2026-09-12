# 11_diseno_de_pantallas.md

# WorkDesk — Diseño de pantallas

**Versión:** 1.0  
**Estado:** DEFINITIVO  
**Proyecto:** WorkDesk  
**Tipo de aplicación:** Sistema web de gestión de tickets de soporte TI  
**Enfoque:** responsive, accesible, modular y preparado para evolución futura  

---

## 1. Propósito

Este documento define la arquitectura de información, navegación, comportamiento de las principales vistas, componentes reutilizables, estados de interfaz, reglas responsive, criterios de accesibilidad, Design System, wireframes y mockups de WorkDesk.

Su objetivo es servir como referencia directa para la implementación del frontend y mantener consistencia entre diseño, experiencia de usuario y las reglas ya definidas en la documentación funcional y técnica del proyecto.

Este documento complementa, pero no reemplaza, las definiciones contenidas en:

- `01_vision_del_proyecto.md`
- `02_objetivos.md`
- `03_roles_y_permisos.md`
- `04_requisitos_funcionales.md`
- `05_requisitos_no_funcionales.md`
- `06_reglas_de_negocio.md`
- `07_casos_de_uso.md`
- `08_flujo_de_tickets.md`
- `09_modelo_de_datos.md`
- `10_arquitectura.md`

Ante un conflicto entre una decisión puramente visual y una regla funcional o de negocio previamente aprobada, prevalecen los documentos funcionales y técnicos definitivos.

---

## 2. Alcance

Esta especificación cubre:

- arquitectura de información;
- navegación por rol;
- jerarquía de pantallas;
- componentes comunes;
- estructura de formularios;
- filtros y tablas;
- dashboards;
- detalle y gestión de tickets;
- Base de conocimiento;
- Reportes;
- Administración;
- Carga de trabajo;
- configuración de SLA;
- comportamiento responsive;
- accesibilidad;
- estados de carga, error y vacío;
- Design System WorkDesk v1.0;
- wireframes;
- mockups de alta fidelidad.

No se define todavía:

- logotipo gráfico definitivo;
- identidad gráfica avanzada;
- tema oscuro final;
- animaciones decorativas;
- prototipos interactivos;
- integraciones externas no contempladas por el MVP.

---

# 3. Principios de diseño

## 3.1. Personalidad visual

WorkDesk debe sentirse:

- profesional;
- moderno;
- tecnológico;
- sobrio;
- confiable;
- amigable;
- claro.

Las sensaciones principales que debe transmitir son:

1. **Orden**
2. **Control**
3. **Simplicidad**
4. **Tecnología**

La interfaz adopta una estética SaaS moderna y profesional, evitando una apariencia excesivamente corporativa, fría o genérica.

---

## 3.2. Principios UX

La interfaz debe:

- priorizar claridad sobre ornamentación;
- permitir comprender rápidamente el estado de una solicitud;
- mostrar primero la información que permite actuar;
- evitar exponer complejidad interna a usuarios que no la necesitan;
- reutilizar patrones y componentes;
- mantener terminología consistente;
- ofrecer navegación comprensible;
- mantener accesibles los filtros relevantes;
- proporcionar feedback después de acciones;
- evitar formularios innecesariamente extensos;
- mantener visibles las acciones principales;
- separar acciones frecuentes de acciones secundarias;
- utilizar modales u offcanvas cuando sea preferible mantener contexto;
- evitar pantallas independientes para operaciones que pueden resolverse contextualmente;
- destacar visualmente los tickets no cerrados frente a registros históricos;
- no depender exclusivamente del color para comunicar información.

---

## 3.3. Identidad gráfica provisional

Durante esta etapa no se define logotipo gráfico.

El espacio de marca muestra únicamente:

```text
WorkDesk
```

En la sidebar oscura el texto se presenta en blanco.

En Login se utiliza únicamente el nombre de la aplicación hasta que se defina posteriormente un logotipo o imagen de acceso definitiva.

No deben crearse isotipos, símbolos ni variantes multicolor provisionales.

---

# 4. Arquitectura de información

## 4.1. Inventario de pantallas

| ID | Pantalla |
|---|---|
| UI-001 | Login |
| UI-002 | Dashboard |
| UI-003 | Listado de tickets |
| UI-004 | Crear ticket |
| UI-005 | Detalle y gestión de ticket |
| UI-006 | Carga de trabajo |
| UI-007 | Reasignación masiva |
| UI-008 | Centro de notificaciones |
| UI-009 | Base de conocimiento |
| UI-010 | Detalle de artículo |
| UI-011 | Editor de artículo |
| UI-012 | Reportes |
| UI-013 | Mi cuenta |
| UI-014 | Inicio de Administración |
| UI-015 | Gestión de usuarios |
| UI-016 | Crear / editar usuario |
| UI-017 | Gestión de grupos |
| UI-018 | Gestión de categorías |
| UI-019 | Gestión de prioridades |
| UI-020 | Gestión de ubicaciones |
| UI-021 | Estados y transiciones |
| UI-022 | Configuración de SLA |
| UI-023 | Configuración de cierre y reapertura |
| UI-024 | Configuración de notificaciones |
| UI-025 | Configuración de archivos |
| UI-026 | Políticas de retención |
| UI-027 | Auditoría administrativa |
| UI-028 | Respaldos y restauración |
| UI-029 | Estado del sistema |

---

## 4.2. Acciones contextuales

Las siguientes operaciones no requieren una pantalla principal independiente cuando puedan resolverse mediante interacción contextual dentro de UI-005 u otras vistas:

- asignar técnicos;
- autoasignar;
- modificar prioridad cuando el rol lo permita;
- cambiar estado;
- pasar a `En espera`;
- resolver;
- cerrar directamente;
- confirmar resolución;
- rechazar resolución;
- reabrir;
- escalar;
- relacionar tickets;
- vincular duplicados;
- añadir comentarios públicos;
- añadir notas internas;
- adjuntar archivos;
- vincular artículos de conocimiento.

Los patrones preferidos son:

- **modal** para confirmaciones, resolución, cierre o acciones de alto impacto;
- **offcanvas** para operaciones contextuales complejas como asignaciones o filtros avanzados;
- **dropdown** para acciones secundarias;
- **inline** para comentarios, edición simple o estados inmediatos.

---

# 5. Navegación por rol

## 5.1. Solicitante

```text
Dashboard
Mis tickets
Crear ticket
Base de conocimiento
Notificaciones
────────
Mi cuenta
```

---

## 5.2. Técnico

```text
Dashboard
Tickets
Crear ticket
Carga de trabajo
Base de conocimiento
Reportes
Notificaciones
────────
Mi cuenta
```

El módulo de Reportes se limita al alcance de información autorizado para el Técnico.

---

## 5.3. Supervisor

```text
Dashboard
Tickets
Crear ticket
Carga de trabajo
Reasignación
Base de conocimiento
Reportes
Notificaciones
────────
Mi cuenta
```

---

## 5.4. Administrador

```text
Dashboard
Tickets
Crear ticket
Carga de trabajo
Reasignación
Base de conocimiento
Reportes
Notificaciones
Administración
────────
Mi cuenta
```

---

## 5.5. Regla de navegación y autorización

Las opciones no autorizadas:

- no deben mostrarse deshabilitadas;
- no deben aparecer en sidebar;
- no deben ser accesibles mediante navegación directa;
- siempre deben protegerse en backend.

La interfaz nunca sustituye las validaciones de autorización del servidor.

---

# 6. Matriz de acceso por pantalla

Leyenda:

- **✓** acceso principal;
- **C** acceso condicionado por permisos/alcance;
- **—** sin acceso.

| Pantalla | Solicitante | Técnico | Supervisor | Administrador |
|---|:---:|:---:|:---:|:---:|
| Login | ✓ | ✓ | ✓ | ✓ |
| Dashboard | ✓ | ✓ | ✓ | ✓ |
| Listado de tickets | ✓* | ✓ | ✓ | ✓ |
| Crear ticket | ✓ | ✓ | ✓ | ✓ |
| Detalle de ticket | ✓* | ✓ | ✓ | ✓ |
| Carga de trabajo | — | ✓ | ✓ | ✓ |
| Reasignación masiva | — | — | ✓ | ✓ |
| Notificaciones | ✓ | ✓ | ✓ | ✓ |
| Base de conocimiento | ✓ | ✓ | ✓ | ✓ |
| Detalle de artículo | ✓ | ✓ | ✓ | ✓ |
| Editor de artículo | — | C | ✓ | ✓ |
| Reportes | — | C | ✓ | ✓ |
| Mi cuenta | ✓ | ✓ | ✓ | ✓ |
| Administración | — | — | — | ✓ |
| Usuarios | — | — | — | ✓ |
| Crear / editar usuario | — | — | — | ✓ |
| Grupos | — | — | — | ✓ |
| Categorías | — | — | — | ✓ |
| Prioridades | — | — | — | ✓ |
| Ubicaciones | — | — | — | ✓ |
| Estados y transiciones | — | — | — | ✓ |
| SLA | — | — | — | ✓ |
| Cierre y reapertura | — | — | — | ✓ |
| Notificaciones - configuración | — | — | — | ✓ |
| Archivos - configuración | — | — | — | ✓ |
| Retención | — | — | — | ✓ |
| Auditoría | — | — | — | ✓ |
| Respaldos | — | — | — | ✓ |
| Estado del sistema | — | — | — | ✓ |

\* Solo sobre tickets autorizados.

---

# 7. Reglas de visualización por rol

## 7.1. Solicitante

El Solicitante:

- visualiza solo tickets autorizados;
- visualiza comentarios públicos;
- nunca visualiza notas internas;
- no visualiza estructura operacional innecesaria;
- no administra grupos ni técnicos;
- no visualiza SLA operacional detallado;
- puede visualizar la prioridad;
- puede confirmar una resolución;
- puede rechazar una resolución y aportar observaciones;
- puede adjuntar archivos cuando corresponda.

La experiencia debe privilegiar lenguaje comprensible para usuario final.

Ejemplos:

- `Atendido por` en lugar de una estructura técnica compleja;
- `Requiere tu revisión` en lugar de términos internos de validación.

---

## 7.2. Técnico

El Técnico:

- accede a información operacional;
- consulta tickets autorizados;
- puede gestionar tickets incluso cuando no sea el único técnico asignado, según permisos;
- visualiza y crea notas internas;
- gestiona comentarios públicos;
- consulta grupo responsable;
- consulta técnicos asignados;
- consulta SLA;
- puede resolver;
- puede ejecutar cierre manual cuando corresponda;
- consulta prioridad, pero no la modifica después de la creación.

---

## 7.3. Supervisor

Además de las capacidades operacionales correspondientes:

- puede modificar prioridad;
- puede ejecutar escalamiento manual;
- puede utilizar reasignación;
- accede a reportes amplios;
- puede publicar contenido de conocimiento cuando tenga autorización.

---

## 7.4. Administrador

El Administrador:

- accede a Administración;
- gestiona parámetros;
- gestiona usuarios y estructura;
- configura SLA y políticas;
- consulta auditoría;
- gestiona respaldos;
- consulta estado del sistema;
- puede realizar eliminación física cuando las reglas lo permitan.

---

# 8. App Shell

## 8.1. Sidebar

Color:

```text
#111827
```

Dimensiones:

```text
Expandida: 248 px
Colapsada: 72 px
```

Características:

- icono + texto en estado expandido;
- iconos en estado colapsado;
- tooltip obligatorio para opciones colapsadas;
- estado activo claramente visible;
- pequeño acento azul;
- navegación accesible por teclado;
- botón `Contraer` en desktop.

En tablet y mobile la sidebar se reemplaza por `offcanvas`.

---

## 8.2. Topbar

Altura:

```text
64 px
```

Incluye:

- búsqueda global;
- notificaciones;
- avatar;
- nombre;
- rol;
- menú de usuario.

Desktop:

```text
Buscar ticket por ID o texto...       🔔   TS Tony Soprano
                                           Supervisor
```

Mobile:

```text
☰  WorkDesk                     🔔  HS
```

---

## 8.3. Búsqueda global

Placeholder recomendado:

```text
Buscar ticket por ID o texto...
```

La búsqueda global no sustituye las búsquedas específicas de cada módulo.

Ejemplo en Listado:

```text
Buscar por ID, título o contenido...
```

Ejemplo en Base de conocimiento:

```text
Buscar artículos, soluciones o palabras clave...
```

---

# 9. Design System WorkDesk v1.0

## 9.1. Dirección visual

Tema principal:

- claro;
- poco agresivo visualmente;
- fondos ligeramente grisáceos;
- superficies claras;
- sidebar oscura.

El diseño debe quedar preparado para permitir un tema oscuro futuro mediante tokens semánticos.

Evitar:

- negro puro en grandes superficies;
- blanco puro como fondo general;
- gradientes;
- glassmorphism;
- sombras exageradas;
- neón;
- estética gamer;
- estética cyberpunk;
- exceso de iconografía;
- tarjetas excesivamente redondeadas.

---

## 9.2. Colores principales

```text
Primary                #1D4ED8
Sidebar                #111827
Background app         #F1F5F9
Surface / Cards        #FCFCFD
Text primary           #111827
Text secondary         #64748B
Border                 #DDE3EA
Success                #16A34A
Warning                #F59E0B
Danger                 #EF4444
Assigned / Purple      #7C3AED
```

---

## 9.3. Fondos semánticos

```text
Azul suave             #EFF6FF
Verde suave            #F0FDF4
Ámbar suave            #FFFBEB
Rojo suave             #FEF2F2
Morado suave           #F5F3FF
Gris suave             #F8FAFC
```

Los colores intensos deben concentrarse en:

- texto;
- iconos;
- indicadores;
- botones;
- pequeños badges.

Para áreas grandes se priorizan fondos semánticos suaves.

---

# 10. Tipografía

Familia principal:

```text
Inter
```

Escala:

| Uso | Tamaño |
|---|---:|
| Display | 32 px |
| H1 | 28 px |
| H2 | 24 px |
| H3 | 20 px |
| H4 | 18 px |
| Body | 15 px |
| Small | 13 px |
| Metadata | 12 px |

Pesos:

```text
H1 / H2       700
H3 / H4       600
Labels        600
Botones       500–600
Body          400
```

---

# 11. Espaciado, radios y sombras

## 11.1. Escala de spacing

```text
4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 px
```

Separación habitual entre grandes bloques:

```text
24 px
```

Padding habitual de cards:

```text
20–24 px
```

---

## 11.2. Radios

```text
Input / botón       6 px
Card                8 px
Modal              10 px
Badge              pill
```

---

## 11.3. Sombras

- cards: sombra muy sutil;
- dropdowns: sombra moderada;
- modales: sombra moderada;
- evitar profundidad visual excesiva.

La jerarquía debe depender principalmente de:

- fondo;
- borde;
- espaciado;
- tipografía.

---

# 12. Iconografía

Biblioteca:

```text
Bootstrap Icons
```

Usos habituales:

```text
Dashboard             grid / speedometer
Tickets               ticket / file
Crear                 plus-circle
Carga de trabajo      people / chart
Reasignación          arrow-left-right
Base de conocimiento  book
Reportes              bar-chart
Notificaciones        bell
Administración        gear
Mi cuenta             person
Adjuntos              paperclip
SLA                    clock
Buscar                 search
```

Los iconos:

- complementan texto;
- no sustituyen acciones importantes;
- mantienen consistencia;
- no se utilizan como decoración innecesaria.

---

# 13. Avatares

En MVP:

```text
TS
BW
WW
HS
```

Se utilizan iniciales como fallback.

Preparación futura:

```text
si usuario tiene fotografía
→ mostrar fotografía

si no tiene fotografía
→ mostrar iniciales
```

La futura carga de fotografía puede incorporarse desde `Mi cuenta`.

---

# 14. Botones

## 14.1. Primario

- fondo `#1D4ED8`;
- texto blanco;
- radio 6 px;
- visualmente compacto;
- área interactiva accesible.

Ejemplos:

```text
Crear ticket
Guardar cambios
Resolver
```

---

## 14.2. Secundario

- fondo gris claro;
- texto oscuro;
- borde suave.

Ejemplos:

```text
Cancelar
Descartar
Asignar
```

---

## 14.3. Destructivo

El rojo sólido se reserva para acciones destructivas reales.

Ejemplos:

- eliminar físicamente;
- restauración de alto impacto;
- acciones irreversibles.

No deben mostrarse automáticamente en rojo:

- Resolver;
- Cerrar ticket;
- Reabrir;
- Cancelar formulario.

---

## 14.4. Tamaño

Desktop:

```text
36–40 px visualmente
```

Mobile / táctil:

```text
≈ 44 px o más de área interactiva
```

---

# 15. Formularios

Reglas:

- labels visibles sobre el campo;
- placeholder solo como ayuda;
- campos obligatorios marcados con `*`;
- asterisco rojo;
- indicación general `* Campos obligatorios` cuando ayude;
- ayuda contextual debajo del campo;
- tooltip solo cuando sea necesario;
- errores de validación inmediatamente debajo del campo;
- errores técnicos/globales mediante alert;
- no perder información ingresada por validación fallida.

Ejemplo:

```text
Título *
[____________________________]

Ingresa un título.
```

Acciones:

```text
[Cancelar] [Guardar]
```

alineadas habitualmente a la derecha.

---

# 16. Inputs y controles

Altura:

```text
40 px desktop
44 px en contexto táctil/mobile
```

Focus:

- borde azul;
- focus ring visible de 2 px;
- contraste suficiente.

Dropdowns y selects deben compartir lenguaje visual con inputs.

---

# 17. Cards

## 17.1. Estilo

```text
Fondo:      #FCFCFD
Borde:      #DDE3EA
Radius:     8 px
Sombra:     sutil
```

Las cards deben destacar mediante:

- contraste de superficie;
- jerarquía;
- espaciado;

y no mediante sombras fuertes.

---

## 17.2. KPI Cards

Estructura:

```text
Etiqueta
Valor principal
Indicador secundario
```

Mini gráficos permitidos únicamente cuando aporten tendencia real.

Preferidos en:

- Dashboard operacional;
- Reportes.

No se utilizan como decoración.

---

## 17.3. Cards navegables

Cuando una card representa un módulo:

- toda la superficie es clicable;
- hover suave;
- focus visible;
- flecha o affordance discreto.

---

# 18. Tablas

## 18.1. Estilo

- cabecera azul muy claro;
- texto semibold;
- filas claras;
- sin zebra stripes permanentes;
- separadores horizontales suaves;
- hover gris/azulado;
- selección azul suave;
- densidad media.

Altura aproximada:

```text
44–48 px
```

---

## 18.2. Acciones

Preferir:

```text
⋮
```

para acciones secundarias por fila.

El detalle se abre desde:

- ID;
- título.

No es obligatorio un botón `Ver`.

---

## 18.3. Paginación

Patrón:

```text
‹ 1 2 3 4 5 ›
```

Debe incluir:

```text
Mostrando 1–10 de N
```

cuando corresponda.

---

# 19. Filtros y ordenamiento

Patrón principal:

```text
Estado
Prioridad
Técnico
SLA
[Más filtros]
```

Filtros menos frecuentes pueden utilizar offcanvas.

Ejemplos:

- Categoría;
- Grupo;
- Solicitante;
- Ubicación;
- fechas.

Filtros activos pueden representarse mediante chips eliminables:

```text
Prioridad: Alta ×
```

pero solo cuando el filtro esté realmente activo.

La interfaz debe ofrecer una acción clara de limpieza.

Ordenamientos frecuentes:

- Más recientes;
- Más antiguos;
- Mayor prioridad;
- Menor prioridad;
- SLA más urgente;
- Título A–Z;
- Título Z–A.

---

# 20. Tabs

Patrón:

```text
Actividad | Archivos | Historial
─────────
```

La tab activa utiliza:

- texto de mayor jerarquía;
- línea inferior azul.

No se utilizan grandes botones para simular tabs salvo necesidad específica.

---

# 21. Timeline y actividad

Patrón:

```text
Avatar
Nombre
Rol / contexto
Fecha
Contenido
```

Se evita una línea cronológica decorativa excesiva.

Ejemplo:

```text
TS Tony Soprano
Técnico · Hace 8 min

Estamos revisando la configuración...
```

---

## 21.1. Nota interna

Debe diferenciarse claramente del comentario público:

- fondo morado muy suave;
- acento morado;
- icono;
- texto `NOTA INTERNA`;
- indicación `Solo visible para soporte`.

Las notas internas nunca se muestran al Solicitante.

---

# 22. Modales y offcanvas

## 22.1. Modal

Usar para:

- confirmaciones;
- Resolver;
- Cerrar;
- Reabrir;
- acciones destructivas;
- decisiones de alto impacto.

---

## 22.2. Offcanvas

Usar para:

- Asignación;
- filtros avanzados;
- operaciones contextuales complejas.

Debe permitir conservar contexto de la página actual.

---

# 23. Feedback

## 23.1. Toast

Posición:

```text
superior derecha
```

Duración por defecto:

```text
5 segundos
```

Ejemplo:

```text
✓ Ticket #205 actualizado correctamente.
```

Los errores importantes pueden permanecer hasta cierre manual.

Información crítica no debe depender exclusivamente de un toast.

---

## 23.2. Feedback semántico

```text
Información    azul
Éxito          verde
Advertencia    ámbar
Error          rojo
```

---

# 24. Empty states

Patrón:

```text
Icono simple
Mensaje
Explicación breve
Acción cuando corresponda
```

Ejemplo:

```text
No hay tickets abiertos.

Actualmente no tienes trabajo pendiente.

[Crear ticket]
```

Evitar ilustraciones decorativas grandes.

---

# 25. Loading

Patrón principal:

- skeleton para páginas, tablas y cards;
- spinner pequeño para acciones puntuales.

Ejemplo:

```text
[ ⟳ Guardando... ]
```

---

# 26. Adjuntos

En Crear ticket:

```text
Drag & drop + botón Seleccionar archivos
```

En detalle:

```text
Adjuntar archivo
```

Nunca depender exclusivamente de drag & drop.

Un archivo agregado puede mostrarse:

```text
captura_error_vpn.png
248 KB
×
```

---

# 27. Estados y semántica visual

## 27.1. Estados estructurales

Los estados oficiales son exactamente:

1. Nuevo
2. Asignado
3. En progreso
4. En espera
5. Resuelto
6. Cerrado

No deben incorporarse como estados:

- Reabierto;
- Cancelado;
- Duplicado.

`Reabierto` es una acción del flujo.

---

## 27.2. Colores por estado

| Estado | Color |
|---|---|
| Nuevo | Azul grisáceo |
| Asignado | Morado |
| En progreso | Azul |
| En espera | Ámbar |
| Resuelto | Verde |
| Cerrado | Gris |

---

# 28. Prioridades

Las cuatro prioridades son:

| Prioridad | Color |
|---|---|
| Baja | Gris / verde suave |
| Media | Azul |
| Alta | Naranja |
| Crítica | Rojo |

Siempre se muestra texto además del color.

---

# 29. SLA

## 29.1. Semántica

| Estado SLA | Tratamiento |
|---|---|
| Dentro de SLA | Verde |
| Próximo a vencer | Ámbar |
| Vencido | Rojo |
| Pausado | Gris |
| Sin SLA | Neutral |

---

## 29.2. Configuración

La configuración debe contemplar:

- prioridad;
- primera respuesta opcional;
- objetivo de resolución;
- umbral de aviso porcentual;
- calendario laboral;
- días hábiles;
- feriados;
- aviso próximo a vencer;
- aviso al vencer;
- aviso de escalamiento;
- pausa durante `En espera`.

Cuando el SLA se pausa durante `En espera`, al continuar el ticket se reanuda desde el tiempo restante; no se reinicia.

El SLA es informativo y no bloquea la operación.

---

# 30. Notificaciones

Notificación no leída:

- punto azul;
- fondo azul muy suave cuando corresponda.

Leída:

- sin punto;
- superficie normal.

El color rojo no debe utilizarse simplemente para representar una notificación pendiente.

---

# 31. Responsive

WorkDesk utiliza los breakpoints estándar de Bootstrap:

```text
sm     576 px
md     768 px
lg     992 px
xl    1200 px
xxl   1400 px
```

---

## 31.1. Desktop ≥ 992 px

- sidebar visible;
- sidebar expandida o colapsada;
- topbar completa;
- tablas completas;
- dashboards en grilla;
- paneles laterales cuando corresponda.

---

## 31.2. Tablet 768–991 px

- sidebar pasa a offcanvas;
- KPI en 2 × 2;
- columnas secundarias pueden apilarse;
- tablas reducen columnas;
- acciones menos frecuentes pueden agruparse.

---

## 31.3. Mobile < 768 px

- navegación mediante `☰`;
- topbar compacta;
- contenido en una columna;
- botones con zona táctil ampliada;
- formularios apilados;
- tablas complejas se convierten en cards o vistas reducidas;
- paneles laterales pasan al flujo vertical;
- búsqueda puede abrirse mediante acción específica.

---

# 32. Accesibilidad

Objetivo:

- aproximación a WCAG AA;
- navegación por teclado;
- focus visible;
- contraste suficiente;
- labels reales;
- iconos acompañados por texto cuando la acción sea importante;
- no depender exclusivamente del color;
- uploader accesible;
- modales con gestión adecuada del foco;
- mensajes de error asociados al campo;
- controles táctiles suficientemente grandes;
- contenido comprensible sin hover obligatorio.

---

# 33. Animaciones

Duraciones:

```text
Fast         150 ms
Normal       200 ms
Structural   300 ms
```

Usos:

```text
hover        150 ms
focus        150 ms
tabs         150–200 ms
dropdown     200 ms
modal        200–300 ms
sidebar      300 ms
offcanvas    300 ms
```

Evitar:

- rebotes;
- zoom exagerado;
- parallax;
- animaciones decorativas;
- elementos pulsantes sin necesidad.

---

# 34. Estados globales de interfaz

La aplicación debe contemplar:

- normal;
- loading;
- empty;
- sin resultados;
- error de validación;
- error interno;
- no autorizado;
- procesando;
- éxito;
- confirmación crítica;
- sesión expirada.

Estados específicos de tickets:

- ticket bloqueado temporalmente;
- conflicto de concurrencia;
- `En espera`;
- SLA próximo;
- SLA vencido;
- SLA pausado;
- Resuelto pendiente de validación;
- Cerrado;
- reapertura disponible según reglas.

---

# 35. Especificación de pantallas

## UI-001 — Login

### Objetivo

Autenticar mediante:

```text
Usuario
Contraseña
Iniciar sesión
```

### No incluye en MVP

- correo como identificador;
- registro;
- creación de cuenta;
- login social;
- recordar dispositivo;
- recuperación de contraseña;
- selector de rol;
- captcha.

### Diseño

- fondo `#F1F5F9`;
- card central de 400–440 px;
- `WorkDesk` como texto;
- botón primario full-width;
- mostrar/ocultar contraseña;
- Enter envía el formulario.

### Error

```text
Usuario o contraseña incorrectos.
```

No especificar cuál dato falló.

---

## UI-002 — Dashboard

El contenido depende del rol.

### Solicitante

Objetivo:

```text
Mis tickets
Acciones pendientes
Notificaciones
Crear ticket
```

KPIs recomendados:

- Tickets abiertos;
- En progreso;
- Requieren tu revisión;
- Cerrados recientemente.

Si existe una resolución pendiente:

```text
Tienes 1 solicitud pendiente de revisión.
[Revisar resolución]
```

No mostrar:

- carga de técnicos;
- grupos;
- SLA operacional;
- métricas globales.

### Técnico / Supervisor

KPIs:

- Tickets abiertos;
- Sin asignar;
- Críticos;
- Fuera de SLA.

Indicadores secundarios:

- Próximos a vencer SLA;
- En espera.

Áreas:

- Tickets abiertos prioritarios;
- Carga de trabajo;
- Actividad reciente.

### Administrador

Puede utilizar la base operacional, respetando sus permisos y acceso adicional a Administración.

---

## UI-003 — Listado de tickets

### Objetivo

Buscar, filtrar, ordenar y consultar tickets.

### Header

```text
Tickets
Consulta, filtra y gestiona las solicitudes registradas.
```

Tabs rápidas:

```text
Todos
Abiertos
Cerrados
```

Vista operacional recomendada:

```text
Abiertos
```

### Columnas

```text
□
ID
Título
Estado
Prioridad
Categoría
Grupo
Solicitante
Técnico(s)
SLA
Actualizado
⋮
```

Solicitante y Técnico(s) permanecen próximos para facilitar lectura.

### Filtros

Principales:

- Estado;
- Prioridad;
- Técnico;
- SLA.

`Más filtros`:

- Categoría;
- Grupo;
- Solicitante;
- Ubicación;
- fechas.

### Técnicos múltiples

```text
Tony Soprano +2
```

cuando sea preferible evitar múltiples nombres en una celda.

### Responsive

En notebook/tablet priorizar:

- ID;
- Título;
- Estado;
- Prioridad;
- Solicitante;
- Técnico(s);
- SLA.

En mobile utilizar cards.

---

## UI-004 — Crear ticket

### Objetivo

Crear una solicitud sin exigir conocimiento de la estructura interna de soporte.

### Solicitante

Secciones:

1. Cuéntanos qué necesitas
2. Clasificación
3. Adjuntos

Campos:

```text
Título *
Descripción *
Categoría *
Prioridad *
Ubicación
```

### No mostrar al Solicitante

- Grupo responsable;
- técnicos;
- SLA;
- escalamiento;
- cola;
- responsable principal.

### Valores iniciales

- Prioridad puede iniciar en `Media`;
- Categoría puede admitir `Sin clasificar` cuando la configuración lo permita.

### Adjuntos

Drag & drop + selector de archivo.

### Después de crear

```text
Crear ticket
↓
Ticket creado
↓
Detalle del nuevo ticket
```

Toast:

```text
✓ Ticket #XXX creado correctamente.
```

---

## UI-005 — Detalle y gestión de ticket

La pantalla cambia según rol.

### Técnico / Supervisor

Header:

```text
#205
Sin acceso VPN
[En progreso] [Crítica]
```

Acciones habituales:

```text
Asignar
Cambiar estado
Resolver
Más
```

Layout:

```text
Contenido principal 70%
Resumen lateral     30%
```

Tabs:

```text
Actividad
Archivos
Historial
Relaciones
Conocimiento
```

Actividad:

- comentario público;
- nota interna;
- adjuntos;
- timeline.

Resumen:

- Estado;
- Prioridad;
- Categoría;
- Grupo responsable;
- Solicitante(s);
- Técnico(s);
- Ubicación;
- fechas;
- SLA.

### Solicitante

No muestra:

- notas internas;
- SLA detallado;
- grupo responsable;
- cambiar estado;
- resolver;
- escalamiento;
- asignación.

Tabs:

```text
Actividad
Archivos
Historial
```

Resumen simplificado:

- Estado;
- Prioridad;
- Categoría;
- Atendido por;
- Ubicación;
- Creado;
- Actualizado.

---

## UI-005A — Resuelto pendiente de validación

Cuando un ticket entra en `Resuelto`, el Solicitante debe ver una acción clara:

```text
El equipo indicó que tu solicitud está resuelta.

¿Tu solicitud quedó resuelta?

[No, necesito más ayuda]
[Sí, está resuelto]
```

Confirmación:

```text
Resuelto
↓
Confirmación positiva
↓
Cerrado
```

Rechazo:

- solicita comentario;
- reabre el ticket;
- `Reabierto` no se convierte en estado estructural.

---

## UI-006 — Carga de trabajo

### Objetivo

Mostrar distribución actual del trabajo.

No es un ranking de técnicos.

KPIs:

- Tickets activos asignados;
- Sin asignar;
- Críticos;
- SLA en riesgo.

Tabla por técnico:

```text
Técnico
Activos
En progreso
En espera
Críticos
SLA en riesgo
Distribución
Ver tickets
```

Las barras de distribución son comparativas, no representan capacidad máxima salvo que exista configuración explícita.

### Múltiples técnicos

Un ticket puede pertenecer a más de un técnico.

Por tanto:

> La suma de tickets por técnico puede ser superior al total de tickets únicos.

No debe interpretarse como error de cálculo.

### Sobrecarga

Si existe un parámetro configurado de carga elevada, puede mostrarse una advertencia visual.

La advertencia:

- no bloquea nuevas asignaciones;
- no convierte la pantalla en ranking;
- debe acompañarse de texto.

### Áreas secundarias

- Carga por grupo;
- Tickets sin asignar.

### Relación con Reasignación

```text
Carga de trabajo
→ analizar

Reasignación
→ modificar distribución
```

---

## UI-007 — Reasignación masiva

### Objetivo

Permitir al Supervisor/Administrador redistribuir múltiples tickets.

Debe incluir:

- selección de tickets;
- filtros;
- técnico/grupo actual;
- destino;
- resumen de la operación;
- confirmación previa.

No debe mezclarse con Carga de trabajo.

---

## UI-008 — Centro de notificaciones

### Objetivo

Consultar avisos generados por eventos del sistema.

Patrón:

- no leído: punto azul + fondo azul suave;
- leído: fondo normal.

Debe permitir:

- abrir la entidad relacionada;
- marcar como leído;
- filtrar cuando corresponda.

MVP prioriza notificaciones internas.

---

## UI-009 — Base de conocimiento

### Objetivo

Permitir autoservicio antes de crear una solicitud.

Flujo:

```text
Buscar
↓
Explorar categorías
↓
Encontrar artículo
↓
Leer solución
↓
Crear ticket si aún se necesita ayuda
```

### Solicitante

Header:

```text
Base de conocimiento
Encuentra guías y soluciones para resolver problemas frecuentes.
```

Buscador:

```text
Buscar artículos, soluciones o palabras clave...
```

Categorías ejemplo:

- Accesos;
- Correo;
- Hardware;
- Software;
- Redes;
- Aplicaciones.

Áreas:

- Explorar por categoría;
- Artículos destacados;
- Artículos recientes;
- CTA Crear ticket.

No mostrar:

- borradores;
- notas internas;
- métricas editoriales;
- valoraciones;
- favoritos;
- editor.

---

## UI-010 — Detalle de artículo

Debe contener:

- breadcrumb;
- título;
- categoría;
- contenido;
- fecha o metadata autorizada;
- artículos relacionados;
- acción para volver a Base de conocimiento.

El ancho de lectura debe ser controlado y no utilizar toda la pantalla.

---

## UI-011 — Editor de artículo

Acceso según permisos.

Decisión de diseño adoptada:

- Técnico: puede crear/editar borradores autorizados;
- Supervisor: puede crear, editar y publicar;
- Administrador: gestión completa, incluida desactivación.

Debe incluir:

- título;
- contenido;
- categoría;
- visibilidad;
- estado editorial;
- acciones Guardar / Publicar según permiso.

---

## UI-012 — Reportes

### Objetivo

Analizar comportamiento y rendimiento de soporte.

Filtros:

- Periodo;
- Grupo;
- Técnico;
- Categoría;
- Prioridad.

Periodo ejemplo:

```text
Últimos 30 días
```

KPIs:

- Tickets creados;
- Tickets resueltos;
- Tiempo medio de resolución;
- Fuera de SLA.

Gráficos:

1. Tickets por estado — barras verticales.
2. Tickets por categoría — barras horizontales.
3. Tiempo medio de resolución — línea.
4. Tickets por prioridad — barras.

Tabla:

```text
Técnico
Gestionados
Resueltos
En curso
Prom. resolución
Fuera SLA
```

La pantalla:

- no debe emitir rankings de empleados;
- no debe mostrar medallas;
- no debe calificar automáticamente a una persona como mejor o peor.

Los gráficos son complementarios y deben disponer de equivalentes accesibles o información textual.

---

## UI-013 — Mi cuenta

Debe permitir:

- visualizar datos básicos;
- editar campos autorizados;
- cambiar contraseña cuando corresponda;
- cerrar sesión.

Preparación futura:

- fotografía de perfil opcional.

No debe exponer permisos administrativos innecesarios.

---

## UI-014 — Administración

### Objetivo

Actuar como hub de configuración.

Secciones:

### Personas y organización

- Usuarios;
- Grupos.

### Configuración de tickets

- Categorías;
- Prioridades;
- Ubicaciones;
- Estados y transiciones.

### Operación y políticas

- SLA;
- Cierre y reapertura;
- Notificaciones;
- Archivos;
- Retención.

### Sistema y seguridad

- Auditoría;
- Respaldos;
- Estado del sistema.

Cada card:

- icono;
- título;
- descripción;
- metadata opcional;
- navegación completa desde la card.

La pantalla no debe convertirse en un formulario gigante.

---

## UI-015 — Gestión de usuarios

Debe permitir:

- buscar;
- filtrar;
- consultar estado;
- consultar rol;
- crear usuario;
- editar;
- activar/desactivar según permisos.

Patrón de tabla reutiliza UI-003.

---

## UI-016 — Crear / editar usuario

Formulario administrativo con ancho controlado.

Debe reutilizar:

- labels superiores;
- errores inline;
- select de rol;
- estado;
- grupos cuando aplique;
- botones Descartar / Guardar.

---

## UI-017 — Grupos

Debe permitir:

- listar grupos;
- crear;
- editar;
- consultar miembros;
- activar/desactivar según reglas.

No asumir un único grupo por Técnico.

---

## UI-018 — Categorías

Debe permitir:

- listar;
- crear;
- editar;
- activar/desactivar;
- configurar relación propuesta con grupo cuando corresponda.

El Solicitante no está obligado a conocer grupos internos.

---

## UI-019 — Prioridades

Debe contemplar exactamente:

- Baja;
- Media;
- Alta;
- Crítica.

Si la configuración permite parámetros, estos no deben alterar la semántica visual oficial sin revisión del Design System.

---

## UI-020 — Ubicaciones

Debe permitir administrar ubicaciones disponibles para formularios y tickets.

La obligatoriedad del campo depende de configuración.

---

## UI-021 — Estados y transiciones

Debe reflejar exactamente:

```text
Nuevo
Asignado
En progreso
En espera
Resuelto
Cerrado
```

Debe permitir consultar/configurar transiciones autorizadas cuando corresponda.

No agregar `Reabierto` como séptimo estado.

---

## UI-022 — Configuración de SLA

### Header

```text
Administración / SLA

Configuración de SLA
Define los objetivos de atención y resolución según la prioridad del ticket.
```

### Estado general

```text
Aplicar SLA a los tickets [ON/OFF]
```

### Objetivos por prioridad

Tabla:

```text
Prioridad
Primera respuesta
Resolución
Umbral de aviso
```

La primera respuesta es opcional.

Debe poder representar:

```text
Sin objetivo
```

Ejemplos demostrativos:

| Prioridad | Primera respuesta | Resolución | Umbral |
|---|---:|---:|---:|
| Baja | 8 h | 24 h | 80 % |
| Media | 4 h | 12 h | 80 % |
| Alta | 2 h | 6 h | 75 % |
| Crítica | 30 min | 4 h | 75 % |

Estos valores son ejemplos visuales, no constantes obligatorias del sistema.

### Calendario laboral

Debe existir acceso a configuración de:

- días;
- horarios;
- feriados;
- calendario utilizado por SLA.

Resumen:

```text
Calendario laboral
Lunes a viernes · Configurado

[Configurar calendario]
```

### Alertas y comportamiento

```text
[ON] Generar alerta de SLA próximo a vencer
[ON] Generar alerta al vencer el SLA
[ON] Generar aviso de escalamiento
[ON] Pausar SLA mientras el ticket esté En espera
```

### Ayuda semántica

```text
✓ Dentro de SLA
! Próximo a vencer
! Vencido
Ⅱ Pausado
```

El SLA es informativo y no impide continuar trabajando.

---

## UI-023 — Cierre y reapertura

Debe configurar:

- confirmación del Solicitante;
- reapertura;
- cierre automático;
- periodo configurable en horas/días cuando corresponda.

No duplicar configuración de SLA.

---

## UI-024 — Configuración de notificaciones

Debe permitir configurar eventos internos.

MVP:

- notificaciones internas.

No asumir obligatoriamente:

- SMS;
- push externo;
- email externo.

---

## UI-025 — Configuración de archivos

Debe permitir definir:

- tipos permitidos;
- tamaño máximo;
- límites aplicables;
- políticas necesarias.

Evitar hardcodear en diseño un valor que todavía sea configurable.

---

## UI-026 — Retención

Debe permitir administrar políticas de conservación de información según reglas definidas.

---

## UI-027 — Auditoría

Debe permitir consultar eventos relevantes:

- cambios de estado;
- asignaciones;
- modificaciones;
- notas;
- acciones administrativas;
- eventos de seguridad autorizados.

Patrón recomendado:

- tabla;
- filtros;
- fecha;
- usuario;
- entidad;
- acción.

---

## UI-028 — Respaldos y restauración

Debe permitir:

- crear respaldo manual;
- consultar respaldos;
- restaurar cuando corresponda;
- mostrar advertencias de alto impacto.

La restauración requiere confirmación explícita.

La arquitectura de respaldo contempla base de datos, archivos y manifest cuando corresponda.

---

## UI-029 — Estado del sistema

Debe mostrar estado operativo de componentes relevantes.

Ejemplo:

```text
● Operativo
```

El verde solo complementa el texto.

---

# 36. Diseño responsive específico: Detalle Solicitante Mobile

El mockup mobile utiliza el mismo ticket de la vista desktop:

```text
#196 — Problema con correo
Estado: Resuelto
Prioridad: Media
```

Orden recomendado:

```text
Topbar mobile
↓
Volver a Mis tickets
↓
Título / estado / prioridad
↓
Validación pendiente
↓
Resumen
↓
Descripción
↓
Tabs
↓
Actividad
↓
Agregar comentario
```

Topbar:

```text
☰ WorkDesk   🔔 HS
```

La sidebar se abre como offcanvas.

### Validación

Botones verticales:

```text
[Sí, está resuelto]
[No, necesito más ayuda]
```

La acción primaria aparece primero.

---

# 37. Reglas de consistencia de datos en mockups

Los nombres, cantidades, tiempos y métricas utilizados en los mockups son datos ficticios para demostrar la interfaz.

No representan constantes de negocio.

Ejemplos:

- número de usuarios;
- número de categorías;
- número de tickets;
- tiempos SLA;
- cantidades de artículos;
- métricas de reportes.

Las reglas definitivas deben obtenerse de configuración o de la base de datos.

Los IDs ficticios reutilizados entre pantallas deben mantener consistencia narrativa cuando representen el mismo ticket.

---

# 38. Wireframes

Los wireframes constituyen la referencia estructural de media fidelidad.

Ubicación:

```text
docs/assets/wireframes/
```

Archivos:

```text
wf_01_login.png
wf_02_dashboard_solicitante.png
wf_03_dashboard_operacional.png
wf_04_listado_tickets.png
wf_05_crear_ticket.png
wf_06_detalle_ticket_solicitante.png
wf_07_detalle_ticket_tecnico.png
wf_08_administracion.png
```

---

## 38.1. Login

![Wireframe - Login](assets/wireframes/wf_01_login.png)

---

## 38.2. Dashboard Solicitante

![Wireframe - Dashboard Solicitante](assets/wireframes/wf_02_dashboard_solicitante.png)

---

## 38.3. Dashboard operacional

![Wireframe - Dashboard operacional](assets/wireframes/wf_03_dashboard_operacional.png)

---

## 38.4. Listado de tickets

![Wireframe - Listado de tickets](assets/wireframes/wf_04_listado_tickets.png)

---

## 38.5. Crear ticket

![Wireframe - Crear ticket](assets/wireframes/wf_05_crear_ticket.png)

---

## 38.6. Detalle Solicitante

![Wireframe - Detalle ticket Solicitante](assets/wireframes/wf_06_detalle_ticket_solicitante.png)

---

## 38.7. Detalle Técnico / Supervisor

![Wireframe - Detalle ticket Técnico](assets/wireframes/wf_07_detalle_ticket_tecnico.png)

---

## 38.8. Administración

![Wireframe - Administración](assets/wireframes/wf_08_administracion.png)

---

# 39. Mockups

Los mockups representan la referencia visual de alta fidelidad.

Ubicación:

```text
docs/assets/mockups/
```

El mockup maestro que establece el lenguaje visual general es:

```text
mockup_03_dashboard_operacional.png
```

Las restantes vistas reutilizan el mismo Design System.

---

## 39.1. Login

![Mockup - Login](assets/mockups/mockup_01_login.png)

---

## 39.2. Dashboard Solicitante

![Mockup - Dashboard Solicitante](assets/mockups/mockup_02_dashboard_solicitante.png)

---

## 39.3. Dashboard Técnico / Supervisor

![Mockup - Dashboard operacional](assets/mockups/mockup_03_dashboard_operacional.png)

---

## 39.4. Listado de tickets

![Mockup - Listado de tickets](assets/mockups/mockup_04_listado_tickets.png)

---

## 39.5. Crear ticket

![Mockup - Crear ticket](assets/mockups/mockup_05_crear_ticket.png)

---

## 39.6. Detalle Técnico / Supervisor

![Mockup - Detalle ticket Técnico](assets/mockups/mockup_06_detalle_ticket_tecnico.png)

---

## 39.7. Detalle Solicitante

![Mockup - Detalle ticket Solicitante](assets/mockups/mockup_07_detalle_ticket_solicitante.png)

---

## 39.8. Administración

![Mockup - Administración](assets/mockups/mockup_08_administracion.png)

---

## 39.9. Reportes

![Mockup - Reportes](assets/mockups/mockup_09_reportes.png)

---

## 39.10. Base de conocimiento

![Mockup - Base de conocimiento](assets/mockups/mockup_10_base_conocimiento.png)

---

## 39.11. Detalle Solicitante Mobile

![Mockup - Detalle ticket Solicitante Mobile](assets/mockups/mockup_11_detalle_ticket_solicitante_mobile.png)

---

## 39.12. Carga de trabajo

![Mockup - Carga de trabajo](assets/mockups/mockup_12_carga_trabajo.png)

---

## 39.13. Configuración de SLA

![Mockup - Configuración de SLA](assets/mockups/mockup_13_configuracion_sla.png)

---

# 40. Convención de archivos visuales

Estructura recomendada:

```text
docs/
└── assets/
    ├── diagrams/
    ├── images/
    ├── wireframes/
    │   ├── wf_01_login.png
    │   ├── wf_02_dashboard_solicitante.png
    │   ├── wf_03_dashboard_operacional.png
    │   ├── wf_04_listado_tickets.png
    │   ├── wf_05_crear_ticket.png
    │   ├── wf_06_detalle_ticket_solicitante.png
    │   ├── wf_07_detalle_ticket_tecnico.png
    │   └── wf_08_administracion.png
    └── mockups/
        ├── mockup_01_login.png
        ├── mockup_02_dashboard_solicitante.png
        ├── mockup_03_dashboard_operacional.png
        ├── mockup_04_listado_tickets.png
        ├── mockup_05_crear_ticket.png
        ├── mockup_06_detalle_ticket_tecnico.png
        ├── mockup_07_detalle_ticket_solicitante.png
        ├── mockup_08_administracion.png
        ├── mockup_09_reportes.png
        ├── mockup_10_base_conocimiento.png
        ├── mockup_11_detalle_ticket_solicitante_mobile.png
        ├── mockup_12_carga_trabajo.png
        └── mockup_13_configuracion_sla.png
```

Reglas:

- nombres en minúscula;
- sin espacios;
- sin tildes;
- prefijo consistente;
- extensión `.png`.

---

# 41. Design Tokens para implementación

Se recomienda utilizar variables semánticas.

Ejemplo conceptual:

```css
--wd-color-primary;
--wd-color-bg-app;
--wd-color-surface;
--wd-color-text;
--wd-color-text-muted;
--wd-color-border;

--wd-color-success;
--wd-color-warning;
--wd-color-danger;
--wd-color-assigned;

--wd-radius-sm;
--wd-radius-md;

--wd-space-1;
--wd-space-2;
--wd-space-3;

--wd-shadow-card;
--wd-shadow-overlay;
```

Evitar utilizar directamente nombres como:

```css
--blue;
--red;
--gray;
```

La convención semántica permite sustituir valores en un futuro tema oscuro sin reescribir componentes.

---

# 42. Integración con Bootstrap

La implementación debe aprovechar Bootstrap para:

- grid;
- responsive;
- offcanvas;
- modales;
- dropdowns;
- utilities;
- forms;
- breakpoints.

Bootstrap no debe impedir personalizar WorkDesk.

Se recomienda:

- definir variables y estilos propios;
- encapsular componentes visuales reutilizables;
- evitar depender completamente de estilos Bootstrap por defecto;
- mantener el Design System como fuente visual de verdad.

---

# 43. Componentes reutilizables principales

La biblioteca UI de WorkDesk debe contemplar:

```text
App Shell
Sidebar
Topbar
Breadcrumb
Page Header

Button
Icon Button
Input
Textarea
Select
Checkbox
Radio
Toggle
Uploader

Card
KPI Card
Navigation Card

Badge
Alert
Toast

Tabs
Dropdown
Offcanvas
Modal

Table
Pagination
Search
Filters

Timeline
Attachment
Avatar

SLA Indicator
Priority Indicator
Status Indicator

Empty State
Loading State
Error State
```

---

# 44. Reglas de microcopy

El lenguaje debe ser:

- español;
- claro;
- directo;
- amable;
- sin tecnicismos innecesarios.

Preferir:

```text
Crear ticket
Guardar cambios
Publicar comentario
Resolver
Cancelar
```

Evitar, salvo necesidad funcional:

```text
Ejecutar operación
Procesar requerimiento
Confirmar transacción
```

---

# 45. Criterios de aceptación visual

Una pantalla de WorkDesk se considera consistente cuando:

- utiliza el App Shell correcto para el rol;
- aplica tokens aprobados;
- utiliza Inter;
- utiliza Bootstrap Icons;
- mantiene sidebar grafito;
- utiliza fondo claro no agresivo;
- mantiene cards claras y discretas;
- usa el azul únicamente como identidad/interacción;
- usa colores semánticos con moderación;
- no depende del color para comunicar estado;
- mantiene radios aprobados;
- mantiene densidad media;
- conserva focus visible;
- muestra labels reales;
- aplica responsive según breakpoints;
- no agrega funcionalidades no definidas;
- no introduce un logotipo provisional;
- mantiene la terminología funcional oficial.

---

# 46. Consideraciones para implementación

Durante desarrollo:

1. Crear primero App Shell y tokens.
2. Implementar componentes reutilizables.
3. Desarrollar pantallas siguiendo wireframe + mockup.
4. No copiar literalmente datos ficticios.
5. Respetar autorización desde backend.
6. Implementar estados Loading / Empty / Error desde el inicio.
7. Probar navegación con teclado.
8. Validar mobile en cada pantalla, no al final del proyecto.
9. Evitar hardcodear estados, prioridades o SLA en plantillas.
10. Reutilizar filtros, tablas, badges y cards.

---

# 47. Decisiones de diseño derivadas

Las siguientes decisiones fueron necesarias para completar la experiencia de usuario y deben mantenerse alineadas con permisos:

## Base de conocimiento

- Solicitante: consume artículos publicados y autorizados.
- Técnico: puede crear/editar borradores autorizados.
- Supervisor: puede crear, editar y publicar.
- Administrador: gestión completa, incluida desactivación.

## Reportes

- Solicitante: sin módulo dedicado.
- Técnico: reportes operacionales limitados a información autorizada.
- Supervisor: reportes operacionales amplios.
- Administrador: acceso global según permisos.

Estas reglas de interfaz deben verificarse siempre contra la autorización real del sistema.

---

# 48. Decisiones futuras fuera del MVP visual actual

Quedan abiertas para evolución:

- logotipo gráfico;
- imagen/logo específica de Login;
- tema oscuro;
- fotografías de perfil;
- sidebar compacta persistida por usuario;
- recuperación de contraseña;
- valoración de artículos;
- favoritos;
- analítica avanzada;
- gráficos adicionales;
- calendarios SLA avanzados;
- comportamiento multi-tenant;
- nuevas integraciones.

Ninguna de estas decisiones debe asumirse implementada por aparecer como posibilidad futura.

---

# 49. Estado final del diseño

El diseño de pantallas de WorkDesk queda definido mediante:

```text
Arquitectura de información        ✅
Navegación por roles               ✅
29 vistas funcionales              ✅
Design System v1.0                 ✅
Componentes UI                     ✅
Responsive                         ✅
Accesibilidad                      ✅
8 wireframes                       ✅
13 mockups                         ✅
Revisión global de consistencia    ✅
```

Los wireframes definen la estructura.

Los mockups definen la apariencia visual.

El Design System define las reglas comunes que deben impedir divergencias entre pantallas.

---

# 50. Cierre

Con esta especificación se considera completada la fase de diseño de pantallas de WorkDesk.

El documento proporciona una referencia suficiente para comenzar posteriormente la implementación de la interfaz sin necesidad de redefinir la experiencia visual durante la codificación.

Cualquier modificación futura que afecte:

- estados;
- prioridades;
- permisos;
- SLA;
- navegación;
- componentes;
- Design System;

deberá revisarse contra este documento y los documentos funcionales anteriores para preservar consistencia.

---

**Fin del documento — `11_diseno_de_pantallas.md`**
