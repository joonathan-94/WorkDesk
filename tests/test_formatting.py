from datetime import UTC, datetime

import pytest

from src.workdesk.formatting import format_duration, format_size, local_datetime


def test_a_missing_date_is_shown_as_a_dash(app):
    with app.app_context():
        assert local_datetime(None) == "—"


def test_the_date_is_shown_in_the_configured_timezone(app):
    app.config["APP_TIMEZONE"] = "America/Santiago"

    with app.app_context():
        # Chile está en UTC-3 en verano y en UTC-4 en invierno.
        summer = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        winter = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)

        assert local_datetime(summer) == "15-01-2026 09:00"
        assert local_datetime(winter) == "15-07-2026 08:00"


def test_a_date_without_timezone_is_treated_as_utc(app):
    app.config["APP_TIMEZONE"] = "America/Santiago"

    with app.app_context():
        # Sin zona horaria a propósito: es el caso que se prueba.
        naive = datetime(2026, 1, 15, 12, 0)  # noqa: DTZ001

        assert local_datetime(naive) == "15-01-2026 09:00"


def test_an_unknown_timezone_falls_back_to_utc(app):
    app.config["APP_TIMEZONE"] = "Nowhere/Land"

    with app.app_context():
        moment = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)

        assert local_datetime(moment) == "15-01-2026 12:00"


def test_the_filter_is_available_in_templates(app):
    app.config["APP_TIMEZONE"] = "America/Santiago"

    with app.test_request_context():
        template = app.jinja_env.from_string(
            "{{ value|local_datetime }}"
        )

        assert template.render(
            value=datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
        ) == "15-01-2026 09:00"


# --- Duraciones -----------------------------------------------------------


@pytest.mark.parametrize(
    ("minutes", "text"),
    [
        (0, "0 min"),
        (1, "1 min"),
        (30, "30 min"),
        (59, "59 min"),
        (60, "1 h"),
        (61, "1 h 1 min"),
        (90, "1 h 30 min"),
        (240, "4 h"),
        (1440, "24 h"),
        (1441, "24 h 1 min"),
        # Sin días: en tiempo laboral un día dura distinto según el calendario.
        (60000, "1000 h"),
    ],
)
def test_a_duration_is_shown_as_a_person_would_say_it(minutes, text):
    assert format_duration(minutes) == text


def test_a_missing_duration_is_shown_as_a_dash():
    assert format_duration(None) == "—"


def test_a_negative_duration_is_a_bug_not_something_to_show():
    with pytest.raises(ValueError, match="negativa"):
        format_duration(-1)


def test_the_duration_filter_is_available_in_templates(app):
    with app.test_request_context():
        template = app.jinja_env.from_string("{{ value|duration }}")

        assert template.render(value=90) == "1 h 30 min"
        assert template.render(value=None) == "—"


# --- Tamaño de un archivo (`filesize`) ------------------------------------------------


@pytest.mark.parametrize(
    ("size", "text"),
    [
        (0, "1 KB"),
        (10, "1 KB"),
        (1024, "1 KB"),
        (1025, "2 KB"),
        (500 * 1024, "500 KB"),
        (1024 * 1024 - 1, "1024 KB"),
        (1024 * 1024, "1 MB"),
        (1536 * 1024, "1,5 MB"),
        # Un límite nunca aparenta ser mayor: 1,99 MB es «1,9 MB».
        (2 * 1024 * 1024 - 1, "1,9 MB"),
        (10 * 1024 * 1024, "10 MB"),
    ],
)
def test_a_size_is_shown_as_a_person_reads_it(size, text):
    assert format_size(size) == text
