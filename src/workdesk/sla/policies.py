"""Políticas de SLA por prioridad (docs/09, 20.2; docs/11, UI-022).

Una política dice cuánto tiempo laboral tiene un ticket de cierta prioridad para
recibir su primera respuesta (opcional) y para resolverse, a partir de qué
consumo se considera «próximo a vencer» y si el reloj se detiene mientras el
ticket está en espera. Estas son las reglas que la gobiernan:

- **Una política por prioridad.** El servicio nunca crea una segunda fila para
  la misma prioridad (activa o no) y un índice único parcial impide dos activas.
  Desactivarla significa que esa prioridad no tiene SLA; reactivarla la devuelve
  con los objetivos que tenía.
- **Se edita en el sitio.** A diferencia del calendario laboral, una política no
  se versiona: lo que ya se calculó no cambia porque cada ticket guardará su
  propia copia de los objetivos en el período de SLA que abra (docs/09, 20.1 y
  20.3). Cada cambio queda en la auditoría con sus valores anterior y nuevo.
- **Quien edita dice qué vio.** El formulario lleva una marca de la política tal
  como estaba al abrirlo (`policy_token`). Si otra persona la cambió mientras
  tanto, no se guarda nada y se avisa, como con el calendario y con la versión de
  un ticket: pisar un cambio que no se vio no es una opción.
- **Las operaciones sobre una misma prioridad se serializan** bloqueando la fila
  de la prioridad. Así, dos Administradores que definen la política de la misma
  prioridad a la vez no la crean dos veces, y quien llega segundo ve el resultado
  del primero. El bloqueo es el más débil que sirve (`FOR NO KEY UPDATE`): no
  frena la creación de tickets de esa prioridad, que solo necesita leer su clave.
- **Los tiempos son minutos laborales**: se miden con el calendario vigente
  (`worktime.py`), no con el reloj de pared.

Ninguna función hace commit: el cambio y su evento de auditoría se confirman o se
revierten juntos, y el commit lo realiza quien llama.
"""

from dataclasses import dataclass
from datetime import UTC
from enum import StrEnum

from sqlalchemy.exc import IntegrityError

from ..audit import AuditAction, record_admin_event
from ..cleaning import blank_to_none
from ..extensions import db
from ..formatting import format_duration
from ..models import Estado, PoliticaSla, Prioridad, User
from ..models.estado import ON_HOLD_STATE_CODE

# Valor de `entidad_tipo` en la auditoría.
ENTITY_TYPE = "politica_sla"

# Un tope razonable para un objetivo (1000 horas laborales): atrapa un error de
# tipeo (un cero de más) sin impedir ningún plazo realista.
MAX_TARGET_HOURS = 1000
MAX_TARGET_MINUTES = MAX_TARGET_HOURS * 60

# La marca de «todavía no hay política» (ver `policy_token`).
NO_POLICY_TOKEN = "0"

CONFLICT_MESSAGE = (
    "Otra persona modificó los objetivos de esta prioridad mientras los "
    "editabas. Revisa los valores vigentes y vuelve a intentarlo."
)


