import pytest
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.models import (
    Categoria,
    Estado,
    MotivoCierre,
    Prioridad,
    Ubicacion,
)
from src.workdesk.models.categoria import FALLBACK_CATEGORY_CODE
from src.workdesk.seeds import seed_catalogs


def _codes(model):
    return set(db.session.scalars(db.select(model.codigo)))


# --- Datos iniciales -------------------------------------------------------


def test_seed_creates_the_six_structural_states_in_order(app):
    with app.app_context():
        seed_catalogs()

        states = db.session.scalars(db.select(Estado).order_by(Estado.orden))

        assert [state.codigo for state in states] == [
            "NUEVO",
            "ASIGNADO",
            "EN_PROGRESO",
            "EN_ESPERA",
            "RESUELTO",
            "CERRADO",
        ]


def test_seed_creates_the_base_priorities_with_increasing_level(app):
    with app.app_context():
        seed_catalogs()

        priorities = db.session.scalars(
            db.select(Prioridad).order_by(Prioridad.nivel)
        ).all()

        assert [p.nombre for p in priorities] == [
            "Baja",
            "Media",
            "Alta",
            "Crítica",
        ]
        assert [p.nivel for p in priorities] == [1, 2, 3, 4]
        assert all(p.activo for p in priorities)


def test_seed_creates_the_fallback_category(app):
    with app.app_context():
        seed_catalogs()

        category = db.session.scalar(
            db.select(Categoria).where(
                Categoria.codigo == FALLBACK_CATEGORY_CODE
            )
        )

        assert category is not None
        assert category.nombre == "Sin clasificar"
        assert category.activo is True


def test_seed_creates_the_base_close_reasons(app):
    with app.app_context():
        seed_catalogs()

        assert _codes(MotivoCierre) == {
            "RESOLUCION_VALIDADA",
            "CIERRE_DIRECTO",
            "INACTIVIDAD",
            "DUPLICADO",
            "CANCELACION",
            "CIERRE_EXCEPCIONAL",
        }


def test_seed_does_not_create_locations(app):
    with app.app_context():
        seed_catalogs()

        assert db.session.scalar(db.select(db.func.count(Ubicacion.id))) == 0


def test_seed_reports_what_it_created_and_is_idempotent(app):
    with app.app_context():
        first = seed_catalogs()
        second = seed_catalogs()

        assert first == {
            "estados": 6,
            "prioridades": 4,
            "categorias": 1,
            "motivos_cierre": 6,
        }
        assert second == {
            "estados": 0,
            "prioridades": 0,
            "categorias": 0,
            "motivos_cierre": 0,
        }
        assert db.session.scalar(db.select(db.func.count(Estado.id))) == 6


def test_seed_does_not_overwrite_changes_made_by_an_administrator(app):
    with app.app_context():
        seed_catalogs()

        priority = db.session.scalar(
            db.select(Prioridad).where(Prioridad.codigo == "MEDIA")
        )
        priority.nombre = "Normal"
        priority.activo = False
        db.session.commit()

        seed_catalogs()

        priority = db.session.scalar(
            db.select(Prioridad).where(Prioridad.codigo == "MEDIA")
        )
        assert priority.nombre == "Normal"
        assert priority.activo is False


# --- Restricciones de la base de datos -------------------------------------


def test_state_code_is_unique(app):
    with app.app_context():
        db.session.add(Estado(codigo="NUEVO", nombre_visible="A", orden=1))
        db.session.commit()

        db.session.add(Estado(codigo="NUEVO", nombre_visible="B", orden=2))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_priority_level_must_be_positive(app):
    with app.app_context():
        db.session.add(Prioridad(codigo="X", nombre="X", nivel=0))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_two_active_priorities_cannot_share_a_level(app):
    with app.app_context():
        db.session.add(Prioridad(codigo="A", nombre="A", nivel=1))
        db.session.commit()

        db.session.add(Prioridad(codigo="B", nombre="B", nivel=1))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_an_inactive_priority_can_share_a_level(app):
    with app.app_context():
        db.session.add(Prioridad(codigo="A", nombre="A", nivel=1, activo=False))
        db.session.add(Prioridad(codigo="B", nombre="B", nivel=1))
        db.session.commit()

        assert db.session.scalar(db.select(db.func.count(Prioridad.id))) == 2


def test_category_name_is_unique_ignoring_case(app):
    with app.app_context():
        db.session.add(Categoria(nombre="Redes"))
        db.session.commit()

        db.session.add(Categoria(nombre="redes"))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_category_code_is_optional_but_unique_when_present(app):
    with app.app_context():
        db.session.add(Categoria(nombre="Una"))
        db.session.add(Categoria(nombre="Otra"))
        db.session.add(Categoria(codigo="COD", nombre="Con código"))
        db.session.commit()

        db.session.add(Categoria(codigo="COD", nombre="Repetida"))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_close_reason_code_is_required_and_unique(app):
    with app.app_context():
        db.session.add(MotivoCierre(codigo="X", nombre="X"))
        db.session.commit()

        db.session.add(MotivoCierre(codigo="X", nombre="Otro"))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_catalog_audit_columns_have_sensible_defaults(app):
    with app.app_context():
        location = Ubicacion(nombre="Oficina central", tipo="OFICINA")
        db.session.add(location)
        db.session.commit()

        assert location.activo is True
        assert location.fecha_creacion is not None
        assert location.usuario_creacion_id is None
        assert location.fecha_modificacion is None


# --- Comando CLI -----------------------------------------------------------


def test_seed_catalogs_command_loads_the_catalogs(app):
    runner = app.test_cli_runner()

    result = runner.invoke(args=["seed-catalogs"])

    assert result.exit_code == 0
    assert "Estados: 6" in result.output
    assert "prioridades: 4" in result.output

    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Estado.id))) == 6


def test_seed_catalogs_command_is_idempotent(app):
    runner = app.test_cli_runner()

    runner.invoke(args=["seed-catalogs"])
    result = runner.invoke(args=["seed-catalogs"])

    assert result.exit_code == 0
    assert "Estados: 0" in result.output
