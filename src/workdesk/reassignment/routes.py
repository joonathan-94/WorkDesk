"""Pantallas de la reasignación masiva (docs/11, UI-007; docs/07, CU-014).

Flujo en tres pasos, sin modales y sin JavaScript obligatorio:

1. `GET /reassign`: elegir el técnico de origen, ver sus tickets activos (con filtros), elegir
   cuáles pasar, a qué técnicos y por qué.
2. `POST /reassign/review`: el resumen de la operación, con el reparto ticket por ticket, antes
   de confirmar. No cambia nada.
3. `POST /reassign/confirm`: ejecuta y muestra el resultado (movidos y omitidos).

**El servidor no confía en lo que viaja por el navegador.** El resumen lleva el reparto en campos
ocultos, pero `reassign_tickets` vuelve a validar cada ticket al confirmar (puede haber cambiado
entre un paso y otro) y comprueba el permiso por su cuenta. Solo el Supervisor y el
Administrador entran (403 al resto).
"""

from flask import abort, flash, redirect, render_template, request, url_for

from ..catalogs.service import list_priorities
from ..extensions import db
from ..models import Estado, Ticket, TicketTechnician, User
from ..security import RoleCode, current_actor, roles_required
from ..sla.periods import STOPPING_STATES
from ..tickets.assignment import list_escalation_technicians
from ..tickets.queries import (
    SORT_RECENT,
    TAB_ALL,
    TicketFilters,
    active_state_condition,
    list_group_options,
    list_states,
    list_tickets,
)
from ..tickets.reassignment import MAX_REASON_LENGTH, distribute, reassign_tickets
from ..tickets.service import TicketRuleError
from ..workload import workload_overview
from . import bp

area_only = roles_required(RoleCode.SUPERVISOR, RoleCode.ADMINISTRADOR)

# Una lista con más tickets que esto se recorta (con aviso): se filtra para ver el resto.
MAX_TICKETS_SHOWN = 500


# --- Paso 1: elegir ----------------------------------------------------------------


@bp.get("")
@area_only
def select_page():
    return _select(request.args.get("origen", type=int))


def _select(origin_id, *, tickets_chosen=None, destinations_chosen=None, reason=""):
    actor = current_actor()
    overview = workload_overview(actor)
    loads = {row.user.id: row for row in overview.technicians}
    origin = loads.get(origin_id)

    states = [state for state in list_states() if state.codigo not in STOPPING_STATES]
    priorities = list_priorities("")
    groups = list_group_options()
    filters = {
        "prioridad": _choice("prioridad", priorities),
        "estado": _choice("estado", states),
        "grupo": _choice("grupo", groups),
    }

    tickets, total = [], 0

    if origin is not None:
        page = list_tickets(
            actor,
            TicketFilters(
                technician_id=origin.user.id,
                active_only=True,
                priority_id=filters["prioridad"],
                state_id=filters["estado"],
                group_id=filters["grupo"],
            ),
            tab=TAB_ALL,
            sort=SORT_RECENT,
            per_page=MAX_TICKETS_SHOWN,
        )
        tickets, total = list(page.items), page.total

    destinations = [
        user
        for user in list_escalation_technicians()
        if origin is None or user.id != origin.user.id
    ]

    return render_template(
        "reassignment/select.html",
        sources=overview.technicians,
        origin=origin,
        tickets=tickets,
        total=total,
        truncated=total > len(tickets),
        destinations=destinations,
        loads=loads,
        states=states,
        priorities=priorities,
        groups=groups,
        filters=filters,
        # Lo marcado: todo al abrir (se desmarca lo que no se quiere mover) o lo enviado.
        tickets_chosen={t.id for t in tickets} if tickets_chosen is None else tickets_chosen,
        destinations_chosen=destinations_chosen or set(),
        reason=reason,
        max_reason=MAX_REASON_LENGTH,
    )


# --- Paso 2: revisar ---------------------------------------------------------------


