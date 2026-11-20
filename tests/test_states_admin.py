"""Administración de los estados y las transiciones del flujo (docs/04,
RF-118; docs/06, RN-164; docs/11, UI-021).

El Administrador puede renombrar los seis estados y habilitar o deshabilitar
transiciones ya definidas. Lo que no puede es romper el flujo: las transiciones
esenciales y las que dejarían un estado sin entrada o sin salida están
protegidas.
"""

import threading

import pytest

from src.workdesk.catalogs.flow import (
    MAX_STATE_DESCRIPTION_LENGTH,
    MAX_STATE_NAME_LENGTH,
    BrokenFlowError,
    EssentialTransitionError,
    activate_transition,
    count_tickets_by_state,
    deactivate_transition,
    describe_transition,
    group_by_origin,
    list_states,
    list_transitions,
    performed_by,
    transition_blocker,
    update_state,
)
from src.workdesk.catalogs.service import (
    CatalogRuleError,
    DuplicateNameError,
    NothingToChangeError,
)
from src.workdesk.extensions import db
from src.workdesk.models import (
    AdminAuditLog,
    Estado,
    StateAction,
    TransicionEstado,
)
from src.workdesk.models.transicion_estado import STATE_ACTION_LABELS
from src.workdesk.tickets.lifecycle import available_actions, change_state
from src.workdesk.tickets.state_actions import ESSENTIAL_ACTIONS
from tests.ticket_helpers import login, make_ticket, person, plain_text, text

# --- Auxiliares -------------------------------------------------------------


def state(code) -> Estado:
    return db.session.scalar(db.select(Estado).where(Estado.codigo == code))


def transition(origin, action, destination=None) -> TransicionEstado:
    statement = (
        db.select(TransicionEstado)
        .join(Estado, Estado.id == TransicionEstado.estado_origen_id)
        .where(Estado.codigo == origin, TransicionEstado.accion == action)
    )

    if destination is not None:
        statement = statement.where(
            TransicionEstado.estado_destino_id == state(destination).id
        )

    return db.session.scalar(statement)


def audit(action) -> list[AdminAuditLog]:
    return list(
        db.session.scalars(
            db.select(AdminAuditLog)
            .where(AdminAuditLog.accion == action)
            .order_by(AdminAuditLog.id)
        )
    )


def rename(code, name, *, actor_id, description=None):
    changed = update_state(
        state(code),
        actor=person(actor_id),
        nombre_visible=name,
        descripcion=description,
    )
    db.session.commit()

    return changed


def disable(origin, action, *, actor_id, destination=None, reason=None):
    deactivate_transition(
        transition(origin, action, destination),
        actor=person(actor_id),
        reason=reason,
    )
    db.session.commit()


@pytest.fixture()
def admin(make_user, catalog):
    return make_user("ADMINISTRADOR", username="admin")


@pytest.fixture()
def tech(make_user, catalog):
    return make_user("TECNICO", username="tecnico")


# --- Estados: consultas --------------------------------------------------------


def test_the_six_states_come_in_flow_order(app, catalog):
    with app.app_context():
        assert [s.codigo for s in list_states()] == [
            "NUEVO",
            "ASIGNADO",
            "EN_PROGRESO",
            "EN_ESPERA",
            "RESUELTO",
            "CERRADO",
        ]


def test_tickets_are_counted_by_state(app, catalog, tech):
    make_ticket(app, catalog, tech["id"], title="Uno")
    make_ticket(app, catalog, tech["id"], title="Dos")

    with app.app_context():
        counts = count_tickets_by_state()

        assert counts == {state("NUEVO").id: 2}
        # Un estado sin tickets no figura: la pantalla muestra 0.
        assert counts.get(state("CERRADO").id, 0) == 0


# --- Estados: editar --------------------------------------------------------------


def test_renaming_a_state_changes_only_what_is_visible(app, admin):
    with app.app_context():
        original_id = state("NUEVO").id

        assert rename("NUEVO", "  Recién llegado  ", actor_id=admin["id"],
                      description="  Aún sin revisar.  ") is True

        renamed = state("NUEVO")

        assert renamed.id == original_id
        assert renamed.codigo == "NUEVO"
        assert renamed.nombre_visible == "Recién llegado"
        assert renamed.descripcion == "Aún sin revisar."
        # El orden y el color son parte del diseño del flujo: no se tocan.
        assert renamed.orden == 1


