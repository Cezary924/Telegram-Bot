from datetime import datetime

from core.api import Answers, Button, Ctx, Module, Outcome, Question, View, bold, escape, italic, labelled, plain
from core.chart import canvas, colored_line, date_axis, palette, picture

module = Module(name="bmi", place=50, is_guarded=True, uses=["bodytracker"],
                icons={'name': "🩺", 'count': "🧮", 'history': "📜", 'chart': "📈", 'save_new': "💾"},
                endings={'how': "😊", 'empty': "🤷", 'saved': "✅"})

categories = [(16.0, "severe_thinness"), (18.5, "underweight"), (25.0, "normal"), (30.0, "overweight"),
              (35.0, "obesity_1"), (40.0, "obesity_2"), (float("inf"), "obesity_3")]
saved_keys = ("height", "weight")
height_limits = (50, 250)
weight_limits = (20, 400)
history_size = 10
colors = {'normal': palette['green'], 'over': palette['yellow'], 'obese': palette['red']}
category_colors = {'severe_thinness': "obese", 'underweight': "over", 'normal': "normal", 'overweight': "over",
                   'obesity_1': "obese", 'obesity_2': "obese", 'obesity_3': "obese"}


def bmi(weight: float, height: float) -> float:
    return weight / (height / 100) ** 2


def category(value: float) -> str:
    return next(name for limit, name in categories if value < limit)


def height_on(heights: list[tuple[str, float]], moment: str) -> float:
    return next((height for measured, height in reversed(heights) if measured <= moment), heights[0][1])


def tracked_points(ctx: Ctx) -> list[tuple[datetime, float]]:
    heights = ctx.ask("bodytracker", "heights")
    if not heights:
        return []
    return [(datetime.fromisoformat(moment), bmi(weight, height_on(heights, moment)))
            for moment, weight in ctx.ask("bodytracker", "weights") or []]


def source(ctx: Ctx, answers: Answers, key: str) -> str:
    return "" if key in answers.typed else " (" + ctx.t("from_tracker") + ")"


def save_buttons(ctx: Ctx, answers: Answers) -> list[Button]:
    new = answers.new(saved_keys)
    if not new or not ctx.has_module("bodytracker"):
        return []
    return [Button(ctx.t("save_new"), "save", *["{:g}".format(new[key]) if key in new else "" for key in saved_keys])]


