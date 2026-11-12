from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager

from ..audit import AuditAction, record_admin_event
from ..auth.credentials import reset_password, set_temporary_password
from ..auth.security import invalidate_user_sessions, reset_login_failures
from ..extensions import db
from ..models import Role, User
from ..security import RoleCode

PAGE_SIZE = 20
MAX_SEARCH_LENGTH = 100

STATUS_ACTIVE = "activo"
STATUS_INACTIVE = "inactivo"
VALID_STATUSES = frozenset({STATUS_ACTIVE, STATUS_INACTIVE})


class DuplicateUserError(ValueError):
    """El username o el email ya pertenecen a otro usuario.

    `field` indica cuál es ("username" o "email"); es None cuando el
    conflicto solo se detectó al escribir en la base de datos.
    """

    def __init__(self, field: str | None) -> None:
        self.field = field

        super().__init__(
            "El username o el email ya están registrados."
        )


class UnknownRoleError(ValueError):
    """El código de rol indicado no existe."""


class UserRuleError(ValueError):
    """Una regla de negocio impide realizar la operación sobre el usuario."""


class SelfProtectionError(UserRuleError):
    """Un Administrador intentó una acción restringida sobre sí mismo."""


class LastAdministratorError(UserRuleError):
    """La operación dejaría al sistema sin Administradores activos."""


class NothingToChangeError(UserRuleError):
    """El usuario ya está en el estado solicitado."""


def normalize_username(username: str) -> str:
    return username.strip().lower()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def list_roles() -> list[Role]:
    return list(db.session.scalars(db.select(Role).order_by(Role.id)))


def list_users(
    *,
    query_text: str = "",
    role_code: str = "",
    status: str = "",
    page: int = 1,
):
    """Devuelve una página de usuarios aplicando búsqueda y filtros.

    La paginación se hace en PostgreSQL y el rol se carga con el mismo
    JOIN del filtro (`contains_eager`), de modo que mostrar el rol de cada
    fila no genera una consulta adicional por usuario.
    """
    statement = (
        db.select(User)
        .join(User.rol)
        .options(contains_eager(User.rol))
        .order_by(User.apellido, User.nombre, User.id)
    )

    query_text = query_text.strip()[:MAX_SEARCH_LENGTH]

    if query_text:
        pattern = f"%{_escape_like(query_text)}%"

        statement = statement.where(
            db.or_(
                User.nombre.ilike(pattern, escape="\\"),
                User.apellido.ilike(pattern, escape="\\"),
                (User.nombre + " " + User.apellido).ilike(
                    pattern,
                    escape="\\",
                ),
                User.username.ilike(pattern, escape="\\"),
                User.email.ilike(pattern, escape="\\"),
            )
        )

    if role_code:
        statement = statement.where(Role.codigo == role_code)

    if status == STATUS_ACTIVE:
        statement = statement.where(User.activo.is_(True))
    elif status == STATUS_INACTIVE:
        statement = statement.where(User.activo.is_(False))

    return db.paginate(
        statement,
        page=page,
        per_page=PAGE_SIZE,
        max_per_page=PAGE_SIZE,
        error_out=False,
    )


