"""Lo que escribe el Administrador al definir los objetivos de SLA: las duraciones
(«30 min», «4 h», «1 h 30 min») y el formulario que las recoge (docs/11, UI-022).

Qué valores son aceptables lo decide `policy_problems` (ver `test_sla_policies.py`);
aquí se comprueba que cada error se señala junto a su campo, todos a la vez, y que
una duración se entiende como la escribiría una persona.
"""

import pytest

from src.workdesk.extensions import db
from src.workdesk.models import PoliticaSla, Prioridad
from src.workdesk.sla.policies import NO_POLICY_TOKEN, policy_token
from src.workdesk.sla.policy_forms import (
    DEFAULT_WARNING_PERCENT,
    MAX_DURATION_TEXT_LENGTH,
    PolicyForm,
    duration_text,
    parse_duration,
    policy_form_data,
)

# --- Las duraciones: de texto a minutos ---------------------------------------------


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        # Minutos, con todas las formas de decir la unidad.
        ("30 min", 30),
        ("30min", 30),
        ("30 m", 30),
        ("30m", 30),
        ("30 mins", 30),
        ("30 minuto", 30),
        ("30 minutos", 30),
        ("1 minuto", 1),
        ("90 min", 90),
        # Horas.
        ("4 h", 240),
        ("4h", 240),
        ("4 hr", 240),
        ("4 hrs", 240),
        ("4 hora", 240),
        ("4 horas", 240),
        ("1 hora", 60),
        # Horas y minutos.
        ("1 h 30 min", 90),
        ("1h30", 90),
        ("1h 30", 90),
        ("1 h 30", 90),
        ("1h30m", 90),
        ("1 hora 30 minutos", 90),
        ("2 horas 15 minutos", 135),
        ("10h5m", 605),
        # Mayúsculas y espacios alrededor.
        ("2H15M", 135),
        ("  4 h  ", 240),
        ("4 H", 240),
        # Ceros: se entienden; la regla del valor decide si sirven.
        ("0 min", 0),
        ("0 h", 0),
        ("00 h 05 m", 5),
    ],
)
def test_a_duration_is_read_as_a_person_would_write_it(text, minutes):
    assert parse_duration(text) == minutes


@pytest.mark.parametrize("text", ["", "   ", None])
def test_no_text_means_no_objective(text):
    assert parse_duration(text) is None


@pytest.mark.parametrize("text", ["30", "4", "0", "  45  "])
def test_a_bare_number_is_ambiguous_and_asks_for_the_unit(text):
    with pytest.raises(ValueError, match="le falta la unidad"):
        parse_duration(text)


@pytest.mark.parametrize("text", ["1,5 h", "1.5 h", "0,5 h", "2.25h", "1,5"])
def test_decimals_are_refused_with_a_hint(text):
    with pytest.raises(ValueError, match="enteros"):
        parse_duration(text)


@pytest.mark.parametrize(
    "text",
    [
        "abc",
        "h",
        "min",
        "m",
        "-5 min",
        "-1 h",
        "+5 min",
        # Los días no se admiten: su duración depende del calendario.
        "2 d",
        "2 días",
        "1 dia",
        "1 semana",
        # Unidades repetidas o en otro orden.
        "4 h 30 h",
        "30 min 1 h",
        "1 h 2 h",
        "30 min 5 min",
        "1 h 30 m 5",
        "1:30",
        "4 h.",
        "4 horas y 30 minutos",
    ],
)
def test_anything_else_is_not_a_duration(text):
    with pytest.raises(ValueError, match="no es una duración válida"):
        parse_duration(text)


def test_the_error_quotes_what_was_written_and_gives_examples():
    with pytest.raises(ValueError) as error:
        parse_duration("dos horas")

    message = str(error.value)

    assert "«dos horas»" in message
    assert "«30 min»" in message
    assert "«4 h»" in message
    assert "«1 h 30 min»" in message


def test_huge_numbers_are_read_and_left_to_the_value_rules():
    # Python no desborda: el tope lo pone `policy_problems`, con su mensaje.
    assert parse_duration("99999999999999999999 h") == 99999999999999999999 * 60


