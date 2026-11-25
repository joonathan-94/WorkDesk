"""Comandos de la base de conocimiento (solo desarrollo, por ahora)."""

import click
from flask import Flask, current_app

from ..seeds import DemoArticlesError, seed_demo_articles


def register(app: Flask) -> None:
    @app.cli.command("seed-demo-articles")
    def seed_demo_articles_command() -> None:
        """Carga artículos de ejemplo en la base de conocimiento.

        Requiere seed-demo (los autores) y seed-catalogs (las categorías). Usa las
        categorías Redes, Hardware, Correo e Impresoras si existen. No duplica los
        artículos ya cargados y no se ejecuta con APP_ENV=production.
        """

        if current_app.config["APP_ENV"] == "production":
            raise click.ClickException(
                "Los datos de demostración no se cargan en producción."
            )

        try:
            result = seed_demo_articles()
        except DemoArticlesError as error:
            raise click.ClickException(str(error)) from error

        click.echo(
            f"Artículos demo creados: {result.created}. "
            f"Omitidos (ya existían): {result.skipped}."
        )

        for warning in result.warnings:
            click.echo(f"Aviso: {warning}")
