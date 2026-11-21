"""Pantallas de los objetivos de SLA por prioridad (docs/11, UI-022): la tabla en
«SLA», el formulario de definir o editar y las confirmaciones de desactivar y
reactivar. Son exclusivas del Administrador."""

import re

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Estado, PoliticaSla, Prioridad
from src.workdesk.sla import policy_routes
from src.workdesk.sla.policies import (
    PolicyRuleError,
    deactivate_policy,
    get_policy,
    policy_token,
)
from tests.ticket_helpers import login, person, plain_text

SLA_URL = "/admin/sla"


# --- Auxiliares -------------------------------------------------------------


@pytest.fixture()
def admin(app, make_user, seeded_catalogs):
    return make_user("ADMINISTRADOR", username="admin")


def priority_by_code(code) -> Prioridad:
    return db.session.scalar(db.select(Prioridad).where(Prioridad.codigo == code))


def priority_id(app, code) -> int:
    with app.app_context():
        return priority_by_code(code).id


def url(app, code, action="edit") -> str:
    return f"{SLA_URL}/priorities/{priority_id(app, code)}/{action}"


def policy_of(app, code) -> dict | None:
    """Los valores de la política guardada, como un diccionario (o None)."""
    with app.app_context():
        policy = get_policy(priority_by_code(code))

        if policy is None:
            return None

        return {
            "respuesta": policy.tiempo_objetivo_respuesta_minutos,
            "resolucion": policy.tiempo_objetivo_resolucion_minutos,
            "umbral": policy.umbral_aviso_consumo_porcentaje,
            "pausa": policy.pausa_en_espera,
            "activo": policy.activo,
            "modificada": policy.fecha_modificacion,
        }


def remove_policy(app, code) -> None:
    with app.app_context():
        db.session.delete(get_policy(priority_by_code(code)))
        db.session.commit()


def token_of(app, code) -> str:
    with app.app_context():
        return policy_token(get_policy(priority_by_code(code)))


def audit(app, action) -> list[AdminAuditLog]:
    with app.app_context():
        return list(
            db.session.scalars(
                db.select(AdminAuditLog)
                .where(AdminAuditLog.accion == action)
                .order_by(AdminAuditLog.id)
            )
        )


def open_form(client, address) -> tuple[str, dict[str, str]]:
    """Abre el formulario y devuelve su HTML y los valores con que se llenó."""
    html = client.get(address).get_data(as_text=True)
    values = {}

    for name in ("primera_respuesta", "resolucion", "umbral_aviso", "base", "motivo"):
        match = re.search(rf'<input[^>]*name="{name}"[^>]*value="([^"]*)"', html)
        values[name] = match.group(1) if match else None

    values["pausa"] = bool(
        re.search(r'name="pausa_en_espera"[^>]*\bchecked\b', html)
    )

    return html, values


def submitted(values, **changes) -> dict[str, str]:
    """Lo que enviaría el navegador con lo que trajo el formulario, más los
    cambios. Un valor `None` omite el campo."""
    data = {
        "primera_respuesta": values["primera_respuesta"],
        "resolucion": values["resolucion"],
        "umbral_aviso": values["umbral_aviso"],
        "base": values["base"],
        "motivo": "",
    }

    if values["pausa"]:
        data["pausa_en_espera"] = "y"

    data.update(changes)

    return {name: value for name, value in data.items() if value is not None}


# --- Acceso -------------------------------------------------------------------


@pytest.mark.parametrize("action", ["edit", "deactivate", "activate"])
def test_an_anonymous_user_is_sent_to_the_login(client, app, admin, action):
    for method in (client.get, client.post):
        response = method(url(app, "ALTA", action))

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
@pytest.mark.parametrize("action", ["edit", "deactivate", "activate"])
def test_only_the_administrator_can_use_the_screens(
    client, app, make_user, admin, role, action
):
    login(client, make_user(role, username="persona"))
    before = policy_of(app, "ALTA")

    assert client.get(url(app, "ALTA", action)).status_code == 403
    assert client.post(url(app, "ALTA", action), data={"resolucion": "1 h"}).status_code == 403
    assert policy_of(app, "ALTA") == before
    assert audit(app, "POLITICA_SLA_MODIFICADA") == []
    assert audit(app, "POLITICA_SLA_DESACTIVADA") == []


