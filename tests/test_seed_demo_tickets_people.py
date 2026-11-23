"""Solicitantes agregados y retirados, comentarios, notas internas y adjuntos."""

import hashlib
import re
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import (
    Attachment,
    TicketEvent,
)
from src.workdesk.seeds import (
    DemoTicketsError,
    seed_demo_tickets,
)
from src.workdesk.seeds.demo_tickets import validate_demo_tickets
from src.workdesk.seeds.demo_tickets_data import (
    DEMO_TICKETS,
    DemoAdjustment,
)
from src.workdesk.tickets.attachments import attachment_path
from tests.demo_data import NOW, ROLES
from tests.seed_helpers import (
    attachments_of,
    by_clave,
    comments_of,
    content_snapshot,
    date_snapshot,
    events_of,
    history_of,
    initial_requesters,
    log_in,
    page_text,
    requesters_of,
    user,
)

# --- Solicitantes agregados y retirados ------------------------------------




def link_for(ticket, username):
    return next(
        link for link in requesters_of(ticket) if link.solicitante.username == username
    )


@pytest.mark.parametrize(
    ("adjustment", "message"),
    [
        # `excel-bloqueado` (el primero) lo crea Javiera, que es su solicitante.
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        agregar_solicitante="felipe.araya"),
         "no es un Solicitante demo"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="felipe.araya"),
         "no es un Solicitante demo"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="andres.silva"),
         "no es solicitante en ese momento"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        agregar_solicitante="javiera.torres"),
         "ya es solicitante en ese momento"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="javiera.torres",
                        agregar_solicitante="javiera.torres"),
         "retirar y agregar a la misma persona"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        agregar_solicitante="andres.silva",
                        motivo_retiro="Sin sentido"),
         "motivo_retiro solo va con retirar_solicitante"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="javiera.torres",
                        motivo_retiro="x" * 501),
         "motivo de retiro supera los 500"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1,
                        retirar_solicitante="javiera.torres",
                        motivo_retiro=" con espacios "),
         "motivo de retiro está vacío o tiene espacios"),
        (DemoAdjustment(actor="paula.contreras", despues_horas=1,
                        agregar_solicitante="andres.silva"),
         "no es personal"),
    ],
)
def test_validation_rejects_inconsistent_requester_steps(adjustment, message):
    ticket = replace(DEMO_TICKETS[0], ajustes=(adjustment,))

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((ticket,))


def test_validation_follows_the_requesters_step_by_step():
    # Retirar a alguien y volver a agregarlo más tarde es válido...
    steps = (
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       retirar_solicitante="javiera.torres"),
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       agregar_solicitante="javiera.torres"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=steps),))

    # ...y cambiar a una persona por otra en un mismo paso también.
    swap = (
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       retirar_solicitante="javiera.torres",
                       agregar_solicitante="andres.silva"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=swap),))

    # Pero no agregar dos veces a la misma persona.
    twice = (
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       agregar_solicitante="andres.silva"),
        DemoAdjustment(actor="diego.soto", despues_horas=1,
                       agregar_solicitante="andres.silva"),
    )

    with pytest.raises(DemoTicketsError, match="ya es solicitante en ese momento"):
        validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=twice),))


def test_demo_data_covers_the_requester_changes():
    steps = [(demo, step) for demo in DEMO_TICKETS for step in demo.ajustes]

    # Cambiar a una persona por otra en un mismo paso.
    assert any(
        step.retirar_solicitante and step.agregar_solicitante for _, step in steps
    )
    # Agregar a quien nace en un ticket sin solicitantes (RN-12).
    assert any(
        step.agregar_solicitante and not initial_requesters(demo)
        for demo, step in steps
    )
    # Agregar a alguien y retirarlo en un paso posterior.
    def adds_then_retires(demo):
        added = set()

        for step in demo.ajustes:
            if step.retirar_solicitante in added:
                return True

            if step.agregar_solicitante is not None:
                added.add(step.agregar_solicitante)

        return False

    assert any(adds_then_retires(demo) for demo in DEMO_TICKETS)
    # Retirar a quien creó el ticket (que lo sigue viendo).
    assert any(
        step.retirar_solicitante == demo.creado_por for demo, step in steps
    )


