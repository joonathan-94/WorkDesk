"""Datos de demostración: tickets de soporte TI.

Este archivo es SOLO datos. La lógica que los carga está en el paquete `demo_tickets/`;
para mejorar la demostración se edita esta lista, sin tocar el código.

Cómo leerla:

- `clave` es la identidad estable de cada ticket (un nombre corto en
  minúsculas, único). El comando reconoce con ella los tickets que ya cargó,
  así que se puede mejorar el título, la descripción o cualquier otro dato
  de la lista sin que al volver a ejecutarlo se dupliquen. No hay que
  cambiarla nunca una vez cargado el ticket.
- Los tickets los crean las personas del equipo ficticio de `seed-demo`
  (`creado_por` es un username). Cuando crea una persona con rol Solicitante,
  ella misma queda como solicitante, igual que en la pantalla "Crear ticket";
  cuando crea el personal (Técnico o Supervisor), `solicitantes` indica a
  nombre de quién.
- La antigüedad es relativa y se mide en tiempo laboral: `hace_dias=12`
  significa "12 días laborales antes del día en que se carga el seed", a la
  `hora` indicada (hora local de `APP_TIMEZONE`, siempre dentro de la
  jornada). Así la demostración siempre tiene tickets de hoy, de la semana
  pasada y del mes anterior.
- Qué días y horas son laborales lo define `DEMO_CALENDAR` (en
  `worktime.py`, junto al motor que calcula el tiempo laboral): por defecto,
  de lunes a viernes de 09:00 a 18:00 y sin feriados. Se puede cambiar sin
  tocar el código que carga los datos. Ningún ticket ni ningún ajuste cae
  fuera de ese calendario.
- `ajustes` son pasos posteriores del personal sobre el mismo ticket
  (reclasificar, cambiar la prioridad con motivo o corregir el título tras
  hablar con la persona). `despues_horas` son horas LABORALES desde el paso
  anterior: el reloj salta las noches, los fines de semana y los feriados.
  Se hacen con los servicios reales, así que dejan su rastro en el historial.
- Categorías y ubicaciones se buscan por su nombre exacto entre las que ya
  existen (el seed no las crea).

Los textos imitan a personas reales y poco técnicas: títulos vagos, prisa,
faltas de tilde, el problema equivocado ("no tengo internet" cuando era un
cable) y prioridades exageradas. Esa ambigüedad es intencional: es lo que
ocurre en un soporte de verdad.

Cada ajuste admite campos opcionales con valor por defecto (ver
`DemoAdjustment`): cambios de estado, grupo, asignación de técnicos,
solicitantes agregados o retirados, comentarios y notas internas, archivos
adjuntos, resolución, validación, cierre y reapertura, y relaciones y
duplicados. Cuando una fase nueva añada algo al ticket se suma un campo
opcional más, y los tickets ya escritos siguen siendo válidos.

Los tickets cuya historia va más allá de la creación están al final de la
lista, agrupados por tema. Al volver a ejecutar el comando solo se crean los
que faltan y un ticket ya cargado no cambia de contenido (para ver esos
cambios en tickets antiguos hay que recrear la base de desarrollo).
"""

from dataclasses import dataclass

# Categoría de respaldo: la crea `seed-catalogs` y siempre existe.
FALLBACK_CATEGORY = "Sin clasificar"

# Nombres exactos de las categorías de la demostración (más la de respaldo).
DEMO_CATEGORIES = (
    "Redes",
    "Hardware",
    "Correo",
    "Impresoras",
    FALLBACK_CATEGORY,
)

# Nombres exactos de las ubicaciones de la demostración.
MARCOLETA = "Suc Lo Marcoleta"
MATTA = "Suc Manuel Antonio Matta"
DEMO_LOCATIONS = (MARCOLETA, MATTA)

# Códigos de prioridad (no cambian aunque un Administrador renombre la prioridad).
PRIORITY_CODES = ("BAJA", "MEDIA", "ALTA", "CRITICA")


@dataclass(frozen=True)
class DemoAdjustment:
    """Un paso posterior del personal sobre un ticket ya creado.

    `despues_horas` son horas laborales desde el paso anterior. Debe cambiar
    algo: título, descripción, categoría, prioridad, estado, grupo,
    asignación, solicitantes o escribir un comentario o una nota. Cambiar la
    prioridad exige `motivo`.

    `estado` es una acción de estado (`INICIAR`, `PONER_EN_ESPERA`,
    `REACTIVAR`, o las de resolución y cierre que se describen más abajo) que se
    ejecuta al final del paso, después de los demás
    cambios, y debe ser válida desde el estado en que va el ticket (empieza
    en Nuevo). Solo `PONER_EN_ESPERA` admite `motivo_espera` (el código de un
    motivo del catálogo, por ejemplo `ESPERA_TERCERO`) y, si ese motivo lo
    permite (`OTRO`), un `texto` libre. Los dos son opcionales.

    `grupo` es el nombre de uno de los grupos de `seed-demo` y lo fija un
    Supervisor. `asignar` es el username de un técnico: lo asigna él mismo
    (se asigna a sí mismo) o un Supervisor; si el ticket está en Nuevo, pasa
    a Asignado.

    `agregar_solicitante` y `retirar_solicitante` son el username de un
    Solicitante demo que el personal agrega o retira como solicitante del
    ticket. Retirar a alguien exige que sea solicitante en ese momento (el
    creador que es Solicitante lo es desde el principio) y agregarlo, que no
    lo sea; `motivo_retiro` es el motivo opcional de la retirada. Quien creó el
    ticket sigue viéndolo aunque se le retire como solicitante.

    `comentario` es un comentario público y `nota_interna` una nota interna
    (solo la ve el personal). La nota la escribe siempre el personal; el
    comentario también puede escribirlo un Solicitante, que debe ser el
    creador o un solicitante del ticket en ese momento y, en ese caso, el paso
    no puede cambiar nada más.

    `adjunto` es un archivo de texto, como `("error.log", "contenido")`: el
    nombre debe terminar en `.txt`, `.log` o `.csv`. Cuelga del comentario
    público del paso; si no hay, de la nota interna; y si tampoco, del ticket.
    Se guarda de verdad en el almacenamiento de adjuntos.

    Resolución y cierre (también con `estado`): `RESOLVER` deja el ticket
    pendiente de validación y su `texto` es la explicación de la solución
    (opcional); `CIERRE_DIRECTO` lo cierra sin pasar por Resuelto (`texto`
    opcional y `motivo_cierre` opcional: `CIERRE_DIRECTO`, por defecto, o
    `CANCELACION`); `CIERRE_EXCEPCIONAL` lo ejecuta un Supervisor desde Resuelto
    y su `texto` es obligatorio; `CONFIRMAR` (`texto` opcional) y `RECHAZAR`
    (`texto` obligatorio) los ejecuta un Solicitante que sea solicitante del
    ticket en ese momento y el paso no puede cambiar nada más (salvo su
    comentario público); `REABRIR` devuelve un ticket Resuelto o Cerrado a En
    progreso y, si el ticket está cerrado, es el único paso posible y va solo.

    Relaciones (solo el personal): `relacionar` es la clave de otro ticket de la
    lista que aparece **antes** y se le relaciona (`RELACIONADO`); `duplicado_de`
    es la clave del ticket principal (también anterior y más antiguo) y marca este
    ticket como su duplicado: lo cierra con el motivo «Duplicado» por el camino del
    cierre directo, así que no puede ir con `estado`, el ticket debe poder cerrarse
    directamente y el principal no puede ser a su vez un duplicado. Tras cerrarlo,
    un ticket solo admite reabrirlo.

    En un mismo paso el orden es: datos, prioridad, grupo, asignación,
    solicitantes (primero se retira y después se agrega), comentario público,
    nota interna, adjunto y, al final, el cambio de estado.
    """

    actor: str
    despues_horas: int
    titulo: str | None = None
    descripcion: str | None = None
    categoria: str | None = None
    prioridad: str | None = None
    motivo: str | None = None
    estado: str | None = None
    motivo_espera: str | None = None
    texto: str | None = None
    grupo: str | None = None
    asignar: str | None = None
    agregar_solicitante: str | None = None
    retirar_solicitante: str | None = None
    motivo_retiro: str | None = None
    comentario: str | None = None
    nota_interna: str | None = None
    adjunto: tuple[str, str] | None = None
    motivo_cierre: str | None = None
    relacionar: str | None = None
    duplicado_de: str | None = None


@dataclass(frozen=True)
class DemoTicket:
    clave: str
    titulo: str
    descripcion: str
    categoria: str
    prioridad: str
    creado_por: str
    hace_dias: int
    hora: str
    ubicacion: str | None = None
    solicitantes: tuple[str, ...] = ()
    ajustes: tuple[DemoAdjustment, ...] = ()