def test_writing_and_reading_a_duration_are_inverse_operations():
    for minutes in [*range(1, 2001), 3599, 3600, 59999, 60000, 60001]:
        assert parse_duration(duration_text(minutes)) == minutes, minutes


def test_the_form_text_of_a_missing_objective_is_empty():
    assert duration_text(None) == ""
    assert duration_text(90) == "1 h 30 min"
    assert duration_text(30) == "30 min"
    assert duration_text(240) == "4 h"


# --- El formulario -----------------------------------------------------------------------------


def submit(app, **fields):
    """Envía el formulario con valores válidos, salvo los que se cambien. Un valor
    `None` omite el campo (como una casilla sin marcar)."""
    data = {
        "primera_respuesta": "",
        "resolucion": "4 h",
        "umbral_aviso": "80",
        "pausa_en_espera": "y",
        "motivo": "",
        "base": NO_POLICY_TOKEN,
    }
    data.update(fields)
    data = {name: value for name, value in data.items() if value is not None}

    with app.test_request_context(method="POST", data=data):
        form = PolicyForm()
        valid = form.validate()

    return form, valid


def test_a_valid_form_converts_the_durations(app):
    form, valid = submit(app, primera_respuesta="30 min", resolucion="1 h 30 min")

    assert valid
    assert form.response_minutes == 30
    assert form.resolution_minutes == 90
    assert form.umbral_aviso.data == 80
    assert form.pausa_en_espera.data is True
    assert form.base.data == NO_POLICY_TOKEN
    assert form.errors == {}


def test_a_form_without_a_first_response_is_valid(app):
    form, valid = submit(app, primera_respuesta="")

    assert valid
    assert form.response_minutes is None
    assert form.resolution_minutes == 240


def test_an_empty_warning_means_no_warning(app):
    form, valid = submit(app, umbral_aviso="")

    assert valid
    assert form.umbral_aviso.data is None


def test_an_unchecked_pause_is_false(app):
    form, valid = submit(app, pausa_en_espera=None)

    assert valid
    assert form.pausa_en_espera.data is False


def test_the_resolution_is_required_and_the_error_is_not_repeated(app):
    form, valid = submit(app, resolucion="")

    assert not valid
    assert form.resolucion.errors == ["Ingresa el objetivo de resolución."]
    assert form.resolution_minutes is None


def test_a_badly_written_duration_is_reported_once_next_to_its_field(app):
    form, valid = submit(app, resolucion="dos horas")

    assert not valid
    assert len(form.resolucion.errors) == 1
    assert "no es una duración válida" in form.resolucion.errors[0]
    assert form.primera_respuesta.errors == []


def test_a_zero_duration_is_rejected_by_the_value_rules(app):
    form, valid = submit(app, resolucion="0 min")

    assert not valid
    assert form.resolucion.errors == [
        "El objetivo de resolución debe ser mayor que cero."
    ]


def test_a_zero_resolution_is_the_only_problem_even_with_a_first_response(app):
    # No se compara la primera respuesta con una resolución que ya está mal.
    form, valid = submit(app, primera_respuesta="2 h", resolucion="0 min")

    assert not valid
    assert form.resolucion.errors == [
        "El objetivo de resolución debe ser mayor que cero."
    ]
    assert form.primera_respuesta.errors == []


def test_a_first_response_longer_than_the_resolution_is_reported_on_the_response(app):
    form, valid = submit(app, primera_respuesta="5 h", resolucion="4 h")

    assert not valid
    assert form.resolucion.errors == []
    assert form.primera_respuesta.errors == [
        "La primera respuesta no puede tardar más que la resolución (4 h)."
    ]


def test_a_duration_over_the_limit_is_reported(app):
    form, valid = submit(app, resolucion="1001 h")

    assert not valid
    assert form.resolucion.errors == [
        "El objetivo de resolución no puede superar 1000 h."
    ]

    form, valid = submit(app, resolucion="1000 h")

    assert valid


@pytest.mark.parametrize("value", ["0", "101", "-5", "1000"])
def test_a_warning_out_of_range_is_reported(app, value):
    form, valid = submit(app, umbral_aviso=value)

    assert not valid
    assert form.umbral_aviso.errors == ["El umbral debe estar entre 1 y 100."]


