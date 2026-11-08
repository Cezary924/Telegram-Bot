import io
import re
import unicodedata
from dataclasses import replace
from datetime import datetime, time, timedelta
from functools import partial
from itertools import accumulate

from matplotlib.figure import Figure

from core.api import (Answers, Button, Ctx, Module, Outcome, Problem, Question, View, bold, escape, italic, labelled,
                      plain)

module = Module(name="counter", place=35, is_guarded=True,
                icons={'name': "🔢", 'new': "➕", 'settings_button': "⚙️", 'type_amount': "✍️", 'edit': "✏️",
                       'remove': "🗑️", 'history': "📜", 'chart': "📈", 'edit_name': "🏷️", 'edit_step': "👣",
                       'edit_goal': "🎯", 'edit_period': "🔄", 'edit_amount': "✏️", 'edit_when': "🕒", 'erase': "🗑️",
                       'undo': "↩️", 'open': "🔢", 'set_week': "📅", 'previous': "⬅️", 'next': "➡️"},
                endings={'how': "😊", 'created': "✅", 'changed': "✅", 'deleted': "✅", 'changed_entry': "✅",
                         'deleted_entry': "✅", 'undone': "✅", 'reached': "🎉", 'empty': "🤷", 'no_changes': "🤷",
                         'gone': "💔", 'gone_entry': "💔"})

priority = 5
periods = ("never", "daily", "weekly", "monthly")
week_starts = {'monday': 0, 'sunday': 6}
name_limit = 30
counter_limit = 20
step_limits = (0.01, 1000)
goal_limits = (0.01, 100000)
amount_limit = 100000
page_size = 8
history_limit = 60
chart_days = 30
chart_periods = 12
bar_size = 10
bar_widths = {'daily': 0.8, 'weekly': 5.0, 'monthly': 20.0}
bar_middles = {'daily': 0.0, 'weekly': 3.5, 'monthly': 15.0}
day_formats = {'daily': "%d.%m", 'weekly': "%d.%m", 'monthly': "%m.%Y"}
tick_count = 8
week_key = "week"
reached_key = "reached."
colors = {'surface': "#fcfcfb", 'ink': "#0b0b0b", 'muted': "#898781", 'grid': "#e1e0d9", 'axis': "#c3c2b7",
          'count': "#2a78d6", 'goal': "#0b0b0b", 'reached': "#0ca30c", 'missed': "#d03b3b"}
number = r"[+-]\s*\d+(?:[.,]\d+)?"
trailing = re.compile(r"(?P<name>.*?\S)\s*(?P<amount>" + number + ")")
leading = re.compile(r"(?P<amount>" + number + r")\s*(?P<name>\S.*)")
amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?")
signed_name = re.compile(number + ".*|.*\\s" + number)


def table(ctx: Ctx, name: str) -> str:
    return ctx.db.table(name)


def counters_of(ctx: Ctx) -> list:
    return ctx.db.query_all("SELECT id, name, step, goal, period FROM " + table(ctx, "counters") +
                            " WHERE user_id = ? ORDER BY id;", (ctx.user.id,))


def counter_of(ctx: Ctx, counter: int):
    return ctx.db.query_one("SELECT id, name, step, goal, period FROM " + table(ctx, "counters") +
                            " WHERE id = ? AND user_id = ?;", (counter, ctx.user.id))


def entry_of(ctx: Ctx, entry_id: int):
    return ctx.db.query_one("SELECT changes.id, changes.counter_id, changes.amount, changes.changed_at, counters.name "
                            "FROM " + table(ctx, "changes") + " AS changes JOIN " + table(ctx, "counters") +
                            " AS counters ON counters.id = changes.counter_id WHERE changes.id = ? "
                            "AND changes.user_id = ?;", (entry_id, ctx.user.id))


def changes_of(ctx: Ctx, counter: int, since: datetime = datetime.min) -> list:
    return ctx.db.query_all("SELECT id, amount, changed_at FROM " + table(ctx, "changes") + " WHERE counter_id = ? "
                            "AND user_id = ? AND changed_at >= ? ORDER BY changed_at, id;",
                            (counter, ctx.user.id, moment_text(since)))


