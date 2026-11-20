"""Relaciones entre tickets y duplicados (docs/06, RN-162; docs/09, 19).

Hay dos tipos (`RelationType`):

- **`RELACIONADO`**: dos tickets conectados, sin dirección. El par se guarda
  normalizado (id menor primero), así «A con B» y «B con A» son la misma
  relación. Se puede agregar y quitar mientras el ticket desde el que se actúa
  esté abierto; el otro ticket puede estar en cualquier estado.
- **`DUPLICADO`**: va del ticket duplicado al principal. Marcar un ticket como
  duplicado **crea la relación y cierra el ticket duplicado** con el motivo de
  cierre «Duplicado» (no existe un estado «Duplicado»). No transfiere
  comentarios, adjuntos ni solicitantes al principal y cada ticket conserva su
  historial. La relación es el rastro del cierre: mientras el duplicado siga
  cerrado no se quita; si se reabre, sí.

Para que la trazabilidad siga siendo simple, un ticket duplicado apunta siempre
a un principal que **no** es a su vez un duplicado, y un ticket que ya es el
principal de otros no puede pasar a ser duplicado: no hay cadenas ni ciclos.

Las relaciones son del personal: el Solicitante no las ve (RN-162). Quién puede
gestionarlas lo decide la capa de rutas con `can_manage_relations`; aquí viven
las reglas de los datos. Nada hace commit: la relación, su evento y, en un
duplicado, el cierre se confirman o se revierten juntos.

Agregar o quitar una relación no sube la versión del ticket (es aditivo, como
asignar técnicos o agregar solicitantes); marcar un duplicado sí, porque cierra
el ticket. El evento se registra en el ticket desde el que se actúa; el otro
ticket muestra la relación en su tarjeta (con quién y cuándo), que sale de la
propia tabla.
"""

import re
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    RelationType,
    StateAction,
    Ticket,
    TicketEvent,
    TicketRelation,
    TipoRelacionTicket,
    User,
)
from .lifecycle import DUPLICATE_CLOSE_REASON, change_state
from .service import (
    CLOSED_STATE_CODE,
    TicketRuleError,
    get_ticket_by_public_id,
    record_ticket_event,
)
from .versioning import begin_ticket_operation, lock_ticket

# Contexto opcional de una relación.
MAX_RELATION_COMMENT_LENGTH = 500

# Cómo se ve una relación desde un ticket concreto.
KIND_DUPLICATE_OF = "duplicado_de"  # este ticket es duplicado de `other`
KIND_PRINCIPAL_OF = "principal_de"  # `other` es duplicado de este ticket
KIND_RELATED = "relacionado"

_NUMBER = re.compile(r"#?\s*(\d{1,18})")


@dataclass(frozen=True)
class RelationView:
    """Una relación vista desde un ticket: de qué clase es y con cuál."""

    kind: str
    relation: TicketRelation
    other: Ticket
    # Una relación se puede quitar salvo la de un duplicado que sigue cerrado
    # (es el rastro del cierre).
    removable: bool


# --- Consultas --------------------------------------------------------


def parse_ticket_number(value: str | None) -> str:
    """Número de ticket escrito por una persona («12» o «#12»).

    Lanza `TicketRuleError` si no es un número.
    """
    match = _NUMBER.fullmatch((value or "").strip())

    if match is None:
        raise TicketRuleError("Escribe el número del ticket, por ejemplo 12.")

    return str(int(match.group(1)))