def test_a_warning_that_is_not_a_number_is_reported_once(app):
    form, valid = submit(app, umbral_aviso="abc")

    assert not valid
    assert form.umbral_aviso.errors == ["Ingresa un número entero."]


def test_every_problem_is_reported_at_once_next_to_its_field(app):
    form, valid = submit(
        app,
        primera_respuesta="mucho",
        resolucion="poco",
        umbral_aviso="500",
        motivo="x" * 501,
    )

    assert not valid
    assert len(form.primera_respuesta.errors) == 1
    assert len(form.resolucion.errors) == 1
    assert form.umbral_aviso.errors == ["El umbral debe estar entre 1 y 100."]
    assert len(form.motivo.errors) == 1


def test_an_overlong_text_is_reported_without_trying_to_read_it(app):
    # Además de largo, no es una duración: solo se señala el largo, que es lo
    # primero que hay que arreglar (leerlo añadiría un segundo error al campo).
    form, valid = submit(app, resolucion="mucho" * 10)

    assert not valid
    assert form.resolucion.errors == [f"Máximo {MAX_DURATION_TEXT_LENGTH} caracteres."]

    # Un texto largo pero legible tampoco se acepta.
    form, valid = submit(app, resolucion="9" * (MAX_DURATION_TEXT_LENGTH + 1) + " h")

    assert not valid
    assert form.resolucion.errors == [f"Máximo {MAX_DURATION_TEXT_LENGTH} caracteres."]


def test_a_missing_token_is_reported_so_the_form_cannot_skip_the_check(app):
    form, valid = submit(app, base="")

    assert not valid
    assert any("Recarga la página" in error for error in form.base.errors)

    form, valid = submit(app, base=None)

    assert not valid


def test_the_reason_is_optional(app):
    form, valid = submit(app, motivo="")

    assert valid
    assert not form.motivo.data

    form, valid = submit(app, motivo="  Revisión trimestral  ")

    assert valid
    assert form.motivo.data == "Revisión trimestral"


# --- Los valores con que se abre el formulario --------------------------------------------


def test_a_new_policy_form_opens_with_the_suggested_values(app):
    data = policy_form_data(None)

    assert data == {
        "primera_respuesta": "",
        "resolucion": "",
        "umbral_aviso": DEFAULT_WARNING_PERCENT,
        "pausa_en_espera": True,
        "base": NO_POLICY_TOKEN,
    }
    assert DEFAULT_WARNING_PERCENT == 80


def test_an_existing_policy_form_opens_with_its_values_and_its_token(app, seeded_catalogs):
    with app.app_context():
        policy = db.session.scalar(
            db.select(PoliticaSla)
            .join(Prioridad, PoliticaSla.prioridad_id == Prioridad.id)
            .where(Prioridad.codigo == "ALTA")
        )

        assert policy_form_data(policy) == {
            "primera_respuesta": "2 h",
            "resolucion": "6 h",
            "umbral_aviso": 75,
            "pausa_en_espera": True,
            "base": policy_token(policy),
        }

        # Una política sin primera respuesta ni aviso abre esos campos vacíos.
        policy.tiempo_objetivo_respuesta_minutos = None
        policy.umbral_aviso_consumo_porcentaje = None
        policy.pausa_en_espera = False

        data = policy_form_data(policy)

        assert data["primera_respuesta"] == ""
        assert data["umbral_aviso"] is None
        assert data["pausa_en_espera"] is False


def test_what_the_form_opens_with_is_what_it_submits_back_unchanged(app, seeded_catalogs):
    with app.app_context():
        policy = db.session.scalar(
            db.select(PoliticaSla)
            .join(Prioridad, PoliticaSla.prioridad_id == Prioridad.id)
            .where(Prioridad.codigo == "CRITICA")
        )
        data = policy_form_data(policy)

        form, valid = submit(
            app,
            primera_respuesta=data["primera_respuesta"],
            resolucion=data["resolucion"],
            umbral_aviso=str(data["umbral_aviso"]),
            base=data["base"],
        )

        assert valid
        assert form.response_minutes == policy.tiempo_objetivo_respuesta_minutos
        assert form.resolution_minutes == policy.tiempo_objetivo_resolucion_minutos
