import pytest

from src.workdesk.catalogs import service
from src.workdesk.catalogs.service import (
    ActivationConflictError,
    CatalogRuleError,
    DuplicateNameError,
    LastActivePriorityError,
    NothingToChangeError,
    ProtectedItemError,
    activate_item,
    create_category,
    create_location,
    deactivate_item,
    deactivation_blocker,
    list_categories,
    list_locations,
    list_priorities,
    update_category,
    update_location,
    update_priority,
)
from src.workdesk.extensions import db
from src.workdesk.models import (
    AdminAuditLog,
    Categoria,
    Prioridad,
    Ubicacion,
    User,
)
from src.workdesk.tickets.service import TicketRuleError, create_ticket


@pytest.fixture()
def admin_id(make_user, seeded_roles, seeded_catalogs):
    return make_user("ADMINISTRADOR")["id"]


def admin(admin_id) -> User:
    return db.session.get(User, admin_id)


def by_code(model, code):
    return db.session.scalar(db.select(model).where(model.codigo == code))


def audit_entries() -> list[AdminAuditLog]:
    return list(
        db.session.scalars(db.select(AdminAuditLog).order_by(AdminAuditLog.id))
    )


def names(items) -> list[str]:
    return [item.nombre for item in items]


# --- Categorías: alta -------------------------------------------------


def test_create_category_saves_the_data_and_the_creator(app, admin_id):
    with app.app_context():
        category = create_category(
            actor=admin(admin_id),
            nombre="  Redes  ",
            descripcion="  Conectividad y VPN  ",
            orden=5,
        )
        db.session.commit()

        assert category.id is not None
        assert category.nombre == "Redes"
        assert category.descripcion == "Conectividad y VPN"
        assert category.orden == 5
        assert category.activo is True
        assert category.usuario_creacion_id == admin_id
        # Las creadas desde la interfaz no llevan código: es solo del seed.
        assert category.codigo is None


def test_create_category_stores_a_blank_description_as_null(app, admin_id):
    with app.app_context():
        category = create_category(
            actor=admin(admin_id),
            nombre="Correo",
            descripcion="   ",
        )

        assert category.descripcion is None
        assert category.orden is None


def test_create_category_audits_the_creation(app, admin_id):
    with app.app_context():
        category = create_category(
            actor=admin(admin_id),
            nombre="Hardware",
            orden=2,
        )
        db.session.commit()

        (entry,) = audit_entries()

        assert entry.accion == "CATALOGO_CREADO"
        assert entry.actor_usuario_id == admin_id
        assert entry.entidad_tipo == "categoria"
        assert entry.entidad_id == category.id
        assert entry.detalle == "Hardware"
        assert entry.valor_nuevo == {
            "nombre": "Hardware",
            "descripcion": None,
            "orden": 2,
            "activo": True,
        }


def test_create_does_not_commit(app, admin_id):
    with app.app_context():
        create_category(actor=admin(admin_id), nombre="Temporal")
        db.session.rollback()

        assert (
            db.session.scalar(
                db.select(Categoria).where(Categoria.nombre == "Temporal")
            )
            is None
        )
        assert audit_entries() == []


@pytest.mark.parametrize("name", ["", "   "])
def test_create_requires_a_name(app, admin_id, name):
    with app.app_context(), pytest.raises(CatalogRuleError):
        create_category(actor=admin(admin_id), nombre=name)


@pytest.mark.parametrize("name", ["Sin clasificar", "SIN CLASIFICAR", " sin clasificar "])
def test_create_rejects_a_name_that_exists_ignoring_case(app, admin_id, name):
    with app.app_context():
        with pytest.raises(DuplicateNameError):
            create_category(actor=admin(admin_id), nombre=name)

        assert audit_entries() == []


def test_create_recovers_from_a_name_race(app, admin_id, monkeypatch):
    """Si dos altas pasan la comprobación, gana el índice único."""
    with app.app_context():
        monkeypatch.setattr(
            service,
            "_ensure_name_available",
            lambda model, nombre, *, exclude_id=None: None,
        )

        with pytest.raises(DuplicateNameError):
            create_category(actor=admin(admin_id), nombre="Sin clasificar")

        # La sesión sigue siendo utilizable y no quedó auditoría.
        monkeypatch.undo()
        db.session.rollback()

        assert audit_entries() == []


# --- Categorías: edición ----------------------------------------------


