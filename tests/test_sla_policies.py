"""Políticas de SLA por prioridad (docs/09, 20.2; docs/11, UI-022).

Una política dice cuánto tiempo laboral tiene un ticket de cierta prioridad para
recibir su primera respuesta y para resolverse. Hay una por prioridad, se edita en
el sitio, y `seed-catalogs` carga las iniciales.
"""

import threading
from datetime import UTC, datetime

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import AdminAuditLog, Estado, PoliticaSla, Prioridad
from src.workdesk.seeds import seed_catalogs
from src.workdesk.seeds.catalogs import INITIAL_SLA_POLICIES
from src.workdesk.sla import policies
from src.workdesk.sla.policies import (
    CONFLICT_MESSAGE,
    MAX_TARGET_MINUTES,
    NO_POLICY_TOKEN,
    NothingToChangeError,
    PolicyConflictError,
    PolicyRuleError,
    SaveOutcome,
    activate_policy,
    deactivate_policy,
    get_policy,
    get_priority,
    list_policy_rows,
    on_hold_state_name,
    policy_problems,
    policy_token,
    save_policy,
)
from tests.ticket_helpers import person

# Lo que carga `seed-catalogs` (docs/11, UI-022): primera respuesta, resolución y
# umbral, en minutos y porcentaje.
SEEDED = {
    "BAJA": (480, 1440, 80),
    "MEDIA": (240, 720, 80),
    "ALTA": (120, 360, 75),
    "CRITICA": (30, 240, 75),
}


# --- Auxiliares -------------------------------------------------------------


@pytest.fixture()
def admin(app, make_user, seeded_catalogs):
    return make_user("ADMINISTRADOR", username="admin")


@pytest.fixture()
def other_admin(make_user, admin):
    return make_user("ADMINISTRADOR", username="otro_admin")


def priority_by_code(code) -> Prioridad:
    return db.session.scalar(db.select(Prioridad).where(Prioridad.codigo == code))


def policy_by_code(code) -> PoliticaSla | None:
    return get_policy(priority_by_code(code))


def policy_count(code) -> int:
    return db.session.scalar(
        db.select(db.func.count(PoliticaSla.id)).where(
            PoliticaSla.prioridad_id == priority_by_code(code).id
        )
    )


def delete_policy(code) -> None:
    """Quita la política que cargó el seed, para probar el alta."""
    db.session.delete(policy_by_code(code))
    db.session.commit()


def events(action) -> list[AdminAuditLog]:
    return list(
        db.session.scalars(
            db.select(AdminAuditLog)
            .where(AdminAuditLog.accion == action)
            .order_by(AdminAuditLog.id)
        )
    )


def save(code, actor_id, *, base=None, **changes):
    """Guarda con el servicio como lo haría la pantalla: con la marca vigente de la
    política, salvo que se indique otra."""
    row = priority_by_code(code)
    values = {
        "response_minutes": 30,
        "resolution_minutes": 240,
        "warning_percent": 80,
        "pause_on_hold": True,
        "reason": None,
    }
    values.update(changes)
    token = policy_token(get_policy(row)) if base is None else base

    return save_policy(row, actor=person(actor_id), base_token=token, **values)


def raw_policy(code="BAJA", **values) -> PoliticaSla:
    """Una política escrita directamente, sin pasar por el servicio."""
    data = {
        "prioridad_id": priority_by_code(code).id,
        "tiempo_objetivo_resolucion_minutos": 240,
    }
    data.update(values)

    return PoliticaSla(**data)


# --- Los valores iniciales ------------------------------------------------------


def test_the_seed_creates_one_policy_per_priority_with_the_documented_values(app, admin):
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(PoliticaSla.id))) == 4

        for code, (response, resolution, warning) in SEEDED.items():
            policy = policy_by_code(code)

            assert policy.tiempo_objetivo_respuesta_minutos == response
            assert policy.tiempo_objetivo_resolucion_minutos == resolution
            assert policy.umbral_aviso_consumo_porcentaje == warning
            assert policy.pausa_en_espera is True
            assert policy.activo is True
            # Las carga el sistema: no tienen creador.
            assert policy.usuario_creacion_id is None
            assert policy.fecha_modificacion is None


def test_the_seeded_values_follow_the_rules_of_a_policy(app):
    # Si alguien cambia la lista inicial y se equivoca, el seed no debe poder
    # cargar una política que el formulario rechazaría.
    for code, response, resolution, warning in INITIAL_SLA_POLICIES:
        assert policy_problems(
            response_minutes=response,
            resolution_minutes=resolution,
            warning_percent=warning,
        ) == {}, code

    assert {row[0] for row in INITIAL_SLA_POLICIES} == set(SEEDED)


