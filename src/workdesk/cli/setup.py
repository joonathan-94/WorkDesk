"""Comandos de la preparación inicial: roles, catálogos y el Administrador."""

import click
from flask import Flask

from ..extensions import db
from ..models import Role, User
from ..security import PasswordPolicyError, RoleCode
from ..seeds import seed_catalogs, seed_roles
from ..users.service import (
    AdministratorAlreadyExistsError,
    DuplicateUserError,
    InvalidUserDataError,
    create_initial_administrator,
)


def register(app: Flask) -> None:
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

        # Antes de preguntar nada: sin el rol, o con un Administrador ya creado, no
        # tiene sentido pedir los datos.
        admin_role = db.session.scalar(
            db.select(Role.id).where(Role.codigo == RoleCode.ADMINISTRADOR)
        )

        if admin_role is None:
            raise click.ClickException(
                "No existe el rol ADMINISTRADOR. "
                "Ejecuta primero el comando seed-roles."
            )

        if db.session.scalar(db.select(User.id).where(User.rol_id == admin_role).limit(1)):
            raise click.ClickException("Ya existe un usuario con rol ADMINISTRADOR.")

        nombre = click.prompt("Nombre")
        apellido = click.prompt("Apellido")
        username = click.prompt("Username")
        email = click.prompt("Email")
        password = click.prompt(
            "Contraseña",
            hide_input=True,
            confirmation_prompt=True,
        )

        # Las reglas son las de cualquier alta (`users/service.py`): forma del username y
        # del correo (RN-148), unicidad y política de contraseñas. Se audita como acción
        # del sistema.
        try:
            admin = create_initial_administrator(
                nombre=nombre,
                apellido=apellido,
                username=username,
                email=email,
                password=password,
            )
            db.session.commit()
        except InvalidUserDataError as error:
            raise click.ClickException(_describe_problems(error.problems)) from error
        except DuplicateUserError as error:
            raise click.ClickException(_DUPLICATE_MESSAGES[error.field]) from error
        except (AdministratorAlreadyExistsError, PasswordPolicyError) as error:
            raise click.ClickException(str(error)) from error

        click.echo(
            f"Administrador '{admin.username}' creado correctamente."
        )


_FIELD_LABELS = {
    "nombre": "Nombre",
    "apellido": "Apellido",
    "username": "Username",
    "email": "Email",
}

_DUPLICATE_MESSAGES = {
    "username": "El username indicado ya está registrado.",
    "email": "El email indicado ya está registrado.",
    None: "El username o el email ya están registrados.",
}


def _describe_problems(problems: dict[str, str]) -> str:
    return " ".join(f"{_FIELD_LABELS[field]}: {message}" for field, message in problems.items())
