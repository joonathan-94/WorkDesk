"""Calendario laboral administrable (docs/09, 21 y 40.8; docs/11, UI-022).

El calendario es global y está versionado: guardar nunca modifica una versión,
crea la siguiente. Mientras no haya ninguna guardada, el sistema usa el
calendario por defecto.
"""

import threading
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import (
    AdminAuditLog,
    CalendarioLaboral,
    Feriado,
    HorarioLaboral,
)
from src.workdesk.sla.forms import (
    MAX_REPORTED_PROBLEMS,
    HolidayErrors,
    format_day,
    format_holidays,
    parse_day,
    parse_holidays,
)
from src.workdesk.sla.work_calendar import (
    MAX_HOLIDAY_NAME_LENGTH,
    MAX_REASON_LENGTH,
    CalendarConflictError,
    CalendarRuleError,
    Holiday,
    NothingToChangeError,
    ScheduleLine,
    available_zone_names,
    clock_for,
    describe_calendar,
    describe_schedule,
    list_calendar_versions,
    resolve_work_calendar,
    save_work_calendar,
    summarize,
)
from src.workdesk.worktime import Franja, parse_time
from tests.ticket_helpers import person

ZONE = ZoneInfo("America/Santiago")


# --- Auxiliares -------------------------------------------------------------


def at(day, hour=0, minute=0):
    """Un momento de noviembre de 2026 en Santiago (lun 16 ... vie 20, sáb 21)."""
    return datetime(2026, 11, day, hour, minute, tzinfo=ZONE)


def franja(day, start, end):
    return Franja(day, parse_time(start), parse_time(end))


def week(start="09:00", end="18:00", days=range(5)):
    """Una franja por día, igual para todos los días indicados."""
    return [franja(day, start, end) for day in days]


@pytest.fixture()
def admin(app, make_user):
    app.config["APP_TIMEZONE"] = "America/Santiago"

    return make_user("ADMINISTRADOR", username="admin")


@pytest.fixture()
def other_admin(make_user, admin):
    return make_user("ADMINISTRADOR", username="otro_admin")


def save(
    actor_id,
    *,
    base_version,
    zone="America/Santiago",
    franjas=None,
    holidays=(),
    reason=None,
):
    """Guarda una versión (como lo haría la ruta, con commit) y devuelve su número."""
    saved = save_work_calendar(
        actor=person(actor_id),
        base_version=base_version,
        zone_name=zone,
        franjas=week() if franjas is None else franjas,
        holidays=holidays,
        reason=reason,
    )
    db.session.commit()

    return saved.version


def audit() -> list[AdminAuditLog]:
    return list(
        db.session.scalars(
            db.select(AdminAuditLog)
            .where(AdminAuditLog.accion == "CALENDARIO_LABORAL_GUARDADO")
            .order_by(AdminAuditLog.id)
        )
    )


def versions() -> list[CalendarioLaboral]:
    return list(
        db.session.scalars(
            db.select(CalendarioLaboral).order_by(CalendarioLaboral.version)
        )
    )


# --- El calendario por defecto ----------------------------------------------------


def test_without_a_saved_calendar_the_default_one_is_used(app, admin):
    with app.app_context():
        resolved = resolve_work_calendar()

        assert resolved.is_default
        assert resolved.record is None
        assert resolved.version == 0
        assert resolved.zone_name == "America/Santiago"
        assert resolved.clock.zone == ZONE
        # Lunes a viernes de 09:00 a 18:00: el miércoles 10:00 se trabaja, a las
        # 18:00 y el sábado no.
        assert resolved.clock.is_working_time(at(18, 10, 0))
        assert not resolved.clock.is_working_time(at(18, 18, 0))
        assert not resolved.clock.is_working_time(at(21, 10, 0))


