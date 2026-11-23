"""Constantes y tipos que comparten los módulos del seed de tickets."""

import re
from dataclasses import dataclass
from datetime import timedelta

STAFF_ROLES = ("TECNICO", "SUPERVISOR")
SOLICITANTE = "SOLICITANTE"
SUPERVISOR = "SUPERVISOR"
TECNICO = "TECNICO"

# Marca que el seed deja en `historial_ticket.contexto` de sus eventos.
MARKER_KEY = "demo_clave"
MARKER_STEP = "demo_paso"

MAX_KEY_LENGTH = 60
KEY_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

# Margen para que ningún evento quede en el futuro.
LIMIT_MARGIN = timedelta(minutes=1)


class DemoTicketsError(Exception):
    """Los datos o el estado de la base impiden cargar los tickets demo.

    El mensaje está pensado para mostrarse en la terminal.
    """


@dataclass(frozen=True)
class DemoTicketsResult:
    created: int
    refreshed: int
    warnings: tuple[str, ...] = ()


def is_own(context: dict | None, key: str) -> bool:
    return bool(context) and context.get(MARKER_KEY) == key
