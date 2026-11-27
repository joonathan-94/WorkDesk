"""Los reportes operativos (RF-098, UI-012; docs/12, fase 8).

Responden qué pasó en un período: cuántos tickets entraron y cuántos se resolvieron
(comparado con el período anterior de la misma duración), cuánto tardó la resolución,
cuántos incumplieron el SLA, cómo se reparten por estado, categoría y prioridad, cómo
evolucionó el tiempo de resolución semana a semana y qué cifras tiene cada técnico.

Definiciones (una sola vez, aquí):

- **Período:** días locales (`APP_TIMEZONE`), ambos incluidos. Por defecto, los últimos
  30 días hasta hoy; como mucho un año. El **período anterior** tiene la misma duración y
  termina el día antes de que empiece este.
- **Creados:** la fecha de creación cae en el período.
- **Resueltos:** la fecha de resolución **vigente** cae en el período. Un ticket rechazado
  o reabierto pierde su resolución y deja de contar hasta que se resuelva de nuevo; uno
  cerrado sin pasar por «Resuelto» (cierre directo, cancelación, duplicado) no es un
  resuelto.
- **Tiempo de resolución:** tiempo corrido desde la creación hasta esa resolución, de los
  resueltos del período. Media y mediana, calculadas en PostgreSQL. La mirada en tiempo
  laboral la da el SLA.
- **Fuera de SLA:** de los creados en el período, los que incumplieron su SLA (aunque
  después se haya bajado la prioridad: un incumplimiento no se borra). Con el SLA apagado
  esta cifra no existe.
- **Desgloses por estado, categoría y prioridad:** los creados en el período, según su
  estado, categoría y prioridad **actuales**. Cada desglose suma los creados.
- **Por técnico:** los tickets que tiene asignados **ahora** (como el listado y la carga
  de trabajo), así que un ticket con dos técnicos cuenta en cada uno. *Gestionados* son
  sus creados del período; *en trabajo*, los de esos que siguen sin resolver ni cerrar;
  *resueltos* y su tiempo, sus resueltos del período; *fuera de SLA*, sus creados que
  incumplieron. Los técnicos se listan por apellido: la pantalla no ordena ni califica a
  las personas (UI-012).

**Cada cifra es el total de su listado.** No se cuenta con condiciones propias: cada una se
cuenta con `listing_conditions`, las mismas condiciones del listado de tickets (en la
tabla por técnico, con sus mismas piezas: el técnico lo pone el `JOIN` de la asignación
vigente, que es lo que comprueba el filtro `tecnico`), y lleva los filtros
(`TicketFilters`) que la explican. `report_listing_params` los convierte en
la URL del listado con `listing_params`, el mismo código que usa el propio listado. Un
test comprueba los totales y que cada enlace, leído por la ruta del listado, reproduce
exactamente esos filtros.

Todo se calcula con un número fijo de consultas, sin una por técnico ni por semana.
"""

from dataclasses import dataclass, fields, replace
from datetime import date, datetime, timedelta

from sqlalchemy import Date, and_, cast, func, or_, select

from ..dashboard.requester import local_today
from ..extensions import db
from ..formatting import app_zone
from ..models import Categoria, Estado, Prioridad, Role, Ticket, TicketTechnician, User
from ..security import (
    RoleCode,
    can_view_every_technician_report,
    can_view_reports,
)
from ..sla import periods as sla_periods
from ..sla.queries import SlaFilter, sla_condition
from ..tickets.queries import (
    TAB_ALL,
    TicketFilters,
    active_state_condition,
    listing_conditions,
    listing_params,
    local_days_conditions,
)

DEFAULT_PERIOD_DAYS = 30
MAX_PERIOD_DAYS = 366
# Los períodos que ofrece la pantalla, en días hasta hoy.
PERIOD_PRESETS = (7, 30, 90, 365)


# --- Período y filtros ------------------------------------------------------------------


@dataclass(frozen=True)
class Period:
    """Días locales, ambos incluidos."""

    first: date
    last: date

    @property
    def days(self) -> int:
        return (self.last - self.first).days + 1

    def previous(self) -> "Period":
        """El período de la misma duración que termina el día antes de este."""
        return Period(self.first - timedelta(days=self.days), self.first - timedelta(days=1))


def preset_period(days: int, today: date) -> Period:
    """Los últimos `days` días, hoy incluido."""
    return Period(today - timedelta(days=days - 1), today)