def wanted_number(ctx: Ctx, position: int = 0) -> int:
    parts = ":".join(ctx.arguments).split(":")
    found = parts[position] if len(parts) > position else ""
    return int(found) if found.isdigit() else 0


def moment_text(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def number_text(value: float) -> str:
    return "{:.2f}".format(round(value, 2) + 0.0).rstrip("0").rstrip(".")


def signed_text(value: float) -> str:
    return ("+" if value > 0 else "") + number_text(value)


def key_of(name: str) -> str:
    return " ".join(re.sub(r"[^\w\s-]|_", " ", name.casefold()).split())


def bare_name(name: str) -> str:
    return " ".join("".join(char for char in name if unicodedata.category(char) not in ("So", "Sk", "Cf", "Mn"))
                    .split())


def above(line: str, text: str) -> str:
    return line + "\n\n" + text if line else text


# ----- periods -----

def week_name(ctx: Ctx) -> str:
    found = ctx.state.get(week_key) or ""
    return found if found in week_starts else "monday"


def week_of(ctx: Ctx) -> int:
    return week_starts[week_name(ctx)]


def period_start(period: str, now: datetime, week: int) -> datetime:
    day = datetime.combine(now.date(), time())
    if period == "daily":
        return day
    if period == "weekly":
        return day - timedelta(days=(day.weekday() - week) % 7)
    if period == "monthly":
        return day.replace(day=1)
    return datetime.min


def value_of(ctx: Ctx, row, now: datetime) -> float:
    found = ctx.db.query_one("SELECT SUM(amount) AS total FROM " + table(ctx, "changes") + " WHERE counter_id = ? "
                             "AND user_id = ? AND changed_at >= ?;",
                             (row['id'], ctx.user.id, moment_text(period_start(row['period'], now, week_of(ctx)))))
    return round(found['total'] or 0.0, 2)


def state_text(row, value: float) -> str:
    return number_text(value) + (" / " + number_text(row['goal']) if row['goal'] is not None else "")


def bar_text(row, value: float) -> str:
    if row['goal'] is None:
        return ""
    share = max(0.0, value / row['goal'])
    filled = min(bar_size, int(share * bar_size + 1e-9))
    return "▰" * filled + "▱" * (bar_size - filled) + " " + "{:.0f}%".format(share * 100)


def state_lines(ctx: Ctx, row, value: float) -> list[str]:
    lines = [labelled(row['name'], state_text(row, value) + " " + plain(ctx.t("now." + row['period'])))]
    return lines + ([bar_text(row, value)] if row['goal'] is not None else [])


def reached_line(ctx: Ctx, row, before: float, now: datetime) -> str:
    key = reached_key + str(row['id'])
    start = moment_text(period_start(row['period'], now, week_of(ctx)))
    after = value_of(ctx, row, now)
    if row['goal'] is None or not before < row['goal'] <= after or ctx.state.get(key) == start:
        return ""
    ctx.state.set(key, start)
    return ctx.t("reached")


def rechecked(ctx: Ctx, counter: int) -> None:
    row = counter_of(ctx, counter)
    if row is not None and (row['goal'] is None or value_of(ctx, row, datetime.now()) < row['goal']):
        ctx.state.delete(reached_key + str(counter))


def counted(ctx: Ctx, row, amount: float) -> tuple[int, str]:
    now = datetime.now()
    before = value_of(ctx, row, now)
    cursor = ctx.db.execute("INSERT INTO " + table(ctx, "changes") + " (counter_id, user_id, amount, changed_at) "
                            "VALUES (?, ?, ?, ?);", (row['id'], ctx.user.id, round(amount, 2), moment_text(now)))
    return cursor.lastrowid or 0, reached_line(ctx, row, before, now)


# ----- checking -----

def taken_by(ctx: Ctx, counter: int = 0) -> list[str]:
    return [key_of(row['name']) for row in counters_of(ctx) if row['id'] != counter]


def readings(text: str) -> list[tuple[str, float]]:
    text = " ".join(text.split())
    found = []
    for pattern in (trailing, leading):
        match = pattern.fullmatch(text)
        if match is not None:
            found.append((key_of(match['name']), float(match['amount'].replace(" ", "").replace(",", "."))))
    return found


def parse_name(text: str, values: dict) -> str | Problem:
    name = " ".join(text.split())
    if not 1 <= len(name) <= name_limit:
        return Problem("core:form.length", {'low': 1, 'high': name_limit})
    if not any(char.isalpha() for char in key_of(name)):
        return Problem("wrong.letter")
    if signed_name.fullmatch(name):
        return Problem("wrong.sign")
    if key_of(name) in values.get('taken', []):
        return Problem("wrong.taken", {'name': name})
    return name


def amount_problem(amount: float) -> Problem | None:
    if round(amount, 2) == 0:
        return Problem("wrong.zero")
    if abs(amount) > amount_limit:
        return Problem("wrong.too_much", {'high': amount_limit})
    return None


def parse_amount(text: str, _values: dict) -> float | Problem | None:
    compact = "".join(text.split())
    if not amount_pattern.fullmatch(compact):
        return None
    amount = float(compact.replace(",", "."))
    return amount_problem(amount) or round(amount, 2)


def problem_text(ctx: Ctx, problem: Problem) -> str:
    return ctx.t(problem.key, **problem.values)


# ----- menu -----

@module.command("counter")
def command_counter(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(text=ctx.t("how"),
                buttons=[Button(escape(row['name']), "one", row['id']) for row in counters_of(ctx)] +
                [Button(ctx.t("new"), "new"), Button.settings(ctx.t("settings_button"), module.name)])


name_question = Question("name", "text", parse=parse_name)
step_question = Question("step", low=step_limits[0], high=step_limits[1], clear="one_step")
goal_question = Question("goal", low=goal_limits[0], high=goal_limits[1], clear="no_goal")
period_question = Question("period", "choice", choices=periods, labels="period")
amount_question = Question("amount", parse=parse_amount, problem="wrong.amount")
when_question = Question("when", "moment", back=None)


@module.callback("new")
def open_new(ctx: Ctx) -> View:
    if len(counters_of(ctx)) >= counter_limit:
        return ctx.retry(ctx.t("full", limit=counter_limit))
    return ctx.form("create", known={'taken': taken_by(ctx)})


@module.form("create", [name_question, step_question, goal_question, period_question], parent="menu", title="new")
def created(ctx: Ctx, answers: Answers) -> View:
    if len(counters_of(ctx)) >= counter_limit:
        ctx.close_screen()
        return View(text=ctx.t("full", limit=counter_limit))
    counter = ctx.db.execute("INSERT INTO " + table(ctx, "counters") + " (user_id, name, step, goal, period) "
                             "VALUES (?, ?, ?, ?, ?);",
                             (ctx.user.id, answers['name'], round(answers['step'] or 1, 2), answers['goal'],
                              answers['period'])).lastrowid or 0
    ctx.log("Counter made")
    return counter_view(ctx, counter_of(ctx, counter), ctx.t("created"))


# ----- one counter -----

def counter_view(ctx: Ctx, row, line: str = "") -> View:
    value = value_of(ctx, row, datetime.now())
    step = number_text(row['step'])
    lines = [bold(row['name']), bold(state_text(row, value)) + " " + ctx.t("now." + row['period'])]
    if row['goal'] is not None:
        lines.append(bar_text(row, value))
    return View(text=above(line, "\n".join(lines)), name="one", argument=str(row['id']), columns=2,
                buttons=[Button("➖ " + step, "minus", row['id']), Button("➕ " + step, "plus", row['id']),
                         Button(ctx.t("type_amount"), "amount", row['id']), Button(ctx.t("edit"), "edit", row['id']),
                         Button(ctx.t("history"), "history", row['id']), Button(ctx.t("chart"), "chart", row['id']),
                         Button(ctx.t("remove"), "delete", row['id'])])


@module.callback("one")
def open_one(ctx: Ctx) -> View:
    return one(ctx)


@module.view("one", parent="menu")
def one(ctx: Ctx) -> View:
    row = counter_of(ctx, wanted_number(ctx))
    return gone(ctx) if row is None else counter_view(ctx, row)


@module.callback("open")
def open_counter(ctx: Ctx) -> View:
    ctx.close_screen()
    return one(ctx)


def stepped(ctx: Ctx, sign: int) -> View:
    row = counter_of(ctx, wanted_number(ctx))
    if row is None:
        return gone(ctx)
    _, line = counted(ctx, row, sign * row['step'])
    ctx.log("Counted with a button")
    return counter_view(ctx, row, line)


@module.callback("plus")
def press_plus(ctx: Ctx) -> View:
    return stepped(ctx, 1)


@module.callback("minus")
def press_minus(ctx: Ctx) -> View:
    return stepped(ctx, -1)


@module.callback("amount")
def open_amount(ctx: Ctx) -> View:
    if counter_of(ctx, wanted_number(ctx)) is None:
        return gone(ctx)
    return ctx.form("add_amount", known={'counter': wanted_number(ctx)})


@module.form("add_amount", [amount_question], parent="one", title="type_amount")
def amount_given(ctx: Ctx, answers: Answers) -> View:
    row = counter_of(ctx, answers['counter'])
    if row is None:
        return gone(ctx)
    _, line = counted(ctx, row, answers['amount'])
    ctx.log("Amount counted")
    added = ctx.t("added", amount=signed_text(answers['amount']))
    return counter_view(ctx, row, added + ("\n" + line if line else ""))


# ----- editing -----

def details(ctx: Ctx, row) -> str:
    return "\n".join([labelled(ctx.t("labels.name"), row['name']),
                      labelled(ctx.t("labels.step"), number_text(row['step'])),
                      labelled(ctx.t("labels.goal"),
                               number_text(row['goal']) if row['goal'] is not None else ctx.t("none")),
                      labelled(ctx.t("labels.period"), ctx.t("period." + row['period']))])


def edit_view(ctx: Ctx, row, line: str = "") -> View:
    return View(text=above(line, details(ctx, row)), name="edit", argument=str(row['id']), columns=2,
                buttons=[Button(ctx.t("edit_name"), "name", row['id']), Button(ctx.t("edit_step"), "step", row['id']),
                         Button(ctx.t("edit_goal"), "goal", row['id']),
                         Button(ctx.t("edit_period"), "period", row['id'])])


@module.callback("edit")
def open_edit(ctx: Ctx) -> View:
    return edit(ctx)


@module.view("edit", parent="one", title="edit")
def edit(ctx: Ctx) -> View:
    row = counter_of(ctx, wanted_number(ctx))
    return gone(ctx) if row is None else edit_view(ctx, row)


def reopened(ctx: Ctx, form: str) -> View:
    counter = wanted_number(ctx)
    if counter_of(ctx, counter) is None:
        return gone(ctx)
    return ctx.form(form, known={'counter': counter, 'taken': taken_by(ctx, counter)})


@module.callback("name")
def open_name(ctx: Ctx) -> View:
    return reopened(ctx, "rename")


@module.callback("step")
def open_step(ctx: Ctx) -> View:
    return reopened(ctx, "restep")


@module.callback("goal")
def open_goal(ctx: Ctx) -> View:
    return reopened(ctx, "regoal")


@module.callback("period")
def open_period(ctx: Ctx) -> View:
    return reopened(ctx, "reperiod")


def changed(ctx: Ctx, counter: int, column: str, value) -> View:
    if column not in ("name", "step", "goal", "period"):
        raise ValueError("Unknown column: " + column)
    if not ctx.db.execute("UPDATE " + table(ctx, "counters") + " SET " + column + " = ? WHERE id = ? AND user_id = ?;",
                          (value, counter, ctx.user.id)).rowcount:
        return gone(ctx)
    if column in ("goal", "period"):
        ctx.state.delete(reached_key + str(counter))
    ctx.log("Counter " + str(counter) + " changed")
    return edit_view(ctx, counter_of(ctx, counter), ctx.t("changed"))


@module.form("rename", [name_question], parent="edit", title="edit_name")
def renamed(ctx: Ctx, answers: Answers) -> View:
    return changed(ctx, answers['counter'], "name", answers['name'])


@module.form("restep", [step_question], parent="edit", title="edit_step")
def restepped(ctx: Ctx, answers: Answers) -> View:
    return changed(ctx, answers['counter'], "step", round(answers['step'] or 1, 2))


@module.form("regoal", [goal_question], parent="edit", title="edit_goal")
def regoaled(ctx: Ctx, answers: Answers) -> View:
    return changed(ctx, answers['counter'], "goal", answers['goal'])


@module.form("reperiod", [period_question], parent="edit", title="edit_period")
def reperiodded(ctx: Ctx, answers: Answers) -> View:
    return changed(ctx, answers['counter'], "period", answers['period'])


@module.callback("delete")
def open_delete(ctx: Ctx) -> View:
    return removal(ctx)


@module.view("delete", parent="one", title="remove")
def removal(ctx: Ctx) -> View:
    row = counter_of(ctx, wanted_number(ctx))
    if row is None:
        return gone(ctx)
    return View(text=ctx.t("sure") + "\n" + details(ctx, row), argument=str(row['id']),
                buttons=[Button(ctx.t("core:yes_button"), "delete_confirmed", row['id'])])


@module.callback("delete_confirmed")
def confirm_delete(ctx: Ctx) -> View:
    counter = wanted_number(ctx)
    if not ctx.db.execute("DELETE FROM " + table(ctx, "counters") + " WHERE id = ? AND user_id = ?;",
                          (counter, ctx.user.id)).rowcount:
        return gone(ctx)
    ctx.state.delete(reached_key + str(counter))
    ctx.log("Counter " + str(counter) + " deleted")
    found = menu(ctx)
    return replace(found, text=ctx.t("deleted") + "\n\n" + found.text)


def gone(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone"))


# ----- history -----

def entry_lines(ctx: Ctx, name: str, amount: float, when: str) -> str:
    return "\n".join([labelled(ctx.t("labels.counter"), name), labelled(ctx.t("labels.amount"), signed_text(amount)),
                      labelled(ctx.t("labels.when"), when.replace("T", " ")[:16])])


@module.callback("history")
def open_history(ctx: Ctx) -> View:
    return history(ctx)


@module.view("history", parent="one", title="history")
def history(ctx: Ctx) -> View:
    row = counter_of(ctx, wanted_number(ctx))
    return gone(ctx) if row is None else changes_page(ctx, row, wanted_number(ctx, 1))


def changes_page(ctx: Ctx, row, wanted: int) -> View:
    rows = list(reversed(changes_of(ctx, row['id'])))
    if not rows:
        return View(text=ctx.t("no_changes"), name="history", argument=str(row['id']) + ":0")
    pages = -(-len(rows) // page_size)
    page = min(wanted, pages - 1)
    buttons = [Button(change['changed_at'].replace("T", " ")[:16] + " - " + signed_text(change['amount']), "entry",
                      change['id']) for change in rows[page * page_size:(page + 1) * page_size]]
    if pages > 1:
        buttons += [Button(ctx.t("previous"), "history", row['id'], max(0, page - 1)),
                    Button(ctx.t("next"), "history", row['id'], min(pages - 1, page + 1))]
    return View(text=bold(row['name']) + "\n" + ctx.t("pick", page=italic(page + 1), pages=italic(pages),
                                                      total=italic(len(rows))),
                buttons=buttons, name="history", argument=str(row['id']) + ":" + str(page))


def entry_view(ctx: Ctx, row, line: str = "") -> View:
    return View(text=above(line, entry_lines(ctx, row['name'], row['amount'], row['changed_at'])), name="entry",
                argument=str(row['id']),
                buttons=[Button(ctx.t("edit_amount"), "amend", row['id']),
                         Button(ctx.t("edit_when"), "move", row['id']), Button(ctx.t("erase"), "erase", row['id'])])


@module.callback("entry")
def open_entry(ctx: Ctx) -> View:
    return entry(ctx)


@module.view("entry", parent="history", title="entry")
def entry(ctx: Ctx) -> View:
    row = entry_of(ctx, wanted_number(ctx))
    return gone_entry(ctx) if row is None else entry_view(ctx, row)


def amended(ctx: Ctx, entry_id: int, column: str, value) -> View:
    if column not in ("amount", "changed_at"):
        raise ValueError("Unknown column: " + column)
    if not ctx.db.execute("UPDATE " + table(ctx, "changes") + " SET " + column + " = ? WHERE id = ? AND user_id = ?;",
                          (value, entry_id, ctx.user.id)).rowcount:
        return gone_entry(ctx)
    ctx.log("Counter entry " + str(entry_id) + " changed")
    row = entry_of(ctx, entry_id)
    rechecked(ctx, row['counter_id'])
    return entry_view(ctx, row, ctx.t("changed_entry"))


@module.callback("amend")
def open_amend(ctx: Ctx) -> View:
    if entry_of(ctx, wanted_number(ctx)) is None:
        return gone_entry(ctx)
    return ctx.form("fix_amount", known={'entry': wanted_number(ctx)})


@module.form("fix_amount", [amount_question], parent="entry", title="edit_amount")
def amount_fixed(ctx: Ctx, answers: Answers) -> View:
    return amended(ctx, answers['entry'], "amount", answers['amount'])


@module.callback("move")
def open_move(ctx: Ctx) -> View:
    if entry_of(ctx, wanted_number(ctx)) is None:
        return gone_entry(ctx)
    return ctx.form("fix_when", known={'entry': wanted_number(ctx)})


@module.form("fix_when", [when_question], parent="entry", title="edit_when")
def moved(ctx: Ctx, answers: Answers) -> View:
    return amended(ctx, answers['entry'], "changed_at", answers['when'])


@module.callback("erase")
def open_erase(ctx: Ctx) -> View:
    row = entry_of(ctx, wanted_number(ctx))
    if row is None:
        return gone_entry(ctx)
    return View(text=ctx.t("sure_entry") + "\n" + entry_lines(ctx, row['name'], row['amount'], row['changed_at']),
                name="entry", argument=str(row['id']),
                buttons=[Button(ctx.t("core:yes_button"), "erase_confirmed", row['id'])])


@module.callback("erase_confirmed")
def confirm_erase(ctx: Ctx) -> View:
    row = entry_of(ctx, wanted_number(ctx))
    if row is None:
        return gone_entry(ctx)
    ctx.db.execute("DELETE FROM " + table(ctx, "changes") + " WHERE id = ? AND user_id = ?;", (row['id'], ctx.user.id))
    ctx.log("Counter entry " + str(row['id']) + " deleted")
    rechecked(ctx, row['counter_id'])
    found = changes_page(ctx, counter_of(ctx, row['counter_id']), 0)
    return replace(found, text=above(ctx.t("deleted_entry"), found.text))


def gone_entry(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone_entry"))


# ----- plain messages -----

def reading_of(ctx: Ctx) -> tuple | None:
    found = readings(ctx.text)
    if not found:
        return None
    by_key = {key_of(row['name']): row for row in counters_of(ctx)}
    return next(((by_key[key], amount) for key, amount in found if key in by_key and amount_problem(amount) is None),
                None)


def is_counted(ctx: Ctx) -> bool:
    return reading_of(ctx) is not None


@module.match(is_counted, priority=priority, is_personal=True)
def count_message(ctx: Ctx) -> View | None:
    found = reading_of(ctx)
    if found is None:
        return None
    row, amount = found
    entry_id, line = counted(ctx, row, amount)
    ctx.log("Counted from a message")
    lines = [ctx.t("added", amount=signed_text(amount))] + state_lines(ctx, row, value_of(ctx, row, datetime.now()))
    return View(text="\n".join(lines + ([line] if line else [])), columns=2,
                buttons=[Button(ctx.t("undo"), "undo", entry_id), Button(ctx.t("open"), "open", row['id'])])


@module.callback("undo")
def undo(ctx: Ctx) -> View:
    row = entry_of(ctx, wanted_number(ctx))
    if row is None:
        return View(text=ctx.t("gone_entry"))
    ctx.db.execute("DELETE FROM " + table(ctx, "changes") + " WHERE id = ? AND user_id = ?;", (row['id'], ctx.user.id))
    if ctx.message is not None:
        ctx.remove_buttons(ctx.message.message_id)
    ctx.log("Counter entry " + str(row['id']) + " undone")
    rechecked(ctx, row['counter_id'])
    counter = counter_of(ctx, row['counter_id'])
    return View(text="\n".join([ctx.t("undone", amount=signed_text(row['amount']))] +
                               state_lines(ctx, counter, value_of(ctx, counter, datetime.now()))))


# ----- the chart -----

def bucket_period(row) -> str:
    return row['period'] if row['period'] in ("weekly", "monthly") else "daily"


def starts_of(period: str, now: datetime, week: int, first: datetime) -> list[datetime]:
    earliest = period_start(period, first - timedelta(days=1), week)
    starts = [period_start(period, now, week)]
    while len(starts) < (chart_days if period == "daily" else chart_periods) and starts[0] > earliest:
        starts.insert(0, period_start(period, starts[0] - timedelta(days=1), week))
    return starts


def label_of(period: str, start: datetime) -> str:
    return start.strftime("%Y-%m") if period == "monthly" else start.date().isoformat()


def value_labels(values: list[float], is_running: bool) -> list[str]:
    if is_running:
        return [number_text(value) if index == 0 or value != values[index - 1] else ""
                for index, value in enumerate(values)]
    return [number_text(value) if value else "" for value in values]


def bar_colors(values: list[float], wanted: float | None) -> list[str]:
    if wanted is None:
        return [colors['count']] * len(values)
    return [colors['reached'] if value >= wanted else colors['count'] if index == len(values) - 1 else colors['missed']
            for index, value in enumerate(values)]


def draw(points: list[tuple[datetime, float]], wanted: float | None, texts: dict, is_running: bool,
         period: str) -> bytes:
    figure = Figure(figsize=(8, 4.5), dpi=120, facecolor=colors['surface'])
    axes = figure.subplots()
    axes.set_facecolor(colors['surface'])
    moments = [moment + timedelta(days=0.0 if is_running else bar_middles[period]) for moment, _ in points]
    values = [value for _, value in points]
    labels = value_labels(values, is_running)
    if is_running:
        axes.plot(moments, values, color=colors['count'], linewidth=2, marker="o", markersize=3)
        axes.grid(color=colors['grid'], linewidth=0.8)
        for moment, value, label in zip(moments, values, labels):
            if label:
                axes.annotate(label, (moment, value), xytext=(0, 5), textcoords="offset points", ha="center",
                              color=colors['ink'], fontsize=8)
    else:
        bars = axes.bar(moments, values, width=bar_widths[period], color=bar_colors(values, wanted))
        axes.bar_label(bars, labels=labels, padding=2, color=colors['ink'], fontsize=8)
        axes.grid(axis="y", color=colors['grid'], linewidth=0.8)
    axes.margins(y=0.12)
    axes.set_axisbelow(True)
    if wanted is not None:
        axes.axhline(wanted, color=colors['goal'], linewidth=1.5, linestyle="--")
        axes.annotate(texts['goal'] + " " + number_text(wanted), (1, wanted), xycoords=("axes fraction", "data"),
                      xytext=(0, 4), textcoords="offset points", ha="right", color=colors['ink'], fontsize=8)
    axes.set_title(texts['title'], color=colors['ink'], loc="left", parse_math=False)
    axes.tick_params(colors=colors['muted'])
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(colors['axis'])
    picked = range(0, len(points), -(-len(points) // tick_count))
    axes.set_xticks([moments[index] for index in picked],
                    labels=[points[index][0].strftime(day_formats[period]) for index in picked])
    figure.tight_layout()
    picture = io.BytesIO()
    figure.savefig(picture, format="png", facecolor=colors['surface'])
    return picture.getvalue()


@module.callback("chart", is_background=True)
def open_chart(ctx: Ctx) -> View:
    return chart(ctx)


@module.view("chart", parent="one", title="chart")
def chart(ctx: Ctx) -> View:
    row = counter_of(ctx, wanted_number(ctx))
    if row is None:
        return gone(ctx)
    week, period, is_running = week_of(ctx), bucket_period(row), row['period'] == "never"
    first = ctx.db.query_one("SELECT MIN(changed_at) AS first FROM " + table(ctx, "changes") + " WHERE counter_id = ? "
                             "AND user_id = ?;", (row['id'], ctx.user.id))['first']
    if first is None:
        return View(text=ctx.t("empty"), argument=str(row['id']))
    starts = starts_of(period, datetime.now(), week, datetime.fromisoformat(first))
    rows = changes_of(ctx, row['id'], starts[0])
    if not rows:
        return View(text=ctx.t("empty"), argument=str(row['id']))
    totals, seen = {start: 0.0 for start in starts}, set()
    for change in rows:
        start = period_start(period, datetime.fromisoformat(change['changed_at']), week)
        totals[start] = totals.get(start, 0.0) + change['amount']
        seen.add(start)
    base = ctx.db.query_one("SELECT SUM(amount) AS total FROM " + table(ctx, "changes") + " WHERE counter_id = ? "
                            "AND user_id = ? AND changed_at < ?;",
                            (row['id'], ctx.user.id, moment_text(starts[0])))['total'] or 0.0
    values = list(accumulate(totals.values(), initial=base))[1:] if is_running else list(totals.values())
    shown = dict(zip(totals, values))
    photo = draw(list(shown.items()), row['goal'],
                 {'title': plain(ctx.t("chart_texts." + row['period'], name=bare_name(row['name']))),
                  'goal': plain(ctx.t("chart_texts.goal"))}, is_running, period)
    goal_line = [labelled(ctx.t("labels.goal"), number_text(row['goal']))] if row['goal'] is not None else []
    lines = [escape(label_of(period, start) + " - " + number_text(shown[start])) for start in sorted(seen)]
    ctx.log("Counter chart shown")
    return View(text="\n".join(goal_line + lines), photo=photo, argument=str(row['id']))


# ----- settings -----

@module.settings()
def settings(ctx: Ctx) -> View:
    return View(text=ctx.t("settings_text") + "\n\n" + labelled(ctx.t("labels.week"), ctx.t("week." + week_name(ctx))),
                buttons=[Button(ctx.t("set_week"), "set_week")])


@module.callback("set_week")
def open_week(ctx: Ctx) -> View:
    return ctx.form("week")


@module.form("week", [Question("week", "choice", choices=tuple(week_starts), labels="week")], parent="settings",
             title="set_week")
def week_given(ctx: Ctx, answers: Answers) -> View:
    ctx.state.set(week_key, answers['week'])
    ctx.log("Week start set")
    return settings(ctx)


# ----- the assistant -----

def named(ctx: Ctx, name: str) -> list:
    return [row for row in counters_of(ctx) if key_of(row['name']) == key_of(name)]


@module.context()
def summary(ctx: Ctx) -> str:
    now = datetime.now()
    return "\n".join(state_lines(ctx, row, value_of(ctx, row, now))[0] for row in counters_of(ctx))


@module.action("add", parameters={'counter': str, 'amount': float}, is_confirmed=True)
def act_add(ctx: Ctx, counter: str, amount: float) -> Outcome:
    found = named(ctx, counter)
    if not found:
        return Outcome.refused(ctx.t("missing"))
    row = found[0]
    problem = amount_problem(amount)
    if problem is not None:
        return Outcome.refused(problem_text(ctx, problem))
    after = value_of(ctx, row, datetime.now()) + round(amount, 2)
    return Outcome.ask(ctx.t("add_sure") + "\n" + "\n".join([labelled(ctx.t("labels.counter"), row['name']),
                                                            labelled(ctx.t("labels.amount"), signed_text(amount)),
                                                            labelled(ctx.t("labels.after"), state_text(row, after))]),
                       partial(added_by_assistant, ctx, row['id'], amount))


def added_by_assistant(ctx: Ctx, counter: int, amount: float) -> str:
    row = counter_of(ctx, counter)
    if row is None:
        return ctx.t("gone")
    _, line = counted(ctx, row, amount)
    ctx.log("Counted by the assistant")
    lines = [ctx.t("added", amount=signed_text(amount))] + state_lines(ctx, row, value_of(ctx, row, datetime.now()))
    return "\n".join(lines + ([line] if line else []))


@module.action("list")
def act_list(ctx: Ctx) -> Outcome:
    now = datetime.now()
    return Outcome.done([{'name': row['name'], 'value': value_of(ctx, row, now), 'step': row['step'],
                          'goal': row['goal'], 'starts_from_zero': row['period']} for row in counters_of(ctx)])


@module.action("history", parameters={'counter': str})
def act_history(ctx: Ctx, counter: str) -> Outcome:
    found = named(ctx, counter)
    if not found:
        return Outcome.refused(ctx.t("missing"))
    row = found[0]
    return Outcome.done({'name': row['name'], 'value': value_of(ctx, row, datetime.now()),
                         'starts_from_zero': row['period'],
                         'changes': [{'when': change['changed_at'], 'amount': change['amount']}
                                     for change in changes_of(ctx, row['id'])[-history_limit:]]})
