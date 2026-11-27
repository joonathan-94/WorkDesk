"""La pantalla de reportes (`/reports`, UI-012, RF-098 y RN-179).

Lo importante:
- Solo la ve el personal: el Solicitante recibe 403 desde el backend.
- **Cada cifra de la página lleva a un listado cuyo total es esa cifra.** Los enlaces se
  leen de la propia página y se abren de verdad; se compara con lo que el listado muestra en
  la pestaña «Todos».
- Un Técnico ve su fila y nada más en la tabla por técnico.

También: el período elegido, los filtros inválidos, el SLA apagado, lo escrito por otras
personas se escapa y la tabla equivalente del gráfico semanal.
"""

import html as htmllib
import re
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.workdesk import settings
from src.workdesk.configuration import save_setting
from src.workdesk.extensions import db
from src.workdesk.models import Categoria, Grupo, Prioridad, User
from src.workdesk.reports.charts import (
    bars,
    count_change,
    resolution_line,
    time_change,
)
from src.workdesk.reports.queries import (
    BreakdownRow,
    Comparison,
    Count,
    Duration,
    WeekRow,
)
from src.workdesk.tickets.queries import TicketFilters
from tests.demo_data import DEMO_PASSWORD, SOLICITANTES
from tests.ticket_helpers import login, make_ticket, person, text

ZONE = ZoneInfo("America/Santiago")

# Una cifra con enlace: las tarjetas (`kpi-card`) y los números de las barras y las tablas.
KPI = re.compile(
    r'<a\s+class="kpi-card[^"]*"\s+href="([^"]+)"\s*>.*?kpi-label">([^<]+)<.*?kpi-value">([^<]+)<',
    re.DOTALL,
)
COUNT = re.compile(r'<a\s+href="(/tickets\?[^"]+)"\s+aria-label="(\d+) tickets: ([^"]+)"')
ALL_TAB = re.compile(r'aria-current="page"[^>]*>\s*Todos\s*<span[^>]*>\s*(\d+)')


def sign_in(client, username):
    login(client, {"username": username, "password": DEMO_PASSWORD})


def figures(page_html: str) -> list[tuple[str, str, int]]:
    """Cada cifra de la página con enlace: (qué es, URL, número)."""
    found = [
        (label.strip(), href, int(value))
        for href, label, value in KPI.findall(page_html)
        if value.strip().isdigit()
    ]
    found += [(what, href, int(value)) for href, value, what in COUNT.findall(page_html)]

    return found


def listing_total(client, href: str) -> int:
    page = client.get(htmllib.unescape(href)).get_data(as_text=True)

    return int(ALL_TAB.search(page).group(1))


def ids(model, **criteria):
    return db.session.scalar(db.select(model.id).filter_by(**criteria))


# --- Quién entra -------------------------------------------------------------------------


@pytest.mark.parametrize("username", ["diego.soto", "camila.rojas"])
def test_the_staff_sees_the_reports(seeded, client, username):
    sign_in(client, username)
    page = client.get("/reports")

    assert page.status_code == 200
    assert "Tickets por estado" in text(page)
    assert "no-store" in page.headers["Cache-Control"]


def test_the_administrator_sees_the_reports(seeded, client, make_user):
    login(client, make_user("ADMINISTRADOR", username="jefa"))

    assert client.get("/reports").status_code == 200


@pytest.mark.parametrize("username", SOLICITANTES)
def test_a_requester_gets_403_and_no_data(seeded, client, username):
    sign_in(client, username)
    page = client.get("/reports?periodo=365")

    assert page.status_code == 403
    assert "Tickets por estado" not in text(page)


def test_without_a_session_it_asks_to_log_in(client):
    response = client.get("/reports")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_the_screen_only_reads(seeded, client):
    sign_in(client, "camila.rojas")

    assert client.post("/reports").status_code in (400, 405)


# --- Cada cifra es el total de su listado ------------------------------------------------


def _check_every_figure(client, url):
    page = client.get(url).get_data(as_text=True)
    found = figures(page)

    assert len(found) > 10, url

    for what, href, value in found:
        assert listing_total(client, href) == value, (url, what, href)


@pytest.mark.parametrize(
    "query",
    ["", "periodo=90", "periodo=personalizado&desde=2026-10-01&hasta=2026-11-18"],
)
def test_every_figure_leads_to_a_list_with_that_total(seeded, client, query):
    sign_in(client, "camila.rojas")

    _check_every_figure(client, f"/reports?{query}")


