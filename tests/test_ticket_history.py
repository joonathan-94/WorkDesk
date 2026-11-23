"""Líneas legibles del historial de un ticket (`tickets/history.py`).

Es solo presentación: quién ve cada evento lo decide la consulta del historial
y quién ve su motivo, la ruta del detalle (docs/06, RN-155). Aquí se garantizan
tres cosas:

- que todo evento del vocabulario tiene su descriptor (uno nuevo no puede
  quedar mudo sin que alguien lo haya decidido, igual que pasa con su
  visibilidad y su nombre);
- que ninguna línea repite un motivo ni el texto de un comentario;
- qué cuenta cada evento.

Los eventos se construyen sin guardar: el descriptor solo lee sus valores, así
que no hace falta base de datos.
"""

import pytest

from src.workdesk.models import TicketEvent, TicketHistory
from src.workdesk.models.ticket_history import (
    DEFAULT_EVENT_VISIBILITY,
    TICKET_EVENT_LABELS,
)
from src.workdesk.tickets.history import (
    describe_history_changes,
    described_events,
)


def _entry(event, old=None, new=None, context=None) -> TicketHistory:
    return TicketHistory(
        tipo_evento=event,
        valor_anterior=old,
        valor_nuevo=new,
        contexto=context,
    )


def _lines(event, old=None, new=None, context=None) -> list[str]:
    return describe_history_changes(_entry(event, old, new, context))


# --- Vocabulario ---------------------------------------------------------------


def test_every_event_has_a_describer():
    # Si falla, el evento nuevo hay que describirlo en `tickets/history.py`
    # (aunque sea con una función que devuelva una lista vacía).
    assert described_events() == frozenset(TicketEvent)


def test_every_event_is_named_and_has_a_visibility():
    # Las tres decisiones por evento deben ir juntas: cómo se llama, quién lo ve
    # y qué cuenta.
    assert set(TICKET_EVENT_LABELS) == set(TicketEvent)
    assert set(DEFAULT_EVENT_VISIBILITY) == set(TicketEvent)


def test_an_event_outside_the_vocabulary_says_nothing():
    # El historial es append-only: una fila antigua con un evento que ya no
    # existe no debe romper el detalle.
    assert _lines("EVENTO_QUE_NO_EXISTE", new={"nombre": "X"}) == []


def test_missing_values_are_not_a_problem():
    # `valor_anterior` y `valor_nuevo` son opcionales en la base de datos.
    for event in TicketEvent:
        assert isinstance(_lines(event), list)


# --- Qué cuenta cada evento ----------------------------------------------------

LONG_TEXT = "Texto largo que no debe repetirse en el historial."