@pytest.mark.parametrize("action", ["edit", "deactivate", "activate"])
def test_an_unknown_priority_is_a_404(client, admin, action):
    login(client, admin)

    for method in (client.get, client.post):
        assert method(f"{SLA_URL}/priorities/999999/{action}").status_code == 404


def test_the_sidebar_keeps_administration_active_on_the_policy_screens(client, app, admin):
    login(client, admin)

    for action in ("edit", "deactivate"):
        html = client.get(url(app, "ALTA", action)).get_data(as_text=True)

        assert re.search(r'data-label="Administración"\s*aria-current="page"', html)


# --- La tabla en «SLA» ---------------------------------------------------------------


def test_the_sla_page_shows_the_objectives_of_every_priority(client, admin):
    login(client, admin)
    response = client.get(SLA_URL)
    page = plain_text(response)

    assert response.status_code == 200
    assert "Configuración de SLA" in page
    assert "Objetivos por prioridad" in page
    assert "Primera respuesta Resolución Umbral de aviso Pausa en «En espera»" in page
    assert "Baja 8 h 24 h 80 % Sí Activa" in page
    assert "Media 4 h 12 h 80 % Sí Activa" in page
    assert "Alta 2 h 6 h 75 % Sí Activa" in page
    assert "Crítica 30 min 4 h 75 % Sí Activa" in page
    # El calendario y sus versiones siguen ahí.
    assert "Calendario laboral" in page
    assert "Versiones del calendario" in page


def test_the_priorities_are_listed_from_lowest_to_highest_level(client, admin):
    login(client, admin)
    page = plain_text(client.get(SLA_URL))
    table = page[page.index("Objetivos por prioridad") :]

    positions = [table.index(f"{name} ") for name in ("Baja", "Media", "Alta", "Crítica")]

    assert positions == sorted(positions)


def test_no_row_is_dimmed_when_every_policy_is_active(client, admin):
    login(client, admin)

    assert '<tr class="text-secondary">' not in client.get(SLA_URL).get_data(as_text=True)


def test_each_row_links_to_its_own_screens(client, app, admin):
    login(client, admin)
    html = client.get(SLA_URL).get_data(as_text=True)

    for code in ("BAJA", "MEDIA", "ALTA", "CRITICA"):
        assert f'href="{url(app, code, "edit")}"' in html
        assert f'href="{url(app, code, "deactivate")}"' in html
        # Está activa: no se ofrece reactivar.
        assert f'href="{url(app, code, "activate")}"' not in html


def test_an_objective_that_was_not_defined_is_shown_as_such(client, app, admin):
    with app.app_context():
        policy = get_policy(priority_by_code("MEDIA"))
        policy.tiempo_objetivo_respuesta_minutos = None
        policy.umbral_aviso_consumo_porcentaje = None
        policy.pausa_en_espera = False
        db.session.commit()

    login(client, admin)
    page = plain_text(client.get(SLA_URL))

    assert "Media Sin objetivo 12 h Sin aviso No Activa" in page


def test_a_priority_without_a_policy_offers_to_define_it(client, app, admin):
    remove_policy(app, "ALTA")
    login(client, admin)
    response = client.get(SLA_URL)
    html = response.get_data(as_text=True)
    page = plain_text(response)

    assert "Alta Sin objetivos: esta prioridad no tiene SLA. Sin definir" in page
    assert f'href="{url(app, "ALTA", "edit")}"' in html
    assert "Definir" in page
    # No hay nada que desactivar ni reactivar.
    assert f'href="{url(app, "ALTA", "deactivate")}"' not in html
    assert f'href="{url(app, "ALTA", "activate")}"' not in html


def test_an_inactive_policy_is_shown_dimmed_and_offers_to_reactivate_it(client, app, admin):
    with app.app_context():
        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()

    login(client, admin)
    response = client.get(SLA_URL)
    html = response.get_data(as_text=True)

    assert "Alta 2 h 6 h 75 % Sí Inactiva" in plain_text(response)
    assert f'href="{url(app, "ALTA", "activate")}"' in html
    assert f'href="{url(app, "ALTA", "deactivate")}"' not in html
    assert f'href="{url(app, "ALTA", "edit")}"' in html
    # La fila entera se atenúa (y solo la de la política desactivada).
    assert html.count('<tr class="text-secondary">') == 1


