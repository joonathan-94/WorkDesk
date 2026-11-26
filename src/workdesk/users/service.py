from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager

from .. import settings
from ..audit import AuditAction, record_admin_event
from ..auth.credentials import reset_password, set_temporary_password
from ..auth.security import invalidate_user_sessions, reset_login_failures
from ..cleaning import blank_to_none
from ..configuration import value_of
from ..extensions import db
from ..groups.service import close_user_group_links
from ..models import Role, User
from ..search import escape_like
from ..security import RoleCode, hash_password, validate_password_policy
from ..status_filter import STATUS_ACTIVE, STATUS_INACTIVE
from .rules import identity_problems, normalize_email, normalize_username

PAGE_SIZE = 20
MAX_SEARCH_LENGTH = 100


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


class InvalidUserDataError(ValueError):
    """Algún dato de identidad no tiene la forma que exige RN-148.

    `problems` dice qué campo y por qué (los mismos mensajes del formulario). El
    formulario web ya lo impide; este error cubre los demás caminos (el comando
    `create-admin`, un envío fabricado a mano) para que ninguno se salte la regla.
    """

    def __init__(self, problems: dict[str, str]) -> None:
        self.problems = problems

        super().__init__(" ".join(problems.values()))


class AdministratorAlreadyExistsError(UserRuleError):
    """Ya hay un Administrador: el inicial solo se crea una vez."""


def _check_identity(*, nombre, apellido, username, email) -> None:
    problems = identity_problems(
        nombre=nombre, apellido=apellido, username=username, email=email
    )

    if problems:
        raise InvalidUserDataError(problems)


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
        pattern = f"%{escape_like(query_text)}%"

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

    Lanza `InvalidUserDataError`, `DuplicateUserError`, `UnknownRoleError` o
    `PasswordPolicyError` sin dejar nada pendiente en la sesión. No hace commit.
    """
    user, role = _new_user(
        nombre=nombre,
        apellido=apellido,
        username=username,
        email=email,
        role_code=role_code,
    )
    user.telefono = blank_to_none(telefono)
    user.cargo = blank_to_none(cargo)
    user.departamento_area = blank_to_none(departamento_area)
    user.usuario_creacion_id = actor.id

    # Valida la política antes de tocar la base de datos.
    set_temporary_password(user, temporary_password)

    _insert_and_audit(user, role, actor=actor)

    return user


def create_initial_administrator(
    *, nombre: str, apellido: str, username: str, email: str, password: str
) -> User:
    """Crea el Administrador inicial (`create-admin`, RF-124 y RN-125).

    Aplica las mismas reglas que cualquier alta (forma, unicidad y política de
    contraseñas) y se audita como acción del sistema: no hay ningún usuario que la
    ejecute. La contraseña la elige quien instala, así que no queda pendiente de
    cambio. Bloquea las filas de los Administradores para que dos ejecuciones a la
    vez no creen dos. Lanza `AdministratorAlreadyExistsError`, `InvalidUserDataError`,
    `DuplicateUserError` o `PasswordPolicyError`. No hace commit.
    """
    existing = db.session.scalar(
        db.select(User.id)
        .join(Role)
        .where(Role.codigo == RoleCode.ADMINISTRADOR)
        .limit(1)
        .with_for_update(of=User)
    )

    if existing is not None:
        raise AdministratorAlreadyExistsError("Ya existe un usuario con rol ADMINISTRADOR.")

    user, role = _new_user(
        nombre=nombre,
        apellido=apellido,
        username=username,
        email=email,
        role_code=RoleCode.ADMINISTRADOR,
    )
    validate_password_policy(password, min_length=value_of(settings.PASSWORD_MIN_LENGTH))
    user.password_hash = hash_password(password)

    _insert_and_audit(user, role, actor=None, detail="Administrador inicial (create-admin).")

    return user


def _new_user(*, nombre, apellido, username, email, role_code) -> tuple[User, Role]:
    """Un usuario nuevo (sin guardar) con su identidad validada y su rol."""
    nombre = nombre.strip()
    apellido = apellido.strip()
    username = normalize_username(username)
    email = normalize_email(email)

    _check_identity(nombre=nombre, apellido=apellido, username=username, email=email)

    role = db.session.scalar(db.select(Role).where(Role.codigo == role_code))

    if role is None:
        raise UnknownRoleError(role_code)

    if _is_in_use(User.username, username):
        raise DuplicateUserError("username")

    if _is_in_use(User.email, email):
        raise DuplicateUserError("email")

    user = User(
        nombre=nombre,
        apellido=apellido,
        username=username,
        email=email,
        rol_id=role.id,
    )

    return user, role


def _insert_and_audit(user: User, role: Role, *, actor: User | None, detail=None) -> None:
    # Dos altas simultáneas pueden pasar la comprobación de unicidad y chocar
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
        detail=detail,
        new_value={
            "username": user.username,
            "email": user.email,
            "rol": role.codigo,
            "activo": True,
            "cambio_obligatorio": user.debe_cambiar_password,
        },
    )


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

    Lanza `InvalidUserDataError` si algún dato no tiene la forma de RN-148 y
    `DuplicateUserError` si el correo pertenece a otro usuario. No hace commit.
    """
    new_values = {
        "nombre": nombre.strip(),
        "apellido": apellido.strip(),
        "email": normalize_email(email),
        "telefono": blank_to_none(telefono),
        "cargo": blank_to_none(cargo),
        "departamento_area": blank_to_none(departamento_area),
    }

    changed = {
        field: value
        for field, value in new_values.items()
        if getattr(user, field) != value
    }

    if not changed:
        return False

    # Solo se juzga lo que cambia: un dato antiguo que no cumpla la regla (de antes de
    # que existiera) no debe impedir, por ejemplo, actualizar el teléfono.
    problems = {
        field: message
        for field, message in identity_problems(
            nombre=new_values["nombre"],
            apellido=new_values["apellido"],
            username=None,
            email=new_values["email"],
        ).items()
        if field in changed
    }

    if problems:
        raise InvalidUserDataError(problems)

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

    # Quien deja de ser Técnico deja de ser miembro de sus grupos, y quien
    # deja de ser Supervisor deja de ser responsable (docs/09, 10.2 y 10.3).
    # El historial se conserva.
    close_user_group_links(
        user,
        actor=actor,
        reason="Cambio de rol.",
        members=previous_code == RoleCode.TECNICO,
        supervisors=previous_code == RoleCode.SUPERVISOR,
    )

    record_admin_event(
        AuditAction.CAMBIO_ROL,
        actor=actor,
        entity_type="usuario",
        entity_id=user.id,
        old_value={"rol": previous_code},
        new_value={"rol": role.codigo},
        reason=blank_to_none(reason),
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

    # Una cuenta desactivada deja sus grupos: no se reabren al reactivarla.
    close_user_group_links(user, actor=actor, reason="Usuario desactivado.")

    record_admin_event(
        AuditAction.USUARIO_DESACTIVADO,
        actor=actor,
        entity_type="usuario",
        entity_id=user.id,
        old_value={"activo": True},
        new_value={"activo": False},
        reason=blank_to_none(reason),
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
        reason=blank_to_none(reason),
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