def list_relations(ticket: Ticket) -> list[RelationView]:
    """Las relaciones vigentes del ticket, con el otro ticket cargado (y su
    estado) en una sola consulta: primero de qué es duplicado, luego sus
    duplicados y al final los relacionados."""
    relations = db.session.scalars(
        db.select(TicketRelation)
        .where(
            TicketRelation.activo.is_(True),
            db.or_(
                TicketRelation.ticket_origen_id == ticket.id,
                TicketRelation.ticket_destino_id == ticket.id,
            ),
        )
        .options(
            joinedload(TicketRelation.origen).joinedload(Ticket.estado),
            joinedload(TicketRelation.destino).joinedload(Ticket.estado),
            joinedload(TicketRelation.tipo),
            joinedload(TicketRelation.creada_por),
        )
        .order_by(TicketRelation.fecha_creacion, TicketRelation.id)
    ).all()

    views = []

    for relation in relations:
        is_origin = relation.ticket_origen_id == ticket.id
        other = relation.destino if is_origin else relation.origen

        if relation.tipo.codigo == RelationType.DUPLICADO:
            kind = KIND_DUPLICATE_OF if is_origin else KIND_PRINCIPAL_OF
        else:
            kind = KIND_RELATED

        removable = not (
            kind != KIND_RELATED
            and relation.origen.estado.codigo == CLOSED_STATE_CODE
        )

        views.append(
            RelationView(
                kind=kind,
                relation=relation,
                other=other,
                removable=removable,
            )
        )

    order = {KIND_DUPLICATE_OF: 0, KIND_PRINCIPAL_OF: 1, KIND_RELATED: 2}

    return sorted(views, key=lambda view: order[view.kind])


def duplicate_of(ticket: Ticket) -> TicketRelation | None:
    """La relación vigente que dice de qué ticket es duplicado, si lo es."""
    return db.session.scalar(_duplicate_query().where(
        TicketRelation.ticket_origen_id == ticket.id
    ))


# --- Relacionar y desrelacionar ---------------------------------------


def add_relation(
    ticket: Ticket,
    other_number: str,
    *,
    actor: User,
    comment: str | None = None,
) -> TicketRelation:
    """Relaciona el ticket con otro (`RELACIONADO`).

    `other_number` es el número del otro ticket. No puede ser el mismo ticket
    ni uno con el que ya exista una relación vigente. El otro ticket puede
    estar en cualquier estado. Registra `RELACION_AGREGADA` (evento interno).
    Un ticket cerrado lanza `TicketClosedError`.
    """
    begin_ticket_operation(ticket, actor)

    other = _find_ticket(other_number)
    comment = _clean_comment(comment)

    if other.id == ticket.id:
        raise TicketRuleError("Un ticket no puede relacionarse consigo mismo.")

    existing = _active_between(ticket, other)

    if existing is not None:
        raise TicketRuleError(_already_linked_message(existing))

    low, high = sorted((ticket.id, other.id))
    relation = TicketRelation(
        ticket_origen_id=low,
        ticket_destino_id=high,
        tipo_relacion_id=_type(RelationType.RELACIONADO).id,
        comentario=comment,
        usuario_creacion_id=actor.id,
    )

    # La fila del ticket ya está bloqueada; el índice único del par vigente es
    # el respaldo si otra persona relaciona los mismos tickets desde el otro
    # lado, y el savepoint deshace solo este intento.
    try:
        with db.session.begin_nested():
            db.session.add(relation)
            db.session.flush()
    except IntegrityError as error:
        raise TicketRuleError(
            "Estos tickets ya están relacionados."
        ) from error

    record_ticket_event(
        ticket,
        TicketEvent.RELACION_AGREGADA,
        actor=actor,
        detail=f"Relacionado con #{other.public_id}.",
        new_value=_relation_snapshot(relation, RelationType.RELACIONADO, other),
        context={"relacion_id": relation.id},
    )

    return relation