def test_a_wrongly_associated_requester_is_replaced(app, seeded):
    with app.app_context():
        ticket = by_clave("proyector-sala-chica")
        removed = link_for(ticket, "constanza.herrera")
        added = link_for(ticket, "paula.contreras")
        felipe = user("felipe.araya")

        assert [r.solicitante.username for r in ticket.solicitantes_vigentes] == [
            "paula.contreras"
        ]
        assert removed.fecha_retiro is not None
        assert removed.retirado_por_usuario_id == felipe.id
        assert added.asociado_por_usuario_id == felipe.id

        # Primero se retira y después se agrega, con la marca de su paso.
        kinds = [e.tipo_evento for e in history_of(ticket)]

        assert kinds == ["TICKET_CREADO", "SOLICITANTE_RETIRADO", "SOLICITANTE_AGREGADO"]
        assert all(e.contexto["demo_clave"] == "proyector-sala-chica" for e in history_of(ticket))

        retired_event, added_event = history_of(ticket)[1:]

        assert retired_event.visibilidad == "INTERNO"
        assert retired_event.contexto["motivo"].startswith("Constanza solo avisó")
        assert retired_event.contexto["participacion_id"] == removed.id
        assert added_event.contexto["participacion_id"] == added.id
        # No se tocó la versión ni la fecha de modificación (como en la
        # aplicación: los solicitantes no modifican el ticket).
        assert ticket.version == 1
        assert ticket.fecha_modificacion is None
        assert ticket.estado.codigo == "NUEVO"


def test_a_requester_can_be_added_to_a_ticket_that_started_without_any(app, seeded):
    with app.app_context():
        ticket = by_clave("ups-bodega-mantencion")
        (link,) = requesters_of(ticket)
        (event,) = events_of(ticket, TicketEvent.SOLICITANTE_AGREGADO)
        created = history_of(ticket)[0]

        assert link.solicitante.username == "ignacio.molina"
        assert link.asociado_por_usuario_id == user("valentina.pizarro").id
        # Se asocia en el momento de su evento, después de crear el ticket.
        assert link.fecha_asociacion == event.fecha_hora
        assert link.fecha_asociacion > created.fecha_hora
        assert ticket.fecha_actualizacion == ticket.fecha_creacion


def test_a_requester_added_and_retired_later_keeps_both_dates(app, seeded):
    with app.app_context():
        ticket = by_clave("vpn-se-corta")
        original = link_for(ticket, "sebastian.vargas")
        guest = link_for(ticket, "andres.silva")
        (added,) = events_of(ticket, TicketEvent.SOLICITANTE_AGREGADO)
        (retired,) = events_of(ticket, TicketEvent.SOLICITANTE_RETIRADO)

        assert original.fecha_retiro is None
        assert original.fecha_asociacion == ticket.fecha_creacion
        assert guest.fecha_asociacion == added.fecha_hora
        assert guest.fecha_retiro == retired.fecha_hora
        assert guest.fecha_retiro > guest.fecha_asociacion
        assert retired.contexto["motivo"] == "Su problema era otro y se atendió por separado."
        assert [e.tipo_evento for e in history_of(ticket)] == [
            "TICKET_CREADO",
            "SOLICITANTE_AGREGADO",
            "SOLICITANTE_RETIRADO",
        ]


def test_the_creator_keeps_seeing_the_ticket_after_being_retired(app, seeded):
    with app.app_context():
        ticket = by_clave("impresora-proyectos-a-nombre-de")
        public_id = ticket.public_id

        assert link_for(ticket, "constanza.herrera").fecha_retiro is not None
        assert [r.solicitante.username for r in ticket.solicitantes_vigentes] == [
            "andres.silva"
        ]

    # Constanza sigue viéndolo porque lo creó; Andrés porque es el solicitante.
    for username in ("constanza.herrera", "andres.silva"):
        client = log_in(app, username)

        assert client.get(f"/tickets/{public_id}").status_code == 200, username
        assert f'href="/tickets/{public_id}"' in client.get(
            "/tickets?vista=todos"
        ).get_data(as_text=True), username

    # Quien no tiene relación con el ticket, no.
    assert log_in(app, "paula.contreras").get(f"/tickets/{public_id}").status_code == 404