def test_an_inactive_priority_is_marked_but_still_listed(client, app, admin):
    with app.app_context():
        priority_by_code("BAJA").activo = False
        db.session.commit()

    login(client, admin)
    page = plain_text(client.get(SLA_URL))

    assert "Baja (inactiva) 8 h 24 h" in page


def test_the_column_title_follows_the_renaming_of_the_state(client, app, admin):
    with app.app_context():
        state = db.session.scalar(db.select(Estado).where(Estado.codigo == "EN_ESPERA"))
        state.nombre_visible = "En pausa"
        db.session.commit()

    login(client, admin)
    page = plain_text(client.get(SLA_URL))

    assert "Pausa en «En pausa»" in page
    assert "Pausa en «En espera»" not in page


def test_without_priorities_the_page_says_how_to_load_them(client, app, admin):
    with app.app_context():
        db.session.execute(db.delete(PoliticaSla))
        db.session.execute(db.delete(Prioridad))
        db.session.commit()

    login(client, admin)
    page = plain_text(client.get(SLA_URL))

    assert "No hay prioridades configuradas" in page
    assert "seed-catalogs" in page


def test_the_names_are_escaped(client, app, admin):
    with app.app_context():
        priority_by_code("ALTA").nombre = "<script>alert(1)</script>"
        db.session.commit()

    login(client, admin)

    for address in (SLA_URL, url(app, "ALTA", "edit"), url(app, "ALTA", "deactivate")):
        html = client.get(address).get_data(as_text=True)

        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


# --- El formulario: abrirlo ---------------------------------------------------------------


def test_the_form_opens_with_the_current_values(client, app, admin):
    login(client, admin)
    response = client.get(url(app, "ALTA"))
    page = plain_text(response)
    _, values = open_form(client, url(app, "ALTA"))

    assert response.status_code == 200
    assert "Editar objetivos de SLA: Alta" in page
    assert values["primera_respuesta"] == "2 h"
    assert values["resolucion"] == "6 h"
    assert values["umbral_aviso"] == "75"
    assert values["pausa"] is True
    assert values["base"] == token_of(app, "ALTA")
    assert "Guardar objetivos" in page
    assert 'action="' + url(app, "ALTA") + '"' in response.get_data(as_text=True)


def test_the_pause_label_uses_the_current_name_of_the_state(client, app, admin):
    login(client, admin)

    assert "Pausar el SLA mientras el ticket esté en «En espera»" in plain_text(
        client.get(url(app, "ALTA"))
    )

    with app.app_context():
        state = db.session.scalar(db.select(Estado).where(Estado.codigo == "EN_ESPERA"))
        state.nombre_visible = "En pausa"
        db.session.commit()

    assert "Pausar el SLA mientras el ticket esté en «En pausa»" in plain_text(
        client.get(url(app, "ALTA"))
    )


def test_a_priority_without_a_policy_opens_a_form_to_define_it(client, app, admin):
    remove_policy(app, "ALTA")
    login(client, admin)
    response = client.get(url(app, "ALTA"))
    page = plain_text(response)
    _, values = open_form(client, url(app, "ALTA"))

    assert "Definir objetivos de SLA: Alta" in page
    assert "Definir objetivos" in page
    assert values["primera_respuesta"] == ""
    assert values["resolucion"] == ""
    # El aviso propuesto y la pausa activada.
    assert values["umbral_aviso"] == "80"
    assert values["pausa"] is True
    assert values["base"] == "0"


def test_the_form_of_an_inactive_policy_warns_that_it_stays_inactive(client, app, admin):
    with app.app_context():
        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()

    login(client, admin)
    page = plain_text(client.get(url(app, "ALTA")))

    assert "Esta política está desactivada" in page
    assert "seguirá desactivada" in page


def test_an_active_policy_has_no_inactive_warning(client, app, admin):
    login(client, admin)

    assert "Esta política está desactivada" not in plain_text(client.get(url(app, "ALTA")))


def test_a_policy_without_first_response_opens_that_field_empty(client, app, admin):
    with app.app_context():
        policy = get_policy(priority_by_code("ALTA"))
        policy.tiempo_objetivo_respuesta_minutos = None
        policy.umbral_aviso_consumo_porcentaje = None
        policy.pausa_en_espera = False
        db.session.commit()

    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    assert values["primera_respuesta"] == ""
    assert values["umbral_aviso"] == ""
    assert values["pausa"] is False