def remove_relation(ticket: Ticket, relation_id: int, *, actor: User) -> None:
    """Quita una relación del ticket (eliminación lógica: la relación se
    conserva como historial).

    La relación de un duplicado que sigue cerrado no se quita: es el rastro
    del cierre (si se cerró por error, se reabre y entonces se puede quitar).
    Registra `RELACION_ELIMINADA` (evento interno). Un ticket cerrado lanza
    `TicketClosedError`.
    """
    begin_ticket_operation(ticket, actor)

    relation = db.session.scalar(
        db.select(TicketRelation)
        .where(
            TicketRelation.id == relation_id,
            TicketRelation.activo.is_(True),
            db.or_(
                TicketRelation.ticket_origen_id == ticket.id,
                TicketRelation.ticket_destino_id == ticket.id,
            ),
        )
        .options(
            joinedload(TicketRelation.origen).joinedload(Ticket.estado),
            joinedload(TicketRelation.destino),
            joinedload(TicketRelation.tipo),
        )
        .with_for_update(of=TicketRelation)
    )

    if relation is None:
        raise TicketRuleError("Esa relación ya no existe.")

    if (
        relation.tipo.codigo == RelationType.DUPLICADO
        and relation.origen.estado.codigo == CLOSED_STATE_CODE
    ):
        raise TicketRuleError(
            "El ticket duplicado sigue cerrado: la relación es el rastro del "
            "cierre. Si se cerró por error, reábrelo y luego quita la relación."
        )

    other = (
        relation.destino
        if relation.ticket_origen_id == ticket.id
        else relation.origen
    )

    # La hora la pone la base de datos, como `fecha_creacion`.
    relation.activo = False
    relation.fecha_desactivacion = func.now()
    relation.usuario_desactivacion_id = actor.id
    db.session.flush()

    record_ticket_event(
        ticket,
        TicketEvent.RELACION_ELIMINADA,
        actor=actor,
        detail=f"Relación con #{other.public_id} eliminada.",
        old_value=_relation_snapshot(
            relation, RelationType(relation.tipo.codigo), other
        ),
        context={"relacion_id": relation.id},
    )


# --- Duplicados -------------------------------------------------------


def mark_duplicate(
    ticket: Ticket,
    principal_number: str,
    *,
    actor: User,
    expected_version: int,
    comment: str | None = None,
) -> TicketRelation:
    """Marca el ticket como duplicado de otro y lo cierra.

    Crea la relación `DUPLICADO` (del duplicado al principal), registra
    `RELACION_AGREGADA` y cierra el ticket con el motivo «Duplicado» por el
    mismo camino del cierre directo (`change_state`), de modo que el ticket
    cerrado tiene fecha y motivo de cierre como cualquier otro. Reglas:

    - el principal existe (en cualquier estado) y es otro ticket;
    - el principal no es a su vez un duplicado, y el ticket no es el principal
      de otros duplicados (no hay cadenas);
    - el ticket debe poder cerrarse directamente (Nuevo, Asignado, En progreso
      o En espera); un ticket cerrado lanza `TicketClosedError`.

    Bloquea las dos filas, en orden de id para que dos personas que actúan a la
    vez sobre el mismo par no se bloqueen entre sí. Sube la versión del ticket.
    """
    if not actor.is_active:
        raise TicketRuleError("El usuario no está activo.")

    principal = _find_ticket(principal_number)

    if principal.id == ticket.id:
        raise TicketRuleError("Un ticket no puede ser duplicado de sí mismo.")

    for locked in sorted((ticket, principal), key=lambda t: t.id):
        lock_ticket(locked)

    # Comprueba (con las filas ya bloqueadas) que el ticket no esté cerrado.
    begin_ticket_operation(ticket, actor)

    comment = _clean_comment(comment)

    current = duplicate_of(ticket)

    if current is not None:
        raise TicketRuleError(
            "Este ticket ya figura como duplicado de otro. Si no lo es, quita "
            "esa relación primero."
        )

    if db.session.scalar(_duplicate_query().where(
        TicketRelation.ticket_origen_id == principal.id
    )) is not None:
        raise TicketRuleError(
            f"El ticket #{principal.public_id} ya es un duplicado de otro: "
            "elige el ticket principal."
        )

    if db.session.scalar(_duplicate_query().where(
        TicketRelation.ticket_destino_id == ticket.id
    )) is not None:
        raise TicketRuleError(
            "Hay tickets marcados como duplicados de este: no puede ser a su "
            "vez un duplicado. Márcalos contra el ticket principal."
        )

    relation = TicketRelation(
        ticket_origen_id=ticket.id,
        ticket_destino_id=principal.id,
        tipo_relacion_id=_type(RelationType.DUPLICADO).id,
        comentario=comment,
        usuario_creacion_id=actor.id,
    )

    try:
        with db.session.begin_nested():
            db.session.add(relation)
            db.session.flush()
    except IntegrityError as error:
        raise TicketRuleError(
            "Este ticket ya está marcado como duplicado de ese ticket."
        ) from error

    record_ticket_event(
        ticket,
        TicketEvent.RELACION_AGREGADA,
        actor=actor,
        detail=f"Marcado como duplicado de #{principal.public_id}.",
        new_value=_relation_snapshot(relation, RelationType.DUPLICADO, principal),
        context={"relacion_id": relation.id},
    )

    # El cierre: mismo camino que el cierre directo, con el motivo que fija
    # este flujo y el ticket principal en el evento.
    change_state(
        ticket,
        actor=actor,
        action=StateAction.CIERRE_DIRECTO,
        expected_version=expected_version,
        close_reason_code=DUPLICATE_CLOSE_REASON,
        extra_context={
            "duplicado_de": principal.public_id,
            "relacion_id": relation.id,
        },
    )

    return relation


