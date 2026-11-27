"""Los gráficos de los reportes, dibujados en el servidor (UI-012; docs/12, fase 8).

Sin librerías de gráficos ni JavaScript: las barras son HTML (cada una con su texto y, si
tiene tickets, un enlace a su listado) y la evolución semanal es un SVG con una tabla
equivalente. Aquí solo se calcula la geometría y los textos; la plantilla los dibuja.
Las barras no comparan personas: solo hay barras de estados, categorías y prioridades.
"""

import math
from dataclasses import dataclass

from ..formatting import format_elapsed
from .queries import Comparison, Count, WeekRow

# El color de cada estado y prioridad, por su código, como en sus insignias (docs/11,
# secciones 27 y 28). Son clases que pintan con tokens `--wd-*`.
STATE_TONES = {
    "NUEVO": "neutral",
    "ASIGNADO": "purple",
    "EN_PROGRESO": "primary",
    "EN_ESPERA": "warning",
    "RESUELTO": "success",
    "CERRADO": "neutral",
}
PRIORITY_TONES = {"BAJA": "neutral", "MEDIA": "primary", "ALTA": "warning", "CRITICA": "danger"}


@dataclass(frozen=True)
class Bar:
    """Una barra: su nombre, su cifra y su largo, relativo a la mayor del gráfico."""

    label: str
    count: Count
    percent: int
    tone: str


def bars(rows, tones: dict[str, str] | None = None) -> list[Bar]:
    """Las barras de un desglose (`BreakdownRow`). La mayor ocupa todo el largo; una con
    tickets nunca queda invisible (al menos un 2 %)."""
    largest = max((row.count.value for row in rows), default=0)

    def percent(value: int) -> int:
        if value == 0:
            return 0

        return max(2, round(value * 100 / largest))

    return [
        Bar(
            row.label,
            row.count,
            percent(row.count.value),
            (tones or {}).get(getattr(row.item, "codigo", None) or "", "primary"),
        )
        for row in rows
    ]


# --- Comparación con el período anterior ----------------------------------------------


def count_change(comparison: Comparison) -> str:
    """«+9 (+8 %) respecto del período anterior», «Igual que el período anterior» o, si
    antes no había nada, «Antes: 0»."""
    change = comparison.change

    if change == 0:
        return "Igual que el período anterior"

    if comparison.change_percent is None:
        return f"Antes: {comparison.previous.value}"

    return f"{change:+d} ({comparison.change_percent:+d} %) respecto del período anterior"


def time_change(current: float | None, previous: float | None) -> str:
    """Cuánto cambió un tiempo respecto del período anterior, en palabras."""
    if current is None or previous is None:
        return "Sin datos del período anterior" if current is not None else ""

    difference = round(current - previous)

    if abs(difference) < 60:
        return "Igual que el período anterior"

    sign = "+" if difference > 0 else "−"

    return f"{sign}{format_elapsed(abs(difference))} respecto del período anterior"


# --- Línea semanal --------------------------------------------------------------------

WIDTH = 640
HEIGHT = 220
LEFT = 64
RIGHT = 16
TOP = 12
BOTTOM = 30
MAX_X_LABELS = 8
MAX_Y_STEPS = 4

# Los escalones posibles del eje vertical, en segundos: de 15 minutos a 4 semanas.
_STEPS = (
    15 * 60,
    30 * 60,
    3600,
    2 * 3600,
    3 * 3600,
    6 * 3600,
    12 * 3600,
    86400,
    2 * 86400,
    7 * 86400,
    14 * 86400,
    28 * 86400,
)


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    label: str


@dataclass(frozen=True)
class Series:
    """Una línea (`name` la nombra en la leyenda); `paths` son sus tramos sin huecos."""

    key: str
    name: str
    paths: list[str]
    points: list[Point]


@dataclass(frozen=True)
class Tick:
    position: float
    label: str


@dataclass(frozen=True)
class LineChart:
    width: int
    height: int
    left: int
    right: int
    top: int
    bottom: int
    series: list[Series]
    y_ticks: list[Tick]
    x_ticks: list[Tick]

    @property
    def empty(self) -> bool:
        return not any(series.points for series in self.series)


def resolution_line(weeks: list[WeekRow]) -> LineChart:
    """La media y la mediana del tiempo de resolución, semana a semana. Una semana sin
    resueltos deja un hueco en la línea: no hay un tiempo que dibujar."""
    values = [
        value
        for week in weeks
        for value in (week.resolution.mean_seconds, week.resolution.median_seconds)
        if value is not None
    ]
    largest = max(values, default=0)
    step = _step(largest)
    top_value = step * max(1, math.ceil(largest / step))
    plot_width = WIDTH - LEFT - RIGHT
    plot_height = HEIGHT - TOP - BOTTOM

    def x_of(index: int) -> float:
        if len(weeks) == 1:
            return LEFT + plot_width / 2

        return round(LEFT + index * plot_width / (len(weeks) - 1), 1)

    def y_of(seconds: float) -> float:
        return round(TOP + plot_height - seconds * plot_height / top_value, 1)

    def series(key: str, name: str, attribute: str) -> Series:
        paths, points, current = [], [], []

        for index, week in enumerate(weeks):
            value = getattr(week.resolution, attribute)

            if value is None:
                if current:
                    paths.append(current)
                current = []
                continue

            point = Point(x_of(index), y_of(value), format_elapsed(value))
            points.append(point)
            current.append(point)

        if current:
            paths.append(current)

        return Series(
            key,
            name,
            [
                "M " + " L ".join(f"{p.x} {p.y}" for p in path)
                for path in paths
                if len(path) > 1
            ],
            points,
        )

    every = max(1, -(-len(weeks) // MAX_X_LABELS))

    return LineChart(
        WIDTH,
        HEIGHT,
        LEFT,
        RIGHT,
        TOP,
        BOTTOM,
        [
            series("mean", "Media", "mean_seconds"),
            series("median", "Mediana", "median_seconds"),
        ],
        [
            Tick(y_of(value), format_elapsed(value) if value else "0")
            for value in range(0, top_value + 1, step)
        ],
        [
            Tick(x_of(index), week.first.strftime("%d-%m"))
            for index, week in enumerate(weeks)
            if index % every == 0
        ],
    )


def _step(largest: float) -> int:
    """El menor escalón con el que el eje llega al valor más alto en pocas marcas."""
    for step in _STEPS:
        if largest <= step * MAX_Y_STEPS:
            return step

    return math.ceil(largest / MAX_Y_STEPS)