# --- El formulario: guardar ----------------------------------------------------------------------


def test_editing_saves_the_changes_and_audits_them(client, app, admin):
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    response = client.post(
        url(app, "ALTA"),
        data=submitted(values, resolucion="3 h 30 min", motivo="Contrato nuevo"),
        follow_redirects=True,
    )
    page = plain_text(response)

    assert response.request.path == SLA_URL
    assert "SLA de la prioridad «Alta» actualizado." in page
    assert "Alta 2 h 3 h 30 min 75 %" in page

    saved = policy_of(app, "ALTA")

    assert saved["resolucion"] == 210
    assert saved["respuesta"] == 120
    assert saved["modificada"] is not None

    (entry,) = audit(app, "POLITICA_SLA_MODIFICADA")

    assert entry.actor_usuario_id == admin["id"]
    assert entry.motivo == "Contrato nuevo"
    assert entry.valor_anterior == {"tiempo_objetivo_resolucion_minutos": 360}
    assert entry.valor_nuevo == {"tiempo_objetivo_resolucion_minutos": 210}


def test_every_field_is_saved(client, app, admin):
    login(client, admin)
    _, values = open_form(client, url(app, "MEDIA"))

    client.post(
        url(app, "MEDIA"),
        data=submitted(
            values,
            primera_respuesta="",
            resolucion="2h",
            umbral_aviso="",
            pausa_en_espera=None,
        ),
    )

    saved = policy_of(app, "MEDIA")

    assert saved["respuesta"] is None
    assert saved["resolucion"] == 120
    assert saved["umbral"] is None
    assert saved["pausa"] is False


def test_saving_without_changes_says_so_and_audits_nothing(client, app, admin):
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    response = client.post(
        url(app, "ALTA"), data=submitted(values), follow_redirects=True
    )

    assert "No había cambios que guardar." in plain_text(response)
    assert policy_of(app, "ALTA")["modificada"] is None
    assert audit(app, "POLITICA_SLA_MODIFICADA") == []


def test_defining_a_missing_policy_creates_it(client, app, admin):
    remove_policy(app, "ALTA")
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    response = client.post(
        url(app, "ALTA"),
        data=submitted(values, primera_respuesta="45 min", resolucion="5 h"),
        follow_redirects=True,
    )
    page = plain_text(response)

    assert "SLA de la prioridad «Alta» definido." in page
    assert "Alta 45 min 5 h 80 % Sí Activa" in page

    saved = policy_of(app, "ALTA")

    assert saved["activo"] is True
    assert saved["resolucion"] == 300

    (entry,) = audit(app, "POLITICA_SLA_CREADA")

    assert entry.actor_usuario_id == admin["id"]


def test_editing_an_inactive_policy_keeps_it_inactive(client, app, admin):
    with app.app_context():
        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()

    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))
    client.post(url(app, "ALTA"), data=submitted(values, resolucion="9 h"))

    saved = policy_of(app, "ALTA")

    assert saved["resolucion"] == 540
    assert saved["activo"] is False


# --- El formulario: errores -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "field", "message"),
    [
        ({"resolucion": ""}, "resolucion", "Ingresa el objetivo de resolución."),
        ({"resolucion": "mucho"}, "resolucion", "no es una duración válida"),
        ({"resolucion": "4"}, "resolucion", "le falta la unidad"),
        ({"resolucion": "1,5 h"}, "resolucion", "enteros"),
        ({"resolucion": "0 min"}, "resolucion", "mayor que cero"),
        ({"resolucion": "1001 h"}, "resolucion", "no puede superar 1000 h"),
        ({"primera_respuesta": "7 h"}, "primera_respuesta", "no puede tardar más que la resolución (6 h)"),
        ({"primera_respuesta": "0 min"}, "primera_respuesta", "mayor que cero"),
        ({"primera_respuesta": "rápido"}, "primera_respuesta", "no es una duración válida"),
        ({"umbral_aviso": "0"}, "umbral_aviso", "entre 1 y 100"),
        ({"umbral_aviso": "101"}, "umbral_aviso", "entre 1 y 100"),
        ({"umbral_aviso": "abc"}, "umbral_aviso", "Ingresa un número entero."),
        ({"motivo": "x" * 501}, "motivo", "Máximo 500 caracteres."),
    ],
)
def test_an_invalid_value_is_reported_next_to_its_field_and_saves_nothing(
    client, app, admin, changes, field, message
):
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))
    before = policy_of(app, "ALTA")

    response = client.post(url(app, "ALTA"), data=submitted(values, **changes))
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'id="{field}-error"' in html
    assert message in plain_text(response)
    assert policy_of(app, "ALTA") == before
    assert audit(app, "POLITICA_SLA_MODIFICADA") == []


