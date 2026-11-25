"""Comandos que cargan datos de demostración (solo desarrollo)."""

import os

import click
from flask import Flask, current_app

from .. import settings
from ..configuration import value_of
from ..security import PasswordPolicyError, validate_password_policy
from ..seeds import (
    DemoNotificationsError,
    DemoTicketsError,
    seed_demo_groups,
    seed_demo_notifications,
    seed_demo_tickets,
    seed_demo_users,
    seed_roles,
)

# Variable de entorno opcional con la contraseña de los usuarios demo, para
# ejecutar `seed-demo` sin interacción. Nunca se guarda ni se muestra.
DEMO_PASSWORD_ENV = "WORKDESK_DEMO_PASSWORD"


def register(app: Flask) -> None:
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
                min_length=value_of(settings.PASSWORD_MIN_LENGTH),
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

        Crea decenas de tickets con textos realistas, repartidos en el tiempo
        y a nombre del equipo ficticio de seed-demo. No crea categorías ni
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

    @app.cli.command("seed-demo-notifications")
    @click.option(
        "--username",
        "usernames",
        multiple=True,
        help="Cuenta que recibe los avisos (se puede repetir). Sin ella, el equipo de seed-demo.",
    )
    def seed_demo_notifications_command(usernames: tuple[str, ...]) -> None:
        """Carga notificaciones de ejemplo para ver el centro de notificaciones.

        Cada aviso apunta a un ticket que esa persona puede ver, así que necesita
        tickets (por ejemplo, los de seed-demo-tickets). Con --username se cargan
        para esa cuenta (por ejemplo, la del Administrador). No repite avisos y no
        se ejecuta con APP_ENV=production.
        """

        if current_app.config["APP_ENV"] == "production":
            raise click.ClickException(
                "Los datos de demostración no se cargan en producción."
            )

        try:
            result = seed_demo_notifications(list(usernames) or None)
        except DemoNotificationsError as error:
            raise click.ClickException(str(error)) from error

        click.echo(f"Notificaciones demo creadas: {result.created}.")

        for username in result.without_tickets:
            click.echo(
                f"Aviso: {username} no ve ningún ticket, así que no se le crearon avisos."
            )
