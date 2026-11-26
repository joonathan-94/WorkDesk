"""Invariantes del esquema que protegen la trazabilidad (RN-02, RN-03, RN-110 y RF-112).

Se comprueban sobre los modelos, así que una tabla o una clave nueva queda cubierta sin
tocar este archivo:

- **Ninguna clave foránea borra en cascada.** Un `ON DELETE CASCADE` haría que eliminar un
  ticket o un usuario se llevara por delante su historial o su auditoría sin que nadie lo
  pidiera. Con `RESTRICT`, la base se niega, y la futura retención tendrá que borrar en
  orden y a propósito. La comparación de migraciones y modelos no lo vería: si se cambian
  los dos a la vez, coinciden.
- **Toda tabla de eventos es de solo añadir.** Una tabla con `fecha_hora` es un registro de
  lo que pasó (auditoría, historial y los que vengan): el ORM debe rechazar modificar o
  borrar sus filas. Una tabla nueva de este tipo hace fallar la prueba hasta que se proteja.
"""

import pytest
from sqlalchemy import inspect as sa_inspect

from src.workdesk import models
from src.workdesk.extensions import db

EVENT_TIMESTAMP_COLUMN = "fecha_hora"


def _models_by_table():
    return {mapper.local_table.name: mapper.class_ for mapper in db.Model.registry.mappers}


def _event_log_models():
    return sorted(
        (
            model
            for table, model in _models_by_table().items()
            if EVENT_TIMESTAMP_COLUMN in db.metadata.tables[table].c
        ),
        key=lambda model: model.__tablename__,
    )


def test_there_are_foreign_keys_and_event_logs_to_check():
    assert models  # los modelos están importados y registrados
    assert len([fk for t in db.metadata.sorted_tables for fk in t.foreign_keys]) > 50
    assert {m.__tablename__ for m in _event_log_models()} >= {
        "auditoria_administrativa",
        "historial_ticket",
    }


def test_no_foreign_key_deletes_in_cascade():
    loose = [
        f"{table.name}.{fk.parent.name} → {fk.column.table.name} ({fk.ondelete})"
        for table in db.metadata.sorted_tables
        for fk in table.foreign_keys
        if (fk.ondelete or "").upper() != "RESTRICT"
    ]

    assert loose == [], "toda clave foránea debe ser ON DELETE RESTRICT"


@pytest.mark.parametrize("model", _event_log_models(), ids=lambda m: m.__tablename__)
@pytest.mark.parametrize("operation", ["before_update", "before_delete"])
def test_every_event_log_rejects_changes_through_the_orm(model, operation):
    listeners = list(getattr(sa_inspect(model).dispatch, operation))

    assert listeners, f"{model.__tablename__} no rechaza {operation}"

    # Se llama a cada escucha como lo hace SQLAlchemy al confirmar: con el mapper y el
    # estado de una fila (aquí, una sin guardar; ninguno debe llegar a mirarla).
    mapper = sa_inspect(model)

    for listener in listeners:
        with pytest.raises(Exception, match="no pueden"):
            listener(mapper, None, sa_inspect(model()))
