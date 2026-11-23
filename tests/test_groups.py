"""Grupos de atención (docs/06, RN-146; docs/09, 10.1 a 10.3).

Cubre el modelo, las políticas, el servicio, los ganchos de la administración
de usuarios y las pantallas de `/groups`.
"""

import pytest
from flask_login import AnonymousUserMixin
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from src.workdesk.extensions import db
from src.workdesk.groups import service
from src.workdesk.groups.service import (
    DuplicateGroupNameError,
    GroupRuleError,
    NothingToChangeError,
    activate_group,
    add_member,
    close_user_group_links,
    create_group,
    deactivate_group,
    designate_supervisor,
    list_groups,
    list_member_candidates,
    list_supervisor_candidates,
    remove_member,
    remove_supervisor,
    update_group,
    visible_groups_condition,
)
from src.workdesk.models import (
    AdminAuditLog,
    Grupo,
    GrupoSupervisor,
    User,
    UsuarioGrupo,
)
from src.workdesk.security import (
    can_access_groups,
    can_manage_group_members,
    can_manage_groups,
    can_view_group,
    is_responsible_supervisor,
)
from src.workdesk.users.service import change_role, deactivate_user
from tests.ticket_helpers import audit_entries, login, plain_text, text

ALL_ROLES = ("SOLICITANTE", "TECNICO", "SUPERVISOR", "ADMINISTRADOR")


# --- Ayudas -----------------------------------------------------------


@pytest.fixture()
def people(make_user):
    """Una persona de cada rol, más un técnico y un supervisor adicionales."""
    return {
        "admin": make_user("ADMINISTRADOR", username="admin1", nombre="Ana", apellido="Admin"),
        "sup": make_user("SUPERVISOR", username="sup1", nombre="Camila", apellido="Rojas"),
        "sup2": make_user("SUPERVISOR", username="sup2", nombre="Matías", apellido="Fuentes"),
        "tec": make_user("TECNICO", username="tec1", nombre="Diego", apellido="Soto"),
        "tec2": make_user("TECNICO", username="tec2", nombre="Valentina", apellido="Pizarro"),
        "req": make_user("SOLICITANTE", username="req1", nombre="Javiera", apellido="Torres"),
    }


def user(people, key) -> User:
    return db.session.get(User, people[key]["id"])


def group_audit() -> list[AdminAuditLog]:
    return [e for e in audit_entries() if e.entidad_tipo == "grupo"]


def new_group(people, name="Soporte Redes", **kwargs) -> Grupo:
    group = create_group(actor=user(people, "admin"), nombre=name, **kwargs)
    db.session.commit()

    return group


def with_supervisor(people, group, key="sup"):
    designate_supervisor(group, people[key]["id"], actor=user(people, "admin"))
    db.session.commit()
    db.session.refresh(group)


def with_member(people, group, key="tec"):
    add_member(group, people[key]["id"], actor=user(people, "admin"))
    db.session.commit()
    db.session.refresh(group)


# --- Base de datos ---------------------------------------------------------


def test_group_name_is_unique_ignoring_case(app):
    with app.app_context():
        db.session.add(Grupo(nombre="Soporte"))
        db.session.commit()

        db.session.add(Grupo(nombre="SOPORTE"))

        with pytest.raises(IntegrityError):
            db.session.commit()


def test_a_member_is_unique_while_current_but_can_return_later(app, people):
    with app.app_context():
        group = new_group(people)
        tec = people["tec"]["id"]

        db.session.add(UsuarioGrupo(usuario_id=tec, grupo_id=group.id))
        db.session.commit()

        db.session.add(UsuarioGrupo(usuario_id=tec, grupo_id=group.id))

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()

        # Cerrada la primera, puede volver a entrar.
        link = db.session.scalars(db.select(UsuarioGrupo)).one()
        link.fecha_fin = func.now()
        db.session.commit()
        db.session.add(UsuarioGrupo(usuario_id=tec, grupo_id=group.id))
        db.session.commit()

        assert db.session.scalar(db.select(func.count(UsuarioGrupo.id))) == 2


def test_a_responsible_supervisor_is_unique_while_current(app, people):
    with app.app_context():
        group = new_group(people)
        sup = people["sup"]["id"]

        db.session.add(GrupoSupervisor(grupo_id=group.id, supervisor_id=sup))
        db.session.commit()

        db.session.add(GrupoSupervisor(grupo_id=group.id, supervisor_id=sup))

        with pytest.raises(IntegrityError):
            db.session.commit()


@pytest.mark.parametrize("model", [UsuarioGrupo, GrupoSupervisor])
def test_a_link_cannot_end_before_it_starts(app, people, model):
    with app.app_context():
        group = new_group(people)
        values = (
            {"usuario_id": people["tec"]["id"]}
            if model is UsuarioGrupo
            else {"supervisor_id": people["sup"]["id"]}
        )
        link = model(grupo_id=group.id, **values)
        db.session.add(link)
        db.session.commit()

        link.fecha_fin = link.fecha_inicio.replace(year=link.fecha_inicio.year - 1)

        with pytest.raises(IntegrityError):
            db.session.commit()


# --- Políticas -------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "access", "manage"),
    [
        ("SOLICITANTE", False, False),
        ("TECNICO", False, False),
        ("SUPERVISOR", True, False),
        ("ADMINISTRADOR", True, True),
    ],
)
def test_group_area_and_management_policies_by_role(
    app,
    make_user,
    role,
    access,
    manage,
):
    person = make_user(role)

    with app.app_context():
        member = db.session.get(User, person["id"])

        assert can_access_groups(member) is access
        assert can_manage_groups(member) is manage