def test_the_default_calendar_is_described_for_the_screens(app, admin):
    with app.app_context():
        view = describe_calendar(resolve_work_calendar())

        assert view.is_default
        assert view.version == 0
        assert view.zone_name == "America/Santiago"
        assert view.schedule == [ScheduleLine("Lunes a viernes", "09:00–18:00")]
        assert view.summary == "Lunes a viernes 09:00–18:00"
        assert view.holidays == ()
        assert view.saved_by is None
        assert view.saved_at is None
        assert list_calendar_versions() == []


def test_the_default_zone_follows_the_application_zone(app, admin):
    app.config["APP_TIMEZONE"] = "America/Bogota"

    with app.app_context():
        resolved = resolve_work_calendar()

        assert resolved.zone_name == "America/Bogota"
        assert resolved.clock.zone == ZoneInfo("America/Bogota")


# --- Guardar: versiones ---------------------------------------------------------------


def test_the_first_save_creates_version_1_and_becomes_the_current_one(app, admin):
    with app.app_context():
        number = save(
            admin["id"],
            base_version=0,
            zone="America/Bogota",
            franjas=week("08:00", "17:00", days=range(4)),
            holidays=[Holiday(date(2026, 12, 24), "Nochebuena")],
        )

        resolved = resolve_work_calendar()

        assert number == 1
        assert not resolved.is_default
        assert resolved.version == 1
        assert resolved.zone_name == "America/Bogota"
        assert resolved.record.activo is True
        assert resolved.record.usuario_creacion_id == admin["id"]
        assert resolved.record.fecha_creacion is not None
        # Lo guardado manda: el viernes ya no se trabaja y la zona es la guardada.
        bogota = ZoneInfo("America/Bogota")
        monday = datetime(2026, 11, 16, 9, 0, tzinfo=bogota)
        friday = datetime(2026, 11, 20, 9, 0, tzinfo=bogota)

        assert resolved.clock.zone == bogota
        assert resolved.clock.is_working_time(monday)
        assert not resolved.clock.is_working_time(friday)
        # El jueves 24 de diciembre se trabajaría, pero es feriado.
        assert not resolved.clock.is_workday(date(2026, 12, 24))
        assert resolved.clock.is_workday(date(2026, 12, 17))


def test_every_save_creates_a_new_version_and_keeps_the_previous_one(app, admin):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            franjas=week("09:00", "18:00"),
            holidays=[Holiday(date(2026, 12, 25), "Navidad")],
        )
        save(admin["id"], base_version=1, franjas=week("08:00", "17:00"))

        first, second = versions()

        assert (first.version, first.activo) == (1, False)
        assert (second.version, second.activo) == (2, True)
        # La versión 1 quedó exactamente como se guardó.
        assert [(h.dia_semana, h.hora_inicio, h.hora_fin) for h in first.horarios] == [
            (day, time(9, 0), time(18, 0)) for day in range(1, 6)
        ]
        assert [(h.fecha, h.nombre) for h in first.feriados] == [
            (date(2026, 12, 25), "Navidad")
        ]
        assert [(h.hora_inicio, h.hora_fin) for h in second.horarios] == [
            (time(8, 0), time(17, 0))
        ] * 5
        assert second.feriados == []


def test_an_old_version_still_builds_the_clock_it_had(app, admin):
    with app.app_context():
        save(admin["id"], base_version=0, franjas=week("09:00", "18:00"))
        save(admin["id"], base_version=1, franjas=week("08:00", "12:00"))

        first, second = versions()

        # Las 14:00 del miércoles se trabajaban en la versión 1 y ya no en la 2.
        assert clock_for(first).is_working_time(at(18, 14, 0))
        assert not clock_for(second).is_working_time(at(18, 14, 0))
        assert resolve_work_calendar().record.id == second.id


