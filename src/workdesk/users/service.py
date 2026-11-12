from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager

from ..audit import AuditAction, record_admin_event
from ..auth.credentials import set_temporary_password
from ..extensions import db
from ..models import Role, User

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


def _is_in_use(column, value: str) -> bool:
    return (
        db.session.scalar(db.select(User.id).where(column == value).limit(1))
        is not None
    )


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
