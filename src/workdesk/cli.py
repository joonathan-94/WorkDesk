import os

import click
from flask import Flask, current_app

from .extensions import db
from .models import Role, User
from .security import (
    PasswordPolicyError,
    hash_password,
    validate_password_policy,
)
from .seeds import seed_catalogs, seed_demo_users, seed_roles

# Variable de entorno opcional con la contraseña de los usuarios demo, para
# ejecutar `seed-demo` sin interacción. Nunca se guarda ni se muestra.
DEMO_PASSWORD_ENV = "WORKDESK_DEMO_PASSWORD"


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
            f"prioridades: {created['prioridades']}, "
            f"categorías: {created['categorias']}, "
            f"motivos de cierre: {created['motivos_cierre']}."
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
        """Carga usuarios de demostración (equipo de soporte ficticio).

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
        click.echo(
            "No se creó ningún Administrador: usa create-admin para crear "
            "el tuyo."
        )