def test_the_franjas_are_stored_with_iso_weekdays(app, admin):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            franjas=[
                franja(0, "09:00", "13:00"),
                franja(0, "14:00", "18:00"),
                franja(6, "10:00", "12:00"),
            ],
        )

        rows = db.session.scalars(
            db.select(HorarioLaboral).order_by(
                HorarioLaboral.dia_semana, HorarioLaboral.hora_inicio
            )
        ).all()

        # El lunes es 1 y el domingo 7 en la base; el motor usa 0 y 6.
        assert [(r.dia_semana, r.hora_inicio, r.hora_fin) for r in rows] == [
            (1, time(9, 0), time(13, 0)),
            (1, time(14, 0), time(18, 0)),
            (7, time(10, 0), time(12, 0)),
        ]

        clock = resolve_work_calendar().clock

        assert clock.is_working_time(at(16, 9, 30))
        assert not clock.is_working_time(at(16, 13, 30))
        assert clock.is_working_time(at(22, 10, 30))


def test_the_default_calendar_can_be_saved_as_is(app, admin):
    """Guardarlo tal cual es una forma legítima de empezar las versiones."""
    with app.app_context():
        assert save(admin["id"], base_version=0) == 1

        resolved = resolve_work_calendar()

        assert not resolved.is_default
        assert resolved.clock.is_working_time(at(18, 10, 0))


def test_the_holidays_are_saved_sorted_and_trimmed(app, admin):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            holidays=[
                Holiday(date(2026, 12, 25), "  Navidad  "),
                Holiday(date(2026, 1, 1), "Año Nuevo"),
            ],
        )

        record = resolve_work_calendar().record

        assert [(h.fecha, h.nombre) for h in record.feriados] == [
            (date(2026, 1, 1), "Año Nuevo"),
            (date(2026, 12, 25), "Navidad"),
        ]


def test_saving_does_not_commit(app, admin):
    with app.app_context():
        save_work_calendar(
            actor=person(admin["id"]),
            base_version=0,
            zone_name="America/Santiago",
            franjas=week(),
            holidays=[],
        )
        db.session.rollback()

        assert versions() == []
        assert audit() == []
        assert resolve_work_calendar().is_default


# --- Guardar: sin cambios, conflicto y reglas --------------------------------------------


def test_saving_the_same_content_creates_nothing(app, admin):
    holidays = [Holiday(date(2026, 12, 25), "Navidad")]

    with app.app_context():
        save(admin["id"], base_version=0, holidays=holidays)

        with pytest.raises(NothingToChangeError):
            save(admin["id"], base_version=1, holidays=holidays)

        db.session.rollback()

        assert [v.version for v in versions()] == [1]
        assert len(audit()) == 1


def test_the_order_of_the_franjas_and_holidays_is_not_a_change(app, admin):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            franjas=[franja(0, "09:00", "13:00"), franja(0, "14:00", "18:00")],
            holidays=[
                Holiday(date(2026, 1, 1), "Año Nuevo"),
                Holiday(date(2026, 12, 25), "Navidad"),
            ],
        )

        with pytest.raises(NothingToChangeError):
            save(
                admin["id"],
                base_version=1,
                franjas=[franja(0, "14:00", "18:00"), franja(0, "09:00", "13:00")],
                holidays=[
                    Holiday(date(2026, 12, 25), "Navidad"),
                    Holiday(date(2026, 1, 1), "Año Nuevo"),
                ],
            )


@pytest.mark.parametrize(
    ("change", "kwargs"),
    [
        ("la zona horaria", {"zone": "America/Bogota"}),
        ("un horario", {"franjas": week("08:00", "18:00")}),
        ("un día más", {"franjas": week(days=range(6))}),
        ("un feriado nuevo", {"holidays": [Holiday(date(2026, 12, 25), "Navidad")]}),
        ("el nombre de un feriado", {"holidays": [Holiday(date(2026, 1, 1), "Otro")]}),
    ],
)
def test_any_difference_is_a_change(app, admin, change, kwargs):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            holidays=[Holiday(date(2026, 1, 1), "Año Nuevo")],
        )
        base = {"holidays": [Holiday(date(2026, 1, 1), "Año Nuevo")]}
        base.update(kwargs)

        assert save(admin["id"], base_version=1, **base) == 2


