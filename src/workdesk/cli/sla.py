"""Comandos del SLA: reconstruir los períodos de los tickets y ver el de uno."""

import click
from flask import Flask, current_app

from ..extensions import db
from ..formatting import format_duration, local_datetime
from ..models import Prioridad, Ticket
from ..sla.evaluation import SlaStatus, evaluate_ticket_sla
from ..sla.periods import list_periods
from ..sla.rebuild import fill_missing_warning_dates, rebuild_periods

_SLA_STATUS_LABELS = {
    SlaStatus.DENTRO: "dentro de plazo",
    SlaStatus.PROXIMO_A_VENCER: "próximo a vencer",
    SlaStatus.VENCIDO: "vencido",
    SlaStatus.PAUSADO: "pausado",
}


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

    if snapshot.period.fecha_umbral_aviso is not None:
        lines.append(
            f"Aviso al {snapshot.period.umbral_aviso_porcentaje} %: "
            f"{local_datetime(snapshot.period.fecha_umbral_aviso)}"
        )

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


def register(app: Flask) -> None:
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
        # Los períodos abiertos antes de la fecha de aviso la reciben ahora (RN-169).
        completed = fill_missing_warning_dates()
        db.session.commit()

        click.echo(
            f"Tickets recalculados: {result.tickets}. "
            f"Períodos de SLA: {result.periods}. "
            f"Fechas de aviso completadas: {completed}."
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
