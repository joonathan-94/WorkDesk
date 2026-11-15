import re

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    Categoria,
    Prioridad,
    Ticket,
    TicketHistory,
    Ubicacion,
    User,
)
from src.workdesk.tickets.editing import update_ticket
from tests.ticket_helpers import (
    login,
    make_ticket,
    plain_text,
    set_state,
    text,
)

STAFF_ROLES = ("TECNICO", "SUPERVISOR", "ADMINISTRADOR")


@pytest.fixture()
def staff(make_user, catalog):
    return make_user("TECNICO", username="personal")


@pytest.fixture()
def owner(make_user, catalog):
    return make_user("SOLICITANTE", username="dueno")


@pytest.fixture()
def public_id(app, catalog, staff, owner):
    """Un ticket creado por el personal a nombre del Solicitante `owner`."""
    return make_ticket(
        app,
        catalog,
        staff["id"],
        requester_ids=[owner["id"]],
        title="Título original",
        description="Descripción original",
    )


def state(app, public_id) -> dict:
    with app.app_context():
        ticket = db.session.scalar(
            db.select(Ticket).where(Ticket.public_id == public_id)
        )

        return {
            "titulo": ticket.titulo,
            "descripcion": ticket.descripcion,
            "categoria": ticket.categoria_id,
            "prioridad": ticket.prioridad_id,
            "ubicacion": ticket.ubicacion_id,
            "version": ticket.version,
            "eventos": [
                entry.tipo_evento
                for entry in db.session.scalars(
                    db.select(TicketHistory)
                    .where(TicketHistory.ticket_id == ticket.id)
                    .order_by(TicketHistory.id)
                )
            ],
        }


def edit_data(catalog, **overrides):
    data = {
        "titulo": "Título original",
        "descripcion": "Descripción original",
        "categoria": catalog["hardware"],
        "ubicacion": "",
        "version": 1,
    }
    data.update(overrides)

    return data


def priority_data(catalog, **overrides):
    data = {
        "prioridad": catalog["high"],
        "motivo": "El cliente no puede trabajar.",
        "version": 1,
    }
    data.update(overrides)

    return data


def options(response, field_id: str) -> list[tuple[str, bool, str]]:
    html = response.get_data(as_text=True)
    block = re.search(
        rf'<select[^>]*id="{field_id}".*?</select>',
        html,
        re.DOTALL,
    ).group(0)

    return [
        (value, "selected" in attributes, label)
        for value, attributes, label in re.findall(
            r'<option\s+value="(\d*)"([^>]*)>\s*([^<]*?)\s*</option>',
            block,
            re.DOTALL,
        )
    ]


# --- Acceso -----------------------------------------------------------


@pytest.mark.parametrize("suffix", ["edit", "priority"])
@pytest.mark.parametrize("method", ["get", "post"])
def test_anonymous_user_is_redirected_to_login(
    client,
    public_id,
    suffix,
    method,
):
    response = getattr(client, method)(f"/tickets/{public_id}/{suffix}")

    assert response.status_code == 302
    assert "/login" in response.location


@pytest.mark.parametrize("suffix", ["edit", "priority"])
@pytest.mark.parametrize("role_code", STAFF_ROLES)
def test_staff_can_open_both_screens(
    client,
    make_user,
    public_id,
    suffix,
    role_code,
):
    login(client, make_user(role_code, username="otro_personal"))

    assert client.get(f"/tickets/{public_id}/{suffix}").status_code == 200


@pytest.mark.parametrize("suffix", ["edit", "priority"])
def test_a_solicitante_who_can_see_the_ticket_gets_a_403(
    client,
    app,
    catalog,
    owner,
    public_id,
    suffix,
):
    login(client, owner)
    before = state(app, public_id)

    get = client.get(f"/tickets/{public_id}/{suffix}")
    post = client.post(
        f"/tickets/{public_id}/{suffix}",
        data=edit_data(catalog, titulo="Intruso")
        if suffix == "edit"
        else priority_data(catalog),
    )

    assert get.status_code == 403
    assert post.status_code == 403
    assert state(app, public_id) == before


