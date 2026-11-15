"""Catálogo de motivos de espera (docs/09, 12.3; docs/06, RN-49 y RN-152).

Cubre el modelo y el seed, el servicio de administración, las pantallas del
Administrador y la referencia desde el historial de un ticket.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.workdesk.catalogs.service import (
    NothingToChangeError,
    activate_item,
    create_wait_reason,
    deactivate_item,
    deactivation_blocker,
    list_wait_reasons,
    update_wait_reason,
)
from src.workdesk.extensions import db
from src.workdesk.models import (
    AdminAuditLog,
    MotivoEspera,
    Ticket,
    TicketEvent,
    TicketHistory,
    User,
)
from src.workdesk.seeds import seed_catalogs
from src.workdesk.seeds.catalogs import INITIAL_WAIT_REASONS
from src.workdesk.tickets.service import record_ticket_event
from tests.ticket_helpers import login, make_ticket, text

NON_ADMIN_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR")


@pytest.fixture()
def admin_id(make_user, seeded_roles, seeded_catalogs):
    return make_user("ADMINISTRADOR", username="creador")["id"]


def by_code(code):
    return db.session.scalar(
        db.select(MotivoEspera).where(MotivoEspera.codigo == code)
    )


def audit_entries() -> list[AdminAuditLog]:
    return list(
        db.session.scalars(db.select(AdminAuditLog).order_by(AdminAuditLog.id))
    )


def names(items) -> list[str]:
    return [item.nombre for item in items]


# --- Datos iniciales ------------------------------------------------------


def test_seed_creates_the_base_wait_reasons_in_order(app):
    with app.app_context():
        seed_catalogs()

        reasons = list_wait_reasons()

        assert [r.codigo for r in reasons] == [
            "INFORMACION_PENDIENTE",
            "ESPERA_TERCERO",
            "APROBACION_PENDIENTE",
            "RECURSO_PENDIENTE",
            "OTRO",
        ]
        assert all(r.activo for r in reasons)


def test_only_the_generic_reason_allows_free_text(app):
    with app.app_context():
        seed_catalogs()

        allowing = [
            r.codigo for r in list_wait_reasons() if r.permite_texto_otro
        ]

        assert allowing == ["OTRO"]


def test_seed_wait_reasons_is_idempotent_and_keeps_administrator_changes(app):
    with app.app_context():
        assert seed_catalogs()["motivos_espera"] == len(INITIAL_WAIT_REASONS)

        reason = by_code("ESPERA_TERCERO")
        reason.nombre = "Proveedor externo"
        reason.activo = False
        db.session.commit()

        assert seed_catalogs()["motivos_espera"] == 0

        reason = by_code("ESPERA_TERCERO")

        assert reason.nombre == "Proveedor externo"
        assert reason.activo is False
        assert db.session.scalar(
            db.select(db.func.count(MotivoEspera.id))
        ) == len(INITIAL_WAIT_REASONS)


def test_seed_catalogs_command_reports_the_wait_reasons(app):
    result = app.test_cli_runner().invoke(args=["seed-catalogs"])

    assert result.exit_code == 0
    assert f"motivos de espera: {len(INITIAL_WAIT_REASONS)}" in result.output


# --- Restricciones de la base de datos ------------------------------------


def test_wait_reason_name_is_unique_ignoring_case(app):
    with app.app_context():
        db.session.add(MotivoEspera(nombre="Proveedor"))
        db.session.commit()

        db.session.add(MotivoEspera(nombre="PROVEEDOR"))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_wait_reason_code_is_optional_but_unique_when_present(app):
    with app.app_context():
        db.session.add_all(
            [MotivoEspera(nombre="Uno"), MotivoEspera(nombre="Dos")]
        )
        db.session.commit()

        db.session.add(MotivoEspera(codigo="X", nombre="Tres"))
        db.session.commit()

        db.session.add(MotivoEspera(codigo="X", nombre="Cuatro"))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_a_wait_reason_does_not_allow_free_text_by_default(app):
    with app.app_context():
        reason = MotivoEspera(nombre="Proveedor")
        db.session.add(reason)
        db.session.commit()
        db.session.refresh(reason)

        assert reason.permite_texto_otro is False
        assert reason.activo is True
        assert reason.orden is None


# --- Servicio -------------------------------------------------------------


def test_create_wait_reason_saves_the_data_the_creator_and_the_audit(
    app,
    admin_id,
):
    with app.app_context():
        actor = db.session.get(User, admin_id)

        reason = create_wait_reason(
            actor=actor,
            nombre="  Visita del proveedor  ",
            descripcion="  Debe ir a la sucursal  ",
            orden=7,
            permite_texto_otro=True,
        )
        db.session.commit()

        assert reason.nombre == "Visita del proveedor"
        assert reason.descripcion == "Debe ir a la sucursal"
        assert reason.orden == 7
        assert reason.permite_texto_otro is True
        assert reason.codigo is None
        assert reason.activo is True
        assert reason.usuario_creacion_id == admin_id

        entry = audit_entries()[-1]

        assert entry.accion == "CATALOGO_CREADO"
        assert entry.entidad_tipo == "motivo_espera"
        assert entry.entidad_id == reason.id
        assert entry.detalle == "Visita del proveedor"
        assert entry.valor_nuevo["permite_texto_otro"] is True


def test_create_wait_reason_rejects_a_repeated_name(app, admin_id):
    from src.workdesk.catalogs.service import DuplicateNameError

    with app.app_context():
        actor = db.session.get(User, admin_id)

        with pytest.raises(DuplicateNameError):
            create_wait_reason(actor=actor, nombre="información PENDIENTE")


def test_update_wait_reason_changes_only_what_was_modified(app, admin_id):
    with app.app_context():
        actor = db.session.get(User, admin_id)
        reason = by_code("OTRO")

        changed = update_wait_reason(
            reason,
            actor=actor,
            nombre="Otro motivo",
            descripcion=reason.descripcion,
            orden=reason.orden,
            permite_texto_otro=False,
        )
        db.session.commit()

        assert changed is True
        assert reason.permite_texto_otro is False

        entry = audit_entries()[-1]

        assert entry.accion == "CATALOGO_MODIFICADO"
        assert entry.valor_anterior == {"permite_texto_otro": True}
        assert entry.valor_nuevo == {"permite_texto_otro": False}


def test_update_wait_reason_without_changes_audits_nothing(app, admin_id):
    with app.app_context():
        actor = db.session.get(User, admin_id)
        reason = by_code("OTRO")
        before = len(audit_entries())

        changed = update_wait_reason(
            reason,
            actor=actor,
            nombre=reason.nombre,
            descripcion=reason.descripcion,
            orden=reason.orden,
            permite_texto_otro=reason.permite_texto_otro,
        )

        assert changed is False
        assert len(audit_entries()) == before


def test_no_wait_reason_is_protected_from_deactivation(app, admin_id):
    # El motivo es opcional (RN-49): no hace falta ninguno de respaldo, ni
    # siquiera la opción genérica.
    with app.app_context():
        actor = db.session.get(User, admin_id)

        for reason in list_wait_reasons():
            assert deactivation_blocker(reason) is None

        for reason in list_wait_reasons():
            deactivate_item(reason, actor=actor)

        db.session.commit()

        assert list_wait_reasons("activo") == []


def test_deactivate_and_activate_audit_the_wait_reason(app, admin_id):
    with app.app_context():
        actor = db.session.get(User, admin_id)
        reason = by_code("RECURSO_PENDIENTE")

        deactivate_item(reason, actor=actor, reason="Ya no se usa")
        db.session.commit()

        entry = audit_entries()[-1]

        assert reason.activo is False
        assert entry.accion == "CATALOGO_DESACTIVADO"
        assert entry.entidad_tipo == "motivo_espera"
        assert entry.motivo == "Ya no se usa"

        with pytest.raises(NothingToChangeError):
            deactivate_item(reason, actor=actor)

        activate_item(reason, actor=actor)
        db.session.commit()

        assert reason.activo is True
        assert audit_entries()[-1].accion == "CATALOGO_ACTIVADO"

        with pytest.raises(NothingToChangeError):
            activate_item(reason, actor=actor)


def test_wait_reasons_are_listed_by_order_then_name_and_can_be_filtered(
    app,
    admin_id,
):
    with app.app_context():
        actor = db.session.get(User, admin_id)

        create_wait_reason(actor=actor, nombre="zeta sin orden")
        create_wait_reason(actor=actor, nombre="Alfa sin orden")
        create_wait_reason(actor=actor, nombre="Primero", orden=0)
        db.session.commit()

        assert names(list_wait_reasons()) == [
            "Primero",
            "Información pendiente",
            "Espera de un tercero",
            "Aprobación pendiente",
            "Recurso pendiente",
            "Otro motivo",
            "Alfa sin orden",
            "zeta sin orden",
        ]

        deactivate_item(by_code("OTRO"), actor=actor)
        db.session.commit()

        assert "Otro motivo" not in names(list_wait_reasons("activo"))
        assert names(list_wait_reasons("inactivo")) == ["Otro motivo"]


# --- Referencia desde el historial ----------------------------------------


def _ticket_id(app, catalog, creator_id) -> int:
    public_id = make_ticket(app, catalog, creator_id)

    with app.app_context():
        return db.session.scalar(
            db.select(Ticket.id).where(Ticket.public_id == public_id)
        )


def test_a_history_event_can_reference_a_wait_reason(app, make_user, catalog):
    staff = make_user("TECNICO")
    ticket_id = _ticket_id(app, catalog, staff["id"])

    with app.app_context():
        reason = by_code("ESPERA_TERCERO")

        record_ticket_event(
            db.session.get(Ticket, ticket_id),
            TicketEvent.PRIORIDAD_CAMBIADA,
            actor=db.session.get(User, staff["id"]),
            wait_reason=reason,
        )
        db.session.commit()

        entry = db.session.scalars(
            db.select(TicketHistory).where(
                TicketHistory.ticket_id == ticket_id,
                TicketHistory.motivo_espera_id.is_not(None),
            )
        ).one()

        assert entry.motivo_espera_id == reason.id


def test_events_without_a_wait_reason_leave_it_empty(app, make_user, catalog):
    staff = make_user("TECNICO")
    ticket_id = _ticket_id(app, catalog, staff["id"])

    with app.app_context():
        entries = db.session.scalars(
            db.select(TicketHistory).where(TicketHistory.ticket_id == ticket_id)
        ).all()

        assert entries
        assert all(e.motivo_espera_id is None for e in entries)


def test_deactivating_a_wait_reason_does_not_affect_the_history(
    app,
    make_user,
    catalog,
):
    staff = make_user("TECNICO")
    ticket_id = _ticket_id(app, catalog, staff["id"])

    with app.app_context():
        actor = db.session.get(User, staff["id"])
        reason = by_code("INFORMACION_PENDIENTE")

        record_ticket_event(
            db.session.get(Ticket, ticket_id),
            TicketEvent.PRIORIDAD_CAMBIADA,
            actor=actor,
            wait_reason=reason,
        )
        db.session.commit()

        reason.activo = False
        db.session.commit()

        entry = db.session.scalars(
            db.select(TicketHistory).where(
                TicketHistory.motivo_espera_id == reason.id
            )
        ).one()

        assert entry.motivo_espera_id == reason.id


def test_a_wait_reason_in_use_cannot_be_deleted(app, make_user, catalog):
    staff = make_user("TECNICO")
    ticket_id = _ticket_id(app, catalog, staff["id"])

    with app.app_context():
        reason = by_code("OTRO")

        record_ticket_event(
            db.session.get(Ticket, ticket_id),
            TicketEvent.PRIORIDAD_CAMBIADA,
            actor=db.session.get(User, staff["id"]),
            wait_reason=reason,
        )
        db.session.commit()

        db.session.delete(reason)

        with pytest.raises(IntegrityError):
            db.session.commit()


# --- Pantallas del Administrador ------------------------------------------

ROUTES = (
    "/admin/wait-reasons",
    "/admin/wait-reasons/new",
    "/admin/wait-reasons/{id}/edit",
    "/admin/wait-reasons/{id}/deactivate",
    "/admin/wait-reasons/{id}/activate",
)


@pytest.fixture()
def reason_id(app, admin_id):
    with app.app_context():
        return by_code("ESPERA_TERCERO").id


def admin_session(client, make_user):
    admin = make_user("ADMINISTRADOR", username="admin_ui")
    login(client, admin)

    return admin


@pytest.mark.parametrize("route", ROUTES)
def test_anonymous_user_is_redirected_to_login(client, reason_id, route):
    response = client.get(route.format(id=reason_id))

    assert response.status_code == 302
    assert "/login" in response.location


# La lista solo admite GET; el resto acepta también POST.
POST_ROUTES = tuple(route for route in ROUTES if route != ROUTES[0])


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("role_code", NON_ADMIN_ROLES)
def test_non_admin_roles_are_forbidden_on_get(
    client,
    make_user,
    reason_id,
    role_code,
    route,
):
    login(client, make_user(role_code, username="otro"))

    assert client.get(route.format(id=reason_id)).status_code == 403


@pytest.mark.parametrize("route", POST_ROUTES)
@pytest.mark.parametrize("role_code", NON_ADMIN_ROLES)
def test_non_admin_roles_cannot_change_anything(
    client,
    app,
    make_user,
    reason_id,
    role_code,
    route,
):
    login(client, make_user(role_code, username="otro"))
    entries_before = len(_audit(app))

    response = client.post(
        route.format(id=reason_id),
        data={"nombre": "Intruso"},
    )

    assert response.status_code == 403

    assert len(_audit(app)) == entries_before

    with app.app_context():
        assert db.session.scalar(
            db.select(MotivoEspera).where(MotivoEspera.nombre == "Intruso")
        ) is None


def _audit(app):
    with app.app_context():
        return audit_entries()


@pytest.mark.parametrize(
    "route",
    [route for route in ROUTES if not route.endswith("/activate")],
)
def test_administrator_can_open_every_screen(
    client,
    make_user,
    reason_id,
    route,
):
    admin_session(client, make_user)

    assert client.get(route.format(id=reason_id)).status_code == 200


def test_administrator_can_open_the_reactivation_of_an_inactive_reason(
    client,
    app,
    make_user,
    admin_id,
    reason_id,
):
    admin_session(client, make_user)

    with app.app_context():
        deactivate_item(
            db.session.get(MotivoEspera, reason_id),
            actor=db.session.get(User, admin_id),
        )
        db.session.commit()

    response = client.get(f"/admin/wait-reasons/{reason_id}/activate")

    assert response.status_code == 200
    assert "Reactivar motivo de espera" in text(response)


@pytest.mark.parametrize("action", ["edit", "deactivate", "activate"])
def test_unknown_ids_return_404(client, make_user, reason_id, action):
    admin_session(client, make_user)

    assert client.get(f"/admin/wait-reasons/99999/{action}").status_code == 404


def test_post_without_csrf_token_is_rejected(
    client,
    app,
    make_user,
    reason_id,
):
    admin_session(client, make_user)
    app.config["WTF_CSRF_ENABLED"] = True

    assert (
        client.post("/admin/wait-reasons/new", data={"nombre": "X"})
    ).status_code == 400


def test_the_hub_links_to_the_wait_reasons(client, make_user, reason_id):
    admin_session(client, make_user)

    content = client.get("/admin").get_data(as_text=True)

    assert 'href="/admin/wait-reasons"' in content


def test_the_list_shows_every_reason_with_its_free_text_flag(
    client,
    make_user,
    reason_id,
):
    admin_session(client, make_user)

    content = text(client.get("/admin/wait-reasons"))

    assert "Motivos de espera" in content
    assert "Información pendiente" in content
    assert "Otro motivo" in content
    assert "Texto libre" in content
    assert "Nuevo motivo de espera" in content
    # Ninguno está protegido: todos ofrecen Desactivar.
    assert "Protegida" not in content
    assert content.count("Desactivar") == len(INITIAL_WAIT_REASONS)


def test_the_list_can_be_filtered_by_status(client, app, make_user, admin_id):
    admin_session(client, make_user)

    with app.app_context():
        deactivate_item(by_code("OTRO"), actor=db.session.get(User, admin_id))
        db.session.commit()

    active = text(client.get("/admin/wait-reasons?estado=activo"))
    inactive = text(client.get("/admin/wait-reasons?estado=inactivo"))

    assert "Otro motivo" not in active
    assert "Información pendiente" in active
    assert "Otro motivo" in inactive
    assert "Información pendiente" not in inactive
    assert "Reactivar" in inactive


def test_names_are_escaped_in_the_list(client, app, make_user, admin_id):
    admin_session(client, make_user)

    with app.app_context():
        create_wait_reason(
            actor=db.session.get(User, admin_id),
            nombre="<script>alert(1)</script>",
        )
        db.session.commit()

    content = client.get("/admin/wait-reasons").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content


def test_create_wait_reason_with_the_free_text_option(
    client,
    app,
    make_user,
    reason_id,
):
    admin = admin_session(client, make_user)

    response = client.post(
        "/admin/wait-reasons/new",
        data={
            "nombre": "Visita técnica",
            "descripcion": "Esperando al proveedor",
            "orden": "9",
            "permite_texto_otro": "y",
        },
        follow_redirects=True,
    )

    assert "El motivo de espera «Visita técnica» fue creado." in text(response)

    with app.app_context():
        reason = db.session.scalar(
            db.select(MotivoEspera).where(MotivoEspera.nombre == "Visita técnica")
        )

        assert reason.permite_texto_otro is True
        assert reason.orden == 9
        assert reason.descripcion == "Esperando al proveedor"
        assert reason.usuario_creacion_id == admin["id"]
        assert audit_entries()[-1].accion == "CATALOGO_CREADO"


def test_an_unchecked_box_means_no_free_text(client, app, make_user, reason_id):
    admin_session(client, make_user)

    client.post("/admin/wait-reasons/new", data={"nombre": "Sin texto"})

    with app.app_context():
        reason = db.session.scalar(
            db.select(MotivoEspera).where(MotivoEspera.nombre == "Sin texto")
        )

        assert reason.permite_texto_otro is False
        assert reason.orden is None


def test_create_requires_a_name_and_rejects_repeated_names(
    client,
    make_user,
    reason_id,
):
    admin_session(client, make_user)

    missing = client.post("/admin/wait-reasons/new", data={"nombre": " "})
    repeated = client.post(
        "/admin/wait-reasons/new",
        data={"nombre": "información pendiente"},
    )

    assert "Ingresa el nombre." in text(missing)
    assert "Ya existe un motivo de espera con ese nombre." in text(repeated)


def test_create_rejects_an_invalid_order_and_overlong_values(
    client,
    make_user,
    reason_id,
):
    admin_session(client, make_user)

    bad_order = client.post(
        "/admin/wait-reasons/new",
        data={"nombre": "Uno", "orden": "abc"},
    )
    too_big = client.post(
        "/admin/wait-reasons/new",
        data={"nombre": "Dos", "orden": "10000"},
    )
    long_name = client.post(
        "/admin/wait-reasons/new",
        data={"nombre": "x" * 101},
    )

    assert "Ingresa un número entero." in text(bad_order)
    assert "Usa un número entre 0 y 9999." in text(too_big)
    assert "Máximo 100 caracteres." in text(long_name)


def test_edit_form_is_prefilled_and_shows_the_checkbox_state(
    client,
    app,
    make_user,
    reason_id,
):
    admin_session(client, make_user)

    with app.app_context():
        generic_id = by_code("OTRO").id

    other = client.get(f"/admin/wait-reasons/{generic_id}/edit")
    third_party = client.get(f"/admin/wait-reasons/{reason_id}/edit")

    assert 'value="Otro motivo"' in other.get_data(as_text=True)
    assert "checked" in other.get_data(as_text=True)
    assert "checked" not in third_party.get_data(as_text=True)


def test_edit_saves_the_changes_including_unchecking_the_box(
    client,
    app,
    make_user,
    reason_id,
):
    admin_session(client, make_user)

    with app.app_context():
        generic_id = by_code("OTRO").id

    response = client.post(
        f"/admin/wait-reasons/{generic_id}/edit",
        data={"nombre": "Otra causa", "descripcion": "", "orden": "5"},
        follow_redirects=True,
    )

    assert "El motivo de espera «Otra causa» se actualizó." in text(response)

    with app.app_context():
        reason = db.session.get(MotivoEspera, generic_id)

        assert reason.nombre == "Otra causa"
        assert reason.permite_texto_otro is False
        assert reason.descripcion is None
        assert reason.codigo == "OTRO"

        entry = audit_entries()[-1]

        assert entry.accion == "CATALOGO_MODIFICADO"
        assert entry.valor_anterior["permite_texto_otro"] is True


def test_edit_without_changes_only_warns(client, app, make_user, reason_id):
    admin_session(client, make_user)

    with app.app_context():
        reason = db.session.get(MotivoEspera, reason_id)
        data = {
            "nombre": reason.nombre,
            "descripcion": reason.descripcion,
            "orden": str(reason.orden),
        }
        before = len(audit_entries())

    response = client.post(
        f"/admin/wait-reasons/{reason_id}/edit",
        data=data,
        follow_redirects=True,
    )

    assert "No había cambios que guardar." in text(response)

    with app.app_context():
        assert len(audit_entries()) == before


def test_edit_rejects_the_name_of_another_reason(
    client,
    make_user,
    reason_id,
):
    admin_session(client, make_user)

    response = client.post(
        f"/admin/wait-reasons/{reason_id}/edit",
        data={"nombre": "Otro motivo"},
    )

    assert "Ya existe un motivo de espera con ese nombre." in text(response)


def test_deactivate_and_reactivate_with_a_reason(
    client,
    app,
    make_user,
    reason_id,
):
    admin_session(client, make_user)

    confirmation = client.get(f"/admin/wait-reasons/{reason_id}/deactivate")

    assert "Desactivar motivo de espera" in text(confirmation)

    deactivated = client.post(
        f"/admin/wait-reasons/{reason_id}/deactivate",
        data={"motivo": "Ya no se usa"},
        follow_redirects=True,
    )

    assert "fue desactivado." in text(deactivated)

    with app.app_context():
        assert db.session.get(MotivoEspera, reason_id).activo is False
        assert audit_entries()[-1].motivo == "Ya no se usa"

    again = client.post(
        f"/admin/wait-reasons/{reason_id}/deactivate",
        follow_redirects=True,
    )

    assert "Este elemento ya está desactivado." in text(again)

    reactivated = client.post(
        f"/admin/wait-reasons/{reason_id}/activate",
        follow_redirects=True,
    )

    assert "fue reactivado." in text(reactivated)

    with app.app_context():
        assert db.session.get(MotivoEspera, reason_id).activo is True