CASES = [
    pytest.param(TicketEvent.TICKET_CREADO, {}, {}, [], id="creado-sin-lineas"),
    pytest.param(
        TicketEvent.TICKET_MODIFICADO,
        {"titulo": "Wifi", "ubicacion": None},
        {"titulo": "Wifi caído", "descripcion": LONG_TEXT, "ubicacion": "Bodega"},
        [
            "Título: «Wifi» → «Wifi caído»",
            "Descripción modificada.",
            "Ubicación: — → «Bodega»",
        ],
        id="modificado-todo",
    ),
    pytest.param(
        TicketEvent.TICKET_MODIFICADO,
        {},
        {"descripcion": LONG_TEXT},
        ["Descripción modificada."],
        id="modificado-solo-descripcion",
    ),
    pytest.param(
        TicketEvent.CATEGORIA_CAMBIADA,
        {"nombre": "Redes"},
        {"nombre": "Correo"},
        ["Categoría: «Redes» → «Correo»"],
        id="categoria",
    ),
    pytest.param(
        TicketEvent.PRIORIDAD_CAMBIADA,
        {"nombre": "Media"},
        {"nombre": "Alta"},
        ["Prioridad: «Media» → «Alta»"],
        id="prioridad",
    ),
    pytest.param(
        TicketEvent.ESTADO_CAMBIADO,
        {"nombre": "Nuevo"},
        {"nombre": "En progreso"},
        ["Estado: «Nuevo» → «En progreso»"],
        id="estado",
    ),
    pytest.param(
        TicketEvent.TICKET_RESUELTO,
        {"nombre": "En progreso"},
        {"nombre": "Resuelto", "resolucion": "Reinicié el router", "ciclo": 1},
        ["Estado: «En progreso» → «Resuelto»", "Resolución: «Reinicié el router»"],
        id="resuelto-con-solucion",
    ),
    pytest.param(
        TicketEvent.TICKET_RESUELTO,
        {"nombre": "En progreso"},
        {"nombre": "Resuelto", "resolucion": None, "ciclo": 1},
        ["Estado: «En progreso» → «Resuelto»"],
        id="resuelto-sin-solucion",
    ),
    pytest.param(
        TicketEvent.TICKET_CERRADO,
        {"nombre": "Resuelto"},
        {"nombre": "Cerrado", "motivo_cierre": {"nombre": "Resolución validada"}},
        ["Estado: «Resuelto» → «Cerrado»", "Motivo de cierre: «Resolución validada»"],
        id="cerrado-con-motivo",
    ),
    pytest.param(
        TicketEvent.TICKET_REABIERTO,
        {"nombre": "Cerrado"},
        {"nombre": "En progreso"},
        ["Estado: «Cerrado» → «En progreso»"],
        id="reabierto",
    ),
    pytest.param(
        TicketEvent.VALIDACION_ACEPTADA, {}, {}, [], id="validacion-aceptada"
    ),
    pytest.param(
        TicketEvent.VALIDACION_RECHAZADA, {}, {}, [], id="validacion-rechazada"
    ),
    pytest.param(
        TicketEvent.TECNICO_ASIGNADO,
        {},
        {"nombre": "Ana Pérez"},
        ["Técnico asignado: «Ana Pérez»"],
        id="tecnico-asignado",
    ),
    pytest.param(
        TicketEvent.TECNICO_DESASIGNADO,
        {"nombre": "Ana Pérez"},
        {},
        ["Técnico desasignado: «Ana Pérez»"],
        id="tecnico-desasignado",
    ),
    pytest.param(
        TicketEvent.SOLICITANTE_AGREGADO,
        {},
        {"nombre": "Luis Rojas"},
        ["Solicitante agregado: «Luis Rojas»"],
        id="solicitante-agregado",
    ),
    pytest.param(
        TicketEvent.SOLICITANTE_RETIRADO,
        {"nombre": "Luis Rojas"},
        {},
        ["Solicitante retirado: «Luis Rojas»"],
        id="solicitante-retirado",
    ),
    pytest.param(
        TicketEvent.GRUPO_CAMBIADO,
        {},
        {"nombre": "Soporte Redes"},
        ["Grupo: — → «Soporte Redes»"],
        id="grupo-asignado",
    ),
    pytest.param(
        TicketEvent.GRUPO_CAMBIADO,
        {"nombre": "Soporte Redes"},
        {},
        ["Grupo: «Soporte Redes» → —"],
        id="grupo-quitado",
    ),
    pytest.param(
        TicketEvent.TICKET_ESCALADO,
        {"grupo": {"nombre": "Redes"}, "tecnicos": [{"nombre": "Ana"}]},
        {
            "grupo": {"nombre": "Usuarios"},
            "tecnicos": [{"nombre": "Luis"}, {"nombre": "Marta"}],
        },
        ["Grupo: «Redes» → «Usuarios»", "Técnicos: «Ana» → «Luis, Marta»"],
        id="escalado-grupo-y-tecnicos",
    ),
    pytest.param(
        TicketEvent.TICKET_ESCALADO,
        {"grupo": {"nombre": "Redes"}, "tecnicos": [{"nombre": "Ana"}]},
        {"grupo": {"nombre": "Redes"}, "tecnicos": []},
        ["Técnicos: «Ana» → —"],
        id="escalado-solo-tecnicos",
    ),
    pytest.param(
        TicketEvent.TICKET_ESCALADO,
        {"grupo": None, "tecnicos": []},
        {"grupo": {"nombre": "Redes"}, "tecnicos": []},
        ["Grupo: — → «Redes»"],
        id="escalado-solo-grupo",
    ),
    pytest.param(
        TicketEvent.COMENTARIO_AGREGADO,
        {},
        {"contenido": LONG_TEXT, "tipo": "PUBLICO"},
        ["Comentario público"],
        id="comentario-publico",
    ),
    pytest.param(
        TicketEvent.COMENTARIO_EDITADO,
        {"contenido": "antes", "tipo": "INTERNO"},
        {"contenido": LONG_TEXT, "tipo": "INTERNO"},
        ["Nota interna"],
        id="nota-editada",
    ),
    pytest.param(
        TicketEvent.COMENTARIO_ELIMINADO,
        {"contenido": LONG_TEXT, "tipo": "INTERNO"},
        {},
        ["Nota interna"],
        id="nota-eliminada",
    ),
    pytest.param(
        TicketEvent.ARCHIVO_ADJUNTADO,
        {},
        {"nombre": "captura.png"},
        ["Archivo: «captura.png»"],
        id="archivo-adjuntado",
    ),
    pytest.param(
        TicketEvent.ARCHIVO_ELIMINADO,
        {"nombre": "captura.png"},
        {},
        ["Archivo: «captura.png»"],
        id="archivo-eliminado",
    ),
    pytest.param(
        TicketEvent.RELACION_AGREGADA,
        {},
        {"tipo": "DUPLICADO", "ticket": 12},
        ["Duplicado de #12"],
        id="relacion-duplicado",
    ),
    pytest.param(
        TicketEvent.RELACION_AGREGADA,
        {},
        {"tipo": "RELACIONADO", "ticket": 12},
        ["Relacionado con #12"],
        id="relacion-relacionado",
    ),
    pytest.param(
        TicketEvent.RELACION_ELIMINADA,
        {"tipo": "RELACIONADO", "ticket": 12},
        {},
        ["Relación con #12 eliminada"],
        id="relacion-eliminada",
    ),
]


