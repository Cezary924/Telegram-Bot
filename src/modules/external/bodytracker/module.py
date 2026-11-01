import io
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta

from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure

from core.api import Answers, Button, Ctx, Module, Outcome, Question, View, escape, italic, labelled, past_moment

module = Module(name="bodytracker", place=40, is_guarded=True,
                icons={'name': "⚖️", 'log': "➕", 'history': "📜", 'chart': "📈", 'settings_button': "⚙️",
                       'set_height': "📏", 'heights': "📜", 'edit_value': "✏️", 'edit_when': "🕒", 'remove': "🗑️",
                       'previous': "⬅️", 'next': "➡️"},
                endings={'how': "💪", 'saved': "✅", 'height_saved': "✅", 'changed': "✅", 'deleted': "✅",
                         'empty.weight': "🤷", 'empty.height': "🤷", 'gone': "💔"})

fresh_days = 30
weight_limits = (20.0, 400.0)
height_limits = (50.0, 250.0)
history_limit = 60
page_size = 8
moment_format = "%Y-%m-%d %H:%M"
kinds = {'weight': "weights", 'height': "heights"}
colors = {'surface': "#fcfcfb", 'ink': "#0b0b0b", 'muted': "#898781", 'grid': "#e1e0d9", 'axis': "#c3c2b7",
          'line': "#2a78d6"}


def table(ctx: Ctx, kind: str) -> str:
    return ctx.db.table(kinds[kind])


def rows_of(ctx: Ctx, kind: str) -> list:
    return ctx.db.query_all("SELECT id, " + kind + " AS value, measured_at FROM " + table(ctx, kind) +
                            " WHERE user_id = ? ORDER BY measured_at, id;", (ctx.user.id,))


def row_of(ctx: Ctx, kind: str, entry: int):
    return ctx.db.query_one("SELECT id, " + kind + " AS value, measured_at FROM " + table(ctx, kind) +
                            " WHERE id = ? AND user_id = ?;", (entry, ctx.user.id))


def height_now(ctx: Ctx) -> float | None:
    rows = rows_of(ctx, "height")
    return rows[-1]['value'] if rows else None


def now_moment() -> str:
    return datetime.now().isoformat(timespec="seconds")


def insert(ctx: Ctx, kind: str, value: float, when: str) -> None:
    ctx.db.execute("INSERT INTO " + table(ctx, kind) + " (user_id, " + kind + ", measured_at) VALUES (?, ?, ?);",
                   (ctx.user.id, round(value, 2), when))


def update(ctx: Ctx, kind: str, entry: int, column: str, value) -> bool:
    if column not in (kind, "measured_at"):
        raise ValueError("Unknown column: " + column)
    return bool(ctx.db.execute("UPDATE " + table(ctx, kind) + " SET " + column + " = ? WHERE id = ? AND user_id = ?;",
                               (value, entry, ctx.user.id)).rowcount)


def shown(ctx: Ctx, kind: str, value: float) -> str:
    return ctx.profile.weight(value) if kind == "weight" else ctx.profile.height(value)


def is_fresh(measured_at: str, now: datetime) -> bool:
    return now - datetime.fromisoformat(measured_at) <= timedelta(days=fresh_days)


def is_recent(measured_at: str, now: datetime) -> bool:
    return now - datetime.fromisoformat(measured_at) <= timedelta(hours=1)


# ----- what the other modules read -----

@module.expose("latest")
def latest(ctx: Ctx) -> dict:
    rows = rows_of(ctx, "weight")
    weight = rows[-1]['value'] if rows and is_fresh(rows[-1]['measured_at'], datetime.now()) else None
    return {'weight': weight, 'height': height_now(ctx)}


@module.expose("weights")
def weights(ctx: Ctx) -> list[tuple[str, float]]:
    return [(row['measured_at'], row['value']) for row in rows_of(ctx, "weight")]


@module.expose("heights")
def heights(ctx: Ctx) -> list[tuple[str, float]]:
    return [(row['measured_at'], row['value']) for row in rows_of(ctx, "height")]


