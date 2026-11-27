"""Los reportes operativos (`reports/queries.py`, RF-098 y UI-012).

La regla central, como en los dashboards y la carga de trabajo: **cada cifra es el total del
listado que la explica**. Aquí se comprueba con los tickets de demostración para cada cifra
del reporte (los totales, el período anterior, los desgloses, las semanas y cada técnico),
con y sin filtros, y además que el enlace de cada una, leído por la propia ruta del listado,
reproduce exactamente los filtros con que se contó.

Lo demás: las definiciones (qué es un resuelto, la media y la mediana, las semanas de lunes
a domingo en la hora local), el período, quién ve qué, el SLA apagado y que el número de
consultas no crece con el equipo.
"""

import re
import statistics
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event

from src.workdesk import settings
from src.workdesk.catalogs.service import (
    list_categories,
    list_locations,
    list_priorities,
    list_states,
)
from src.workdesk.configuration import save_setting
from src.workdesk.extensions import db
from src.workdesk.models import Categoria, Grupo, Prioridad, StateAction, User
from src.workdesk.reports import (
    Period,
    ReportFilters,
    build_report,
    preset_period,
    resolve_period,
)
from src.workdesk.reports.queries import MAX_PERIOD_DAYS, Comparison, Count
from src.workdesk.tickets.assignment import assign_technician
from src.workdesk.tickets.lifecycle import change_state
from src.workdesk.tickets.queries import (
    TAB_ALL,
    TicketFilters,
    list_group_options,
    list_technician_options,
    list_tickets,
)
from src.workdesk.tickets.routes.listing import read_listing_filters
from tests.demo_data import DEMO_PASSWORD, NOW, SOLICITANTES
from tests.ticket_helpers import login, make_ticket, person, ticket_by_public_id

ZONE = ZoneInfo("America/Santiago")
TODAY = NOW.date()


def user(username):
    return db.session.scalar(db.select(User).where(User.username == username))


def last_days(days=30):
    return preset_period(days, TODAY)


def staff_report(username="camila.rojas", **filters):
    filters.setdefault("period", last_days())
    return build_report(user(username), ReportFilters(**filters), now=NOW)


def listing_total(listing: TicketFilters) -> int:
    """El total del listado (todas las pestañas) que ve el personal con esos filtros."""
    return list_tickets(user("camila.rojas"), listing, tab=TAB_ALL, now=NOW).total


def every_count(report) -> list[tuple[str, Count]]:
    """Cada cifra del reporte que enlaza con un listado, con un nombre para los mensajes."""
    counts = [
        ("creados", report.created.current),
        ("creados antes", report.created.previous),
        ("resueltos", report.resolved.current),
        ("resueltos antes", report.resolved.previous),
    ]

    if report.breached is not None:
        counts += [
            ("fuera de SLA", report.breached.current),
            ("fuera de SLA antes", report.breached.previous),
        ]

    for name, rows in (
        ("estado", report.by_state),
        ("categoría", report.by_category),
        ("prioridad", report.by_priority),
    ):
        counts += [(f"{name} {row.label}", row.count) for row in rows]

    counts += [(f"semana {week.first}", week.resolution.resolved) for week in report.weeks]

    rows = list(report.technicians)

    if report.unassigned is not None:
        rows.append(report.unassigned)

    for row in rows:
        who = row.user.username if row.user else "sin asignar"
        counts += [
            (f"{who} gestionados", row.handled),
            (f"{who} en trabajo", row.in_work),
            (f"{who} resueltos", row.resolution.resolved),
        ]

        if row.breached is not None:
            counts.append((f"{who} fuera de SLA", row.breached))

    return counts


def demo_filters():
    """Combinaciones de filtros con las que se recorre el reporte de demostración."""
    group = db.session.scalar(db.select(Grupo.id).where(Grupo.nombre == "Soporte Redes"))
    networks = db.session.scalar(db.select(Categoria.id).where(Categoria.nombre == "Redes"))
    high = db.session.scalar(db.select(Prioridad.id).where(Prioridad.codigo == "ALTA"))

    return [
        {},
        {"period": last_days(7)},
        {"period": last_days(90)},
        {"group_id": group},
        {"technician_id": user("diego.soto").id},
        {"category_id": networks},
        {"priority_id": high},
        {"group_id": group, "priority_id": high, "period": last_days(90)},
    ]


