"""Reglas de los grupos de atención (docs/06, RN-146; docs/09, 10.1 a 10.3).

Un grupo es una unidad organizativa opcional: tiene técnicos miembros y
Supervisores responsables, ambos con vigencia (`fecha_fin` NULL es vigente) y
con historial. Quién puede hacer cada cosa lo decide la capa de rutas con las
políticas de `security/authorization.py`; aquí viven las reglas de los datos.

Ninguna función hace commit: el cambio y su evento de auditoría se confirman
o se revierten juntos, y el commit lo realiza quien llama.
"""

from sqlalchemy import func, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..audit import AuditAction, record_admin_event
from ..cleaning import blank_to_none
from ..extensions import db
from ..models import Grupo, GrupoSupervisor, Role, User, UsuarioGrupo
from ..security import RoleCode, can_manage_groups, has_any_role

STATUS_ACTIVE = "activo"
STATUS_INACTIVE = "inactivo"
VALID_STATUSES = frozenset({STATUS_ACTIVE, STATUS_INACTIVE})

ENTITY_TYPE = "grupo"


class GroupRuleError(ValueError):
    """Una regla de los grupos impide la operación.

    El mensaje está pensado para mostrarse al usuario.
    """


class DuplicateGroupNameError(GroupRuleError):
    """Ya existe otro grupo con ese nombre."""


class NothingToChangeError(GroupRuleError):
    """La operación no cambiaría nada."""


# --- Consultas --------------------------------------------------------


def visible_groups_condition(user):
    """Condición SQL con los grupos que `user` puede ver.

    - El Administrador ve todos.
    - El Supervisor ve solo los grupos de los que es responsable vigente.
    - Cualquier otro caso (Técnico, Solicitante, anónimo, inactivo): ninguno.

    Es el mismo criterio que la política `can_view_group`; un test comprueba
    que ambos coinciden. Si se cambia uno hay que cambiar el otro.
    """
    if can_manage_groups(user):
        return true()

    if has_any_role(user, RoleCode.SUPERVISOR):
        return db.exists().where(
            GrupoSupervisor.grupo_id == Grupo.id,
            GrupoSupervisor.supervisor_id == user.id,
            GrupoSupervisor.fecha_fin.is_(None),
        )

    return db.false()


def list_groups(user: User, status: str = "") -> list[Grupo]:
    """Grupos visibles para `user`, por nombre.

    Carga de una vez los miembros y supervisores vigentes que muestra el
    listado, sin una consulta por grupo.
    """
    statement = (
        db.select(Grupo)
        .where(visible_groups_condition(user))
        .options(
            selectinload(Grupo.membresias).joinedload(UsuarioGrupo.usuario),
            selectinload(Grupo.designaciones).joinedload(
                GrupoSupervisor.supervisor
            ),
        )
        .order_by(func.lower(Grupo.nombre))
    )

    if status == STATUS_ACTIVE:
        statement = statement.where(Grupo.activo.is_(True))
    elif status == STATUS_INACTIVE:
        statement = statement.where(Grupo.activo.is_(False))

    return list(db.session.scalars(statement))


def get_group(group_id: int) -> Grupo | None:
    """Un grupo con sus miembros y supervisores. No comprueba permisos."""
    return db.session.scalar(
        db.select(Grupo)
        .where(Grupo.id == group_id)
        .options(
            selectinload(Grupo.membresias).joinedload(UsuarioGrupo.usuario),
            selectinload(Grupo.designaciones).joinedload(
                GrupoSupervisor.supervisor
            ),
        )
    )


def list_member_candidates(group: Grupo) -> list[User]:
    """Técnicos activos que todavía no son miembros vigentes del grupo."""
    current = [m.usuario_id for m in group.miembros_vigentes]

    return _active_users_with_role(RoleCode.TECNICO, exclude_ids=current)


def list_supervisor_candidates(group: Grupo) -> list[User]:
    """Supervisores activos que todavía no son responsables vigentes."""
    current = [d.supervisor_id for d in group.supervisores_vigentes]

    return _active_users_with_role(RoleCode.SUPERVISOR, exclude_ids=current)


# --- Alta, edición y estado -------------------------------------------


def create_group(
    *,
    actor: User,
    nombre: str,
    descripcion: str | None = None,
) -> Grupo:
    """Crea un grupo activo. Lanza `DuplicateGroupNameError` si el nombre
    existe (sin distinguir mayúsculas). Audita `GRUPO_CREADO`."""
    values = {
        "nombre": _clean_name(nombre),
        "descripcion": blank_to_none(descripcion),
    }
    _ensure_name_available(values["nombre"])

    group = Grupo(**values, usuario_creacion_id=actor.id)

    # Dos altas simultáneas pueden pasar la comprobación anterior y chocar en
    # el índice único del nombre: el savepoint deshace solo este intento.
    try:
        with db.session.begin_nested():
            db.session.add(group)
            db.session.flush()
    except IntegrityError as error:
        raise DuplicateGroupNameError(_DUPLICATE_MESSAGE) from error

    _audit(
        AuditAction.GRUPO_CREADO,
        group,
        actor,
        new_value={**values, "activo": True},
    )

    return group