def test_a_retired_requester_who_did_not_create_the_ticket_loses_access(app, seeded):
    with app.app_context():
        public_id = by_clave("proyector-sala-chica").public_id

    assert log_in(app, "constanza.herrera").get(f"/tickets/{public_id}").status_code == 404
    assert log_in(app, "paula.contreras").get(f"/tickets/{public_id}").status_code == 200


def test_the_requester_events_are_only_for_staff_in_the_demo(app, seeded):
    with app.app_context():
        public_id = by_clave("proyector-sala-chica").public_id

    requester = page_text(log_in(app, "paula.contreras"), public_id)

    assert "Ticket creado" in requester
    assert "Solicitante agregado" not in requester
    assert "Solicitante retirado" not in requester
    assert "Constanza Herrera" not in requester
    assert "la sala la tenía reservada Paula" not in requester

    staff = page_text(log_in(app, "felipe.araya"), public_id)

    assert "Solicitante retirado: «Constanza Herrera»" in staff
    assert "Solicitante agregado: «Paula Contreras»" in staff
    assert "Motivo: Constanza solo avisó por teléfono; la sala la tenía reservada Paula." in staff
    assert "Solicitante Gestionar" in staff


def test_requester_dates_follow_a_refresh_in_order(app, seeded):
    with app.app_context():
        first = date_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert date_snapshot() != first

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            added = {
                e.contexto["participacion_id"]: e.fecha_hora
                for e in events_of(ticket, TicketEvent.SOLICITANTE_AGREGADO)
            }
            retired = {
                e.contexto["participacion_id"]: e.fecha_hora
                for e in events_of(ticket, TicketEvent.SOLICITANTE_RETIRADO)
            }

            for link in requesters_of(ticket):
                assert link.fecha_asociacion == added.get(link.id, ticket.fecha_creacion)

                if link.id in retired:
                    assert link.fecha_retiro == retired[link.id]
                    assert link.fecha_retiro >= link.fecha_asociacion
                else:
                    assert link.fecha_retiro is None


def test_a_hand_made_requester_change_follows_the_refresh(app, seeded):
    from src.workdesk.tickets.requesters import add_requester, remove_requester

    later = NOW + timedelta(days=3)

    with app.app_context():
        ticket = by_clave("proyector-sala-chica")
        diego = user("diego.soto")

        # A mano: se suma a Javiera y después se retira a Paula.
        added = add_requester(ticket, user("javiera.torres").id, actor=diego)
        db.session.commit()
        remove_requester(
            ticket,
            link_for(ticket, "paula.contreras").id,
            actor=diego,
            reason="A mano",
        )
        db.session.commit()

        seed_demo_tickets(now=later)

        ticket = by_clave("proyector-sala-chica")
        events = history_of(ticket)
        times = [e.fecha_hora for e in events]
        hand_added = events_of(ticket, TicketEvent.SOLICITANTE_AGREGADO)[-1]
        hand_removed = events_of(ticket, TicketEvent.SOLICITANTE_RETIRADO)[-1]

        # Los eventos hechos a mano siguen en orden y no quedan en el futuro.
        assert times == sorted(times)
        assert max(times) <= later - timedelta(minutes=1)
        # Y sus participaciones los acompañan, con el retiro nunca antes de empezar.
        db.session.refresh(added)
        paula = link_for(ticket, "paula.contreras")

        assert added.fecha_asociacion == hand_added.fecha_hora
        assert paula.fecha_retiro == hand_removed.fecha_hora
        assert paula.fecha_retiro >= paula.fecha_asociacion


# --- Comentarios y notas internas ------------------------------------------


@pytest.mark.parametrize(
    ("adjustment", "message"),
    [
        # `excel-bloqueado` (el primero) lo crea Javiera, que es su solicitante.
        (DemoAdjustment(actor="paula.contreras", despues_horas=1, comentario="Hola"),
         "no es solicitante ni creó el ticket"),
        (DemoAdjustment(actor="javiera.torres", despues_horas=1, comentario="Hola",
                        titulo="Otro título"),
         "no es personal"),
        (DemoAdjustment(actor="javiera.torres", despues_horas=1, nota_interna="Secreto"),
         "no es personal"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, comentario="x" * 5001),
         "comentario supera los 5000"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, nota_interna="y" * 5001),
         "nota interna supera los 5000"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, comentario=" con espacios "),
         "comentario está vacío o tiene espacios"),
    ],
)
def test_validation_rejects_inconsistent_comment_steps(adjustment, message):
    ticket = replace(DEMO_TICKETS[0], ajustes=(adjustment,))

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((ticket,))