@module.expose("save", is_writing=True)
def save(ctx: Ctx, values: dict) -> list[str]:
    saved = []
    if weight_limits[0] <= values.get('weight', 0) <= weight_limits[1]:
        rows = rows_of(ctx, "weight")
        now = datetime.now()
        if not rows or rows[-1]['value'] != round(values['weight'], 2) or not is_recent(rows[-1]['measured_at'], now):
            insert(ctx, "weight", values['weight'], now.isoformat(timespec="seconds"))
        saved.append("weight")
    if height_limits[0] <= values.get('height', 0) <= height_limits[1]:
        if height_now(ctx) != round(values['height'], 2):
            insert(ctx, "height", values['height'], now_moment())
        saved.append("height")
    if saved:
        ctx.log("Body data saved from another module")
    return saved


# ----- the assistant -----

def changes(ctx: Ctx, label: str, rows: list, show: Callable[[float], str]) -> str:
    if not rows:
        return ""
    earlier = [("before", rows[-2])] if len(rows) > 1 else []
    earlier += [("first", rows[0])] if len(rows) > 2 else []
    return ", ".join([labelled(ctx.t("labels." + label), show(rows[-1]['value']) + " (" + rows[-1]['measured_at'][:10]
                               + ")")] + [ctx.t("context." + key, value=show(row['value']), day=row['measured_at'][:10])
                                          for key, row in earlier])


@module.context()
def summary(ctx: Ctx) -> str:
    profile = ctx.profile
    lines = [changes(ctx, "weight", rows_of(ctx, "weight"), profile.weight),
             changes(ctx, "height", rows_of(ctx, "height"), profile.height)]
    if profile.sex:
        lines.append(labelled(ctx.t("labels.sex"), ctx.t("sex." + profile.sex)))
    if profile.age is not None:
        lines.append(labelled(ctx.t("labels.age"), profile.age))
    return "\n".join(line for line in lines if line)


def moment_of(ctx: Ctx, when: str | None) -> tuple[str, str]:
    if when is None:
        return now_moment(), ""
    found = past_moment(when)
    return (found, "") if found else ("", ctx.t("core:form.wrong_moment_any"))


def measured(ctx: Ctx, kind: str, value: float, moment: str) -> str:
    return "\n".join([labelled(ctx.t("labels." + kind), shown(ctx, kind, value)),
                      labelled(ctx.t("labels.when"), moment.replace("T", " ")[:16])])


def logged(ctx: Ctx, kind: str, value: float, when: str | None) -> Outcome:
    moment, problem = moment_of(ctx, when)
    low, high = weight_limits if kind == "weight" else height_limits
    if not low <= value <= high:
        problem = ctx.t("wrong." + kind, low="{:g}".format(low), high="{:g}".format(high))
    if problem:
        return Outcome.refused(problem)
    details = measured(ctx, kind, value, moment)
    return Outcome.ask(ctx.t(kind + "_sure") + "\n" + details, lambda: confirmed(ctx, kind, value, moment, details))


def confirmed(ctx: Ctx, kind: str, value: float, moment: str, details: str) -> str:
    insert(ctx, kind, value, moment)
    ctx.log(kind.capitalize() + " logged by the assistant")
    return ctx.t("saved" if kind == "weight" else "height_saved") + "\n" + details


@module.action("log_weight", parameters={'weight': float, 'when': str}, optional=["when"], is_confirmed=True)
def act_log_weight(ctx: Ctx, weight: float, when: str | None) -> Outcome:
    return logged(ctx, "weight", weight, when)


@module.action("log_height", parameters={'height': float, 'when': str}, optional=["when"], is_confirmed=True)
def act_log_height(ctx: Ctx, height: float, when: str | None) -> Outcome:
    return logged(ctx, "height", height, when)


@module.action("history")
def act_history(ctx: Ctx) -> Outcome:
    return Outcome.done({'weights_kg': [{'when': row['measured_at'], 'weight': row['value']}
                                        for row in rows_of(ctx, "weight")[-history_limit:]],
                         'heights_cm': [{'when': row['measured_at'], 'height': row['value']}
                                        for row in rows_of(ctx, "height")[-history_limit:]]})


# ----- menu -----