@module.command("bmi")
def command_bmi(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    buttons = [Button(ctx.t("count"), "count")]
    if tracked_points(ctx):
        buttons += [Button(ctx.t("history"), "history"), Button(ctx.t("chart"), "chart")]
    return View(text=ctx.t("how"), buttons=buttons)


@module.callback("count")
def count(ctx: Ctx) -> View:
    return ctx.form("body", offered=ctx.ask("bodytracker", "latest"))


@module.form("body", [Question("height", "height", low=height_limits[0], high=height_limits[1]),
                      Question("weight", "weight", low=weight_limits[0], high=weight_limits[1])],
             parent="menu", title="count")
def counted(ctx: Ctx, answers: Answers) -> View:
    value = bmi(answers['weight'], answers['height'])
    ctx.close_screen()
    ctx.log("BMI counted")
    return View(text="\n".join([
        labelled(ctx.t("labels.bmi"), "{:.1f}".format(value)),
        labelled(ctx.t("labels.category"), ctx.t("category." + category(value))),
        labelled(ctx.t("labels.weight"), ctx.profile.weight(answers['weight'])) + source(ctx, answers, "weight"),
        labelled(ctx.t("labels.height"), ctx.profile.height(answers['height'])) + source(ctx, answers, "height"),
        "", ctx.t("note")]), buttons=save_buttons(ctx, answers))


def saved_values(arguments: tuple[str, ...]) -> dict:
    try:
        return {key: float(value)
                for key, value in zip(saved_keys, arguments) if value}
    except ValueError:
        return {}


@module.callback("save")
def save(ctx: Ctx) -> View:
    values = saved_values(ctx.arguments)
    if not values or not ctx.ask("bodytracker", "save", values):
        return View(ctx.t("core:not_working_buttons"), heading=None)
    if ctx.message is not None:
        ctx.remove_buttons(ctx.message.message_id)
    return View(text=ctx.t("saved"))


# ----- the assistant -----

@module.context()
def summary(ctx: Ctx) -> str:
    found = tracked_points(ctx)
    if not found:
        return ""
    moment, value = found[-1]
    return labelled(ctx.t("labels.bmi"), "{:.1f}, ".format(value) + ctx.t("category." + category(value))
                    + " (" + moment.strftime("%Y-%m-%d") + ")")


@module.action("count", parameters={'weight': float, 'height': float}, optional=["weight", "height"])
def act_count(ctx: Ctx, weight: float | None, height: float | None) -> Outcome:
    found = ctx.ask("bodytracker", "latest") or {}
    weight = found.get('weight') if weight is None else weight
    height = found.get('height') if height is None else height
    if weight is None or height is None:
        return Outcome.refused(ctx.t("missing"))
    if not weight_limits[0] <= weight <= weight_limits[1] or not height_limits[0] <= height <= height_limits[1]:
        return Outcome.refused(ctx.t("wrong", weight_low=weight_limits[0], weight_high=weight_limits[1],
                                     height_low=height_limits[0], height_high=height_limits[1]))
    value = bmi(weight, height)
    return Outcome.done({'bmi': round(value, 1), 'category': plain(ctx.t("category." + category(value))),
                         'weight_kg': weight, 'height_cm': height})


# ----- history -----

@module.callback("history")
def open_history(ctx: Ctx) -> View:
    return history(ctx)


@module.view("history", parent="menu", title="history")
def history(ctx: Ctx) -> View:
    found = tracked_points(ctx)
    if not found:
        return View(text=ctx.t("empty"))
    lines = [italic(moment.strftime("%Y-%m-%d")) + " - " + bold("{:.1f}".format(value)) + " "
             + ctx.t("category." + category(value)) for moment, value in reversed(found[-history_size:])]
    return View(text=labelled(ctx.t("history_text"), len(found)) + "\n\n" + "\n".join(lines))


def color_of(value: float) -> str:
    return colors[category_colors[category(value)]]


def draw(found: list[tuple[datetime, float]], title: str) -> bytes:
    figure, axes = canvas(title, "BMI", grid="x")
    values = [value for _, value in found]
    bottom, top = min(values + [17.0]) - 1, max(values + [31.0]) + 1
    axes.axhspan(bottom, 16, color=colors['obese'], alpha=0.10, linewidth=0)
    axes.axhspan(16, 18.5, color=colors['over'], alpha=0.14, linewidth=0)
    axes.axhspan(18.5, 25, color=colors['normal'], alpha=0.10, linewidth=0)
    axes.axhspan(25, 30, color=colors['over'], alpha=0.14, linewidth=0)
    axes.axhspan(30, top, color=colors['obese'], alpha=0.10, linewidth=0)
    for limit in (16, 18.5, 25, 30):
        axes.axhline(limit, color=palette['axis'], linewidth=0.8)
        axes.annotate("{:g}".format(limit), (1, limit), xycoords=("axes fraction", "data"), xytext=(4, 0),
                      textcoords="offset points", va="center", color=palette['muted'], fontsize=8)
    colored_line(axes, found, [limit for limit, _ in categories], color_of)
    axes.scatter([moment for moment, _ in found], values, c=[color_of(value) for value in values], s=30, zorder=3)
    axes.set_ylim(bottom, top)
    date_axis(axes)
    return picture(figure)


@module.callback("chart", is_background=True)
def open_chart(ctx: Ctx) -> View:
    return chart(ctx)


@module.view("chart", parent="menu", title="chart")
def chart(ctx: Ctx) -> View:
    found = tracked_points(ctx)
    if not found:
        return View(text=ctx.t("empty"))
    photo = draw(found, ctx.t("chart_title"))
    ctx.log("BMI chart shown")
    lines = [escape(moment.strftime("%Y-%m-%d") + " - {:.1f}".format(value)) for moment, value in found]
    return View(text="\n".join(lines), photo=photo)