@pytest.mark.parametrize("suffix", ["edit", "priority"])
@pytest.mark.parametrize("method", ["get", "post"])
def test_someone_elses_ticket_looks_like_a_missing_one(
    client,
    make_user,
    public_id,
    suffix,
    method,
):
    login(client, make_user("SOLICITANTE", username="ajeno"))

    response = getattr(client, method)(f"/tickets/{public_id}/{suffix}")
    missing = getattr(client, method)(f"/tickets/999999/{suffix}")

    assert response.status_code == missing.status_code == 404


@pytest.mark.parametrize("suffix", ["edit", "priority"])
@pytest.mark.parametrize("public_id_value", ["999999", "abc", "-1", "1.5"])
def test_unknown_tickets_are_a_404_for_staff(
    client,
    staff,
    suffix,
    public_id_value,
):
    login(client, staff)

    assert client.get(f"/tickets/{public_id_value}/{suffix}").status_code == 404


@pytest.mark.parametrize("suffix", ["edit", "priority"])
def test_a_closed_ticket_redirects_to_the_detail_with_a_message(
    client,
    app,
    catalog,
    staff,
    public_id,
    suffix,
):
    set_state(app, public_id, "CERRADO")
    login(client, staff)
    before = state(app, public_id)

    get = client.get(f"/tickets/{public_id}/{suffix}", follow_redirects=True)
    post = client.post(
        f"/tickets/{public_id}/{suffix}",
        data=edit_data(catalog, titulo="Nuevo")
        if suffix == "edit"
        else priority_data(catalog),
    )

    assert "Un ticket cerrado no se puede editar." in text(get)
    assert post.status_code == 302
    assert state(app, public_id) == before


# --- Botones del detalle ----------------------------------------------


def test_staff_sees_the_edit_buttons_in_the_detail(
    client,
    staff,
    public_id,
):
    login(client, staff)

    content = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert f'href="/tickets/{public_id}/edit"' in content
    assert f'href="/tickets/{public_id}/priority"' in content


def test_a_solicitante_does_not_see_the_edit_buttons(
    client,
    owner,
    public_id,
):
    login(client, owner)

    content = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert f"/tickets/{public_id}/edit" not in content
    assert f"/tickets/{public_id}/priority" not in content


def test_a_closed_ticket_shows_no_buttons_but_explains_why(
    client,
    app,
    staff,
    public_id,
):
    set_state(app, public_id, "CERRADO")
    login(client, staff)

    response = client.get(f"/tickets/{public_id}")
    content = response.get_data(as_text=True)

    assert f"/tickets/{public_id}/edit" not in content
    assert "Un ticket cerrado no se puede editar." in text(response)


def test_the_detail_shows_when_it_was_last_updated(client, staff, public_id):
    login(client, staff)

    assert "Actualizado" in text(client.get(f"/tickets/{public_id}"))


# --- Editar datos -----------------------------------------------------


def test_the_edit_form_is_prefilled(client, catalog, staff, public_id):
    login(client, staff)

    response = client.get(f"/tickets/{public_id}/edit")
    content = response.get_data(as_text=True)

    assert 'value="Título original"' in content
    assert "Descripción original</textarea>" in content
    assert re.search(r'name="version"\s+value="1"', content)
    assert "20/2000" in text(response)

    categories = options(response, "categoria")

    assert [label for _, selected, label in categories if selected] == [
        "Hardware"
    ]


def test_the_edit_form_keeps_the_current_location(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        location_id=catalog["location"],
    )
    login(client, staff)

    locations = options(client.get(f"/tickets/{public_id}/edit"), "ubicacion")

    assert [label for _, selected, label in locations if selected] == [
        "Casa matriz"
    ]


