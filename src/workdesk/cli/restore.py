"""El comando que restaura un respaldo (`backups/restore.py`)."""

from pathlib import Path

import click
from flask import Flask, current_app

from ..backups import BackupError
from ..backups.package import SIGNATURE_LABELS, parse_moment, resolve_backup
from ..backups.restore import RestorePlan, RestoreRefused, plan_restore, restore_backup
from ..formatting import local_datetime
from ..system.migrations import REVISION_LABELS
from .backups import content_line, plural


def _describe(plan: RestorePlan) -> None:
    created = parse_moment(plan.manifest.get("creado_en"))
    click.echo(f"Respaldo: {plan.path.name}" + (f" (creado el {local_datetime(created)})" if created else ""))
    click.echo(f"Contiene: {content_line(plan.manifest)}.")
    click.echo(f"Firma: {SIGNATURE_LABELS[plan.signature]}")
    click.echo(f"Migraciones: {REVISION_LABELS[plan.revision]}")
    click.echo("")
    click.echo("Se reemplazará, sin vuelta atrás salvo con otro respaldo:")

    if plan.current is None:
        click.echo(f"  - la base {plan.database} (esquema {plan.schema}), que no tiene datos de WorkDesk;")
    else:
        current = plan.current
        click.echo(
            f"  - la base {plan.database} (esquema {plan.schema}), que hoy tiene "
            f"{plural(current.tickets, 'ticket', 'tickets')}, "
            f"{plural(current.users, 'usuario', 'usuarios')} y "
            f"{plural(current.attachments, 'adjunto', 'adjuntos')};"
        )

    click.echo(f"  - los adjuntos de {current_app.config['UPLOADS_DIR']}.")


def _report(result) -> None:
    if result.safety_backup is not None:
        click.echo(f"Respaldo previo de lo que había: {result.safety_backup.path}")

    click.echo(f"Base restaurada. Adjuntos restaurados: {result.attachments}.")
    click.echo("Todas las sesiones se cerraron: cada persona debe iniciar sesión de nuevo.")

    for warning in result.warnings:
        click.echo(f"Aviso: {warning}")

    if result.plan.needs_upgrade:
        click.echo("El respaldo es de una versión anterior. Ponla al día ahora con:")
        click.echo("  python -m flask --app src.workdesk db upgrade")

    click.echo("Vuelve a iniciar WorkDesk y el planificador.")


def register(app: Flask) -> None:
    @app.cli.command("backup-restore")
    @click.argument("backup")
    @click.option(
        "--accept-other-key",
        is_flag=True,
        help="Acepta un respaldo firmado con otra SECRET_KEY (su contenido se comprueba igual).",
    )
    @click.option(
        "--skip-safety-backup",
        is_flag=True,
        help="No respalda antes lo actual (solo si la base está dañada y no se puede respaldar).",
    )
    @click.option(
        "--ignore-connections",
        is_flag=True,
        help="Restaura aunque haya otras conexiones a la base (por ejemplo, un pgAdmin abierto).",
    )
    def backup_restore_command(
        backup: str, accept_other_key: bool, skip_safety_backup: bool, ignore_connections: bool
    ) -> None:
        """Reemplaza la base de datos y los adjuntos por los de un respaldo.

        BACKUP es el nombre de un respaldo de BACKUPS_DIR o la ruta a uno. Antes lo comprueba
        entero, exige que nadie más esté conectado, pide escribir el nombre de la base y
        respalda lo actual. La base se restaura en una sola transacción: si algo falla, queda
        como estaba. Todas las sesiones se cierran.
        """
        try:
            plan = plan_restore(resolve_backup(Path(current_app.config["BACKUPS_DIR"]), backup), accept_other_key=accept_other_key)
        except FileNotFoundError as error:
            raise click.ClickException(str(error)) from error
        except RestoreRefused as refused:
            for problem in refused.problems:
                click.echo(f"Problema: {problem}")

            raise click.ClickException("No se restauró nada.") from refused

        _describe(plan)
        click.echo(
            "No se creará un respaldo previo de lo actual."
            if skip_safety_backup or plan.current is None
            else "Antes se creará un respaldo de lo actual."
        )
        typed = click.prompt(f"Escribe el nombre de la base ({plan.database}) para confirmar", default="", show_default=False)

        if typed.strip() != plan.database:
            raise click.ClickException("El nombre no coincide. No se restauró nada.")

        try:
            result = restore_backup(plan, safety_backup=not skip_safety_backup, ignore_connections=ignore_connections)
        except BackupError as error:
            raise click.ClickException(str(error)) from error

        _report(result)
