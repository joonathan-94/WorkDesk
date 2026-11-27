"""La exportación de la auditoría (RF-099 a RF-101, RF-109), solo para el Administrador.

Exporta la pestaña que se ve, con sus filtros, desde la misma consulta de la pantalla
(`audit_statement`). Los nombres son los de la pantalla (`audit/labels.py`); además va el
código de la acción, que es lo estable para filtrar en una hoja de cálculo. Los valores
anterior y nuevo van como JSON compacto.

Se lee por tramos de `CHUNK` filas y las personas y los tickets de cada tramo se cargan en
lote (`page_context`), como en la pantalla.
"""

import json

from ..exports import Table
from ..extensions import db
from ..models.admin_audit_log import AuditResult
from ..tickets.history import describe_history_changes
from .labels import action_label, entity_label
from .queries import VIEW_LABELS, AuditFilters, AuditView, audit_statement, page_context

CHUNK = 1000

RESULT_LABELS = {AuditResult.EXITOSO.value: "Correcto", AuditResult.FALLIDO.value: "Fallido"}

HEADERS = {
    AuditView.ADMINISTRATIVA: (
        "Fecha",
        "Quién",
        "Qué pasó",
        "Código de la acción",
        "Sobre",
        "Número",
        "Detalle",
        "Resultado",
        "Motivo",
        "Antes",
        "Después",
        "IP",
        "Navegador",
    ),
    AuditView.ACCESOS: (
        "Fecha",
        "Cuenta",
        "Escrito como usuario",
        "Qué pasó",
        "Causa",
        "Resultado",
        "IP",
        "Navegador",
    ),
    AuditView.TICKETS: (
        "Fecha",
        "Ticket",
        "Quién",
        "Qué pasó",
        "Visibilidad",
        "Cambios",
        "Motivo",
        "Antes",
        "Después",
    ),
}


def audit_table(view: AuditView, filters: AuditFilters) -> Table:
    return Table(f"Auditoría - {VIEW_LABELS[view]}", HEADERS[view], _rows(view, filters))


def _rows(view: AuditView, filters: AuditFilters):
    statement = audit_statement(view, filters)
    offset = 0
    line = _LINES[view]

    while True:
        rows = list(db.session.scalars(statement.limit(CHUNK).offset(offset)))

        if not rows:
            return

        context = page_context(view, rows)

        for row in rows:
            yield line(row, context)

        if len(rows) < CHUNK:
            return

        offset += CHUNK


def _person(user_id, context, fallback="Sistema"):
    if user_id is None:
        return fallback

    user = context.users.get(user_id)

    return f"{user.nombre} {user.apellido} ({user.username})" if user else str(user_id)


def _json(value):
    if value is None:
        return None

    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _administrative(row, context) -> list:
    return [
        row.fecha_hora,
        _person(row.actor_usuario_id, context),
        action_label(row.accion),
        row.accion,
        entity_label(row.entidad_tipo) if row.entidad_tipo else None,
        row.entidad_id,
        row.detalle,
        RESULT_LABELS.get(row.resultado, row.resultado),
        row.motivo,
        _json(row.valor_anterior),
        _json(row.valor_nuevo),
        row.ip_origen,
        row.user_agent,
    ]


def _access(row, context) -> list:
    return [
        row.fecha_hora,
        _person(row.usuario_id, context, fallback=None),
        row.identificador_intentado,
        row.etiqueta,
        row.causa,
        RESULT_LABELS.get(row.resultado, row.resultado),
        row.ip_origen,
        row.user_agent,
    ]


def _ticket(row, context) -> list:
    number = context.tickets.get(row.ticket_id)

    return [
        row.fecha_hora,
        int(number) if number else None,
        _person(row.actor_usuario_id, context),
        row.evento_nombre,
        "Interno" if row.visibilidad == "INTERNO" else "Público",
        "; ".join(describe_history_changes(row)) or None,
        (row.contexto or {}).get("motivo"),
        _json(row.valor_anterior),
        _json(row.valor_nuevo),
    ]


_LINES = {
    AuditView.ADMINISTRATIVA: _administrative,
    AuditView.ACCESOS: _access,
    AuditView.TICKETS: _ticket,
}
