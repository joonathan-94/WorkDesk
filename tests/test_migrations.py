"""Las migraciones de Alembic (docs/10, «Base de datos»; AGENTS.md, sección 10).

El resto de la suite crea el esquema con `db.create_all()` a partir de los modelos, así que
ninguna otra prueba comprueba que las migraciones den ese mismo esquema. Estas lo hacen con
el procedimiento de siempre (`flask db ...`), en un esquema propio y desechable dentro de
`workdesk_test`:

1. **Las migraciones son coherentes.** Suben todas y hay **una sola cabeza** (dos ramas de
   migraciones que se cruzan son un clásico); `db check` no encuentra diferencias con los
   modelos (una migración olvidada, o escrita a mano con algo distinto de lo que dicen los
   modelos, hace fallar este test); bajan hasta la base y **no queda nada** (todas las
   `downgrade` se ejecutan sin error y dejan la base vacía, también la de la secuencia de los
   tickets; no detecta una `downgrade` que olvide deshacer un detalle que otra migración
   anterior ya borra después); y vuelven a subir y siguen coincidiendo con los modelos.
2. **Una instalación limpia funciona.** `db check` compara tablas, columnas e índices, pero
   no ve las secuencias ni las restricciones `CHECK` ni los valores por defecto del servidor:
   si una migración se olvidara de la secuencia de los tickets, `db check` pasaría y nadie
   podría crear un ticket. Esta prueba sigue el README como lo haría quien clona el
   repositorio (migraciones, datos iniciales, equipo y tickets de demostración, avisos y
   planificador) sobre un esquema creado **solo por las migraciones**, y comprueba lo que
   deja en la base de datos.

Corren en un subproceso porque el `env.py` de Alembic reconfigura el logging de todo el
proceso (`fileConfig`) y eso desactivaría los registros de los demás tests. El subproceso
apunta, con una variable de entorno, al esquema de cada test: nunca a `workdesk_dev`.
"""

import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.workdesk.seeds.demo_tickets_data import DEMO_TICKETS
from tests.database import checked_database_url, worker_schema
from tests.demo_data import DEMO_PASSWORD

ROOT = Path(__file__).resolve().parent.parent

# Tablas y secuencia que tienen que existir al subir (una muestra de cada fase).
EXPECTED_TABLES = {
    "usuarios",
    "auditoria_administrativa",
    "tickets",
    "transiciones_estados",
    "comentarios",
    "archivos",
    "calendarios_laborales",
    "politicas_sla",
    "tickets_sla_periodos",
    "notificaciones",
}

# La salida de `run-scheduler --once`.
SCHEDULER_LINE = re.compile(
    r"SLA próximo a vencer: (?P<warnings>\d+)\. SLA vencido: (?P<breaches>\d+)\. "
    r"Tickets cerrados automáticamente: (?P<closed>\d+)\. Errores: (?P<failures>\d+)\."
)


@contextmanager
def _scratch_schema(suffix, **extra_env):
    """Un esquema vacío y desechable dentro de `workdesk_test`, y el entorno para que un
    subproceso de Flask apunte a él. Se elimina al terminar, pase lo que pase."""
    base_url = checked_database_url()
    schema = f"{worker_schema() or 'wd_test'}_{suffix}"
    engine = create_engine(base_url)
    url = make_url(base_url).update_query_dict({"options": f"-csearch_path={schema}"})
    env = {
        **os.environ,
        "DATABASE_URL": url.render_as_string(hide_password=False),
        "SECRET_KEY": "migrations-test",
        "LOG_LEVEL": "ERROR",
        # Por una tubería, Windows codifica la salida en cp1252: sin esto las tildes de lo
        # que imprimen los comandos no se leerían como UTF-8.
        "PYTHONUTF8": "1",
        **extra_env,
    }

    try:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))

        yield engine, schema, env
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))

        engine.dispose()