def test_renaming_audits_only_the_fields_that_changed(app, admin):
    with app.app_context():
        # Solo cambia la descripción: el nombre queda igual.
        rename("EN_PROGRESO", "En progreso", actor_id=admin["id"],
               description="Se está trabajando.")
        (event,) = audit("ESTADO_MODIFICADO")

        assert event.entidad_tipo == "estado"
        assert event.entidad_id == state("EN_PROGRESO").id
        assert event.detalle == "EN_PROGRESO"
        assert event.actor_usuario_id == admin["id"]
        assert event.valor_nuevo == {"descripcion": "Se está trabajando."}
        assert event.valor_anterior["descripcion"] is not None


def test_saving_without_changes_does_not_audit(app, admin):
    with app.app_context():
        current = state("RESUELTO")

        assert rename(
            "RESUELTO",
            current.nombre_visible,
            actor_id=admin["id"],
            description=current.descripcion,
        ) is False
        assert audit("ESTADO_MODIFICADO") == []


def test_a_blank_description_becomes_none(app, admin):
    with app.app_context():
        rename("CERRADO", "Cerrado", actor_id=admin["id"], description="   ")

        assert state("CERRADO").descripcion is None


def test_a_state_name_cannot_repeat_ignoring_case(app, admin):
    with app.app_context():
        for taken in ("Cerrado", "CERRADO", "  cerrado "):
            with pytest.raises(DuplicateNameError, match="otro estado"):
                rename("NUEVO", taken, actor_id=admin["id"])

            db.session.rollback()

        assert state("NUEVO").nombre_visible == "Nuevo"


def test_a_state_may_keep_its_own_name_with_other_capitalization(app, admin):
    with app.app_context():
        assert rename("NUEVO", "NUEVO", actor_id=admin["id"]) is True
        assert state("NUEVO").nombre_visible == "NUEVO"


@pytest.mark.parametrize(
    ("name", "description", "message"),
    [
        ("", None, "obligatorio"),
        ("   ", None, "obligatorio"),
        ("x" * (MAX_STATE_NAME_LENGTH + 1), None, "no puede superar"),
        ("Nombre válido", "x" * (MAX_STATE_DESCRIPTION_LENGTH + 1), "no puede superar"),
    ],
)
def test_state_data_is_validated(app, admin, name, description, message):
    with app.app_context(), pytest.raises(CatalogRuleError, match=message):
        update_state(
            state("NUEVO"),
            actor=person(admin["id"]),
            nombre_visible=name,
            descripcion=description,
        )


def test_the_limits_are_accepted_exactly(app, admin):
    with app.app_context():
        rename(
            "NUEVO",
            "x" * MAX_STATE_NAME_LENGTH,
            actor_id=admin["id"],
            description="y" * MAX_STATE_DESCRIPTION_LENGTH,
        )

        assert len(state("NUEVO").nombre_visible) == MAX_STATE_NAME_LENGTH


def test_updating_a_state_does_not_commit(app, admin):
    with app.app_context():
        update_state(
            state("NUEVO"),
            actor=person(admin["id"]),
            nombre_visible="Otro",
            descripcion=None,
        )
        db.session.rollback()

        assert state("NUEVO").nombre_visible == "Nuevo"
        assert audit("ESTADO_MODIFICADO") == []


def test_two_administrators_renaming_to_the_same_name_at_once_leave_one(
    app,
    make_user,
    admin,
):
    """Las seis filas se bloquean mientras se comprueba el nombre: dos
    renombrados a la vez al mismo nombre no pueden dejar dos estados iguales."""
    other = make_user("ADMINISTRADOR", username="otro_admin")
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(code, user_id):
        with app.app_context():
            actor = person(user_id)
            target = state(code)
            barrier.wait(timeout=10)

            try:
                update_state(
                    target,
                    actor=actor,
                    nombre_visible="Mismo nombre",
                    descripcion=None,
                )
                db.session.commit()
                outcomes.append("ok")
            except DuplicateNameError:
                db.session.rollback()
                outcomes.append("duplicado")
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=("NUEVO", admin["id"])),
        threading.Thread(target=attempt, args=("ASIGNADO", other["id"])),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["duplicado", "ok"]

    with app.app_context():
        names = [s.nombre_visible for s in list_states()]

        assert names.count("Mismo nombre") == 1


# --- Transiciones: consultas -------------------------------------------------------