def test_policies_deny_anonymous_and_inactive_users(app, people, make_user):
    inactive = make_user("ADMINISTRADOR", username="inactivo", activo=False)

    with app.app_context():
        group = new_group(people)

        for who in (AnonymousUserMixin(), db.session.get(User, inactive["id"])):
            assert can_access_groups(who) is False
            assert can_manage_groups(who) is False
            assert can_view_group(who, group) is False
            assert can_manage_group_members(who, group) is False


def test_only_a_current_supervisor_of_the_group_is_responsible(app, people):
    with app.app_context():
        group = new_group(people)
        other = new_group(people, "Soporte Usuarios")
        with_supervisor(people, group, "sup")

        assert is_responsible_supervisor(user(people, "sup"), group) is True
        # Otro supervisor, el Administrador y el Técnico no lo son.
        assert is_responsible_supervisor(user(people, "sup2"), group) is False
        assert is_responsible_supervisor(user(people, "admin"), group) is False
        assert is_responsible_supervisor(user(people, "tec"), group) is False
        # Ni siquiera el mismo supervisor, en otro grupo.
        assert is_responsible_supervisor(user(people, "sup"), other) is False

        remove_supervisor(
            group,
            group.supervisores_vigentes[0].id,
            actor=user(people, "admin"),
        )
        db.session.commit()
        db.session.refresh(group)

        assert is_responsible_supervisor(user(people, "sup"), group) is False


def test_view_and_member_policies_follow_the_responsibility(app, people):
    with app.app_context():
        group = new_group(people)
        with_supervisor(people, group, "sup")

        expected = {
            "admin": True,
            "sup": True,
            "sup2": False,
            "tec": False,
            "req": False,
        }

        for key, allowed in expected.items():
            assert can_view_group(user(people, key), group) is allowed
            assert can_manage_group_members(user(people, key), group) is allowed


@pytest.mark.parametrize("who", ["admin", "sup", "sup2", "tec", "req"])
def test_the_sql_condition_matches_the_policy(app, people, who):
    with app.app_context():
        mine = new_group(people, "Mío")
        theirs = new_group(people, "Ajeno")
        retired = new_group(people, "Retirado")
        with_supervisor(people, mine, "sup")
        with_supervisor(people, theirs, "sup2")
        with_supervisor(people, retired, "sup")
        remove_supervisor(
            retired,
            retired.supervisores_vigentes[0].id,
            actor=user(people, "admin"),
        )
        db.session.commit()

        member = user(people, who)
        visible = set(
            db.session.scalars(
                db.select(Grupo.id).where(visible_groups_condition(member))
            )
        )
        by_policy = {
            g.id
            for g in db.session.scalars(db.select(Grupo))
            if can_view_group(member, g)
        }

        assert visible == by_policy


def test_the_sql_condition_hides_everything_from_anonymous_and_inactive(
    app,
    people,
    make_user,
):
    inactive = make_user("SUPERVISOR", username="sup_inactivo", activo=False)

    with app.app_context():
        group = new_group(people)
        db.session.add(
            GrupoSupervisor(grupo_id=group.id, supervisor_id=inactive["id"])
        )
        db.session.commit()

        for who in (AnonymousUserMixin(), db.session.get(User, inactive["id"])):
            assert list(
                db.session.scalars(
                    db.select(Grupo.id).where(visible_groups_condition(who))
                )
            ) == []


# --- Servicio: alta, edición y estado -------------------------------------


def test_create_group_saves_the_data_and_audits_it(app, people):
    with app.app_context():
        group = create_group(
            actor=user(people, "admin"),
            nombre="  Soporte Redes  ",
            descripcion="  Redes y VPN  ",
        )
        db.session.commit()

        assert group.nombre == "Soporte Redes"
        assert group.descripcion == "Redes y VPN"
        assert group.activo is True
        assert group.usuario_creacion_id == people["admin"]["id"]

        (entry,) = group_audit()

        assert entry.accion == "GRUPO_CREADO"
        assert entry.entidad_id == group.id
        assert entry.detalle == "Soporte Redes"
        assert entry.valor_nuevo["activo"] is True


def test_create_group_requires_a_name_and_rejects_duplicates(app, people):
    with app.app_context():
        new_group(people)

        with pytest.raises(GroupRuleError, match="obligatorio"):
            create_group(actor=user(people, "admin"), nombre="   ")

        with pytest.raises(DuplicateGroupNameError):
            create_group(actor=user(people, "admin"), nombre="soporte REDES")


def test_create_group_recovers_from_a_name_race(app, people, monkeypatch):
    with app.app_context():
        new_group(people)

        # Dos altas pasan la comprobación a la vez: decide el índice único.
        monkeypatch.setattr(service, "_ensure_name_available", lambda *a, **k: None)

        with pytest.raises(DuplicateGroupNameError):
            create_group(actor=user(people, "admin"), nombre="Soporte Redes")

        monkeypatch.undo()
        db.session.rollback()

        assert [e.accion for e in group_audit()] == ["GRUPO_CREADO"]


def test_update_group_changes_only_what_was_modified(app, people):
    with app.app_context():
        group = new_group(people, descripcion="Antigua")

        changed = update_group(
            group,
            actor=user(people, "admin"),
            nombre="Soporte Redes",
            descripcion="Nueva",
        )
        db.session.commit()

        assert changed is True
        assert group.descripcion == "Nueva"
        assert group.usuario_modificacion_id == people["admin"]["id"]

        entry = group_audit()[-1]

        assert entry.accion == "GRUPO_MODIFICADO"
        assert entry.valor_anterior == {"descripcion": "Antigua"}
        assert entry.valor_nuevo == {"descripcion": "Nueva"}