def test_a_stale_version_is_a_conflict_and_saves_nothing(app, admin, other_admin):
    with app.app_context():
        # Las dos personas abrieron la pantalla cuando no había nada guardado.
        save(admin["id"], base_version=0, franjas=week("08:00", "17:00"))

        with pytest.raises(CalendarConflictError, match="Otra persona guardó"):
            save(other_admin["id"], base_version=0, franjas=week("10:00", "19:00"))

        db.session.rollback()

        assert [v.version for v in versions()] == [1]
        assert len(audit()) == 1

        # Y con la versión 2 de por medio, abrir con la 1 también es obsoleto.
        save(admin["id"], base_version=1, franjas=week("09:00", "18:00"))

        with pytest.raises(CalendarConflictError):
            save(other_admin["id"], base_version=1, franjas=week("10:00", "19:00"))

        db.session.rollback()

        assert [v.version for v in versions()] == [1, 2]


def test_a_base_version_from_the_future_is_a_conflict(app, admin):
    with app.app_context():
        with pytest.raises(CalendarConflictError):
            save(admin["id"], base_version=3)

        db.session.rollback()

        assert versions() == []


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"zone": "Mars/Olympus"}, "no existe"),
        ({"zone": ""}, "no existe"),
        ({"zone": "america/santiago"}, "no existe"),
        ({"zone": "../etc/passwd"}, "no existe"),
        ({"franjas": []}, "al menos un día laboral"),
        (
            {"franjas": [franja(1, "09:00", "13:00"), franja(1, "12:00", "18:00")]},
            "se solapan",
        ),
        ({"franjas": [franja(2, "18:00", "09:00")]}, "anterior a su fin"),
        (
            {
                "holidays": [
                    Holiday(date(2026, 12, 25), "Navidad"),
                    Holiday(date(2026, 12, 25), "Otra"),
                ]
            },
            "está repetido",
        ),
        ({"holidays": [Holiday(date(2026, 12, 25), "   ")]}, "necesitan un nombre"),
        (
            {"holidays": [Holiday(date(2026, 12, 25), "x" * (MAX_HOLIDAY_NAME_LENGTH + 1))]},
            "no puede superar",
        ),
        ({"reason": "x" * (MAX_REASON_LENGTH + 1)}, "motivo no puede superar"),
    ],
)
def test_invalid_data_is_refused_and_saves_nothing(app, admin, kwargs, message):
    with app.app_context():
        with pytest.raises(CalendarRuleError, match=message):
            save(admin["id"], base_version=0, **kwargs)

        db.session.rollback()

        assert versions() == []
        assert audit() == []


def test_the_limits_are_exact(app, admin):
    with app.app_context():
        number = save(
            admin["id"],
            base_version=0,
            holidays=[Holiday(date(2026, 12, 25), "x" * MAX_HOLIDAY_NAME_LENGTH)],
            reason="y" * MAX_REASON_LENGTH,
        )

        assert number == 1


def test_an_inactive_user_cannot_save(app, admin, make_user):
    inactive = make_user("ADMINISTRADOR", username="inactivo", activo=False)

    with app.app_context():
        with pytest.raises(CalendarRuleError, match="no está activo"):
            save(inactive["id"], base_version=0)

        db.session.rollback()

        assert versions() == []


def test_every_zone_name_offered_is_accepted(app, admin):
    with app.app_context():
        names = available_zone_names()

        assert "America/Santiago" in names
        assert "UTC" in names
        assert len(names) > 300


# --- Auditoría -------------------------------------------------------------------------------


