"""Pantallas del calendario laboral (docs/11, UI-022): el resumen en «SLA» y el
formulario «Configurar calendario». Son exclusivas del Administrador."""

import re
from datetime import date

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, CalendarioLaboral
from src.workdesk.sla.work_calendar import Holiday, save_work_calendar
from src.workdesk.worktime import Franja, parse_time
from tests.ticket_helpers import login, person, plain_text

SLA_URL = "/admin/sla"
CALENDAR_URL = "/admin/sla/calendar"


# --- Auxiliares -------------------------------------------------------------


@pytest.fixture()
def admin(app, make_user):
    app.config["APP_TIMEZONE"] = "America/Santiago"

    return make_user("ADMINISTRADOR", username="admin")


def form_data(**changes):
    """Lo que enviaría el formulario con el calendario por defecto, más los cambios."""
    data = {
        "zona_horaria": "America/Santiago",
        **{f"dia_{number}": "09:00-18:00" for number in range(5)},
        "dia_5": "",
        "dia_6": "",
        "feriados": "",
        "motivo": "",
        "version_base": "0",
    }
    data.update(changes)

    return data


def saved_calendar(app, admin_id, *, base_version=0, **changes):
    """Guarda una versión con el servicio (como lo haría la pantalla)."""
    values = {
        "zone_name": "America/Santiago",
        "franjas": [
            Franja(day, parse_time("09:00"), parse_time("18:00")) for day in range(5)
        ],
        "holidays": [],
    }
    values.update(changes)

    with app.app_context():
        saved = save_work_calendar(
            actor=person(admin_id), base_version=base_version, **values
        )
        db.session.commit()

        return saved.version


def versions(app) -> list[tuple[int, bool]]:
    with app.app_context():
        return [
            (row.version, row.activo)
            for row in db.session.scalars(
                db.select(CalendarioLaboral).order_by(CalendarioLaboral.version)
            )
        ]


def field_values(html: str) -> dict[str, str]:
    """Los valores de los campos de texto y ocultos del formulario, por nombre."""
    values = dict(re.findall(r'name="(dia_\d|zona_horaria|motivo)"[^>]*?value="([^"]*)"', html))
    version = re.search(r'name="version_base"\s+value="([^"]*)"', html)
    holidays = re.search(
        r'<textarea[^>]*name="feriados"[^>]*>(.*?)</textarea>', html, re.DOTALL
    )

    values["version_base"] = version.group(1) if version else None
    values["feriados"] = holidays.group(1) if holidays else None

    return values


# --- Acceso -------------------------------------------------------------------


def test_an_anonymous_user_is_sent_to_the_login(client):
    for url in (SLA_URL, CALENDAR_URL):
        response = client.get(url)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_only_the_administrator_can_use_the_screens(client, app, make_user, role):
    person_data = make_user(role, username="persona")
    login(client, person_data)

    assert client.get(SLA_URL).status_code == 403
    assert client.get(CALENDAR_URL).status_code == 403
    # La pantalla del formulario también acepta POST: el rol se comprueba antes.
    assert client.post(CALENDAR_URL, data=form_data()).status_code == 403
    assert versions(app) == []


def test_the_hub_links_the_screen(client, admin):
    login(client, admin)
    html = client.get("/admin").get_data(as_text=True)

    assert f'href="{SLA_URL}"' in html


def test_the_sidebar_keeps_administration_active_on_these_screens(client, admin):
    login(client, admin)

    for url in (SLA_URL, CALENDAR_URL):
        html = client.get(url).get_data(as_text=True)

        assert re.search(r'data-label="Administración"\s*aria-current="page"', html)


# --- El resumen en «SLA» -----------------------------------------------------------


def test_the_sla_page_shows_the_default_calendar(client, admin):
    login(client, admin)
    response = client.get(SLA_URL)
    page = plain_text(response)

    assert response.status_code == 200
    assert "Calendario laboral" in page
    assert "Por defecto (sin configurar)" in page
    assert "Lunes a viernes · 09:00–18:00" in page
    assert "America/Santiago" in page
    assert "Sin feriados" in page
    assert "Todavía no hay versiones guardadas" in page
    assert "Configurar calendario" in page
    assert f'href="{CALENDAR_URL}"' in response.get_data(as_text=True)