def test_update_group_without_changes_audits_nothing(app, people):
    with app.app_context():
        group = new_group(people)
        before = len(audit_entries())

        assert (
            update_group(
                group,
                actor=user(people, "admin"),
                nombre="Soporte Redes",
                descripcion=None,
            )
            is False
        )
        assert len(audit_entries()) == before


def test_update_group_rejects_the_name_of_another_but_allows_its_own_case(
    app,
    people,
):
    with app.app_context():
        group = new_group(people)
        new_group(people, "Soporte Usuarios")

        with pytest.raises(DuplicateGroupNameError):
            update_group(
                group,
                actor=user(people, "admin"),
                nombre="soporte usuarios",
                descripcion=None,
            )

        db.session.rollback()

        assert update_group(
            group,
            actor=user(people, "admin"),
            nombre="SOPORTE REDES",
            descripcion=None,
        )


def test_deactivate_and_activate_keep_members_and_supervisors(app, people):
    with app.app_context():
        group = new_group(people)
        with_member(people, group)
        with_supervisor(people, group)
        admin = user(people, "admin")

        deactivate_group(group, actor=admin, reason="  Reorganización  ")
        db.session.commit()

        assert group.activo is False
        assert group.fecha_desactivacion is not None
        assert group.usuario_desactivacion_id == admin.id
        assert len(group.miembros_vigentes) == 1
        assert len(group.supervisores_vigentes) == 1
        assert group_audit()[-1].accion == "GRUPO_DESACTIVADO"
        assert group_audit()[-1].motivo == "Reorganización"

        with pytest.raises(NothingToChangeError):
            deactivate_group(group, actor=admin)

        activate_group(group, actor=admin)
        db.session.commit()

        assert group.activo is True
        assert group.fecha_desactivacion is None
        assert group.usuario_desactivacion_id is None
        assert group_audit()[-1].accion == "GRUPO_ACTIVADO"

        with pytest.raises(NothingToChangeError):
            activate_group(group, actor=admin)


# --- Servicio: miembros ----------------------------------------------------


def test_add_member_creates_a_current_membership_and_audits_it(app, people):
    with app.app_context():
        group = new_group(people)

        link = add_member(group, people["tec"]["id"], actor=user(people, "admin"))
        db.session.commit()

        assert link.fecha_fin is None
        assert link.asignado_por_usuario_id == people["admin"]["id"]
        assert [m.usuario_id for m in group.miembros_vigentes] == [
            people["tec"]["id"]
        ]

        entry = group_audit()[-1]

        assert entry.accion == "GRUPO_MIEMBRO_AGREGADO"
        assert entry.valor_nuevo == {
            "usuario_id": people["tec"]["id"],
            "username": "tec1",
        }


@pytest.mark.parametrize("who", ["sup", "admin", "req"])
def test_only_active_technicians_can_be_members(app, people, who):
    with app.app_context():
        group = new_group(people)

        with pytest.raises(GroupRuleError, match="técnico activo"):
            add_member(group, people[who]["id"], actor=user(people, "admin"))


def test_an_unknown_or_inactive_technician_cannot_be_added(
    app,
    people,
    make_user,
):
    inactive = make_user("TECNICO", username="tec_inactivo", activo=False)

    with app.app_context():
        group = new_group(people)

        for user_id in (inactive["id"], 99999):
            with pytest.raises(GroupRuleError, match="técnico activo"):
                add_member(group, user_id, actor=user(people, "admin"))


def test_a_current_member_cannot_be_added_twice(app, people):
    with app.app_context():
        group = new_group(people)
        with_member(people, group)

        with pytest.raises(GroupRuleError, match="ya es miembro"):
            add_member(group, people["tec"]["id"], actor=user(people, "admin"))


def test_add_member_recovers_from_a_race(app, people, monkeypatch):
    with app.app_context():
        group = new_group(people)
        with_member(people, group)

        # La comprobación previa no ve al miembro: decide el índice único.
        monkeypatch.setattr(
            type(group),
            "miembros_vigentes",
            property(lambda self: []),
        )

        with pytest.raises(GroupRuleError, match="ya es miembro"):
            add_member(group, people["tec"]["id"], actor=user(people, "admin"))

        monkeypatch.undo()
        db.session.rollback()


def test_members_cannot_be_added_to_an_inactive_group(app, people):
    with app.app_context():
        group = new_group(people)
        deactivate_group(group, actor=user(people, "admin"))
        db.session.commit()

        with pytest.raises(GroupRuleError, match="desactivado"):
            add_member(group, people["tec"]["id"], actor=user(people, "admin"))

        with pytest.raises(GroupRuleError, match="desactivado"):
            designate_supervisor(
                group,
                people["sup"]["id"],
                actor=user(people, "admin"),
            )


def test_remove_member_closes_the_membership_and_keeps_the_history(
    app,
    people,
):
    with app.app_context():
        group = new_group(people)
        with_member(people, group)
        link = group.miembros_vigentes[0]
        actor = user(people, "sup")

        remove_member(group, link.id, actor=actor, reason="  Cambio de turno ")
        db.session.commit()
        db.session.refresh(link)
        db.session.refresh(group)

        assert link.fecha_fin is not None
        assert link.retirado_por_usuario_id == actor.id
        assert link.motivo_retiro == "Cambio de turno"
        assert group.miembros_vigentes == []
        assert len(group.membresias) == 1

        entry = group_audit()[-1]

        assert entry.accion == "GRUPO_MIEMBRO_RETIRADO"
        assert entry.valor_anterior["username"] == "tec1"
        assert entry.motivo == "Cambio de turno"