def _flask(env, *args):
    return subprocess.run(
        [sys.executable, "-m", "flask", "--app", "src.workdesk", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )


def _ok(result, step):
    """La salida del comando; el test falla con lo que dijo si terminó con error."""
    assert result.returncode == 0, (
        f"{step} falló:\n{result.stdout[-800:]}\n{result.stderr[-1500:]}"
    )

    return result.stdout


def _scalar(engine, schema, sql):
    """Una consulta sobre el esquema desechable."""
    with engine.connect() as connection:
        connection.execute(text(f'SET search_path TO "{schema}"'))

        return connection.scalar(text(sql))


def _scheduler_counts(output):
    """Lo que informó `run-scheduler --once`, como números."""
    found = SCHEDULER_LINE.search(output)

    assert found is not None, f"no se reconoce la salida del planificador:\n{output}"

    return {name: int(value) for name, value in found.groupdict().items()}


def test_the_migrations_apply_match_the_models_and_revert():
    with _scratch_schema("migrations") as (engine, schema, env):

        def objects():
            with engine.connect() as connection:
                tables = set(
                    connection.scalars(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema = :schema"
                        ),
                        {"schema": schema},
                    )
                )
                sequences = set(
                    connection.scalars(
                        text(
                            "SELECT sequence_name FROM information_schema.sequences "
                            "WHERE sequence_schema = :schema"
                        ),
                        {"schema": schema},
                    )
                )

            return tables, sequences

        # 1. Sube y hay una sola cabeza.
        _ok(_flask(env, "db", "upgrade"), "db upgrade")
        heads = _ok(_flask(env, "db", "heads"), "db heads").strip().splitlines()

        assert len(heads) == 1, f"hay más de una cabeza de migraciones: {heads}"

        current = _ok(_flask(env, "db", "current"), "db current")

        assert heads[0].split()[0] in current
        assert "(head)" in current

        tables, sequences = objects()

        assert EXPECTED_TABLES <= tables
        assert "tickets_public_id_seq" in sequences

        # 2. Las migraciones dan lo mismo que los modelos.
        _ok(_flask(env, "db", "check"), "db check (tras subir)")

        # 3. Bajan hasta la base sin dejar nada.
        _ok(_flask(env, "db", "downgrade", "base"), "db downgrade base")
        tables, sequences = objects()

        assert tables == {"alembic_version"}, f"quedaron tablas: {tables}"
        assert not sequences, f"quedaron secuencias: {sequences}"

        # 4. Vuelven a subir.
        _ok(_flask(env, "db", "upgrade"), "db upgrade (segunda vez)")
        _ok(_flask(env, "db", "check"), "db check (tras volver a subir)")


def test_a_fresh_install_built_only_from_the_migrations_works(tmp_path):
    """Los pasos del README, sobre un esquema que solo conoce las migraciones.

    `create-admin` queda fuera: pide la contraseña con `getpass`, que en Windows lee la
    consola y no una tubería (lo cubre `test_cli.py`). El equipo de `seed-demo` ya inserta
    usuarios sobre este mismo esquema.
    """
    uploads = tmp_path / "uploads"

    with _scratch_schema(
        "install", UPLOADS_DIR=str(uploads), WORKDESK_DEMO_PASSWORD=DEMO_PASSWORD
    ) as (engine, schema, env):

        def run(step, *args):
            return _ok(_flask(env, *args), step)

        def scalar(sql):
            return _scalar(engine, schema, sql)

        run("db upgrade", "db", "upgrade")

        assert "Roles creados: 4" in run("seed-roles", "seed-roles")

        catalogs = run("seed-catalogs", "seed-catalogs")

        assert "Estados: 6" in catalogs
        assert "prioridades: 4" in catalogs
        assert "políticas de SLA: 4" in catalogs
        assert "tipos de relación: 2" in catalogs

        demo = run("seed-demo", "seed-demo")

        assert "Usuarios demo creados: 12" in demo
        assert "Grupos demo creados: 3" in demo

        # Sin categorías ni ubicaciones hechas a mano (como recién instalado) los tickets
        # usan «Sin clasificar»: el comando avisa y sigue.
        tickets = run("seed-demo-tickets", "seed-demo-tickets")

        assert f"Tickets demo creados: {len(DEMO_TICKETS)}" in tickets

        notifications = run("seed-demo-notifications", "seed-demo-notifications")

        assert re.search(r"Notificaciones demo creadas: [1-9]\d*\.", notifications)

        # Lo que quedó en la base de datos: la secuencia de los tickets, los períodos de
        # SLA y las restricciones de las migraciones aguantaron la carga completa.
        assert scalar("SELECT count(*) FROM tickets") == len(DEMO_TICKETS)
        assert scalar(
            "SELECT count(*) FROM tickets t WHERE NOT EXISTS "
            "(SELECT 1 FROM tickets_sla_periodos p WHERE p.ticket_id = t.id)"
        ) == 0, "hay tickets sin ningún período de SLA"

        status = run("sla-status 1", "sla-status", "1")

        assert "Ticket #1" in status
        assert "SLA:" in status

        # Primera pasada del planificador sobre la base recién cargada: los períodos no
        # tienen marcas, así que avisa de lo vencido y no falla en nada.
        first = _scheduler_counts(run("run-scheduler --once", "run-scheduler", "--once"))

        assert first["failures"] == 0
        assert first["breaches"] > 0, (
            "la demostración tiene tickets vencidos y el planificador no avisó de ninguno"
        )

        # RN-91: cada vencimiento avisado quedó registrado en el historial, una sola vez,
        # y avisó a alguien.
        assert scalar(
            "SELECT count(*) FROM historial_ticket WHERE tipo_evento = 'SLA_VENCIDO'"
        ) == first["breaches"]
        assert scalar(
            "SELECT count(*) FROM notificaciones WHERE tipo_evento = 'SLA_VENCIDO'"
        ) >= first["breaches"]

        # Repetirlo no falla ni duplica nada: ningún período tiene dos registros de
        # vencimiento.
        second = _scheduler_counts(run("run-scheduler --once (2)", "run-scheduler", "--once"))

        assert second["failures"] == 0
        assert scalar(
            "SELECT count(*) FROM (SELECT contexto->>'periodo_id' FROM historial_ticket "
            "WHERE tipo_evento = 'SLA_VENCIDO' GROUP BY 1 HAVING count(*) > 1) repetidos"
        ) == 0
