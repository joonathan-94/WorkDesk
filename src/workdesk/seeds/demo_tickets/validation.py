"""Validación de los datos de demostración antes de tocar la base."""


from ...cleaning import MAX_REASON_LENGTH
from ...models import (
    StateAction,
)
from ...models.comment import MAX_COMMENT_LENGTH
from ...models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ...tickets.service import (
    CLOSED_STATE_CODE,
    INITIAL_STATE_CODE,
)
from ...tickets.state_actions import MAX_WAIT_TEXT_LENGTH, STATE_ACTIONS
from ...tickets.storage import ALLOWED_TYPES
from ...worktime import (
    DEMO_CALENDAR,
    TIME_PATTERN,
    WorkCalendar,
    calendar_problems,
    parse_time,
)
from ..catalogs import INITIAL_TRANSITIONS, INITIAL_WAIT_REASONS
from ..demo import DEMO_GROUPS, DEMO_USERS
from ..demo_tickets_data import (
    DEMO_CATEGORIES,
    DEMO_LOCATIONS,
    DEMO_TICKETS,
    PRIORITY_CODES,
    DemoTicket,
)
from .common import (
    KEY_PATTERN,
    MAX_KEY_LENGTH,
    SOLICITANTE,
    STAFF_ROLES,
    SUPERVISOR,
    TECNICO,
    DemoTicketsError,
)

# --- Validación de los datos ----------------------------------------------


def validate_demo_tickets(
    tickets: tuple[DemoTicket, ...] = DEMO_TICKETS,
    calendar: WorkCalendar | None = DEMO_CALENDAR,
) -> None:
    """Comprueba que los datos son coherentes antes de tocar la base.

    Así un error al editar la lista (un username mal escrito, una prioridad
    inexistente, una clave repetida) se descubre al instante y con un mensaje
    claro, no a mitad de la carga. Con `calendar=None` (un calendario de
    franjas guardado por el Administrador) no se comprueba que cada hora caiga
    en la jornada: no hay una jornada única con la que compararla.
    """
    roles = {demo.username: demo.rol for demo in DEMO_USERS}
    problems: list[str] = [] if calendar is None else calendar_problems(calendar)
    workday = calendar if calendar is not None and not problems else None
    keys: set[str] = set()
    duplicates: dict[str, str] = {}
    titles: set[str] = set()

    for number, ticket in enumerate(tickets, start=1):
        label = f"Ticket {number} («{ticket.clave}»)"

        _check_identity(problems, label, ticket, keys, titles)
        _check_fields(problems, label, ticket, workday)
        _check_people(problems, label, ticket, roles)

        for step, adjustment in enumerate(ticket.ajustes, start=1):
            _check_adjustment(problems, f"{label}, ajuste {step}", adjustment, roles)

        _check_state_steps(problems, label, ticket)
        _check_requester_steps(problems, label, ticket, roles)
        _check_relation_steps(problems, label, ticket, tickets[: number - 1], duplicates)

    if problems:
        raise DemoTicketsError(
            "Los datos de demostración no son válidos:\n- " + "\n- ".join(problems)
        )


def _check_identity(problems, label, ticket, keys, titles) -> None:
    """La clave (bien formada y única) y el título (único)."""
    if not KEY_PATTERN.fullmatch(ticket.clave) or len(ticket.clave) > MAX_KEY_LENGTH:
        problems.append(
            f"{label}: la clave debe ser un nombre corto en minúsculas, números y "
            f"guiones (máximo {MAX_KEY_LENGTH} caracteres)."
        )

    if ticket.clave in keys:
        problems.append(f"{label}: la clave está repetida.")
    keys.add(ticket.clave)

    title_key = ticket.titulo.casefold()
    if title_key in titles:
        problems.append(f"{label}: el título está repetido.")
    titles.add(title_key)


def _check_fields(problems, label, ticket, workday) -> None:
    """Textos, catálogos y hora de creación. `workday` es el calendario de jornada
    única contra el que comparar la hora, o None si no se compara."""
    _check_text(problems, label, "título", ticket.titulo, MAX_TITLE_LENGTH)
    _check_text(
        problems, label, "descripción", ticket.descripcion, MAX_DESCRIPTION_LENGTH
    )

    if ticket.categoria not in DEMO_CATEGORIES:
        problems.append(f"{label}: categoría desconocida «{ticket.categoria}».")

    if ticket.prioridad not in PRIORITY_CODES:
        problems.append(f"{label}: prioridad desconocida «{ticket.prioridad}».")

    if ticket.ubicacion is not None and ticket.ubicacion not in DEMO_LOCATIONS:
        problems.append(f"{label}: ubicación desconocida «{ticket.ubicacion}».")

    if ticket.hace_dias < 0:
        problems.append(f"{label}: hace_dias no puede ser negativo.")

    if not TIME_PATTERN.fullmatch(ticket.hora):
        problems.append(f"{label}: la hora «{ticket.hora}» no tiene formato HH:MM.")
    elif workday is not None and not (
        parse_time(workday.inicio) <= parse_time(ticket.hora) < parse_time(workday.fin)
    ):
        problems.append(
            f"{label}: la hora {ticket.hora} cae fuera de la jornada "
            f"({workday.inicio}-{workday.fin})."
        )