def test_a_removed_member_can_be_added_again_as_a_new_row(app, people):
    with app.app_context():
        group = new_group(people)
        with_member(people, group)
        remove_member(
            group,
            group.miembros_vigentes[0].id,
            actor=user(people, "admin"),
        )
        db.session.commit()
        db.session.refresh(group)

        with_member(people, group)

        assert len(group.membresias) == 2
        assert len(group.miembros_vigentes) == 1


def test_remove_member_rejects_an_unknown_or_already_removed_membership(
    app,
    people,
):
    with app.app_context():
        group = new_group(people)
        other = new_group(people, "Soporte Usuarios")
        with_member(people, other)
        foreign_link = other.miembros_vigentes[0].id

        # Un id de otro grupo no se puede usar para retirar de este.
        for membership_id in (99999, foreign_link):
            with pytest.raises(GroupRuleError, match="ya no es miembro"):
                remove_member(group, membership_id, actor=user(people, "admin"))


# --- Servicio: supervisores ------------------------------------------------


def test_designate_supervisor_and_remove_it(app, people):
    with app.app_context():
        group = new_group(people)
        admin = user(people, "admin")

        designation = designate_supervisor(group, people["sup"]["id"], actor=admin)
        db.session.commit()
        db.session.refresh(group)

        assert designation.asignado_por_usuario_id == admin.id
        assert [d.supervisor_id for d in group.supervisores_vigentes] == [
            people["sup"]["id"]
        ]
        assert group_audit()[-1].accion == "GRUPO_SUPERVISOR_DESIGNADO"

        remove_supervisor(group, designation.id, actor=admin, reason="Traslado")
        db.session.commit()
        db.session.refresh(group)

        assert group.supervisores_vigentes == []
        assert designation.fecha_fin is not None
        assert designation.motivo_retiro == "Traslado"
        assert group_audit()[-1].accion == "GRUPO_SUPERVISOR_RETIRADO"


def test_a_group_can_have_several_supervisors_and_none(app, people):
    with app.app_context():
        group = new_group(people)

        assert group.supervisores_vigentes == []

        with_supervisor(people, group, "sup")
        with_supervisor(people, group, "sup2")

        assert len(group.supervisores_vigentes) == 2


@pytest.mark.parametrize("who", ["tec", "admin", "req"])
def test_only_active_supervisors_can_be_designated(app, people, who):
    with app.app_context():
        group = new_group(people)

        with pytest.raises(GroupRuleError, match="supervisor activo"):
            designate_supervisor(
                group,
                people[who]["id"],
                actor=user(people, "admin"),
            )


def test_a_supervisor_cannot_be_designated_twice(app, people):
    with app.app_context():
        group = new_group(people)
        with_supervisor(people, group)

        with pytest.raises(GroupRuleError, match="ya es responsable"):
            designate_supervisor(
                group,
                people["sup"]["id"],
                actor=user(people, "admin"),
            )


def test_remove_supervisor_rejects_an_unknown_designation(app, people):
    with app.app_context():
        group = new_group(people)

        with pytest.raises(GroupRuleError, match="ya no es responsable"):
            remove_supervisor(group, 99999, actor=user(people, "admin"))


# --- Servicio: consultas ---------------------------------------------------


def test_candidates_exclude_current_members_and_supervisors(app, people):
    with app.app_context():
        group = new_group(people)
        with_member(people, group, "tec")
        with_supervisor(people, group, "sup")

        assert [u.username for u in list_member_candidates(group)] == ["tec2"]
        assert [u.username for u in list_supervisor_candidates(group)] == ["sup2"]


def test_candidates_only_include_active_people_of_the_right_role(
    app,
    people,
    make_user,
):
    make_user("TECNICO", username="tec_inactivo", activo=False)

    with app.app_context():
        group = new_group(people)

        assert {u.username for u in list_member_candidates(group)} == {
            "tec1",
            "tec2",
        }
        assert {u.username for u in list_supervisor_candidates(group)} == {
            "sup1",
            "sup2",
        }


def test_each_role_lists_only_the_groups_it_may_see(app, people):
    with app.app_context():
        mine = new_group(people, "Alfa")
        theirs = new_group(people, "Beta")
        new_group(people, "Gamma")
        with_supervisor(people, mine, "sup")
        with_supervisor(people, theirs, "sup2")

        def names(key):
            return [g.nombre for g in list_groups(user(people, key))]

        assert names("admin") == ["Alfa", "Beta", "Gamma"]
        assert names("sup") == ["Alfa"]
        assert names("sup2") == ["Beta"]
        assert names("tec") == []
        assert names("req") == []


def test_the_list_can_be_filtered_by_status_and_is_ordered_ignoring_case(
    app,
    people,
):
    with app.app_context():
        new_group(people, "zeta")
        new_group(people, "Alfa")
        inactive = new_group(people, "Beta")
        deactivate_group(inactive, actor=user(people, "admin"))
        db.session.commit()

        admin = user(people, "admin")

        assert [g.nombre for g in list_groups(admin)] == ["Alfa", "Beta", "zeta"]
        assert [g.nombre for g in list_groups(admin, "activo")] == ["Alfa", "zeta"]
        assert [g.nombre for g in list_groups(admin, "inactivo")] == ["Beta"]


