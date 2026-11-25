"""Reglas del frontend que ninguna otra prueba vigila (AGENTS.md, sección 11; docs/11, 41.1).

- **Colores solo con tokens `--wd-*`.** Se definen en `app.css`; ninguna otra hoja,
  plantilla ni script escribe un color a mano. Cuatro hojas anteriores a esa regla aún
  tienen colores escritos (pasan a tokens en `v0.9.0`, antes del tema oscuro): su número
  **solo puede bajar**.
- **Nada de JavaScript en línea** (la política de contenido de `security/headers.py` lo
  bloquearía en el navegador, no en los tests).
- **Nada de Internet:** WorkDesk funciona sin conexión, así que no hay recursos externos.
- **Todo parcial incluido existe.**
"""

import re
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "workdesk"
TEMPLATES = PACKAGE / "templates"
STATIC = PACKAGE / "static"
TOKENS_FILE = "app.css"

# Colores escritos a mano que quedan en hojas anteriores a los tokens. Al pasarlos a
# tokens hay que bajar la cifra; nunca subirla.
PENDING_COLORS = {"auth.css": 17, "errors.css": 2, "layout.css": 21, "theme.css": 56}

_COLOR = re.compile(
    r"(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b"
    r"|\b(?:rgba?|hsla?)\(\s*\d"
)
_INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>")
_EVENT_HANDLER = re.compile(r"<[^<>{}]*\son[a-z]+\s*=")
_EXTERNAL = re.compile(r"(?:src|href|action)=[\"']https?://|url\([\"']?https?://|@import")
_INCLUDE = re.compile(r"\{%-?\s*(?:include|extends|from|import)\s+[\"']([^\"']+)[\"']")


def _templates() -> list[Path]:
    return sorted(TEMPLATES.rglob("*.html"))


def _own(pattern: str) -> list[Path]:
    """Los archivos estáticos propios (los de `vendor` son de terceros y no se tocan)."""
    return sorted(p for p in STATIC.rglob(pattern) if "vendor" not in p.parts)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _matching(paths, pattern) -> list[str]:
    return [p.relative_to(PACKAGE).as_posix() for p in paths if pattern.search(_read(p))]


def test_there_are_files_to_check():
    assert len(_templates()) > 50
    assert len(_own("*.css")) >= 8
    assert len(_own("*.js")) >= 8


def test_templates_and_scripts_write_no_colors():
    assert _matching(_templates() + _own("*.js"), _COLOR) == []


@pytest.mark.parametrize(
    "sheet", [p for p in _own("*.css") if p.name != TOKENS_FILE], ids=lambda p: p.name
)
def test_style_sheets_use_tokens(sheet):
    found = len(_COLOR.findall(_read(sheet)))
    allowed = PENDING_COLORS.get(sheet.name, 0)

    assert found <= allowed, (
        f"{sheet.name} tiene {found} colores escritos a mano (máximo {allowed}): usa un "
        "token --wd-* y, si falta, defínelo en app.css."
    )
    assert found == allowed, (
        f"{sheet.name} ya solo tiene {found}: baja su cifra en PENDING_COLORS."
    )


def test_the_tokens_file_only_writes_colors_in_tokens():
    sheet = next(p for p in _own("*.css") if p.name == TOKENS_FILE)
    content = re.sub(r"/\*.*?\*/", "", _read(sheet), flags=re.DOTALL)
    # Cada declaración (puede ocupar varias líneas, como una sombra).
    stray = [
        declaration.strip()
        for declaration in re.split(r"[;{}]", content)
        if _COLOR.search(declaration) and not declaration.strip().startswith("--wd-")
    ]

    assert stray == []


def test_templates_have_no_inline_javascript():
    assert _matching(_templates(), _INLINE_SCRIPT) == []
    assert _matching(_templates(), _EVENT_HANDLER) == []


def test_nothing_is_loaded_from_the_internet():
    assert _matching(_templates() + _own("*.css") + _own("*.js"), _EXTERNAL) == []


def test_every_referenced_template_exists():
    missing = sorted(
        f"{path.relative_to(TEMPLATES).as_posix()} → {name}"
        for path in _templates()
        for name in _INCLUDE.findall(_read(path))
        if not (TEMPLATES / name).is_file()
    )

    assert missing == []