DEMO_TICKETS = (
    # --- Javiera Torres (Finanzas) -----------------------------------------
    DemoTicket(
        clave="excel-bloqueado",
        titulo="no puedo abrir el excel",
        descripcion=(
            "hola, desde hace un par de dias cuando abro el archivo del cierre "
            "mensual me sale un cuadro que dice que esta bloqueado por otro "
            "usuario. pero yo soy la unica que lo usa!!\n"
            "lo necesito si o si para el cierre de la semana. ayuda porfa"
        ),
        categoria="Sin clasificar",
        prioridad="ALTA",
        creado_por="javiera.torres",
        ubicacion=MATTA,
        hace_dias=3,
        hora="09:12",
        ajustes=(
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=4,
                titulo=(
                    "Excel: archivo del cierre mensual bloqueado en la "
                    "carpeta compartida"
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="computador-lento",
        titulo="mi computador esta muy lento",
        descripcion=(
            "hola, buenas tardes. te escribo porque mi computador esta muy "
            "lento hace como una semana. se demora muchisimo en prender "
            "(como 10 minutos!!) y despues se queda pegado cuando abro mas "
            "de dos cosas (excel, el correo y el sistema de contabilidad). "
            "ya lo reinicie varias veces y nada.\n"
            "ademas a veces la pantalla se pone negra un segundo y vuelve. "
            "mi compañera dice que puede ser el internet, pero a ella le "
            "funciona bien con el mismo internet.\n"
            "no se si sera el computador o que, si alguien pudiera venir a "
            "verlo se lo agradeceria harto. gracias"
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="javiera.torres",
        ubicacion=MATTA,
        hace_dias=13,
        hora="15:40",
    ),
    DemoTicket(
        clave="sin-internet-finanzas",
        titulo="URGENTE no tengo internet",
        descripcion=(
            "no tengo internet en mi computador desde que llegue en la "
            "mañana. mis compañeras si tienen!!\n"
            "tengo que enviar los pagos del dia antes de las 12 asi que por "
            "favor vengan lo antes posible!!!!"
        ),
        categoria="Redes",
        prioridad="CRITICA",
        creado_por="javiera.torres",
        ubicacion=MATTA,
        hace_dias=1,
        hora="09:20",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=1,
                titulo="Finanzas: un solo equipo sin red (cable desconectado)",
                prioridad="ALTA",
                motivo=(
                    "Solo afecta al equipo de Javiera: el resto de la oficina "
                    "tiene red. Se atiende en el día."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="contrasena-contabilidad",
        titulo="contraseña",
        descripcion=(
            "no me acuerdo de la contraseña del sistema de contabilidad. "
            "probe varias y ahora dice usuario bloqueado :("
        ),
        categoria="Sin clasificar",
        prioridad="MEDIA",
        creado_por="javiera.torres",
        hace_dias=6,
        hora="11:05",
    ),
    DemoTicket(
        clave="impresora-no-imprime",
        titulo="la impresora no imprime",
        descripcion=(
            "mando a imprimir los comprobantes y dice que esta imprimiendo "
            "pero no sale nada. lo mande como 5 veces y ahora salio todo "
            "junto (se gasto harta hoja).\n"
            "¿se puede ver que pasa? es la del pasillo cerca de contabilidad"
        ),
        categoria="Impresoras",
        prioridad="MEDIA",
        creado_por="javiera.torres",
        ubicacion=MATTA,
        hace_dias=2,
        hora="16:25",
    ),
    # --- Sebastián Vargas (Ventas) -----------------------------------------
    DemoTicket(
        clave="correos-cliente-no-llegan",
        titulo="no me llegan los correos",
        descripcion=(
            "hola, desde hace unos dias no me llegan los correos de un "
            "cliente de Rancagua. le pedi que me mandara uno de prueba y "
            "tampoco llega. me estan reclamando por una cotizacion que yo ni "
            "he visto!!\n"
            "estoy perdiendo ventas, por favor revisar"
        ),
        categoria="Correo",
        prioridad="ALTA",
        creado_por="sebastian.vargas",
        ubicacion=MARCOLETA,
        hace_dias=4,
        hora="09:48",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=10,
                titulo="Correo de un cliente llega a la carpeta de spam",
            ),
        ),
    ),
    DemoTicket(
        clave="wifi-sala-reuniones",
        titulo="el wifi!!!!",
        descripcion=(
            "no funciona el wifi en la sala de reuniones del segundo piso. "
            "estoy con un cliente y no puedo mostrar la presentacion. "
            "URGENTE por favor"
        ),
        categoria="Redes",
        prioridad="CRITICA",
        creado_por="sebastian.vargas",
        ubicacion=MARCOLETA,
        hace_dias=0,
        hora="10:40",
    ),
    DemoTicket(
        clave="correo-celular",
        titulo="celular no recibe el correo de la empresa",
        descripcion=(
            "en mi celular dejo de llegar el correo de la empresa desde que "
            "cambie la clave. en el computador funciona normal. me pidio una "
            "clave y la puse pero sigue igual"
        ),
        categoria="Correo",
        prioridad="MEDIA",
        creado_por="sebastian.vargas",
        hace_dias=8,
        hora="17:10",
    ),
    DemoTicket(
        clave="mouse-malo",
        titulo="mouse malo",
        descripcion=(
            "se echo a perder el mouse, el cursor se mueve solo o se queda "
            "pegado. si pueden cambiarmelo, gracias"
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="sebastian.vargas",
        ubicacion=MARCOLETA,
        hace_dias=20,
        hora="12:30",
    ),
    DemoTicket(
        clave="pantalla-azul",
        titulo="pantalla azul",
        descripcion=(
            "hola, necesito ayuda con mi computador. se me puso la pantalla "
            "azul con letras blancas y un monton de numeros y se reinicio "
            "solo, tenia cosas sin guardar!! ya me paso dos veces en la "
            "semana, la primera pense que fue una falla de luz pero no.\n"
            "ademas el computador se pone muy caliente de abajo y a veces "
            "suena como un zumbido. tengo una reunion con gerencia y "
            "necesito el computador funcionando, si tienen uno de repuesto "
            "para prestarme mientras lo revisan seria excelente.\n"
            "mi anexo es el 214 por si me quieren llamar. gracias!!"
        ),
        categoria="Hardware",
        prioridad="ALTA",
        creado_por="sebastian.vargas",
        ubicacion=MARCOLETA,
        hace_dias=5,
        hora="14:05",
    ),
    # --- Constanza Herrera (Administración) --------------------------------
    DemoTicket(
        clave="impresora-segundo-piso",
        titulo="impresora del segundo piso",
        descripcion=(
            "la impresora del segundo piso no esta funcionando, nadie puede "
            "imprimir. avisamos varias personas. gracias"
        ),
        categoria="Impresoras",
        prioridad="ALTA",
        creado_por="constanza.herrera",
        ubicacion=MATTA,
        hace_dias=2,
        hora="09:30",
    ),
    DemoTicket(
        clave="telefono-sin-tono",
        titulo="el telefono no tiene tono",
        descripcion=(
            "el telefono de mi escritorio no tiene tono, tiene la "
            "pantallita prendida pero no puedo llamar ni recibir. lo "
            "desenchufe y lo enchufe de nuevo y sigue igual"
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="constanza.herrera",
        ubicacion=MATTA,
        hace_dias=10,
        hora="10:15",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=11,
                titulo="Teléfono IP sin conexión (cable de red suelto en el puesto)",
                categoria="Redes",
            ),
        ),
    ),
    DemoTicket(
        clave="correo-practicante",
        titulo="correo para la practicante",
        descripcion=(
            "buenos dias, la proxima semana parte una practicante nueva en "
            "administracion y necesita un correo y acceso a la carpeta "
            "compartida. se llama Camila Reyes (ojo, no confundir con la "
            "jefa de soporte, que tambien se llama Camila). gracias de "
            "antemano"
        ),
        categoria="Correo",
        prioridad="MEDIA",
        creado_por="constanza.herrera",
        hace_dias=16,
        hora="09:00",
    ),
    DemoTicket(
        clave="archivo-borrado",
        titulo="se borro un archivo",
        descripcion=(
            "se me borro una carpeta completa con las rendiciones del mes, "
            "no se si fui yo o se borro sola. estaba en el escritorio del "
            "computador. necesito recuperarla urgente por favor, la "
            "jefatura la esta pidiendo"
        ),
        categoria="Sin clasificar",
        prioridad="ALTA",
        creado_por="constanza.herrera",
        ubicacion=MATTA,
        hace_dias=7,
        hora="16:50",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=5,
                titulo=(
                    "Recuperar carpeta borrada (rendiciones del mes) desde "
                    "el respaldo"
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="toner-bajo",
        titulo="toner",
        descripcion=(
            "en la pantallita de la impresora aparece 'Cartucho <NEGRO> casi "
            "vacio' hace semanas. todavia imprime bien pero queria avisar "
            "antes de que se acabe del todo"
        ),
        categoria="Impresoras",
        prioridad="BAJA",
        creado_por="constanza.herrera",
        ubicacion=MATTA,
        hace_dias=28,
        hora="11:20",
    ),
    # --- Ignacio Molina (Logística) ----------------------------------------
    DemoTicket(
        clave="pistola-lectora",
        titulo="la pistola no lee",
        descripcion=(
            "la pistola lectora de la bodega no lee los codigos, apunto y no "
            "pasa nada. tengo camiones esperando para descarga!!! necesito "
            "que la arreglen YA"
        ),
        categoria="Hardware",
        prioridad="CRITICA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=1,
        hora="09:05",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                titulo="Lector de códigos de barras sin batería (bodega)",
                prioridad="MEDIA",
                motivo=(
                    "El lector solo estaba sin carga: con la base conectada "
                    "ya funciona. No hay detención de la operación."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="etiquetas-despacho",
        titulo="etiquetas",
        descripcion=(
            "no puedo imprimir las etiquetas de los despachos, salen en "
            "blanco o se cortan a la mitad. ya cambie el rollo.\n"
            "les saque una foto de como salen pero no encuentro donde "
            "subirla. necesito las etiquetas para los envios del dia"
        ),
        categoria="Impresoras",
        prioridad="ALTA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=6,
        hora="09:40",
    ),
    DemoTicket(
        clave="sistema-caido-bodega",
        titulo="se cayo el sistema",
        descripcion=(
            "no puedo entrar al sistema de bodega, sale un error y no "
            "carga. tampoco pueden los demas de la bodega. no se que paso"
        ),
        categoria="Sin clasificar",
        prioridad="CRITICA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=11,
        hora="13:30",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=3,
                categoria="Redes",
                prioridad="ALTA",
                motivo=(
                    "No es una caída del sistema: la bodega perdió la "
                    "conexión de red. Hay respaldo en papel para operar, se "
                    "atiende con prioridad alta."
                ),
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=9,
                titulo="Bodega sin red: cable de un switch desconectado",
            ),
        ),
    ),
    DemoTicket(
        clave="computador-bodega-ruido",
        titulo="computador de la bodega",
        descripcion=(
            "el computador de la bodega hace mucho ruido, parece un avion. "
            "esta lleno de tierra el aparato. creo que hay que limpiarlo"
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=33,
        hora="10:50",
    ),
    DemoTicket(
        clave="internet-bodega-intermitente",
        titulo="internet se corta",
        descripcion=(
            "el internet de la bodega se corta cada rato, a veces vuelve "
            "solo a los 5 minutos. cuando se corta no puedo ver las guias de "
            "despacho"
        ),
        categoria="Redes",
        prioridad="MEDIA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=24,
        hora="15:15",
    ),
    # --- Paula Contreras (Recursos humanos) --------------------------------
    DemoTicket(
        clave="impresora-contratos",
        titulo="no imprime contratos",
        descripcion=(
            "buenas, la impresora de recursos humanos no me imprime los "
            "contratos. cuando mando a imprimir sale una hoja con simbolos "
            "raros (como letras chinas o algo asi) y despues sigue sacando "
            "hojas con mas simbolos hasta que le saco el papel!! ya la apague "
            "y la prendi y igual.\n"
            "es la unica impresora que tengo para esto porque los contratos "
            "van en papel especial. necesito imprimir los contratos de las "
            "personas que entran esta semana para la firma y no puedo "
            "atrasarme. ayuda por favor, no se a quien mas pedirle"
        ),
        categoria="Impresoras",
        prioridad="ALTA",
        creado_por="paula.contreras",
        ubicacion=MATTA,
        hace_dias=3,
        hora="14:40",
    ),
    DemoTicket(
        clave="video-sin-sonido",
        titulo="no se escucha el video de la capacitacion",
        descripcion=(
            "el video de la capacitacion obligatoria no tiene sonido en mi "
            "computador, en el de mi compañera si. ya revise y el volumen "
            "esta al maximo"
        ),
        categoria="Sin clasificar",
        prioridad="BAJA",
        creado_por="paula.contreras",
        ubicacion=MATTA,
        hace_dias=9,
        hora="11:35",
    ),
    DemoTicket(
        clave="correo-sospechoso",
        titulo="me llego un correo raro",
        descripcion=(
            "me llego un correo que dice ser de la gerencia pidiendo que "
            "haga clic en un link para actualizar mi cuenta. me dio "
            "desconfianza asi que no hice nada. ¿es real?\n"
            "(tengo una captura pero no se como adjuntarla)"
        ),
        categoria="Correo",
        prioridad="ALTA",
        creado_por="paula.contreras",
        hace_dias=4,
        hora="12:05",
        ajustes=(
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=2,
                prioridad="CRITICA",
                motivo=(
                    "Otras tres personas recibieron el mismo correo con un "
                    "enlace sospechoso. Se escala para bloquear al remitente "
                    "y avisar a todo el personal."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="scanner-rrhh",
        titulo="el scanner",
        descripcion=(
            "el scanner de la impresora de rrhh dice 'error de conexion con "
            "la carpeta' cuando intento escanear documentos. antes "
            "funcionaba"
        ),
        categoria="Impresoras",
        prioridad="MEDIA",
        creado_por="paula.contreras",
        ubicacion=MATTA,
        hace_dias=18,
        hora="10:05",
    ),
    DemoTicket(
        clave="teclado-defectuoso",
        titulo="teclado",
        descripcion=(
            "mi teclado tiene la letra e y la tecla enter que no funcionan "
            "bien, hay que apretar muy fuerte. es medio molesto pero se "
            "puede trabajar. cuando puedan"
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="paula.contreras",
        ubicacion=MATTA,
        hace_dias=22,
        hora="17:20",
    ),
    # --- Andrés Silva (Proyectos) ------------------------------------------
    DemoTicket(
        clave="vpn-no-conecta",
        titulo="no puedo conectarme a la VPN",
        descripcion=(
            "estoy trabajando desde la casa y no me conecta la VPN, dice "
            "'no se pudo establecer la conexion segura'. antes funcionaba "
            "bien. tengo una entrega de planos para un cliente y necesito "
            "entrar a la carpeta del proyecto"
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="andres.silva",
        hace_dias=2,
        hora="17:55",
    ),
    DemoTicket(
        clave="notebook-sobrecalentamiento",
        titulo="notebook se calienta",
        descripcion=(
            "mi notebook se calienta muchisimo y el ventilador suena fuerte, "
            "sobre todo cuando uso el programa de planos. a veces se apaga "
            "solo. es el notebook de la empresa"
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="andres.silva",
        hace_dias=14,
        hora="13:10",
    ),
    DemoTicket(
        clave="instalar-programa-planos",
        titulo="necesito instalar un programa",
        descripcion=(
            "mi jefe me dijo que pidiera por aca la instalacion de un "
            "programa para ver planos en 3D. no se como se llama exactamente "
            "pero es el que usa el equipo de arquitectura (tiene un icono "
            "azul). ¿me pueden ayudar?"
        ),
        categoria="Sin clasificar",
        prioridad="BAJA",
        creado_por="andres.silva",
        hace_dias=30,
        hora="09:35",
    ),
    # --- Creados por el personal, a nombre de otras personas ----------------
    DemoTicket(
        clave="cable-red-ventas",
        titulo="Cambio de cable de red en puesto de Ventas",
        descripcion=(
            "Se solicita cambiar el cable de red del puesto de Sebastián "
            "Vargas (sala de ventas): el conector está suelto y la conexión "
            "se corta al mover el equipo.\n"
            "Pendiente coordinar la visita."
        ),
        categoria="Redes",
        prioridad="BAJA",
        creado_por="diego.soto",
        solicitantes=("sebastian.vargas",),
        ubicacion=MARCOLETA,
        hace_dias=6,
        hora="15:30",
    ),
    DemoTicket(
        clave="notebook-lento-proyectos",
        titulo="Notebook lento - Proyectos",
        descripcion=(
            "Andrés llamó por teléfono: dice que ya había creado un ticket "
            "por el notebook que se calienta y no ha tenido respuesta. Se "
            "registra de nuevo para no perder el caso.\n"
            "Revisar el ventilador y el uso de CPU con prioridad."
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="diego.soto",
        solicitantes=("andres.silva",),
        hace_dias=12,
        hora="11:00",
    ),
    DemoTicket(
        clave="restablecer-clave-correo",
        titulo="Restablecer contraseña de correo",
        descripcion=(
            "Constanza solicita restablecer su contraseña de correo: la "
            "olvidó y el autoservicio no le funciona. Entregar una clave "
            "temporal por teléfono y pedirle que la cambie al ingresar."
        ),
        categoria="Correo",
        prioridad="BAJA",
        creado_por="diego.soto",
        solicitantes=("constanza.herrera",),
        ubicacion=MATTA,
        hace_dias=15,
        hora="12:15",
    ),
    DemoTicket(
        clave="switch-intermitencia",
        titulo="Intermitencia en el switch de la sucursal",
        descripcion=(
            "Se detectan caídas breves de red en varios puestos de la "
            "sucursal Lo Marcoleta durante el día (bodega y sala de ventas). "
            "Pendiente revisar puertos y cableado del switch del rack y "
            "cambiar el equipo si es necesario."
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="valentina.pizarro",
        ubicacion=MARCOLETA,
        hace_dias=9,
        hora="09:45",
    ),
    DemoTicket(
        clave="internet-lento-matta",
        titulo="Varios reclamos por internet lento",
        descripcion=(
            "Constanza y Javiera avisaron por separado que el internet va "
            "muy lento en la oficina Manuel Antonio Matta, sobre todo en la "
            "mañana. Se agrupan en un solo ticket para revisar el enlace y "
            "el wifi."
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="valentina.pizarro",
        solicitantes=("constanza.herrera", "javiera.torres"),
        ubicacion=MATTA,
        hace_dias=3,
        hora="10:20",
    ),
    DemoTicket(
        clave="monitor-sin-imagen",
        titulo="Monitor sin imagen",
        descripcion=(
            "Paula informa que su monitor 'se apagó' y no muestra nada, "
            "aunque el computador parece encendido (se escucha el "
            "ventilador). Verificar el cable de video y la fuente del "
            "monitor antes de cambiar equipos."
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="felipe.araya",
        solicitantes=("paula.contreras",),
        ubicacion=MATTA,
        hace_dias=19,
        hora="12:45",
    ),
    DemoTicket(
        clave="impresora-nueva-administracion",
        titulo="Instalación de impresora nueva en Administración",
        descripcion=(
            "Llegó la impresora multifuncional nueva para Administración. "
            "Falta instalarla, configurar el escaneo a carpeta y retirar la "
            "antigua."
        ),
        categoria="Impresoras",
        prioridad="BAJA",
        creado_por="felipe.araya",
        ubicacion=MATTA,
        hace_dias=26,
        hora="09:20",
    ),
    DemoTicket(
        clave="reposicion-toner-sucursal",
        titulo="Reposición de tóner en impresoras de la sucursal",
        descripcion=(
            "Revisión mensual: se detecta tóner bajo en tres impresoras. "
            "Reponer antes de que se agote y dejar un repuesto en bodega."
        ),
        categoria="Impresoras",
        prioridad="BAJA",
        creado_por="felipe.araya",
        ubicacion=MARCOLETA,
        hace_dias=38,
        hora="10:10",
    ),
    DemoTicket(
        clave="buzon-lleno",
        titulo="Usuario no puede enviar correos (buzón lleno)",
        descripcion=(
            "Ignacio no puede enviar ni recibir correos desde hace días: el "
            "buzón alcanzó su límite. Se le pidió depurar mensajes antiguos "
            "y archivar; pendiente ampliar la cuota si corresponde."
        ),
        categoria="Correo",
        prioridad="MEDIA",
        creado_por="francisca.munoz",
        solicitantes=("ignacio.molina",),
        ubicacion=MARCOLETA,
        hace_dias=17,
        hora="14:30",
    ),
    DemoTicket(
        clave="mantencion-preventiva",
        titulo="Mantención preventiva de equipos",
        descripcion=(
            "Plan trimestral de mantención preventiva (limpieza interna, "
            "actualizaciones y revisión de discos) de los equipos de la "
            "sucursal Lo Marcoleta. Se coordina por bloques para no detener "
            "la operación."
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="camila.rojas",
        ubicacion=MARCOLETA,
        hace_dias=44,
        hora="09:00",
    ),
    DemoTicket(
        clave="equipo-nuevo-proyectos",
        titulo="Solicitud de equipo nuevo para Proyectos",
        descripcion=(
            "Proyectos solicita un notebook con mayor capacidad para los "
            "planos 3D. Se evalúa cambiar el equipo de Andrés "
            "(sobrecalentamiento recurrente). Pendiente cotización."
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="camila.rojas",
        solicitantes=("andres.silva",),
        hace_dias=11,
        hora="16:00",
    ),
    DemoTicket(
        clave="respaldo-semanal-fallido",
        titulo="Respaldo semanal falló",
        descripcion=(
            "El respaldo automático del servidor de archivos terminó con "
            "errores en la última ejecución (no completó las carpetas de "
            "Administración y Finanzas). Revisar el espacio disponible y "
            "reintentar.\n"
            "Relacionado con la recuperación de archivos pedida por "
            "Administración."
        ),
        categoria="Sin clasificar",
        prioridad="ALTA",
        creado_por="matias.fuentes",
        hace_dias=7,
        hora="09:50",
    ),
    # --- Tickets con cambios de estado ---------------------------------------
    # Van al final a propósito: al volver a ejecutar el comando solo se crean
    # los que faltan (un ticket ya cargado no se modifica).
    DemoTicket(
        clave="vpn-clave-vencida",
        titulo="no puedo entrar a la vpn desde mi casa",
        descripcion=(
            "buenas, desde ayer no puedo conectarme a la vpn desde mi casa. "
            "me pide la clave y despues dice que es incorrecta pero es la "
            "misma de siempre!!\n"
            "necesito entrar para ver unos contratos que estan en la red de "
            "la oficina, es para hoy. gracias"
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="paula.contreras",
        hace_dias=9,
        hora="10:05",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=2,
                estado="INICIAR",
            ),
        ),
    ),
    DemoTicket(
        clave="monitor-parpadea",
        titulo="el monitor se apaga solo",
        descripcion=(
            "mi monitor se apaga solo como cada 10 minutos y despues vuelve. "
            "al principio pense que era el cable pero ya lo movi y sigue "
            "igual. no se si es el monitor o el computador.\n"
            "es el de la oficina del fondo, el que esta al lado de la "
            "impresora grande."
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="constanza.herrera",
        ubicacion=MATTA,
        hace_dias=14,
        hora="11:20",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=2,
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=6,
                estado="PONER_EN_ESPERA",
                motivo_espera="ESPERA_TERCERO",
            ),
        ),
    ),
    DemoTicket(
        clave="factura-electronica-error",
        titulo="el sistema no me deja emitir facturas",
        descripcion=(
            "cuando trato de emitir una factura electronica me sale un error "
            "rojo y no la emite. a mi companera le pasa lo mismo desde esta "
            "mañana. tenemos como 6 facturas pendientes de enviar a clientes "
            "y algunos ya llamaron preguntando."
        ),
        categoria="Sin clasificar",
        prioridad="ALTA",
        creado_por="javiera.torres",
        ubicacion=MATTA,
        hace_dias=6,
        hora="12:10",
        ajustes=(
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=1,
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=3,
                estado="PONER_EN_ESPERA",
                motivo_espera="INFORMACION_PENDIENTE",
            ),
        ),
    ),
    DemoTicket(
        clave="licencia-autocad",
        titulo="necesito el programa de planos en mi notebook nuevo",
        descripcion=(
            "me entregaron el notebook nuevo pero no tiene el programa de "
            "planos. en el otro lo tenia instalado hace años. lo necesito "
            "para el proyecto que parte el lunes, asi que si se puede lo "
            "antes posible."
        ),
        categoria="Sin clasificar",
        prioridad="MEDIA",
        creado_por="andres.silva",
        hace_dias=19,
        hora="15:25",
        ajustes=(
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=3,
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=4,
                estado="PONER_EN_ESPERA",
                motivo_espera="APROBACION_PENDIENTE",
            ),
        ),
    ),
    DemoTicket(
        clave="teclado-ventas",
        titulo="teclado con teclas que no funcionan",
        descripcion=(
            "al teclado se le pegan varias teclas (la e, la a y el espacio) "
            "y a veces escribe dos veces. ya le pase un paño pero sigue "
            "igual. con las ventas del dia no puedo andar copiando y "
            "pegando letras jaja"
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="sebastian.vargas",
        ubicacion=MARCOLETA,
        hace_dias=22,
        hora="09:35",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                estado="PONER_EN_ESPERA",
                motivo_espera="RECURSO_PENDIENTE",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=10,
                estado="REACTIVAR",
            ),
        ),
    ),
    DemoTicket(
        clave="wifi-bodega",
        titulo="el wifi de la bodega se cae todo el dia",
        descripcion=(
            "el wifi de la bodega se cae todo el dia y no podemos usar las "
            "pistolas para registrar la mercaderia. tenemos que anotar todo "
            "a mano y despues pasarlo, se pierde mucho tiempo.\n"
            "es urgente porque llegan camiones el jueves."
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=5,
        hora="13:45",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=1,
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=5,
                estado="PONER_EN_ESPERA",
                motivo_espera="OTRO",
                texto=(
                    "Hay que esperar la visita del proveedor de internet a la "
                    "bodega, agendada para el jueves en la mañana."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="correo-reenvio-vacaciones",
        titulo="como configuro que mi correo se reenvie mientras estoy de vacaciones",
        descripcion=(
            "me voy de vacaciones dos semanas y quiero que mis correos le "
            "lleguen a mi jefe mientras no estoy. no se donde se configura "
            "eso en el correo nuevo, lo busque y no lo encuentro."
        ),
        categoria="Correo",
        prioridad="BAJA",
        creado_por="sebastian.vargas",
        hace_dias=2,
        hora="16:40",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=1,
                estado="INICIAR",
            ),
        ),
    ),
    DemoTicket(
        clave="impresora-finanzas-atascada",
        titulo="Impresora de Finanzas se atasca al imprimir en doble cara",
        descripcion=(
            "Javiera informa que la impresora de Finanzas se atasca cada "
            "vez que imprime en doble cara. Ya se limpiaron los rodillos y "
            "se cambió el papel, sin resultado. Se revisa el modo dúplex."
        ),
        categoria="Impresoras",
        prioridad="MEDIA",
        creado_por="felipe.araya",
        solicitantes=("javiera.torres",),
        ubicacion=MATTA,
        hace_dias=4,
        hora="10:50",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                estado="INICIAR",
            ),
        ),
    ),
    # --- Tickets con grupo y asignación ---------------------------------------
    DemoTicket(
        clave="disco-lleno-servidor",
        titulo="Servidor de archivos con el disco casi lleno",
        descripcion=(
            "El servidor de archivos llegó al 94 % de uso. Hay carpetas de "
            "proyectos antiguos que ocupan mucho espacio y los respaldos "
            "nocturnos están empezando a fallar. Hay que depurar o ampliar "
            "el disco antes de que se llene."
        ),
        categoria="Sin clasificar",
        prioridad="MEDIA",
        creado_por="matias.fuentes",
        hace_dias=10,
        hora="11:30",
        ajustes=(
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=2,
                grupo="Soporte Redes",
                asignar="valentina.pizarro",
            ),
        ),
    ),
    DemoTicket(
        clave="teams-no-conecta",
        titulo="no me conecto a las reuniones de teams",
        descripcion=(
            "desde hoy cuando entro a una reunion de teams se queda cargando "
            "y despues me saca. con el celular si funciona. tengo reunion "
            "con un cliente en la tarde, por favor"
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="sebastian.vargas",
        hace_dias=3,
        hora="12:40",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=1,
                asignar="diego.soto",
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=2,
                estado="INICIAR",
            ),
        ),
    ),
    DemoTicket(
        clave="mouse-inalambrico",
        titulo="el mouse inalambrico se desconecta solo",
        descripcion=(
            "el mouse se desconecta cada rato y tengo que sacar y poner "
            "de nuevo el aparatito del USB. ya le cambie las pilas. a mi "
            "compañera de al lado le pasa lo mismo con el suyo."
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="paula.contreras",
        hace_dias=16,
        hora="10:25",
        ajustes=(
            DemoAdjustment(
                actor="matias.fuentes",
                despues_horas=3,
                grupo="Soporte Usuarios",
                asignar="felipe.araya",
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=4,
                asignar="diego.soto",
            ),
        ),
    ),
    DemoTicket(
        clave="sistema-contable-lento",
        titulo="el sistema contable esta lentisimo",
        descripcion=(
            "el sistema contable se demora como un minuto en abrir cada "
            "pantalla desde ayer. a todo el equipo de finanzas nos pasa. "
            "estamos con el cierre del mes y no podemos avanzar."
        ),
        categoria="Sin clasificar",
        prioridad="ALTA",
        creado_por="javiera.torres",
        ubicacion=MATTA,
        hace_dias=7,
        hora="14:15",
        ajustes=(
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=1,
                grupo="Aplicaciones",
            ),
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=1,
                asignar="francisca.munoz",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=5,
                estado="PONER_EN_ESPERA",
                motivo_espera="ESPERA_TERCERO",
            ),
        ),
    ),
    DemoTicket(
        clave="cobertura-wifi-reuniones",
        titulo="Cobertura wifi insuficiente en la sala de reuniones",
        descripcion=(
            "Se reporta que en la sala de reuniones del segundo piso la "
            "señal wifi es muy débil y se cortan las videollamadas. Se deriva "
            "al grupo de redes para evaluar un punto de acceso adicional."
        ),
        categoria="Redes",
        prioridad="MEDIA",
        creado_por="camila.rojas",
        solicitantes=("andres.silva",),
        ubicacion=MARCOLETA,
        hace_dias=5,
        hora="15:10",
        ajustes=(
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=1,
                grupo="Soporte Redes",
            ),
        ),
    ),
    DemoTicket(
        clave="respaldo-notebook",
        titulo="quiero respaldar mi notebook antes de que lo cambien",
        descripcion=(
            "me dijeron que me van a cambiar el notebook la proxima semana "
            "y tengo cosas importantes guardadas en el. como hago para no "
            "perder nada? gracias"
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=4,
        hora="09:45",
        ajustes=(
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=2,
                asignar="valentina.pizarro",
            ),
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=3,
                estado="INICIAR",
            ),
        ),
    ),
    # --- Tickets con solicitantes agregados y retirados -----------------------
    DemoTicket(
        clave="proyector-sala-chica",
        titulo="Proyector de la sala chica no muestra imagen",
        descripcion=(
            "Constanza llamó por teléfono: el proyector de la sala chica "
            "enciende, pero no muestra imagen cuando se conecta un notebook. "
            "Se registra a su nombre mientras se confirma quién tiene "
            "reservada la sala."
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="felipe.araya",
        solicitantes=("constanza.herrera",),
        ubicacion=MARCOLETA,
        hace_dias=6,
        hora="10:05",
        ajustes=(
            # Se asoció a la persona equivocada: se corrige.
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                retirar_solicitante="constanza.herrera",
                motivo_retiro=(
                    "Constanza solo avisó por teléfono; la sala la tenía "
                    "reservada Paula."
                ),
                agregar_solicitante="paula.contreras",
            ),
        ),
    ),
    DemoTicket(
        clave="ups-bodega-mantencion",
        titulo="Mantención preventiva de la UPS de la bodega",
        descripcion=(
            "Mantención semestral de la UPS de la bodega: revisar las "
            "baterías, limpiar los filtros y probar la autonomía con un corte "
            "simulado. Es una tarea interna del equipo de infraestructura, "
            "por eso nace sin solicitante."
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="valentina.pizarro",
        ubicacion=MARCOLETA,
        hace_dias=9,
        hora="09:30",
        ajustes=(
            # El jefe de bodega pide que lo mantengan informado.
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=3,
                agregar_solicitante="ignacio.molina",
            ),
        ),
    ),
    DemoTicket(
        clave="vpn-se-corta",
        titulo="VPN que se corta cada pocos minutos",
        descripcion=(
            "Sebastián se conecta a la VPN desde su casa y a los pocos "
            "minutos se corta y tiene que volver a entrar. Ya reinició el "
            "computador y el router sin resultado."
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="matias.fuentes",
        solicitantes=("sebastian.vargas",),
        hace_dias=5,
        hora="11:20",
        ajustes=(
            # Otra persona reporta lo mismo y se suma al ticket...
            DemoAdjustment(
                actor="matias.fuentes",
                despues_horas=1,
                agregar_solicitante="andres.silva",
            ),
            # ...pero después se comprueba que su problema era otro.
            DemoAdjustment(
                actor="matias.fuentes",
                despues_horas=6,
                retirar_solicitante="andres.silva",
                motivo_retiro="Su problema era otro y se atendió por separado.",
            ),
        ),
    ),
    DemoTicket(
        clave="impresora-proyectos-a-nombre-de",
        titulo="la impresora de proyectos dice error de conexion",
        descripcion=(
            "hola, escribo yo porque andres esta en terreno y no tiene "
            "tiempo. la impresora de la oficina de proyectos no imprime "
            "desde ayer, sale un cartel de 'error de conexion'. el necesita "
            "imprimir unos planos para el jueves."
        ),
        categoria="Impresoras",
        prioridad="MEDIA",
        creado_por="constanza.herrera",
        ubicacion=MARCOLETA,
        hace_dias=2,
        hora="14:50",
        ajustes=(
            # Quien creó el ticket deja de ser solicitante, pero lo sigue
            # viendo: el creador original no cambia.
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=2,
                retirar_solicitante="constanza.herrera",
                motivo_retiro=(
                    "Quien usa la impresora es Andrés; Constanza solo creó "
                    "el ticket."
                ),
                agregar_solicitante="andres.silva",
            ),
        ),
    ),
    # --- Tickets con comentarios y notas internas -----------------------------
    DemoTicket(
        clave="intranet-credenciales",
        titulo="no puedo entrar a la intranet de ventas",
        descripcion=(
            "desde esta mañana la intranet me dice «credenciales invalidas». "
            "no cambie nada, ayer entre sin problema. necesito subir unos "
            "pedidos antes del mediodia"
        ),
        categoria="Sin clasificar",
        prioridad="ALTA",
        creado_por="sebastian.vargas",
        hace_dias=4,
        hora="10:15",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                asignar="felipe.araya",
                estado="INICIAR",
                comentario=(
                    "Hola Sebastián, soy Felipe de soporte. ¿Cambiaste tu "
                    "contraseña de Windows esta semana? A veces la intranet "
                    "se queda con la anterior."
                ),
            ),
            # El Solicitante también comenta, desde su propio ticket.
            DemoAdjustment(
                actor="sebastian.vargas",
                despues_horas=2,
                comentario=(
                    "Si, la cambie el lunes porque el correo me lo pidio. "
                    "¿Es por eso?"
                ),
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                nota_interna=(
                    "La intranet sincroniza las credenciales con el directorio "
                    "cada 24 h. Forzar la sincronización desde el panel de "
                    "administración."
                ),
                comentario=(
                    "Sí, es por eso. Ya forzamos la sincronización: prueba "
                    "entrar de nuevo en unos 10 minutos y me cuentas."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="teclado-derrame-rrhh",
        titulo="se me cayo cafe al teclado",
        descripcion=(
            "se me cayo cafe en el teclado y algunas teclas se quedan pegadas. "
            "lo limpie con una toalla pero sigue igual. ¿me lo pueden cambiar?"
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="paula.contreras",
        hace_dias=6,
        hora="15:30",
        ajustes=(
            # Una respuesta pública y una nota que el solicitante no ve.
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=2,
                comentario=(
                    "Hola Paula, no te preocupes, pasa seguido. Te dejamos un "
                    "teclado de reemplazo en tu escritorio esta tarde."
                ),
                nota_interna=(
                    "Tercer teclado de RRHH este trimestre. Sacar uno del stock "
                    "de reserva y avisar a Camila para ver si conviene comprar "
                    "teclados lavables."
                ),
            ),
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=3,
                nota_interna=(
                    "Anotado. Con la compra de diciembre pedimos teclados "
                    "lavables para las oficinas con más derrames."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="licencia-office-constanza",
        titulo="Licencia de Office de Constanza vencida",
        descripcion=(
            "Constanza informa que Excel le muestra «producto sin licencia». "
            "Se registra para revisar la asignación de licencias del área de "
            "Administración."
        ),
        categoria="Sin clasificar",
        prioridad="MEDIA",
        creado_por="matias.fuentes",
        solicitantes=("constanza.herrera",),
        hace_dias=3,
        hora="12:05",
        ajustes=(
            DemoAdjustment(
                actor="constanza.herrera",
                despues_horas=1,
                comentario=(
                    "Hola, lo de Excel me sigue pasando. Ayer a las 17:00 aún "
                    "funcionaba."
                ),
            ),
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=2,
                asignar="francisca.munoz",
                estado="INICIAR",
                nota_interna=(
                    "La licencia quedó asociada al notebook anterior: el "
                    "inventario no se actualizó cuando se lo cambiaron."
                ),
                comentario=(
                    "Constanza, encontramos el problema: la licencia quedó "
                    "asociada al equipo anterior. La reasignamos hoy y se "
                    "activa sola al abrir Excel."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="switch-bodega-puertos",
        titulo="Switch de la bodega con puertos intermitentes",
        descripcion=(
            "Ignacio reporta cortes de red de pocos segundos en la bodega, "
            "sobre todo en los puestos de despacho. Se revisa el switch de la "
            "sala técnica."
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="diego.soto",
        solicitantes=("ignacio.molina",),
        ubicacion=MARCOLETA,
        hace_dias=2,
        hora="09:40",
        ajustes=(
            # Dos notas del equipo y un solo comentario público: Ignacio ve
            # únicamente el último.
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=2,
                nota_interna=(
                    "Logs del switch: errores CRC en los puertos 3 y 4, casi "
                    "seguro cableado. Hay cable de repuesto en el pañol de TI."
                ),
            ),
            DemoAdjustment(
                actor="matias.fuentes",
                despues_horas=3,
                nota_interna=(
                    "Programar el cambio para el jueves temprano. Que Diego "
                    "avise a Ignacio para coordinar con el despacho."
                ),
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=1,
                comentario=(
                    "Hola Ignacio, el jueves en la mañana vamos a cambiar unos "
                    "cables en la bodega. Puede haber cortes de un par de "
                    "minutos; te avisamos antes de empezar."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="wifi-visitas-clave",
        titulo="la clave del wifi de visitas no funciona",
        descripcion=(
            "vienen unos auditores el jueves y la clave del wifi de visitas "
            "que tenia anotada no les funciona. ¿me pueden dar la nueva?"
        ),
        categoria="Redes",
        prioridad="MEDIA",
        creado_por="javiera.torres",
        ubicacion=MATTA,
        hace_dias=1,
        hora="16:20",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                comentario=(
                    "Hola Javiera, la clave de visitas cambia cada mes. Te la "
                    "paso en un rato, ¿cuántas personas van a conectarse?"
                ),
            ),
            DemoAdjustment(
                actor="javiera.torres",
                despues_horas=1,
                comentario="Serían cuatro personas, desde las 9 del jueves.",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                comentario=(
                    "Perfecto. Te dejamos cuatro accesos temporales para el "
                    "jueves; el detalle te lo entrego mañana en persona."
                ),
                nota_interna=(
                    "Crear 4 accesos temporales en el portal de invitados, "
                    "vigencia 12 h."
                ),
            ),
        ),
    ),
    # --- Tickets con archivos adjuntos ----------------------------------------
    DemoTicket(
        clave="error-sistema-contable-log",
        titulo="el sistema contable se cierra solo al guardar",
        descripcion=(
            "cuando guardo un asiento el sistema contable se cierra sin avisar. "
            "me pidieron que adjuntara el archivo de errores, aqui va"
        ),
        categoria="Sin clasificar",
        prioridad="ALTA",
        creado_por="javiera.torres",
        ubicacion=MATTA,
        hace_dias=3,
        hora="11:40",
        ajustes=(
            # Un Solicitante adjunta un archivo a su comentario.
            DemoAdjustment(
                actor="javiera.torres",
                despues_horas=1,
                comentario="Adjunto el archivo de errores que genera el programa.",
                adjunto=(
                    "errores-contabilidad.log",
                    (
                        "2026-11-17 11:36:02 ERROR  Guardar asiento 4471: acceso denegado\n"
                        "2026-11-17 11:36:02 ERROR  El proceso terminó de forma inesperada\n"
                    ),
                ),
            ),
            # La nota interna del equipo lleva su propio archivo, que el
            # Solicitante no ve.
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=2,
                asignar="francisca.munoz",
                estado="INICIAR",
                nota_interna="Es un permiso: la carpeta compartida cambió de servidor. Dejo el diagnóstico.",
                adjunto=(
                    "diagnostico-permisos.txt",
                    "Usuario: javiera.torres\nCarpeta: \\\\srv-archivos\\contabilidad\nPermiso actual: solo lectura\nPermiso esperado: modificar\n",
                ),
                comentario="Javiera, ya encontramos la causa: te faltaba un permiso en la carpeta. Prueba de nuevo y me cuentas.",
            ),
        ),
    ),
    DemoTicket(
        clave="inventario-notebooks-csv",
        titulo="Inventario de notebooks para el cambio de equipos",
        descripcion=(
            "Se prepara el cambio de notebooks del área comercial. Se adjunta "
            "la lista de equipos que se reemplazan."
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="matias.fuentes",
        solicitantes=("sebastian.vargas",),
        hace_dias=5,
        hora="14:10",
        ajustes=(
            # Un archivo del ticket, sin comentario.
            DemoAdjustment(
                actor="matias.fuentes",
                despues_horas=1,
                adjunto=(
                    "notebooks-a-reemplazar.csv",
                    "usuario,equipo,antiguedad_anos\nsebastian.vargas,NB-0412,5\nandres.silva,NB-0377,6\n",
                ),
            ),
        ),
    ),
    # --- Tickets con resolución, cierre y reapertura --------------------------
    # Resuelto y pendiente de que la solicitante responda: ella ve el aviso
    # «¿Tu solicitud quedó resuelta?» al abrirlo.
    DemoTicket(
        clave="lector-huella-no-reconoce",
        titulo="el lector de huella de la entrada no me reconoce",
        descripcion=(
            "desde ayer el lector de huella de la entrada no me deja marcar, "
            "dice huella no valida. antes funcionaba bien"
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="paula.contreras",
        ubicacion=MARCOLETA,
        hace_dias=3,
        hora="09:40",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                asignar="felipe.araya",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                estado="RESOLVER",
                texto=(
                    "Limpié el lector y volví a registrar tu huella. Prueba "
                    "mañana a primera hora y me avisas si falla."
                ),
            ),
        ),
    ),
    # Resuelto y confirmado por quien lo pidió: se cierra con el motivo
    # «Resolución validada».
    DemoTicket(
        clave="cargador-notebook-bodega",
        titulo="el cargador del notebook ya no carga",
        descripcion=(
            "el notebook de la bodega se queda sin bateria porque el cargador "
            "ya no hace nada, la luz no prende. lo necesito para el inventario"
        ),
        categoria="Hardware",
        prioridad="ALTA",
        creado_por="ignacio.molina",
        hace_dias=5,
        hora="10:15",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=1,
                asignar="diego.soto",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=3,
                estado="RESOLVER",
                texto="Cambié el cargador por uno nuevo y probé que cargue.",
            ),
            DemoAdjustment(
                actor="ignacio.molina",
                despues_horas=2,
                estado="CONFIRMAR",
                texto="Listo, ya carga. Gracias!",
            ),
        ),
    ),
    # La solución no alcanzó: el solicitante la rechaza, el ticket vuelve a En
    # progreso y se resuelve por segunda vez (segundo ciclo de resolución).
    DemoTicket(
        clave="escritorio-remoto-rechazado",
        titulo="no puedo entrar al escritorio remoto del trabajo",
        descripcion=(
            "estoy en la casa y no logro conectarme al escritorio remoto del "
            "trabajo, me da error de credenciales. mañana tengo una "
            "presentacion y necesito mis archivos"
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="sebastian.vargas",
        hace_dias=6,
        hora="15:30",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=1,
                asignar="valentina.pizarro",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=2,
                estado="RESOLVER",
                texto="Habilité tu usuario en el servidor de escritorio remoto.",
            ),
            DemoAdjustment(
                actor="sebastian.vargas",
                despues_horas=3,
                estado="RECHAZAR",
                texto="Sigo sin poder entrar, ahora me pide una clave que no tengo.",
            ),
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=1,
                comentario="Entiendo, te llamo para revisarlo contigo por teléfono.",
                nota_interna=(
                    "La clave del servidor expiró; hay que restablecerla en el "
                    "directorio, no solo habilitar el usuario."
                ),
            ),
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=2,
                estado="RESOLVER",
                texto=(
                    "Restablecí la clave del servidor y lo probamos juntos por "
                    "teléfono: ya entras."
                ),
            ),
        ),
    ),
    # Cierre directo sin solicitante: una mantención rutinaria no pasa por la
    # validación de nadie.
    DemoTicket(
        clave="aire-sala-servidores-mensual",
        titulo="Revisión mensual del aire acondicionado de la sala de servidores",
        descripcion=(
            "Revisión mensual programada del aire acondicionado de la sala de "
            "servidores: filtros, temperatura y drenaje."
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="matias.fuentes",
        hace_dias=4,
        hora="09:20",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=3,
                estado="CIERRE_DIRECTO",
                texto="Revisión hecha según el calendario, sin hallazgos.",
            ),
        ),
    ),
    # Una cancelación no es un estado: es un cierre directo con ese motivo.
    DemoTicket(
        clave="segundo-monitor-cancelado",
        titulo="ya no necesito el segundo monitor",
        descripcion=(
            "pedi un segundo monitor para mi puesto pero con el cambio de "
            "oficina ya no lo voy a usar. cancelen la solicitud porfa"
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="constanza.herrera",
        ubicacion=MATTA,
        hace_dias=2,
        hora="12:05",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                comentario=(
                    "Constanza, anulamos la solicitud entonces. Si lo vuelves a "
                    "necesitar nos avisas."
                ),
                estado="CIERRE_DIRECTO",
                motivo_cierre="CANCELACION",
                texto="Cancelado a pedido de la solicitante.",
            ),
        ),
    ),
    # Resuelto sin solicitante: nadie puede confirmar y el cierre automático
    # llega en otra versión, así que lo cierra un Supervisor.
    DemoTicket(
        clave="antivirus-notebooks-bodega",
        titulo="Actualización de antivirus en los notebooks de la bodega",
        descripcion=(
            "Actualizar el antivirus en los 8 notebooks de la bodega a la "
            "última versión. No requiere intervención de los usuarios."
        ),
        categoria="Hardware",
        prioridad="BAJA",
        creado_por="matias.fuentes",
        hace_dias=6,
        hora="11:00",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                asignar="felipe.araya",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=4,
                estado="RESOLVER",
                texto="Antivirus actualizado en los 8 notebooks.",
            ),
            DemoAdjustment(
                actor="camila.rojas",
                despues_horas=9,
                estado="CIERRE_EXCEPCIONAL",
                texto="Sin solicitante que valide; se cierra por el equipo.",
            ),
        ),
    ),
    # Se cerró bien, pero el problema volvió: el personal lo reabre y la
    # solicitante explica con un comentario público.
    DemoTicket(
        clave="impresora-contratos-rayas",
        titulo="la impresora de contratos imprime con rayas",
        descripcion=(
            "los contratos salen con una raya negra a lo largo de la hoja. "
            "necesito imprimir varios para firmar esta semana"
        ),
        categoria="Impresoras",
        prioridad="MEDIA",
        creado_por="paula.contreras",
        ubicacion=MARCOLETA,
        hace_dias=6,
        hora="14:45",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                asignar="felipe.araya",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                estado="RESOLVER",
                texto="Cambié el cartucho de tóner y limpié el tambor.",
            ),
            DemoAdjustment(
                actor="paula.contreras",
                despues_horas=2,
                estado="CONFIRMAR",
                texto="Quedó perfecta.",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=9,
                estado="REABRIR",
            ),
            DemoAdjustment(
                actor="paula.contreras",
                despues_horas=1,
                comentario=(
                    "Hoy volvió a imprimir con rayas, no sé si es el mismo "
                    "problema."
                ),
            ),
        ),
    ),
    # --- Tickets con duplicados y relaciones ----------------------------------
    # Dos tickets que repiten uno que ya existía (el principal, `wifi-bodega`):
    # el personal los marca como duplicados y se cierran con el motivo
    # «Duplicado». Quien los pidió ve el cierre; las relaciones, solo el personal.
    DemoTicket(
        clave="wifi-bodega-otra-vez",
        titulo="otra vez sin wifi en la bodega",
        descripcion=(
            "otra vez se cayo el wifi de la bodega y no funcionan las pistolas. "
            "ya van varios dias asi, necesitamos que alguien lo arregle"
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=3,
        hora="10:25",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=2,
                comentario=(
                    "Ignacio, esto ya lo estamos viendo en otro ticket: el "
                    "proveedor visita la bodega el jueves. Lo unimos con ese."
                ),
                duplicado_de="wifi-bodega",
            ),
        ),
    ),
    DemoTicket(
        clave="internet-bodega-sigue-mal",
        titulo="sigue sin funcionar el internet de la bodega",
        descripcion=(
            "el internet de la bodega sigue con problemas, se corta cada rato. "
            "avisen cuando lo arreglen porfa"
        ),
        categoria="Redes",
        prioridad="MEDIA",
        creado_por="ignacio.molina",
        ubicacion=MARCOLETA,
        hace_dias=1,
        hora="09:50",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=1,
                nota_interna="Mismo problema que el ticket del wifi de la bodega.",
                duplicado_de="wifi-bodega",
            ),
        ),
    ),
    # Tickets relacionados (sin ser duplicados): siguen abiertos y se enlazan
    # entre sí; el enlace lo ve el personal.
    DemoTicket(
        clave="impresora-notebook-nuevo",
        titulo="no puedo imprimir desde mi notebook nuevo",
        descripcion=(
            "con el notebook nuevo no logro imprimir en la impresora de "
            "proyectos, me aparece que no hay drivers"
        ),
        categoria="Impresoras",
        prioridad="MEDIA",
        creado_por="andres.silva",
        hace_dias=1,
        hora="10:30",
        ajustes=(
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=1,
                asignar="francisca.munoz",
                estado="INICIAR",
                relacionar="impresora-proyectos-a-nombre-de",
                nota_interna=(
                    "Puede ser lo mismo que el error de conexión de la "
                    "impresora de proyectos: reviso los dos juntos."
                ),
            ),
        ),
    ),
    DemoTicket(
        clave="wifi-reuniones-sigue-cayendo",
        titulo="el wifi de la sala de reuniones sigue cayéndose",
        descripcion=(
            "en la sala de reuniones el wifi se cae cuando hay mas de cinco "
            "personas conectadas. pasa en cada reunion con clientes"
        ),
        categoria="Redes",
        prioridad="MEDIA",
        creado_por="sebastian.vargas",
        ubicacion=MATTA,
        hace_dias=2,
        hora="16:10",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=1,
                relacionar="cobertura-wifi-reuniones",
                comentario=(
                    "Sebastián, lo estamos revisando junto con la cobertura "
                    "de la sala: parece ser lo mismo."
                ),
            ),
        ),
    ),
    # Tickets para los dashboards: cada Solicitante con solicitudes que esperan su
    # revisión, cierres recientes y tickets en progreso.
    DemoTicket(
        clave="correo-jefatura-no-llega",
        titulo="no me llega el correo de la jefatura",
        descripcion=(
            "desde ayer no recibo los correos de mi jefatura, los demas si llegan. necesito esos para la reunion"
        ),
        categoria="Correo",
        prioridad="MEDIA",
        creado_por="javiera.torres",
        hace_dias=2,
        hora="09:30",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=1,
                asignar="diego.soto",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=3,
                estado="RESOLVER",
                texto="Estaba en la carpeta de correo no deseado por una regla vieja. La borré y ya te llegan; revisa y me cuentas.",
            ),
        ),
    ),
    DemoTicket(
        clave="mouse-oficina-contabilidad",
        titulo="el mouse de mi puesto salta solo",
        descripcion=(
            "el cursor se mueve solo y hace clic donde quiere, ya me equivoque dos veces en un pago"
        ),
        categoria="Hardware",
        prioridad="ALTA",
        creado_por="sebastian.vargas",
        hace_dias=1,
        hora="10:05",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                asignar="felipe.araya",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=3,
                estado="RESOLVER",
                texto="Cambié el mouse por uno nuevo y probé en tu equipo. Avísame si vuelve a pasar.",
            ),
        ),
    ),
    DemoTicket(
        clave="impresora-contabilidad-atasco",
        titulo="la impresora de contabilidad se traba con la hoja",
        descripcion=(
            "cada vez que imprimo mas de tres hojas se atasca y hay que apagarla. ya limpie lo que pude"
        ),
        categoria="Impresoras",
        prioridad="MEDIA",
        creado_por="constanza.herrera",
        hace_dias=2,
        hora="11:15",
        ajustes=(
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=1,
                asignar="francisca.munoz",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=3,
                estado="RESOLVER",
                texto="Limpié los rodillos y cambié el papel que estaba húmedo. Probé con veinte hojas sin problema.",
            ),
        ),
    ),
    DemoTicket(
        clave="vpn-casa-no-conecta",
        titulo="no puedo conectarme a la red desde mi casa",
        descripcion=(
            "estoy en teletrabajo y no logro entrar a los archivos compartidos, me dice que no encuentra el servidor"
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="ignacio.molina",
        hace_dias=1,
        hora="14:20",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=1,
                asignar="valentina.pizarro",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=3,
                estado="RESOLVER",
                texto="Faltaba renovar tu acceso remoto. Ya quedó activo: cierra sesión, vuelve a entrar y dime si carga.",
            ),
        ),
    ),
    DemoTicket(
        clave="firma-correo-desactualizada",
        titulo="mi firma del correo sale con el cargo antiguo",
        descripcion=(
            "mande un correo a un cliente y la firma dice el cargo que tenia el año pasado, quede mal"
        ),
        categoria="Correo",
        prioridad="BAJA",
        creado_por="paula.contreras",
        hace_dias=3,
        hora="15:40",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=1,
                asignar="diego.soto",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=3,
                estado="RESOLVER",
                texto="Actualicé tu firma con el cargo nuevo. Envíate un correo de prueba para confirmar que se ve bien.",
            ),
        ),
    ),
    DemoTicket(
        clave="teclado-recepcion-teclas",
        titulo="el teclado de recepcion tiene teclas que no responden",
        descripcion=(
            "la e y la o a veces no escriben, hay que apretar fuerte. los clientes se dan cuenta"
        ),
        categoria="Hardware",
        prioridad="MEDIA",
        creado_por="andres.silva",
        hace_dias=2,
        hora="16:30",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                asignar="felipe.araya",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=3,
                estado="RESOLVER",
                texto="Cambié el teclado por otro y dejé el antiguo para repuestos. Pruébalo y me avisas.",
            ),
        ),
    ),
    DemoTicket(
        clave="scanner-bodega-no-envia",
        titulo="el scanner no manda los documentos al correo",
        descripcion=(
            "escaneo y aparece que se envio pero no llega nada a mi correo, lo hice tres veces"
        ),
        categoria="Impresoras",
        prioridad="MEDIA",
        creado_por="javiera.torres",
        hace_dias=4,
        hora="09:10",
        ajustes=(
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=1,
                asignar="francisca.munoz",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="francisca.munoz",
                despues_horas=3,
                estado="RESOLVER",
                texto="Cambié la dirección de destino del escáner y probé con tu correo; ya debería llegar.",
            ),
            DemoAdjustment(
                actor="javiera.torres",
                despues_horas=2,
                estado="CONFIRMAR",
                texto="Perfecto, ya me llegan los escaneos. Gracias!",
            ),
        ),
    ),
    DemoTicket(
        clave="wifi-sala-capacitacion",
        titulo="el wifi de la sala de capacitacion es lentisimo",
        descripcion=(
            "con el proyector y el notebook conectados no carga ni una presentacion, la capacitacion se atraso"
        ),
        categoria="Redes",
        prioridad="ALTA",
        creado_por="sebastian.vargas",
        hace_dias=3,
        hora="12:00",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=1,
                asignar="valentina.pizarro",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=3,
                estado="RESOLVER",
                texto="Moví el punto de acceso a la sala y reinicié el router. Prueba con la presentación.",
            ),
            DemoAdjustment(
                actor="sebastian.vargas",
                despues_horas=2,
                estado="CONFIRMAR",
                texto="Ahora sí, ya carga todo. Muchas gracias por la ayuda rápida.",
            ),
        ),
    ),
    DemoTicket(
        clave="notebook-sin-bateria",
        titulo="mi notebook se apaga a los veinte minutos",
        descripcion=(
            "esta enchufado igual se apaga, a veces ni prende. tengo que presentar manana"
        ),
        categoria="Hardware",
        prioridad="ALTA",
        creado_por="constanza.herrera",
        hace_dias=5,
        hora="10:40",
        ajustes=(
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=1,
                asignar="diego.soto",
                estado="INICIAR",
            ),
            DemoAdjustment(
                actor="diego.soto",
                despues_horas=3,
                estado="RESOLVER",
                texto="Cambié el cargador y la batería no estaba dañada. Verifica que cargue al 100%.",
            ),
            DemoAdjustment(
                actor="constanza.herrera",
                despues_horas=2,
                estado="CONFIRMAR",
                texto="Listo, funciona con el cargador nuevo. Gracias por el cambio.",
            ),
        ),
    ),
    DemoTicket(
        clave="casilla-correo-llena",
        titulo="dice que mi casilla de correo esta llena",
        descripcion=(
            "no puedo recibir ni enviar nada, ya borre cosas pero sigue igual"
        ),
        categoria="Correo",
        prioridad="MEDIA",
        creado_por="ignacio.molina",
        hace_dias=1,
        hora="11:50",
        ajustes=(
            DemoAdjustment(
                actor="felipe.araya",
                despues_horas=1,
                asignar="felipe.araya",
                estado="INICIAR",
            ),
        ),
    ),
    DemoTicket(
        clave="red-oficina-intermitente",
        titulo="el internet de mi oficina se corta cada tanto",
        descripcion=(
            "cada diez o quince minutos se va el internet y vuelve solo, no puedo hacer videollamadas"
        ),
        categoria="Redes",
        prioridad="MEDIA",
        creado_por="andres.silva",
        hace_dias=1,
        hora="15:10",
        ajustes=(
            DemoAdjustment(
                actor="valentina.pizarro",
                despues_horas=1,
                asignar="valentina.pizarro",
                estado="INICIAR",
            ),
        ),
    ),
)