def test_listing_does_not_query_per_group(app, people):
    from sqlalchemy import event

    with app.app_context():
        for index in range(5):
            group = new_group(people, f"Grupo {index}")
            with_member(people, group)
            with_supervisor(people, group)

        db.session.expire_all()
        statements = []

        def count(conn, cursor, statement, *args):
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", count)

        try:
            groups = list_groups(user(people, "admin"))
            statements.clear()

            for group in groups:
                [m.usuario.nombre for m in group.miembros_vigentes]
                [d.supervisor.nombre for d in group.supervisores_vigentes]
        finally:
            event.remove(db.engine, "before_cursor_execute", count)

        assert statements == []


# --- Ganchos de la administración de usuarios ------------------------------


def test_a_technician_who_changes_role_leaves_their_groups(app, people):
    with app.app_context():
        group = new_group(people)
        with_member(people, group)
        admin = user(people, "admin")

        change_role(user(people, "tec"), "SUPERVISOR", actor=admin)
        db.session.commit()
        db.session.refresh(group)

        assert group.miembros_vigentes == []
        assert len(group.membresias) == 1

        entry = [e for e in group_audit() if e.accion == "GRUPO_MIEMBRO_RETIRADO"][-1]

        assert entry.entidad_id == group.id
        assert entry.motivo == "Cambio de rol."
        assert entry.valor_anterior["username"] == "tec1"


def test_a_supervisor_who_changes_role_stops_being_responsible(app, people):
    with app.app_context():
        group = new_group(people)
        with_supervisor(people, group)
        with_member(people, group)
        admin = user(people, "admin")

        change_role(user(people, "sup"), "TECNICO", actor=admin)
        db.session.commit()
        db.session.refresh(group)

        assert group.supervisores_vigentes == []
        # El grupo y sus técnicos siguen: solo cambió la responsabilidad.
        assert len(group.miembros_vigentes) == 1
        assert group.activo is True
        assert can_view_group(user(people, "sup"), group) is False
        assert [e.accion for e in group_audit()][-1] == "GRUPO_SUPERVISOR_RETIRADO"


def test_changing_role_to_a_group_role_closes_nothing(app, people):
    with app.app_context():
        group = new_group(people)
        with_member(people, group)
        before = len(group_audit())

        # Un solicitante pasa a técnico: no tenía grupos que cerrar.
        change_role(user(people, "req"), "TECNICO", actor=user(people, "admin"))
        db.session.commit()

        assert len(group_audit()) == before
        assert len(group.miembros_vigentes) == 1


def test_deactivating_a_user_closes_their_group_links(app, people):
    with app.app_context():
        group = new_group(people)
        other = new_group(people, "Soporte Usuarios")
        with_member(people, group)
        with_member(people, other)
        with_supervisor(people, group, "sup")
        admin = user(people, "admin")

        deactivate_user(user(people, "tec"), actor=admin)
        deactivate_user(user(people, "sup"), actor=admin)
        db.session.commit()
        db.session.refresh(group)
        db.session.refresh(other)

        assert group.miembros_vigentes == []
        assert other.miembros_vigentes == []
        assert group.supervisores_vigentes == []
        assert {e.motivo for e in group_audit() if "RETIRADO" in e.accion} == {
            "Usuario desactivado."
        }


def test_reactivating_a_user_does_not_restore_their_groups(app, people):
    from src.workdesk.users.service import activate_user

    with app.app_context():
        group = new_group(people)
        with_member(people, group)
        admin = user(people, "admin")

        deactivate_user(user(people, "tec"), actor=admin)
        db.session.commit()
        activate_user(user(people, "tec"), actor=admin)
        db.session.commit()
        db.session.refresh(group)

        assert group.miembros_vigentes == []
        # Candidatos por apellido y nombre: Pizarro antes que Soto.
        assert [u.username for u in list_member_candidates(group)] == [
            "tec2",
            "tec1",
        ]


def test_close_user_group_links_counts_what_it_closes(app, people):
    with app.app_context():
        one = new_group(people, "Uno")
        two = new_group(people, "Dos")
        with_member(people, one)
        with_member(people, two)

        closed = close_user_group_links(
            user(people, "tec"),
            actor=user(people, "admin"),
            reason="Prueba",
        )

        assert closed == 2
        assert (
            close_user_group_links(
                user(people, "tec"),
                actor=user(people, "admin"),
                reason="Prueba",
            )
            == 0
        )


# --- Pantallas -------------------------------------------------------------


def open_as(client, people, key):
    client.post("/logout")
    login(client, people[key])


def group_with_team(app, people, name="Soporte Redes"):
    """Un grupo con un supervisor responsable y un técnico, ya confirmado."""
    with app.app_context():
        group = new_group(people, name)
        with_supervisor(people, group, "sup")
        with_member(people, group, "tec")

        return group.id


@pytest.mark.parametrize("key", ["tec", "req"])
@pytest.mark.parametrize(
    "path",
    [
        "/groups",
        "/groups/new",
        "/groups/{id}",
        "/groups/{id}/edit",
        "/groups/{id}/deactivate",
        "/groups/{id}/activate",
    ],
)
def test_technicians_and_requesters_are_forbidden(
    client,
    app,
    people,
    key,
    path,
):
    group_id = group_with_team(app, people)
    login(client, people[key])

    assert client.get(path.format(id=group_id)).status_code == 403