def test_a_successful_edit_updates_the_ticket_and_the_history(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    login(client, staff)

    response = client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(
            catalog,
            titulo="  Título nuevo ",
            descripcion="Descripción nueva",
            categoria=catalog["networks"],
            ubicacion=catalog["location"],
        ),
        follow_redirects=True,
    )
    content = plain_text(response)
    after = state(app, public_id)

    assert response.status_code == 200
    assert f"Ticket #{public_id} actualizado." in content
    assert after["titulo"] == "Título nuevo"
    assert after["descripcion"] == "Descripción nueva"
    assert after["categoria"] == catalog["networks"]
    assert after["ubicacion"] == catalog["location"]
    assert after["version"] == 2
    assert after["eventos"] == [
        "TICKET_CREADO",
        "TICKET_MODIFICADO",
        "CATEGORIA_CAMBIADA",
    ]
    # El historial del detalle explica qué cambió.
    assert "Título: «Título original» → «Título nuevo»" in content
    assert "Descripción modificada." in content
    assert "Categoría: «Hardware» → «Redes»" in content
    assert "Ubicación: — → «Casa matriz»" in content


def test_an_edit_without_changes_only_warns(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    login(client, staff)
    before = state(app, public_id)

    response = client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(catalog),
        follow_redirects=True,
    )

    assert "No había cambios que guardar." in text(response)
    assert state(app, public_id) == before


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"titulo": "  "}, "Ingresa un título."),
        ({"titulo": "a" * 201}, "Máximo 200 caracteres."),
        ({"descripcion": "  "}, "Describe tu solicitud."),
        ({"descripcion": "a" * 2001}, "Máximo 2000 caracteres."),
        ({"categoria": ""}, "Selecciona una categoría."),
        ({"categoria": 999999}, "Selecciona una categoría."),
        ({"categoria": "abc"}, "Ingresa un número entero."),
        ({"ubicacion": 999999}, "Selecciona una ubicación válida."),
        ({"version": ""}, "No se pudo comprobar la versión del ticket."),
        ({"version": "0"}, "No se pudo comprobar la versión del ticket."),
        ({"version": "abc"}, "Ingresa un número entero."),
    ],
)
def test_invalid_edits_are_rejected_without_changing_anything(
    client,
    app,
    catalog,
    staff,
    public_id,
    overrides,
    message,
):
    login(client, staff)
    before = state(app, public_id)

    response = client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(catalog, **overrides),
    )

    assert response.status_code == 200
    assert message in text(response)
    assert state(app, public_id) == before


def test_the_edit_form_keeps_what_was_typed_after_an_error(
    client,
    catalog,
    staff,
    public_id,
):
    login(client, staff)

    response = client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(
            catalog,
            titulo="Mi título nuevo",
            descripcion="  ",
            categoria=catalog["networks"],
        ),
    )
    content = response.get_data(as_text=True)

    assert 'value="Mi título nuevo"' in content
    assert re.search(r'name="version"\s+value="1"', content)
    assert [
        label
        for _, selected, label in options(response, "categoria")
        if selected
    ] == ["Redes"]


def test_a_deactivated_current_category_can_be_kept(
    client,
    app,
    catalog,
    staff,
):
    public_id = make_ticket(
        app,
        catalog,
        staff["id"],
        category_id=catalog["networks"],
    )

    with app.app_context():
        db.session.get(Categoria, catalog["networks"]).activo = False
        db.session.commit()

    login(client, staff)
    form = client.get(f"/tickets/{public_id}/edit")

    labels = [label for _, _, label in options(form, "categoria")]

    # Se ofrece la actual, marcada; las demás desactivadas no existen aquí.
    assert "Redes (inactiva)" in labels

    client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(
            catalog,
            titulo="Solo el título",
            categoria=catalog["networks"],
        ),
    )

    after = state(app, public_id)

    assert after["titulo"] == "Solo el título"
    assert after["categoria"] == catalog["networks"]


