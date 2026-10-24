from ..extensions import db
from ..models import Role

INITIAL_ROLES = (
    {
        "codigo": "SOLICITANTE",
        "nombre": "Solicitante",
        "descripcion": "Usuario que registra y consulta solicitudes autorizadas.",
    },
    {
        "codigo": "TECNICO",
        "nombre": "Técnico",
        "descripcion": "Usuario encargado de la atención operativa de tickets.",
    },
    {
        "codigo": "SUPERVISOR",
        "nombre": "Supervisor",
        "descripcion": "Usuario responsable de supervisión y gestión operativa.",
    },
    {
        "codigo": "ADMINISTRADOR",
        "nombre": "Administrador",
        "descripcion": "Usuario con acceso a la administración del sistema.",
    },
)


def seed_roles() -> int:
    created = 0

    for role_data in INITIAL_ROLES:
        existing_role = db.session.scalar(
            db.select(Role).where(Role.codigo == role_data["codigo"])
        )

        if existing_role is not None:
            continue

        db.session.add(Role(**role_data))
        created += 1

    db.session.commit()

    return created