def test_every_figure_also_matches_with_filters(seeded, app, client):
    with app.app_context():
        group = ids(Grupo, nombre="Soporte Redes")
        high = ids(Prioridad, codigo="ALTA")
        networks = ids(Categoria, nombre="Redes")

    sign_in(client, "camila.rojas")

    _check_every_figure(client, f"/reports?periodo=90&grupo={group}&prioridad={high}")
    _check_every_figure(client, f"/reports?periodo=365&categoria={networks}")


def test_every_figure_matches_for_a_technician(seeded, client):
    sign_in(client, "diego.soto")

    _check_every_figure(client, "/reports?periodo=90")


# --- Período y filtros -------------------------------------------------------------------


def _today():
    return datetime.now(UTC).astimezone(ZONE).date()


def _period_text(client, query):
    page = text(client.get(f"/reports?{query}"))

    return re.search(r"Del (\S+) al (\S+) \((\d+) días?\)", page).groups()


@pytest.mark.parametrize(
    ("query", "days"),
    [
        ("", 30),
        ("periodo=7", 7),
        ("periodo=90", 90),
        ("periodo=365", 365),
        ("periodo=12", 30),
        ("periodo=%C2%B2", 30),
        # Las fechas solo cuentan con «Personalizado».
        ("desde=2026-01-01&hasta=2026-01-05", 30),
    ],
)
def test_the_period_comes_from_the_presets(seeded, client, query, days):
    sign_in(client, "camila.rojas")

    _first, last, length = _period_text(client, query)

    assert int(length) == days
    assert last == _today().strftime("%d-%m-%Y")


def test_a_custom_period_uses_the_dates(seeded, client):
    sign_in(client, "camila.rojas")

    assert _period_text(
        client, "periodo=personalizado&desde=2026-10-01&hasta=2026-10-07"
    ) == ("01-10-2026", "07-10-2026", "7")


def test_a_custom_period_without_valid_dates_falls_back(seeded, client):
    sign_in(client, "camila.rojas")

    _first, last, length = _period_text(client, "periodo=personalizado&desde=no&hasta=2099-01-01")

    assert (last, length) == (_today().strftime("%d-%m-%Y"), "30")


@pytest.mark.parametrize(
    "query", ["grupo=abc", "tecnico=99999", "categoria=-1", "prioridad=1.5"]
)
def test_an_invalid_filter_is_ignored(seeded, client, query):
    sign_in(client, "camila.rojas")
    plain = figures(client.get("/reports").get_data(as_text=True))
    filtered = client.get(f"/reports?{query}")

    assert filtered.status_code == 200
    assert figures(filtered.get_data(as_text=True))[0] == plain[0]


# --- Lo que ve un Técnico ----------------------------------------------------------------


def test_a_technician_sees_only_their_own_row_and_can_only_pick_themselves(seeded, app, client):
    with app.app_context():
        other = ids(User, username="valentina.pizarro")

    sign_in(client, "diego.soto")
    page = client.get(f"/reports?periodo=90&tecnico={other}").get_data(as_text=True)
    table = page.split('id="por-tecnico"', 1)[1]
    options = page.split('id="tecnico"', 1)[1].split("</select>", 1)[0]

    assert "Diego Soto" in table
    assert "Valentina Pizarro" not in table
    assert "Sin asignar" not in table
    assert "Ves solo tu propia fila" in table
    assert "Soto, Diego" in options and "Pizarro" not in options


def test_the_supervisor_sees_every_technician_and_the_unassigned(seeded, client):
    sign_in(client, "camila.rojas")
    table = client.get("/reports?periodo=90").get_data(as_text=True).split('id="por-tecnico"', 1)[1]

    for name in ("Felipe Araya", "Francisca Muñoz", "Valentina Pizarro", "Diego Soto", "Sin asignar"):
        assert name in table
    assert "Ves solo tu propia fila" not in table


# --- SLA apagado, escape y gráfico -------------------------------------------------------


def test_with_the_sla_switched_off_nothing_about_it_is_shown(seeded, app, client, make_user):
    admin = make_user("ADMINISTRADOR", username="admin_reportes")

    with app.app_context():
        save_setting(settings.SLA_ENABLED, False, actor=person(admin["id"]))
        db.session.commit()

    sign_in(client, "camila.rojas")
    page = text(client.get("/reports?periodo=90"))

    assert "Fuera de SLA" not in page