def create_user(
    *,
    actor: User,
    nombre: str,
    apellido: str,
    username: str,
    email: str,
    role_code: str,
    temporary_password: str,
    telefono: str | None = None,
    cargo: str | None = None,
    departamento_area: str | None = None,
) -> User:
    """Crea un usuario con una contraseña temporal.

    El usuario queda activo y con el cambio de contraseña pendiente. La
    creación se audita (`USUARIO_CREADO`) en la misma transacción.

    Lanza `DuplicateUserError`, `UnknownRoleError` o `PasswordPolicyError`
    sin dejar nada pendiente en la sesión. No hace commit.
    """
    username = normalize_username(username)
    email = normalize_email(email)

    role = db.session.scalar(db.select(Role).where(Role.codigo == role_code))

    if role is None:
        raise UnknownRoleError(role_code)

    if _is_in_use(User.username, username):
        raise DuplicateUserError("username")

    if _is_in_use(User.email, email):
        raise DuplicateUserError("email")

    user = User(
        nombre=nombre.strip(),
        apellido=apellido.strip(),
        username=username,
        email=email,
        telefono=_blank_to_none(telefono),
        cargo=_blank_to_none(cargo),
        departamento_area=_blank_to_none(departamento_area),
        rol_id=role.id,
        usuario_creacion_id=actor.id,
    )

    # Valida la política antes de tocar la base de datos.
    set_temporary_password(user, temporary_password)

    # Dos altas simultáneas pueden pasar la comprobación anterior y chocar
    # en la restricción UNIQUE. El savepoint deshace solo este intento y
    # deja intacta el resto de la transacción.
    try:
        with db.session.begin_nested():
            db.session.add(user)
            db.session.flush()
    except IntegrityError as error:
        raise DuplicateUserError(None) from error

    record_admin_event(
        AuditAction.USUARIO_CREADO,
        actor=actor,
        entity_type="usuario",
        entity_id=user.id,
        new_value={
            "username": user.username,
            "email": user.email,
            "rol": role.codigo,
            "activo": True,
            "cambio_obligatorio": True,
        },
    )

    return user


def get_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def update_profile(
    user: User,
    *,
    actor: User,
    nombre: str,
    apellido: str,
    email: str,
    telefono: str | None,
    cargo: str | None,
    departamento_area: str | None,
) -> bool:
    """Actualiza los datos personales del usuario (no su rol ni su estado).

    El username no se puede cambiar. Devuelve False, sin modificar nada ni
    auditar, si los datos no cambiaron. Audita `USUARIO_MODIFICADO` con los
    valores anteriores y nuevos de los campos que sí cambiaron.

    Lanza `DuplicateUserError` si el correo pertenece a otro usuario.
    No hace commit.
    """
    new_values = {
        "nombre": nombre.strip(),
        "apellido": apellido.strip(),
        "email": normalize_email(email),
        "telefono": _blank_to_none(telefono),
        "cargo": _blank_to_none(cargo),
        "departamento_area": _blank_to_none(departamento_area),
    }

    changed = {
        field: value
        for field, value in new_values.items()
        if getattr(user, field) != value
    }

    if not changed:
        return False

    if "email" in changed and _is_in_use(
        User.email,
        changed["email"],
        exclude_id=user.id,
    ):
        raise DuplicateUserError("email")

    old_values = {field: getattr(user, field) for field in changed}

    # Mismo savepoint que en la creación: una carrera por el correo la
    # resuelve la restricción UNIQUE sin dañar el resto de la transacción.
    try:
        with db.session.begin_nested():
            for field, value in changed.items():
                setattr(user, field, value)

            user.mark_modified(actor)
            db.session.flush()
    except IntegrityError as error:
        raise DuplicateUserError("email") from error

    record_admin_event(
        AuditAction.USUARIO_MODIFICADO,
        actor=actor,
        entity_type="usuario",
        entity_id=user.id,
        old_value=old_values,
        new_value=changed,
    )

    return True