@pytest.mark.parametrize("key", ["tec", "req", "sup"])
@pytest.mark.parametrize(
    "path",
    ["/groups/new", "/groups/{id}/members/add", "/groups/{id}/supervisors/add"],
)
def test_forbidden_roles_cannot_post(client, app, people, key, path):
    group_id = group_with_team(app, people)
    login(client, people[key])

    response = client.post(
        path.format(id=group_id),
        data={"nombre": "Intruso", "usuario": people["tec2"]["id"]},
    )

    # Técnico y Solicitante: 403 por rol. El Supervisor, en las rutas
    # exclusivas del Administrador (/new y supervisores) también 403; en la de
    # miembros sí puede actuar sobre su grupo.
    if key == "sup" and path.endswith("/members/add"):
        assert response.status_code == 302
    else:
        assert response.status_code == 403

    with app.app_context():
        assert db.session.scalar(
            db.select(Grupo).where(Grupo.nombre == "Intruso")
        ) is None


def test_the_administrator_opens_every_screen(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    for path in (
        "/groups",
        "/groups/new",
        f"/groups/{group_id}",
        f"/groups/{group_id}/edit",
        f"/groups/{group_id}/deactivate",
    ):
        assert client.get(path).status_code == 200, path


def test_unknown_groups_are_404(client, app, people):
    login(client, people["admin"])

    for path in (
        "/groups/99999",
        "/groups/99999/edit",
        "/groups/99999/deactivate",
        "/groups/99999/activate",
        "/groups/99999/members/1/remove",
        "/groups/99999/supervisors/1/remove",
    ):
        assert client.get(path).status_code == 404, path


def test_a_supervisor_sees_only_their_own_groups(client, app, people):
    group_with_team(app, people, "Soporte Redes")
    with app.app_context():
        new_group(people, "Soporte Usuarios")
        other = new_group(people, "Soporte Aplicaciones")
        with_supervisor(people, other, "sup2")
        other_id = other.id

    login(client, people["sup"])
    content = text(client.get("/groups"))

    assert "Soporte Redes" in content
    assert "Soporte Usuarios" not in content
    assert "Soporte Aplicaciones" not in content
    assert "Nuevo grupo" not in content
    # Un grupo ajeno responde igual que uno inexistente.
    assert client.get(f"/groups/{other_id}").status_code == 404
    assert client.get("/groups/99999").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/groups/{id}/edit",
        "/groups/{id}/deactivate",
        "/groups/{id}/activate",
    ],
)
def test_a_supervisor_cannot_manage_the_group_itself(client, app, people, path):
    group_id = group_with_team(app, people)
    login(client, people["sup"])

    assert client.get(path.format(id=group_id)).status_code == 403
    assert client.post(path.format(id=group_id), data={"nombre": "X"}).status_code == 403


def test_a_supervisor_cannot_touch_the_supervisors_of_their_group(
    client,
    app,
    people,
):
    group_id = group_with_team(app, people)
    with app.app_context():
        designation_id = db.session.scalars(db.select(GrupoSupervisor)).one().id

    login(client, people["sup"])
    path = f"/groups/{group_id}/supervisors/{designation_id}/remove"

    assert client.get(path).status_code == 403
    assert client.post(path).status_code == 403

    with app.app_context():
        assert db.session.get(GrupoSupervisor, designation_id).fecha_fin is None


def test_a_supervisor_cannot_act_on_the_members_of_a_foreign_group(
    client,
    app,
    people,
):
    with app.app_context():
        foreign = new_group(people, "Ajeno")
        with_supervisor(people, foreign, "sup2")
        with_member(people, foreign, "tec")
        foreign_id = foreign.id
        link_id = foreign.miembros_vigentes[0].id

    login(client, people["sup"])

    assert (
        client.post(
            f"/groups/{foreign_id}/members/add",
            data={"usuario": people["tec2"]["id"]},
        ).status_code
        == 404
    )
    assert client.get(f"/groups/{foreign_id}/members/{link_id}/remove").status_code == 404
    assert client.post(f"/groups/{foreign_id}/members/{link_id}/remove").status_code == 404

    with app.app_context():
        assert db.session.get(UsuarioGrupo, link_id).fecha_fin is None


def test_the_administrator_creates_a_group(client, app, people):
    login(client, people["admin"])

    response = client.post(
        "/groups/new",
        data={"nombre": "Soporte Redes", "descripcion": "Redes y VPN"},
        follow_redirects=True,
    )

    assert "El grupo «Soporte Redes» fue creado." in text(response)

    with app.app_context():
        group = db.session.scalar(db.select(Grupo))

        assert group.descripcion == "Redes y VPN"
        assert group_audit()[-1].accion == "GRUPO_CREADO"


def test_group_form_validations(client, app, people):
    login(client, people["admin"])
    new_group_in_db = group_with_team(app, people)

    missing = client.post("/groups/new", data={"nombre": " "})
    duplicate = client.post("/groups/new", data={"nombre": "soporte redes"})
    long_name = client.post("/groups/new", data={"nombre": "x" * 101})
    long_description = client.post(
        "/groups/new",
        data={"nombre": "Otro", "descripcion": "x" * 501},
    )

    assert "Ingresa el nombre." in text(missing)
    assert "Ya existe un grupo con ese nombre." in text(duplicate)
    assert "Máximo 100 caracteres." in text(long_name)
    assert "Máximo 500 caracteres." in text(long_description)
    assert new_group_in_db


