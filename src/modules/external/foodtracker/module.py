import io
from dataclasses import replace
from datetime import date, datetime, timedelta
from functools import partial

from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure

from core.api import (Answers, Button, Ctx, Html, Module, Outcome, Question, View, escape, italic, labelled,
                      past_moment, plain)

module = Module(name="foodtracker", place=70, is_guarded=True, uses=["bodytracker", "calories", "drinktracker"],
                icons={'name': "🍽️", 'add': "➕", 'today': "📅", 'history': "📜", 'chart': "📈",
                       'settings_button': "⚙️", 'set_goal': "🎯", 'auto_goal': "🔄", 'edit_kcal': "✏️",
                       'edit_when': "🕒", 'remove': "🗑️", 'previous': "⬅️", 'next': "➡️"},
                endings={'how': "😊", 'saved': "✅", 'changed': "✅", 'deleted': "✅", 'empty': "🤷", 'no_meals': "🤷",
                         'gone': "💔"})

activities = ("sedentary", "light", "moderate", "active", "very_active")
told_days = 14
kcal_limits = (1, 5000)
chart_days = 30
page_size = 8
moment_format = "%Y-%m-%d %H:%M"
goal_key = "goal"
activity_key = "activity"
colors = {'surface': "#fcfcfb", 'ink': "#0b0b0b", 'muted': "#898781", 'grid': "#e1e0d9", 'axis': "#c3c2b7",
          'food': "#2a78d6", 'alcohol': "#eb6834", 'goal': "#0b0b0b"}


def table(ctx: Ctx) -> str:
    return ctx.db.table("meals")


def kcal_text(value: float) -> str:
    return "{:.0f} kcal".format(value)


def daily(ctx: Ctx, since: date) -> dict[str, float]:
    return {row['day']: row['kcal'] for row in ctx.db.query_all(
        "SELECT substr(eaten_at, 1, 10) AS day, SUM(kcal) AS kcal FROM " + table(ctx) +
        " WHERE user_id = ? AND eaten_at >= ? GROUP BY day;", (ctx.user.id, since.isoformat()))}


def alcohol(ctx: Ctx, since: date) -> dict[str, float]:
    return ctx.ask("drinktracker", "kcal", since.isoformat()) or {}


def auto_goal(ctx: Ctx, activity: str) -> float | None:
    found, profile = ctx.ask("bodytracker", "latest") or {}, ctx.profile
    if found.get('weight') is None or found.get('height') is None or profile.age is None \
            or not ctx.has_module("calories"):
        return None
    return ctx.ask("calories", "need", profile.sex or "undisclosed", profile.age, found['height'], found['weight'],
                   activity)


def goal(ctx: Ctx) -> float | None:
    activity = ctx.state.get(activity_key)
    if activity:
        return auto_goal(ctx, activity)
    stored = ctx.state.get(goal_key)
    return float(stored) if stored else None


def goal_name(ctx: Ctx) -> Html:
    wanted = goal(ctx)
    activity = ctx.state.get(activity_key)
    if activity:
        shown = kcal_text(wanted) if wanted is not None else ctx.t("goal.missing")
        return Html(escape(shown) + " (" + ctx.t("goal.auto", activity=ctx.t("activity." + activity)) + ")")
    return Html(escape(kcal_text(wanted))) if wanted is not None else ctx.t("goal.none")


# ----- menu -----