def test_the_form_keeps_what_was_written_when_there_are_errors(client, app, admin):
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    response = client.post(
        url(app, "ALTA"),
        data=submitted(values, resolucion="unas horas", primera_respuesta="3 h"),
    )
    kept = {}
    html = response.get_data(as_text=True)

    for name in ("primera_respuesta", "resolucion"):
        match = re.search(rf'<input[^>]*name="{name}"[^>]*value="([^"]*)"', html)
        kept[name] = match.group(1)

    assert kept == {"primera_respuesta": "3 h", "resolucion": "unas horas"}


def test_every_error_is_reported_at_once(client, app, admin):
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    response = client.post(
        url(app, "ALTA"),
        data=submitted(
            values, primera_respuesta="x", resolucion="y", umbral_aviso="500"
        ),
    )
    html = response.get_data(as_text=True)

    for field in ("primera_respuesta", "resolucion", "umbral_aviso"):
        assert f'id="{field}-error"' in html


def test_a_screen_that_was_open_while_someone_else_saved_is_not_saved(client, app, admin, make_user):
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    # Otra persona guarda mientras tanto, desde su propia sesión.
    other = make_user("ADMINISTRADOR", username="otro_admin")
    second = app.test_client()
    login(second, other)
    _, other_values = open_form(second, url(app, "ALTA"))
    second.post(url(app, "ALTA"), data=submitted(other_values, resolucion="3 h"))

    response = client.post(
        url(app, "ALTA"), data=submitted(values, resolucion="9 h"), follow_redirects=True
    )
    page = plain_text(response)
    _, current = open_form(client, url(app, "ALTA"))

    assert "Otra persona modificó los objetivos de esta prioridad" in page
    # Se vuelve al formulario con lo vigente: lo escrito se pierde a propósito.
    assert response.request.path == url(app, "ALTA")
    assert current["resolucion"] == "3 h"
    assert policy_of(app, "ALTA")["resolucion"] == 180
    assert len(audit(app, "POLITICA_SLA_MODIFICADA")) == 1


def test_a_request_without_the_token_cannot_skip_the_check(client, app, admin):
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))
    before = policy_of(app, "ALTA")

    response = client.post(
        url(app, "ALTA"), data=submitted(values, base=None, resolucion="9 h")
    )

    assert response.status_code == 200
    assert "Recarga la página" in plain_text(response)
    assert policy_of(app, "ALTA") == before


def test_a_form_opened_before_the_policy_existed_cannot_create_it_twice(client, app, admin):
    remove_policy(app, "ALTA")
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    # Mientras la pantalla estaba abierta, la política se definió por otra vía.
    with app.app_context():
        db.session.add(
            PoliticaSla(
                prioridad_id=priority_by_code("ALTA").id,
                tiempo_objetivo_resolucion_minutos=100,
            )
        )
        db.session.commit()

    response = client.post(
        url(app, "ALTA"), data=submitted(values, resolucion="9 h"), follow_redirects=True
    )

    assert "Otra persona modificó los objetivos" in plain_text(response)
    assert policy_of(app, "ALTA")["resolucion"] == 100
    assert audit(app, "POLITICA_SLA_CREADA") == []


def test_a_rule_error_from_the_service_is_shown_next_to_its_field(
    client, app, admin, monkeypatch
):
    def refuse(*args, **kwargs):
        raise PolicyRuleError("Valor no aceptado.", "resolucion")

    monkeypatch.setattr(policy_routes, "save_policy", refuse)
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    response = client.post(url(app, "ALTA"), data=submitted(values))

    assert response.status_code == 200
    assert 'id="resolucion-error"' in response.get_data(as_text=True)
    assert "Valor no aceptado." in plain_text(response)


def test_a_rule_error_without_a_field_is_shown_as_a_notice(client, app, admin, monkeypatch):
    def refuse(*args, **kwargs):
        raise PolicyRuleError("No se puede guardar ahora.")

    monkeypatch.setattr(policy_routes, "save_policy", refuse)
    login(client, admin)
    _, values = open_form(client, url(app, "ALTA"))

    response = client.post(url(app, "ALTA"), data=submitted(values))

    assert response.status_code == 200
    assert "No se puede guardar ahora." in plain_text(response)