def test_higher_priorities_have_tighter_objectives(app):
    # La lógica del SLA: cuanto más urgente, menos tiempo.
    with app.app_context():
        seed_catalogs()
        levels = [
            policy_by_code(row.codigo).tiempo_objetivo_resolucion_minutos
            for row in db.session.scalars(
                db.select(Prioridad).order_by(Prioridad.nivel)
            )
        ]

        assert levels == sorted(levels, reverse=True)


def test_the_seed_reports_the_policies_it_created_and_is_idempotent(app):
    with app.app_context():
        first = seed_catalogs()
        second = seed_catalogs()

        assert first["politicas_sla"] == 4
        assert second["politicas_sla"] == 0
        assert db.session.scalar(db.select(db.func.count(PoliticaSla.id))) == 4


def test_the_seed_does_not_touch_what_an_administrator_changed(app, admin):
    with app.app_context():
        save("MEDIA", admin["id"], resolution_minutes=600, response_minutes=None)
        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()

        seed_catalogs()

        media = policy_by_code("MEDIA")

        assert media.tiempo_objetivo_resolucion_minutos == 600
        assert media.tiempo_objetivo_respuesta_minutos is None
        # Una política desactivada no se reactiva ni se duplica.
        assert policy_by_code("ALTA").activo is False
        assert policy_count("ALTA") == 1


def test_the_seed_creates_only_the_policies_that_are_missing(app, admin):
    with app.app_context():
        delete_policy("BAJA")

        assert seed_catalogs()["politicas_sla"] == 1

        policy = policy_by_code("BAJA")

        assert policy.tiempo_objetivo_resolucion_minutos == SEEDED["BAJA"][1]


def test_the_seed_follows_the_priority_by_code_not_by_name(app, admin):
    with app.app_context():
        priority_by_code("CRITICA").nombre = "Urgente"
        delete_policy("CRITICA")

        assert seed_catalogs()["politicas_sla"] == 1
        assert policy_by_code("CRITICA") is not None


# --- Restricciones de la base de datos ----------------------------------------------


@pytest.mark.parametrize(
    "values",
    [
        {"tiempo_objetivo_resolucion_minutos": 0},
        {"tiempo_objetivo_resolucion_minutos": -5},
        {"tiempo_objetivo_respuesta_minutos": 0},
        {"tiempo_objetivo_respuesta_minutos": -1},
        # La primera respuesta no puede tardar más que la resolución.
        {
            "tiempo_objetivo_respuesta_minutos": 300,
            "tiempo_objetivo_resolucion_minutos": 240,
        },
        {"umbral_aviso_consumo_porcentaje": 0},
        {"umbral_aviso_consumo_porcentaje": 101},
        {"umbral_aviso_consumo_porcentaje": -10},
    ],
)
def test_the_database_rejects_invalid_policies(app, seeded_catalogs, values):
    with app.app_context():
        delete_policy("BAJA")
        db.session.add(raw_policy("BAJA", **values))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"umbral_aviso_consumo_porcentaje": 1},
        {"umbral_aviso_consumo_porcentaje": 100},
        # La primera respuesta puede ser tan larga como la resolución.
        {
            "tiempo_objetivo_respuesta_minutos": 240,
            "tiempo_objetivo_resolucion_minutos": 240,
        },
        {"tiempo_objetivo_respuesta_minutos": 1},
    ],
)
def test_the_database_accepts_the_limits(app, seeded_catalogs, values):
    with app.app_context():
        delete_policy("BAJA")
        db.session.add(raw_policy("BAJA", **values))
        db.session.commit()


def test_a_new_policy_has_sensible_defaults(app, seeded_catalogs):
    with app.app_context():
        delete_policy("BAJA")
        policy = raw_policy("BAJA")
        db.session.add(policy)
        db.session.commit()

        assert policy.activo is True
        assert policy.pausa_en_espera is True
        assert policy.tiempo_objetivo_respuesta_minutos is None
        assert policy.umbral_aviso_consumo_porcentaje is None
        assert policy.fecha_creacion is not None
        assert policy.usuario_creacion_id is None
        assert policy.fecha_modificacion is None
        assert policy.usuario_modificacion_id is None