def resolve_period(since: date | None, until: date | None, today: date) -> Period:
    """El período que piden `since` y `until` (cualquiera puede faltar), siempre válido:
    no termina después de hoy, no empieza después de terminar y no dura más de un año.
    Lo que no tiene sentido se corrige en lugar de dar un error, como en los filtros."""
    last = min(until or today, today)
    first = since if since is not None and since <= last else None

    if first is None:
        return preset_period(DEFAULT_PERIOD_DAYS, last)

    return Period(max(first, last - timedelta(days=MAX_PERIOD_DAYS - 1)), last)


@dataclass(frozen=True)
class ReportFilters:
    """El período y los filtros que restringen qué tickets se cuentan (combinables)."""

    period: Period
    group_id: int | None = None
    technician_id: int | None = None
    category_id: int | None = None
    priority_id: int | None = None

    def listing(self, **extra) -> TicketFilters:
        """Los filtros del listado con los de este reporte; `extra` añade otros o
        reemplaza alguno (el técnico de cada fila de la tabla por técnico)."""
        values = {
            "group_id": self.group_id,
            "technician_id": self.technician_id,
            "category_id": self.category_id,
            "priority_id": self.priority_id,
        }

        return TicketFilters(**(values | extra))

    def created(self, period: Period | None = None, **extra) -> TicketFilters:
        period = period or self.period
        return self.listing(created_from=period.first, created_to=period.last, **extra)

    def resolved(self, period: Period | None = None, **extra) -> TicketFilters:
        period = period or self.period
        return self.listing(resolved_from=period.first, resolved_to=period.last, **extra)


# --- Resultado --------------------------------------------------------------------------


def report_listing_params(listing: TicketFilters) -> dict:
    """La URL del listado que explica una cifra: todas las pestañas y sus filtros."""
    params = {key: value for key, value in listing_params(listing).items() if value is not None}

    return {"vista": TAB_ALL, **params}


@dataclass(frozen=True)
class Count:
    """Una cifra y el listado que la explica (su total es `value`)."""

    value: int
    listing: TicketFilters

    @property
    def params(self) -> dict:
        return report_listing_params(self.listing)


@dataclass(frozen=True)
class Duration:
    """El tiempo de resolución de unos resueltos, en segundos (None si no hay ninguno)."""

    resolved: Count
    mean_seconds: float | None
    median_seconds: float | None


@dataclass(frozen=True)
class Comparison:
    """Una cifra del período y la del período anterior."""

    current: Count
    previous: Count

    @property
    def change(self) -> int:
        return self.current.value - self.previous.value

    @property
    def change_percent(self) -> int | None:
        """La variación en porcentaje, redondeada; None si antes no había nada."""
        if self.previous.value == 0:
            return None

        return round(self.change * 100 / self.previous.value)


@dataclass(frozen=True)
class DurationComparison:
    current: Duration
    previous: Duration


@dataclass(frozen=True)
class BreakdownRow:
    """Una barra de un desglose: el estado, la categoría o la prioridad y su cifra."""

    item: Estado | Categoria | Prioridad
    label: str
    count: Count


@dataclass(frozen=True)
class WeekRow:
    """Una semana (de lunes a domingo, recortada al período) y su tiempo de resolución."""

    first: date
    last: date
    resolution: Duration


@dataclass(frozen=True)
class TechnicianRow:
    """Las cifras de un técnico; `user` es None en la fila «sin asignar»."""

    user: User | None
    handled: Count
    in_work: Count
    resolution: Duration
    # None con el SLA apagado.
    breached: Count | None


@dataclass(frozen=True)
class Report:
    filters: ReportFilters
    now: datetime
    sla_enabled: bool
    created: Comparison
    resolved: Comparison
    resolution: DurationComparison
    # None con el SLA apagado.
    breached: Comparison | None
    by_state: list[BreakdownRow]
    by_category: list[BreakdownRow]
    by_priority: list[BreakdownRow]
    weeks: list[WeekRow]
    technicians: list[TechnicianRow]
    # Los tickets sin técnico; None si se filtra por un técnico o quien consulta solo ve
    # sus propias cifras.
    unassigned: TechnicianRow | None
    # Si quien consulta ve a todos los técnicos o solo su propia fila.
    every_technician: bool


def default_filters(now: datetime | None = None) -> ReportFilters:
    """Los últimos 30 días, sin más filtros."""
    return ReportFilters(preset_period(DEFAULT_PERIOD_DAYS, local_today(now)))