def test_the_transitions_come_grouped_by_origin_in_flow_order(app, catalog):
    with app.app_context():
        groups = group_by_origin(list_transitions())

        assert [g.origin.codigo for g in groups] == [
            "NUEVO",
            "ASIGNADO",
            "EN_PROGRESO",
            "EN_ESPERA",
            "RESUELTO",
            "CERRADO",
        ]
        assert sum(len(g.rows) for g in groups) == 20
        assert all(
            row.transition.estado_origen_id == g.origin.id
            for g in groups
            for row in g.rows
        )


def test_the_essential_transitions_and_the_only_entry_to_waiting_are_protected(
    app,
    catalog,
):
    with app.app_context():
        rows = list_transitions()
        protected = [row for row in rows if row.blocker]
        essential = [row for row in rows if row.essential_reason]

        assert {row.transition.accion for row in essential} == {
            action.value for action in ESSENTIAL_ACTIONS
        }
        # Ocho filas esenciales (reabrir tiene dos) y, además, la única entrada
        # a «En espera»: si se deshabilitara, ese estado dejaría de ser
        # alcanzable.
        assert len(essential) == 8
        assert {row.transition.accion for row in protected} - {
            row.transition.accion for row in essential
        } == {"PONER_EN_ESPERA"}
        assert len(protected) == 9


def test_the_optional_transitions_can_be_disabled(app, catalog):
    with app.app_context():
        free = {
            (row.transition.estado_origen.codigo, row.transition.accion)
            for row in list_transitions()
            if row.blocker is None
        }

        assert ("NUEVO", "RESOLVER") in free
        assert ("EN_PROGRESO", "CIERRE_DIRECTO") in free
        assert ("EN_ESPERA", "REACTIVAR") in free
        assert ("NUEVO", "INICIAR") in free
        assert len(free) == 11


def test_who_performs_each_action(app, catalog):
    with app.app_context():
        assert performed_by("INICIAR") == "Técnico, Supervisor y Administrador"
        assert performed_by("CIERRE_EXCEPCIONAL") == "Supervisor y Administrador"
        assert performed_by("CONFIRMAR") == "Solicitante (solo un solicitante del ticket)"
        assert performed_by("REABRIR").startswith(
            "Técnico, Supervisor, Administrador y Solicitante ("
        )
        assert performed_by("ASIGNAR").startswith("Automática:")
        assert performed_by("AUTO_CIERRE").startswith("El sistema")
        assert performed_by("NO_EXISTE") == "—"


def test_every_transition_has_a_readable_action_name(app, catalog):
    with app.app_context():
        for row in list_transitions():
            expected = STATE_ACTION_LABELS[StateAction(row.transition.accion)]

            assert row.transition.accion_nombre == expected


def test_listing_the_transitions_does_not_query_per_row(app, catalog):
    from sqlalchemy import event

    with app.app_context():
        statements = []

        def count(conn, cursor, statement, *args):
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", count)

        try:
            rows = list_transitions()

            # Todo lo que usa la pantalla está ya cargado.
            for row in rows:
                _ = (
                    row.transition.estado_origen.nombre_visible,
                    row.transition.estado_destino.nombre_visible,
                    row.transition.accion_nombre,
                    row.performed_by,
                    row.blocker,
                )
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

        assert len(rows) == 20
        # Estados, transiciones (con sus estados) y roles: pocas consultas, no
        # una por fila.
        assert len(statements) <= 4


# --- Transiciones: deshabilitar y habilitar --------------------------------------------


def test_disabling_an_optional_transition(app, admin):
    with app.app_context():
        disable("NUEVO", "RESOLVER", actor_id=admin["id"], reason="  No resolvemos de golpe.  ")

        disabled = transition("NUEVO", "RESOLVER")

        assert disabled.activa is False
        assert disabled.usuario_modificacion_id == admin["id"]
        assert disabled.fecha_modificacion is not None

        (event,) = audit("TRANSICION_DESACTIVADA")

        assert event.entidad_tipo == "transicion"
        assert event.entidad_id == disabled.id
        assert event.detalle == "Nuevo → Resuelto (Resolver)"
        assert event.valor_anterior == {"activa": True}
        assert event.valor_nuevo == {"activa": False}
        assert event.motivo == "No resolvemos de golpe."


def test_enabling_a_transition_again(app, admin):
    with app.app_context():
        disable("NUEVO", "RESOLVER", actor_id=admin["id"])
        activate_transition(
            transition("NUEVO", "RESOLVER"),
            actor=person(admin["id"]),
            reason="Volvemos al flujo anterior.",
        )
        db.session.commit()

        assert transition("NUEVO", "RESOLVER").activa is True

        (event,) = audit("TRANSICION_ACTIVADA")

        assert event.valor_nuevo == {"activa": True}
        assert event.motivo == "Volvemos al flujo anterior."