def test_validation_accepts_the_creator_and_a_current_requester_commenting():
    # Javiera crea `excel-bloqueado`; en el ticket comenta quien es solicitante
    # en ese momento, aunque se haya agregado después.
    creator = (
        DemoAdjustment(actor="javiera.torres", despues_horas=1, comentario="Gracias"),
    )
    added = (
        DemoAdjustment(actor="diego.soto", despues_horas=1, agregar_solicitante="andres.silva"),
        DemoAdjustment(actor="andres.silva", despues_horas=1, comentario="A mí también me pasa"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=creator),))
    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=added),))

    # Pero no después de retirarlo.
    retired = added + (
        DemoAdjustment(actor="diego.soto", despues_horas=1, retirar_solicitante="andres.silva"),
        DemoAdjustment(actor="andres.silva", despues_horas=1, comentario="Sigo aquí"),
    )

    with pytest.raises(DemoTicketsError, match="no es solicitante ni creó el ticket"):
        validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=retired),))


def test_demo_data_covers_the_comment_cases():
    steps = [step for demo in DEMO_TICKETS for step in demo.ajustes]

    assert any(s.comentario and ROLES[s.actor] != "SOLICITANTE" for s in steps)
    assert any(s.comentario and ROLES[s.actor] == "SOLICITANTE" for s in steps), (
        "falta un comentario de un Solicitante"
    )
    assert any(s.nota_interna for s in steps), "falta una nota interna"
    assert any(s.comentario and s.nota_interna for s in steps), "falta un paso con ambas"
    assert any(s.comentario and s.estado for s in steps), (
        "falta un comentario junto a un cambio de estado"
    )
    # Un ticket con más notas que comentarios públicos: el Solicitante ve poco.
    assert any(
        sum(1 for s in demo.ajustes if s.nota_interna)
        > sum(1 for s in demo.ajustes if s.comentario)
        for demo in DEMO_TICKETS
    )


def test_a_conversation_leaves_the_same_history_as_the_application(app, seeded):
    with app.app_context():
        ticket = by_clave("intranet-credenciales")
        comments = comments_of(ticket)
        events = history_of(ticket)
        notes = [
            e
            for e in events
            if e.tipo_evento == "COMENTARIO_AGREGADO" and e.visibilidad == "INTERNO"
        ]

        # Dentro de un paso, el comentario público va antes que la nota.
        assert [(c.autor.username, c.tipo) for c in comments] == [
            ("felipe.araya", "PUBLICO"),
            ("sebastian.vargas", "PUBLICO"),
            ("felipe.araya", "PUBLICO"),
            ("felipe.araya", "INTERNO"),
        ]
        assert [e.tipo_evento for e in events].count("COMENTARIO_AGREGADO") == 4
        assert len(notes) == 1
        assert all(e.contexto["demo_clave"] == "intranet-credenciales" for e in events)
        assert ticket.estado.codigo == "EN_PROGRESO"


def test_comments_alone_do_not_modify_the_ticket(app, seeded):
    with app.app_context():
        ticket = by_clave("teclado-derrame-rrhh")

        assert len(comments_of(ticket)) == 3
        assert ticket.version == 1
        assert ticket.fecha_modificacion is None
        assert ticket.fecha_actualizacion == ticket.fecha_creacion


def test_each_comment_carries_the_date_of_its_event(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            published = {
                e.contexto["comentario_id"]: e.fecha_hora
                for e in history_of(ticket)
                if e.tipo_evento == "COMENTARIO_AGREGADO"
            }

            for comment in comments_of(ticket):
                assert comment.fecha_creacion == published[comment.id], demo.clave
                assert comment.fecha_creacion >= ticket.fecha_creacion


def test_the_requester_sees_the_public_conversation_but_never_the_notes(app, seeded):
    client = log_in(app, "sebastian.vargas")

    with app.app_context():
        public_id = by_clave("intranet-credenciales").public_id

    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)
    plain = " ".join(re.sub(r"<[^>]+>", " ", html).split())

    assert "Actividad (3)" in plain
    assert "Ya forzamos la sincronización" in plain
    assert "¿Es por eso?" in plain
    assert "sincroniza las credenciales" not in html
    assert "NOTA INTERNA" not in html
    assert "Solo visible para soporte" not in html