def test_the_first_save_is_audited_with_what_changed_from_the_default(app, admin):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            zone="America/Bogota",
            franjas=week("08:00", "17:00", days=range(4)),
            holidays=[Holiday(date(2026, 12, 25), "Navidad")],
            reason="Horario de verano",
        )

        (entry,) = audit()
        version = resolve_work_calendar().record

        assert entry.actor_usuario_id == admin["id"]
        assert entry.entidad_tipo == "calendario_laboral"
        assert entry.entidad_id == version.id
        assert entry.detalle == "Versión 1"
        assert entry.motivo == "Horario de verano"
        assert entry.valor_anterior == {
            "version": None,
            "zona_horaria": "America/Santiago",
            "horario": {
                "lunes": "09:00-18:00",
                "martes": "09:00-18:00",
                "miércoles": "09:00-18:00",
                "jueves": "09:00-18:00",
                "viernes": "09:00-18:00",
            },
            "feriados": [],
        }
        assert entry.valor_nuevo == {
            "version": 1,
            "zona_horaria": "America/Bogota",
            "horario": {
                "lunes": "08:00-17:00",
                "martes": "08:00-17:00",
                "miércoles": "08:00-17:00",
                "jueves": "08:00-17:00",
            },
            "feriados": [{"fecha": "2026-12-25", "nombre": "Navidad"}],
        }


def test_a_later_save_audits_only_the_sections_that_changed(app, admin):
    with app.app_context():
        save(admin["id"], base_version=0)
        save(
            admin["id"],
            base_version=1,
            holidays=[Holiday(date(2026, 12, 25), "Navidad")],
        )

        first, second = audit()

        # La primera guardó el calendario por defecto tal cual: no cambió ninguna
        # sección, solo nace la versión 1.
        assert first.valor_anterior == {"version": None}
        assert first.valor_nuevo == {"version": 1}
        assert second.valor_anterior == {"version": 1, "feriados": []}
        assert second.valor_nuevo == {
            "version": 2,
            "feriados": [{"fecha": "2026-12-25", "nombre": "Navidad"}],
        }
        assert second.motivo is None


def test_the_audit_records_the_lunch_break_as_one_text_per_day(app, admin):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            franjas=[franja(0, "09:00", "13:00"), franja(0, "14:00", "18:00")],
        )

        (entry,) = audit()

        assert entry.valor_nuevo["horario"] == {"lunes": "09:00-13:00, 14:00-18:00"}


# --- Descripciones --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("franjas", "expected"),
    [
        (week(), [ScheduleLine("Lunes a viernes", "09:00–18:00")]),
        (
            week(days=range(4)) + [franja(4, "09:00", "17:00")],
            [
                ScheduleLine("Lunes a jueves", "09:00–18:00"),
                ScheduleLine("Viernes", "09:00–17:00"),
            ],
        ),
        (week(days=range(2)), [ScheduleLine("Lunes y martes", "09:00–18:00")]),
        (week(days=[2]), [ScheduleLine("Miércoles", "09:00–18:00")]),
        (
            # Los días que comparten horas pero no son seguidos van por separado.
            week(days=[0, 2]),
            [ScheduleLine("Lunes", "09:00–18:00"), ScheduleLine("Miércoles", "09:00–18:00")],
        ),
        (
            [franja(0, "09:00", "13:00"), franja(0, "14:00", "18:00"), franja(1, "09:00", "13:00"), franja(1, "14:00", "18:00")],
            [ScheduleLine("Lunes y martes", "09:00–13:00 y 14:00–18:00")],
        ),
        (week(days=[5, 6]), [ScheduleLine("Sábado y domingo", "09:00–18:00")]),
        ([], []),
    ],
)
def test_the_schedule_is_summarized_by_runs_of_days(franjas, expected):
    assert describe_schedule(franjas) == expected


def test_the_summary_is_one_line(app):
    lines = describe_schedule(week(days=range(4)) + [franja(4, "09:00", "17:00")])

    assert summarize(lines) == "Lunes a jueves 09:00–18:00 · Viernes 09:00–17:00"
    assert summarize([]) == "Sin días laborales"


def test_the_versions_are_listed_newest_first_with_their_summary(app, admin):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            holidays=[Holiday(date(2026, 1, 1), "Año Nuevo"), Holiday(date(2026, 12, 25), "Navidad")],
        )
        save(admin["id"], base_version=1, franjas=week("08:00", "17:00"))

        second, first = list_calendar_versions()

        assert (second.record.version, first.record.version) == (2, 1)
        assert second.summary == "Lunes a viernes 08:00–17:00"
        assert first.summary == "Lunes a viernes 09:00–18:00"
        assert (second.holiday_count, first.holiday_count) == (0, 2)