def test_the_sla_page_shows_a_saved_calendar(client, app, admin):
    saved_calendar(
        app,
        admin["id"],
        zone_name="America/Bogota",
        franjas=[
            *(Franja(day, parse_time("08:00"), parse_time("17:00")) for day in range(4)),
            Franja(4, parse_time("08:00"), parse_time("13:00")),
        ],
        holidays=[
            Holiday(date(2000, 1, 1), "Año Nuevo antiguo"),
            Holiday(date(2099, 12, 24), "Nochebuena"),
            Holiday(date(2099, 12, 25), "Navidad"),
        ],
    )
    login(client, admin)
    page = plain_text(client.get(SLA_URL))

    assert "Configurado · versión 1" in page
    assert "Por defecto" not in page
    assert "Lunes a jueves · 08:00–17:00" in page
    assert "Viernes · 08:00–13:00" in page
    assert "America/Bogota" in page
    assert "3 feriados en total" in page
    # Solo los que aún no pasaron.
    assert "24-12-2099 Nochebuena" in page
    assert "25-12-2099 Navidad" in page
    assert "01-01-2000" not in page.split("Próximos:")[1].split("Guardado")[0]
    assert "Administrador Pruebas" in page


def test_only_the_next_holidays_are_listed(client, app, admin):
    saved_calendar(
        app,
        admin["id"],
        holidays=[Holiday(date(2099, 1, day), f"Feriado {day}") for day in range(1, 9)],
    )
    login(client, admin)
    page = plain_text(client.get(SLA_URL))

    assert "8 feriados en total" in page
    assert "Feriado 5" in page
    assert "Feriado 6" not in page


def test_a_calendar_without_upcoming_holidays_says_so(client, app, admin):
    saved_calendar(app, admin["id"], holidays=[Holiday(date(2000, 1, 1), "Antiguo")])
    login(client, admin)

    assert "1 feriado en total. Ninguno próximo." in plain_text(client.get(SLA_URL))


def test_the_sla_page_lists_every_version(client, app, admin):
    saved_calendar(app, admin["id"])
    saved_calendar(
        app,
        admin["id"],
        base_version=1,
        franjas=[Franja(day, parse_time("08:00"), parse_time("17:00")) for day in range(5)],
    )
    login(client, admin)
    html = client.get(SLA_URL).get_data(as_text=True)
    page = plain_text(client.get(SLA_URL))

    assert "Configurado · versión 2" in page
    assert page.index("Lunes a viernes 08:00–17:00") < page.index("Lunes a viernes 09:00–18:00")
    assert html.count("Vigente") == 1
    assert html.count("Anterior") == 1


def test_html_in_holiday_names_is_escaped(client, app, admin):
    saved_calendar(
        app,
        admin["id"],
        holidays=[Holiday(date(2099, 5, 1), "<script>alert('x')</script>")],
    )
    login(client, admin)

    for url in (SLA_URL, CALENDAR_URL):
        html = client.get(url).get_data(as_text=True)

        assert "<script>alert('x')" not in html
        assert "&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;" in html


# --- El formulario: abrirlo ---------------------------------------------------------------


def test_the_form_is_prefilled_with_the_default_calendar(client, admin):
    login(client, admin)
    response = client.get(CALENDAR_URL)
    html = response.get_data(as_text=True)
    values = field_values(html)

    assert response.status_code == 200
    assert values["zona_horaria"] == "America/Santiago"
    assert [values[f"dia_{number}"] for number in range(7)] == [
        "09:00-18:00", "09:00-18:00", "09:00-18:00", "09:00-18:00", "09:00-18:00", "", "",
    ]
    assert values["feriados"] == ""
    assert values["version_base"] == "0"
    assert "versión 1" in plain_text(response)
    assert "Todavía no hay un calendario guardado" in plain_text(response)