def _check_text(problems, label, name, value, limit) -> None:
    if not value or value != value.strip():
        problems.append(f"{label}: el {name} está vacío o tiene espacios en los bordes.")
    elif len(value) > limit:
        problems.append(f"{label}: el {name} supera los {limit} caracteres.")


def _check_people(problems, label, ticket, roles) -> None:
    creator_role = roles.get(ticket.creado_por)

    if creator_role is None:
        problems.append(f"{label}: el creador «{ticket.creado_por}» no es un usuario demo.")
        return

    if creator_role == SOLICITANTE and ticket.solicitantes:
        # Quien crea siendo Solicitante es siempre su propio solicitante.
        problems.append(
            f"{label}: lo crea un Solicitante, así que no lleva `solicitantes`."
        )

    if len(set(ticket.solicitantes)) != len(ticket.solicitantes):
        problems.append(f"{label}: hay solicitantes repetidos.")

    for username in ticket.solicitantes:
        if roles.get(username) != SOLICITANTE:
            problems.append(f"{label}: «{username}» no es un Solicitante demo.")


# Campos que solo cambia el personal. Un paso con alguno de ellos no puede
# tener a un Solicitante como actor.
_STAFF_ONLY_FIELDS = (
    "titulo",
    "descripcion",
    "categoria",
    "prioridad",
    "estado",
    "grupo",
    "asignar",
    "agregar_solicitante",
    "retirar_solicitante",
    "nota_interna",
    "relacionar",
    "duplicado_de",
)


# Acciones de estado que ejecuta un Solicitante: responder a la resolución.
_REQUESTER_ACTIONS = (StateAction.CONFIRMAR.value, StateAction.RECHAZAR.value)


def _is_requester_step(adjustment, roles) -> bool:
    """Un paso de un Solicitante: su comentario público y/o su respuesta a la
    resolución (confirmar o rechazar). No puede cambiar nada más."""
    if roles.get(adjustment.actor) != SOLICITANTE:
        return False

    others_empty = all(
        getattr(adjustment, name) is None
        for name in _STAFF_ONLY_FIELDS
        if name != "estado"
    )
    answers = adjustment.estado in _REQUESTER_ACTIONS

    return (
        others_empty
        and (adjustment.estado is None or answers)
        and (adjustment.comentario is not None or answers)
    )


def _check_adjustment(problems, label, adjustment, roles) -> None:
    _check_actor(problems, label, adjustment, roles)

    if adjustment.despues_horas < 1:
        problems.append(f"{label}: despues_horas debe ser al menos 1.")

    _check_changes_something(problems, label, adjustment)
    _check_attachment(problems, label, adjustment)
    _check_texts(problems, label, adjustment)
    _check_group_and_assignment(problems, label, adjustment, roles)
    _check_requester_fields(problems, label, adjustment, roles)
    _check_priority_change(problems, label, adjustment)


def _check_actor(problems, label, adjustment, roles) -> None:
    actor_role = roles.get(adjustment.actor)

    # Un Solicitante solo aparece comentando en su ticket (que sea el creador o
    # un solicitante lo comprueba `_check_requester_steps`); todo lo demás lo
    # hace el personal.
    if actor_role not in STAFF_ROLES and not _is_requester_step(adjustment, roles):
        problems.append(
            f"{label}: «{adjustment.actor}» no es personal (Técnico o Supervisor) demo."
        )

    # Confirmar o rechazar la solución es del solicitante; el personal no
    # responde por él.
    if adjustment.estado in _REQUESTER_ACTIONS and actor_role != SOLICITANTE:
        problems.append(
            f"{label}: «{adjustment.estado}» la ejecuta un Solicitante demo, no "
            "el personal."
        )

    # Solo un Supervisor cierra de forma excepcional.
    if (
        adjustment.estado == StateAction.CIERRE_EXCEPCIONAL.value
        and actor_role != SUPERVISOR
    ):
        problems.append(
            f"{label}: el cierre excepcional lo ejecuta un Supervisor demo."
        )