def test_a_requester_sees_one_comment_where_staff_wrote_two_notes(app, seeded):
    client = log_in(app, "ignacio.molina")

    with app.app_context():
        public_id = by_clave("switch-bodega-puertos").public_id

    html = client.get(f"/tickets/{public_id}").get_data(as_text=True)
    plain = " ".join(re.sub(r"<[^>]+>", " ", html).split())

    assert "Actividad (1)" in plain
    assert "cambiar unos cables en la bodega" in plain
    assert "errores CRC" not in html
    assert "NOTA INTERNA" not in html


def test_staff_sees_the_notes_marked_as_internal(app, seeded):
    client = log_in(app, "camila.rojas")

    with app.app_context():
        public_id = by_clave("switch-bodega-puertos").public_id

    plain = page_text(client, public_id)

    assert "Actividad (3)" in plain
    assert "errores CRC en los puertos 3 y 4" in plain
    assert plain.count("NOTA INTERNA") == 2
    assert "Solo visible para soporte" in plain


def test_comment_dates_follow_a_refresh(app, seeded):
    with app.app_context():
        first = date_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert date_snapshot() != first

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            published = {
                e.contexto["comentario_id"]: e.fecha_hora
                for e in history_of(ticket)
                if e.tipo_evento == "COMENTARIO_AGREGADO"
            }

            for comment in comments_of(ticket):
                assert comment.fecha_creacion == published[comment.id], demo.clave


def test_a_hand_made_edit_and_deletion_follow_the_refresh_in_order(app, seeded):
    from src.workdesk.tickets.comments import delete_comment, edit_comment

    later = NOW + timedelta(days=3)

    with app.app_context():
        ticket = by_clave("wifi-visitas-clave")
        first, second, *_ = comments_of(ticket)
        camila = user("camila.rojas")

        # A mano: se corrige un comentario y se elimina otro.
        edit_comment(ticket, first.id, actor=camila, content="Texto corregido a mano")
        db.session.commit()
        delete_comment(ticket, second.id, actor=camila)
        db.session.commit()

        seed_demo_tickets(now=later)

        ticket = by_clave("wifi-visitas-clave")
        events = history_of(ticket)
        times = [e.fecha_hora for e in events]
        edit = next(e for e in events if e.tipo_evento == "COMENTARIO_EDITADO")
        deletion = next(e for e in events if e.tipo_evento == "COMENTARIO_ELIMINADO")

        db.session.refresh(first)
        db.session.refresh(second)

        # Los eventos hechos a mano siguen en orden y no quedan en el futuro...
        assert times == sorted(times)
        assert max(times) <= later - timedelta(minutes=1)
        # ...y el comentario los acompaña, sin perder lo que se escribió.
        assert first.fecha_modificacion == edit.fecha_hora
        assert second.fecha_eliminacion == deletion.fecha_hora
        assert first.fecha_modificacion >= first.fecha_creacion
        assert first.contenido == "Texto corregido a mano"
        assert second.activo is False


def test_refresh_keeps_the_comments(app, seeded):
    with app.app_context():
        before = content_snapshot()

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert content_snapshot() == before


# --- Adjuntos ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("adjustment", "message"),
    [
        (DemoAdjustment(actor="diego.soto", despues_horas=1, adjunto=("virus.exe", "MZ")),
         "debe terminar en .txt, .log o .csv"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, adjunto=("imagen.png", "x")),
         "debe terminar en .txt, .log o .csv"),
        (DemoAdjustment(actor="diego.soto", despues_horas=1, adjunto=("vacio.txt", "  ")),
         "está vacío"),
        # Un Solicitante solo adjunta a su propio comentario.
        (DemoAdjustment(actor="javiera.torres", despues_horas=1, adjunto=("a.txt", "x")),
         "no es personal"),
    ],
)
def test_validation_rejects_inconsistent_attachment_steps(adjustment, message):
    ticket = replace(DEMO_TICKETS[0], ajustes=(adjustment,))

    with pytest.raises(DemoTicketsError, match=message):
        validate_demo_tickets((ticket,))