class PolicyRuleError(ValueError):
    """Una regla impide guardar la política. El mensaje se muestra a quien la edita.

    `field` es el campo del formulario al que pertenece el problema, si es de uno
    solo (`primera_respuesta`, `resolucion` o `umbral_aviso`).
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class PolicyConflictError(PolicyRuleError):
    """Otra persona cambió la política mientras esta pantalla estaba abierta."""


class NothingToChangeError(PolicyRuleError):
    """La operación no cambiaría nada."""


class SaveOutcome(StrEnum):
    CREATED = "creada"
    UPDATED = "modificada"
    UNCHANGED = "sin cambios"


@dataclass(frozen=True)
class SaveResult:
    policy: PoliticaSla
    outcome: SaveOutcome


@dataclass(frozen=True)
class PolicyRow:
    """Una fila de la pantalla: la prioridad y su política, si ya tiene una."""

    priority: Prioridad
    policy: PoliticaSla | None


# --- Consultas ------------------------------------------------------------------


def list_policy_rows() -> list[PolicyRow]:
    """Todas las prioridades de menor a mayor nivel, cada una con su política.

    Una sola consulta: la política viene en el mismo `JOIN`, sin una consulta por
    prioridad.
    """
    statement = (
        db.select(Prioridad, PoliticaSla)
        .outerjoin(PoliticaSla, PoliticaSla.prioridad_id == Prioridad.id)
        .order_by(Prioridad.nivel, Prioridad.id)
    )

    return [
        PolicyRow(priority, policy)
        for priority, policy in db.session.execute(statement)
    ]


def get_priority(priority_id: int) -> Prioridad | None:
    return db.session.get(Prioridad, priority_id)


def get_policy(priority: Prioridad) -> PoliticaSla | None:
    return db.session.scalar(
        db.select(PoliticaSla).where(PoliticaSla.prioridad_id == priority.id)
    )


def on_hold_state_name() -> str:
    """El nombre visible del estado en que el SLA puede pausarse.

    El Administrador puede renombrar los estados, así que los textos de las
    pantallas no lo escriben a mano.
    """
    name = db.session.scalar(
        db.select(Estado.nombre_visible).where(Estado.codigo == ON_HOLD_STATE_CODE)
    )

    return name or "En espera"


def policy_token(policy: PoliticaSla | None) -> str:
    """La marca que identifica en qué estado está una política.

    Cambia con cada modificación, activación o desactivación (todas anotan la
    fecha). El formulario la lleva escondida y, al guardar, se compara con la
    actual: si no coinciden, otra persona cambió la política mientras tanto.
    `NO_POLICY_TOKEN` marca «todavía no hay política».
    """
    if policy is None:
        return NO_POLICY_TOKEN

    stamp = policy.fecha_modificacion or policy.fecha_creacion

    return stamp.astimezone(UTC).isoformat()


# --- Reglas de los valores -------------------------------------------------------


def policy_problems(
    *,
    response_minutes: int | None,
    resolution_minutes: int | None,
    warning_percent: int | None,
) -> dict[str, str]:
    """Lo que está mal en los valores de una política, por campo del formulario.

    Es la regla única: la usan el formulario (para señalar cada error junto a su
    campo, todos a la vez) y `save_policy` (que la aplica de todos modos, porque
    el servicio no confía en quien lo llama). `None` en la resolución significa
    que falta; en la primera respuesta o el umbral, que no se definió.
    """
    problems: dict[str, str] = {}
    max_text = format_duration(MAX_TARGET_MINUTES)

    if resolution_minutes is None:
        problems["resolucion"] = "Ingresa el objetivo de resolución."
    elif resolution_minutes <= 0:
        problems["resolucion"] = (
            "El objetivo de resolución debe ser mayor que cero."
        )
    elif resolution_minutes > MAX_TARGET_MINUTES:
        problems["resolucion"] = (
            f"El objetivo de resolución no puede superar {max_text}."
        )

    if response_minutes is not None:
        if response_minutes <= 0:
            problems["primera_respuesta"] = (
                "El objetivo de primera respuesta debe ser mayor que cero. "
                "Déjalo vacío si no quieres uno."
            )
        elif response_minutes > MAX_TARGET_MINUTES:
            problems["primera_respuesta"] = (
                f"El objetivo de primera respuesta no puede superar {max_text}."
            )
        # Solo se compara con una resolución válida: si ya está mal, ese es el
        # problema que hay que señalar.
        elif "resolucion" not in problems and response_minutes > resolution_minutes:
            problems["primera_respuesta"] = (
                "La primera respuesta no puede tardar más que la resolución "
                f"({format_duration(resolution_minutes)})."
            )

    if warning_percent is not None and not 1 <= warning_percent <= 100:
        problems["umbral_aviso"] = "El umbral debe estar entre 1 y 100."

    return problems


# --- Alta y edición --------------------------------------------------------------


def save_policy(
    priority: Prioridad,
    *,
    actor: User,
    base_token: str,
    response_minutes: int | None,
    resolution_minutes: int,
    warning_percent: int | None,
    pause_on_hold: bool,
    reason: str | None = None,
) -> SaveResult:
    """Define o edita los objetivos de SLA de la prioridad.

    Si la prioridad todavía no tiene política la crea (activa); si ya la tiene,
    aplica solo los campos que cambiaron. `base_token` es la marca de la política
    tal como estaba al abrir la pantalla (`policy_token`): si otra persona la
    cambió mientras tanto, lanza `PolicyConflictError` sin guardar nada. Una
    política desactivada puede editarse y sigue desactivada.

    Lanza `PolicyRuleError` si un valor no es válido y devuelve
    `SaveOutcome.UNCHANGED`, sin auditar, si nada cambió.
    """
    problems = policy_problems(
        response_minutes=response_minutes,
        resolution_minutes=resolution_minutes,
        warning_percent=warning_percent,
    )

    if problems:
        field, message = next(iter(problems.items()))

        raise PolicyRuleError(message, field)

    policy = _lock_policy(priority)

    if base_token != policy_token(policy):
        raise PolicyConflictError(CONFLICT_MESSAGE)

    values = {
        "tiempo_objetivo_respuesta_minutos": response_minutes,
        "tiempo_objetivo_resolucion_minutos": resolution_minutes,
        "umbral_aviso_consumo_porcentaje": warning_percent,
        "pausa_en_espera": bool(pause_on_hold),
    }
    reason = blank_to_none(reason)

    if policy is None:
        return _create_policy(priority, actor, values, reason)

    return _update_policy(priority, policy, actor, values, reason)


def _create_policy(
    priority: Prioridad,
    actor: User,
    values: dict,
    reason: str | None,
) -> SaveResult:
    policy = PoliticaSla(
        prioridad_id=priority.id,
        usuario_creacion_id=actor.id,
        **values,
    )

    # Bajo el bloqueo de la prioridad dos altas no pueden chocar, pero el índice
    # único parcial es la última defensa (por ejemplo, ante otra vía que escriba
    # en la tabla sin ese bloqueo): el savepoint deshace solo este intento.
    try:
        with db.session.begin_nested():
            db.session.add(policy)
            db.session.flush()
    except IntegrityError as error:
        raise PolicyConflictError(CONFLICT_MESSAGE) from error

    record_admin_event(
        AuditAction.POLITICA_SLA_CREADA,
        actor=actor,
        entity_type=ENTITY_TYPE,
        entity_id=policy.id,
        detail=_detail(priority),
        new_value={**values, "activo": True},
        reason=reason,
    )

    return SaveResult(policy, SaveOutcome.CREATED)


def _update_policy(
    priority: Prioridad,
    policy: PoliticaSla,
    actor: User,
    values: dict,
    reason: str | None,
) -> SaveResult:
    changed = {
        field: value
        for field, value in values.items()
        if getattr(policy, field) != value
    }

    if not changed:
        return SaveResult(policy, SaveOutcome.UNCHANGED)

    old_values = {field: getattr(policy, field) for field in changed}

    for field, value in changed.items():
        setattr(policy, field, value)

    policy.mark_modified(actor)
    db.session.flush()

    record_admin_event(
        AuditAction.POLITICA_SLA_MODIFICADA,
        actor=actor,
        entity_type=ENTITY_TYPE,
        entity_id=policy.id,
        detail=_detail(priority),
        old_value=old_values,
        new_value=changed,
        reason=reason,
    )

    return SaveResult(policy, SaveOutcome.UPDATED)


# --- Activación y desactivación -------------------------------------------------


def deactivate_policy(
    priority: Prioridad,
    *,
    actor: User,
    reason: str | None = None,
) -> PoliticaSla:
    """Desactiva la política: la prioridad deja de tener SLA.

    No toca el SLA que los tickets ya tienen en curso: cada uno conserva sus
    objetivos (docs/09, 20.1). Audita `POLITICA_SLA_DESACTIVADA`.
    """
    policy = _require_policy(priority)

    if not policy.activo:
        raise NothingToChangeError("La política ya está desactivada.")

    policy.activo = False
    policy.mark_modified(actor)
    db.session.flush()

    record_admin_event(
        AuditAction.POLITICA_SLA_DESACTIVADA,
        actor=actor,
        entity_type=ENTITY_TYPE,
        entity_id=policy.id,
        detail=_detail(priority),
        old_value={"activo": True},
        new_value={"activo": False},
        reason=blank_to_none(reason),
    )

    return policy


def activate_policy(
    priority: Prioridad,
    *,
    actor: User,
    reason: str | None = None,
) -> PoliticaSla:
    """Reactiva la política con los objetivos que tenía. Audita
    `POLITICA_SLA_ACTIVADA`."""
    policy = _require_policy(priority)

    if policy.activo:
        raise NothingToChangeError("La política ya está activa.")

    try:
        with db.session.begin_nested():
            policy.activo = True
            policy.mark_modified(actor)
            db.session.flush()
    except IntegrityError as error:
        raise PolicyRuleError(
            "No se puede reactivar: la prioridad ya tiene otra política activa."
        ) from error

    record_admin_event(
        AuditAction.POLITICA_SLA_ACTIVADA,
        actor=actor,
        entity_type=ENTITY_TYPE,
        entity_id=policy.id,
        detail=_detail(priority),
        old_value={"activo": False},
        new_value={"activo": True},
        reason=blank_to_none(reason),
    )

    return policy


# --- Piezas comunes --------------------------------------------------------------


def _lock_policy(priority: Prioridad) -> PoliticaSla | None:
    """Bloquea la prioridad y devuelve su política, leída de nuevo, o None.

    Todas las operaciones de escritura empiezan aquí, así que se ejecutan de una
    en una por prioridad y cada una ve lo que confirmó la anterior (de ahí
    `populate_existing`: sin él, la sesión podría devolver una copia vieja).
    """
    db.session.execute(
        db.select(Prioridad.id)
        .where(Prioridad.id == priority.id)
        .with_for_update(key_share=True)
    )

    return db.session.scalar(
        db.select(PoliticaSla)
        .where(PoliticaSla.prioridad_id == priority.id)
        .execution_options(populate_existing=True)
    )


def _require_policy(priority: Prioridad) -> PoliticaSla:
    policy = _lock_policy(priority)

    if policy is None:
        raise PolicyRuleError(
            "Esta prioridad todavía no tiene una política de SLA."
        )

    return policy


def _detail(priority: Prioridad) -> str:
    return f"Prioridad {priority.nombre}"