def change_role(
    user: User,
    role_code: str,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Cambia el rol del usuario.

    Un Administrador no puede cambiar su propio rol ni dejar al sistema sin
    Administradores activos. El cambio sube `token_version`: el usuario debe
    volver a iniciar sesión y entra ya con su nuevo rol.

    Audita `CAMBIO_ROL`. No hace commit.
    """
    _ensure_not_self(user, actor, "No puedes cambiar tu propio rol.")

    role = db.session.scalar(db.select(Role).where(Role.codigo == role_code))

    if role is None:
        raise UnknownRoleError(role_code)

    if role.id == user.rol_id:
        raise NothingToChangeError("El usuario ya tiene ese rol.")

    previous_code = user.rol.codigo

    if user.activo and previous_code == RoleCode.ADMINISTRADOR:
        _ensure_another_active_administrator(user)

    user.rol = role
    invalidate_user_sessions(user)
    user.mark_modified(actor)

    record_admin_event(
        AuditAction.CAMBIO_ROL,
        actor=actor,
        entity_type="usuario",
        entity_id=user.id,
        old_value={"rol": previous_code},
        new_value={"rol": role.codigo},
        reason=_blank_to_none(reason),
    )


def deactivate_user(
    user: User,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Desactiva la cuenta: el usuario deja de poder iniciar sesión.

    Un Administrador no puede desactivarse a sí mismo ni dejar al sistema
    sin Administradores activos. Sube `token_version`, de modo que cualquier
    sesión abierta queda invalidada. El historial del usuario se conserva.

    Audita `USUARIO_DESACTIVADO`. No hace commit.
    """
    _ensure_not_self(user, actor, "No puedes desactivar tu propia cuenta.")

    if not user.activo:
        raise NothingToChangeError("El usuario ya está desactivado.")

    if user.rol.codigo == RoleCode.ADMINISTRADOR:
        _ensure_another_active_administrator(user)

    user.activo = False
    user.fecha_desactivacion = datetime.now(UTC)
    user.usuario_desactivacion_id = actor.id
    invalidate_user_sessions(user)
    user.mark_modified(actor)

    record_admin_event(
        AuditAction.USUARIO_DESACTIVADO,
        actor=actor,
        entity_type="usuario",
        entity_id=user.id,
        old_value={"activo": True},
        new_value={"activo": False},
        reason=_blank_to_none(reason),
    )


def activate_user(
    user: User,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Reactiva una cuenta desactivada.

    Limpia los datos de la desactivación y los intentos fallidos y el
    bloqueo temporal. Audita `USUARIO_ACTIVADO`. No hace commit.
    """
    if user.activo:
        raise NothingToChangeError("El usuario ya está activo.")

    user.activo = True
    user.fecha_desactivacion = None
    user.usuario_desactivacion_id = None
    reset_login_failures(user)
    user.mark_modified(actor)

    record_admin_event(
        AuditAction.USUARIO_ACTIVADO,
        actor=actor,
        entity_type="usuario",
        entity_id=user.id,
        old_value={"activo": False},
        new_value={"activo": True},
        reason=_blank_to_none(reason),
    )


def reset_user_password(
    user: User,
    temporary_password: str,
    *,
    actor: User,
) -> None:
    """Restablece la contraseña de otro usuario con una temporal.

    Un Administrador no restablece su propia contraseña: para eso existe el
    cambio de contraseña propio, que exige conocer la actual. Delega en
    `auth.credentials.reset_password`. No hace commit.
    """
    _ensure_not_self(
        user,
        actor,
        "Para cambiar tu propia contraseña usa «Cambiar contraseña».",
    )

    reset_password(user, temporary_password, actor=actor)


def _ensure_not_self(user: User, actor: User, message: str) -> None:
    if user.id == actor.id:
        raise SelfProtectionError(message)


def _ensure_another_active_administrator(user: User) -> None:
    """Exige que, además de `user`, quede otro Administrador activo.

    Se bloquean las filas de los Administradores activos (`FOR UPDATE`): si
    dos Administradores se desactivan entre sí a la vez, el segundo espera,
    vuelve a contar y comprueba el resultado ya confirmado del primero.
    """
    active_administrator_ids = db.session.scalars(
        db.select(User.id)
        .join(User.rol)
        .where(
            Role.codigo == RoleCode.ADMINISTRADOR.value,
            User.activo.is_(True),
        )
        .with_for_update(of=User)
    ).all()

    if not any(user_id != user.id for user_id in active_administrator_ids):
        raise LastAdministratorError(
            "Debe quedar al menos un Administrador activo."
        )


def _is_in_use(column, value: str, *, exclude_id: int | None = None) -> bool:
    statement = db.select(User.id).where(column == value)

    if exclude_id is not None:
        statement = statement.where(User.id != exclude_id)

    return db.session.scalar(statement.limit(1)) is not None


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


def _escape_like(text: str) -> str:
    # Para que "%" y "_" escritos por el usuario se busquen literalmente.
    return (
        text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