def test_listing_the_versions_does_not_query_per_version(app, admin):
    with app.app_context():
        save(admin["id"], base_version=0, holidays=[Holiday(date(2026, 1, 1), "Año Nuevo")])

        for number in range(1, 6):
            save(
                admin["id"],
                base_version=number,
                franjas=week(f"0{number}:00", "18:00"),
            )

        queries = []

        def count(conn, cursor, statement, *args):
            queries.append(statement)

        event.listen(db.engine, "before_cursor_execute", count)

        try:
            rows = list_calendar_versions()
            # Tocar lo que muestra la pantalla no debe lanzar más consultas.
            shown = [
                (item.record.creado_por, len(item.record.feriados), item.summary)
                for item in rows
            ]
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

        assert len(rows) == len(shown) == 6
        # La lista con quienes las guardaron, las franjas y los feriados: tres.
        assert len(queries) <= 3


def test_the_saved_calendar_is_described_for_the_screens(app, admin):
    with app.app_context():
        save(
            admin["id"],
            base_version=0,
            holidays=[Holiday(date(2026, 12, 25), "Navidad")],
        )

        view = describe_calendar(resolve_work_calendar())

        assert not view.is_default
        assert view.version == 1
        assert view.holidays == (Holiday(date(2026, 12, 25), "Navidad"),)
        assert view.saved_by.username == "admin"
        assert view.saved_at is not None


# --- Restricciones de la base de datos ----------------------------------------------------


def _version(number=1, **values):
    values.setdefault("zona_horaria", "America/Santiago")

    return CalendarioLaboral(version=number, **values)


def test_only_one_version_can_be_current(app):
    with app.app_context():
        db.session.add(_version(1))
        db.session.commit()
        db.session.add(_version(2))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()

        # Las versiones históricas, en cambio, pueden ser tantas como haga falta.
        db.session.add(_version(2, activo=False))
        db.session.add(_version(3, activo=False))
        db.session.commit()

        assert [(v.version, v.activo) for v in versions()] == [
            (1, True),
            (2, False),
            (3, False),
        ]


def test_the_version_number_is_unique_and_positive(app):
    with app.app_context():
        db.session.add(_version(1, activo=False))
        db.session.commit()
        db.session.add(_version(1, activo=False))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()
        db.session.add(_version(0))

        with pytest.raises(IntegrityError):
            db.session.flush()


@pytest.mark.parametrize("weekday", [0, 8, -1])
def test_a_franja_needs_a_weekday_from_1_to_7(app, weekday):
    with app.app_context():
        calendar = _version()
        calendar.horarios = [
            HorarioLaboral(dia_semana=weekday, hora_inicio=time(9), hora_fin=time(18))
        ]
        db.session.add(calendar)

        with pytest.raises(IntegrityError):
            db.session.flush()


@pytest.mark.parametrize(("start", "end"), [(time(18), time(9)), (time(9), time(9))])
def test_a_franja_starts_before_it_ends(app, start, end):
    with app.app_context():
        calendar = _version()
        calendar.horarios = [HorarioLaboral(dia_semana=1, hora_inicio=start, hora_fin=end)]
        db.session.add(calendar)

        with pytest.raises(IntegrityError):
            db.session.flush()


def test_a_version_cannot_repeat_a_franja_start_or_a_holiday(app):
    with app.app_context():
        calendar = _version()
        calendar.horarios = [
            HorarioLaboral(dia_semana=1, hora_inicio=time(9), hora_fin=time(13)),
            HorarioLaboral(dia_semana=1, hora_inicio=time(9), hora_fin=time(18)),
        ]
        db.session.add(calendar)

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()
        calendar = _version()
        calendar.feriados = [
            Feriado(fecha=date(2026, 12, 25), nombre="Navidad"),
            Feriado(fecha=date(2026, 12, 25), nombre="Otra"),
        ]
        db.session.add(calendar)

        with pytest.raises(IntegrityError):
            db.session.flush()