# --- Cada cifra es el total de su listado ------------------------------------------------


def test_every_figure_equals_the_list_it_links_to(seeded, app):
    with app.app_context():
        for filters in demo_filters():
            report = staff_report(**filters)
            counts = every_count(report)

            assert report.created.current.value > 0, filters

            for name, count in counts:
                assert count.value == listing_total(count.listing), (name, filters)


def test_every_link_reads_back_as_the_same_filters(seeded, app):
    """La URL de cada cifra, leída por la ruta del listado, da los mismos filtros: así el
    enlace de la pantalla lleva exactamente al listado que se contó."""
    with app.app_context():
        options = {
            "is_staff": True,
            "states": list_states(),
            "priorities": list_priorities(""),
            "categories": list_categories(""),
            "locations": list_locations(""),
            "technicians": list_technician_options(),
            "groups": list_group_options(),
        }
        reports = [staff_report(**filters) for filters in demo_filters()]

    for report in reports:
        for name, count in every_count(report):
            assert count.params["vista"] == TAB_ALL

            with app.test_request_context(f"/tickets?{urlencode(count.params)}"):
                assert read_listing_filters(**options) == count.listing, name


def test_the_breakdowns_add_up_to_the_created_and_the_weeks_to_the_resolved(seeded, app):
    with app.app_context():
        for filters in demo_filters():
            report = staff_report(**filters)
            created = report.created.current.value

            assert sum(row.count.value for row in report.by_state) == created
            assert sum(row.count.value for row in report.by_category) == created
            assert sum(row.count.value for row in report.by_priority) == created
            assert (
                sum(week.resolution.resolved.value for week in report.weeks)
                == report.resolved.current.value
            )


def test_the_demonstration_fills_every_part_of_the_report(seeded, app):
    """Los datos de demostración sirven para ver el reporte entero: hay creados,
    resueltos con su tiempo, incumplimientos, varias categorías y técnicos con cifras."""
    with app.app_context():
        report = staff_report(period=last_days(90))

    assert report.resolved.current.value > 0
    assert report.resolution.current.mean_seconds > 0
    assert report.breached.current.value > 0
    assert len(report.by_category) >= 3
    assert any(row.handled.value > 0 for row in report.technicians)
    assert report.unassigned.handled.value > 0


# --- Definiciones ------------------------------------------------------------------------


def test_the_resolution_time_is_the_mean_and_median_of_the_resolved(seeded, app):
    """Tiempo corrido desde la creación hasta la resolución vigente, calculado aquí en
    Python a partir de los propios tickets del listado."""
    with app.app_context():
        report = staff_report(period=last_days(90))
        tickets = list_tickets(
            user("camila.rojas"),
            report.resolved.current.listing,
            tab=TAB_ALL,
            now=NOW,
            per_page=500,
        ).items
        seconds = [
            (t.fecha_resolucion - t.fecha_creacion).total_seconds() for t in tickets
        ]

    resolution = report.resolution.current

    assert len(seconds) == resolution.resolved.value > 1
    assert resolution.mean_seconds == pytest.approx(statistics.mean(seconds))
    assert resolution.median_seconds == pytest.approx(statistics.median(seconds))


@pytest.fixture()
def desk(app, make_user, catalog):
    """Un equipo mínimo con la hora de Santiago."""
    app.config["APP_TIMEZONE"] = "America/Santiago"

    return {
        "boss": make_user("SUPERVISOR", username="jefa"),
        "tech": make_user("TECNICO", username="tecnico_uno", apellido="Uno"),
        "other": make_user("TECNICO", username="tecnico_dos", apellido="Dos"),
        "requester": make_user("SOLICITANTE", username="pide"),
        "catalog": catalog,
    }


def act(app, number, actor_id, action, **extra):
    with app.app_context():
        ticket = ticket_by_public_id(number)
        change_state(
            ticket,
            actor=person(actor_id),
            action=action,
            expected_version=ticket.version,
            **extra,
        )
        db.session.commit()


def report_today(app, username="jefa", **filters):
    with app.app_context():
        filters.setdefault("period", resolve_period(None, None, _local_today()))
        return build_report(user(username), ReportFilters(**filters))


