"""Creación de tickets (docs/06, RN-153 y RN-175).
"""

import hashlib

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ... import settings
from ...catalogs.service import list_locations, list_priorities
from ...configuration import value_of
from ...extensions import db
from ...models.ticket import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from ...security import can_choose_requesters, can_create_ticket, current_actor
from .. import bp
from ..attachments import add_attachments, discard_files
from ..forms import TicketForm
from ..service import (
    TicketRuleError,
    categories_for_selection,
    create_ticket,
    list_requester_candidates,
    location_required,
)
from ..similar import find_similar_tickets
from ..storage import MAX_FILES_PER_REQUEST, allowed_extensions
from .common import requester_choices

# Prioridad que se ofrece preseleccionada al crear un ticket (docs/11, UI-004).
DEFAULT_PRIORITY_CODE = "MEDIA"

# El campo oculto que dice qué advertencia de duplicados ya vio la persona.
CONFIRMATION_FIELD = "confirmado"


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_ticket():
    # La autorización se comprueba en backend; ocultar el enlace no basta.
    if not can_create_ticket(current_user):
        abort(403)

    choose_requesters = can_choose_requesters(current_user)
    priorities = list_priorities("activo")

    form = TicketForm(
        category_choices=[
            (category.id, category.nombre)
            for category in categories_for_selection()
        ],
        priority_choices=[
            (priority.id, priority.nombre) for priority in priorities
        ],
        location_choices=[
            (location.id, location.nombre)
            for location in list_locations("activo")
        ],
        location_required=location_required(),
        requester_choices=(
            requester_choices(list_requester_candidates())
            if choose_requesters
            else None
        ),
        # Solo al abrir el formulario: un envío sin prioridad debe fallar en
        # lugar de quedar en Media sin que nadie la haya elegido.
        **_initial_values(priorities, is_new_form=request.method == "GET"),
    )

    similar = []
    signature = None

    if form.validate_on_submit():
        signature = _signature(form.titulo.data, form.categoria.data)

        # Solo se avisa si la persona no confirmó ya esta misma combinación de título y
        # categoría: si los cambia, se vuelve a comprobar. Nunca impide crear.
        if request.form.get(CONFIRMATION_FIELD) != signature:
            similar = find_similar_tickets(
                current_user,
                title=form.titulo.data,
                category_id=form.categoria.data,
            )

    # `signature` solo existe si el formulario es válido: se crea si no hay nada que advertir.
    if signature and not similar:
        # El Solicitante siempre es su propio solicitante; el personal
        # elige a quién (puede ser nadie).
        requester_ids = (
            form.solicitantes.data if choose_requesters else [current_user.id]
        )

        paths: list[str] = []

        try:
            ticket = create_ticket(
                actor=current_actor(),
                title=form.titulo.data,
                description=form.descripcion.data,
                category_id=form.categoria.data,
                priority_id=form.prioridad.data,
                location_id=form.ubicacion.data,
                requester_ids=requester_ids,
            )
            # En la misma transacción: si un archivo no es válido, no se crea el ticket.
            attachments = add_attachments(
                ticket,
                actor=current_actor(),
                uploads=request.files.getlist("archivos"),
            )
            paths = [attachment.ruta_archivo for attachment in attachments]
            db.session.commit()
        except TicketRuleError as error:
            # Por ejemplo, un valor de catálogo desactivado mientras se
            # rellenaba el formulario, o un archivo no permitido.
            db.session.rollback()
            flash(str(error), "error")
        except Exception:
            # Si la base de datos falla tras guardar los archivos, se borran.
            db.session.rollback()
            discard_files(paths)

            raise
        else:
            flash(f"Ticket #{ticket.public_id} creado correctamente.", "success")

            return redirect(
                url_for("tickets.detail", public_id=ticket.public_id)
            )

    return render_template(
        "tickets/new.html",
        form=form,
        choose_requesters=choose_requesters,
        max_title=MAX_TITLE_LENGTH,
        max_description=MAX_DESCRIPTION_LENGTH,
        similar=similar,
        # Un navegador no conserva los archivos elegidos al volver a mostrar la página.
        files_to_choose_again=_chose_files(),
        max_files=min(MAX_FILES_PER_REQUEST, value_of(settings.UPLOAD_MAX_FILES_PER_TICKET)),
        max_upload=value_of(settings.UPLOAD_MAX_BYTES),
        allowed_extensions=allowed_extensions(),
        confirmation=signature if similar else None,
        confirmation_field=CONFIRMATION_FIELD,
    )


def _chose_files() -> bool:
    return any(upload.filename for upload in request.files.getlist("archivos"))


def _signature(title: str, category_id: int) -> str:
    return hashlib.sha256(f"{category_id}|{title}".encode()).hexdigest()[:32]


def _initial_values(priorities, *, is_new_form: bool) -> dict:
    """Valores con los que arranca el formulario recién abierto."""
    if not is_new_form:
        return {}

    default = next(
        (p for p in priorities if p.codigo == DEFAULT_PRIORITY_CODE),
        None,
    )

    return {} if default is None else {"prioridad": default.id}