def test_only_one_policy_can_be_active_per_priority(app, seeded_catalogs):
    with app.app_context():
        # ALTA ya tiene la suya, cargada por el seed.
        db.session.add(raw_policy("ALTA"))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_an_inactive_policy_does_not_block_another_active_one(app, seeded_catalogs):
    with app.app_context():
        old = policy_by_code("ALTA")
        old.activo = False
        db.session.commit()

        # Una nueva activa convive con la desactivada...
        db.session.add(raw_policy("ALTA"))
        db.session.flush()

        # ...pero la vieja ya no puede reactivarse: habría dos activas.
        old.activo = True

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_a_policy_needs_an_existing_priority(app, seeded_catalogs):
    with app.app_context():
        db.session.add(PoliticaSla(prioridad_id=999999, tiempo_objetivo_resolucion_minutos=60))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_a_priority_with_a_policy_cannot_be_deleted(app, seeded_catalogs):
    with app.app_context():
        db.session.delete(priority_by_code("BAJA"))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


# --- Las reglas de los valores ----------------------------------------------------------


def test_valid_values_have_no_problems():
    assert policy_problems(
        response_minutes=30, resolution_minutes=240, warning_percent=80
    ) == {}
    assert policy_problems(
        response_minutes=None, resolution_minutes=1, warning_percent=None
    ) == {}


def test_the_resolution_is_required():
    problems = policy_problems(
        response_minutes=None, resolution_minutes=None, warning_percent=None
    )

    assert problems == {"resolucion": "Ingresa el objetivo de resolución."}


@pytest.mark.parametrize("minutes", [0, -1, -600])
def test_the_resolution_must_be_positive(minutes):
    problems = policy_problems(
        response_minutes=None, resolution_minutes=minutes, warning_percent=None
    )

    assert problems == {
        "resolucion": "El objetivo de resolución debe ser mayor que cero."
    }


def test_the_resolution_has_an_upper_bound_that_is_inclusive():
    assert policy_problems(
        response_minutes=None,
        resolution_minutes=MAX_TARGET_MINUTES,
        warning_percent=None,
    ) == {}

    problems = policy_problems(
        response_minutes=None,
        resolution_minutes=MAX_TARGET_MINUTES + 1,
        warning_percent=None,
    )

    assert problems == {
        "resolucion": "El objetivo de resolución no puede superar 1000 h."
    }


@pytest.mark.parametrize("minutes", [0, -1])
def test_the_first_response_must_be_positive_when_given(minutes):
    problems = policy_problems(
        response_minutes=minutes, resolution_minutes=240, warning_percent=None
    )

    assert list(problems) == ["primera_respuesta"]
    assert "mayor que cero" in problems["primera_respuesta"]


def test_the_first_response_has_the_same_upper_bound():
    problems = policy_problems(
        response_minutes=MAX_TARGET_MINUTES + 1,
        resolution_minutes=MAX_TARGET_MINUTES + 1,
        warning_percent=None,
    )

    assert "no puede superar 1000 h" in problems["primera_respuesta"]


def test_the_first_response_cannot_take_longer_than_the_resolution():
    problems = policy_problems(
        response_minutes=241, resolution_minutes=240, warning_percent=None
    )

    assert problems == {
        "primera_respuesta": (
            "La primera respuesta no puede tardar más que la resolución (4 h)."
        )
    }

    # Igual a la resolución sí se acepta.
    assert policy_problems(
        response_minutes=240, resolution_minutes=240, warning_percent=None
    ) == {}


@pytest.mark.parametrize("resolution", [None, 0, -3, MAX_TARGET_MINUTES + 1])
def test_the_first_response_is_not_compared_with_an_invalid_resolution(resolution):
    # Si la resolución ya está mal, ese es el único problema que se señala: no
    # tiene sentido comparar nada con ella (ni formatear una duración negativa).
    problems = policy_problems(
        response_minutes=500, resolution_minutes=resolution, warning_percent=None
    )

    assert list(problems) == ["resolucion"]


@pytest.mark.parametrize("percent", [0, -1, 101, 1000])
def test_the_warning_must_be_between_1_and_100(percent):
    problems = policy_problems(
        response_minutes=None, resolution_minutes=240, warning_percent=percent
    )

    assert problems == {"umbral_aviso": "El umbral debe estar entre 1 y 100."}


@pytest.mark.parametrize("percent", [1, 50, 100])
def test_the_warning_limits_are_accepted(percent):
    assert policy_problems(
        response_minutes=None, resolution_minutes=240, warning_percent=percent
    ) == {}


def test_all_the_problems_are_reported_at_once_resolution_first():
    problems = policy_problems(
        response_minutes=0, resolution_minutes=0, warning_percent=500
    )

    assert list(problems) == ["resolucion", "primera_respuesta", "umbral_aviso"]


# --- Consultas -----------------------------------------------------------------------------