def test_the_form_is_prefilled_with_the_saved_calendar(client, app, admin):
    saved_calendar(
        app,
        admin["id"],
        zone_name="America/Bogota",
        franjas=[
            Franja(0, parse_time("09:00"), parse_time("13:00")),
            Franja(0, parse_time("14:00"), parse_time("18:00")),
            Franja(5, parse_time("10:00"), parse_time("12:00")),
        ],
        holidays=[
            Holiday(date(2099, 12, 25), "Navidad"),
            Holiday(date(2099, 1, 1), "Año Nuevo"),
        ],
    )
    login(client, admin)
    response = client.get(CALENDAR_URL)
    values = field_values(response.get_data(as_text=True))
    page = plain_text(response)

    assert values["zona_horaria"] == "America/Bogota"
    assert values["dia_0"] == "09:00-13:00, 14:00-18:00"
    assert values["dia_1"] == ""
    assert values["dia_5"] == "10:00-12:00"
    assert values["feriados"] == "01-01-2099 Año Nuevo\n25-12-2099 Navidad"
    assert values["version_base"] == "1"
    assert "Vigente: versión 1" in page
    assert "se creará la versión 2" in page


def test_opening_the_form_saves_nothing(client, app, admin):
    login(client, admin)
    client.get(CALENDAR_URL)

    assert versions(app) == []


def test_the_form_offers_the_known_time_zones(client, admin):
    login(client, admin)
    html = client.get(CALENDAR_URL).get_data(as_text=True)

    assert '<datalist id="zone-names">' in html
    assert '<option value="America/Santiago">' in html
    assert '<option value="UTC">' in html


# --- El formulario: guardar ----------------------------------------------------------------


def test_saving_the_first_calendar_through_the_screen(client, app, admin):
    login(client, admin)
    response = client.post(
        CALENDAR_URL,
        data=form_data(
            zona_horaria="America/Bogota",
            dia_4="08:00-14:00",
            dia_5="10:00-12:00",
            feriados="25-12-2099 Navidad\n1-1-2099 Año Nuevo",
            motivo="Horario de la sucursal",
            version_base="0",
        ),
        follow_redirects=True,
    )
    page = plain_text(response)

    assert response.status_code == 200
    assert "Calendario laboral guardado: versión 1." in page
    assert "Configurado · versión 1" in page
    assert "Lunes a jueves · 09:00–18:00" in page
    assert "Viernes · 08:00–14:00" in page
    assert "Sábado · 10:00–12:00" in page
    assert "America/Bogota" in page
    assert versions(app) == [(1, True)]


def test_saving_creates_a_new_version_each_time(client, app, admin):
    login(client, admin)
    client.post(CALENDAR_URL, data=form_data(version_base="0"))
    response = client.post(
        CALENDAR_URL,
        data=form_data(dia_4="09:00-17:00", version_base="1"),
        follow_redirects=True,
    )

    assert "Calendario laboral guardado: versión 2." in plain_text(response)
    assert versions(app) == [(1, False), (2, True)]


def test_the_audit_keeps_who_saved_and_why(client, app, admin):
    login(client, admin)
    client.post(
        CALENDAR_URL,
        data=form_data(dia_4="09:00-17:00", motivo="Cierra antes los viernes"),
    )

    with app.app_context():
        (entry,) = db.session.scalars(
            db.select(AdminAuditLog).where(
                AdminAuditLog.accion == "CALENDARIO_LABORAL_GUARDADO"
            )
        )

        assert entry.actor_usuario_id == admin["id"]
        assert entry.motivo == "Cierra antes los viernes"
        assert entry.detalle == "Versión 1"
        assert entry.valor_nuevo["horario"]["viernes"] == "09:00-17:00"


def test_saving_the_same_content_warns_and_creates_nothing(client, app, admin):
    saved_calendar(app, admin["id"])
    login(client, admin)
    response = client.post(
        CALENDAR_URL, data=form_data(version_base="1"), follow_redirects=True
    )

    assert "No hay cambios que guardar." in plain_text(response)
    assert versions(app) == [(1, True)]


