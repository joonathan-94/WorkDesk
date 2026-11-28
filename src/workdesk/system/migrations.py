"""Qué revisión de migraciones espera el código y cuál tiene una base.

Restaurar un respaldo y la pantalla de estado del sistema necesitan comparar las dos: un
volcado solo encaja con el código si su revisión es la última que el código conoce
(`HEAD`) o una anterior, que `db upgrade` pone al día. Una revisión que el código no conoce
viene de una versión más nueva (o de otra aplicación) y no se puede usar.
"""

import functools
from enum import StrEnum
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


class RevisionMatch(StrEnum):
    AL_DIA = "AL_DIA"  # la misma que espera el código
    ANTERIOR = "ANTERIOR"  # una que el código conoce: `db upgrade` la pone al día
    DESCONOCIDA = "DESCONOCIDA"  # el código no la conoce (más nueva o de otra aplicación)
    SIN_REVISION = "SIN_REVISION"  # la base no se creó con las migraciones


REVISION_LABELS = {
    RevisionMatch.AL_DIA: "al día con el código",
    RevisionMatch.ANTERIOR: "anterior al código (se pone al día con db upgrade)",
    RevisionMatch.DESCONOCIDA: "desconocida para este código",
    RevisionMatch.SIN_REVISION: "sin revisión de migraciones",
}


@functools.cache
def _scripts() -> ScriptDirectory:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))

    return ScriptDirectory.from_config(config)


def code_heads() -> frozenset[str]:
    """Las revisiones finales que conoce el código (una, si la historia es lineal)."""
    return frozenset(_scripts().get_heads())


def known_revisions() -> frozenset[str]:
    return frozenset(script.revision for script in _scripts().walk_revisions())


def split_revision(text_value: str | None) -> frozenset[str]:
    """Una revisión como la guarda un respaldo (varias, separadas por comas)."""
    return frozenset(part for part in (text_value or "").split(",") if part)


def compare_revision(revision: str | None) -> RevisionMatch:
    revisions = split_revision(revision)

    if not revisions:
        return RevisionMatch.SIN_REVISION

    if revisions == code_heads():
        return RevisionMatch.AL_DIA

    if revisions <= known_revisions():
        return RevisionMatch.ANTERIOR

    return RevisionMatch.DESCONOCIDA


def database_revision(connection) -> str | None:
    """La revisión de la base (la tabla `alembic_version`), o `None` si no la tiene."""
    if not connection.scalar(text("SELECT to_regclass('alembic_version') IS NOT NULL")):
        return None

    revisions = connection.scalars(text("SELECT version_num FROM alembic_version")).all()

    return ",".join(sorted(revisions)) or None