@bp.post("/review")
@area_only
def review():
    actor = current_actor()
    origin_id = request.form.get("origen", type=int)
    ticket_ids = _ints("tickets")
    destination_ids = _ints("destinos")
    reason = " ".join(request.form.get("motivo", "").split())

    def back(problems):
        for problem in problems:
            flash(problem, "error")

        return _select(
            origin_id,
            tickets_chosen=set(ticket_ids),
            destinations_chosen=set(destination_ids),
            reason=reason,
        )

    overview = workload_overview(actor)
    loads = {row.user.id: row for row in overview.technicians}

    if origin_id not in loads:
        flash("Elige el técnico de origen.", "error")

        return redirect(url_for("reassignment.select_page"))

    origin = loads[origin_id].user
    candidates = {user.id: user for user in list_escalation_technicians() if user.id != origin_id}

    problems = _problems(ticket_ids, destination_ids, candidates, reason)

    if problems:
        return back(problems)

    # Solo siguen siendo reasignables los que el origen todavía atiende y están en trabajo.
    still = _still_assigned(origin_id, ticket_ids)

    if not still:
        return back([f"Ninguno de esos tickets sigue asignado a {_name(origin)}."])

    if len(still) < len(set(ticket_ids)):
        flash(
            f"{len(set(ticket_ids)) - len(still)} de los tickets elegidos ya no estaban "
            "asignados a ese técnico o ya no están en trabajo: no se incluyen.",
            "warning",
        )

    destinations = [candidates[d] for d in dict.fromkeys(destination_ids)]
    plan = distribute(still, [user.id for user in destinations])
    by_ticket = {
        ticket.id: ticket
        for ticket in db.session.scalars(
            db.select(Ticket)
            .where(Ticket.id.in_(still))
            .options(db.joinedload(Ticket.estado), db.joinedload(Ticket.prioridad))
        )
    }
    received = {user.id: 0 for user in destinations}

    for _, destination_id in plan:
        received[destination_id] += 1

    return render_template(
        "reassignment/review.html",
        origin=origin,
        origin_active=loads[origin_id].active,
        reason=reason,
        rows=[(by_ticket[ticket_id], candidates[dest_id]) for ticket_id, dest_id in plan],
        summary=[
            (user, loads[user.id].active if user.id in loads else 0, received[user.id])
            for user in destinations
        ],
        moves=[f"{ticket_id}:{dest_id}" for ticket_id, dest_id in plan],
    )


# --- Paso 3: confirmar --------------------------------------------------------------


@bp.post("/confirm")
@area_only
def confirm():
    origin_id = request.form.get("origen", type=int)
    reason = request.form.get("motivo", "")
    moves = _moves()

    if origin_id is None or not moves:
        flash("La reasignación no es válida: vuelve a empezar.", "error")

        return redirect(url_for("reassignment.select_page"))

    try:
        result = reassign_tickets(
            current_actor(), source_id=origin_id, moves=moves, reason=reason
        )
    except PermissionError:
        abort(403)
    except TicketRuleError as error:
        db.session.rollback()
        flash(str(error), "error")

        return redirect(url_for("reassignment.select_page", origen=origin_id))

    db.session.commit()

    return render_template("reassignment/result.html", result=result, reason=reason)


def _problems(ticket_ids, destination_ids, candidates, reason) -> list[str]:
    """Lo que está mal en lo que se envió (todo a la vez, para corregirlo de una vez)."""
    problems = []

    if not ticket_ids:
        problems.append("Elige al menos un ticket para reasignar.")

    if not destination_ids:
        problems.append("Elige al menos un técnico de destino.")
    elif any(destination not in candidates for destination in destination_ids):
        problems.append("Elige técnicos de destino activos de la lista.")

    if not reason:
        problems.append("Indica el motivo de la reasignación (por ejemplo, vacaciones).")
    elif len(reason) > MAX_REASON_LENGTH:
        problems.append(f"El motivo no puede superar los {MAX_REASON_LENGTH} caracteres.")

    return problems


# --- Piezas ---------------------------------------------------------------------------


def _still_assigned(origin_id: int, ticket_ids) -> list[int]:
    """Los ids, entre `ticket_ids`, que `origin_id` atiende ahora y están en trabajo."""
    return sorted(
        db.session.scalars(
            db.select(Ticket.id)
            .join(TicketTechnician, TicketTechnician.ticket_id == Ticket.id)
            .join(Estado, Estado.id == Ticket.estado_id)
            .where(
                Ticket.id.in_(set(ticket_ids)),
                TicketTechnician.tecnico_id == origin_id,
                TicketTechnician.fecha_desasignacion.is_(None),
                active_state_condition(),
            )
        )
    )


def _ints(name: str) -> list[int]:
    """Los valores enteros de un campo repetido; lo que no es un entero se descarta."""
    values = []

    for raw in request.form.getlist(name):
        try:
            values.append(int(raw))
        except ValueError:
            continue

    return values


def _moves() -> list[tuple[int, int]]:
    """Los pares «ticket:destino» del resumen. Uno mal formado invalida todo el envío."""
    moves = []

    for raw in request.form.getlist("movimientos"):
        try:
            ticket_id, destination_id = (int(part) for part in raw.split(":"))
        except ValueError:
            return []

        moves.append((ticket_id, destination_id))

    return moves


def _choice(name: str, options) -> int | None:
    value = request.args.get(name, type=int)

    return value if value in {option.id for option in options} else None


def _name(user: User) -> str:
    return f"{user.nombre} {user.apellido}"