@module.command("bodytracker")
def command_bodytracker(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(text=ctx.t("how"), buttons=[Button(ctx.t("log"), "log"),
                                            Button(ctx.t("history"), "history"),
                                            Button(ctx.t("chart"), "chart"),
                                            Button.settings(ctx.t("settings_button"), module.name)])


# ----- logging -----

def value_question(kind: str) -> Question:
    low, high = weight_limits if kind == "weight" else height_limits
    return Question(kind, kind, low=low, high=high)


when_question = Question("when", "moment", back=None)


@module.callback("log")
def open_log(ctx: Ctx) -> View:
    return ctx.form("weight")


@module.form("weight", [value_question("weight"), when_question], parent="menu", title="log")
def weight_given(ctx: Ctx, answers: Answers) -> View:
    insert(ctx, "weight", answers['weight'], answers['when'])
    ctx.close_screen()
    ctx.log("Weight logged")
    return View(text=ctx.t("saved") + "\n" + measured(ctx, "weight", answers['weight'], answers['when']))


@module.callback("set_height")
def open_height(ctx: Ctx) -> View:
    return ctx.form("height")


@module.form("height", [value_question("height"), when_question], parent="settings", title="set_height")
def height_given(ctx: Ctx, answers: Answers) -> View:
    insert(ctx, "height", answers['height'], answers['when'])
    ctx.log("Height logged")
    return replace_text(settings(ctx), ctx.t("height_saved"))


# ----- entries -----

def wanted_number(ctx: Ctx, position: int = 0) -> int:
    found = ctx.arguments[position] if len(ctx.arguments) > position else ""
    return int(found) if found.isdigit() else 0


def entries(ctx: Ctx, kind: str) -> View:
    rows = list(reversed(rows_of(ctx, kind)))
    if not rows:
        return View(text=ctx.t("empty." + kind))
    pages = -(-len(rows) // page_size)
    page = min(wanted_number(ctx), pages - 1)
    buttons = [Button(row['measured_at'].replace("T", " ")[:16] + " - " + shown(ctx, kind, row['value']),
                      kind + "_entry", row['id']) for row in rows[page * page_size:(page + 1) * page_size]]
    if pages > 1:
        buttons += [Button(ctx.t("previous"), kinds[kind], max(0, page - 1)),
                    Button(ctx.t("next"), kinds[kind], min(pages - 1, page + 1))]
    return View(text=ctx.t("pick", page=italic(page + 1), pages=italic(pages), total=italic(len(rows))),
                buttons=buttons, argument=str(page))


@module.callback("history")
def open_history(ctx: Ctx) -> View:
    return history(ctx)


@module.view("history", parent="menu", title="history")
def history(ctx: Ctx) -> View:
    return entries(ctx, "weight")


@module.callback("weights")
def turn_weights(ctx: Ctx) -> View:
    return history(ctx)


@module.callback("heights")
def open_heights(ctx: Ctx) -> View:
    return heights_screen(ctx)


@module.view("heights", parent="settings", title="heights")
def heights_screen(ctx: Ctx) -> View:
    return entries(ctx, "height")


def entry_of(ctx: Ctx, kind: str, entry: int) -> View:
    row = row_of(ctx, kind, entry)
    if row is None:
        return gone(ctx)
    return View(text=measured(ctx, kind, row['value'], row['measured_at']), name=kind + "_entry", argument=str(entry),
                buttons=[Button(ctx.t("edit_value"), "edit", kind, entry),
                         Button(ctx.t("edit_when"), "move", kind, entry),
                         Button(ctx.t("remove"), "remove", kind, entry)])


@module.callback("weight_entry")
def open_weight_entry(ctx: Ctx) -> View:
    return weight_entry(ctx)


@module.view("weight_entry", parent="history", title="entry")
def weight_entry(ctx: Ctx) -> View:
    return entry_of(ctx, "weight", wanted_number(ctx))


@module.callback("height_entry")
def open_height_entry(ctx: Ctx) -> View:
    return height_entry(ctx)


@module.view("height_entry", parent="heights", title="entry")
def height_entry(ctx: Ctx) -> View:
    return entry_of(ctx, "height", wanted_number(ctx))


def picked(ctx: Ctx) -> tuple[str, int]:
    kind = ctx.arguments[0] if ctx.arguments else ""
    return (kind, wanted_number(ctx, 1)) if kind in kinds else ("", 0)


@module.callback("edit")
def open_edit(ctx: Ctx) -> View:
    kind, entry = picked(ctx)
    if not kind or row_of(ctx, kind, entry) is None:
        return gone(ctx)
    return ctx.form("edit_" + kind, known={'entry': entry})


def edited(ctx: Ctx, kind: str, answers: Answers, column: str, key: str) -> View:
    if not update(ctx, kind, answers['entry'], column, round(answers[key], 2) if key == kind else answers[key]):
        return gone(ctx)
    ctx.log(kind.capitalize() + " entry " + str(answers['entry']) + " changed")
    return replace_text(entry_of(ctx, kind, answers['entry']), ctx.t("changed"))


def replace_text(view: View, line: str) -> View:
    return replace(view, text=line + "\n\n" + view.text)


@module.form("edit_weight", [value_question("weight")], parent="weight_entry", title="edit_value")
def weight_edited(ctx: Ctx, answers: Answers) -> View:
    return edited(ctx, "weight", answers, "weight", "weight")


@module.form("edit_height", [value_question("height")], parent="height_entry", title="edit_value")
def height_edited(ctx: Ctx, answers: Answers) -> View:
    return edited(ctx, "height", answers, "height", "height")


@module.callback("move")
def open_move(ctx: Ctx) -> View:
    kind, entry = picked(ctx)
    if not kind or row_of(ctx, kind, entry) is None:
        return gone(ctx)
    return ctx.form("move_" + kind, known={'kind': kind, 'entry': entry})


@module.form("move_weight", [when_question], parent="weight_entry", title="edit_when")
@module.form("move_height", [when_question], parent="height_entry", title="edit_when")
def moved(ctx: Ctx, answers: Answers) -> View:
    return edited(ctx, answers['kind'], answers, "measured_at", "when")


@module.callback("remove")
def open_remove(ctx: Ctx) -> View:
    kind, entry = picked(ctx)
    if not kind:
        return gone(ctx)
    row = row_of(ctx, kind, entry)
    if row is None:
        return gone(ctx)
    return View(text=ctx.t("sure") + "\n" + measured(ctx, kind, row['value'], row['measured_at']),
                name=kind + "_entry", argument=str(entry),
                buttons=[Button(ctx.t("core:yes_button"), "remove_confirmed", kind, entry)])


@module.callback("remove_confirmed")
def confirm_remove(ctx: Ctx) -> View:
    kind, entry = picked(ctx)
    removed = ctx.db.execute("DELETE FROM " + table(ctx, kind) + " WHERE id = ? AND user_id = ?;",
                             (entry, ctx.user.id)).rowcount if kind else 0
    if not removed:
        return gone(ctx)
    ctx.log(kind.capitalize() + " entry " + str(entry) + " deleted")
    view = history(ctx) if kind == "weight" else heights_screen(ctx)
    return replace_text(view, ctx.t("deleted"))


def gone(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone"))


# ----- the chart -----

def draw(points: list[tuple[datetime, float]], title: str, unit: str) -> bytes:
    figure = Figure(figsize=(8, 4.5), dpi=120, facecolor=colors['surface'])
    axes = figure.subplots()
    axes.set_facecolor(colors['surface'])
    axes.plot([moment for moment, _ in points], [value for _, value in points], color=colors['line'],
              linewidth=2, marker="o", markersize=5)
    axes.set_title(title, color=colors['ink'], loc="left")
    axes.set_ylabel(unit, color=colors['muted'])
    axes.grid(color=colors['grid'], linewidth=0.8)
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
    rows = rows_of(ctx, "weight")
    if not rows:
        return View(text=ctx.t("empty.weight"))
    profile = ctx.profile
    photo = draw([(datetime.fromisoformat(row['measured_at']), profile.in_weight_unit(row['value'])) for row in rows],
                 ctx.t("chart_title"), profile.weight_name)
    ctx.log("Weight chart shown")
    return View(text="\n".join(escape(row['measured_at'][:10] + " - " + profile.weight(row['value'])) for row in rows),
                photo=photo)


# ----- settings -----

@module.settings()
def settings(ctx: Ctx) -> View:
    height = height_now(ctx)
    line = labelled(ctx.t("labels.height"), ctx.profile.height(height) if height else ctx.t("unknown"))
    buttons = [Button(ctx.t("set_height"), "set_height")] + ([Button(ctx.t("heights"), "heights")] if height else [])
    return View(text=ctx.t("settings_text") + "\n\n" + line, buttons=buttons)