def test_toggling_to_the_same_state_is_reported(app, admin):
    with app.app_context():
        with pytest.raises(NothingToChangeError, match="ya está habilitada"):
            activate_transition(
                transition("NUEVO", "RESOLVER"), actor=person(admin["id"])
            )

        disable("NUEVO", "RESOLVER", actor_id=admin["id"])

        with pytest.raises(NothingToChangeError, match="ya está deshabilitada"):
            deactivate_transition(
                transition("NUEVO", "RESOLVER"), actor=person(admin["id"])
            )


@pytest.mark.parametrize("action", sorted(a.value for a in ESSENTIAL_ACTIONS))
def test_an_essential_transition_cannot_be_disabled(app, admin, action):
    with app.app_context():
        origins = db.session.scalars(
            db.select(Estado.codigo)
            .join(TransicionEstado, TransicionEstado.estado_origen_id == Estado.id)
            .where(TransicionEstado.accion == action)
        ).all()

        for origin in origins:
            target = transition(origin, action)

            with pytest.raises(EssentialTransitionError, match="es esencial"):
                deactivate_transition(target, actor=person(admin["id"]))

            db.session.rollback()
            assert db.session.get(TransicionEstado, target.id).activa is True

        assert audit("TRANSICION_DESACTIVADA") == []


def test_the_reason_an_action_is_essential_is_explained(app, admin):
    with app.app_context():
        blocker = transition_blocker(transition("RESUELTO", "CONFIRMAR"))

        assert "es esencial" in blocker
        assert "validación del solicitante" in blocker


def test_the_only_entry_to_a_state_cannot_be_disabled(app, admin):
    with app.app_context():
        with pytest.raises(BrokenFlowError) as error:
            deactivate_transition(
                transition("EN_PROGRESO", "PONER_EN_ESPERA"), actor=person(admin["id"])
            )

        assert "«En espera» dejaría de ser alcanzable desde «Nuevo»" in str(error.value)


def test_the_last_exit_of_a_state_cannot_be_disabled(app, admin):
    with app.app_context():
        disable("EN_ESPERA", "REACTIVAR", actor_id=admin["id"])
        disable("EN_ESPERA", "RESOLVER", actor_id=admin["id"])

        # Solo queda el cierre directo: es la última salida de «En espera».
        with pytest.raises(BrokenFlowError) as error:
            deactivate_transition(
                transition("EN_ESPERA", "CIERRE_DIRECTO"), actor=person(admin["id"])
            )

        assert "desde «En espera» ya no se podría llegar a «Cerrado»" in str(error.value)


def test_reaching_a_state_only_by_going_back_does_not_count(app, admin):
    """Con las dos formas de iniciar el trabajo deshabilitadas, un ticket solo
    llegaría a «En progreso» resolviéndolo y reabriéndolo: no es un flujo."""
    with app.app_context():
        disable("NUEVO", "INICIAR", actor_id=admin["id"])

        with pytest.raises(BrokenFlowError) as error:
            deactivate_transition(
                transition("ASIGNADO", "INICIAR"), actor=person(admin["id"])
            )

        assert "«En progreso» dejaría de ser alcanzable" in str(error.value)


def test_the_messages_use_the_current_state_names(app, admin):
    with app.app_context():
        rename("EN_ESPERA", "Pausado", actor_id=admin["id"])
        rename("NUEVO", "Recién llegado", actor_id=admin["id"])

        blocker = transition_blocker(transition("EN_PROGRESO", "PONER_EN_ESPERA"))

        assert "«Pausado» dejaría de ser alcanzable desde «Recién llegado»" in blocker
        assert describe_transition(transition("EN_PROGRESO", "PONER_EN_ESPERA")) == (
            "En progreso → Pausado (Poner en espera)"
        )


def test_a_flow_that_was_already_broken_does_not_block_unrelated_changes(
    app,
    admin,
):
    """Solo cuenta lo que empeora: si algo ya estaba roto (por ejemplo, editado
    en la base de datos), deshabilitar una transición que no tiene que ver no se
    bloquea."""
    with app.app_context():
        # Se rompe a propósito saltándose las protecciones.
        broken = transition("EN_PROGRESO", "PONER_EN_ESPERA")
        broken.activa = False
        db.session.commit()

        assert transition_blocker(transition("NUEVO", "RESOLVER")) is None


