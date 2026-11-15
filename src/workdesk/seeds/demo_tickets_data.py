"""Datos de demostración: tickets de soporte TI.

Este archivo es SOLO datos. La lógica que los carga está en `demo_tickets.py`;
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
- Qué días y horas son laborales lo define `DEMO_CALENDAR` (más abajo):
  por defecto, de lunes a viernes de 09:00 a 18:00 y sin feriados. Se
  puede cambiar sin tocar el código que carga los datos. Ningún ticket ni
  ningún ajuste cae fuera de ese calendario.
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

Cuando existan estados, asignaciones, cierres y comentarios, se añadirán
campos opcionales a `DemoTicket` (con valor por defecto) y los tickets ya
escritos seguirán siendo válidos.
"""

from dataclasses import dataclass
from datetime import date

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
class WorkCalendar:
    """Días y horas laborales con los que se fechan los tickets demo.

    - `dias`: números de día de la semana, de 0 (lunes) a 6 (domingo).
    - `inicio` y `fin`: jornada en formato HH:MM; `fin` no se incluye (un
      ticket puede crearse a las 17:59, no a las 18:00).
    - `feriados`: fechas que no son laborales aunque caigan en un día laboral.

    Cuando exista el calendario laboral administrable del proyecto (llega con
    el SLA, en `v0.5.0`), el motor deberá leerlo de la base de datos; esta
    constante quedará como respaldo.
    """

    dias: tuple[int, ...] = (0, 1, 2, 3, 4)
    inicio: str = "09:00"
    fin: str = "18:00"
    feriados: tuple[date, ...] = ()


DEMO_CALENDAR = WorkCalendar()


@dataclass(frozen=True)
class DemoAdjustment:
    """Un paso posterior del personal sobre un ticket ya creado.

    `despues_horas` son horas laborales desde el paso anterior. Debe cambiar
    algo: título, descripción, categoría o prioridad. Cambiar la prioridad
    exige `motivo`.
    """

    actor: str
    despues_horas: int
    titulo: str | None = None
    descripcion: str | None = None
    categoria: str | None = None
    prioridad: str | None = None
    motivo: str | None = None


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
)