def test_the_rows_list_every_priority_in_level_order_with_its_policy(app, admin):
    with app.app_context():
        rows = list_policy_rows()

        assert [row.priority.codigo for row in rows] == [
            "BAJA",
            "MEDIA",
            "ALTA",
            "CRITICA",
        ]
        assert [row.policy.tiempo_objetivo_resolucion_minutos for row in rows] == [
            SEEDED[row.priority.codigo][1] for row in rows
        ]


def test_the_rows_follow_the_priority_level_not_the_insertion_order(app, admin):
    with app.app_context():
        # Con los ids del seed, el orden por nivel y el de inserción coinciden:
        # se sube el nivel de la más baja para que dejen de coincidir.
        priority_by_code("BAJA").nivel = 10
        db.session.commit()

        assert [row.priority.codigo for row in list_policy_rows()] == [
            "MEDIA",
            "ALTA",
            "CRITICA",
            "BAJA",
        ]


def test_a_priority_without_a_policy_is_listed_with_none(app, admin):
    with app.app_context():
        delete_policy("MEDIA")
        rows = {row.priority.codigo: row.policy for row in list_policy_rows()}

        assert rows["MEDIA"] is None
        assert rows["BAJA"] is not None


def test_an_inactive_priority_and_an_inactive_policy_are_still_listed(app, admin):
    with app.app_context():
        priority_by_code("BAJA").activo = False
        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()

        rows = {row.priority.codigo: row for row in list_policy_rows()}

        assert len(rows) == 4
        assert rows["BAJA"].priority.activo is False
        assert rows["ALTA"].policy.activo is False


def test_listing_the_rows_is_a_single_query(app, admin):
    with app.app_context():
        queries = []

        def count(conn, cursor, statement, *args):
            queries.append(statement)

        event.listen(db.engine, "before_cursor_execute", count)

        try:
            rows = list_policy_rows()
            # Tocar lo que muestra la pantalla no debe lanzar más consultas.
            shown = [
                (row.priority.nombre, row.policy.tiempo_objetivo_resolucion_minutos)
                for row in rows
            ]
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

        assert len(shown) == 4
        assert len(queries) == 1


def test_the_priority_and_its_policy_are_found_by_id(app, admin):
    with app.app_context():
        priority = priority_by_code("ALTA")

        assert get_priority(priority.id) is priority
        assert get_priority(999999) is None
        assert get_policy(priority).prioridad_id == priority.id


def test_the_on_hold_state_name_follows_the_administrators_renaming(app, admin):
    with app.app_context():
        assert on_hold_state_name() == "En espera"

        state = db.session.scalar(db.select(Estado).where(Estado.codigo == "EN_ESPERA"))
        state.nombre_visible = "En pausa"
        db.session.commit()

        assert on_hold_state_name() == "En pausa"


def test_the_policy_token_identifies_each_state_of_the_policy(app, admin):
    with app.app_context():
        assert policy_token(None) == NO_POLICY_TOKEN

        policy = policy_by_code("ALTA")
        created = policy_token(policy)

        # Es estable mientras nadie cambie nada, también al leerla de nuevo.
        db.session.expire_all()
        assert policy_token(policy_by_code("ALTA")) == created

        save("ALTA", admin["id"], resolution_minutes=300)
        db.session.commit()
        edited = policy_token(policy_by_code("ALTA"))

        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()
        deactivated = policy_token(policy_by_code("ALTA"))

        assert len({created, edited, deactivated}) == 3


# --- Definir los objetivos de una prioridad --------------------------------------------


def test_defining_the_objectives_creates_an_active_policy(app, admin):
    with app.app_context():
        delete_policy("ALTA")

        result = save("ALTA", admin["id"], reason="Primera configuración")
        db.session.commit()

        policy = policy_by_code("ALTA")

        assert result.outcome is SaveOutcome.CREATED
        assert result.policy is policy
        assert policy.activo is True
        assert policy.tiempo_objetivo_respuesta_minutos == 30
        assert policy.tiempo_objetivo_resolucion_minutos == 240
        assert policy.umbral_aviso_consumo_porcentaje == 80
        assert policy.pausa_en_espera is True
        assert policy.usuario_creacion_id == admin["id"]
        assert policy.fecha_modificacion is None


def test_a_policy_can_have_no_first_response_and_no_warning_and_no_pause(app, admin):
    with app.app_context():
        delete_policy("ALTA")

        save(
            "ALTA",
            admin["id"],
            response_minutes=None,
            warning_percent=None,
            pause_on_hold=False,
        )
        db.session.commit()

        policy = policy_by_code("ALTA")

        assert policy.tiempo_objetivo_respuesta_minutos is None
        assert policy.umbral_aviso_consumo_porcentaje is None
        assert policy.pausa_en_espera is False


