"""Las pantallas de respaldos (UI-028) y de estado del sistema (UI-029), solo de lectura.

Los respaldos se crean y se restauran por comandos, nunca desde la web (`docs/12`, fase 8):
quien puede restaurar es quien administra el servidor, y una restauración no puede ocurrir
mientras la propia aplicación atiende peticiones. Estas pantallas muestran lo que hay y qué
comando usar.
"""

from datetime import UTC, datetime
from pathlib import Path

from flask import abort, current_app, render_template
from sqlalchemy import select

from ..audit import AuditAction
from ..audit.labels import action_label
from ..backups.package import (
    SIGNATURE_LABELS,
    Signature,
    leftover_temporaries,
    list_backups,
)
from ..extensions import db
from ..models import AdminAuditLog
from ..security import admin_only, can_view_system, current_actor
from ..system.migrations import REVISION_LABELS, RevisionMatch, compare_revision
from ..system.status import HEALTH_LABELS, ago, overall, system_status
from . import bp

RECENT_EVENTS = 10
BACKUP_EVENTS = (AuditAction.RESPALDO_CREADO, AuditAction.RESPALDO_RESTAURADO)


def _require_system_view() -> None:
    # Dos capas: `admin_only` en la ruta y la política, que nombra el requisito.
    if not can_view_system(current_actor()):
        abort(403)


@bp.get("/system")
@admin_only
def system_status_page():
    _require_system_view()
    components = system_status()

    return render_template(
        "admin/system.html",
        components=components,
        overall=overall(components),
        health_labels=HEALTH_LABELS,
    )


def _recent_backup_events():
    return db.session.scalars(
        select(AdminAuditLog)
        .where(AdminAuditLog.accion.in_(BACKUP_EVENTS))
        .order_by(AdminAuditLog.fecha_hora.desc(), AdminAuditLog.id.desc())
        .limit(RECENT_EVENTS)
    ).all()


@bp.get("/backups")
@admin_only
def backups():
    _require_system_view()
    config = current_app.config
    folder = Path(config["BACKUPS_DIR"])
    rows = [
        (info, compare_revision(info.revision) if info.manifest else None)
        for info in list_backups(folder, config["SECRET_KEY"])
    ]

    return render_template(
        "admin/backups.html",
        rows=rows,
        folder=folder,
        leftovers=leftover_temporaries(folder),
        events=_recent_backup_events(),
        now=datetime.now(UTC),
        ago=ago,
        action_label=action_label,
        signature_labels=SIGNATURE_LABELS,
        revision_labels=REVISION_LABELS,
        Signature=Signature,
        RevisionMatch=RevisionMatch,
    )
