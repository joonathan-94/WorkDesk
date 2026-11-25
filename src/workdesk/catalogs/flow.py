"""Administración controlada de los estados y las transiciones del flujo de
tickets (docs/04, RF-118; docs/06, RN-164; docs/11, UI-021).

Los seis estados y sus transiciones son **estructurales**: el Administrador no
crea, elimina ni reemplaza nada. Lo que sí puede hacer es:

- cambiar el **nombre visible** y la **descripción** de un estado (su código es
  inmutable y es el que usa el código de la aplicación);
- **habilitar o deshabilitar** una transición ya definida, con dos protecciones
  para que el flujo no quede incoherente:

  1. las transiciones **esenciales** nunca se deshabilitan (por ejemplo, la
     confirmación del solicitante): `ESSENTIAL_REASONS`, en
     `tickets/state_actions.py`, dice cuáles y por qué;
  2. ninguna deshabilitación puede dejar un estado inalcanzable desde `Nuevo`
     avanzando por el flujo (las acciones que devuelven un ticket atrás, como
     reabrir, no cuentan) ni impedir que desde cualquier estado se llegue a
     `Cerrado`. Es una comprobación sobre el grafo de transiciones activas:
     casi no sabe de acciones, así que sigue valiendo si mañana se añaden
     estados o acciones.

Lo que se configura se aplica de inmediato y a todos los tickets: el motor de
estados lee la tabla en cada acción (`tickets/lifecycle.py`). Un ticket que ya
está en un estado conserva el que tiene.

Ninguna función hace commit: el cambio y su evento de auditoría se confirman o
se revierten juntos, y el commit lo realiza quien llama.
"""

from dataclasses import dataclass

from sqlalchemy.orm import joinedload

from ..audit import AuditAction, record_admin_event
from ..cleaning import blank_to_none
from ..extensions import db
from ..models import Estado, Role, StateAction, Ticket, TransicionEstado, User
from ..tickets.service import CLOSED_STATE_CODE, INITIAL_STATE_CODE
from ..tickets.state_actions import (
    AUTOMATIC_ACTIONS,
    ESSENTIAL_REASONS,
    RETURN_ACTIONS,
    STATE_ACTIONS,
)
from .forms import MAX_STATE_DESCRIPTION_LENGTH, MAX_STATE_NAME_LENGTH
from .service import (
    CatalogRuleError,
    DuplicateNameError,
    NothingToChangeError,
    list_states,
)

_DUPLICATE_STATE_NAME = "Ya hay otro estado con ese nombre."

# Los usa el servicio y también la ruta, que los comprueba antes de ofrecer la
# confirmación para no mostrar algo que no se puede hacer.
ALREADY_DISABLED = "Esta transición ya está deshabilitada."
ALREADY_ENABLED = "Esta transición ya está habilitada."


class EssentialTransitionError(CatalogRuleError):
    """La transición es esencial y no puede deshabilitarse."""


class BrokenFlowError(CatalogRuleError):
    """Deshabilitar la transición dejaría el flujo incompleto."""


@dataclass(frozen=True)
class TransitionRow:
    """Una transición lista para mostrarse: la fila, quién ejecuta su acción y
    por qué (si es el caso) no puede deshabilitarse ahora."""

    transition: TransicionEstado
    # Quién la ejecuta, en texto («Técnico, Supervisor y Administrador»).
    performed_by: str
    # Si es esencial, la razón; si no, None.
    essential_reason: str | None
    # Por qué no puede deshabilitarse ahora (esencial o por el flujo), o None.
    blocker: str | None


# --- Consultas --------------------------------------------------------


def count_tickets_by_state() -> dict[int, int]:
    """Cuántos tickets hay en cada estado (`estado_id` -> cantidad)."""
    rows = db.session.execute(
        db.select(Ticket.estado_id, db.func.count()).group_by(Ticket.estado_id)
    )

    return dict(rows.all())


def get_state(state_id: int) -> Estado | None:
    return db.session.get(Estado, state_id)


def get_transition(transition_id: int) -> TransicionEstado | None:
    return db.session.get(TransicionEstado, transition_id)