@pytest.mark.parametrize(("event", "old", "new", "expected"), CASES)
def test_each_event_tells_what_changed(event, old, new, expected):
    assert _lines(event, old, new) == expected


def test_the_type_of_a_comment_can_come_from_the_context():
    # Un evento antiguo puede no llevar el tipo en los valores.
    assert _lines(TicketEvent.COMENTARIO_AGREGADO, context={"tipo": "INTERNO"}) == [
        "Nota interna"
    ]
    assert _lines(TicketEvent.COMENTARIO_AGREGADO) == ["Comentario público"]


def test_a_relation_without_its_ticket_does_not_break():
    assert _lines(TicketEvent.RELACION_AGREGADA, new={"tipo": "RELACIONADO"}) == [
        "Relacionado con #?"
    ]
    assert _lines(TicketEvent.RELACION_ELIMINADA) == ["Relación con #? eliminada"]


def test_a_sla_breach_tells_its_objective():
    # El evento lo registra el planificador y lleva el objetivo en el contexto.
    assert _lines(TicketEvent.SLA_VENCIDO, context={"objetivo_minutos": 90}) == [
        "Venció el objetivo de resolución de 1 h 30 min"
    ]
    assert _lines(TicketEvent.SLA_VENCIDO) == ["Venció el objetivo de resolución"]


# --- Lo que nunca se cuenta ----------------------------------------------------

REASONS = {
    "motivo": "MOTIVO_DEL_EQUIPO",
    "motivo_rechazo": "MOTIVO_DEL_RECHAZO",
}


@pytest.mark.parametrize("event", list(TicketEvent))
def test_no_line_repeats_a_reason(event):
    """Los motivos los muestra la ruta del detalle, según quién mira (RN-155).

    Con cualquier forma de valores que lleve un evento y los motivos en su
    contexto, ninguna línea puede contenerlos.
    """
    values = {
        "nombre": "Algo",
        "titulo": "Título",
        "ubicacion": "Ubicación",
        "ticket": 7,
        "tipo": "RELACIONADO",
        "grupo": {"nombre": "Grupo"},
        "tecnicos": [{"nombre": "Técnico"}],
        "motivo_cierre": {"nombre": "Cierre"},
        **REASONS,
    }
    lines = _lines(event, values, values, REASONS)

    assert all(isinstance(line, str) for line in lines)

    for reason in REASONS.values():
        assert not any(reason in line for line in lines)


@pytest.mark.parametrize(
    "event",
    [
        TicketEvent.COMENTARIO_AGREGADO,
        TicketEvent.COMENTARIO_EDITADO,
        TicketEvent.COMENTARIO_ELIMINADO,
    ],
)
def test_comment_text_never_reaches_the_history(event):
    lines = _lines(
        event,
        {"contenido": LONG_TEXT, "tipo": "PUBLICO"},
        {"contenido": LONG_TEXT, "tipo": "PUBLICO"},
    )

    assert not any(LONG_TEXT in line for line in lines)