def test_two_administrators_cannot_break_the_flow_together(
    app,
    make_user,
    admin,
):
    """Cada una de estas dos deshabilitaciones es inofensiva por separado (la
    otra salida sigue activa), pero juntas dejarían «En espera» sin salidas:
    las filas se bloquean, así que el segundo ve el resultado del primero."""
    other = make_user("ADMINISTRADOR", username="otro_admin")

    with app.app_context():
        disable("EN_ESPERA", "REACTIVAR", actor_id=admin["id"])

    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(action, user_id):
        with app.app_context():
            actor = person(user_id)
            target = transition("EN_ESPERA", action)
            barrier.wait(timeout=10)

            try:
                deactivate_transition(target, actor=actor)
                db.session.commit()
                outcomes.append("ok")
            except BrokenFlowError:
                db.session.rollback()
                outcomes.append("roto")
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=("RESOLVER", admin["id"])),
        threading.Thread(target=attempt, args=("CIERRE_DIRECTO", other["id"])),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["ok", "roto"]

    with app.app_context():
        active = db.session.scalars(
            db.select(TransicionEstado)
            .join(Estado, Estado.id == TransicionEstado.estado_origen_id)
            .where(Estado.codigo == "EN_ESPERA", TransicionEstado.activa.is_(True))
        ).all()

        assert len(active) == 1


@pytest.mark.parametrize("enabling", [False, True], ids=["disable", "enable"])
def test_two_administrators_toggling_the_same_transition_do_it_once(
    app,
    make_user,
    admin,
    enabling,
):
    """Los dos abren la pantalla con la transición en el mismo estado. Con la
    fila bloqueada, el segundo ve que el primero ya la cambió: no la cambia de
    nuevo ni deja un segundo registro en la auditoría."""
    other = make_user("ADMINISTRADOR", username="otro_admin")

    if enabling:
        with app.app_context():
            disable("NUEVO", "RESOLVER", actor_id=admin["id"])

    operation = activate_transition if enabling else deactivate_transition
    barrier = threading.Barrier(2)
    outcomes = []

    def attempt(user_id):
        with app.app_context():
            actor = person(user_id)
            target = transition("NUEVO", "RESOLVER")
            barrier.wait(timeout=10)

            try:
                operation(target, actor=actor)
                db.session.commit()
                outcomes.append("ok")
            except NothingToChangeError:
                db.session.rollback()
                outcomes.append("ya estaba")
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=attempt, args=(admin["id"],)),
        threading.Thread(target=attempt, args=(other["id"],)),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["ok", "ya estaba"]

    with app.app_context():
        action = "TRANSICION_ACTIVADA" if enabling else "TRANSICION_DESACTIVADA"

        assert len(audit(action)) == 1
        assert transition("NUEVO", "RESOLVER").activa is enabling


def test_toggling_a_transition_does_not_commit(app, admin):
    with app.app_context():
        deactivate_transition(transition("NUEVO", "RESOLVER"), actor=person(admin["id"]))
        db.session.rollback()

        assert transition("NUEVO", "RESOLVER").activa is True
        assert audit("TRANSICION_DESACTIVADA") == []


# --- El motor respeta lo configurado ---------------------------------------------------


def test_a_disabled_transition_is_no_longer_offered_to_tickets(
    app,
    catalog,
    admin,
    tech,
):
    public_id = make_ticket(app, catalog, tech["id"])

    with app.app_context():
        from src.workdesk.models import Ticket

        ticket = db.session.scalar(db.select(Ticket).where(Ticket.public_id == public_id))
        before = {o.info.action for o in available_actions(ticket, person(tech["id"]))}

        disable("NUEVO", "RESOLVER", actor_id=admin["id"])

        after = {
            o.info.action
            for o in available_actions(
                db.session.get(Ticket, ticket.id), person(tech["id"])
            )
        }

        assert before - after == {StateAction.RESOLVER}


def test_a_disabled_transition_is_refused_by_the_state_change(
    app,
    catalog,
    admin,
    tech,
):
    from src.workdesk.models import Ticket
    from src.workdesk.tickets.lifecycle import StateTransitionError

    public_id = make_ticket(app, catalog, tech["id"])

    with app.app_context():
        disable("NUEVO", "RESOLVER", actor_id=admin["id"])
        ticket = db.session.scalar(db.select(Ticket).where(Ticket.public_id == public_id))

        with pytest.raises(StateTransitionError):
            change_state(
                ticket,
                actor=person(tech["id"]),
                action=StateAction.RESOLVER,
                expected_version=ticket.version,
            )