# --- Desactivar y reactivar ----------------------------------------------------------------------


def test_the_confirmation_to_deactivate_explains_the_effect(client, app, admin):
    login(client, admin)
    response = client.get(url(app, "ALTA", "deactivate"))
    page = plain_text(response)

    assert response.status_code == 200
    assert "Desactivar SLA: Alta" in page
    assert "La prioridad «Alta» dejará de tener SLA" in page
    assert "El SLA que ya tienen en curso no cambia" in page
    assert "Motivo" in page
    # Mirar la confirmación no cambia nada.
    assert policy_of(app, "ALTA")["activo"] is True


def test_deactivating_removes_the_sla_and_records_the_reason(client, app, admin):
    login(client, admin)

    response = client.post(
        url(app, "ALTA", "deactivate"),
        data={"motivo": "Se revisa el contrato"},
        follow_redirects=True,
    )
    page = plain_text(response)

    assert response.request.path == SLA_URL
    assert "SLA de la prioridad «Alta» desactivado." in page
    assert "Alta 2 h 6 h 75 % Sí Inactiva" in page
    assert policy_of(app, "ALTA")["activo"] is False

    (entry,) = audit(app, "POLITICA_SLA_DESACTIVADA")

    assert entry.motivo == "Se revisa el contrato"
    assert entry.valor_nuevo == {"activo": False}


def test_reactivating_restores_the_objectives(client, app, admin):
    login(client, admin)
    client.post(url(app, "ALTA", "deactivate"), data={})

    response = client.get(url(app, "ALTA", "activate"))

    assert "Reactivar SLA: Alta" in plain_text(response)

    response = client.post(
        url(app, "ALTA", "activate"), data={"motivo": "Vuelve"}, follow_redirects=True
    )

    assert "SLA de la prioridad «Alta» reactivado." in plain_text(response)
    assert "Alta 2 h 6 h 75 % Sí Activa" in plain_text(response)
    assert policy_of(app, "ALTA")["activo"] is True
    assert audit(app, "POLITICA_SLA_ACTIVADA")[0].motivo == "Vuelve"


def test_the_reason_is_optional(client, app, admin):
    login(client, admin)
    client.post(url(app, "ALTA", "deactivate"), data={})

    assert policy_of(app, "ALTA")["activo"] is False
    assert audit(app, "POLITICA_SLA_DESACTIVADA")[0].motivo is None


def test_an_overlong_reason_keeps_the_confirmation_open(client, app, admin):
    login(client, admin)

    response = client.post(url(app, "ALTA", "deactivate"), data={"motivo": "x" * 501})

    assert response.status_code == 200
    assert "Máximo 500 caracteres." in plain_text(response)
    assert policy_of(app, "ALTA")["activo"] is True


@pytest.mark.parametrize(
    ("action", "message"),
    [
        ("activate", "La política ya está activa."),
        ("deactivate", "La política ya está desactivada."),
    ],
)
def test_an_action_that_no_longer_applies_goes_back_with_a_notice(
    client, app, admin, action, message
):
    login(client, admin)

    if action == "deactivate":
        client.post(url(app, "ALTA", "deactivate"), data={})

    # También al abrir la confirmación (GET), para no ofrecer algo imposible.
    for method in (client.get, client.post):
        response = method(url(app, "ALTA", action), data={}, follow_redirects=True)

        assert response.request.path == SLA_URL
        assert message in plain_text(response)


@pytest.mark.parametrize("action", ["activate", "deactivate"])
def test_a_priority_without_a_policy_has_nothing_to_confirm(client, app, admin, action):
    remove_policy(app, "ALTA")
    login(client, admin)

    for method in (client.get, client.post):
        response = method(url(app, "ALTA", action), data={}, follow_redirects=True)

        assert response.request.path == SLA_URL
        assert "todavía no tiene una política de SLA" in plain_text(response)


def test_the_cancel_links_go_back_to_the_sla_page(client, app, admin):
    login(client, admin)

    for address in (url(app, "ALTA"), url(app, "ALTA", "deactivate")):
        html = client.get(address).get_data(as_text=True)

        assert f'href="{SLA_URL}"' in html
