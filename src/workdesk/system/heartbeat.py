"""El latido del planificador: cuándo hizo su última pasada (UI-029).

El planificador (`run-scheduler`) es un proceso aparte. Si se detiene, los avisos de SLA y el
cierre automático dejan de ocurrir sin que nada lo diga. Cada pasada deja un archivo pequeño
con su hora y sus fallos (`SCHEDULER_HEARTBEAT_FILE`, por defecto en `instance/`), y la
pantalla de estado del sistema lo lee.

Un archivo y no una fila: no escribe en la base cada minuto, ni deja rastro en las
transacciones, y sirve igual con el planificador en marcha que con `--once` programado. Se
escribe en un temporal y se renombra: quien lo lee nunca ve uno a medias.
"""

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Heartbeat:
    last_pass: datetime
    failures: int


def record_heartbeat(path: Path, *, failures: int, moment: datetime | None = None) -> None:
    moment = (moment or datetime.now(UTC)).astimezone(UTC)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps({"ultima_pasada": moment.isoformat(timespec="seconds"), "fallos": failures}),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_heartbeat(path: Path) -> Heartbeat | None:
    """El último latido, o `None` si no hay o no se entiende."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        moment = datetime.fromisoformat(data["ultima_pasada"])
        failures = int(data["fallos"])
    except (OSError, ValueError, KeyError, TypeError):
        return None

    if moment.tzinfo is None or failures < 0:
        return None

    return Heartbeat(last_pass=moment, failures=failures)