def _local_today():
    return datetime.now(UTC).astimezone(ZONE).date()


def test_only_the_current_resolution_counts(app, desk):
    """Un ticket rechazado pierde su resolución; uno cerrado sin pasar por «Resuelto» no
    es un resuelto; uno resuelto dos veces cuenta una vez."""
    boss, requester, catalog = desk["boss"]["id"], desk["requester"]["id"], desk["catalog"]
    rejected = make_ticket(app, catalog, requester, requester_ids=[requester])
    closed = make_ticket(app, catalog, requester, requester_ids=[requester])
    twice = make_ticket(app, catalog, requester, requester_ids=[requester])

    act(app, rejected, boss, StateAction.RESOLVER, text="Listo")
    act(app, rejected, requester, StateAction.RECHAZAR, text="Sigue igual")
    act(app, closed, boss, StateAction.CIERRE_DIRECTO)
    act(app, twice, boss, StateAction.RESOLVER, text="Listo")
    act(app, twice, requester, StateAction.RECHAZAR, text="Sigue igual")
    act(app, twice, boss, StateAction.RESOLVER, text="Ahora sí")

    report = report_today(app)

    assert report.created.current.value == 3
    assert report.resolved.current.value == 1
    assert report.resolution.current.resolved.value == 1


def _resolve_at(app, number, actor_id, created, resolved):
    act(app, number, actor_id, StateAction.RESOLVER, text="Listo")

    with app.app_context():
        ticket = ticket_by_public_id(number)
        ticket.fecha_creacion = created
        ticket.fecha_resolucion = resolved
        db.session.commit()


def test_the_weeks_run_from_monday_to_sunday_in_local_time(app, desk):
    """Un ticket resuelto el domingo a las 23:30 de Santiago pertenece a esa semana, aunque
    en UTC ya sea lunes; uno resuelto el lunes a las 00:30, a la siguiente. Las semanas de
    los extremos se recortan al período."""
    boss, catalog = desk["boss"]["id"], desk["catalog"]
    sunday = datetime(2026, 11, 15, 23, 30, tzinfo=ZONE)
    monday = datetime(2026, 11, 16, 0, 30, tzinfo=ZONE)
    saturday = datetime(2026, 11, 14, 12, 0, tzinfo=ZONE)
    first = make_ticket(app, catalog, boss)
    second = make_ticket(app, catalog, boss)
    third = make_ticket(app, catalog, boss)
    _resolve_at(app, first, boss, sunday - timedelta(hours=2), sunday)
    _resolve_at(app, second, boss, monday - timedelta(hours=6), monday)
    _resolve_at(app, third, boss, saturday - timedelta(hours=5), saturday)

    report = report_today(app, period=Period(date(2026, 11, 12), date(2026, 11, 18)))
    weeks = [(w.first, w.last, w.resolution.resolved.value) for w in report.weeks]

    assert weeks == [
        (date(2026, 11, 12), date(2026, 11, 15), 2),
        (date(2026, 11, 16), date(2026, 11, 18), 1),
    ]
    # La primera semana tiene 2 h y 5 h: media y mediana de 3 h 30 min.
    assert report.weeks[0].resolution.mean_seconds == 3.5 * 3600
    assert report.weeks[0].resolution.median_seconds == 3.5 * 3600
    assert report.weeks[1].resolution.median_seconds == 6 * 3600


@pytest.mark.parametrize(
    ("hours", "mean", "median"),
    [
        # La mediana no se deja arrastrar por un caso largo; la media sí.
        ((1, 2, 3, 10, 50), 13.2, 3),
        # Con una cantidad par, la mediana es el punto medio de los dos centrales.
        ((1, 2, 3, 10), 4, 2.5),
    ],
)
def test_the_mean_and_the_median_of_known_times(app, desk, hours, mean, median):
    boss, catalog = desk["boss"]["id"], desk["catalog"]
    resolved = datetime.now(UTC) - timedelta(hours=1)

    for value in hours:
        number = make_ticket(app, catalog, boss)

        with app.app_context():
            assign_technician(
                ticket_by_public_id(number), desk["tech"]["id"], actor=person(boss)
            )
            db.session.commit()

        _resolve_at(app, number, boss, resolved - timedelta(hours=value), resolved)

    report = report_today(app)
    technician = {row.user.username: row for row in report.technicians}["tecnico_uno"]

    # El total y la fila del técnico (que se calcula en otra consulta) dan lo mismo.
    for resolution in (report.resolution.current, technician.resolution):
        assert resolution.resolved.value == len(hours)
        assert resolution.mean_seconds == pytest.approx(mean * 3600)
        assert resolution.median_seconds == pytest.approx(median * 3600)

    assert report.unassigned.resolution.resolved.value == 0