def test_defining_a_policy_is_audited_with_its_values(app, admin):
    with app.app_context():
        delete_policy("ALTA")
        save("ALTA", admin["id"], reason="Primera configuración")
        db.session.commit()

        (entry,) = events("POLITICA_SLA_CREADA")
        policy = policy_by_code("ALTA")

        assert entry.actor_usuario_id == admin["id"]
        assert entry.entidad_tipo == "politica_sla"
        assert entry.entidad_id == policy.id
        assert entry.detalle == "Prioridad Alta"
        assert entry.motivo == "Primera configuración"
        assert entry.valor_anterior is None
        assert entry.valor_nuevo == {
            "tiempo_objetivo_respuesta_minutos": 30,
            "tiempo_objetivo_resolucion_minutos": 240,
            "umbral_aviso_consumo_porcentaje": 80,
            "pausa_en_espera": True,
            "activo": True,
        }


def test_the_service_does_not_commit(app, admin):
    with app.app_context():
        delete_policy("ALTA")
        save("ALTA", admin["id"])
        db.session.rollback()

        assert policy_by_code("ALTA") is None
        assert events("POLITICA_SLA_CREADA") == []


# --- Editar ------------------------------------------------------------------------------------


def test_editing_applies_only_what_changed_and_audits_it(app, admin):
    with app.app_context():
        before = policy_by_code("ALTA").fecha_creacion

        result = save(
            "ALTA",
            admin["id"],
            response_minutes=120,
            resolution_minutes=480,
            warning_percent=75,
            reason="Más margen para soporte",
        )
        db.session.commit()

        policy = policy_by_code("ALTA")

        assert result.outcome is SaveOutcome.UPDATED
        assert policy.tiempo_objetivo_resolucion_minutos == 480
        assert policy.fecha_creacion == before
        assert policy.fecha_modificacion is not None
        assert policy.usuario_modificacion_id == admin["id"]

        (entry,) = events("POLITICA_SLA_MODIFICADA")

        assert entry.entidad_id == policy.id
        assert entry.detalle == "Prioridad Alta"
        assert entry.motivo == "Más margen para soporte"
        # Solo el campo que cambió, con su valor anterior y el nuevo.
        assert entry.valor_anterior == {"tiempo_objetivo_resolucion_minutos": 360}
        assert entry.valor_nuevo == {"tiempo_objetivo_resolucion_minutos": 480}


def test_every_field_can_be_edited(app, admin):
    with app.app_context():
        save(
            "MEDIA",
            admin["id"],
            response_minutes=None,
            resolution_minutes=100,
            warning_percent=None,
            pause_on_hold=False,
        )
        db.session.commit()

        policy = policy_by_code("MEDIA")

        assert policy.tiempo_objetivo_respuesta_minutos is None
        assert policy.tiempo_objetivo_resolucion_minutos == 100
        assert policy.umbral_aviso_consumo_porcentaje is None
        assert policy.pausa_en_espera is False

        (entry,) = events("POLITICA_SLA_MODIFICADA")

        assert entry.valor_anterior == {
            "tiempo_objetivo_respuesta_minutos": 240,
            "tiempo_objetivo_resolucion_minutos": 720,
            "umbral_aviso_consumo_porcentaje": 80,
            "pausa_en_espera": True,
        }
        assert entry.valor_nuevo == {
            "tiempo_objetivo_respuesta_minutos": None,
            "tiempo_objetivo_resolucion_minutos": 100,
            "umbral_aviso_consumo_porcentaje": None,
            "pausa_en_espera": False,
        }


def test_saving_the_same_values_changes_and_audits_nothing(app, admin):
    with app.app_context():
        response, resolution, warning = SEEDED["ALTA"]
        token = policy_token(policy_by_code("ALTA"))

        result = save(
            "ALTA",
            admin["id"],
            response_minutes=response,
            resolution_minutes=resolution,
            warning_percent=warning,
            pause_on_hold=True,
        )
        db.session.commit()

        assert result.outcome is SaveOutcome.UNCHANGED
        assert policy_by_code("ALTA").fecha_modificacion is None
        assert policy_token(policy_by_code("ALTA")) == token
        assert events("POLITICA_SLA_MODIFICADA") == []


def test_a_blank_reason_is_stored_as_no_reason(app, admin):
    with app.app_context():
        save("ALTA", admin["id"], resolution_minutes=500, reason="   ")
        db.session.commit()

        (entry,) = events("POLITICA_SLA_MODIFICADA")

        assert entry.motivo is None