# --- Pantallas -------------------------------------------------------------------------


STATES_URL = "/admin/states"


def state_id(app, code):
    with app.app_context():
        return state(code).id


def transition_id(app, origin, action, destination=None):
    with app.app_context():
        return transition(origin, action, destination).id


@pytest.mark.parametrize("role", ["SOLICITANTE", "TECNICO", "SUPERVISOR"])
def test_only_the_administrator_can_use_the_screens(client, app, make_user, catalog, role):
    person_data = make_user(role, username="persona")
    login(client, person_data)
    nuevo = state_id(app, "NUEVO")
    resolver = transition_id(app, "NUEVO", "RESOLVER")

    assert client.get(STATES_URL).status_code == 403

    # Estas rutas también aceptan POST: el rol se comprueba antes que nada.
    for url in (
        f"{STATES_URL}/{nuevo}/edit",
        f"/admin/transitions/{resolver}/deactivate",
        f"/admin/transitions/{resolver}/activate",
    ):
        assert client.get(url).status_code == 403
        assert client.post(url, data={}).status_code == 403

    with app.app_context():
        assert state("NUEVO").nombre_visible == "Nuevo"
        assert transition("NUEVO", "RESOLVER").activa is True


def test_unknown_ids_are_a_404(client, admin):
    login(client, admin)

    for url in (
        f"{STATES_URL}/99999/edit",
        "/admin/transitions/99999/deactivate",
        "/admin/transitions/99999/activate",
    ):
        assert client.get(url).status_code == 404
        assert client.post(url, data={}).status_code == 404


def test_the_hub_links_the_screen(client, admin):
    login(client, admin)
    html = client.get("/admin").get_data(as_text=True)

    assert f'href="{STATES_URL}"' in html


def test_the_page_lists_the_states_and_the_transitions(client, app, catalog, admin, tech):
    make_ticket(app, catalog, tech["id"], title="Uno")
    login(client, admin)
    response = client.get(STATES_URL)
    page = plain_text(response)

    assert response.status_code == 200
    for name in ("Nuevo", "Asignado", "En progreso", "En espera", "Resuelto", "Cerrado"):
        assert name in page
    for code in ("NUEVO", "EN_PROGRESO", "CERRADO"):
        assert code in page
    # Acciones con su nombre neutro y quién las ejecuta.
    for label in ("Iniciar trabajo", "Confirmar la solución", "Cierre excepcional"):
        assert label in page
    assert "Técnico, Supervisor y Administrador" in page
    assert "Supervisor y Administrador" in page
    # Los nueve protegidos y los once que se pueden deshabilitar.
    html = response.get_data(as_text=True)

    assert html.count("/deactivate") == 11
    assert html.count("/activate") == 0
    assert html.count("Protegida") >= 9
    assert page.count("Habilitada") == 20


def test_a_protected_transition_explains_why(client, admin):
    login(client, admin)
    page = plain_text(client.get(STATES_URL))

    assert "es esencial y no se puede deshabilitar" in page
    assert "validación del solicitante" in page
    assert "dejaría de ser alcanzable" in page


def test_the_edit_screen_is_prefilled(client, app, admin):
    login(client, admin)
    nuevo = state_id(app, "NUEVO")
    response = client.get(f"{STATES_URL}/{nuevo}/edit")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'value="Nuevo"' in html
    assert "no cambia" in text(response)
    assert "El historial de cada ticket conserva el nombre" in text(response)


def test_renaming_through_the_screen(client, app, admin):
    login(client, admin)
    nuevo = state_id(app, "NUEVO")
    response = client.post(
        f"{STATES_URL}/{nuevo}/edit",
        data={"nombre_visible": "Recién llegado", "descripcion": "Aún sin revisar."},
        follow_redirects=True,
    )
    page = plain_text(response)

    assert "El estado «Recién llegado» se actualizó." in page
    assert "Recién llegado" in page

    with app.app_context():
        assert state("NUEVO").nombre_visible == "Recién llegado"
        assert len(audit("ESTADO_MODIFICADO")) == 1