def test_two_versions_can_share_franjas_and_holidays(app):
    with app.app_context():
        for number in (1, 2):
            calendar = _version(number, activo=number == 2)
            calendar.horarios = [
                HorarioLaboral(dia_semana=1, hora_inicio=time(9), hora_fin=time(18))
            ]
            calendar.feriados = [Feriado(fecha=date(2026, 12, 25), nombre="Navidad")]
            db.session.add(calendar)

        db.session.commit()

        assert db.session.scalar(db.select(db.func.count(HorarioLaboral.id))) == 2
        assert db.session.scalar(db.select(db.func.count(Feriado.id))) == 2


def test_a_holiday_needs_a_name(app):
    with app.app_context():
        calendar = _version()
        calendar.feriados = [Feriado(fecha=date(2026, 12, 25), nombre="   ")]
        db.session.add(calendar)

        with pytest.raises(IntegrityError):
            db.session.flush()


def test_a_version_with_rows_cannot_be_deleted(app):
    """Las versiones no se eliminan: lo que cuelga de ellas lo impide."""
    with app.app_context():
        calendar = _version()
        calendar.horarios = [
            HorarioLaboral(dia_semana=1, hora_inicio=time(9), hora_fin=time(18))
        ]
        db.session.add(calendar)
        db.session.commit()

        with pytest.raises(IntegrityError):
            db.session.execute(db.text("DELETE FROM calendarios_laborales"))


# --- Los textos del formulario: franjas de un día ------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("09:00-18:00", [(time(9), time(18))]),
        ("9:00 - 18:00", [(time(9), time(18))]),
        ("09:00–18:00", [(time(9), time(18))]),  # con raya
        ("09:00-13:00, 14:00-18:00", [(time(9), time(13)), (time(14), time(18))]),
        ("14:00-18:00; 09:00-13:00", [(time(9), time(13)), (time(14), time(18))]),
        ("09:00-13:00,13:00-18:00", [(time(9), time(13)), (time(13), time(18))]),
        ("00:00-23:59", [(time(0), time(23, 59))]),
        ("", []),
        ("   ", []),
        (None, []),
        ("09:00-18:00,", [(time(9), time(18))]),
    ],
)
def test_a_day_text_is_parsed_into_ordered_franjas(text, expected):
    assert parse_day(text) == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("abc", "no tiene el formato HH:MM-HH:MM"),
        ("09:00", "no tiene el formato"),
        ("09:00-", "no tiene el formato"),
        ("09-18", "no tiene el formato"),
        ("09:00-18:00-20:00", "no tiene el formato"),
        ("09:00-25:00", "hora que no existe"),
        ("09:60-18:00", "hora que no existe"),
        ("18:00-09:00", "el inicio debe ser anterior al fin"),
        ("09:00-09:00", "el inicio debe ser anterior al fin"),
        ("09:00-13:00, 12:00-18:00", "se solapan"),
        ("09:00-18:00, 10:00-11:00", "se solapan"),
    ],
)
def test_a_badly_written_day_says_what_is_wrong(text, message):
    with pytest.raises(ValueError, match=message):
        parse_day(text)


def test_a_day_text_roundtrips():
    slots = [(time(9), time(13)), (time(14), time(18, 30))]

    assert format_day(slots) == "09:00-13:00, 14:00-18:30"
    assert parse_day(format_day(slots)) == slots
    assert format_day([]) == ""
    # Se escribe en orden aunque lleguen desordenadas.
    assert format_day(reversed(slots)) == "09:00-13:00, 14:00-18:30"


# --- Los textos del formulario: feriados ------------------------------------------------------------