def _check_changes_something(problems, label, adjustment) -> None:
    changes = (
        adjustment.titulo,
        adjustment.descripcion,
        adjustment.categoria,
        adjustment.prioridad,
        adjustment.estado,
        adjustment.grupo,
        adjustment.asignar,
        adjustment.agregar_solicitante,
        adjustment.retirar_solicitante,
        adjustment.comentario,
        adjustment.nota_interna,
        adjustment.adjunto,
        adjustment.relacionar,
        adjustment.duplicado_de,
    )

    if all(change is None for change in changes):
        problems.append(f"{label}: no cambia nada.")


def _check_attachment(problems, label, adjustment) -> None:
    if adjustment.adjunto is None:
        return

    file_name, file_text = adjustment.adjunto
    kind = ALLOWED_TYPES.get(file_name.rpartition(".")[2].lower(), (None, None))[1]

    if kind != "text":
        problems.append(
            f"{label}: el adjunto «{file_name}» debe terminar en .txt, .log o .csv."
        )

    if not file_text.strip():
        problems.append(f"{label}: el adjunto «{file_name}» está vacío.")


def _check_texts(problems, label, adjustment) -> None:
    """Los textos que el paso escribe y la categoría a la que reclasifica."""
    for name, text_label, limit in (
        ("comentario", "comentario", MAX_COMMENT_LENGTH),
        ("nota_interna", "nota interna", MAX_COMMENT_LENGTH),
        ("titulo", "título", MAX_TITLE_LENGTH),
        ("descripcion", "descripción", MAX_DESCRIPTION_LENGTH),
    ):
        value = getattr(adjustment, name)

        if value is not None:
            _check_text(problems, label, text_label, value, limit)

    if adjustment.categoria is not None and adjustment.categoria not in DEMO_CATEGORIES:
        problems.append(f"{label}: categoría desconocida «{adjustment.categoria}».")


def _check_group_and_assignment(problems, label, adjustment, roles) -> None:
    if adjustment.grupo is not None:
        if adjustment.grupo not in {group.nombre for group in DEMO_GROUPS}:
            problems.append(f"{label}: grupo desconocido «{adjustment.grupo}».")

        if roles.get(adjustment.actor) != SUPERVISOR:
            problems.append(f"{label}: el grupo lo fija un Supervisor demo.")

    if adjustment.asignar is None:
        return

    if roles.get(adjustment.asignar) != TECNICO:
        problems.append(f"{label}: «{adjustment.asignar}» no es un Técnico demo.")

    # Un Técnico solo se asigna a sí mismo; a otra persona la asigna un Supervisor.
    if roles.get(adjustment.actor) != SUPERVISOR and (
        adjustment.actor != adjustment.asignar
    ):
        problems.append(
            f"{label}: solo un Supervisor asigna a otra persona; un Técnico "
            "se asigna a sí mismo."
        )


def _check_requester_fields(problems, label, adjustment, roles) -> None:
    for field_name in ("agregar_solicitante", "retirar_solicitante"):
        username = getattr(adjustment, field_name)

        if username is not None and roles.get(username) != SOLICITANTE:
            problems.append(f"{label}: «{username}» no es un Solicitante demo.")

    if (
        adjustment.agregar_solicitante is not None
        and adjustment.agregar_solicitante == adjustment.retirar_solicitante
    ):
        problems.append(
            f"{label}: no tiene sentido retirar y agregar a la misma persona."
        )

    if adjustment.motivo_retiro is not None:
        if adjustment.retirar_solicitante is None:
            problems.append(f"{label}: motivo_retiro solo va con retirar_solicitante.")

        _check_text(
            problems, label, "motivo de retiro", adjustment.motivo_retiro, MAX_REASON_LENGTH
        )


def _check_priority_change(problems, label, adjustment) -> None:
    if adjustment.prioridad is None:
        return

    if adjustment.prioridad not in PRIORITY_CODES:
        problems.append(f"{label}: prioridad desconocida «{adjustment.prioridad}».")

    reason = adjustment.motivo or ""

    if not reason.strip():
        problems.append(f"{label}: cambiar la prioridad exige un motivo.")
    elif len(reason) > MAX_REASON_LENGTH:
        problems.append(f"{label}: el motivo supera los {MAX_REASON_LENGTH} caracteres.")