def build_report(user, filters: ReportFilters, now: datetime | None = None) -> Report:
    """El reporte de `filters` para `user`. Solo el personal (`PermissionError` si no).

    Un Técnico ve las cifras de todo el equipo, pero en la tabla por técnico solo su
    propia fila, y no puede filtrar por otro técnico (el filtro se ignora)."""
    if not can_view_reports(user):
        raise PermissionError("Solo el personal puede ver los reportes.")

    every = can_view_every_technician_report(user)

    if not every and filters.technician_id not in (None, user.id):
        filters = replace(filters, technician_id=None)

    now = now or sla_periods.current_time()
    enabled = sla_periods.sla_enabled()
    # La fila «sin asignar» es del equipo: no con el filtro de técnico ni para un Técnico.
    unassigned = every and filters.technician_id is None
    totals = _totals(user, filters, now, enabled, include_unassigned=unassigned)

    return Report(
        filters=filters,
        now=now,
        sla_enabled=enabled,
        created=Comparison(totals["created"], totals["created_before"]),
        resolved=Comparison(
            totals["resolution"].resolved, totals["resolution_before"].resolved
        ),
        resolution=DurationComparison(totals["resolution"], totals["resolution_before"]),
        breached=(
            Comparison(totals["breached"], totals["breached_before"]) if enabled else None
        ),
        **_breakdowns(user, filters, now),
        weeks=_weeks(user, filters, now),
        technicians=_technicians(user, filters, now, enabled, every),
        unassigned=totals.get("unassigned"),
        every_technician=every,
    )


# --- Piezas -----------------------------------------------------------------------------


def _seconds():
    """El tiempo corrido de la creación a la resolución vigente, en segundos."""
    return func.extract("epoch", Ticket.fecha_resolucion - Ticket.fecha_creacion)


class _Columns:
    """Arma las columnas `COUNT ... FILTER` de una consulta y lee luego su fila.

    Cada cifra se cuenta con las condiciones del listado que la explica, así que no hay
    una segunda definición que pueda separarse de la del listado. Las condiciones que
    comparten todas las cifras (los filtros del reporte, `base`) van una sola vez en el
    `WHERE` (`where`) y cada `FILTER` lleva solo lo propio de su cifra: `A AND B` es lo
    mismo que `A` en el `WHERE` y `B` en el `FILTER`, pero `A` se evalúa una vez por fila
    y no una vez por cifra (con el filtro de técnico, una subconsulta por cifra)."""

    def __init__(self, user, now: datetime, base: TicketFilters):
        self.user = user
        self.now = now
        self.base = base
        self.columns = []
        self.listings: dict[str, TicketFilters] = {}

    def where(self) -> list:
        return listing_conditions(self.user, self.base, self.now)

    def _condition(self, listing: TicketFilters):
        """Lo que `listing` añade a `base`, como condición SQL."""
        default = TicketFilters()
        extra = {}

        for item in fields(TicketFilters):
            value = getattr(listing, item.name)

            if value != getattr(self.base, item.name):
                # Solo se puede añadir a lo que la base deja libre: reemplazar un filtro
                # del reporte haría que el `WHERE` y el listado dejaran de coincidir.
                if getattr(self.base, item.name) != getattr(default, item.name):
                    raise ValueError(f"La cifra reemplaza el filtro {item.name} del reporte.")

                extra[item.name] = value

        return and_(*listing_conditions(self.user, TicketFilters(**extra), self.now))

    def count(self, name: str, listing: TicketFilters) -> None:
        self.listings[name] = listing
        self.columns.append(func.count(Ticket.id).filter(self._condition(listing)).label(name))

    def duration(self, name: str, listing: TicketFilters) -> None:
        condition = self._condition(listing)
        self.count(name, listing)
        self.columns += [
            func.avg(_seconds()).filter(condition).label(f"{name}_mean"),
            func.percentile_cont(0.5)
            .within_group(_seconds())
            .filter(condition)
            .label(f"{name}_median"),
        ]

    def read_count(self, row, name: str) -> Count:
        return Count(getattr(row, name), self.listings[name])

    def read_duration(self, row, name: str) -> Duration:
        return Duration(
            self.read_count(row, name),
            _float(getattr(row, f"{name}_mean")),
            _float(getattr(row, f"{name}_median")),
        )


def _float(value) -> float | None:
    return None if value is None else float(value)