def test_an_inactive_policy_can_be_edited_and_stays_inactive(app, admin):
    with app.app_context():
        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()

        result = save("ALTA", admin["id"], resolution_minutes=500)
        db.session.commit()

        assert result.outcome is SaveOutcome.UPDATED
        assert policy_by_code("ALTA").activo is False
        assert policy_by_code("ALTA").tiempo_objetivo_resolucion_minutos == 500


def test_editing_does_not_create_a_second_policy(app, admin):
    with app.app_context():
        save("ALTA", admin["id"], resolution_minutes=500)
        db.session.commit()

        assert policy_count("ALTA") == 1


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"resolution_minutes": 0}, "resolucion"),
        ({"resolution_minutes": -3}, "resolucion"),
        ({"resolution_minutes": MAX_TARGET_MINUTES + 1}, "resolucion"),
        ({"response_minutes": 0}, "primera_respuesta"),
        ({"response_minutes": 9999}, "primera_respuesta"),
        ({"warning_percent": 0}, "umbral_aviso"),
        ({"warning_percent": 101}, "umbral_aviso"),
    ],
)
def test_an_invalid_value_is_rejected_and_leaves_nothing(app, admin, changes, field):
    with app.app_context():
        before = policy_by_code("ALTA").tiempo_objetivo_resolucion_minutos

        with pytest.raises(PolicyRuleError) as error:
            save("ALTA", admin["id"], **changes)

        assert error.value.field == field
        assert not isinstance(error.value, PolicyConflictError)

        db.session.rollback()

        assert policy_by_code("ALTA").tiempo_objetivo_resolucion_minutos == before
        assert events("POLITICA_SLA_MODIFICADA") == []


def test_the_first_problem_is_the_one_reported(app, admin):
    with app.app_context():
        with pytest.raises(PolicyRuleError) as error:
            save("ALTA", admin["id"], resolution_minutes=0, warning_percent=500)

        assert error.value.field == "resolucion"

        db.session.rollback()


# --- Ediciones simultáneas -----------------------------------------------------------------------


def test_a_stale_token_is_a_conflict_and_changes_nothing(app, admin, other_admin):
    with app.app_context():
        opened = policy_token(policy_by_code("ALTA"))

        # Otra persona guarda mientras la pantalla estaba abierta.
        save("ALTA", other_admin["id"], resolution_minutes=480)
        db.session.commit()

        with pytest.raises(PolicyConflictError) as error:
            save("ALTA", admin["id"], base=opened, resolution_minutes=600)

        db.session.rollback()

        assert str(error.value) == CONFLICT_MESSAGE
        assert policy_by_code("ALTA").tiempo_objetivo_resolucion_minutos == 480
        assert len(events("POLITICA_SLA_MODIFICADA")) == 1


def test_a_deactivation_while_the_form_was_open_is_a_conflict(app, admin, other_admin):
    with app.app_context():
        opened = policy_token(policy_by_code("ALTA"))
        deactivate_policy(priority_by_code("ALTA"), actor=person(other_admin["id"]))
        db.session.commit()

        with pytest.raises(PolicyConflictError):
            save("ALTA", admin["id"], base=opened, resolution_minutes=600)

        db.session.rollback()


def test_defining_a_policy_that_appeared_meanwhile_is_a_conflict(app, admin):
    with app.app_context():
        # El formulario se abrió cuando no había política (marca «0»)...
        with pytest.raises(PolicyConflictError):
            # ...y ya existe una.
            save("ALTA", admin["id"], base=NO_POLICY_TOKEN)

        db.session.rollback()
        assert policy_count("ALTA") == 1


@pytest.mark.parametrize("token", ["", "basura", "2020-01-01T00:00:00+00:00"])
def test_a_missing_or_wrong_token_is_a_conflict(app, admin, token):
    with app.app_context():
        with pytest.raises(PolicyConflictError):
            save("ALTA", admin["id"], base=token, resolution_minutes=600)

        db.session.rollback()
        assert policy_by_code("ALTA").tiempo_objetivo_resolucion_minutos == 360


