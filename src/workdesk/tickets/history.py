"""Cómo se cuenta cada evento del historial de un ticket (docs/11, UI-005).

El historial guarda datos (`valor_anterior`, `valor_nuevo` y `contexto`); aquí
se convierten en las líneas legibles que ve quien consulta el ticket. Es solo
presentación: quién puede ver cada evento lo decide la consulta
(`list_ticket_history`) y quién puede ver su motivo, la ruta del detalle. Por
eso **ninguna línea incluye un motivo** (docs/06, RN-155).

Para describir un evento nuevo basta con escribir una función y registrarla con
`@describes(...)`. Un test comprueba que todo evento del vocabulario tiene su
descriptor, aunque sea para no decir nada.
"""

from collections.abc import Callable

from ..models import TicketEvent, TicketHistory

# Recibe `(valor_anterior, valor_nuevo, evento)` y devuelve las líneas.
Describer = Callable[[dict, dict, TicketHistory], list[str]]

_DESCRIBERS: dict[TicketEvent, Describer] = {}


def describes(*events: TicketEvent):
    """Registra la función como descriptor de esos eventos."""

    def register(function: Describer) -> Describer:
        for event in events:
            _DESCRIBERS[event] = function

        return function

    return register


def describe_history_changes(entry: TicketHistory) -> list[str]:
    """Líneas legibles con lo que cambió en un evento del historial.

    **Nunca incluye el motivo** de un cambio de prioridad, de una espera, de un
    cierre ni de un escalamiento: quién puede verlo lo decide la ruta. Un
    evento que no es del vocabulario (o que no tiene nada que contar) devuelve
    una lista vacía.
    """
    try:
        event = TicketEvent(entry.tipo_evento)
    except ValueError:
        return []

    describer = _DESCRIBERS.get(event)

    if describer is None:
        return []

    return describer(entry.valor_anterior or {}, entry.valor_nuevo or {}, entry)


def described_events() -> frozenset[TicketEvent]:
    """Los eventos que tienen descriptor (para el test de completitud)."""
    return frozenset(_DESCRIBERS)


def _shown(value) -> str:
    return "—" if value is None else f"«{value}»"


def _arrow(label: str, old: dict, new: dict, key: str = "nombre") -> list[str]:
    """«Etiqueta: «antes» → «después»» con los nombres guardados."""
    return [f"{label}: {_shown(old.get(key))} → {_shown(new.get(key))}"]


# --- Datos del ticket -------------------------------------------------------


@describes(TicketEvent.TICKET_CREADO)
def _nothing(old, new, entry):
    # El título y la descripción ya están en el propio ticket.
    return []


@describes(TicketEvent.TICKET_MODIFICADO)
def _modified(old, new, entry):
    lines = []

    if "titulo" in new:
        lines.append(f"Título: {_shown(old.get('titulo'))} → {_shown(new['titulo'])}")

    if "descripcion" in new:
        # El texto completo no se repite en el historial.
        lines.append("Descripción modificada.")

    if "ubicacion" in new:
        lines.append(
            "Ubicación: "
            f"{_shown(old.get('ubicacion'))} → {_shown(new['ubicacion'])}"
        )

    return lines


@describes(TicketEvent.CATEGORIA_CAMBIADA)
def _category_changed(old, new, entry):
    return _arrow("Categoría", old, new)


@describes(TicketEvent.PRIORIDAD_CAMBIADA)
def _priority_changed(old, new, entry):
    return _arrow("Prioridad", old, new)


# --- Estado, resolución y cierre -----------------------------------------------


@describes(
    TicketEvent.ESTADO_CAMBIADO,
    TicketEvent.TICKET_RESUELTO,
    TicketEvent.TICKET_CERRADO,
    TicketEvent.TICKET_REABIERTO,
)
def _state_changed(old, new, entry):
    lines = _arrow("Estado", old, new)

    # La explicación de la solución es pública y solo sobrevive aquí cuando el
    # ticket se reabre y se resuelve de nuevo.
    if new.get("resolucion"):
        lines.append(f"Resolución: {_shown(new['resolucion'])}")

    if new.get("motivo_cierre"):
        lines.append(
            f"Motivo de cierre: {_shown(new['motivo_cierre'].get('nombre'))}"
        )

    return lines


@describes(TicketEvent.VALIDACION_ACEPTADA, TicketEvent.VALIDACION_RECHAZADA)
def _validation(old, new, entry):
    # El motivo de un rechazo lo muestra la ruta (es público); aquí no hay nada
    # más que decir que lo que indica el nombre del evento.
    return []


# --- Personas y organización ----------------------------------------------------


@describes(TicketEvent.TECNICO_ASIGNADO)
def _technician_assigned(old, new, entry):
    return [f"Técnico asignado: {_shown(new.get('nombre'))}"]


@describes(TicketEvent.TECNICO_DESASIGNADO)
def _technician_unassigned(old, new, entry):
    return [f"Técnico desasignado: {_shown(old.get('nombre'))}"]


@describes(TicketEvent.SOLICITANTE_AGREGADO)
def _requester_added(old, new, entry):
    return [f"Solicitante agregado: {_shown(new.get('nombre'))}"]


@describes(TicketEvent.SOLICITANTE_RETIRADO)
def _requester_removed(old, new, entry):
    return [f"Solicitante retirado: {_shown(old.get('nombre'))}"]


@describes(TicketEvent.GRUPO_CAMBIADO)
def _group_changed(old, new, entry):
    return _arrow("Grupo", old, new)


@describes(TicketEvent.TICKET_ESCALADO)
def _escalated(old, new, entry):
    lines = []
    old_group = (old.get("grupo") or {}).get("nombre")
    new_group = (new.get("grupo") or {}).get("nombre")
    old_techs = [t.get("nombre") for t in old.get("tecnicos") or []]
    new_techs = [t.get("nombre") for t in new.get("tecnicos") or []]

    if old_group != new_group:
        lines.append(f"Grupo: {_shown(old_group)} → {_shown(new_group)}")

    if old_techs != new_techs:
        lines.append(
            f"Técnicos: {_shown(', '.join(old_techs) or None)} → "
            f"{_shown(', '.join(new_techs) or None)}"
        )

    return lines


# --- Comentarios, archivos y relaciones ---------------------------------------------


@describes(
    TicketEvent.COMENTARIO_AGREGADO,
    TicketEvent.COMENTARIO_EDITADO,
    TicketEvent.COMENTARIO_ELIMINADO,
)
def _comment(old, new, entry):
    # Solo el tipo: el texto nunca se repite en el historial.
    kind = (new or old).get("tipo") or (entry.contexto or {}).get("tipo")

    return ["Nota interna" if kind == "INTERNO" else "Comentario público"]


@describes(TicketEvent.ARCHIVO_ADJUNTADO, TicketEvent.ARCHIVO_ELIMINADO)
def _file(old, new, entry):
    return [f"Archivo: {_shown((new or old).get('nombre'))}"]


@describes(TicketEvent.RELACION_AGREGADA)
def _relation_added(old, new, entry):
    other = f"#{new.get('ticket', '?')}"

    if new.get("tipo") == "DUPLICADO":
        return [f"Duplicado de {other}"]

    return [f"Relacionado con {other}"]


@describes(TicketEvent.RELACION_ELIMINADA)
def _relation_removed(old, new, entry):
    return [f"Relación con #{old.get('ticket', '?')} eliminada"]