def _totals(user, filters: ReportFilters, now, enabled: bool, include_unassigned: bool) -> dict:
    """Las cifras principales del período y del anterior y la fila «sin asignar», en una
    sola consulta y un solo recorrido de los tickets de los dos períodos."""
    columns = _Columns(user, now, filters.listing())
    before = filters.period.previous()

    columns.count("created", filters.created())
    columns.count("created_before", filters.created(before))
    columns.duration("resolution", filters.resolved())
    columns.duration("resolution_before", filters.resolved(before))

    if enabled:
        columns.count("breached", filters.created(sla=SlaFilter.VENCIDO))
        columns.count("breached_before", filters.created(before, sla=SlaFilter.VENCIDO))

    if include_unassigned:
        _row_columns(columns, "unassigned", filters, enabled, unassigned=True)

    row = db.session.execute(
        select(*columns.columns)
        .select_from(Ticket)
        .join(Estado, Estado.id == Ticket.estado_id)
        .where(_touches(before.first, filters.period.last), *columns.where())
    ).one()

    totals = {
        "created": columns.read_count(row, "created"),
        "created_before": columns.read_count(row, "created_before"),
        "resolution": columns.read_duration(row, "resolution"),
        "resolution_before": columns.read_duration(row, "resolution_before"),
    }

    if enabled:
        totals["breached"] = columns.read_count(row, "breached")
        totals["breached_before"] = columns.read_count(row, "breached_before")

    if include_unassigned:
        totals["unassigned"] = _read_row(columns, row, "unassigned", None, enabled)

    return totals


def _touches(first: date, last: date):
    """Creado o resuelto entre esos días: los únicos tickets que puede contar el reporte.
    Es solo un filtro previo para no recorrer toda la tabla; cada cifra aplica después
    sus propias condiciones."""
    return or_(
        and_(*local_days_conditions(Ticket.fecha_creacion, first, last)),
        and_(*local_days_conditions(Ticket.fecha_resolucion, first, last)),
    )


def _row_columns(columns: _Columns, prefix: str, filters: ReportFilters, enabled, **who):
    """Las columnas de una fila de la tabla por técnico (`who` dice de quién)."""
    columns.count(f"{prefix}_handled", filters.created(**who))
    columns.count(f"{prefix}_in_work", filters.created(active_only=True, **who))
    columns.duration(f"{prefix}_resolution", filters.resolved(**who))

    if enabled:
        columns.count(f"{prefix}_breached", filters.created(sla=SlaFilter.VENCIDO, **who))


def _read_row(columns: _Columns, row, prefix: str, user, enabled) -> TechnicianRow:
    return TechnicianRow(
        user=user,
        handled=columns.read_count(row, f"{prefix}_handled"),
        in_work=columns.read_count(row, f"{prefix}_in_work"),
        resolution=columns.read_duration(row, f"{prefix}_resolution"),
        breached=columns.read_count(row, f"{prefix}_breached") if enabled else None,
    )


def _breakdowns(user, filters: ReportFilters, now) -> dict:
    """Los creados del período por estado, categoría y prioridad, en una sola consulta
    (`GROUPING SETS`: un recorrido y tres agrupaciones)."""
    created = filters.created()
    counts: dict[str, dict[int, int]] = {"estado": {}, "categoria": {}, "prioridad": {}}
    by_state = func.grouping(Ticket.estado_id) == 0
    by_category = func.grouping(Ticket.categoria_id) == 0

    for row in db.session.execute(
        select(
            Ticket.estado_id,
            Ticket.categoria_id,
            Ticket.prioridad_id,
            by_state.label("by_state"),
            by_category.label("by_category"),
            func.count(Ticket.id).label("total"),
        )
        .where(*listing_conditions(user, created, now))
        .group_by(
            func.grouping_sets(Ticket.estado_id, Ticket.categoria_id, Ticket.prioridad_id)
        )
    ):
        if row.by_state:
            counts["estado"][row.estado_id] = row.total
        elif row.by_category:
            counts["categoria"][row.categoria_id] = row.total
        else:
            counts["prioridad"][row.prioridad_id] = row.total

    def rows(items, key, field, label):
        return [
            BreakdownRow(
                item,
                label(item),
                Count(counts[key].get(item.id, 0), replace(created, **{field: item.id})),
            )
            for item in items
        ]

    states = db.session.scalars(select(Estado).order_by(Estado.orden, Estado.id))
    # Las prioridades activas aunque no tengan tickets; una desactivada, solo si tiene. Con
    # el filtro de prioridad, solo esa: las demás no tienen nada y su enlace llevaría a un
    # listado sin el filtro.
    priorities = [
        p
        for p in db.session.scalars(select(Prioridad).order_by(Prioridad.nivel, Prioridad.id))
        if (p.activo or p.id in counts["prioridad"])
        and filters.priority_id in (None, p.id)
    ]
    # Las categorías solo si tienen tickets, de la más frecuente a la menos.
    categories = sorted(
        db.session.scalars(select(Categoria).where(Categoria.id.in_(counts["categoria"]))),
        key=lambda c: (-counts["categoria"][c.id], c.nombre.lower(), c.id),
    )

    return {
        "by_state": rows(states, "estado", "state_id", lambda s: s.nombre_visible),
        "by_category": rows(categories, "categoria", "category_id", lambda c: c.nombre),
        "by_priority": rows(priorities, "prioridad", "priority_id", lambda p: p.nombre),
    }