def test_a_stale_screen_reopens_the_current_calendar_and_saves_nothing(
    client, app, admin
):
    # La pantalla se abrió cuando no había nada guardado (versión base 0)...
    login(client, admin)
    stale = form_data(dia_4="10:00-19:00", version_base="0")
    # ...y mientras tanto alguien guardó otro calendario.
    saved_calendar(
        app,
        admin["id"],
        franjas=[Franja(day, parse_time("08:00"), parse_time("12:00")) for day in range(5)],
    )

    response = client.post(CALENDAR_URL, data=stale, follow_redirects=True)
    page = plain_text(response)
    values = field_values(response.get_data(as_text=True))

    assert "Otra persona guardó el calendario mientras lo editabas" in page
    # Vuelve el formulario con lo vigente y su versión: lo escrito no pisa nada.
    assert values["dia_4"] == "08:00-12:00"
    assert values["version_base"] == "1"
    assert versions(app) == [(1, True)]


def test_a_post_without_the_version_is_refused_instead_of_completed(client, app, admin):
    login(client, admin)
    data = form_data()
    del data["version_base"]
    response = client.post(CALENDAR_URL, data=data)

    assert response.status_code == 200
    assert "No se pudo comprobar la versión del calendario" in plain_text(response)
    assert versions(app) == []


# --- El formulario: errores --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"dia_1": "mañana"}, "«mañana» no tiene el formato HH:MM-HH:MM"),
        ({"dia_2": "18:00-09:00"}, "el inicio debe ser anterior al fin"),
        ({"dia_3": "09:00-13:00, 12:00-18:00"}, "se solapan"),
        ({"dia_4": "09:00-25:00"}, "hora que no existe"),
        ({"feriados": "25-12-2099 Navidad\nmañana Año Nuevo"}, "Línea 2: «mañana» no es una fecha válida"),
        ({"feriados": "25-12-2099"}, "Línea 1: falta el nombre del feriado"),
        ({"feriados": "25-12-2099 A\n25-12-2099 B"}, "Línea 2: el 25-12-2099 ya está en la línea 1"),
        ({"zona_horaria": "Mars/Olympus"}, "La zona horaria «Mars/Olympus» no existe"),
        ({"zona_horaria": ""}, "Ingresa la zona horaria"),
        ({"motivo": "x" * 501}, "Máximo 500 caracteres"),
        ({"version_base": "abc"}, "Ingresa un número entero"),
        ({"version_base": "-1"}, "No se pudo comprobar la versión"),
    ],
)
def test_a_badly_written_form_says_where_and_saves_nothing(
    client, app, admin, changes, message
):
    login(client, admin)
    response = client.post(CALENDAR_URL, data=form_data(**changes))

    assert response.status_code == 200
    assert message in plain_text(response)
    assert 'aria-invalid="true"' in response.get_data(as_text=True) or "alert-danger" in response.get_data(as_text=True)
    assert versions(app) == []


def test_the_form_keeps_what_was_typed_when_something_is_wrong(client, admin):
    login(client, admin)
    response = client.post(
        CALENDAR_URL,
        data=form_data(
            zona_horaria="America/Bogota",
            dia_0="08:00-12:00, 13:00-17:00",
            dia_1="mal",
            feriados="25-12-2099 Navidad",
            motivo="Un motivo",
            version_base="0",
        ),
    )
    values = field_values(response.get_data(as_text=True))

    assert values["zona_horaria"] == "America/Bogota"
    assert values["dia_0"] == "08:00-12:00, 13:00-17:00"
    assert values["dia_1"] == "mal"
    assert values["feriados"] == "25-12-2099 Navidad"
    assert values["motivo"] == "Un motivo"
    assert values["version_base"] == "0"


def test_a_calendar_without_working_days_is_refused(client, app, admin):
    login(client, admin)
    response = client.post(
        CALENDAR_URL,
        data=form_data(**{f"dia_{number}": "" for number in range(7)}),
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Escribe el horario de al menos un día" in plain_text(response)
    assert 'role="alert"' in html
    assert versions(app) == []


def test_every_error_is_reported_at_once(client, admin):
    login(client, admin)
    response = client.post(
        CALENDAR_URL,
        data=form_data(
            zona_horaria="Mars/Olympus", dia_0="mal", dia_1="también mal", feriados="x"
        ),
    )
    page = plain_text(response)

    assert "La zona horaria «Mars/Olympus» no existe" in page
    assert "«mal» no tiene el formato" in page
    assert "«también mal» no tiene el formato" in page
    assert "Línea 1: «x» no es una fecha válida" in page
