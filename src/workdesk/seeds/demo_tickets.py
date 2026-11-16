"""Carga de los tickets de demostración (comando `seed-demo-tickets`).

Los datos viven en `demo_tickets_data.py`; aquí está la lógica que los carga.

Cómo trabaja:

- Es opcional e independiente de `seed-demo`, pero necesita que ya estén
  cargados los usuarios demo (`seed-demo`) y los catálogos (`seed-catalogs`).
- No crea categorías ni ubicaciones: las busca por su nombre entre las que ya
  existen. Si falta alguna usa la categoría de respaldo o deja el ticket sin
  ubicación, y lo informa.
- Crea y ajusta los tickets con los servicios reales (`create_ticket`,
  `update_ticket`, `change_priority` y `change_state`), así que valida,
  versiona y deja el historial exactamente igual que la aplicación.
- Hace un único `commit` al final: o se carga todo o no se carga nada.

Identidad. Cada ticket de la lista tiene una `clave` estable. Al crearlo, los
eventos de su historial se marcan en `contexto` con esa clave y con el número
de paso (0 = creación, 1... = cada ajuste). Esa marca es la única huella que
deja el seed. Gracias a ella un ticket ya cargado se reconoce siempre, aunque
después se le cambie el título (en la lista o a mano), y se sabe qué eventos
son del seed y cuáles no.

Fechas. Los servicios sellan los eventos con la hora actual. Para dar
antigüedad, las fechas se escriben con un `UPDATE` directo, SOLO en las filas
que el propio seed creó (ticket, solicitantes e historial). Es el único lugar
del proyecto que lo hace: el ORM sigue rechazando cualquier modificación
normal del historial y no se añadió ningún parámetro de fecha a los
servicios.

Tiempo laboral. Todo el tiempo del seed corre según un calendario laboral
configurable (`WorkCalendar`, por defecto lunes a viernes de 09:00 a 18:00):
`hace_dias` cuenta días laborales, las horas de creación caen dentro de la
jornada y los ajustes avanzan en horas laborales, saltando noches, fines de
semana y feriados. Nada cae fuera del calendario ni en el futuro.

Volver a ejecutarlo. No duplica nada. Los tickets que ya existen no se
vuelven a crear: se *refrescan*, es decir, se reescriben sus fechas para que
queden relativas al día en que se ejecuta de nuevo (creación, historial,
solicitantes y fecha de modificación). El contenido (título, descripción,
categoría...) no se toca. Si el ticket recibió ediciones a mano después de
cargarse, esos eventos se desplazan junto con él para que el historial siga en
orden y nada quede en el futuro. Los tickets creados a mano, sin la marca, no
se tocan nunca.
"""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import update

from ..extensions import db
from ..formatting import app_zone
from ..models import (
    Categoria,
    Estado,
    MotivoEspera,
    Prioridad,
    StateAction,
    Ticket,
    TicketEvent,
    TicketHistory,
    TicketRequester,
    TransicionEstado,
    Ubicacion,
    User,
)
from ..models.categoria import FALLBACK_CATEGORY_CODE
from ..models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ..tickets.editing import MAX_REASON_LENGTH, change_priority, update_ticket
from ..tickets.lifecycle import MAX_WAIT_TEXT_LENGTH, STATE_ACTIONS, change_state
from ..tickets.service import INITIAL_STATE_CODE, TicketRuleError, create_ticket
from .catalogs import INITIAL_TRANSITIONS, INITIAL_WAIT_REASONS
from .demo import DEMO_USERS
from .demo_tickets_data import (
    DEMO_CALENDAR,
    DEMO_CATEGORIES,
    DEMO_LOCATIONS,
    DEMO_TICKETS,
    FALLBACK_CATEGORY,
    PRIORITY_CODES,
    DemoTicket,
    WorkCalendar,
)

STAFF_ROLES = ("TECNICO", "SUPERVISOR")
SOLICITANTE = "SOLICITANTE"

# Marca que el seed deja en `historial_ticket.contexto` de sus eventos.
MARKER_KEY = "demo_clave"
MARKER_STEP = "demo_paso"