def test_a_policy_loaded_before_a_concurrent_change_is_read_again_under_the_lock(
    app, admin
):
    # Es lo que pasa con dos peticiones casi simultáneas: la pantalla ya cargó la
    # política cuando la otra transacción confirma su cambio. La copia que tiene la
    # sesión está vieja y solo releerla bajo el bloqueo permite ver el conflicto.
    with app.app_context():
        priority = priority_by_code("ALTA")
        loaded = get_policy(priority)
        opened = policy_token(loaded)

        with db.engine.begin() as other_transaction:
            other_transaction.execute(
                db.update(PoliticaSla)
                .where(PoliticaSla.id == loaded.id)
                .values(
                    tiempo_objetivo_resolucion_minutos=999,
                    fecha_modificacion=datetime.now(UTC),
                )
            )

        with pytest.raises(PolicyConflictError):
            save("ALTA", admin["id"], base=opened, resolution_minutes=600)

        db.session.rollback()

        # No se pisó el cambio ajeno.
        assert policy_by_code("ALTA").tiempo_objetivo_resolucion_minutos == 999
        assert events("POLITICA_SLA_MODIFICADA") == []


def test_a_deactivation_by_someone_else_is_seen_even_if_the_policy_was_loaded(app, admin):
    with app.app_context():
        priority = priority_by_code("ALTA")
        loaded = get_policy(priority)

        with db.engine.begin() as other_transaction:
            other_transaction.execute(
                db.update(PoliticaSla)
                .where(PoliticaSla.id == loaded.id)
                .values(activo=False, fecha_modificacion=datetime.now(UTC))
            )

        # La copia de la sesión dice «activa», pero la fila ya no lo está: no se
        # desactiva dos veces ni se audita una desactivación que no ocurrió aquí.
        with pytest.raises(NothingToChangeError, match="ya está desactivada"):
            deactivate_policy(priority, actor=person(admin["id"]))

        db.session.rollback()
        assert events("POLITICA_SLA_DESACTIVADA") == []


def test_a_reactivation_by_someone_else_is_seen_even_if_the_policy_was_loaded(app, admin):
    with app.app_context():
        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()

        priority = priority_by_code("ALTA")
        loaded = get_policy(priority)

        with db.engine.begin() as other_transaction:
            other_transaction.execute(
                db.update(PoliticaSla)
                .where(PoliticaSla.id == loaded.id)
                .values(activo=True, fecha_modificacion=datetime.now(UTC))
            )

        with pytest.raises(NothingToChangeError, match="ya está activa"):
            activate_policy(priority, actor=person(admin["id"]))

        db.session.rollback()
        assert events("POLITICA_SLA_ACTIVADA") == []


def test_the_unique_index_is_the_last_defense_against_a_second_active_policy(
    app, admin, monkeypatch
):
    with app.app_context():
        # Se simula una vía que no respeta el bloqueo: el servicio cree que no hay
        # política (la marca «0» coincide) y la crea. Solo el índice único lo impide.
        monkeypatch.setattr(policies, "_lock_policy", lambda priority: None)

        with pytest.raises(PolicyConflictError):
            save("ALTA", admin["id"], base=NO_POLICY_TOKEN)

        # El savepoint deshizo solo el intento: la sesión sigue usable y no queda
        # nada a medias ni auditado.
        assert policy_count("ALTA") == 1
        assert events("POLITICA_SLA_CREADA") == []

        db.session.rollback()


# --- Desactivar y reactivar ------------------------------------------------------------------


def test_deactivating_removes_the_sla_of_the_priority_and_is_audited(app, admin):
    with app.app_context():
        policy = deactivate_policy(
            priority_by_code("ALTA"),
            actor=person(admin["id"]),
            reason="Se revisa el contrato",
        )
        db.session.commit()

        assert policy.activo is False
        assert policy.usuario_modificacion_id == admin["id"]
        assert policy.fecha_modificacion is not None

        (entry,) = events("POLITICA_SLA_DESACTIVADA")

        assert entry.entidad_tipo == "politica_sla"
        assert entry.entidad_id == policy.id
        assert entry.detalle == "Prioridad Alta"
        assert entry.valor_anterior == {"activo": True}
        assert entry.valor_nuevo == {"activo": False}
        assert entry.motivo == "Se revisa el contrato"


def test_reactivating_restores_the_same_objectives(app, admin):
    with app.app_context():
        before = {
            "respuesta": policy_by_code("ALTA").tiempo_objetivo_respuesta_minutos,
            "resolucion": policy_by_code("ALTA").tiempo_objetivo_resolucion_minutos,
        }
        deactivate_policy(priority_by_code("ALTA"), actor=person(admin["id"]))
        db.session.commit()

        policy = activate_policy(
            priority_by_code("ALTA"), actor=person(admin["id"]), reason="Vuelve"
        )
        db.session.commit()

        assert policy.activo is True
        assert policy.tiempo_objetivo_respuesta_minutos == before["respuesta"]
        assert policy.tiempo_objetivo_resolucion_minutos == before["resolucion"]
        assert policy_count("ALTA") == 1

        (entry,) = events("POLITICA_SLA_ACTIVADA")

        assert entry.valor_anterior == {"activo": False}
        assert entry.valor_nuevo == {"activo": True}
        assert entry.motivo == "Vuelve"


