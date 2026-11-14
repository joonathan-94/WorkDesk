from datetime import UTC, datetime

from src.workdesk.formatting import local_datetime


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