def list_transitions() -> list[TransitionRow]:
    """Todas las transiciones, por estado de origen y de destino, con lo que la
    pantalla necesita para cada una (quién la ejecuta y si puede
    deshabilitarse). Una sola consulta de transiciones más una de roles."""
    transitions = list(
        db.session.scalars(
            db.select(TransicionEstado)
            .join(Estado, Estado.id == TransicionEstado.estado_origen_id)
            .options(
                joinedload(TransicionEstado.estado_origen),
                joinedload(TransicionEstado.estado_destino),
                joinedload(TransicionEstado.modificada_por),
            )
            .order_by(Estado.orden, TransicionEstado.id)
        )
    )
    role_names = _role_names()
    graph = _Graph.load(transitions)

    return [
        TransitionRow(
            transition=transition,
            performed_by=performed_by(transition.accion, role_names),
            essential_reason=_essential_reason(transition),
            blocker=_blocker_message(transition, graph),
        )
        for transition in transitions
    ]


@dataclass(frozen=True)
class TransitionGroup:
    """Las transiciones que salen de un mismo estado."""

    origin: Estado
    rows: list[TransitionRow]


def group_by_origin(rows: list[TransitionRow]) -> list[TransitionGroup]:
    """Agrupa las filas por estado de origen conservando el orden del flujo
    (las filas ya llegan ordenadas por origen)."""
    groups: list[TransitionGroup] = []

    for row in rows:
        origin = row.transition.estado_origen

        if not groups or groups[-1].origin.id != origin.id:
            groups.append(TransitionGroup(origin=origin, rows=[]))

        groups[-1].rows.append(row)

    return groups


def performed_by(action_code: str, role_names: dict[str, str] | None = None) -> str:
    """Quién ejecuta una acción, para mostrarlo: los roles de las acciones de
    una persona o la explicación de las automáticas."""
    try:
        action = StateAction(action_code)
    except ValueError:
        return "—"

    if action in AUTOMATIC_ACTIONS:
        return AUTOMATIC_ACTIONS[action]

    info = STATE_ACTIONS.get(action)

    if info is None:
        return "—"

    role_names = _role_names() if role_names is None else role_names
    names = [role_names.get(role.value, role.value) for role in info.roles]
    text = _join(names)

    return f"{text} ({info.roles_note})" if info.roles_note else text


# --- Estados ----------------------------------------------------------


def update_state(
    state: Estado,
    *,
    actor: User,
    nombre_visible: str,
    descripcion: str | None,
) -> bool:
    """Cambia el nombre visible y la descripción de un estado.

    El código no cambia nunca. El nombre no puede repetirse entre los seis
    estados (sin distinguir mayúsculas): las seis filas se bloquean mientras se
    comprueba, así que dos Administradores que renombran a la vez no pueden
    dejar dos estados con el mismo nombre. Devuelve False si no cambió nada.
    Audita `ESTADO_MODIFICADO` con solo los campos que cambiaron.
    """
    nombre_visible = _clean_state_name(nombre_visible)
    descripcion = _clean_state_description(descripcion)

    states = _lock_states()
    current = next(s for s in states if s.id == state.id)

    if any(
        other.id != current.id
        and other.nombre_visible.casefold() == nombre_visible.casefold()
        for other in states
    ):
        raise DuplicateNameError(_DUPLICATE_STATE_NAME)

    new_values = {"nombre_visible": nombre_visible, "descripcion": descripcion}
    changed = {
        field: value
        for field, value in new_values.items()
        if getattr(current, field) != value
    }

    if not changed:
        return False

    old_values = {field: getattr(current, field) for field in changed}

    for field, value in changed.items():
        setattr(current, field, value)

    db.session.flush()

    record_admin_event(
        AuditAction.ESTADO_MODIFICADO,
        actor=actor,
        entity_type="estado",
        entity_id=current.id,
        detail=current.codigo,
        old_value=old_values,
        new_value=changed,
    )

    return True


# --- Transiciones -----------------------------------------------------


def transition_blocker(transition: TransicionEstado, *, lock: bool = False) -> str | None:
    """Por qué la transición no puede deshabilitarse, o None si puede.

    Con `lock=True` se bloquean las filas de todas las transiciones
    (`FOR UPDATE`): si dos Administradores deshabilitan a la vez dos
    transiciones que por separado son inofensivas pero juntas romperían el
    flujo, el segundo espera, vuelve a evaluar y ve el resultado del primero.
    """
    problem = _disable_problem(transition, lock=lock)

    return None if problem is None else str(problem)