def test_a_duplicate_name_is_shown_in_the_form(client, app, admin):
    login(client, admin)
    nuevo = state_id(app, "NUEVO")
    response = client.post(
        f"{STATES_URL}/{nuevo}/edit",
        data={"nombre_visible": "cerrado", "descripcion": ""},
    )

    assert response.status_code == 200
    assert "Ya hay otro estado con ese nombre." in text(response)
    assert 'value="cerrado"' in response.get_data(as_text=True)

    with app.app_context():
        assert state("NUEVO").nombre_visible == "Nuevo"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"nombre_visible": "", "descripcion": ""}, "Ingresa el nombre."),
        (
            {"nombre_visible": "x" * (MAX_STATE_NAME_LENGTH + 1), "descripcion": ""},
            f"Máximo {MAX_STATE_NAME_LENGTH} caracteres.",
        ),
        (
            {
                "nombre_visible": "Válido",
                "descripcion": "x" * (MAX_STATE_DESCRIPTION_LENGTH + 1),
            },
            f"Máximo {MAX_STATE_DESCRIPTION_LENGTH} caracteres.",
        ),
    ],
)
def test_the_form_validates_the_data(client, app, admin, data, message):
    login(client, admin)
    nuevo = state_id(app, "NUEVO")
    response = client.post(f"{STATES_URL}/{nuevo}/edit", data=data)

    assert message in text(response)

    with app.app_context():
        assert state("NUEVO").nombre_visible == "Nuevo"


def test_saving_without_changes_says_so(client, app, admin):
    login(client, admin)
    nuevo = state_id(app, "NUEVO")

    with app.app_context():
        current = state("NUEVO")
        data = {
            "nombre_visible": current.nombre_visible,
            "descripcion": current.descripcion or "",
        }

    response = client.post(
        f"{STATES_URL}/{nuevo}/edit", data=data, follow_redirects=True
    )

    assert "No había cambios que guardar." in plain_text(response)


def test_the_state_screen_does_not_accept_a_code_or_an_order(client, app, admin):
    login(client, admin)
    nuevo = state_id(app, "NUEVO")
    client.post(
        f"{STATES_URL}/{nuevo}/edit",
        data={
            "nombre_visible": "Otro nombre",
            "descripcion": "",
            "codigo": "HACKEADO",
            "orden": 99,
            "color": "#000000",
        },
    )

    with app.app_context():
        renamed = state("NUEVO")

        assert renamed.nombre_visible == "Otro nombre"
        assert renamed.codigo == "NUEVO"
        assert renamed.orden == 1
        assert renamed.color != "#000000"


def test_a_renamed_state_is_shown_everywhere_but_the_history_keeps_its_old_name(
    client,
    app,
    catalog,
    admin,
    tech,
):
    public_id = make_ticket(app, catalog, tech["id"])
    login(client, tech)
    client.post(
        f"/tickets/{public_id}/status/start",
        data={"version": 1},
    )
    client.post("/logout")

    with app.app_context():
        rename("EN_PROGRESO", "En curso", actor_id=admin["id"])

    login(client, tech)
    page = plain_text(client.get(f"/tickets/{public_id}"))

    # El estado actual usa el nombre nuevo; el evento del pasado, el que tenía.
    assert "En curso" in page
    assert "Estado: «Nuevo» → «En progreso»" in page


def test_the_confirmation_screens_use_the_current_state_names(
    client,
    app,
    catalog,
    admin,
    tech,
):
    public_id = make_ticket(app, catalog, tech["id"])

    with app.app_context():
        rename("EN_PROGRESO", "En curso", actor_id=admin["id"])

    login(client, tech)
    page = plain_text(client.get(f"/tickets/{public_id}/status/start"))

    assert "El ticket pasará a «En curso»." in page
    assert "En progreso" not in page


def test_the_description_is_the_help_of_the_state_badge(client, app, catalog, admin, tech):
    public_id = make_ticket(app, catalog, tech["id"])

    with app.app_context():
        rename("NUEVO", "Nuevo", actor_id=admin["id"], description="Recién creado.")

    login(client, tech)
    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert 'title="Recién creado."' in html


def test_the_deactivation_screen_explains_the_effect(client, app, admin):
    login(client, admin)
    resolver = transition_id(app, "NUEVO", "RESOLVER")
    response = client.get(f"/admin/transitions/{resolver}/deactivate")
    page = plain_text(response)

    assert response.status_code == 200
    assert "Deshabilitar transición" in page
    assert "Nuevo → Resuelto (Resolver)" in page
    assert "La acción «Resolver» dejará de ofrecerse a los tickets que estén en «Nuevo»" in page
    assert "Los tickets no cambian de estado" in page