def _check_requester_steps(problems, label, ticket, roles) -> None:
    """Comprueba que quien se retira es solicitante en ese momento y quien se
    agrega no lo es todavía, siguiendo los pasos del ticket en orden.

    Empieza con los solicitantes de la creación: quien crea siendo Solicitante
    es su propio solicitante; el personal indica `solicitantes`. En un mismo
    paso primero se retira y después se agrega.
    """
    if roles.get(ticket.creado_por) == SOLICITANTE:
        current = {ticket.creado_por}
    else:
        current = set(ticket.solicitantes)

    for step, adjustment in enumerate(ticket.ajustes, start=1):
        where = f"{label}, ajuste {step}"

        _check_requester_changes(problems, where, adjustment, current)

        if _is_requester_step(adjustment, roles):
            _check_requester_answer(problems, where, adjustment, current, ticket)


def _check_requester_changes(problems, where, adjustment, current: set) -> None:
    """Aplica a `current` (los solicitantes de ese momento) lo que retira y agrega
    el paso, y señala lo que no se puede."""
    removed = adjustment.retirar_solicitante
    added = adjustment.agregar_solicitante

    if removed is not None:
        if removed in current:
            current.discard(removed)
        else:
            problems.append(f"{where}: «{removed}» no es solicitante en ese momento.")

    if added is not None:
        if added in current:
            problems.append(f"{where}: «{added}» ya es solicitante en ese momento.")
        else:
            current.add(added)


def _check_requester_answer(problems, where, adjustment, current, ticket) -> None:
    """Un Solicitante solo comenta en un ticket suyo (el creador también, aunque se
    le retire como solicitante) y solo un solicitante vigente responde a la
    resolución."""
    if adjustment.estado in _REQUESTER_ACTIONS:
        if adjustment.actor not in current:
            problems.append(
                f"{where}: «{adjustment.actor}» no es solicitante en ese "
                "momento, así que no puede responder a la resolución."
            )
    elif adjustment.actor not in current and adjustment.actor != ticket.creado_por:
        problems.append(
            f"{where}: «{adjustment.actor}» no es solicitante ni creó el "
            "ticket, así que no puede comentarlo."
        )


def _check_relation_steps(problems, label, ticket, earlier, duplicates) -> None:
    """Comprueba las relaciones y los duplicados de un ticket: apuntan a un ticket
    anterior de la lista y más antiguo (para que la relación no preceda a su
    creación), no se repiten, un duplicado va solo (sin `estado`) y su principal
    no es a su vez un duplicado."""
    known = {other.clave: other for other in earlier}
    linked: set[str] = set()

    for step, adjustment in enumerate(ticket.ajustes, start=1):
        where = f"{label}, ajuste {step}"

        if adjustment.duplicado_de is not None and adjustment.estado is not None:
            problems.append(
                f"{where}: duplicado_de cierra el ticket; no puede ir con `estado`."
            )

        for field_name in ("relacionar", "duplicado_de"):
            key = getattr(adjustment, field_name)

            if key is None:
                continue

            other = known.get(key)

            if other is None:
                problems.append(
                    f"{where}: «{key}» debe ser la clave de un ticket que aparezca "
                    "antes en la lista."
                )

                continue

            if other.hace_dias < ticket.hace_dias or (
                other.hace_dias == ticket.hace_dias and other.hora > ticket.hora
            ):
                problems.append(
                    f"{where}: «{key}» es más reciente que este ticket: la relación "
                    "no puede ser anterior a su creación."
                )

            if field_name == "relacionar":
                if key in linked:
                    problems.append(f"{where}: ya se relacionó con «{key}».")

                linked.add(key)
            else:
                if key in duplicates:
                    problems.append(
                        f"{where}: «{key}» ya es un duplicado de otro: elige el "
                        "ticket principal."
                    )

                if ticket.clave in duplicates:
                    problems.append(f"{where}: el ticket ya es un duplicado.")

                duplicates[ticket.clave] = key


# Transiciones tal como las carga `seed-catalogs`:
# (estado de origen, acción) -> estado de destino.
_TRANSITIONS = {
    (origin, action.value): destination
    for origin, destination, action, _ in INITIAL_TRANSITIONS
}
_WAIT_REASON_CODES = {row["codigo"]: row for row in INITIAL_WAIT_REASONS}


def _check_state_steps(problems, label, ticket) -> None:
    """Comprueba que los cambios de estado de un ticket se pueden ejecutar en
    ese orden, empezando en Nuevo: cada acción debe ser válida desde el estado
    en que va el ticket, y un ticket cerrado solo admite reabrirlo."""
    current = INITIAL_STATE_CODE
    implemented = {action.value for action in STATE_ACTIONS}

    for step, adjustment in enumerate(ticket.ajustes, start=1):
        current = _check_state_step(
            problems, f"{label}, ajuste {step}", adjustment, current, implemented
        )