MAX_KEY_LENGTH = 60
_KEY_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_TIME_PATTERN = re.compile(r"([01]\d|2[0-3]):[0-5]\d")

# Margen para que ningún evento quede en el futuro.
_LIMIT_MARGIN = timedelta(minutes=1)


class DemoTicketsError(Exception):
    """Los datos o el estado de la base impiden cargar los tickets demo.

    El mensaje está pensado para mostrarse en la terminal.
    """


@dataclass(frozen=True)
class DemoTicketsResult:
    created: int
    refreshed: int
    warnings: tuple[str, ...] = ()


# --- Validación de los datos ----------------------------------------------


def validate_demo_tickets(
    tickets: tuple[DemoTicket, ...] = DEMO_TICKETS,
    calendar: WorkCalendar = DEMO_CALENDAR,
) -> None:
    """Comprueba que los datos son coherentes antes de tocar la base.

    Así un error al editar la lista (un username mal escrito, una prioridad
    inexistente, una clave repetida) se descubre al instante y con un mensaje
    claro, no a mitad de la carga.
    """
    roles = {demo.username: demo.rol for demo in DEMO_USERS}
    problems: list[str] = _calendar_problems(calendar)
    calendar_ok = not problems
    keys: set[str] = set()
    titles: set[str] = set()

    for number, ticket in enumerate(tickets, start=1):
        label = f"Ticket {number} («{ticket.clave}»)"

        if not _KEY_PATTERN.fullmatch(ticket.clave) or len(ticket.clave) > MAX_KEY_LENGTH:
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

        if not _TIME_PATTERN.fullmatch(ticket.hora):
            problems.append(f"{label}: la hora «{ticket.hora}» no tiene formato HH:MM.")
        elif calendar_ok and not (
            _parse_time(calendar.inicio)
            <= _parse_time(ticket.hora)
            < _parse_time(calendar.fin)
        ):
            problems.append(
                f"{label}: la hora {ticket.hora} cae fuera de la jornada "
                f"({calendar.inicio}-{calendar.fin})."
            )

        _check_people(problems, label, ticket, roles)

        for step, adjustment in enumerate(ticket.ajustes, start=1):
            _check_adjustment(problems, f"{label}, ajuste {step}", adjustment, roles)

        _check_state_steps(problems, label, ticket)

    if problems:
        raise DemoTicketsError(
            "Los datos de demostración no son válidos:\n- " + "\n- ".join(problems)
        )


def _parse_time(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":"))

    return time(hour, minute)


def _calendar_problems(calendar: WorkCalendar) -> list[str]:
    problems: list[str] = []

    if not calendar.dias:
        problems.append("Calendario: debe haber al menos un día laboral.")

    if any(not isinstance(d, int) or not 0 <= d <= 6 for d in calendar.dias):
        problems.append("Calendario: los días van de 0 (lunes) a 6 (domingo).")

    if len(set(calendar.dias)) != len(calendar.dias):
        problems.append("Calendario: hay días repetidos.")

    for name, value in (("inicio", calendar.inicio), ("fin", calendar.fin)):
        if not _TIME_PATTERN.fullmatch(value):
            problems.append(f"Calendario: el {name} «{value}» no tiene formato HH:MM.")

    if not problems and _parse_time(calendar.inicio) >= _parse_time(calendar.fin):
        problems.append("Calendario: el inicio debe ser anterior al fin.")

    if any(not isinstance(holiday, date) for holiday in calendar.feriados):
        problems.append("Calendario: los feriados deben ser fechas.")

    return problems


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


