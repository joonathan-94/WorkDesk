import click
from flask import Flask

from .extensions import db
from .models import Role, User
from .security import hash_password
from .seeds import seed_roles


def register_commands(app: Flask) -> None:
    @app.cli.command("seed-roles")
    def seed_roles_command() -> None:
        """Carga los roles estructurales iniciales."""

        created = seed_roles()

        click.echo(f"Roles creados: {created}")

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

        if len(password) < 12:
            raise click.ClickException(
                "La contraseña debe tener al menos 12 caracteres."
            )

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