def test_another_deactivated_category_is_not_offered_nor_accepted(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        db.session.get(Categoria, catalog["networks"]).activo = False
        db.session.commit()

    login(client, staff)
    form = client.get(f"/tickets/{public_id}/edit")

    assert "Redes" not in [label for _, _, label in options(form, "categoria")]

    response = client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(catalog, categoria=catalog["networks"]),
    )

    assert "Selecciona una categoría." in text(response)
    assert state(app, public_id)["categoria"] == catalog["hardware"]


def test_the_edit_form_requires_the_csrf_token(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    login(client, staff)
    app.config["WTF_CSRF_ENABLED"] = True
    before = state(app, public_id)

    response = client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(catalog, titulo="Sin token"),
    )

    assert response.status_code == 400
    assert state(app, public_id) == before


def test_an_edit_that_lost_the_race_does_not_overwrite_the_other_change(
    client,
    app,
    catalog,
    staff,
    make_user,
    public_id,
):
    other = make_user("SUPERVISOR", username="otro_sup")
    login(client, staff)

    # La persona A abre el formulario (versión 1)...
    form = client.get(f"/tickets/{public_id}/edit")

    assert re.search(r'name="version"\s+value="1"', form.get_data(as_text=True))

    # ...la persona B guarda un cambio antes que ella...
    with app.app_context():
        ticket = db.session.scalar(
            db.select(Ticket).where(Ticket.public_id == public_id)
        )
        update_ticket(
            ticket,
            actor=db.session.get(User, other["id"]),
            expected_version=1,
            title="Cambio de B",
            description=ticket.descripcion,
            category_id=ticket.categoria_id,
            location_id=ticket.ubicacion_id,
        )
        db.session.commit()

    # ...y cuando A envía el suyo, se rechaza.
    response = client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(catalog, titulo="Cambio de A"),
    )

    assert response.status_code == 302
    assert response.location.endswith(f"/tickets/{public_id}/edit")

    after = state(app, public_id)

    assert after["titulo"] == "Cambio de B"
    assert after["version"] == 2

    # Se vuelve al formulario con los datos actuales y un aviso.
    refreshed = client.get(response.location)
    content = refreshed.get_data(as_text=True)

    assert "Otra persona modificó este ticket" in text(refreshed)
    assert 'value="Cambio de B"' in content
    assert re.search(r'name="version"\s+value="2"', content)


# --- Cambiar prioridad ------------------------------------------------


def test_the_priority_form_offers_the_active_priorities(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        low = db.session.scalar(
            db.select(Prioridad).where(Prioridad.codigo == "BAJA")
        )
        low.activo = False
        db.session.commit()

    login(client, staff)
    response = client.get(f"/tickets/{public_id}/priority")

    labels = [label for _, _, label in options(response, "prioridad")]

    assert labels == [
        "Selecciona la nueva prioridad",
        "Media (actual)",
        "Alta",
        "Crítica",
    ]
    # No viene ninguna preseleccionada: hay que elegir la nueva.
    assert not any(selected for _, selected, _ in options(response, "prioridad"))
    assert re.search(
        r'name="version"\s+value="1"',
        response.get_data(as_text=True),
    )


def test_a_successful_priority_change(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    login(client, staff)

    response = client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog),
        follow_redirects=True,
    )
    after = state(app, public_id)
    content = plain_text(response)

    assert f"La prioridad del ticket #{public_id} se actualizó." in content
    assert after["prioridad"] == catalog["high"]
    assert after["version"] == 2
    assert after["eventos"] == ["TICKET_CREADO", "PRIORIDAD_CAMBIADA"]
    # El personal ve qué cambió y por qué.
    assert "Prioridad: «Media» → «Alta»" in content
    assert "Motivo: El cliente no puede trabajar." in content


