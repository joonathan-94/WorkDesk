"""Comandos de los respaldos: crearlos, comprobarlos y listarlos (ver `backups/`)."""

from pathlib import Path

import click
from flask import Flask, current_app

from ..backups import BackupError, create_backup, list_backups, verify_backup
from ..backups.package import (
    SIGNATURE_LABELS,
    leftover_temporaries,
    parse_moment,
    resolve_backup,
)
from ..backups.postgres import find_tool
from ..formatting import format_size, local_datetime


def _folder() -> Path:
    return Path(current_app.config["BACKUPS_DIR"])


def plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def content_line(manifest: dict) -> str:
    content = manifest.get("contenido", {})

    return (
        f"{plural(content.get('tickets', 0), 'ticket', 'tickets')}, "
        f"{plural(content.get('usuarios', 0), 'usuario', 'usuarios')} y "
        f"{plural(content.get('adjuntos_copiados', 0), 'adjunto', 'adjuntos')} "
        f"({format_size(content.get('bytes_adjuntos', 0))})"
    )


def _created_at(info) -> str:
    return "fecha desconocida" if info.created_at is None else local_datetime(info.created_at)


def _report_verification(path: Path) -> None:
    pg_restore = find_tool("pg_restore", current_app.config.get("PG_BIN_DIR"))
    result = verify_backup(path, secret_key=current_app.config["SECRET_KEY"], pg_restore=pg_restore)
    created = parse_moment((result.manifest or {}).get("creado_en"))

    click.echo(f"Respaldo: {path.name}" + (f" (creado el {local_datetime(created)})" if created else ""))
    click.echo(f"Huella del paquete: {result.checksum}")
    click.echo(f"Firma: {SIGNATURE_LABELS[result.signature]}")
    click.echo(f"Archivos correctos: {result.files_ok} de {result.files_total}")

    if result.dump_entries is not None:
        click.echo(f"Volcado de la base: se puede leer ({result.dump_entries} elementos)")

    for warning in result.warnings:
        click.echo(f"Aviso: {warning}")

    for problem in result.problems:
        click.echo(f"Problema: {problem}")

    if not result.ok:
        raise click.ClickException("El respaldo no se debe restaurar.")

    click.echo("Resultado: el respaldo está completo y es de esta instalación.")


def _report_list() -> None:
    folder = _folder()
    backups = list_backups(folder, current_app.config["SECRET_KEY"])
    click.echo(f"Respaldos en {folder}:" if backups else f"No hay respaldos en {folder}.")

    for info in backups:
        if info.manifest is None:
            click.echo(f"  {info.name} · {format_size(info.size)} · {info.problem}")
            continue

        click.echo(
            f"  {_created_at(info)} · {info.name} · {format_size(info.size)} · "
            f"{content_line(info.manifest)} · firma: {SIGNATURE_LABELS[info.signature]}"
            + ("" if info.has_checksum else " · sin archivo .sha256")
        )

    leftovers = leftover_temporaries(folder)

    if leftovers:
        click.echo(
            "Restos de respaldos interrumpidos (se pueden borrar): "
            + ", ".join(path.name for path in leftovers)
        )


def register(app: Flask) -> None:
    @app.cli.command("backup-create")
    def backup_create_command() -> None:
        """Crea un respaldo de la base de datos y los adjuntos en BACKUPS_DIR.

        La aplicación puede seguir en uso: el volcado y la lista de adjuntos salen de una
        misma foto de la base. Queda registrado en la auditoría, también si falla.
        """
        try:
            result = create_backup()
        except BackupError as error:
            raise click.ClickException(f"No se creó el respaldo. {error}") from error

        click.echo(f"Respaldo creado: {result.path}")
        click.echo(f"Contenido: {content_line(result.manifest)}.")
        click.echo(f"Tamaño: {format_size(result.size)}.")
        click.echo(f"SHA-256: {result.sha256}")

        for warning in result.warnings:
            click.echo(f"Aviso: {warning}")

    @app.cli.command("backup-verify")
    @click.argument("backup", required=False)
    def backup_verify_command(backup: str | None) -> None:
        """Comprueba un respaldo sin restaurarlo (por defecto, el más reciente).

        BACKUP es el nombre de un respaldo de BACKUPS_DIR o la ruta a uno. No necesita la
        base de datos. Termina con error si el respaldo no se debe restaurar.
        """
        try:
            path = resolve_backup(_folder(), backup)
            _report_verification(path)
        except (FileNotFoundError, BackupError) as error:
            raise click.ClickException(str(error)) from error

    @app.cli.command("backup-list")
    def backup_list_command() -> None:
        """Lista los respaldos de BACKUPS_DIR, del más reciente al más antiguo.

        Solo lee sus manifiestos: para comprobar uno entero, usa backup-verify.
        """
        _report_list()
