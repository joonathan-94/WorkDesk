"""Coherencia entre el código y lo que dicen los documentos.

Los documentos se desfasan en silencio: se añade una variable de entorno, un comando o
una migración y nadie actualiza el README. Estas comprobaciones fallan en ese momento, con
el nombre de lo que falta, en lugar de descubrirlo meses después.

Solo comprueban lo que se puede verificar sin interpretar prosa:

- cada variable de entorno que lee el código está en `.env.example`, en el README y en
  `PROJECT_CONTEXT.md`;
- cada comando propio (`flask --app src.workdesk <comando>`) tiene un ejemplo ejecutable en
  el README y en `PROJECT_CONTEXT.md`;
- cada migración figura en la lista de `PROJECT_CONTEXT.md`;
- la lista «Rutas actuales» del README y de `PROJECT_CONTEXT.md` es el mapa de rutas real:
  ni falta una ruta, ni sobra una que ya no existe, ni se equivoca de métodos.

Si una falla, no se arregla el test: se actualiza el documento (o, si la variable, el
comando o la ruta de verdad ya no existen, se quita de ellos).
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Variables de entorno que el código lee: `os.getenv("X")`, `get_bool_env("X")`, los parámetros
# de `settings.py` (`IntSetting("X", ...)` y `BoolSetting("X", ...)`, que se leen del
# entorno) y la de la
# contraseña de los usuarios demo (una constante que el comando lee con `os.getenv`).
_ENV_CALL = re.compile(r'(?:getenv|get_bool_env|IntSetting|BoolSetting)\(\s*"([A-Z][A-Z0-9_]*)"')
_ENV_CONSTANT = re.compile(r'[A-Z_]+_ENV = "([A-Z][A-Z0-9_]*)"')

# Una línea de la lista de rutas: `GET       /ruta`, `GET POST  /ruta` (README) o
# `GET, POST  /ruta` (PROJECT_CONTEXT).
_ROUTE_LINE = re.compile(
    r"^\s*((?:GET|POST)(?:[,\s]+(?:GET|POST))*)\s+(/\S*)\s*$", re.MULTILINE
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _environment_variables() -> set[str]:
    found: set[str] = set()

    for path in (ROOT / "src" / "workdesk").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        found |= set(_ENV_CALL.findall(text))
        found |= set(_ENV_CONSTANT.findall(text))

    return found


def _mentions(text: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name)}\b", text) is not None


def _normalized(path: str) -> str:
    """`<int:priority_id>`, `<id>` y `<path:filename>` son lo mismo: un parámetro."""
    return re.sub(r"<[^>]+>", "<x>", path)


def _methods_by_route(pairs) -> dict[str, tuple[str, ...]]:
    """Agrupa los métodos por ruta: una misma URL puede declararse en dos reglas.

    `/static` queda fuera: es el servidor de archivos de Flask, no una ruta de WorkDesk, y
    cada documento es libre de mencionarla o no.
    """
    routes: dict[str, set[str]] = {}

    for path, methods in pairs:
        if not path.startswith("/static"):
            routes.setdefault(_normalized(path), set()).update(methods)

    return {path: tuple(sorted(methods)) for path, methods in routes.items()}


def _registered_routes(app) -> dict[str, tuple[str, ...]]:
    return _methods_by_route(
        (rule.rule, rule.methods - {"HEAD", "OPTIONS"}) for rule in app.url_map.iter_rules()
    )


def _documented_routes(text: str) -> dict[str, tuple[str, ...]]:
    return _methods_by_route(
        (path, re.findall(r"GET|POST", methods)) for methods, path in _ROUTE_LINE.findall(text)
    )


def test_the_code_reads_the_environment_variables_this_test_expects():
    # Si el patrón de búsqueda dejara de encontrar variables, las demás pruebas pasarían en
    # vacío: este mínimo lo impide.
    found = _environment_variables()

    assert {"SECRET_KEY", "DATABASE_URL", "AUTO_CLOSE_HOURS", "SLA_ENABLED"} <= found
    assert len(found) >= 20


@pytest.mark.parametrize("document", [".env.example", "README.md", "PROJECT_CONTEXT.md"])
def test_every_environment_variable_is_documented(document):
    text = _read(document)
    missing = sorted(name for name in _environment_variables() if not _mentions(text, name))

    assert not missing, f"{document} no menciona: {missing}"


@pytest.mark.parametrize("document", ["README.md", "PROJECT_CONTEXT.md"])
def test_every_command_has_an_example_in_the_docs(app, document):
    text = _read(document)
    # `db` es el grupo de Flask-Migrate: tiene su propia sección en los documentos.
    commands = sorted(set(app.cli.commands) - {"db"})

    assert "run-scheduler" in commands, "el recorrido por los comandos no encuentra los propios"

    missing = [name for name in commands if f"--app src.workdesk {name}" not in text]

    assert not missing, f"{document} no tiene un ejemplo ejecutable de: {missing}"


@pytest.mark.parametrize("document", ["README.md", "PROJECT_CONTEXT.md"])
def test_the_route_list_is_the_real_route_map(app, document):
    registered = _registered_routes(app)
    documented = _documented_routes(_read(document))

    # Sin este mínimo, un patrón que dejara de reconocer las líneas haría pasar la prueba
    # en vacío.
    assert len(documented) >= 50, f"no se reconoce la lista de rutas de {document}"

    missing = sorted(set(registered) - set(documented))
    unknown = sorted(set(documented) - set(registered))
    different = sorted(
        path for path in set(registered) & set(documented) if registered[path] != documented[path]
    )

    assert not missing, f"{document} no lista las rutas: {missing}"
    assert not unknown, f"{document} lista rutas que no existen: {unknown}"
    assert not different, f"{document} se equivoca de métodos en: {different}"


def test_every_migration_is_listed_in_the_project_context():
    text = _read("PROJECT_CONTEXT.md")
    slugs = [
        path.stem.split("_", 1)[1]
        for path in sorted((ROOT / "migrations" / "versions").glob("*.py"))
    ]

    assert len(slugs) >= 20

    missing = [slug for slug in slugs if slug not in text]

    assert not missing, f"PROJECT_CONTEXT.md no lista las migraciones: {missing}"