def test_the_solicitante_sees_what_changed_but_not_why(
    client,
    app,
    catalog,
    staff,
    owner,
    public_id,
):
    login(client, staff)
    client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog, motivo="Nota interna confidencial."),
    )
    client.post("/logout")

    login(client, owner)
    content = plain_text(client.get(f"/tickets/{public_id}"))

    assert "Prioridad cambiada" in content
    assert "Prioridad: «Media» → «Alta»" in content
    assert "Motivo" not in content
    assert "confidencial" not in content


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"motivo": ""}, "Indica el motivo del cambio."),
        ({"motivo": "   "}, "Indica el motivo del cambio."),
        ({"motivo": "x" * 501}, "Máximo 500 caracteres."),
        ({"prioridad": ""}, "Selecciona una prioridad."),
        ({"prioridad": 999999}, "Selecciona una prioridad."),
        ({"prioridad": "abc"}, "Ingresa un número entero."),
        ({"version": ""}, "No se pudo comprobar la versión del ticket."),
    ],
)
def test_invalid_priority_changes_are_rejected(
    client,
    app,
    catalog,
    staff,
    public_id,
    overrides,
    message,
):
    login(client, staff)
    before = state(app, public_id)

    response = client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog, **overrides),
    )

    assert response.status_code == 200
    assert message in text(response)
    assert state(app, public_id) == before


def test_the_same_priority_changes_nothing(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    login(client, staff)
    before = state(app, public_id)

    response = client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog, prioridad=catalog["medium"]),
        follow_redirects=True,
    )

    assert "El ticket ya tiene esa prioridad." in text(response)
    assert state(app, public_id) == before


def test_an_inactive_priority_cannot_be_chosen(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    with app.app_context():
        db.session.get(Prioridad, catalog["high"]).activo = False
        db.session.commit()

    login(client, staff)
    before = state(app, public_id)

    response = client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog),
    )

    assert "Selecciona una prioridad." in text(response)
    assert state(app, public_id) == before


def test_the_priority_form_keeps_the_reason_after_an_error(
    client,
    catalog,
    staff,
    public_id,
):
    login(client, staff)

    response = client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog, prioridad="", motivo="Mi motivo"),
    )

    assert "Mi motivo</textarea>" in response.get_data(as_text=True)


def test_a_priority_change_that_lost_the_race_is_rejected(
    client,
    app,
    catalog,
    staff,
    make_user,
    public_id,
):
    other = make_user("SUPERVISOR", username="otro_sup")
    login(client, staff)
    client.get(f"/tickets/{public_id}/priority")

    with app.app_context():
        ticket = db.session.scalar(
            db.select(Ticket).where(Ticket.public_id == public_id)
        )
        update_ticket(
            ticket,
            actor=db.session.get(User, other["id"]),
            expected_version=1,
            title="Cambio de B",
            description=ticket.descripcion,
            category_id=ticket.categoria_id,
            location_id=ticket.ubicacion_id,
        )
        db.session.commit()

    response = client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog),
    )

    assert response.status_code == 302
    assert response.location.endswith(f"/tickets/{public_id}/priority")
    assert state(app, public_id)["prioridad"] == catalog["medium"]

    assert "Otra persona modificó este ticket" in text(
        client.get(response.location)
    )


def test_the_priority_form_requires_the_csrf_token(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    login(client, staff)
    app.config["WTF_CSRF_ENABLED"] = True
    before = state(app, public_id)

    response = client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog),
    )

    assert response.status_code == 400
    assert state(app, public_id) == before


# --- Seguridad del contenido ------------------------------------------


def test_the_reason_and_changes_are_escaped(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    login(client, staff)
    client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(catalog, titulo="<b>negrita</b>"),
    )
    client.post(
        f"/tickets/{public_id}/priority",
        data=priority_data(catalog, motivo="<script>alert(1)</script>", version=2),
    )

    content = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content
    assert "<b>negrita</b>" not in content


def test_editing_keeps_the_location_catalog_untouched(
    client,
    app,
    catalog,
    staff,
    public_id,
):
    login(client, staff)

    client.post(
        f"/tickets/{public_id}/edit",
        data=edit_data(catalog, ubicacion=catalog["location"]),
    )

    with app.app_context():
        assert db.session.get(Ubicacion, catalog["location"]).activo is True
