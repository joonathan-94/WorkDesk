import click
from flask import Flask

from .seeds import seed_roles


def register_commands(app: Flask) -> None:
    @app.cli.command("seed-roles")
    def seed_roles_command() -> None:
        """Carga los roles estructurales iniciales."""

        created = seed_roles()

        click.echo(f"Roles creados: {created}")