def _check_adjustment(problems, label, adjustment, roles) -> None:
    if roles.get(adjustment.actor) not in STAFF_ROLES:
        problems.append(
            f"{label}: «{adjustment.actor}» no es personal (Técnico o Supervisor) demo."
        )

    if adjustment.despues_horas < 1:
        problems.append(f"{label}: despues_horas debe ser al menos 1.")

    changes = (
        adjustment.titulo,
        adjustment.descripcion,
        adjustment.categoria,
        adjustment.prioridad,
        adjustment.estado,
    )
    if all(change is None for change in changes):
        problems.append(f"{label}: no cambia nada.")

    if adjustment.titulo is not None:
        _check_text(problems, label, "título", adjustment.titulo, MAX_TITLE_LENGTH)

    if adjustment.descripcion is not None:
        _check_text(
            problems, label, "descripción", adjustment.descripcion, MAX_DESCRIPTION_LENGTH
        )

    if adjustment.categoria is not None and adjustment.categoria not in DEMO_CATEGORIES:
        problems.append(f"{label}: categoría desconocida «{adjustment.categoria}».")

    if adjustment.prioridad is not None:
        if adjustment.prioridad not in PRIORITY_CODES:
            problems.append(f"{label}: prioridad desconocida «{adjustment.prioridad}».")

        reason = adjustment.motivo or ""
        if not reason.strip():
            problems.append(f"{label}: cambiar la prioridad exige un motivo.")
        elif len(reason) > MAX_REASON_LENGTH:
            problems.append(f"{label}: el motivo supera los {MAX_REASON_LENGTH} caracteres.")


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
    en que va el ticket."""
    current = INITIAL_STATE_CODE
    implemented = {action.value for action in STATE_ACTIONS}

    for step, adjustment in enumerate(ticket.ajustes, start=1):
        where = f"{label}, ajuste {step}"
        action = adjustment.estado
        has_reason_data = (
            adjustment.motivo_espera is not None or adjustment.texto is not None
        )

        if action is None:
            if has_reason_data:
                problems.append(
                    f"{where}: motivo_espera y texto solo van con una acción de estado."
                )

            continue

        if action not in implemented:
            problems.append(
                f"{where}: la acción de estado «{action}» no existe o todavía no "
                f"está implementada (usa {', '.join(sorted(implemented))})."
            )

            continue

        destination = _TRANSITIONS.get((current, action))

        if destination is None:
            problems.append(
                f"{where}: «{action}» no es válida desde el estado {current}."
            )

            continue

        current = destination

        if action != StateAction.PONER_EN_ESPERA.value:
            if has_reason_data:
                problems.append(
                    f"{where}: solo PONER_EN_ESPERA admite motivo_espera y texto."
                )

            continue

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


# --- Carga ----------------------------------------------------------------


def seed_demo_tickets(
    now: datetime | None = None,
    tickets: tuple[DemoTicket, ...] | None = None,
    calendar: WorkCalendar | None = None,
) -> DemoTicketsResult:
    """Crea los tickets de demostración que faltan y refresca los que ya existen.

    `now` fija el instante de referencia (los tests lo usan para que las
    fechas sean deterministas), `tickets` permite cargar otra lista (por
    defecto, `DEMO_TICKETS`) y `calendar` otro calendario laboral (por
    defecto, `DEMO_CALENDAR`). Hace commit. Si algo falla, no queda nada a
    medias: se revierte todo y se lanza `DemoTicketsError`.
    """
    tickets = DEMO_TICKETS if tickets is None else tickets
    calendar = DEMO_CALENDAR if calendar is None else calendar
    validate_demo_tickets(tickets, calendar)

    zone = app_zone()
    now = (now or datetime.now(UTC)).astimezone(zone)
    limit = now - _LIMIT_MARGIN
    clock = _BusinessClock(calendar, zone)
    latest = clock.latest_before(limit)

    catalogs = _Catalogs.load(tickets)

    created = 0
    refreshed = 0

    try:
        for demo in tickets:
            times = _planned_times(demo, clock, now, latest)
            ticket = _find_ticket(demo.clave)

            if ticket is None:
                _create(demo, catalogs, times)
                created += 1
            else:
                _refresh(ticket, demo, times, limit)
                refreshed += 1

        db.session.commit()
    except TicketRuleError as error:
        db.session.rollback()
        raise DemoTicketsError(f"No se pudo cargar un ticket demo: {error}") from error
    except Exception:
        db.session.rollback()
        raise

    return DemoTicketsResult(
        created=created,
        refreshed=refreshed,
        warnings=tuple(catalogs.warnings),
    )


class _Catalogs:
    """Usuarios, prioridades, categorías y ubicaciones ya existentes."""

    def __init__(
        self, users, priorities, categories, fallback, locations, wait_reasons
    ):
        self.users: dict[str, User] = users
        self.wait_reasons: dict[str, MotivoEspera] = wait_reasons
        self.priorities: dict[str, Prioridad] = priorities
        self.categories: dict[str, Categoria] = categories
        self.fallback: Categoria = fallback
        self.locations: dict[str, Ubicacion] = locations
        self.warnings: list[str] = []

    @classmethod
    def load(cls, tickets) -> "_Catalogs":
        initial_state = db.session.scalar(
            db.select(Estado.id).where(Estado.codigo == INITIAL_STATE_CODE)
        )
        if initial_state is None:
            raise DemoTicketsError(
                "Faltan los catálogos iniciales. Ejecuta primero seed-catalogs."
            )

        needed = {demo_ticket.creado_por for demo_ticket in tickets}
        for demo_ticket in tickets:
            needed.update(demo_ticket.solicitantes)
            needed.update(step.actor for step in demo_ticket.ajustes)

        users = {
            user.username: user
            for user in db.session.scalars(
                db.select(User).where(User.username.in_(needed))
            )
        }
        missing = sorted(needed - set(users))
        if missing:
            raise DemoTicketsError(
                "Faltan usuarios de demostración "
                f"({', '.join(missing[:4])}{'...' if len(missing) > 4 else ''}). "
                "Ejecuta primero seed-demo."
            )

        priorities = {
            priority.codigo: priority
            for priority in db.session.scalars(
                db.select(Prioridad).where(Prioridad.activo.is_(True))
            )
        }
        missing_priorities = [code for code in PRIORITY_CODES if code not in priorities]
        if missing_priorities:
            raise DemoTicketsError(
                "Faltan prioridades activas "
                f"({', '.join(missing_priorities)}). Ejecuta primero seed-catalogs."
            )

        active_categories = list(
            db.session.scalars(db.select(Categoria).where(Categoria.activo.is_(True)))
        )
        fallback = next(
            (c for c in active_categories if c.codigo == FALLBACK_CATEGORY_CODE),
            None,
        )
        if fallback is None:
            raise DemoTicketsError(
                "Falta la categoría de respaldo. Ejecuta primero seed-catalogs."
            )

        categories = {c.nombre.casefold(): c for c in active_categories}
        locations = {
            location.nombre.casefold(): location
            for location in db.session.scalars(
                db.select(Ubicacion).where(Ubicacion.activo.is_(True))
            )
        }

        wait_reasons = {
            reason.codigo: reason
            for reason in db.session.scalars(
                db.select(MotivoEspera).where(
                    MotivoEspera.activo.is_(True),
                    MotivoEspera.codigo.is_not(None),
                )
            )
        }

        uses_states = any(step.estado for demo in tickets for step in demo.ajustes)
        has_transitions = (
            db.session.scalar(db.select(db.func.count(TransicionEstado.id))) > 0
        )

        if uses_states and not has_transitions:
            raise DemoTicketsError(
                "Faltan las transiciones de estado. Ejecuta primero seed-catalogs."
            )

        return cls(users, priorities, categories, fallback, locations, wait_reasons)

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def category(self, name: str, *, fallback_ok: bool) -> Categoria | None:
        """Categoría por nombre. Si falta: la de respaldo (al crear) o None."""
        if name == FALLBACK_CATEGORY:
            return self.fallback

        found = self.categories.get(name.casefold())
        if found is not None:
            return found

        if fallback_ok:
            self.warn(
                f"Categoría «{name}» no encontrada: los tickets que la usan "
                f"quedaron en «{self.fallback.nombre}»."
            )
            return self.fallback

        self.warn(
            f"Categoría «{name}» no encontrada: se omitió la reclasificación "
            "de algunos tickets."
        )
        return None

    def wait_reason(self, code: str | None) -> MotivoEspera | None:
        """Motivo de espera por código. Es opcional: si falta o está
        desactivado, la espera se registra sin motivo y se avisa."""
        if code is None:
            return None

        found = self.wait_reasons.get(code)
        if found is None:
            self.warn(
                f"Motivo de espera «{code}» no encontrado o desactivado: algunas "
                "esperas quedaron sin motivo."
            )
        return found

    def location(self, name: str | None) -> Ubicacion | None:
        if name is None:
            return None

        found = self.locations.get(name.casefold())
        if found is None:
            self.warn(
                f"Ubicación «{name}» no encontrada: los tickets que la usan "
                "quedaron sin ubicación."
            )
        return found


# --- Identidad ------------------------------------------------------------


def _find_ticket(key: str) -> Ticket | None:
    """El ticket que el seed cargó con esa clave, si existe.

    Se busca por la marca del evento de creación, que es inmutable: el ticket
    se reconoce aunque después cambie de título.
    """
    return db.session.scalar(
        db.select(Ticket)
        .join(TicketHistory, TicketHistory.ticket_id == Ticket.id)
        .where(
            TicketHistory.tipo_evento == TicketEvent.TICKET_CREADO.value,
            TicketHistory.contexto[MARKER_KEY].as_string() == key,
        )
        .limit(1)
    )


def _is_own(context: dict | None, key: str) -> bool:
    return bool(context) and context.get(MARKER_KEY) == key


# --- Fechas planificadas --------------------------------------------------


class _BusinessClock:
    """Calendario laboral: sabe qué días y horas cuentan y avanza en ellos.

    Todos los momentos son fechas con zona horaria (la de la aplicación). La
    jornada incluye el inicio y excluye el fin.
    """

    def __init__(self, calendar: WorkCalendar, zone) -> None:
        self.zone = zone
        self.days = set(calendar.dias)
        self.holidays = set(calendar.feriados)
        self.start = _parse_time(calendar.inicio)
        self.end = _parse_time(calendar.fin)

    def is_workday(self, day: date) -> bool:
        return day.weekday() in self.days and day not in self.holidays

    def previous_workday(self, day: date) -> date:
        """`day` si es laboral; si no, el día laboral anterior."""
        while not self.is_workday(day):
            day -= timedelta(days=1)

        return day

    def next_workday(self, day: date) -> date:
        """`day` si es laboral; si no, el día laboral siguiente."""
        while not self.is_workday(day):
            day += timedelta(days=1)

        return day

    def workdays_before(self, day: date, count: int) -> date:
        """El día laboral que está `count` días laborales antes de `day`."""
        day = self.previous_workday(day)

        for _ in range(count):
            day = self.previous_workday(day - timedelta(days=1))

        return day

    def at(self, day: date, moment: time) -> datetime:
        return datetime.combine(day, moment, tzinfo=self.zone)

    def into_business(self, moment: datetime) -> datetime:
        """El primer momento laboral que no es anterior a `moment`."""
        day = moment.date()

        if self.is_workday(day):
            if moment.time() < self.start:
                return self.at(day, self.start)

            if moment.time() < self.end:
                return moment

        return self.at(self.next_workday(day + timedelta(days=1)), self.start)

    def latest_before(self, limit: datetime) -> datetime:
        """El último momento laboral que no es posterior a `limit`."""
        day = limit.date()

        if self.is_workday(day):
            if self.start <= limit.time() < self.end:
                return limit

            if limit.time() >= self.end:
                return self.at(day, self.end) - _LIMIT_MARGIN

        day = self.previous_workday(day - timedelta(days=1))

        return self.at(day, self.end) - _LIMIT_MARGIN

    def add_hours(self, moment: datetime, hours: int) -> datetime:
        """Avanza `hours` horas LABORALES: salta noches, fines de semana y feriados."""
        moment = self.into_business(moment)
        remaining = timedelta(hours=hours)

        while True:
            available = self.at(moment.date(), self.end) - moment

            if remaining < available:
                return moment + remaining

            remaining -= available
            moment = self.at(
                self.next_workday(moment.date() + timedelta(days=1)), self.start
            )


def _planned_times(
    demo: DemoTicket, clock: _BusinessClock, now: datetime, latest: datetime
) -> list[datetime]:
    """Momentos de la historia: [creación, ajuste 1, ajuste 2, ...].

    Depende solo de los datos, del calendario y del día de la carga, así que
    dos ejecuciones el mismo día producen exactamente lo mismo. Todo cae en
    tiempo laboral y nunca después de `latest` (el último momento laboral que
    ya pasó).

    - Creación: `hace_dias` días laborales antes del día laboral de hoy (si hoy
      no es laboral, se cuenta desde el día laboral anterior), a la hora
      indicada.
    - Cada ajuste: `despues_horas` horas laborales después del paso anterior.
    """
    hour, minute = (int(part) for part in demo.hora.split(":"))
    day = clock.workdays_before(now.date(), demo.hace_dias)
    times = [min(clock.at(day, time(hour, minute)), latest)]

    for adjustment in demo.ajustes:
        moment = clock.add_hours(times[-1], adjustment.despues_horas)
        times.append(max(times[-1], min(moment, latest)))

    return times


# --- Crear ----------------------------------------------------------------


def _create(demo: DemoTicket, catalogs: _Catalogs, times: list[datetime]) -> None:
    creator = catalogs.users[demo.creado_por]

    if creator.rol.codigo == SOLICITANTE:
        requesters = [creator]
    else:
        requesters = [catalogs.users[username] for username in demo.solicitantes]

    location = catalogs.location(demo.ubicacion)

    ticket = create_ticket(
        actor=creator,
        title=demo.titulo,
        description=demo.descripcion,
        category_id=catalogs.category(demo.categoria, fallback_ok=True).id,
        priority_id=catalogs.priorities[demo.prioridad].id,
        location_id=None if location is None else location.id,
        requester_ids=[requester.id for requester in requesters],
    )

    steps: list[tuple[int, list[int]]] = []

    event_ids = _event_ids_after(ticket.id, 0)
    steps.append((0, event_ids))
    last_event_id = event_ids[-1]
    modified_at = None

    for step, adjustment in enumerate(demo.ajustes, start=1):
        _apply_adjustment(ticket, adjustment, catalogs)

        event_ids = _event_ids_after(ticket.id, last_event_id)
        if event_ids:
            steps.append((step, event_ids))
            last_event_id = event_ids[-1]
            modified_at = times[step]

    _write_new_dates(ticket, bool(requesters), demo.clave, steps, times, modified_at)


def _apply_adjustment(ticket: Ticket, adjustment, catalogs: _Catalogs) -> None:
    actor = catalogs.users[adjustment.actor]

    edits_data = any(
        value is not None
        for value in (adjustment.titulo, adjustment.descripcion, adjustment.categoria)
    )

    if edits_data:
        category_id = ticket.categoria_id

        if adjustment.categoria is not None:
            category = catalogs.category(adjustment.categoria, fallback_ok=False)
            if category is not None:
                category_id = category.id

        update_ticket(
            ticket,
            actor=actor,
            expected_version=ticket.version,
            title=adjustment.titulo or ticket.titulo,
            description=adjustment.descripcion or ticket.descripcion,
            category_id=category_id,
            location_id=ticket.ubicacion_id,
        )

    if adjustment.prioridad is not None:
        change_priority(
            ticket,
            actor=actor,
            expected_version=ticket.version,
            priority_id=catalogs.priorities[adjustment.prioridad].id,
            reason=adjustment.motivo,
        )

    if adjustment.estado is not None:
        reason = catalogs.wait_reason(adjustment.motivo_espera)

        change_state(
            ticket,
            actor=actor,
            action=StateAction(adjustment.estado),
            expected_version=ticket.version,
            wait_reason_id=None if reason is None else reason.id,
            # El texto libre exige un motivo que lo admita: sin motivo
            # (porque faltaba en el catálogo) no se guarda.
            text=None if reason is None else adjustment.texto,
        )


def _event_ids_after(ticket_id: int, after_id: int) -> list[int]:
    return list(
        db.session.scalars(
            db.select(TicketHistory.id)
            .where(TicketHistory.ticket_id == ticket_id, TicketHistory.id > after_id)
            .order_by(TicketHistory.id)
        )
    )


def _write_new_dates(
    ticket: Ticket,
    has_requesters: bool,
    key: str,
    steps: list[tuple[int, list[int]]],
    times: list[datetime],
    modified_at: datetime | None,
) -> None:
    """Fecha y marca de las filas que este proceso acaba de crear."""
    tickets = Ticket.__table__
    requesters = TicketRequester.__table__
    history = TicketHistory.__table__

    db.session.execute(
        update(tickets)
        .where(tickets.c.id == ticket.id)
        .values(fecha_creacion=times[0], fecha_modificacion=modified_at)
    )

    if has_requesters:
        db.session.execute(
            update(requesters)
            .where(requesters.c.ticket_id == ticket.id)
            .values(fecha_asociacion=times[0])
        )

    for step, event_ids in steps:
        contexts = dict(
            db.session.execute(
                db.select(history.c.id, history.c.contexto).where(
                    history.c.id.in_(event_ids)
                )
            ).all()
        )

        for event_id in event_ids:
            marker = {MARKER_KEY: key, MARKER_STEP: step}

            db.session.execute(
                update(history)
                .where(history.c.id == event_id)
                .values(
                    fecha_hora=times[step],
                    contexto={**(contexts[event_id] or {}), **marker},
                )
            )


# --- Refrescar ------------------------------------------------------------


def _refresh(
    ticket: Ticket, demo: DemoTicket, times: list[datetime], limit: datetime
) -> None:
    """Reescribe las fechas de un ticket ya cargado, relativas al día de hoy.

    - Los eventos del seed (con su marca) vuelven a su momento planificado.
    - Los eventos que no son del seed (ediciones hechas a mano después) se
      desplazan lo mismo que el último evento del seed, para que sigan después
      de él y nunca queden en el futuro.
    - La fecha de modificación acompaña al evento que la originó, y los
      solicitantes se asocian en la nueva fecha de creación.

    No toca el contenido del ticket ni crea ningún evento.
    """
    db.session.refresh(ticket)

    history = TicketHistory.__table__
    tickets = Ticket.__table__
    requesters = TicketRequester.__table__

    events = db.session.execute(
        db.select(history.c.id, history.c.fecha_hora, history.c.contexto)
        .where(history.c.ticket_id == ticket.id)
        .order_by(history.c.id)
    ).all()

    last_step = len(demo.ajustes)
    new_time: dict[int, datetime] = {}

    for event in events:
        if _is_own(event.contexto, demo.clave):
            step = min(int(event.contexto.get(MARKER_STEP, 0)), last_step)
            new_time[event.id] = times[step]

    old_last_own = max(e.fecha_hora for e in events if e.id in new_time)
    new_last_own = max(new_time.values())
    shift = new_last_own - old_last_own

    running = new_last_own
    for event in events:
        if event.id not in new_time:
            running = min(max(event.fecha_hora + shift, running), limit)
            new_time[event.id] = running

    # La fecha de modificación acompaña al evento que la originó.
    by_old_time = {event.fecha_hora: new_time[event.id] for event in events}
    old_modified = ticket.fecha_modificacion
    if old_modified is None:
        new_modified = None
    else:
        new_modified = by_old_time.get(old_modified) or min(
            max(old_modified + shift, new_last_own), limit
        )

    old_created = ticket.fecha_creacion
    new_created = times[0]
    delta = new_created - old_created

    def clamp(moment: datetime) -> datetime:
        return min(max(moment, new_created), limit)

    db.session.execute(
        update(tickets)
        .where(tickets.c.id == ticket.id)
        .values(fecha_creacion=new_created, fecha_modificacion=new_modified)
    )

    for event in events:
        db.session.execute(
            update(history)
            .where(history.c.id == event.id)
            .values(fecha_hora=new_time[event.id])
        )

    links = db.session.execute(
        db.select(
            requesters.c.id, requesters.c.fecha_asociacion, requesters.c.fecha_retiro
        ).where(requesters.c.ticket_id == ticket.id)
    ).all()

    for link in links:
        associated = (
            new_created
            if link.fecha_asociacion == old_created
            else clamp(link.fecha_asociacion + delta)
        )
        retired = (
            None
            if link.fecha_retiro is None
            else max(associated, clamp(link.fecha_retiro + delta))
        )

        db.session.execute(
            update(requesters)
            .where(requesters.c.id == link.id)
            .values(fecha_asociacion=associated, fecha_retiro=retired)
        )