def test_the_administrator_edits_a_group(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    form = client.get(f"/groups/{group_id}/edit").get_data(as_text=True)

    assert 'value="Soporte Redes"' in form

    changed = client.post(
        f"/groups/{group_id}/edit",
        data={"nombre": "Soporte de Redes", "descripcion": ""},
        follow_redirects=True,
    )
    unchanged = client.post(
        f"/groups/{group_id}/edit",
        data={"nombre": "Soporte de Redes", "descripcion": ""},
        follow_redirects=True,
    )

    assert "El grupo «Soporte de Redes» se actualizó." in text(changed)
    assert "No había cambios que guardar." in text(unchanged)


def test_deactivate_and_reactivate_a_group_with_a_reason(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    confirmation = client.get(f"/groups/{group_id}/deactivate")

    assert "Desactivar grupo" in text(confirmation)

    deactivated = client.post(
        f"/groups/{group_id}/deactivate",
        data={"motivo": "Reorganización"},
        follow_redirects=True,
    )
    content = text(deactivated)

    assert "El grupo «Soporte Redes» fue desactivado." in content
    assert "Este grupo está desactivado" in content
    # Desactivado: no se ofrecen formularios de miembros ni responsables.
    assert "Agregar un técnico" not in content
    assert "Designar un responsable" not in content

    with app.app_context():
        assert group_audit()[-1].motivo == "Reorganización"

    again = client.post(
        f"/groups/{group_id}/deactivate",
        follow_redirects=True,
    )

    assert "El grupo ya está desactivado." in text(again)

    reactivated = client.post(
        f"/groups/{group_id}/activate",
        follow_redirects=True,
    )

    assert "El grupo «Soporte Redes» fue reactivado." in text(reactivated)

    already = client.post(f"/groups/{group_id}/activate", follow_redirects=True)

    assert "El grupo ya está activo." in text(already)


def test_the_detail_shows_the_team_and_the_admin_actions(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    content = plain_text(client.get(f"/groups/{group_id}"))

    assert "Soporte Redes" in content
    assert "Camila Rojas" in content
    assert "Diego Soto" in content
    assert "Técnicos (1)" in content
    assert "Editar" in content
    assert "Desactivar" in content
    assert "Agregar un técnico" in content
    assert "Designar un responsable" in content
    # El candidato ya miembro no se ofrece; el otro sí.
    assert "Valentina Pizarro" in content


def test_the_supervisor_detail_hides_what_only_the_admin_can_do(
    client,
    app,
    people,
):
    group_id = group_with_team(app, people)
    login(client, people["sup"])

    content = text(client.get(f"/groups/{group_id}"))

    assert "Agregar un técnico" in content
    assert "Retirar" in content
    assert "Editar" not in content
    assert "Desactivar" not in content
    assert "Designar un responsable" not in content
    # Sin enlaces a Administración en la ruta de navegación.
    assert "Administración" not in content


def test_the_admin_breadcrumb_goes_through_administration(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    html = client.get(f"/groups/{group_id}").get_data(as_text=True)

    assert 'href="/admin"' in html


def test_add_a_member_from_the_detail(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["sup"])

    response = client.post(
        f"/groups/{group_id}/members/add",
        data={"usuario": people["tec2"]["id"]},
        follow_redirects=True,
    )
    content = plain_text(response)

    assert "Valentina Pizarro se agregó al grupo." in content
    assert "Técnicos (2)" in content

    with app.app_context():
        link = db.session.scalar(
            db.select(UsuarioGrupo).where(
                UsuarioGrupo.usuario_id == people["tec2"]["id"]
            )
        )

        assert link.asignado_por_usuario_id == people["sup"]["id"]


@pytest.mark.parametrize(
    ("data_key", "message"),
    [
        ("req", "Elige un técnico de la lista."),
        ("sup", "Elige un técnico de la lista."),
        ("tec", "Elige un técnico de la lista."),
    ],
)
def test_adding_an_invalid_member_is_rejected(
    client,
    app,
    people,
    data_key,
    message,
):
    # "tec" ya es miembro: no figura entre los candidatos.
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    response = client.post(
        f"/groups/{group_id}/members/add",
        data={"usuario": people[data_key]["id"]},
        follow_redirects=True,
    )

    assert message in text(response)

    with app.app_context():
        assert db.session.scalar(db.select(func.count(UsuarioGrupo.id))) == 1


def test_adding_without_choosing_or_with_garbage_is_rejected(
    client,
    app,
    people,
):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    for data in ({}, {"usuario": ""}, {"usuario": "abc"}, {"usuario": "99999"}):
        response = client.post(
            f"/groups/{group_id}/members/add",
            data=data,
            follow_redirects=True,
        )

        assert "Elige un técnico de la lista." in text(response) or (
            "Ingresa un número entero." in text(response)
        )

    with app.app_context():
        assert db.session.scalar(db.select(func.count(UsuarioGrupo.id))) == 1


def test_adding_a_member_to_an_inactive_group_is_rejected(client, app, people):
    group_id = group_with_team(app, people)

    with app.app_context():
        deactivate_group(db.session.get(Grupo, group_id), actor=user(people, "admin"))
        db.session.commit()

    login(client, people["admin"])
    response = client.post(
        f"/groups/{group_id}/members/add",
        data={"usuario": people["tec2"]["id"]},
        follow_redirects=True,
    )

    assert "desactivado" in text(response)


def test_remove_a_member_with_confirmation(client, app, people):
    group_id = group_with_team(app, people)
    with app.app_context():
        link_id = db.session.scalars(db.select(UsuarioGrupo)).one().id

    login(client, people["sup"])
    path = f"/groups/{group_id}/members/{link_id}/remove"

    confirmation = text(client.get(path))

    assert "Retirar del grupo" in confirmation
    assert "Diego Soto" in confirmation

    response = client.post(path, data={"motivo": "Cambio de turno"}, follow_redirects=True)

    assert "Diego Soto fue retirado del grupo." in text(response)

    with app.app_context():
        link = db.session.get(UsuarioGrupo, link_id)

        assert link.fecha_fin is not None
        assert link.motivo_retiro == "Cambio de turno"

    again = client.post(path, follow_redirects=True)

    assert "Esa persona ya no es miembro del grupo." in text(again)


def test_a_member_id_of_another_group_is_not_removable_from_this_one(
    client,
    app,
    people,
):
    group_id = group_with_team(app, people)
    with app.app_context():
        other = new_group(people, "Otro")
        with_member(people, other, "tec2")
        foreign_link = other.miembros_vigentes[0].id

    login(client, people["admin"])
    response = client.post(
        f"/groups/{group_id}/members/{foreign_link}/remove",
        follow_redirects=True,
    )

    assert "Esa persona ya no es miembro del grupo." in text(response)

    with app.app_context():
        assert db.session.get(UsuarioGrupo, foreign_link).fecha_fin is None


def test_designate_and_remove_a_supervisor_from_the_screens(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    designated = client.post(
        f"/groups/{group_id}/supervisors/add",
        data={"usuario": people["sup2"]["id"]},
        follow_redirects=True,
    )

    assert "Matías Fuentes es ahora responsable del grupo." in text(designated)

    with app.app_context():
        designation_id = db.session.scalar(
            db.select(GrupoSupervisor.id).where(
                GrupoSupervisor.supervisor_id == people["sup2"]["id"]
            )
        )

    path = f"/groups/{group_id}/supervisors/{designation_id}/remove"

    assert "Retirar supervisor responsable" in text(client.get(path))

    removed = client.post(path, data={"motivo": "Traslado"}, follow_redirects=True)

    assert "Matías Fuentes ya no es responsable del grupo." in text(removed)

    with app.app_context():
        assert db.session.get(GrupoSupervisor, designation_id).fecha_fin is not None


def test_an_invalid_supervisor_is_rejected_from_the_screen(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    for key in ("tec2", "req", "sup"):
        response = client.post(
            f"/groups/{group_id}/supervisors/add",
            data={"usuario": people[key]["id"]},
            follow_redirects=True,
        )

        assert "Elige un supervisor de la lista." in text(response)


def test_a_retired_supervisor_loses_access_to_the_group(client, app, people):
    group_id = group_with_team(app, people)
    login(client, people["admin"])

    with app.app_context():
        designation_id = db.session.scalars(db.select(GrupoSupervisor)).one().id

    client.post(f"/groups/{group_id}/supervisors/{designation_id}/remove")
    open_as(client, people, "sup")

    assert client.get(f"/groups/{group_id}").status_code == 404
    assert "Soporte Redes" not in text(client.get("/groups"))


def test_a_group_without_supervisor_shows_who_manages_it(client, app, people):
    with app.app_context():
        group_id = new_group(people).id

    login(client, people["admin"])
    content = text(client.get(f"/groups/{group_id}"))

    assert "Sin supervisor responsable" in content
    assert "Este grupo no tiene técnicos." in content


def test_names_are_escaped(client, app, people):
    with app.app_context():
        create_group(
            actor=user(people, "admin"),
            nombre="<script>alert(1)</script>",
            descripcion="<b>negrita</b>",
        )
        db.session.commit()
        group_id = db.session.scalar(db.select(Grupo.id))

    login(client, people["admin"])

    for path in ("/groups", f"/groups/{group_id}"):
        html = client.get(path).get_data(as_text=True)

        assert "<script>alert(1)</script>" not in html
        assert "<b>negrita</b>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_the_list_filters_by_status_and_ignores_invalid_values(
    client,
    app,
    people,
):
    with app.app_context():
        new_group(people, "Activo uno")
        inactive = new_group(people, "Inactivo uno")
        deactivate_group(inactive, actor=user(people, "admin"))
        db.session.commit()

    login(client, people["admin"])

    active = text(client.get("/groups?estado=activo"))
    inactive_page = text(client.get("/groups?estado=inactivo"))
    garbage = text(client.get("/groups?estado=raro"))

    assert "Activo uno" in active and "Inactivo uno" not in active
    assert "Inactivo uno" in inactive_page and "Activo uno" not in inactive_page
    assert "Activo uno" in garbage and "Inactivo uno" in garbage


def test_the_list_shows_counts_and_supervisors(client, app, people):
    group_with_team(app, people)
    login(client, people["admin"])

    content = text(client.get("/groups"))

    assert "Camila Rojas" in content
    assert "Sin responsable" not in content


def test_the_supervisor_empty_state(client, app, people):
    login(client, people["sup"])

    assert "No eres responsable de ningún grupo todavía." in text(client.get("/groups"))


# --- Navegación ------------------------------------------------------------


def test_the_supervisor_menu_has_the_groups_entry_and_marks_it_active(
    client,
    app,
    people,
):
    group_id = group_with_team(app, people)
    login(client, people["sup"])

    for path in ("/groups", f"/groups/{group_id}"):
        html = client.get(path).get_data(as_text=True)

        assert 'href="/groups"' in html
        assert 'aria-current="page"' in html

    assert "Grupos" in plain_text(client.get("/dashboard"))


def test_the_other_roles_have_no_groups_entry_in_the_menu(client, app, people):
    for key in ("tec", "req", "admin"):
        open_as(client, people, key)
        html = client.get("/dashboard").get_data(as_text=True)

        assert 'href="/groups"' not in html or key == "admin"

    # El Administrador llega por el hub de Administración.
    open_as(client, people, "admin")

    assert 'href="/groups"' in client.get("/admin").get_data(as_text=True)


def test_the_hub_card_for_groups_is_a_link(client, app, people):
    login(client, people["admin"])

    html = client.get("/admin").get_data(as_text=True)

    assert 'href="/groups"' in html
    assert "Grupos" in html
