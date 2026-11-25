"""Qué avisos se envían y a quién, y lo que el Administrador puede apagar (RF-087 y RF-121;
docs/06, RN-97 y RN-172; docs/11, UI-024).

**El catálogo (`RULES`) es la lista de todos los avisos que WorkDesk sabe enviar**, cada
uno como la pareja *evento → destinatarios*. El Administrador solo puede **apagar** parejas
del catálogo (o volver a encenderlas): no puede crear una nueva, así que nunca puede hacer
que a un Solicitante le llegue algo interno. Las que una regla de negocio exige (RN-95 y
RN-96) no se pueden apagar. No es un motor de reglas: quién es cada destinatario en cada
operación lo sigue decidiendo `notifications/events.py`.

Se guarda **solo lo apagado**, como una lista JSON en la tabla `configuracion`: así, sin
nada guardado se envía todo y un aviso nuevo nace encendido.
"""

import json
import logging
from dataclasses import dataclass
from enum import StrEnum

from ..configuration import document_token, save_document, stored_text
from ..models import NotificationEvent

logger = logging.getLogger(__name__)

TABLE_KEY = "notificaciones.desactivadas"

E = NotificationEvent


class Audience(StrEnum):
    """Los destinatarios de un aviso, según su papel en el ticket."""

    SOLICITANTES = "SOLICITANTES"
    TECNICOS = "TECNICOS"
    SUPERVISORES = "SUPERVISORES"


AUDIENCE_LABELS = {
    Audience.SOLICITANTES: "Solicitantes",
    Audience.TECNICOS: "Técnicos asignados",
    Audience.SUPERVISORES: "Supervisores",
}

S, T, V = Audience.SOLICITANTES, Audience.TECNICOS, Audience.SUPERVISORES


@dataclass(frozen=True)
class NotificationRule:
    """Un aviso posible: el evento, sus destinatarios y cuándo ocurre."""

    event: NotificationEvent
    audience: Audience
    description: str
    # Por qué no se puede apagar; `None` si se puede.
    locked: str | None = None

    @property
    def key(self) -> str:
        return f"{self.event.value}:{self.audience.value}"


RULES: tuple[NotificationRule, ...] = (
    NotificationRule(E.TICKET_ASIGNADO, T, "Se le asigna un ticket."),
    NotificationRule(
        E.TICKET_ASIGNADO, S, "Saben quién atiende su ticket (al asignar o reasignar)."
    ),
    NotificationRule(
        E.TICKET_REASIGNADO,
        T,
        "Se le quita un ticket, se escala o se reasignan varios a la vez.",
    ),
    NotificationRule(E.ESTADO_CAMBIADO, S, "Se inicia, reactiva o rechaza una solución."),
    NotificationRule(E.ESTADO_CAMBIADO, T, "Se inicia, reactiva o rechaza una solución."),
    NotificationRule(E.TICKET_EN_ESPERA, S, "El ticket queda en espera."),
    NotificationRule(E.TICKET_EN_ESPERA, T, "El ticket queda en espera."),
    NotificationRule(
        E.VALIDACION_PENDIENTE,
        S,
        "El ticket se resolvió y deben revisar la solución.",
        locked="Deben poder revisar la solución (RN-95).",
    ),
    NotificationRule(E.TICKET_RESUELTO, T, "El ticket se resolvió."),
    NotificationRule(E.TICKET_CERRADO, S, "El ticket se cierra."),
    NotificationRule(E.TICKET_CERRADO, T, "El ticket se cierra."),
    NotificationRule(E.TICKET_REABIERTO, S, "El ticket se reabre."),
    NotificationRule(
        E.TICKET_REABIERTO,
        T,
        "El ticket se reabre y hay que retomarlo.",
        locked="Deben saber que el trabajo se retoma (RN-96).",
    ),
    NotificationRule(E.COMENTARIO_PUBLICO, S, "El equipo responde en su ticket."),
    NotificationRule(E.COMENTARIO_PUBLICO, T, "Un solicitante comenta en su ticket."),
    NotificationRule(E.NOTA_INTERNA, T, "Otra persona escribe una nota interna."),
    NotificationRule(
        E.SLA_PROXIMO_A_VENCER, T, "Un ticket asignado está próximo a vencer su SLA."
    ),
    NotificationRule(
        E.SLA_PROXIMO_A_VENCER,
        V,
        "Un ticket sin técnico está próximo a vencer su SLA.",
    ),
    NotificationRule(E.SLA_VENCIDO, T, "El SLA de un ticket asignado vence."),
    NotificationRule(E.SLA_VENCIDO, V, "El SLA de un ticket de su grupo vence."),
    NotificationRule(
        E.SLA_PRIORIDAD_BAJADA, V, "Se baja la prioridad de un ticket con el SLA en riesgo."
    ),
)

RULES_BY_KEY = {rule.key: rule for rule in RULES}


def disabled_keys() -> frozenset[str]:
    """Las parejas apagadas. Se ignora lo que no esté en el catálogo o no se pueda apagar,
    y un valor corrupto se descarta con un aviso (se envía todo)."""
    raw = stored_text(TABLE_KEY)

    if raw is None:
        return frozenset()

    try:
        stored = json.loads(raw)

        if not isinstance(stored, list) or not all(isinstance(key, str) for key in stored):
            raise ValueError("no es una lista de textos")
    except ValueError as error:
        logger.warning(
            "El valor guardado de «%s» no es válido (%s); se envían todos los avisos.",
            TABLE_KEY,
            error,
        )
        return frozenset()

    return frozenset(
        key for key in stored if key in RULES_BY_KEY and RULES_BY_KEY[key].locked is None
    )


def is_enabled(event: NotificationEvent, audience: Audience) -> bool:
    """Si hay que enviar el aviso de `event` a `audience`.

    Pedir una pareja que no está en el catálogo es un error de programación (un aviso nuevo
    debe declararse aquí para que el Administrador lo vea) y lanza `ValueError`.
    """
    key = f"{NotificationEvent(event).value}:{Audience(audience).value}"

    if key not in RULES_BY_KEY:
        raise ValueError(f"El aviso «{key}» no está en el catálogo de avisos.")

    return key not in disabled_keys()


def preferences_token() -> str:
    """Huella de lo guardado, para detectar que otra persona lo cambió (ver `state_token`)."""
    return document_token(TABLE_KEY)


def save_disabled_keys(
    keys,
    *,
    actor,
    reason: str | None = None,
    base_token: str | None = None,
) -> bool:
    """Guarda las parejas apagadas (las demás se envían). `False` si no cambió nada.

    Ignora lo que no esté en el catálogo y lo que no se puede apagar. Con ninguna apagada
    borra la fila: vuelve a regir el valor inicial. Exige ser Administrador; no hace commit.
    """
    wanted = sorted(
        key for key in set(keys) if key in RULES_BY_KEY and RULES_BY_KEY[key].locked is None
    )

    return save_document(
        TABLE_KEY,
        wanted,
        initial=[],
        current=lambda: sorted(disabled_keys()),
        actor=actor,
        reason=reason,
        base_token=base_token,
    )
