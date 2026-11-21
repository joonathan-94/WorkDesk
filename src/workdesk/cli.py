import os

import click
from flask import Flask, current_app

from .extensions import db
from .formatting import format_duration, local_datetime
from .models import Prioridad, Role, Ticket, User
from .security import (
    PasswordPolicyError,
    hash_password,
    validate_password_policy,
)
from .seeds import (
    DemoTicketsError,
    seed_catalogs,
    seed_demo_groups,
    seed_demo_tickets,
    seed_demo_users,
    seed_roles,
)
from .sla.periods import (
    SlaStatus,
    evaluate_ticket_sla,
    list_periods,
    rebuild_periods,
)

_SLA_STATUS_LABELS = {
    SlaStatus.DENTRO: "dentro de plazo",
    SlaStatus.PROXIMO_A_VENCER: "próximo a vencer",
    SlaStatus.VENCIDO: "vencido",
    SlaStatus.PAUSADO: "pausado",
}

# Variable de entorno opcional con la contraseña de los usuarios demo, para
# ejecutar `seed-demo` sin interacción. Nunca se guarda ni se muestra.
DEMO_PASSWORD_ENV = "WORKDESK_DEMO_PASSWORD"


def _describe_ticket_sla(ticket: Ticket) -> list[str]:
    """Las líneas que muestra `sla-status`: el estado del SLA y sus períodos."""
    lines = [
        (
            f"Ticket #{ticket.public_id} · prioridad {ticket.prioridad.nombre} "
            f"· estado {ticket.estado.nombre_visible}"
        )
    ]
    snapshot = evaluate_ticket_sla(ticket.id)

    if snapshot is None:
        lines.append("SLA: ninguno (la prioridad no tiene una política activa).")

        return lines

    consumed = format_duration(snapshot.consumed_seconds // 60)
    objective = format_duration(snapshot.objective_seconds // 60)
    lines.append(f"SLA: {_SLA_STATUS_LABELS[snapshot.status]}")
    lines.append(f"Consumido: {consumed} de {objective} ({snapshot.percent} %)")

    if snapshot.due_at is not None:
        lines.append(f"Vence: {local_datetime(snapshot.due_at)}")

    if snapshot.period.tiempo_objetivo_respuesta_minutos is None:
        lines.append("Primera respuesta: sin objetivo")
    elif snapshot.responded_at is not None:
        lines.append(f"Primera respuesta: {local_datetime(snapshot.responded_at)}")
    elif snapshot.response_due_at is not None:
        late = " (vencida)" if snapshot.response_overdue else ""
        lines.append(
            f"Primera respuesta: pendiente, vence {local_datetime(snapshot.response_due_at)}{late}"
        )

    lines.append("Períodos:")

    for number, period in enumerate(list_periods(ticket.id), start=1):
        priority = db.session.get(Prioridad, period.prioridad_id)
        mode = "pausado" if period.fecha_vencimiento_resolucion is None else "corriendo"
        end = "vigente" if period.fecha_fin is None else local_datetime(period.fecha_fin)
        consumed = format_duration(period.segundos_consumidos // 60)
        lines.append(
            f"  {number}. {local_datetime(period.fecha_inicio)} → {end} · "
            f"{priority.nombre} · {mode} · consumió {consumed}"
        )

    return lines


def register_commands(app: Flask) -> None:
    @app.cli.command("seed-roles")
    def seed_roles_command() -> None:
        """Carga los roles estructurales iniciales."""

        created = seed_roles()

        click.echo(f"Roles creados: {created}")

    @app.cli.command("seed-catalogs")
    def seed_catalogs_command() -> None:
        """Carga los catálogos iniciales de tickets (idempotente)."""

        created = seed_catalogs()

        click.echo(
            "Catálogos cargados. "
            f"Estados: {created['estados']}, "
            f"transiciones: {created['transiciones']}, "
            f"prioridades: {created['prioridades']}, "
            f"políticas de SLA: {created['politicas_sla']}, "
            f"categorías: {created['categorias']}, "
            f"motivos de cierre: {created['motivos_cierre']}, "
            f"motivos de espera: {created['motivos_espera']}, "
            f"tipos de relación: {created['tipos_relacion']}."
        )

    @app.cli.command("create-admin")
    def create_admin_command() -> None:
        """Crea el Administrador inicial de WorkDesk."""

        admin_role = db.session.scalar(
            db.select(Role).where(Role.codigo == "ADMINISTRADOR")
        )

        if admin_role is None:
            raise click.ClickException(
                "No existe el rol ADMINISTRADOR. "
                "Ejecuta primero el comando seed-roles."
            )

        existing_admin = db.session.scalar(
            db.select(User)
            .where(User.rol_id == admin_role.id)
            .limit(1)
        )

        if existing_admin is not None:
            raise click.ClickException(
                "Ya existe un usuario con rol ADMINISTRADOR."
            )

        nombre = click.prompt("Nombre").strip()
        apellido = click.prompt("Apellido").strip()
        username = click.prompt("Username").strip().lower()
        email = click.prompt("Email").strip().lower()

        if not nombre or not apellido or not username or not email:
            raise click.ClickException(
                "Nombre, apellido, username y email son obligatorios."
            )

        if len(username) > 50:
            raise click.ClickException(
                "El username no puede superar los 50 caracteres."
            )

        if len(email) > 254:
            raise click.ClickException(
                "El email no puede superar los 254 caracteres."
            )

        existing_username = db.session.scalar(
            db.select(User).where(User.username == username)
        )

        if existing_username is not None:
            raise click.ClickException(
                "El username indicado ya está registrado."
            )

        existing_email = db.session.scalar(
            db.select(User).where(User.email == email)
        )

        if existing_email is not None:
            raise click.ClickException(
                "El email indicado ya está registrado."
            )

        password = click.prompt(
            "Contraseña",
            hide_input=True,
            confirmation_prompt=True,
        )

        try:
            validate_password_policy(
                password,
                min_length=current_app.config["PASSWORD_MIN_LENGTH"],
            )
        except PasswordPolicyError as error:
            raise click.ClickException(str(error)) from error

        admin = User(
            nombre=nombre,
            apellido=apellido,
            username=username,
            email=email,
            password_hash=hash_password(password),
            rol_id=admin_role.id,
        )

        db.session.add(admin)
        db.session.commit()

        click.echo(
            f"Administrador '{username}' creado correctamente."
        )

    @app.cli.command("seed-demo")
    def seed_demo_command() -> None:
        """Carga usuarios y grupos de demostración (equipo de soporte ficticio).

        La contraseña de los usuarios demo se pide al ejecutar el comando
        (oculta) o se toma de la variable de entorno WORKDESK_DEMO_PASSWORD.
        No se ejecuta con APP_ENV=production. No crea ningún Administrador.
        """

        if current_app.config["APP_ENV"] == "production":
            raise click.ClickException(
                "Los datos de demostración no se cargan en producción."
            )

        password = os.getenv(DEMO_PASSWORD_ENV) or click.prompt(
            "Contraseña para los usuarios demo",
            hide_input=True,
            confirmation_prompt=True,
        )

        try:
            validate_password_policy(
                password,
                min_length=current_app.config["PASSWORD_MIN_LENGTH"],
            )
        except PasswordPolicyError as error:
            raise click.ClickException(str(error)) from error

        seed_roles()
        created, skipped = seed_demo_users(password)

        click.echo(
            f"Usuarios demo creados: {created}. "
            f"Omitidos (ya existían): {skipped}."
        )
        groups_created, groups_skipped = seed_demo_groups()

        click.echo(
            f"Grupos demo creados: {groups_created}. "
            f"Omitidos (ya existían): {groups_skipped}."
        )
        click.echo(
            "No se creó ningún Administrador: usa create-admin para crear "
            "el tuyo."
        )

    @app.cli.command("seed-demo-tickets")
    def seed_demo_tickets_command() -> None:
        """Carga tickets de demostración (requiere seed-demo y seed-catalogs).

        Crea unos 40 tickets con textos realistas, repartidos en el tiempo y
        a nombre del equipo ficticio de seed-demo. No crea categorías ni
        ubicaciones: las busca por nombre entre las que ya existen. Al volver
        a ejecutarlo no duplica nada: refresca las fechas de los tickets ya
        cargados para que queden relativas al día de la ejecución. No se
        ejecuta con APP_ENV=production.
        """

        if current_app.config["APP_ENV"] == "production":
            raise click.ClickException(
                "Los datos de demostración no se cargan en producción."
            )

        try:
            result = seed_demo_tickets()
        except DemoTicketsError as error:
            raise click.ClickException(str(error)) from error

        click.echo(
            f"Tickets demo creados: {result.created}. "
            f"Actualizados (ya existían): {result.refreshed}."
        )

        for warning in result.warnings:
            click.echo(f"Aviso: {warning}")
    @app.cli.command("sla-rebuild")
    @click.option(
        "--all",
        "rebuild_all",
        is_flag=True,
        help="Recalcula también los tickets que ya tienen períodos de SLA.",
    )
    @click.option(
        "--ticket",
        "public_id",
        default=None,
        help="Limita el recálculo a un ticket (su número, con o sin #).",
    )
    def sla_rebuild_command(rebuild_all: bool, public_id: str | None) -> None:
        """Calcula los períodos de SLA de los tickets a partir de su historial.

        Por defecto solo toca los tickets que no tienen ninguno (los anteriores al
        SLA). Usa la política y el calendario vigentes hoy, porque el historial no
        guarda cuáles eran entonces. `--all` reescribe también los períodos que se
        calcularon en vivo y no se ejecuta con APP_ENV=production.
        """

        if rebuild_all and current_app.config["APP_ENV"] == "production":
            raise click.ClickException(
                "No se recalculan todos los períodos en producción: son el "
                "cálculo en vivo. Ejecuta el comando sin --all."
            )

        result = rebuild_periods(
            only_missing=not rebuild_all,
            public_id=None if public_id is None else public_id.lstrip("#"),
        )
        db.session.commit()

        click.echo(
            f"Tickets recalculados: {result.tickets}. "
            f"Períodos de SLA: {result.periods}."
        )

    @app.cli.command("sla-status")
    @click.argument("ticket_number")
    def sla_status_command(ticket_number: str) -> None:
        """Muestra el SLA de un ticket: su estado, el consumo y sus períodos."""

        ticket = db.session.scalar(
            db.select(Ticket).where(Ticket.public_id == ticket_number.lstrip("#"))
        )

        if ticket is None:
            raise click.ClickException(f"No existe el ticket {ticket_number}.")

        for line in _describe_ticket_sla(ticket):
            click.echo(line)
