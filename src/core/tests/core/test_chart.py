from datetime import date, datetime, timedelta

from core.chart import (bar_values, canvas, colored_line, colored_runs, date_axis, date_ticks, goal_line, moment_line,
                        palette, picture)


def colour(value: float) -> str:
    return palette['green'] if value < 1 else palette['red']


def test_a_picture_is_a_png():
    figure, axes = canvas("Title", "kg")
    axes.plot([0, 1], [2, 3])
    assert picture(figure)[:8] == b"\x89PNG\r\n\x1a\n"


def test_the_canvas_carries_the_title_and_the_unit():
    _, axes = canvas("Coffee $1", "kcal")
    assert axes.get_title(loc="left") == "Coffee $1" and axes.get_ylabel() == "kcal"


def test_at_most_eight_days_are_labelled_from_the_first():
    days = [date(2026, 11, 1) + timedelta(days=index) for index in range(20)]
    _, axes = canvas("Title")
    date_ticks(axes, days, "%d.%m")
    assert [label.get_text() for label in axes.get_xticklabels()] == ["01.11", "04.11", "07.11", "10.11", "13.11",
                                                                      "16.11", "19.11"]


def test_ticks_may_sit_elsewhere_than_the_days_they_name():
    days = [datetime(2026, 11, 2), datetime(2026, 11, 9)]
    _, axes = canvas("Title")
    axes.bar([day + timedelta(days=3.5) for day in days], [1, 2])
    date_ticks(axes, days, "%d.%m", [day + timedelta(days=3.5) for day in days])
    assert [label.get_text() for label in axes.get_xticklabels()] == ["02.11", "09.11"]


def test_one_day_gets_one_tick():
    _, axes = canvas("Title")
    date_ticks(axes, [date(2026, 11, 1)], "%d.%m")
    assert [label.get_text() for label in axes.get_xticklabels()] == ["01.11"]


def test_a_line_is_cut_where_it_crosses_a_limit():
    assert colored_runs([(0, 0.5), (2, 1.5)], [1.0], colour) == [([0, 1.0], [0.5, 1.0], palette['green']),
                                                                 ([1.0, 2], [1.0, 1.5], palette['red'])]


def test_a_line_within_one_range_stays_whole():
    found = colored_runs([(0, 0.1), (1, 0.2), (2, 0.3)], [1.0], colour)
    assert found == [([0, 1, 2], [0.1, 0.2, 0.3], palette['green'])]


def test_a_colored_line_keeps_the_dates_on_the_axis():
    figure, axes = canvas("Title")
    start = datetime(2026, 11, 1, 20, 0)
    colored_line(axes, [(start, 0.5), (start + timedelta(hours=2), 1.5)], [1.0], colour)
    moment_line(axes, start + timedelta(hours=1), "Now")
    date_axis(axes, "%H:%M")
    assert [line.get_color() for line in axes.get_lines()] == [palette['green'], palette['red'], palette['muted']]
    assert picture(figure)[:8] == b"\x89PNG\r\n\x1a\n"
    assert "21:00" in [label.get_text() for label in axes.get_xticklabels()]


def test_bars_and_the_goal_are_labelled():
    figure, axes = canvas("Title", grid="y")
    bars = axes.bar([0, 1], [3, 0])
    bar_values(axes, bars, ["3", ""])
    goal_line(axes, 2, "Goal 2")
    assert [text.get_text() for text in axes.texts] == ["3", "", "Goal 2"]
    assert picture(figure)[:8] == b"\x89PNG\r\n\x1a\n"