def test_the_holidays_are_parsed_one_per_line():
    text = """
    25-12-2026 Navidad
    1/1/2027 Año Nuevo
    2026-09-18 Fiestas Patrias   del Bicentenario

    """

    assert parse_holidays(text) == [
        Holiday(date(2026, 12, 25), "Navidad"),
        Holiday(date(2027, 1, 1), "Año Nuevo"),
        Holiday(date(2026, 9, 18), "Fiestas Patrias   del Bicentenario"),
    ]
    assert parse_holidays("") == []
    assert parse_holidays(None) == []


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("mañana Navidad", "Línea 1: «mañana» no es una fecha válida"),
        ("31-02-2026 Febrero", "Línea 1: «31-02-2026» no es una fecha válida"),
        ("25-12-26 Navidad", "Línea 1: «25-12-26» no es una fecha válida"),
        ("25-12-1999 Antiguo", "el año debe estar entre 2000 y 2100"),
        ("25-12-2101 Futuro", "el año debe estar entre 2000 y 2100"),
        ("25-12-2026", "Línea 1: falta el nombre del feriado"),
        (f"25-12-2026 {'x' * 101}", "el nombre no puede superar los 100 caracteres"),
        ("25-12-2026 Navidad\n25-12-2026 Otra", "Línea 2: el 25-12-2026 ya está en la línea 1"),
        ("\n\n25-12-2026", "Línea 3: falta el nombre"),
    ],
)
def test_a_badly_written_holiday_says_which_line_and_why(text, message):
    with pytest.raises(HolidayErrors) as error:
        parse_holidays(text)

    assert any(message in line for line in error.value.messages)


def test_all_the_problems_are_reported_but_not_too_many():
    text = "\n".join(f"mal{number} Nombre" for number in range(MAX_REPORTED_PROBLEMS + 4))

    with pytest.raises(HolidayErrors) as error:
        parse_holidays(text)

    assert len(error.value.messages) == MAX_REPORTED_PROBLEMS + 1
    assert error.value.messages[-1] == "Y 4 líneas más con problemas."


def test_the_holidays_text_roundtrips_in_date_order():
    holidays = [
        Holiday(date(2026, 12, 25), "Navidad"),
        Holiday(date(2026, 1, 1), "Año Nuevo"),
    ]
    text = format_holidays(holidays)

    assert text == "01-01-2026 Año Nuevo\n25-12-2026 Navidad"
    assert parse_holidays(text) == sorted(holidays, key=lambda item: item.fecha)


# --- Carreras: dos Administradores guardan a la vez ------------------------------------------------------


def _save_at_the_same_time(app, attempts):
    """Cada intento se ejecuta en su hilo y todos arrancan juntos."""
    barrier = threading.Barrier(len(attempts))
    outcomes = []

    def run(user_id, changes):
        with app.app_context():
            actor = person(user_id)
            barrier.wait(timeout=10)

            try:
                save_work_calendar(actor=actor, **changes)
                db.session.commit()
                outcomes.append("guardó")
            except CalendarConflictError:
                db.session.rollback()
                outcomes.append("conflicto")
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run, args=attempt) for attempt in attempts]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=30)

    return sorted(outcomes)


def _changes(base_version, start):
    return {
        "base_version": base_version,
        "zone_name": "America/Santiago",
        "franjas": week(start, "18:00"),
        "holidays": [],
    }


def test_two_administrators_saving_the_first_calendar_at_once_leave_one_version(
    app, admin, other_admin
):
    outcomes = _save_at_the_same_time(
        app,
        [
            (admin["id"], _changes(0, "08:00")),
            (other_admin["id"], _changes(0, "10:00")),
        ],
    )

    assert outcomes == ["conflicto", "guardó"]

    with app.app_context():
        assert [(v.version, v.activo) for v in versions()] == [(1, True)]
        assert len(audit()) == 1


def test_two_administrators_saving_over_the_same_version_leave_one_new_version(
    app, admin, other_admin
):
    with app.app_context():
        save(admin["id"], base_version=0)

    outcomes = _save_at_the_same_time(
        app,
        [
            (admin["id"], _changes(1, "08:00")),
            (other_admin["id"], _changes(1, "10:00")),
        ],
    )

    assert outcomes == ["conflicto", "guardó"]

    with app.app_context():
        assert [(v.version, v.activo) for v in versions()] == [(1, False), (2, True)]
        assert len(audit()) == 2