def update_group(
    group: Grupo,
    *,
    actor: User,
    nombre: str,
    descripcion: str | None,
) -> bool:
    """Edita nombre y descripción. Devuelve False, sin auditar, si nada
    cambió. Audita `GRUPO_MODIFICADO` con los valores anterior y nuevo solo
    de los campos que cambiaron."""
    new_values = {
        "nombre": _clean_name(nombre),
        "descripcion": blank_to_none(descripcion),
    }
    changed = {
        field: value
        for field, value in new_values.items()
        if getattr(group, field) != value
    }

    if not changed:
        return False

    if "nombre" in changed:
        _ensure_name_available(changed["nombre"], exclude_id=group.id)

    old_values = {field: getattr(group, field) for field in changed}

    try:
        with db.session.begin_nested():
            for field, value in changed.items():
                setattr(group, field, value)

            group.mark_modified(actor)
            db.session.flush()
    except IntegrityError as error:
        raise DuplicateGroupNameError(_DUPLICATE_MESSAGE) from error

    _audit(
        AuditAction.GRUPO_MODIFICADO,
        group,
        actor,
        old_value=old_values,
        new_value=changed,
    )

    return True


def deactivate_group(
    group: Grupo,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Desactiva el grupo (no se eliminan, RF-117). Sus miembros y supervisores
    quedan como estaban: es historial. Audita `GRUPO_DESACTIVADO`."""
    if not group.activo:
        raise NothingToChangeError("El grupo ya está desactivado.")

    group.deactivate(actor)

    _audit(
        AuditAction.GRUPO_DESACTIVADO,
        group,
        actor,
        old_value={"activo": True},
        new_value={"activo": False},
        reason=reason,
    )


def activate_group(
    group: Grupo,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Reactiva el grupo. Audita `GRUPO_ACTIVADO`."""
    if group.activo:
        raise NothingToChangeError("El grupo ya está activo.")

    group.reactivate(actor)

    _audit(
        AuditAction.GRUPO_ACTIVADO,
        group,
        actor,
        old_value={"activo": False},
        new_value={"activo": True},
        reason=reason,
    )


# --- Miembros ---------------------------------------------------------


def add_member(group: Grupo, user_id: int, *, actor: User) -> UsuarioGrupo:
    """Agrega un técnico al grupo.

    El grupo debe estar activo y el usuario ser un Técnico activo que no sea
    ya miembro vigente. Audita `GRUPO_MIEMBRO_AGREGADO`.
    """
    _ensure_group_active(group)
    user = _get_user_with_role(
        user_id,
        RoleCode.TECNICO,
        "Elige un técnico activo de la lista.",
    )

    if any(m.usuario_id == user.id for m in group.miembros_vigentes):
        raise GroupRuleError("Esa persona ya es miembro del grupo.")

    link = UsuarioGrupo(
        usuario_id=user.id,
        grupo_id=group.id,
        asignado_por_usuario_id=actor.id,
    )

    # Dos altas a la vez pueden pasar la comprobación: el índice único
    # parcial decide y el savepoint deshace solo este intento.
    try:
        with db.session.begin_nested():
            db.session.add(link)
            db.session.flush()
    except IntegrityError as error:
        raise GroupRuleError("Esa persona ya es miembro del grupo.") from error

    db.session.refresh(group)

    _audit(
        AuditAction.GRUPO_MIEMBRO_AGREGADO,
        group,
        actor,
        new_value=_person(user),
    )

    return link


def remove_member(
    group: Grupo,
    membership_id: int,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Retira a un miembro vigente: cierra su membresía y la conserva como
    historial. Audita `GRUPO_MIEMBRO_RETIRADO`."""
    link = next(
        (m for m in group.miembros_vigentes if m.id == membership_id),
        None,
    )

    if link is None:
        raise GroupRuleError("Esa persona ya no es miembro del grupo.")

    _close_link(link, actor, reason)

    _audit(
        AuditAction.GRUPO_MIEMBRO_RETIRADO,
        group,
        actor,
        old_value=_person(link.usuario),
        reason=reason,
    )


# --- Supervisores responsables ----------------------------------------


def designate_supervisor(
    group: Grupo,
    user_id: int,
    *,
    actor: User,
) -> GrupoSupervisor:
    """Designa a un Supervisor activo como responsable del grupo. Solo el
    Administrador lo hace (lo comprueba la ruta). Audita
    `GRUPO_SUPERVISOR_DESIGNADO`."""
    _ensure_group_active(group)
    user = _get_user_with_role(
        user_id,
        RoleCode.SUPERVISOR,
        "Elige un supervisor activo de la lista.",
    )

    if any(d.supervisor_id == user.id for d in group.supervisores_vigentes):
        raise GroupRuleError("Esa persona ya es responsable del grupo.")

    designation = GrupoSupervisor(
        grupo_id=group.id,
        supervisor_id=user.id,
        asignado_por_usuario_id=actor.id,
    )

    try:
        with db.session.begin_nested():
            db.session.add(designation)
            db.session.flush()
    except IntegrityError as error:
        raise GroupRuleError(
            "Esa persona ya es responsable del grupo."
        ) from error

    db.session.refresh(group)

    _audit(
        AuditAction.GRUPO_SUPERVISOR_DESIGNADO,
        group,
        actor,
        new_value=_person(user),
    )

    return designation


def remove_supervisor(
    group: Grupo,
    designation_id: int,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Retira a un supervisor responsable (cierra la designación y la
    conserva). Un grupo sin supervisor es válido: solo el Administrador gestiona
    entonces sus membresías. Audita `GRUPO_SUPERVISOR_RETIRADO`."""
    designation = next(
        (d for d in group.supervisores_vigentes if d.id == designation_id),
        None,
    )

    if designation is None:
        raise GroupRuleError("Esa persona ya no es responsable del grupo.")

    _close_link(designation, actor, reason)

    _audit(
        AuditAction.GRUPO_SUPERVISOR_RETIRADO,
        group,
        actor,
        old_value=_person(designation.supervisor),
        reason=reason,
    )


# --- Cambios en las cuentas de usuario --------------------------------


def close_user_group_links(
    user: User,
    *,
    actor: User,
    reason: str,
    members: bool = True,
    supervisors: bool = True,
) -> int:
    """Cierra las membresías y designaciones vigentes de un usuario.

    Lo usa la administración de usuarios cuando alguien deja de ser Técnico o
    Supervisor, o se desactiva (docs/09, 10.2 y 10.3): el historial se
    conserva y cada cierre se audita. No hace commit. Devuelve cuántos cerró.
    """
    closed = 0

    if members:
        for link in _current_links(UsuarioGrupo, UsuarioGrupo.usuario_id, user):
            _close_link(link, actor, reason)
            _audit(
                AuditAction.GRUPO_MIEMBRO_RETIRADO,
                link.grupo,
                actor,
                old_value=_person(user),
                reason=reason,
            )
            closed += 1

    if supervisors:
        for link in _current_links(
            GrupoSupervisor,
            GrupoSupervisor.supervisor_id,
            user,
        ):
            _close_link(link, actor, reason)
            _audit(
                AuditAction.GRUPO_SUPERVISOR_RETIRADO,
                link.grupo,
                actor,
                old_value=_person(user),
                reason=reason,
            )
            closed += 1

    return closed


# --- Piezas comunes ---------------------------------------------------

_DUPLICATE_MESSAGE = "Ya existe un grupo con ese nombre."


def _audit(action, group: Grupo, actor, **kwargs) -> None:
    record_admin_event(
        action,
        actor=actor,
        entity_type=ENTITY_TYPE,
        entity_id=group.id,
        detail=group.nombre,
        reason=blank_to_none(kwargs.pop("reason", None)),
        **kwargs,
    )


def _person(user: User) -> dict:
    return {"usuario_id": user.id, "username": user.username}


def _close_link(link, actor: User, reason: str | None) -> None:
    # La hora la pone la base de datos, como `fecha_inicio`: así el cierre
    # nunca queda antes del inicio aunque los relojes difieran.
    link.fecha_fin = func.now()
    link.retirado_por_usuario_id = actor.id
    link.motivo_retiro = blank_to_none(reason)


def _current_links(model, column, user: User) -> list:
    return list(
        db.session.scalars(
            db.select(model)
            .where(column == user.id, model.fecha_fin.is_(None))
            .options(selectinload(model.grupo))
        )
    )


def _ensure_group_active(group: Grupo) -> None:
    if not group.activo:
        raise GroupRuleError(
            "El grupo está desactivado. Reactívalo para cambiar sus "
            "miembros o responsables."
        )


def _get_user_with_role(user_id, role_code: RoleCode, message: str) -> User:
    user = db.session.scalar(
        db.select(User)
        .join(Role, User.rol_id == Role.id)
        .where(
            User.id == user_id,
            User.activo.is_(True),
            Role.codigo == role_code,
        )
    )

    if user is None:
        raise GroupRuleError(message)

    return user


def _active_users_with_role(role_code: RoleCode, *, exclude_ids) -> list[User]:
    statement = (
        db.select(User)
        .join(Role, User.rol_id == Role.id)
        .where(User.activo.is_(True), Role.codigo == role_code)
        .order_by(func.lower(User.apellido), func.lower(User.nombre))
    )

    if exclude_ids:
        statement = statement.where(User.id.not_in(exclude_ids))

    return list(db.session.scalars(statement))


def _clean_name(nombre: str) -> str:
    nombre = (nombre or "").strip()

    if not nombre:
        raise GroupRuleError("El nombre es obligatorio.")

    return nombre


def _ensure_name_available(nombre: str, *, exclude_id=None) -> None:
    # `lower` en la base de datos a ambos lados, igual que el índice único.
    statement = db.select(Grupo.id).where(
        func.lower(Grupo.nombre) == func.lower(nombre)
    )

    if exclude_id is not None:
        statement = statement.where(Grupo.id != exclude_id)

    if db.session.scalar(statement.limit(1)) is not None:
        raise DuplicateGroupNameError(_DUPLICATE_MESSAGE)