def deactivate_transition(
    transition: TransicionEstado,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Deshabilita la transición: la acción deja de ofrecerse desde ese estado.

    Los tickets no se tocan. Lanza `EssentialTransitionError` si es esencial y
    `BrokenFlowError` si dejaría el flujo incompleto. Audita
    `TRANSICION_DESACTIVADA`.
    """
    if not transition.activa:
        raise NothingToChangeError(ALREADY_DISABLED)

    problem = _disable_problem(transition, lock=True)

    # Con las filas bloqueadas, `transition` ya muestra lo que otra persona haya
    # hecho mientras tanto: si la deshabilitó ella, no se repite ni se audita.
    if not transition.activa:
        raise NothingToChangeError(ALREADY_DISABLED)

    if problem is not None:
        raise problem

    transition.activa = False
    transition.mark_modified(actor)

    _audit(AuditAction.TRANSICION_DESACTIVADA, transition, actor, reason, was_active=True)


def activate_transition(
    transition: TransicionEstado,
    *,
    actor: User,
    reason: str | None = None,
) -> None:
    """Vuelve a habilitar la transición. Siempre se puede: habilitar nunca deja
    el flujo incoherente. Audita `TRANSICION_ACTIVADA`."""
    if transition.activa:
        raise NothingToChangeError(ALREADY_ENABLED)

    # Se bloquea la fila y se vuelve a leer: si otra persona la habilita a la
    # vez, la segunda lo ve aquí y no lo repite ni lo audita.
    db.session.refresh(transition, with_for_update=True)

    if transition.activa:
        raise NothingToChangeError(ALREADY_ENABLED)

    transition.activa = True
    transition.mark_modified(actor)

    _audit(AuditAction.TRANSICION_ACTIVADA, transition, actor, reason, was_active=False)


def describe_transition(transition: TransicionEstado) -> str:
    """«Origen → Destino (Acción)» con los nombres visibles actuales."""
    return (
        f"{transition.estado_origen.nombre_visible} → "
        f"{transition.estado_destino.nombre_visible} ({transition.accion_nombre})"
    )


# --- Piezas comunes ---------------------------------------------------


class _Graph:
    """Las transiciones como un grafo de estados, para comprobar que el flujo
    sigue completo. Casi no sabe de acciones: solo distingue las que devuelven
    un ticket atrás (`RETURN_ACTIONS`)."""

    def __init__(
        self,
        states: list[Estado],
        edges: list[tuple[int, int, int, bool, str]],
    ):
        self.states = states
        self.by_code = {state.codigo: state for state in states}
        # (id de la transición, origen, destino, activa, código de la acción)
        self.edges = edges

    @classmethod
    def load(cls, transitions: list[TransicionEstado] | None = None, *, lock: bool = False):
        states = _lock_states() if lock else list_states()

        if transitions is None:
            statement = db.select(TransicionEstado)

            if lock:
                statement = statement.with_for_update().execution_options(
                    populate_existing=True
                )

            transitions = list(db.session.scalars(statement))

        edges = [
            (t.id, t.estado_origen_id, t.estado_destino_id, t.activa, t.accion)
            for t in transitions
        ]

        return cls(states, edges)

    def broken_states(self, *, disabling: int | None = None) -> tuple[set[int], set[int]]:
        """(inalcanzables desde el inicial, sin camino hasta el cierre) usando
        las transiciones activas, sin contar la que se quiere deshabilitar.

        Para llegar desde el inicial solo se avanza (las acciones que devuelven
        un ticket atrás no cuentan); para llegar al cierre sirve cualquier
        transición activa."""
        active = [
            (origin, destination, action)
            for transition_id, origin, destination, enabled, action in self.edges
            if enabled and transition_id != disabling
        ]
        advancing = [
            (origin, destination)
            for origin, destination, action in active
            if action not in RETURN_ACTIONS
        ]
        initial = self.by_code.get(INITIAL_STATE_CODE)
        final = self.by_code.get(CLOSED_STATE_CODE)

        # Sin los estados iniciales (una base sin `seed-catalogs`) no hay
        # nada que comprobar.
        if initial is None or final is None:
            return set(), set()

        all_ids = {state.id for state in self.states}
        forward = _reachable(initial.id, advancing)
        backward = _reachable(
            final.id,
            [(destination, origin) for origin, destination, _ in active],
        )

        return all_ids - forward, all_ids - backward


def _reachable(start: int, edges: list[tuple[int, int]]) -> set[int]:
    """Estados a los que se llega desde `start` siguiendo `edges`."""
    seen = {start}
    pending = [start]

    while pending:
        current = pending.pop()

        for origin, destination in edges:
            if origin == current and destination not in seen:
                seen.add(destination)
                pending.append(destination)

    return seen


def _essential_reason(transition: TransicionEstado) -> str | None:
    try:
        return ESSENTIAL_REASONS.get(StateAction(transition.accion))
    except ValueError:
        return None


def _disable_problem(transition: TransicionEstado, *, lock: bool = False):
    """El error que impide deshabilitar la transición, o None."""
    reason = _essential_reason(transition)

    if reason is not None:
        return EssentialTransitionError(
            f"Esta transición es esencial y no se puede deshabilitar. {reason}"
        )

    return _flow_problem(transition, _Graph.load(lock=lock))


def _blocker_message(transition: TransicionEstado, graph: _Graph) -> str | None:
    """Lo mismo que `transition_blocker`, reutilizando un grafo ya cargado (el
    listado evalúa todas las transiciones con una sola carga)."""
    reason = _essential_reason(transition)

    if reason is not None:
        return f"Esta transición es esencial y no se puede deshabilitar. {reason}"

    if not transition.activa:
        return None

    problem = _flow_problem(transition, graph)

    return None if problem is None else str(problem)


def _flow_problem(transition: TransicionEstado, graph: _Graph):
    """`BrokenFlowError` si deshabilitar la transición dejaría algún estado
    inalcanzable desde el inicial o sin camino hasta el cierre. Solo cuenta lo
    que empeora: un flujo que ya estuviera roto no bloquea transiciones que no
    tienen que ver."""
    before_unreachable, before_stuck = graph.broken_states()
    after_unreachable, after_stuck = graph.broken_states(disabling=transition.id)
    initial = graph.by_code.get(INITIAL_STATE_CODE)
    final = graph.by_code.get(CLOSED_STATE_CODE)

    # Los estados se recorren en el orden del flujo para dar el primero.
    unreachable = next(
        (s for s in graph.states if s.id in after_unreachable - before_unreachable),
        None,
    )

    if unreachable is not None:
        return BrokenFlowError(
            f"No se puede deshabilitar: «{unreachable.nombre_visible}» dejaría "
            f"de ser alcanzable desde «{initial.nombre_visible}»."
        )

    stuck = next(
        (s for s in graph.states if s.id in after_stuck - before_stuck),
        None,
    )

    if stuck is not None:
        return BrokenFlowError(
            f"No se puede deshabilitar: desde «{stuck.nombre_visible}» ya no se "
            f"podría llegar a «{final.nombre_visible}», y los tickets quedarían "
            "atascados."
        )

    return None


def _audit(action, transition, actor, reason, *, was_active: bool) -> None:
    record_admin_event(
        action,
        actor=actor,
        entity_type="transicion",
        entity_id=transition.id,
        detail=describe_transition(transition),
        old_value={"activa": was_active},
        new_value={"activa": not was_active},
        reason=blank_to_none(reason),
    )


def _lock_states() -> list[Estado]:
    """Los seis estados bloqueados (`FOR UPDATE`) y con sus valores al día."""
    return list(
        db.session.scalars(
            db.select(Estado)
            .order_by(Estado.orden)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )


def _role_names() -> dict[str, str]:
    """Nombre visible de cada rol por su código."""
    return {role.codigo: role.nombre for role in db.session.scalars(db.select(Role))}


def _join(names: list[str]) -> str:
    """«A», «A y B», «A, B y C»."""
    if len(names) <= 1:
        return "".join(names)

    return f"{', '.join(names[:-1])} y {names[-1]}"


def _clean_state_name(nombre: str | None) -> str:
    nombre = (nombre or "").strip()

    if not nombre:
        raise CatalogRuleError("El nombre es obligatorio.")

    if len(nombre) > MAX_STATE_NAME_LENGTH:
        raise CatalogRuleError(
            f"El nombre no puede superar los {MAX_STATE_NAME_LENGTH} caracteres."
        )

    return nombre


def _clean_state_description(descripcion: str | None) -> str | None:
    descripcion = blank_to_none(descripcion)

    if descripcion is not None and len(descripcion) > MAX_STATE_DESCRIPTION_LENGTH:
        raise CatalogRuleError(
            "La descripción no puede superar los "
            f"{MAX_STATE_DESCRIPTION_LENGTH} caracteres."
        )

    return descripcion
