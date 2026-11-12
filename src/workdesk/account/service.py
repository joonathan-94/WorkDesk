from ..models import User
from ..users.service import update_profile


def update_own_contact(
    user: User,
    *,
    telefono: str | None,
    cargo: str | None,
    departamento_area: str | None,
) -> bool:
    """Actualiza los datos que el propio usuario puede editar.

    Son el teléfono, el cargo y el departamento o área. El nombre, el
    apellido, el correo, el username y el rol los gestiona el Administrador,
    por eso se pasan sin cambios.

    Delega en `users.service.update_profile`, así que hereda su validación y
    su auditoría (`USUARIO_MODIFICADO`, con el propio usuario como actor y
    solo los campos modificados). Devuelve False si no hubo cambios.

    No hace commit.
    """
    return update_profile(
        user,
        actor=user,
        nombre=user.nombre,
        apellido=user.apellido,
        email=user.email,
        telefono=telefono,
        cargo=cargo,
        departamento_area=departamento_area,
    )