def test_a_week_without_resolutions_still_appears(app, desk):
    report = report_today(app, period=Period(date(2026, 11, 2), date(2026, 11, 15)))

    assert [(w.first, w.resolution.resolved.value) for w in report.weeks] == [
        (date(2026, 11, 2), 0),
        (date(2026, 11, 9), 0),
    ]
    assert report.weeks[0].resolution.mean_seconds is None


def test_the_previous_period_is_compared(app, desk):
    boss, catalog = desk["boss"]["id"], desk["catalog"]
    today = _local_today()
    period = Period(today - timedelta(days=6), today)

    for days_ago in (0, 1, 8, 9, 10, 20):
        number = make_ticket(app, catalog, boss)

        with app.app_context():
            ticket_by_public_id(number).fecha_creacion = datetime.now(UTC) - timedelta(
                days=days_ago
            )
            db.session.commit()

    created = report_today(app, period=period).created

    assert (created.current.value, created.previous.value) == (2, 3)
    assert created.change == -1
    assert created.change_percent == -33


def test_a_change_from_nothing_has_no_percentage():
    listing = TicketFilters()
    comparison = Comparison(Count(4, listing), Count(0, listing))

    assert comparison.change == 4
    assert comparison.change_percent is None


def test_a_figure_cannot_replace_a_filter_of_the_report(app):
    """Los filtros del reporte van una sola vez en el `WHERE`: una cifra que los
    reemplazara contaría otra cosa que su listado, así que se rechaza."""
    from flask_login import AnonymousUserMixin

    from src.workdesk.reports.queries import _Columns

    with app.app_context():
        columns = _Columns(AnonymousUserMixin(), NOW, TicketFilters(category_id=1))

        columns.count("bien", TicketFilters(category_id=1, priority_id=2))

        with pytest.raises(ValueError, match="category_id"):
            columns.count("mal", TicketFilters(category_id=2))


# --- Período -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("since", "until", "expected"),
    [
        (None, None, (date(2026, 10, 20), date(2026, 11, 18))),
        (date(2026, 11, 1), None, (date(2026, 11, 1), date(2026, 11, 18))),
        (date(2026, 11, 1), date(2026, 11, 10), (date(2026, 11, 1), date(2026, 11, 10))),
        # Un final en el futuro se recorta a hoy.
        (date(2026, 11, 1), date(2027, 1, 1), (date(2026, 11, 1), date(2026, 11, 18))),
        # Un comienzo posterior al final se ignora: los últimos 30 días hasta el final.
        (date(2026, 11, 12), date(2026, 11, 10), (date(2026, 10, 12), date(2026, 11, 10))),
        # Como mucho un año.
        (date(2020, 1, 1), None, (date(2025, 11, 18), date(2026, 11, 18))),
    ],
)
def test_the_period_is_always_valid(since, until, expected):
    period = resolve_period(since, until, TODAY)

    assert (period.first, period.last) == expected
    assert period.days <= MAX_PERIOD_DAYS


def test_the_previous_period_has_the_same_length_and_ends_the_day_before():
    period = Period(date(2026, 11, 1), date(2026, 11, 30))

    assert period.previous() == Period(date(2026, 10, 2), date(2026, 10, 31))
    assert period.previous().days == period.days == 30


# --- Quién ve qué ------------------------------------------------------------------------


@pytest.mark.parametrize("username", SOLICITANTES)
def test_a_requester_never_sees_the_reports(seeded, app, username):
    with app.app_context(), pytest.raises(PermissionError):
        staff_report(username)


def test_an_inactive_user_cannot_see_the_reports(seeded, app):
    with app.app_context():
        boss = user("camila.rojas")
        boss.activo = False
        db.session.commit()

        with pytest.raises(PermissionError):
            staff_report("camila.rojas")