def _weeks(user, filters: ReportFilters, now) -> list[WeekRow]:
    """El tiempo de resolución por semana (de lunes a domingo, en la zona de la
    aplicación), en una sola consulta. Las semanas sin resueltos también aparecen."""
    zone = getattr(app_zone(), "key", "UTC")
    monday = cast(
        func.date_trunc("week", func.timezone(zone, Ticket.fecha_resolucion)), Date
    ).label("monday")
    seconds = _seconds()

    found = {
        row.monday: row
        for row in db.session.execute(
            select(
                monday,
                func.count(Ticket.id).label("total"),
                func.avg(seconds).label("mean"),
                func.percentile_cont(0.5).within_group(seconds).label("median"),
            )
            .where(*listing_conditions(user, filters.resolved(), now))
            .group_by(monday)
        )
    }

    period = filters.period
    start = period.first - timedelta(days=period.first.weekday())
    weeks = []

    while start <= period.last:
        first = max(start, period.first)
        last = min(start + timedelta(days=6), period.last)
        row = found.get(start)
        weeks.append(
            WeekRow(
                first,
                last,
                Duration(
                    Count(row.total if row else 0, filters.resolved(Period(first, last))),
                    _float(row.mean) if row else None,
                    _float(row.median) if row else None,
                ),
            )
        )
        start += timedelta(days=7)

    return weeks


def _technicians(user, filters: ReportFilters, now, enabled: bool, every: bool):
    """Una fila por técnico, en una sola consulta, por apellido y nombre.

    Aparecen los técnicos activos (aunque no tengan nada) y cualquiera que tenga cifras
    (un técnico desactivado o que cambió de rol conserva sus tickets). Un Técnico ve solo
    la suya; con el filtro de técnico, solo la de ese técnico."""
    period = filters.period
    created = and_(*local_days_conditions(Ticket.fecha_creacion, period.first, period.last))
    resolved = and_(
        *local_days_conditions(Ticket.fecha_resolucion, period.first, period.last)
    )
    seconds = _seconds()

    columns = [
        func.count(Ticket.id).filter(created).label("handled"),
        func.count(Ticket.id).filter(created, active_state_condition()).label("in_work"),
        func.count(Ticket.id).filter(resolved).label("resolved"),
        func.avg(seconds).filter(resolved).label("mean"),
        func.percentile_cont(0.5).within_group(seconds).filter(resolved).label("median"),
    ]

    if enabled:
        breached = sla_condition(SlaFilter.VENCIDO, now)
        columns.append(func.count(Ticket.id).filter(created, breached).label("breached"))

    # Los tickets que el reporte puede contar, con los filtros del reporte salvo el de
    # técnico: ese lo pone la propia asignación (el `JOIN`), y elige la fila.
    base = filters.listing(technician_id=None)
    statement = (
        select(User, *columns)
        .select_from(User)
        .join(Role, Role.id == User.rol_id)
        .outerjoin(
            TicketTechnician,
            and_(
                TicketTechnician.tecnico_id == User.id,
                TicketTechnician.fecha_desasignacion.is_(None),
            ),
        )
        .outerjoin(
            Ticket,
            and_(
                Ticket.id == TicketTechnician.ticket_id,
                or_(created, resolved),
                *listing_conditions(user, base, now),
            ),
        )
        .outerjoin(Estado, Estado.id == Ticket.estado_id)
        .group_by(User.id, Role.id)
        .having(
            or_(
                and_(User.activo.is_(True), Role.codigo == RoleCode.TECNICO),
                func.count(Ticket.id) > 0,
            )
        )
        .order_by(func.lower(User.apellido), func.lower(User.nombre), User.id)
    )

    only = filters.technician_id if every else user.id

    if only is not None:
        statement = statement.where(User.id == only)

    return [
        TechnicianRow(
            user=row.User,
            handled=Count(row.handled, filters.created(technician_id=row.User.id)),
            in_work=Count(
                row.in_work, filters.created(technician_id=row.User.id, active_only=True)
            ),
            resolution=Duration(
                Count(row.resolved, filters.resolved(technician_id=row.User.id)),
                _float(row.mean),
                _float(row.median),
            ),
            breached=(
                Count(
                    row.breached,
                    filters.created(technician_id=row.User.id, sla=SlaFilter.VENCIDO),
                )
                if enabled
                else None
            ),
        )
        for row in db.session.execute(statement)
    ]
