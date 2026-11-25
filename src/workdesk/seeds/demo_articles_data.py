"""Los artículos de demostración (datos; la lógica está en `demo_articles.py`).

Escritos como los escribiría un equipo de soporte para gente que no es técnica. Cubren cada
caso que la base de conocimiento distingue: publicados y borradores, públicos y privados,
destacados y de distintas categorías.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoArticle:
    title: str
    category: str
    author: str
    content: str
    # Hace cuántos días se publicó; None = es un borrador.
    published_days_ago: int | None
    public: bool = True
    featured: bool = False


DEMO_ARTICLES = (
    DemoArticle(
        title="La impresora no imprime: qué revisar antes de pedir ayuda",
        category="Impresoras",
        author="felipe.araya",
        published_days_ago=2,
        featured=True,
        content=(
            "Antes de crear un ticket, comprueba estos puntos:\n\n"
            "1. La impresora está encendida y sin luces de error.\n"
            "2. Hay papel en la bandeja y no hay hojas atascadas.\n"
            "3. Estás imprimiendo en la impresora correcta (revisa el nombre).\n"
            "4. Cancela los trabajos pendientes de la cola de impresión y vuelve a probar.\n\n"
            "Si nada de esto resuelve el problema, crea un ticket e indica el nombre de la "
            "impresora y el mensaje que aparece."
        ),
    ),
    DemoArticle(
        title="Cómo conectarte al wifi de la oficina",
        category="Redes",
        author="valentina.pizarro",
        published_days_ago=5,
        featured=True,
        content=(
            "Selecciona la red de la empresa e ingresa con tu usuario y contraseña.\n\n"
            "Si tu equipo guardó una contraseña antigua, olvida la red y vuelve a "
            "conectarte. Si ves la red pero no navegas, reinicia el equipo antes de pedir "
            "ayuda."
        ),
    ),
    DemoArticle(
        title="Tu correo no sincroniza en el celular",
        category="Correo",
        author="diego.soto",
        published_days_ago=9,
        content=(
            "Revisa que el celular tenga Internet y que la fecha y la hora sean correctas.\n\n"
            "Si cambiaste la contraseña hace poco, la aplicación de correo puede seguir "
            "usando la anterior: elimina la cuenta y vuelve a agregarla."
        ),
    ),
    DemoArticle(
        title="Contraseña bloqueada o olvidada",
        category="Correo",
        author="felipe.araya",
        published_days_ago=14,
        featured=True,
        content=(
            "Tras varios intentos fallidos la cuenta se bloquea durante unos minutos. "
            "Espera y vuelve a intentarlo.\n\n"
            "Si olvidaste la contraseña, pide a soporte un restablecimiento: recibirás una "
            "contraseña temporal que deberás cambiar al entrar."
        ),
    ),
    DemoArticle(
        title="El computador está muy lento",
        category="Hardware",
        author="diego.soto",
        published_days_ago=20,
        content=(
            "Cierra los programas que no uses y revisa que haya espacio libre en el disco.\n\n"
            "Reinicia el equipo: muchos problemas de lentitud desaparecen. Si persiste, "
            "indícanos desde cuándo ocurre y qué estabas haciendo."
        ),
    ),
    DemoArticle(
        title="La pantalla no enciende o se ve negra",
        category="Hardware",
        author="diego.soto",
        published_days_ago=31,
        content=(
            "Comprueba que el cable de video y el de corriente estén firmes en ambos "
            "extremos y prueba con otro enchufe. En un portátil, revisa la configuración "
            "de pantalla externa."
        ),
    ),
    DemoArticle(
        title="Compartir una carpeta de red con tu equipo",
        category="Redes",
        author="valentina.pizarro",
        published_days_ago=45,
        content=(
            "Pide el acceso indicando la carpeta y quién la necesita. El jefe del área "
            "debe aprobarlo antes de habilitarlo."
        ),
    ),
    DemoArticle(
        title="Procedimiento: reiniciar la cola de impresión del servidor",
        category="Impresoras",
        author="felipe.araya",
        published_days_ago=7,
        public=False,
        content=(
            "Solo para soporte. Detén el servicio de cola, borra los trabajos pendientes y "
            "vuelve a iniciarlo. Avisa antes al área afectada: se pierden los trabajos en "
            "espera."
        ),
    ),
    DemoArticle(
        title="Procedimiento: revisión de un puerto de red sin enlace",
        category="Redes",
        author="valentina.pizarro",
        published_days_ago=12,
        public=False,
        content=(
            "Solo para soporte. Comprueba el cable, el puerto del switch y su estado en la "
            "consola. Anota el puerto en el ticket para seguir su historial."
        ),
    ),
    DemoArticle(
        title="Borrador: configurar la firma de correo",
        category="Correo",
        author="felipe.araya",
        published_days_ago=None,
        content=(
            "Pendiente de revisar con comunicaciones el formato oficial de la firma antes "
            "de publicarlo."
        ),
    ),
    DemoArticle(
        title="Borrador: videollamadas sin sonido",
        category="Hardware",
        author="diego.soto",
        published_days_ago=None,
        content=(
            "Revisar el dispositivo de audio elegido en la aplicación y el volumen del "
            "sistema. Falta añadir capturas de cada paso."
        ),
    ),
)