def test_a_requester_can_attach_a_file_to_their_comment():
    step = DemoAdjustment(
        actor="javiera.torres",
        despues_horas=1,
        comentario="Adjunto el log",
        adjunto=("log.log", "contenido"),
    )

    validate_demo_tickets((replace(DEMO_TICKETS[0], ajustes=(step,)),))


def test_the_files_hang_from_the_right_comment_and_exist_on_disk(app, seeded):
    with app.app_context():
        log_ticket = by_clave("error-sistema-contable-log")
        log, diagnosis = attachments_of(log_ticket)
        comments = comments_of(log_ticket)
        csv = attachments_of(by_clave("inventario-notebooks-csv"))[0]

        # El del Solicitante, a su comentario público; el del equipo, al
        # comentario público de su paso (no a la nota).
        assert log.comentario_id == comments[0].id
        assert diagnosis.comentario_id == comments[1].id
        assert comments[1].tipo == "PUBLICO"
        # El del tercer ticket es del ticket, sin comentario.
        assert csv.comentario_id is None

        for item in (log, diagnosis, csv):
            path = attachment_path(item)

            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item.hash
            assert item.tamano_bytes == path.stat().st_size


def test_a_requester_downloads_their_ticket_files(app, seeded):
    client = log_in(app, "javiera.torres")

    with app.app_context():
        ticket = by_clave("error-sistema-contable-log")
        public_id = ticket.public_id
        item = attachments_of(ticket)[0]
        item_id = item.id

    response = client.get(f"/tickets/{public_id}/attachments/{item_id}/download")

    assert response.status_code == 200
    assert b"acceso denegado" in response.data
    assert "attachment" in response.headers["Content-Disposition"]


def test_each_file_carries_the_date_of_its_event(app, seeded):
    with app.app_context():
        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            uploaded = {
                e.contexto["archivo_id"]: e.fecha_hora
                for e in history_of(ticket)
                if e.tipo_evento == "ARCHIVO_ADJUNTADO"
            }

            for item in attachments_of(ticket):
                assert item.fecha_subida == uploaded[item.id], demo.clave


def test_file_dates_follow_a_refresh_and_the_files_stay(app, seeded):
    with app.app_context():
        before = date_snapshot()
        paths = [attachment_path(f) for f in db.session.scalars(db.select(Attachment))]

        seed_demo_tickets(now=NOW + timedelta(days=3))

        assert date_snapshot() != before
        assert all(p.is_file() for p in paths)
        assert len(db.session.scalars(db.select(Attachment)).all()) == len(paths)

        for demo in DEMO_TICKETS:
            ticket = by_clave(demo.clave)
            uploaded = {
                e.contexto["archivo_id"]: e.fecha_hora
                for e in history_of(ticket)
                if e.tipo_evento == "ARCHIVO_ADJUNTADO"
            }

            for item in attachments_of(ticket):
                assert item.fecha_subida == uploaded[item.id], demo.clave


def test_running_the_seed_again_does_not_duplicate_files(app, seeded):
    with app.app_context():
        files = sorted(Path(app.config["UPLOADS_DIR"]).rglob("*"))
        files = [f for f in files if f.is_file()]

        seed_demo_tickets(now=NOW + timedelta(days=1))

        again = [f for f in Path(app.config["UPLOADS_DIR"]).rglob("*") if f.is_file()]

        assert len(again) == len(files) == 3


def test_a_hand_made_file_deletion_follows_the_refresh(app, seeded):
    from src.workdesk.tickets.attachments import delete_attachment

    later = NOW + timedelta(days=3)

    with app.app_context():
        ticket = by_clave("inventario-notebooks-csv")
        item = attachments_of(ticket)[0]

        delete_attachment(ticket, item.id, actor=user("camila.rojas"))
        db.session.commit()

        seed_demo_tickets(now=later)

        events = history_of(by_clave("inventario-notebooks-csv"))
        removal = next(e for e in events if e.tipo_evento == "ARCHIVO_ELIMINADO")

        db.session.refresh(item)

        assert item.fecha_eliminacion == removal.fecha_hora
        assert item.fecha_eliminacion >= item.fecha_subida
        assert max(e.fecha_hora for e in events) <= later - timedelta(minutes=1)