@module.command("foodtracker")
def command_foodtracker(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(text=ctx.t("how"), buttons=[Button(ctx.t("add"), "add"),
                                            Button(ctx.t("today"), "today"),
                                            Button(ctx.t("history"), "history"),
                                            Button(ctx.t("chart"), "chart"),
                                            Button.settings(ctx.t("settings_button"), module.name)])


# ----- eating -----

kcal_question = Question("kcal", low=kcal_limits[0], high=kcal_limits[1])
when_question = Question("when", "moment", back=None)


@module.callback("add")
def open_add(ctx: Ctx) -> View:
    return ctx.form("meal")


@module.form("meal", [kcal_question, when_question], parent="menu", title="add")
def meal_given(ctx: Ctx, answers: Answers) -> View:
    insert(ctx, answers['kcal'], answers['when'])
    ctx.close_screen()
    ctx.log("Meal logged")
    return View(text=ctx.t("saved") + "\n" + meal_lines(ctx, answers['kcal'], answers['when'], True))


def insert(ctx: Ctx, value: float, when: str) -> None:
    ctx.db.execute("INSERT INTO " + table(ctx) + " (user_id, kcal, eaten_at) VALUES (?, ?, ?);",
                   (ctx.user.id, value, when))


def meal_lines(ctx: Ctx, value: float, when: str, is_saved: bool) -> str:
    day = datetime.fromisoformat(when).date()
    lines = [labelled(ctx.t("labels.meal"), kcal_text(value)),
             labelled(ctx.t("labels.when"), datetime.fromisoformat(when).strftime(moment_format))]
    if is_saved:
        lines.append(labelled(ctx.t("labels.day_total", day=day.isoformat()),
                              kcal_text(daily(ctx, day).get(day.isoformat(), 0.0))))
    return "\n".join(lines)


@module.callback("today")
def open_today(ctx: Ctx) -> View:
    return today(ctx)


@module.view("today", parent="menu", title="today")
def today(ctx: Ctx) -> View:
    day = date.today()
    food = daily(ctx, day).get(day.isoformat(), 0.0)
    drunk = alcohol(ctx, day).get(day.isoformat(), 0.0)
    lines = [labelled(ctx.t("labels.food"), kcal_text(food))]
    if ctx.has_module("drinktracker"):
        lines.append(labelled(ctx.t("labels.alcohol"), kcal_text(drunk)))
    lines.append(labelled(ctx.t("labels.total"), kcal_text(food + drunk)))
    wanted = goal(ctx)
    if wanted is None:
        lines += ["", ctx.t("no_goal")]
    else:
        rest = ctx.t("labels.left") if food + drunk <= wanted else ctx.t("labels.over")
        lines += [labelled(ctx.t("labels.goal"), goal_name(ctx)), labelled(rest, kcal_text(abs(wanted - food - drunk)))]
    return View(text="\n".join(lines))


# ----- meals -----

def wanted_number(ctx: Ctx) -> int:
    return int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0


def meal_of(ctx: Ctx, meal: int):
    return ctx.db.query_one("SELECT id, kcal, eaten_at FROM " + table(ctx) + " WHERE id = ? AND user_id = ?;",
                            (meal, ctx.user.id))


@module.callback("history")
def open_history(ctx: Ctx) -> View:
    return history(ctx)


@module.view("history", parent="menu", title="history")
def history(ctx: Ctx) -> View:
    return meals_page(ctx, wanted_number(ctx))


def meals_page(ctx: Ctx, wanted: int) -> View:
    rows = ctx.db.query_all("SELECT id, kcal, eaten_at FROM " + table(ctx) + " WHERE user_id = ? "
                            "ORDER BY eaten_at DESC, id DESC;", (ctx.user.id,))
    if not rows:
        return View(text=ctx.t("no_meals"), name="history")
    pages = -(-len(rows) // page_size)
    page = min(wanted, pages - 1)
    buttons = [Button(row['eaten_at'].replace("T", " ")[:16] + " - " + kcal_text(row['kcal']), "eaten", row['id'])
               for row in rows[page * page_size:(page + 1) * page_size]]
    if pages > 1:
        buttons += [Button(ctx.t("previous"), "history", max(0, page - 1)),
                    Button(ctx.t("next"), "history", min(pages - 1, page + 1))]
    return View(text=ctx.t("pick", page=italic(page + 1), pages=italic(pages), total=italic(len(rows))),
                buttons=buttons, name="history", argument=str(page))


def meal_view(ctx: Ctx, row, line: str = "") -> View:
    text = meal_lines(ctx, row['kcal'], row['eaten_at'], False)
    return View(text=line + "\n\n" + text if line else text, name="eaten", argument=str(row['id']),
                buttons=[Button(ctx.t("edit_kcal"), "edit", row['id']), Button(ctx.t("edit_when"), "move", row['id']),
                         Button(ctx.t("remove"), "delete", row['id'])])


@module.callback("eaten")
def open_meal(ctx: Ctx) -> View:
    return meal_screen(ctx)


@module.view("eaten", parent="history", title="meal")
def meal_screen(ctx: Ctx) -> View:
    row = meal_of(ctx, wanted_number(ctx))
    return gone(ctx) if row is None else meal_view(ctx, row)


def changed(ctx: Ctx, meal: int, column: str, value) -> View:
    if column not in ("kcal", "eaten_at"):
        raise ValueError("Unknown column: " + column)
    if not ctx.db.execute("UPDATE " + table(ctx) + " SET " + column + " = ? WHERE id = ? AND user_id = ?;",
                          (value, meal, ctx.user.id)).rowcount:
        return gone(ctx)
    ctx.log("Meal " + str(meal) + " changed")
    return meal_view(ctx, meal_of(ctx, meal), ctx.t("changed"))


@module.callback("edit")
def open_edit(ctx: Ctx) -> View:
    if meal_of(ctx, wanted_number(ctx)) is None:
        return gone(ctx)
    return ctx.form("new_kcal", known={'entry': wanted_number(ctx)})


@module.form("new_kcal", [kcal_question], parent="eaten", title="edit_kcal")
def kcal_edited(ctx: Ctx, answers: Answers) -> View:
    return changed(ctx, answers['entry'], "kcal", answers['kcal'])


@module.callback("move")
def open_move(ctx: Ctx) -> View:
    if meal_of(ctx, wanted_number(ctx)) is None:
        return gone(ctx)
    return ctx.form("new_time", known={'entry': wanted_number(ctx)})


@module.form("new_time", [when_question], parent="eaten", title="edit_when")
def moved(ctx: Ctx, answers: Answers) -> View:
    return changed(ctx, answers['entry'], "eaten_at", answers['when'])


@module.callback("delete")
def open_delete(ctx: Ctx) -> View:
    row = meal_of(ctx, wanted_number(ctx))
    if row is None:
        return gone(ctx)
    return View(text=ctx.t("sure") + "\n" + meal_lines(ctx, row['kcal'], row['eaten_at'], False), name="eaten",
                argument=str(row['id']), buttons=[Button(ctx.t("core:yes_button"), "delete_confirmed", row['id'])])


@module.callback("delete_confirmed")
def confirm_delete(ctx: Ctx) -> View:
    wanted = wanted_number(ctx)
    removed = ctx.db.execute("DELETE FROM " + table(ctx) + " WHERE id = ? AND user_id = ?;",
                             (wanted, ctx.user.id)).rowcount
    if not removed:
        return gone(ctx)
    ctx.log("Meal " + str(wanted) + " deleted")
    found = meals_page(ctx, 0)
    return replace(found, text=ctx.t("deleted") + "\n\n" + found.text)


def gone(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone"))


# ----- the assistant -----

@module.context()
def summary(ctx: Ctx) -> str:
    day = date.today().isoformat()
    food, drunk, wanted = daily(ctx, date.today()).get(day, 0.0), alcohol(ctx, date.today()).get(day, 0.0), goal(ctx)
    if not food and not drunk and wanted is None:
        return ""
    lines = [labelled(ctx.t("context.today"), kcal_text(food + drunk))
             + (" (" + ctx.t("with_alcohol", kcal=kcal_text(drunk)) + ")" if drunk else "")]
    if wanted is not None:
        lines.append(labelled(ctx.t("labels.goal"), kcal_text(wanted)))
    return "\n".join(lines)


@module.action("add_meal", parameters={'kcal': float, 'when': str}, optional=["when"], is_confirmed=True)
def act_add_meal(ctx: Ctx, kcal: float, when: str | None) -> Outcome:
    moment = datetime.now().isoformat(timespec="seconds") if when is None else past_moment(when)
    if moment is None:
        return Outcome.refused(ctx.t("core:form.wrong_moment_any"))
    if not kcal_limits[0] <= kcal <= kcal_limits[1]:
        return Outcome.refused(ctx.t("core:form.range", low=kcal_limits[0], high=kcal_limits[1]))
    return Outcome.ask(ctx.t("add_sure") + "\n" + meal_lines(ctx, kcal, moment, False),
                       partial(meal_added, ctx, kcal, moment))


def meal_added(ctx: Ctx, value: float, moment: str) -> str:
    insert(ctx, value, moment)
    ctx.log("Meal logged by the assistant")
    return ctx.t("saved") + "\n" + meal_lines(ctx, value, moment, True)


@module.action("days")
def act_days(ctx: Ctx) -> Outcome:
    since = date.today() - timedelta(days=told_days - 1)
    food, drunk = daily(ctx, since), alcohol(ctx, since)
    return Outcome.done({'goal_kcal': goal(ctx),
                         'days': [{'day': day, 'food_kcal': round(food.get(day, 0.0)),
                                   'alcohol_kcal': round(drunk.get(day, 0.0))}
                                  for day in sorted(set(food) | set(drunk))]})


# ----- over time -----

def draw(days: list[tuple[date, float, float]], wanted: float | None, texts: dict) -> bytes:
    figure = Figure(figsize=(8, 4.5), dpi=120, facecolor=colors['surface'])
    axes = figure.subplots()
    axes.set_facecolor(colors['surface'])
    moments = [day for day, _, _ in days]
    food = [value for _, value, _ in days]
    axes.bar(moments, food, width=0.8, color=colors['food'], label=texts['food'])
    if any(drunk for _, _, drunk in days):
        axes.bar(moments, [drunk for _, _, drunk in days], width=0.8, bottom=food, color=colors['alcohol'],
                 edgecolor=colors['surface'], linewidth=1, label=texts['alcohol'])
        axes.legend(frameon=False, loc="upper left", labelcolor=colors['ink'], fontsize=8)
    if wanted is not None:
        axes.axhline(wanted, color=colors['goal'], linewidth=1.5, linestyle="--")
        axes.annotate(texts['goal'] + " " + "{:.0f}".format(wanted), (1, wanted), xycoords=("axes fraction", "data"),
                      xytext=(0, 4), textcoords="offset points", ha="right", color=colors['ink'], fontsize=8)
    axes.set_title(texts['title'], color=colors['ink'], loc="left")
    axes.set_ylabel("kcal", color=colors['muted'])
    axes.grid(axis="y", color=colors['grid'], linewidth=0.8)
    axes.set_axisbelow(True)
    axes.tick_params(colors=colors['muted'])
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(colors['axis'])
    locator = AutoDateLocator()
    axes.xaxis.set_major_locator(locator)
    axes.xaxis.set_major_formatter(ConciseDateFormatter(locator))
    figure.tight_layout()
    picture = io.BytesIO()
    figure.savefig(picture, format="png", facecolor=colors['surface'])
    return picture.getvalue()


@module.callback("chart", is_background=True)
def open_chart(ctx: Ctx) -> View:
    return chart(ctx)


@module.view("chart", parent="menu", title="chart")
def chart(ctx: Ctx) -> View:
    first = date.today() - timedelta(days=chart_days - 1)
    food, drunk = daily(ctx, first), alcohol(ctx, first)
    if not food and not drunk:
        return View(text=ctx.t("empty"))
    days = [first + timedelta(days=offset) for offset in range(chart_days)]
    wanted = goal(ctx)
    photo = draw([(day, food.get(day.isoformat(), 0.0), drunk.get(day.isoformat(), 0.0)) for day in days], wanted,
                 {key: plain(ctx.t("chart_texts." + key)) for key in ("title", "food", "alcohol", "goal")})
    lines = [escape(day + " - " + kcal_text(food.get(day, 0.0) + drunk.get(day, 0.0))) +
             (" (" + ctx.t("with_alcohol", kcal=kcal_text(drunk[day])) + ")" if drunk.get(day) else "")
             for day in sorted(set(food) | set(drunk))]
    goal_line = [labelled(ctx.t("labels.goal"), kcal_text(wanted))] if wanted is not None else []
    ctx.log("Calories chart shown")
    return View(text="\n".join(goal_line + lines), photo=photo)


# ----- settings -----

@module.settings()
def settings(ctx: Ctx) -> View:
    buttons = [Button(ctx.t("set_goal"), "set_goal")]
    if ctx.has_module("calories") and ctx.has_module("bodytracker"):
        buttons.append(Button(ctx.t("auto_goal"), "auto_goal"))
    return View(text=ctx.t("settings_text") + "\n\n" + labelled(ctx.t("labels.goal"), goal_name(ctx)),
                buttons=buttons)


@module.callback("set_goal")
def open_goal(ctx: Ctx) -> View:
    return ctx.form("goal")


@module.form("goal", [Question("kcal", low=500, high=6000, text="ask.goal")], parent="settings", title="set_goal")
def goal_given(ctx: Ctx, answers: Answers) -> View:
    ctx.state.set(goal_key, "{:g}".format(answers['kcal']))
    ctx.state.delete(activity_key)
    ctx.log("Goal set")
    return settings(ctx)


@module.callback("auto_goal")
def open_auto(ctx: Ctx) -> View:
    return ctx.form("auto")


@module.form("auto", [Question("activity", "choice", choices=activities, labels="activity_choice")], parent="settings",
             title="auto_goal")
def auto_given(ctx: Ctx, answers: Answers) -> View:
    ctx.state.set(activity_key, answers['activity'])
    ctx.log("Goal follows the body tracker")
    return settings(ctx)
