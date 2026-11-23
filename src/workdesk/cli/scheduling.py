"""El comando del planificador (`src/workdesk/scheduler.py`)."""

import click
from flask import Flask, current_app

from ..scheduler import SchedulerResult, run_loop, run_once


def register(app: Flask) -> None:
    @app.cli.command("run-scheduler")
    @click.option(
        "--once",
        is_flag=True,
        help="Ejecuta las tareas una sola vez y termina (para cron o el Programador "
        "de tareas de Windows).",
    )
    @click.option(
        "--interval",
        type=click.IntRange(min=1),
        default=None,
        help="Segundos entre pasadas en modo bucle (por defecto, "
        "SCHEDULER_INTERVAL_SECONDS).",
    )
    def run_scheduler_command(once: bool, interval: int | None) -> None:
        """Avisa de los SLA próximos a vencer o vencidos y cierra los tickets Resueltos
        que nadie validó.

        Sin opciones se queda en marcha y repite las tareas cada pocos segundos (se
        detiene con Ctrl+C). Con --once las ejecuta una vez. Las tareas se pueden
        repetir sin riesgo: no duplican avisos ni cierres.
        """

        def report(result: SchedulerResult) -> None:
            click.echo(
                f"SLA próximo a vencer: {result.warnings}. "
                f"SLA vencido: {result.breaches}. "
                f"Tickets cerrados automáticamente: {result.closed}. "
                f"Errores: {result.failures}."
            )

        if once:
            result = run_once()
            report(result)

            if result.failures:
                raise click.ClickException(
                    "Algunos elementos fallaron: revisa el log (instance/logs)."
                )

            return

        seconds = interval or current_app.config["SCHEDULER_INTERVAL_SECONDS"]
        click.echo(f"Planificador en marcha (cada {seconds} s). Ctrl+C para detenerlo.")

        try:
            # En el bucle solo se informa cuando hubo algo que hacer.
            run_loop(
                seconds,
                on_result=lambda result: report(result) if any(vars(result).values()) else None,
            )
        except KeyboardInterrupt:
            click.echo("Planificador detenido.")
