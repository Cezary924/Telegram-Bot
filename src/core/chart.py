import io
from collections.abc import Callable, Sequence
from datetime import date, datetime
from typing import Literal

from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter, DateFormatter, date2num, num2date
from matplotlib.figure import Figure

palette = {'surface': "#fcfcfb", 'ink': "#0b0b0b", 'muted': "#898781", 'grid': "#e1e0d9", 'axis': "#c3c2b7",
           'blue': "#2a78d6", 'green': "#0ca30c", 'yellow': "#fab219", 'red': "#d03b3b", 'orange': "#eb6834"}
tick_count = 8
Run = tuple[list[float], list[float], str]


def canvas(title: str, unit: str = "", grid: Literal["both", "x", "y"] = "both") -> tuple[Figure, Axes]:
    figure = Figure(figsize=(8, 4.5), dpi=120, facecolor=palette['surface'])
    axes = figure.subplots()
    axes.set_facecolor(palette['surface'])
    axes.set_title(title, color=palette['ink'], loc="left", parse_math=False)
    if unit:
        axes.set_ylabel(unit, color=palette['muted'])
    axes.grid(axis=grid, color=palette['grid'], linewidth=0.8)
    axes.set_axisbelow(True)
    axes.tick_params(colors=palette['muted'])
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(palette['axis'])
    return figure, axes


def picture(figure: Figure) -> bytes:
    figure.tight_layout()
    found = io.BytesIO()
    figure.savefig(found, format="png", facecolor=palette['surface'])
    return found.getvalue()


def date_ticks(axes: Axes, days: Sequence[date], pattern: str, places: Sequence | None = None) -> None:
    picked = range(0, len(days), max(1, -(-len(days) // tick_count)))
    axes.set_xticks([(days if places is None else places)[index] for index in picked],
                    labels=[days[index].strftime(pattern) for index in picked])


def date_axis(axes: Axes, pattern: str | None = None) -> None:
    if pattern is not None:
        axes.xaxis.set_major_formatter(DateFormatter(pattern))
        return
    locator = AutoDateLocator()
    axes.xaxis.set_major_locator(locator)
    axes.xaxis.set_major_formatter(ConciseDateFormatter(locator))


def bar_values(axes: Axes, bars: BarContainer, labels: list[str]) -> None:
    axes.bar_label(bars, labels=labels, padding=2, color=palette['ink'], fontsize=8)
    axes.margins(y=0.12)


def goal_line(axes: Axes, value: float, text: str) -> None:
    axes.axhline(value, color=palette['ink'], linewidth=1.5, linestyle="--")
    axes.annotate(text, (1, value), xycoords=("axes fraction", "data"), xytext=(0, 4), textcoords="offset points",
                  ha="right", color=palette['ink'], fontsize=8)


def moment_line(axes: Axes, moment: datetime, text: str) -> None:
    axes.axvline(date2num(moment), color=palette['muted'], linewidth=1, linestyle="--")
    axes.annotate(text, (moment, 1), xycoords=("data", "axes fraction"), xytext=(3, -12), textcoords="offset points",
                  color=palette['muted'], fontsize=8)


def colored_runs(points: list[tuple[float, float]], edges: list[float], coloring: Callable[[float], str]) -> list[Run]:
    found: list[Run] = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        cuts = sorted(cut for cut in ((limit - y0) / (y1 - y0) for limit in edges if y0 != y1) if 0 < cut < 1)
        for start, end in zip([0.0] + cuts, cuts + [1.0]):
            color = coloring(y0 + (y1 - y0) * (start + end) / 2)
            if not found or found[-1][2] != color:
                found.append(([x0 + (x1 - x0) * start], [y0 + (y1 - y0) * start], color))
            found[-1][0].append(x0 + (x1 - x0) * end)
            found[-1][1].append(y0 + (y1 - y0) * end)
    return found


def colored_line(axes: Axes, points: list[tuple[datetime, float]], edges: list[float],
                 coloring: Callable[[float], str]) -> None:
    for xs, ys, color in colored_runs([(date2num(moment), value) for moment, value in points], edges, coloring):
        axes.plot([num2date(x).replace(tzinfo=None) for x in xs], ys, color=color, linewidth=2)