def test_update_category_changes_only_what_was_modified(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        category = create_category(
            actor=actor,
            nombre="Redes",
            descripcion="Antigua",
            orden=3,
        )
        db.session.commit()

        changed = update_category(
            category,
            actor=actor,
            nombre="Redes",
            descripcion="Nueva",
            orden=3,
        )
        db.session.commit()

        assert changed is True
        assert category.descripcion == "Nueva"
        assert category.usuario_modificacion_id == admin_id
        assert category.fecha_modificacion is not None

        entry = audit_entries()[-1]

        assert entry.accion == "CATALOGO_MODIFICADO"
        assert entry.entidad_tipo == "categoria"
        assert entry.valor_anterior == {"descripcion": "Antigua"}
        assert entry.valor_nuevo == {"descripcion": "Nueva"}


def test_update_category_without_changes_does_nothing(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        category = create_category(actor=actor, nombre="Redes", orden=1)
        db.session.commit()
        entries_before = len(audit_entries())

        changed = update_category(
            category,
            actor=actor,
            nombre=" Redes ",
            descripcion="",
            orden=1,
        )

        assert changed is False
        assert category.fecha_modificacion is None
        assert len(audit_entries()) == entries_before


def test_update_category_can_clear_the_order(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        category = create_category(actor=actor, nombre="Redes", orden=0)
        db.session.commit()

        update_category(
            category,
            actor=actor,
            nombre="Redes",
            descripcion=None,
            orden=None,
        )

        assert category.orden is None


def test_update_category_rejects_the_name_of_another_one(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        create_category(actor=actor, nombre="Redes")
        other = create_category(actor=actor, nombre="Correo")
        db.session.commit()
        entries_before = len(audit_entries())

        with pytest.raises(DuplicateNameError):
            update_category(
                other,
                actor=actor,
                nombre="REDES",
                descripcion=None,
                orden=None,
            )

        db.session.rollback()

        assert len(audit_entries()) == entries_before


def test_update_category_allows_changing_only_the_case_of_its_own_name(
    app,
    admin_id,
):
    with app.app_context():
        actor = admin(admin_id)
        category = create_category(actor=actor, nombre="redes")
        db.session.commit()

        changed = update_category(
            category,
            actor=actor,
            nombre="Redes",
            descripcion=None,
            orden=None,
        )

        assert changed is True
        assert category.nombre == "Redes"


def test_the_fallback_category_can_be_renamed_but_keeps_its_code(app, admin_id):
    with app.app_context():
        fallback = by_code(Categoria, "SIN_CLASIFICAR")

        update_category(
            fallback,
            actor=admin(admin_id),
            nombre="Otros",
            descripcion=fallback.descripcion,
            orden=fallback.orden,
        )
        db.session.commit()

        assert by_code(Categoria, "SIN_CLASIFICAR").nombre == "Otros"


# --- Prioridades ------------------------------------------------------


def test_update_priority_changes_name_and_description_only(app, admin_id):
    with app.app_context():
        medium = by_code(Prioridad, "MEDIA")
        level, color = medium.nivel, medium.color

        changed = update_priority(
            medium,
            actor=admin(admin_id),
            nombre="Normal",
            descripcion="Lo habitual.",
        )
        db.session.commit()

        assert changed is True
        assert medium.nombre == "Normal"
        assert medium.descripcion == "Lo habitual."
        assert (medium.nivel, medium.color) == (level, color)

        entry = audit_entries()[-1]

        assert entry.entidad_tipo == "prioridad"
        assert entry.valor_anterior["nombre"] == "Media"
        assert entry.valor_nuevo["nombre"] == "Normal"


def test_update_priority_rejects_the_name_of_another_one(app, admin_id):
    with app.app_context(), pytest.raises(DuplicateNameError):
        update_priority(
            by_code(Prioridad, "MEDIA"),
            actor=admin(admin_id),
            nombre="alta",
            descripcion=None,
        )


# --- Ubicaciones ------------------------------------------------------


def test_create_location_with_a_type(app, admin_id):
    with app.app_context():
        location = create_location(
            actor=admin(admin_id),
            nombre="Casa matriz",
            descripcion="Santiago centro",
            tipo="SUCURSAL",
        )
        db.session.commit()

        assert location.tipo == "SUCURSAL"
        assert location.tipo_nombre == "Sucursal"
        assert location.usuario_creacion_id == admin_id

        (entry,) = audit_entries()

        assert entry.accion == "CATALOGO_CREADO"
        assert entry.entidad_tipo == "ubicacion"
        assert entry.valor_nuevo["tipo"] == "SUCURSAL"


def test_create_location_without_a_type(app, admin_id):
    with app.app_context():
        location = create_location(
            actor=admin(admin_id),
            nombre="Bodega",
            tipo="  ",
        )

        assert location.tipo is None
        assert location.tipo_nombre is None


def test_create_location_rejects_an_unknown_type(app, admin_id):
    with app.app_context():
        with pytest.raises(CatalogRuleError):
            create_location(
                actor=admin(admin_id),
                nombre="Bodega",
                tipo="CASTILLO",
            )

        assert audit_entries() == []


def test_create_location_rejects_a_repeated_name(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        create_location(actor=actor, nombre="Piso 2")

        with pytest.raises(DuplicateNameError):
            create_location(actor=actor, nombre="piso 2")


def test_update_location_changes_the_type(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        location = create_location(
            actor=actor,
            nombre="Piso 2",
            tipo="PISO",
        )
        db.session.commit()

        update_location(
            location,
            actor=actor,
            nombre="Piso 2",
            descripcion=None,
            tipo="AREA",
        )

        entry = audit_entries()[-1]

        assert location.tipo_nombre == "Área"
        assert entry.valor_anterior == {"tipo": "PISO"}
        assert entry.valor_nuevo == {"tipo": "AREA"}


def test_an_unknown_stored_type_is_shown_as_is(app, admin_id):
    with app.app_context():
        location = Ubicacion(nombre="Antigua", tipo="HISTORICO")

        assert location.tipo_nombre == "HISTORICO"


# --- Desactivar y reactivar -------------------------------------------


def test_deactivate_marks_the_item_inactive_and_audits_it(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        category = create_category(actor=actor, nombre="Redes")
        db.session.commit()

        deactivate_item(category, actor=actor, reason="  Ya no se usa  ")
        db.session.commit()

        assert category.activo is False
        assert category.usuario_modificacion_id == admin_id
        assert category.fecha_modificacion is not None

        entry = audit_entries()[-1]

        assert entry.accion == "CATALOGO_DESACTIVADO"
        assert entry.entidad_tipo == "categoria"
        assert entry.entidad_id == category.id
        assert entry.detalle == "Redes"
        assert entry.valor_anterior == {"activo": True}
        assert entry.valor_nuevo == {"activo": False}
        assert entry.motivo == "Ya no se usa"


def test_the_reason_is_optional(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        location = create_location(actor=actor, nombre="Bodega")
        db.session.commit()

        deactivate_item(location, actor=actor, reason="   ")

        assert audit_entries()[-1].motivo is None


def test_deactivating_an_inactive_item_does_nothing(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        location = create_location(actor=actor, nombre="Bodega")
        deactivate_item(location, actor=actor)
        db.session.commit()
        entries_before = len(audit_entries())

        with pytest.raises(NothingToChangeError):
            deactivate_item(location, actor=actor)

        assert len(audit_entries()) == entries_before


def test_activate_restores_the_item_and_audits_it(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        location = create_location(actor=actor, nombre="Bodega")
        deactivate_item(location, actor=actor)
        db.session.commit()

        activate_item(location, actor=actor, reason="Se reabrió")
        db.session.commit()

        assert location.activo is True

        entry = audit_entries()[-1]

        assert entry.accion == "CATALOGO_ACTIVADO"
        assert entry.valor_anterior == {"activo": False}
        assert entry.valor_nuevo == {"activo": True}
        assert entry.motivo == "Se reabrió"


def test_activating_an_active_item_does_nothing(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        location = create_location(actor=actor, nombre="Bodega")
        db.session.commit()

        with pytest.raises(NothingToChangeError):
            activate_item(location, actor=actor)


def test_the_fallback_category_cannot_be_deactivated(app, admin_id):
    with app.app_context():
        fallback = by_code(Categoria, "SIN_CLASIFICAR")

        with pytest.raises(ProtectedItemError):
            deactivate_item(fallback, actor=admin(admin_id))

        db.session.rollback()

        assert by_code(Categoria, "SIN_CLASIFICAR").activo is True
        assert audit_entries() == []


def test_a_priority_can_be_deactivated_while_others_remain_active(
    app,
    admin_id,
):
    with app.app_context():
        low = by_code(Prioridad, "BAJA")

        deactivate_item(low, actor=admin(admin_id))
        db.session.commit()

        assert low.activo is False
        assert len(list_priorities("activo")) == 3


def test_the_last_active_priority_cannot_be_deactivated(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)

        for code in ("BAJA", "MEDIA", "ALTA"):
            deactivate_item(by_code(Prioridad, code), actor=actor)

        db.session.commit()
        entries_before = len(audit_entries())

        with pytest.raises(LastActivePriorityError):
            deactivate_item(by_code(Prioridad, "CRITICA"), actor=actor)

        db.session.rollback()

        assert by_code(Prioridad, "CRITICA").activo is True
        assert len(audit_entries()) == entries_before


def test_inactive_priorities_do_not_count_as_available(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        deactivate_item(by_code(Prioridad, "BAJA"), actor=actor)
        deactivate_item(by_code(Prioridad, "MEDIA"), actor=actor)
        db.session.commit()

        # Quedan Alta y Crítica: se puede desactivar una, no las dos.
        deactivate_item(by_code(Prioridad, "ALTA"), actor=actor)
        db.session.commit()

        with pytest.raises(LastActivePriorityError):
            deactivate_item(by_code(Prioridad, "CRITICA"), actor=actor)


def test_reactivating_a_priority_whose_level_is_taken_is_rejected(
    app,
    admin_id,
):
    with app.app_context():
        actor = admin(admin_id)
        low = by_code(Prioridad, "BAJA")
        deactivate_item(low, actor=actor)
        db.session.add(Prioridad(codigo="OTRA", nombre="Otra", nivel=low.nivel))
        db.session.commit()
        entries_before = len(audit_entries())

        with pytest.raises(ActivationConflictError):
            activate_item(low, actor=actor)

        db.session.rollback()

        assert by_code(Prioridad, "BAJA").activo is False
        assert len(audit_entries()) == entries_before


def test_deactivation_blocker_explains_why(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        normal = create_category(actor=actor, nombre="Redes")
        db.session.commit()

        assert deactivation_blocker(normal) is None
        assert "respaldo" in deactivation_blocker(
            by_code(Categoria, "SIN_CLASIFICAR")
        )
        assert deactivation_blocker(by_code(Prioridad, "MEDIA")) is None


def test_deactivation_blocker_ignores_inactive_items(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)

        for code in ("BAJA", "MEDIA", "ALTA"):
            deactivate_item(by_code(Prioridad, code), actor=actor)

        assert deactivation_blocker(by_code(Prioridad, "CRITICA")) is not None
        # Una prioridad que ya está inactiva no tiene nada que bloquear.
        assert deactivation_blocker(by_code(Prioridad, "BAJA")) is None


# --- Efecto sobre los tickets -----------------------------------------


def test_deactivating_an_item_does_not_affect_existing_tickets(
    app,
    admin_id,
    ticket_catalog_ids,
):
    with app.app_context():
        actor = admin(admin_id)
        category = create_category(actor=actor, nombre="Redes")
        db.session.commit()

        ticket = create_ticket(
            actor=actor,
            title="Sin red",
            description="No hay conexión.",
            category_id=category.id,
            priority_id=ticket_catalog_ids["priority_id"],
        )
        db.session.commit()

        deactivate_item(category, actor=actor)
        db.session.commit()

        # El ticket histórico conserva su categoría...
        assert ticket.categoria_id == category.id
        assert ticket.categoria.activo is False

        # ...pero ya no puede elegirse en tickets nuevos.
        with pytest.raises(TicketRuleError):
            create_ticket(
                actor=actor,
                title="Otro",
                description="Otro problema.",
                category_id=category.id,
                priority_id=ticket_catalog_ids["priority_id"],
            )


# --- Listados ---------------------------------------------------------


def test_categories_are_listed_by_order_then_name(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        create_category(actor=actor, nombre="Zeta", orden=1)
        create_category(actor=actor, nombre="alfa")
        create_category(actor=actor, nombre="Beta")
        create_category(actor=actor, nombre="Primera", orden=0)
        db.session.commit()

        # "Sin clasificar" (del seed) tiene orden 0.
        assert names(list_categories()) == [
            "Primera",
            "Sin clasificar",
            "Zeta",
            "alfa",
            "Beta",
        ]


def test_priorities_are_listed_by_level(app, admin_id):
    with app.app_context():
        assert names(list_priorities()) == ["Baja", "Media", "Alta", "Crítica"]


def test_locations_are_listed_by_name_ignoring_case(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        create_location(actor=actor, nombre="Zona norte")
        create_location(actor=actor, nombre="oficina")
        create_location(actor=actor, nombre="Bodega")
        db.session.commit()

        assert names(list_locations()) == ["Bodega", "oficina", "Zona norte"]


def test_listings_can_be_filtered_by_status(app, admin_id):
    with app.app_context():
        actor = admin(admin_id)
        active = create_location(actor=actor, nombre="Abierta")
        closed = create_location(actor=actor, nombre="Cerrada")
        deactivate_item(closed, actor=actor)
        db.session.commit()

        assert list_locations("activo") == [active]
        assert list_locations("inactivo") == [closed]
        assert len(list_locations("")) == 2
        # Un valor desconocido no filtra.
        assert len(list_locations("cualquiera")) == 2