def test_what_others_wrote_is_escaped(app, client, make_user, catalog):
    boss = make_user("SUPERVISOR", username="jefa")

    with app.app_context():
        category = Categoria(nombre="<script>alert(1)</script>", orden=9)
        db.session.add(category)
        db.session.commit()
        category_id = category.id

    make_ticket(app, catalog, boss["id"], category_id=category_id)
    login(client, boss)
    page = client.get("/reports").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_without_resolved_tickets_the_chart_says_so_and_keeps_its_table(app, client, make_user, catalog):
    boss = make_user("SUPERVISOR", username="jefa")
    make_ticket(app, catalog, boss["id"])
    login(client, boss)
    page = client.get("/reports?periodo=7").get_data(as_text=True)

    assert "No se resolvió ningún ticket en el período." in page
    assert "<svg" not in page.split('id="por-semana"', 1)[1].split("</section>", 1)[0]
    assert 'id="por-semana-tabla"' in page


def test_the_weekly_chart_has_an_equivalent_table(seeded, client):
    sign_in(client, "camila.rojas")
    page = client.get("/reports?periodo=90").get_data(as_text=True)
    chart = page.split('id="por-semana"', 1)[1].split("</section>", 1)[0]

    assert 'role="img"' in chart
    assert 'aria-describedby="por-semana-tabla"' in chart
    # Una fila por semana del período (90 días tocan 14 semanas, de lunes a domingo).
    assert chart.count('<th scope="row"') >= 13


# --- Los gráficos (sin base de datos) ----------------------------------------------------


class _Item:
    def __init__(self, code):
        self.codigo = code


def _row(label, value, code=None):
    return BreakdownRow(_Item(code), label, Count(value, TicketFilters()))


def test_the_longest_bar_fills_the_track_and_a_small_one_stays_visible():
    result = bars([_row("A", 200), _row("B", 1), _row("C", 0), _row("D", 100)])

    assert [bar.percent for bar in result] == [100, 2, 0, 50]


def test_bars_take_the_colour_of_their_state_or_priority():
    result = bars([_row("Crítica", 3, "CRITICA"), _row("Otra", 1, "INVENTADA")], {"CRITICA": "danger"})

    assert [bar.tone for bar in result] == ["danger", "primary"]


def test_bars_of_nothing_are_empty():
    assert bars([]) == []
    assert [bar.percent for bar in bars([_row("A", 0)])] == [0]


def _comparison(current, previous):
    return Comparison(Count(current, TicketFilters()), Count(previous, TicketFilters()))


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [
        (109, 100, "+9 (+9 %) respecto del período anterior"),
        (90, 100, "-10 (-10 %) respecto del período anterior"),
        (5, 5, "Igual que el período anterior"),
        (4, 0, "Antes: 0"),
    ],
)
def test_the_change_in_a_count(current, previous, expected):
    assert count_change(_comparison(current, previous)) == expected


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [
        (3 * 3600, 2 * 3600, "+1 h respecto del período anterior"),
        (3600, 3600 + 18 * 60, "−18 min respecto del período anterior"),
        (3600, 3630, "Igual que el período anterior"),
        (3600, None, "Sin datos del período anterior"),
        (None, None, ""),
    ],
)
def test_the_change_in_a_time(current, previous, expected):
    assert time_change(current, previous) == expected


def _week(day, mean, median=None):
    first = date(2026, 11, day)

    return WeekRow(
        first,
        first + timedelta(days=6),
        Duration(Count(0 if mean is None else 1, TicketFilters()), mean, median if median is not None else mean),
    )


def test_a_week_without_resolutions_leaves_a_gap_in_the_line():
    chart = resolution_line([_week(2, 3600), _week(9, 7200), _week(16, None), _week(23, 1800)])
    mean = chart.series[0]

    # Un tramo de dos puntos y un punto suelto, que no se une con nada.
    assert len(mean.paths) == 1
    assert len(mean.points) == 3
    assert not chart.empty


def test_the_axis_reaches_the_highest_value_in_a_few_round_steps():
    chart = resolution_line([_week(2, 5 * 3600), _week(9, 7 * 3600)])

    assert [tick.label for tick in chart.y_ticks] == ["0", "2 h", "4 h", "6 h", "8 h"]
    assert chart.y_ticks[-1].position <= min(p.y for p in chart.series[0].points)


def test_a_chart_without_values_is_empty():
    chart = resolution_line([_week(2, None), _week(9, None)])

    assert chart.empty
    assert [tick.label for tick in chart.x_ticks] == ["02-11", "09-11"]


def test_many_weeks_get_only_a_few_date_labels():
    weeks = [_week(1, 3600)] * 53

    assert len(resolution_line(weeks).x_ticks) <= 8