def _check_state_step(problems, where, adjustment, current, implemented) -> str:
    """Comprueba un paso y devuelve el estado en que queda el ticket."""
    # Asignar un técnico a un ticket Nuevo lo pasa a Asignado.
    if adjustment.asignar is not None and current == INITIAL_STATE_CODE:
        current = "ASIGNADO"

    action = adjustment.estado

    # Un ticket cerrado no se modifica: el único paso posible es reabrirlo, y va
    # solo (el cambio de estado se ejecuta al final del paso).
    if current == CLOSED_STATE_CODE and not _only_reopens(adjustment):
        problems.append(
            f"{where}: el ticket está cerrado; el único paso posible es REABRIR, solo."
        )

        return current

    if action is None:
        return _check_step_without_action(problems, where, adjustment, current)

    if action not in implemented:
        problems.append(
            f"{where}: la acción de estado «{action}» no existe o todavía no "
            f"está implementada (usa {', '.join(sorted(implemented))})."
        )

        return current

    destination = _TRANSITIONS.get((current, action))

    if destination is None:
        problems.append(f"{where}: «{action}» no es válida desde el estado {current}.")

        return current

    rule = STATE_ACTIONS[StateAction(action)]

    if action == StateAction.PONER_EN_ESPERA.value:
        _check_wait_data(problems, where, adjustment)
    else:
        if adjustment.motivo_espera is not None:
            problems.append(f"{where}: solo PONER_EN_ESPERA admite motivo_espera.")

        _check_close_data(problems, where, adjustment, rule)

    return destination


def _only_reopens(adjustment) -> bool:
    """El único paso que admite un ticket cerrado: reabrirlo, solo."""
    return (
        adjustment.estado == StateAction.REABRIR.value
        and adjustment.comentario is None
        and all(
            getattr(adjustment, name) is None
            for name in _STAFF_ONLY_FIELDS
            if name != "estado"
        )
    )


def _check_step_without_action(problems, where, adjustment, current) -> str:
    """Un paso sin acción de estado: o marca un duplicado (que cierra el ticket por
    el cierre directo) o no toca el estado."""
    if adjustment.duplicado_de is not None:
        closed_to = _TRANSITIONS.get((current, StateAction.CIERRE_DIRECTO.value))

        if closed_to is None:
            problems.append(
                f"{where}: no se puede marcar como duplicado desde el estado {current}."
            )

            return current

        return closed_to

    if (
        adjustment.motivo_espera is not None
        or adjustment.motivo_cierre is not None
        or adjustment.texto is not None
    ):
        problems.append(
            f"{where}: motivo_espera, motivo_cierre y texto solo van con una "
            "acción de estado."
        )

    return current


def _check_wait_data(problems, where, adjustment) -> None:
    """`motivo_espera` y `texto` de poner un ticket en espera."""
    if adjustment.motivo_cierre is not None:
        problems.append(f"{where}: solo CIERRE_DIRECTO admite motivo_cierre.")

    reason = _WAIT_REASON_CODES.get(adjustment.motivo_espera)

    if adjustment.motivo_espera is not None and reason is None:
        problems.append(
            f"{where}: motivo de espera desconocido «{adjustment.motivo_espera}»."
        )

    if adjustment.texto is not None:
        _check_text(problems, where, "texto", adjustment.texto, MAX_WAIT_TEXT_LENGTH)

        if reason is None or not reason.get("permite_texto_otro"):
            problems.append(
                f"{where}: el texto exige un motivo que admita texto libre (OTRO)."
            )


def _check_close_data(problems, where, adjustment, rule) -> None:
    """`motivo_cierre` y `texto` de las acciones que no son la espera: el
    motivo de cierre solo lo elige el cierre directo y el texto depende de la
    acción (la solución, el motivo de un rechazo o de un cierre...)."""
    if adjustment.motivo_cierre is not None:
        if not rule.close_reasons:
            problems.append(f"{where}: solo CIERRE_DIRECTO admite motivo_cierre.")
        elif adjustment.motivo_cierre not in rule.close_reasons:
            problems.append(
                f"{where}: motivo de cierre «{adjustment.motivo_cierre}» no elegible "
                f"(usa {', '.join(rule.close_reasons)})."
            )

    text = adjustment.texto

    if rule.text_label is None:
        if text is not None:
            problems.append(f"{where}: «{rule.action.value}» no admite texto.")

        return

    if rule.text_required and not (text or "").strip():
        problems.append(f"{where}: «{rule.action.value}» exige un texto.")

    if text is not None:
        _check_text(problems, where, "texto", text, rule.text_max)