def test_an_unrequested_state_change_is_refused(app, admin):
    with app.app_context():
        actor = person(admin["id"])

        with pytest.raises(NothingToChangeError, match="ya está activa"):
            activate_policy(priority_by_code("ALTA"), actor=actor)

        deactivate_policy(priority_by_code("ALTA"), actor=actor)

        with pytest.raises(NothingToChangeError, match="ya está desactivada"):
            deactivate_policy(priority_by_code("ALTA"), actor=actor)

        db.session.commit()
        assert len(events("POLITICA_SLA_DESACTIVADA")) == 1
        assert events("POLITICA_SLA_ACTIVADA") == []


def test_a_priority_without_a_policy_cannot_be_activated_or_deactivated(app, admin):
    with app.app_context():
        delete_policy("ALTA")
        actor = person(admin["id"])

        for operation in (activate_policy, deactivate_policy):
            with pytest.raises(PolicyRuleError, match="todavía no tiene"):
                operation(priority_by_code("ALTA"), actor=actor)


def test_deactivating_and_reactivating_do_not_commit(app, admin):
    with app.app_context():
        actor = person(admin["id"])

        deactivate_policy(priority_by_code("ALTA"), actor=actor)
        db.session.rollback()

        assert policy_by_code("ALTA").activo is True
        assert events("POLITICA_SLA_DESACTIVADA") == []


# --- Carreras: dos Administradores a la vez ----------------------------------------------------


def run_together(app, jobs):
    """Cada trabajo se ejecuta en su hilo, con su sesión, y todos arrancan juntos.

    Cada trabajo recibe el usuario que actúa y devuelve una etiqueta; si lanza una
    `PolicyRuleError`, la etiqueta es el nombre de su clase.
    """
    barrier = threading.Barrier(len(jobs))
    outcomes = []

    def run(user_id, job):
        with app.app_context():
            actor = person(user_id)
            barrier.wait(timeout=10)

            try:
                outcomes.append(job(actor))
                db.session.commit()
            except PolicyRuleError as error:
                db.session.rollback()
                outcomes.append(type(error).__name__)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run, args=job) for job in jobs]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    return sorted(outcomes)


def test_two_administrators_defining_the_same_policy_create_it_once(
    app, admin, other_admin
):
    with app.app_context():
        delete_policy("ALTA")

    def define(resolution):
        def job(actor):
            result = save_policy(
                priority_by_code("ALTA"),
                actor=actor,
                base_token=NO_POLICY_TOKEN,
                response_minutes=None,
                resolution_minutes=resolution,
                warning_percent=None,
                pause_on_hold=True,
            )

            return result.outcome.value

        return job

    outcomes = run_together(
        app,
        [(admin["id"], define(200)), (other_admin["id"], define(300))],
    )

    assert outcomes == ["PolicyConflictError", "creada"]

    with app.app_context():
        # Una sola política y una sola creación auditada.
        assert policy_count("ALTA") == 1
        assert len(events("POLITICA_SLA_CREADA")) == 1


def test_two_administrators_editing_from_the_same_screen_save_only_the_first(
    app, admin, other_admin
):
    with app.app_context():
        opened = policy_token(policy_by_code("ALTA"))

    def edit(resolution):
        def job(actor):
            result = save_policy(
                priority_by_code("ALTA"),
                actor=actor,
                base_token=opened,
                response_minutes=120,
                resolution_minutes=resolution,
                warning_percent=75,
                pause_on_hold=True,
            )

            return result.outcome.value

        return job

    outcomes = run_together(
        app,
        [(admin["id"], edit(400)), (other_admin["id"], edit(500))],
    )

    assert outcomes == ["PolicyConflictError", "modificada"]

    with app.app_context():
        assert len(events("POLITICA_SLA_MODIFICADA")) == 1
        assert policy_by_code("ALTA").tiempo_objetivo_resolucion_minutos in (400, 500)


def test_two_administrators_deactivating_the_same_policy_deactivate_it_once(
    app, admin, other_admin
):
    def deactivate(actor):
        deactivate_policy(priority_by_code("ALTA"), actor=actor)

        return "desactivada"

    outcomes = run_together(
        app,
        [(admin["id"], deactivate), (other_admin["id"], deactivate)],
    )

    assert outcomes == ["NothingToChangeError", "desactivada"]

    with app.app_context():
        assert policy_by_code("ALTA").activo is False
        assert len(events("POLITICA_SLA_DESACTIVADA")) == 1