@pytest.mark.parametrize("username", ["camila.rojas"])
def test_the_supervisor_sees_every_technician_and_the_unassigned(seeded, app, username):
    with app.app_context():
        report = staff_report(username)

    assert report.every_technician
    assert len(report.technicians) >= 4
    assert report.unassigned is not None


def test_a_technician_sees_the_team_figures_but_only_their_own_row(seeded, app):
    with app.app_context():
        own = staff_report("diego.soto")
        team = staff_report("camila.rojas")

    assert not own.every_technician
    assert [row.user.username for row in own.technicians] == ["diego.soto"]
    assert own.unassigned is None
    # Las cifras del equipo son las mismas que ve la Supervisora.
    assert own.created.current.value == team.created.current.value
    assert own.by_category == team.by_category


def test_a_technician_cannot_filter_by_someone_else(seeded, app):
    with app.app_context():
        other = user("valentina.pizarro").id
        report = staff_report("diego.soto", technician_id=other)
        team = staff_report("camila.rojas")

    assert report.filters.technician_id is None
    assert report.created.current.value == team.created.current.value
    assert [row.user.username for row in report.technicians] == ["diego.soto"]


def test_filtering_by_a_technician_leaves_only_their_row(seeded, app):
    with app.app_context():
        tech = user("diego.soto").id
        report = staff_report(technician_id=tech)

    assert [row.user.id for row in report.technicians] == [tech]
    assert report.unassigned is None
    assert report.technicians[0].handled.value == report.created.current.value


def test_the_technicians_are_listed_by_surname_not_by_their_figures(seeded, app):
    """Sin rankings (UI-012): el orden es alfabético, nunca por cifras."""
    with app.app_context():
        rows = staff_report(period=last_days(90)).technicians

    names = [(row.user.apellido.lower(), row.user.nombre.lower()) for row in rows]

    assert names == sorted(names)


def test_an_active_technician_without_tickets_appears_with_zeros(app, desk):
    report = report_today(app)
    rows = {row.user.username: row for row in report.technicians}

    assert set(rows) == {"tecnico_uno", "tecnico_dos"}
    assert rows["tecnico_dos"].handled.value == 0
    assert rows["tecnico_dos"].resolution.mean_seconds is None


# --- SLA apagado -------------------------------------------------------------------------


def test_with_the_sla_switched_off_there_are_no_sla_figures(seeded, app, make_user):
    admin = make_user("ADMINISTRADOR", username="admin_reportes")

    with app.app_context():
        save_setting(settings.SLA_ENABLED, False, actor=person(admin["id"]))
        db.session.commit()
        report = staff_report()

    assert not report.sla_enabled
    assert report.breached is None
    assert all(row.breached is None for row in report.technicians)
    assert report.unassigned.breached is None


# --- El listado filtra por fecha de resolución -------------------------------------------


def test_the_list_filters_by_resolution_date_and_shows_the_fields(seeded, app, client):
    login(client, {"username": "camila.rojas", "password": DEMO_PASSWORD})

    with app.app_context():
        report = staff_report(period=last_days(90))
        expected = report.resolved.current

    html = client.get("/tickets", query_string=expected.params).get_data(as_text=True)

    # La pestaña «Todos», la activa, cuenta lo mismo que el reporte.
    active_tab = re.search(r'aria-current="page"[^>]*>\s*Todos\s*<span[^>]*>\s*(\d+)', html)

    assert int(active_tab.group(1)) == expected.value > 0
    assert f'value="{expected.listing.resolved_from.isoformat()}"' in html
    assert f'value="{expected.listing.resolved_to.isoformat()}"' in html


# --- Coste -------------------------------------------------------------------------------


def count_queries(app, call):
    seen = []

    def count(*_args):
        seen.append(1)

    with app.app_context():
        event.listen(db.engine, "before_cursor_execute", count)

        try:
            call()
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

    return len(seen)


def test_the_number_of_queries_does_not_depend_on_the_size_of_the_team(
    seeded, app, make_user
):
    before = count_queries(app, lambda: staff_report(period=last_days(365)))

    for index in range(15):
        make_user("TECNICO", username=f"tecnico_extra_{index:02d}")

    after = count_queries(app, lambda: staff_report(period=last_days(365)))

    assert after == before
    assert before <= 10
