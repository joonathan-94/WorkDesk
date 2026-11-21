"""Pantallas del centro de notificaciones (docs/11, UI-008). Las reglas están en
`notifications/service.py`; aquí solo se orquesta.

Las ven los cuatro roles, cada uno las suyas: todas las consultas filtran por el
usuario de la sesión y la notificación de otra persona responde 404, igual que una
que no existe. Todo lo que cambia algo es POST con CSRF (también «abrir», que marca
como leída: un GET no debe cambiar nada).
"""

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..security import current_actor
from . import bp
from .service import (
    VALID_VIEWS,
    VIEW_ALL,
    count_notifications,
    count_unread,
    list_notifications,
    mark_all_as_read,
    mark_as_read,
)

LIST_ENDPOINT = "notifications.list_notifications_page"


@bp.get("")
@login_required
def list_notifications_page():
    user = current_actor()
    view = _view()
    pagination = list_notifications(user, view=view, page=_page())

    return render_template(
        "notifications/list.html",
        pagination=pagination,
        view=view,
        counts=count_notifications(user),
    )


@bp.post("/<int:notification_id>/read")
@login_required
def read_notification(notification_id: int):
    """Marca una notificación como leída y vuelve al listado donde estaba."""
    if mark_as_read(current_actor(), notification_id) is None:
        abort(404)

    db.session.commit()

    return _back_to_list()


@bp.post("/<int:notification_id>/open")
@login_required
def open_notification(notification_id: int):
    """Marca la notificación como leída y abre su ticket (o vuelve al listado si es
    un aviso general). Si el usuario ya no puede ver el ticket, el propio ticket
    responde 404: abrirlo no es un permiso."""
    notification = mark_as_read(current_actor(), notification_id)

    if notification is None:
        abort(404)

    ticket = notification.ticket
    db.session.commit()

    if ticket is None:
        return _back_to_list()

    return redirect(url_for("tickets.detail", public_id=ticket.public_id))


@bp.post("/read-all")
@login_required
def read_all_notifications():
    mark_all_as_read(current_actor())
    db.session.commit()

    return _back_to_list()


@bp.get("/unread-count")
@login_required
def unread_count():
    """El número de notificaciones sin leer, en JSON, para la campana.

    La consulta el navegador cada 30 segundos (docs/10, sección 89); además, el
    contador se actualiza al navegar entre páginas. No se guarda en caché.
    """
    response = jsonify(unread=count_unread(current_actor()))
    response.headers["Cache-Control"] = "no-store"

    return response


# --- Piezas comunes -----------------------------------------------------------


def _view() -> str:
    view = request.values.get("vista", VIEW_ALL)

    return view if view in VALID_VIEWS else VIEW_ALL


def _page() -> int:
    try:
        return max(int(request.values.get("page", 1)), 1)
    except ValueError:
        return 1


def _back_to_list():
    """Vuelve al listado, con el filtro y la página en que estaba la persona."""
    return redirect(
        url_for(
            LIST_ENDPOINT,
            vista=_view() if _view() != VIEW_ALL else None,
            page=_page() if _page() > 1 else None,
        )
    )