def test_disabling_a_transition_through_the_screen(client, app, admin):
    login(client, admin)
    resolver = transition_id(app, "NUEVO", "RESOLVER")
    response = client.post(
        f"/admin/transitions/{resolver}/deactivate",
        data={"motivo": "No resolvemos sin pasar por trabajo."},
        follow_redirects=True,
    )
    page = plain_text(response)

    assert "La transición «Nuevo → Resuelto (Resolver)» fue deshabilitada." in page
    assert "Deshabilitada" in page
    assert f"/admin/transitions/{resolver}/activate" in response.get_data(as_text=True)

    with app.app_context():
        assert transition("NUEVO", "RESOLVER").activa is False
        assert audit("TRANSICION_DESACTIVADA")[0].motivo == "No resolvemos sin pasar por trabajo."


def test_enabling_a_transition_through_the_screen(client, app, admin):
    with app.app_context():
        disable("NUEVO", "RESOLVER", actor_id=admin["id"])

    login(client, admin)
    resolver = transition_id(app, "NUEVO", "RESOLVER")
    screen = client.get(f"/admin/transitions/{resolver}/activate")

    assert "Habilitar transición" in text(screen)
    assert "volverá a ofrecerse" in text(screen)

    response = client.post(
        f"/admin/transitions/{resolver}/activate", data={}, follow_redirects=True
    )

    assert "fue habilitada." in plain_text(response)

    with app.app_context():
        assert transition("NUEVO", "RESOLVER").activa is True


def test_a_protected_transition_cannot_be_disabled_through_the_screen(client, app, admin):
    login(client, admin)
    confirm = transition_id(app, "RESUELTO", "CONFIRMAR")

    for method in (client.get, client.post):
        response = method(
            f"/admin/transitions/{confirm}/deactivate", follow_redirects=True
        )

        assert "es esencial y no se puede deshabilitar" in plain_text(response)

    with app.app_context():
        assert transition("RESUELTO", "CONFIRMAR").activa is True
        assert audit("TRANSICION_DESACTIVADA") == []


def test_the_screen_refuses_to_break_the_flow(client, app, admin):
    login(client, admin)
    waiting = transition_id(app, "EN_PROGRESO", "PONER_EN_ESPERA")
    response = client.post(
        f"/admin/transitions/{waiting}/deactivate", follow_redirects=True
    )

    assert "«En espera» dejaría de ser alcanzable desde «Nuevo»" in plain_text(response)

    with app.app_context():
        assert transition("EN_PROGRESO", "PONER_EN_ESPERA").activa is True


def test_toggling_to_the_current_state_through_the_screen_is_reported(
    client,
    app,
    admin,
):
    login(client, admin)
    resolver = transition_id(app, "NUEVO", "RESOLVER")

    enabled = client.get(
        f"/admin/transitions/{resolver}/activate", follow_redirects=True
    )

    assert "Esta transición ya está habilitada." in plain_text(enabled)

    client.post(f"/admin/transitions/{resolver}/deactivate", data={})
    disabled = client.get(
        f"/admin/transitions/{resolver}/deactivate", follow_redirects=True
    )

    assert "Esta transición ya está deshabilitada." in plain_text(disabled)


def test_a_disabled_transition_disappears_from_the_ticket_screens(
    client,
    app,
    catalog,
    admin,
    tech,
):
    public_id = make_ticket(app, catalog, tech["id"])
    login(client, admin)
    resolver = transition_id(app, "NUEVO", "RESOLVER")
    client.post(f"/admin/transitions/{resolver}/deactivate", data={})
    client.post("/logout")

    login(client, tech)
    detail = client.get(f"/tickets/{public_id}").get_data(as_text=True)

    assert f"/tickets/{public_id}/status/resolve" not in detail
    assert f"/tickets/{public_id}/status/start" in detail

    response = client.get(
        f"/tickets/{public_id}/status/resolve", follow_redirects=True
    )

    assert "Esta acción no está disponible para el estado actual del ticket." in plain_text(
        response
    )


def test_the_screens_belong_to_the_administration_menu(client, app, admin):
    login(client, admin)
    nuevo = state_id(app, "NUEVO")

    for url in (STATES_URL, f"{STATES_URL}/{nuevo}/edit"):
        html = client.get(url).get_data(as_text=True)

        assert 'aria-current="page"' in html