# --- Piezas comunes ---------------------------------------------------


def _find_ticket(number: str) -> Ticket:
    """El ticket con ese número (cualquier estado) o `TicketRuleError`."""
    other = get_ticket_by_public_id(parse_ticket_number(number))

    if other is None:
        raise TicketRuleError(f"No existe el ticket #{parse_ticket_number(number)}.")

    return other


def _type(code: RelationType) -> TipoRelacionTicket:
    relation_type = db.session.scalar(
        db.select(TipoRelacionTicket).where(
            TipoRelacionTicket.codigo == code.value,
            TipoRelacionTicket.activo.is_(True),
        )
    )

    if relation_type is None:
        raise TicketRuleError(
            "Falta el tipo de relación. Pide al Administrador que ejecute "
            "`seed-catalogs`."
        )

    return relation_type


def _duplicate_query():
    """Relaciones `DUPLICADO` vigentes (el llamador filtra por ticket)."""
    return (
        db.select(TicketRelation)
        .join(
            TipoRelacionTicket,
            TipoRelacionTicket.id == TicketRelation.tipo_relacion_id,
        )
        .where(
            TipoRelacionTicket.codigo == RelationType.DUPLICADO.value,
            TicketRelation.activo.is_(True),
        )
        .limit(1)
    )


def _active_between(first: Ticket, second: Ticket) -> TicketRelation | None:
    """Una relación vigente entre los dos tickets, del tipo que sea."""
    return db.session.scalar(
        db.select(TicketRelation)
        .where(
            TicketRelation.activo.is_(True),
            db.or_(
                db.and_(
                    TicketRelation.ticket_origen_id == first.id,
                    TicketRelation.ticket_destino_id == second.id,
                ),
                db.and_(
                    TicketRelation.ticket_origen_id == second.id,
                    TicketRelation.ticket_destino_id == first.id,
                ),
            ),
        )
        .options(joinedload(TicketRelation.tipo))
        .limit(1)
    )


def _already_linked_message(relation: TicketRelation) -> str:
    if relation.tipo.codigo == RelationType.DUPLICADO:
        return "Estos tickets ya están vinculados como duplicado."

    return "Estos tickets ya están relacionados."


def _clean_comment(comment: str | None) -> str | None:
    comment = (comment or "").strip()

    if len(comment) > MAX_RELATION_COMMENT_LENGTH:
        raise TicketRuleError(
            f"El comentario no puede superar los {MAX_RELATION_COMMENT_LENGTH} "
            "caracteres."
        )

    return comment or None


def _relation_snapshot(
    relation: TicketRelation,
    code: RelationType,
    other: Ticket,
) -> dict:
    return {
        "relacion_id": relation.id,
        "tipo": code.value,
        "ticket": other.public_id,
        "titulo": other.titulo,
    }
