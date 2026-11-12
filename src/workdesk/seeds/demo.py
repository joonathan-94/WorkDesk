"""Datos de demostración: un equipo de soporte TI ficticio.

Sirven para mostrar WorkDesk con usuarios de todos los roles operativos.
Son personas inventadas, con correos en el dominio reservado
`workdesk.local`. No incluyen ningún Administrador: el Administrador real
se crea con el comando `create-admin`.
"""

from dataclasses import dataclass

from ..audit import AuditAction, record_admin_event
from ..extensions import db
from ..models import Role, User
from ..security import hash_password


@dataclass(frozen=True)
class DemoUser:
    nombre: str
    apellido: str
    username: str
    rol: str
    cargo: str
    departamento_area: str
    telefono: str

    @property
    def email(self) -> str:
        return f"{self.username}@workdesk.local"


DEMO_USERS = (
    # Supervisores
    DemoUser(
        "Camila", "Rojas", "camila.rojas", "SUPERVISOR",
        "Jefa de soporte", "Soporte TI", "+56 9 5555 0101",
    ),
    DemoUser(
        "Matías", "Fuentes", "matias.fuentes", "SUPERVISOR",
        "Coordinador de operaciones", "Soporte TI", "+56 9 5555 0102",
    ),
    # Técnicos
    DemoUser(
        "Diego", "Soto", "diego.soto", "TECNICO",
        "Técnico de soporte nivel 2", "Soporte TI", "+56 9 5555 0103",
    ),
    DemoUser(
        "Valentina", "Pizarro", "valentina.pizarro", "TECNICO",
        "Técnica de redes", "Infraestructura", "+56 9 5555 0104",
    ),
    DemoUser(
        "Felipe", "Araya", "felipe.araya", "TECNICO",
        "Técnico de soporte nivel 1", "Soporte TI", "+56 9 5555 0105",
    ),
    DemoUser(
        "Francisca", "Muñoz", "francisca.munoz", "TECNICO",
        "Técnica de aplicaciones", "Sistemas", "+56 9 5555 0106",
    ),
    # Solicitantes
    DemoUser(
        "Javiera", "Torres", "javiera.torres", "SOLICITANTE",
        "Analista contable", "Finanzas", "+56 9 5555 0107",
    ),
    DemoUser(
        "Sebastián", "Vargas", "sebastian.vargas", "SOLICITANTE",
        "Ejecutivo comercial", "Ventas", "+56 9 5555 0108",
    ),
    DemoUser(
        "Constanza", "Herrera", "constanza.herrera", "SOLICITANTE",
        "Asistente administrativa", "Administración", "+56 9 5555 0109",
    ),
    DemoUser(
        "Ignacio", "Molina", "ignacio.molina", "SOLICITANTE",
        "Jefe de bodega", "Logística", "+56 9 5555 0110",
    ),
    DemoUser(
        "Paula", "Contreras", "paula.contreras", "SOLICITANTE",
        "Ejecutiva de recursos humanos", "Recursos humanos",
        "+56 9 5555 0111",
    ),
    DemoUser(
        "Andrés", "Silva", "andres.silva", "SOLICITANTE",
        "Ingeniero de proyectos", "Proyectos", "+56 9 5555 0112",
    ),
)


def seed_demo_users(password: str) -> tuple[int, int]:
    """Crea los usuarios de demostración que todavía no existan.

    Es idempotente: se omite a quien ya tenga ese username o ese correo, sin
    modificarlo. Todos comparten la contraseña indicada, que quien llama debe
    haber validado con la política de contraseñas; no se guarda ni se muestra.
    Los usuarios quedan activos y sin cambio de contraseña obligatorio, para
    poder entrar directamente en una demostración.

    Cada creación se audita como una acción del sistema. Hace commit.
    Devuelve (creados, omitidos).
    """
    roles = {role.codigo: role for role in db.session.scalars(db.select(Role))}
    password_hash = hash_password(password)

    created = 0
    skipped = 0

    for demo in DEMO_USERS:
        already_exists = db.session.scalar(
            db.select(User.id)
            .where(db.or_(User.username == demo.username, User.email == demo.email))
            .limit(1)
        )

        if already_exists is not None:
            skipped += 1
            continue

        user = User(
            nombre=demo.nombre,
            apellido=demo.apellido,
            username=demo.username,
            email=demo.email,
            telefono=demo.telefono,
            cargo=demo.cargo,
            departamento_area=demo.departamento_area,
            rol_id=roles[demo.rol].id,
            password_hash=password_hash,
        )

        db.session.add(user)
        db.session.flush()

        record_admin_event(
            AuditAction.USUARIO_CREADO,
            actor=None,
            entity_type="usuario",
            entity_id=user.id,
            new_value={
                "username": user.username,
                "email": user.email,
                "rol": demo.rol,
                "activo": True,
                "cambio_obligatorio": False,
            },
            detail="Datos de demostración.",
        )

        created += 1

    db.session.commit()

    return created, skipped
