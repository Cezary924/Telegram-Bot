from datetime import datetime, timedelta

from core.api import (Answers, Button, Ctx, JobCtx, Module, Outcome, Problem, Question, View, escape, labelled, italic,
                      read_moment)

module = Module(name="reminder", place=30, is_guarded=True, notifications="name",
                icons={'name': "🔔", 'set': "➕", 'previous': "⬅️", 'next': "➡️"},
                endings={'how': "😊", 'done': "✅", 'changed': "✅", 'deleted': "✅", 'gone': "💔"})

mark = "🔔 "
interval = 60
delayed_after = 2 * interval
date_format = "%Y-%m-%d %H:%M"
example_format = "%d.%m.%Y %H:%M"
content_limit = 200
page_size = 8
waiting_mark = "🔔 "
done_mark = "🔕 "
listed_limit = 30
upcoming_limit = 3


def parse_date(text: str) -> datetime | None:
    return read_moment(text, is_future=True)


def table(ctx) -> str:
    return ctx.db.table("reminders")


def reminders_of(ctx: Ctx) -> list:
    return ctx.db.query_all("SELECT id, date, content, is_notified FROM " + table(ctx) +
                            " WHERE user_id = ? ORDER BY date DESC;", (ctx.user.id,))


def reminder_of(ctx: Ctx, reminder_id: int):
    return ctx.db.query_one("SELECT id, date, content, is_notified FROM " + table(ctx) +
                            " WHERE id = ? AND user_id = ?;", (reminder_id, ctx.user.id))


def wanted_id(ctx: Ctx) -> int:
    return int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0


def details(ctx: Ctx, content: str, date: str) -> str:
    return labelled(ctx.t("labels.content"), content) + "\n" + labelled(ctx.t("labels.date"), date)


def wrong_content(ctx: Ctx, text: str) -> str:
    return "" if 0 < len(text.strip()) <= content_limit else ctx.t("core:form.length", low="1", high=str(content_limit))


def is_past(moment: datetime) -> bool:
    return moment < datetime.now().replace(second=0, microsecond=0)


def checked_date(ctx: Ctx, text: str) -> tuple[str, str]:
    date = parse_future(text, {})
    if isinstance(date, Problem):
        return "", ctx.t(date.key, example=example_date())
    return (date, "") if date else ("", ctx.t("wrong_date", example=example_date()))


def insert(ctx: Ctx, content: str, date: str) -> None:
    ctx.db.execute("INSERT INTO " + table(ctx) + " (user_id, date, content) VALUES (?, ?, ?);",
                   (ctx.user.id, date, content))
    ctx.log("Reminder set for " + date)


def change(ctx: Ctx, row, content: str, date: str) -> None:
    ctx.db.execute("UPDATE " + table(ctx) + " SET content = ?, date = ?, is_notified = ? WHERE id = ? AND user_id = ?;",
                   (content, date, row['is_notified'] if date == row['date'] else 0, row['id'], ctx.user.id))
    ctx.log("Reminder " + str(row['id']) + " changed")


def remove(ctx: Ctx, reminder_id: int) -> None:
    ctx.db.execute("DELETE FROM " + table(ctx) + " WHERE id = ? AND user_id = ?;", (reminder_id, ctx.user.id))
    ctx.log("Reminder " + str(reminder_id) + " deleted")


@module.command("reminder")
def command_reminder(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    rows = reminders_of(ctx)
    buttons = [Button(ctx.t("set"), "set")]
    if rows:
        buttons.append(Button(ctx.t("manage"), "manage"))
    return View(text=ctx.t("how"), buttons=buttons)


# ----- setting -----

def example_date() -> str:
    return (datetime.now() + timedelta(days=1)).strftime(example_format)


def parse_future(text: str, _values: dict) -> str | Problem | None:
    moment = parse_date(text)
    if moment is None:
        return None
    return Problem("past_date") if is_past(moment) else moment.strftime(date_format)


@module.callback("set")
def open_content(ctx: Ctx) -> View:
    reminder_id = wanted_id(ctx)
    if not reminder_id:
        return ctx.form("new", known={'example': example_date()})
    if reminder_of(ctx, reminder_id) is None:
        return gone(ctx)
    return ctx.form("rewrite", known={'id': reminder_id})


@module.callback("date")
def open_date(ctx: Ctx) -> View:
    if reminder_of(ctx, wanted_id(ctx)) is None:
        return gone(ctx)
    return ctx.form("move", known={'id': wanted_id(ctx), 'example': example_date()})


content_question = Question("content", "text", high=content_limit)
date_question = Question("date", parse=parse_future, problem="wrong_date")


@module.form("new", [content_question, date_question], parent="menu", title="set")
def save_new(ctx: Ctx, answers: Answers) -> View:
    insert(ctx, answers['content'], answers['date'])
    ctx.close_screen()
    return View(text=ctx.t("done") + "\n" + details(ctx, answers['content'], answers['date']))


@module.form("rewrite", [content_question], parent="one", title="labels.content")
def save_content(ctx: Ctx, answers: Answers) -> View:
    row = reminder_of(ctx, answers['id'])
    if row is None:
        return gone(ctx)
    change(ctx, row, answers['content'], row['date'])
    ctx.close_screen()
    return View(text=ctx.t("changed") + "\n" + details(ctx, answers['content'], row['date']))


@module.form("move", [date_question], parent="one", title="labels.date")
def save_date(ctx: Ctx, answers: Answers) -> View:
    row = reminder_of(ctx, answers['id'])
    if row is None:
        return gone(ctx)
    change(ctx, row, row['content'], answers['date'])
    ctx.close_screen()
    return View(text=ctx.t("changed") + "\n" + details(ctx, row['content'], answers['date']))


# ----- managing -----

@module.callback("manage")
def open_manage(ctx: Ctx) -> View:
    return manage(ctx)


@module.view("manage", parent="menu", title="manage")
def manage(ctx: Ctx) -> View:
    rows = reminders_of(ctx)
    if not rows:
        return View(text=ctx.t("empty"))
    pages = max(1, -(-len(rows) // page_size))
    page = min(wanted_page(ctx), pages - 1)
    buttons = [Button(label(row), "one", row['id'])
               for row in rows[page * page_size:(page + 1) * page_size]]
    if pages > 1:
        buttons.append(Button(ctx.t("previous"), "manage", max(0, page - 1)))
        buttons.append(Button(ctx.t("next"), "manage", min(pages - 1, page + 1)))
    return View(text=ctx.t("pick.text") + "\n"
                + ctx.t("pick.page", page=italic(page + 1), pages=italic(pages), total=italic(len(rows))),
                buttons=buttons, argument=str(page))


def wanted_page(ctx: Ctx) -> int:
    return int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0


def label(row) -> str:
    return (done_mark if row['is_notified'] else waiting_mark) + escape(row['content'])


@module.callback("one")
def open_one(ctx: Ctx) -> View:
    return one(ctx)


@module.view("one", parent="manage")
def one(ctx: Ctx) -> View:
    reminder_id = wanted_id(ctx)
    row = reminder_of(ctx, reminder_id)
    if row is None:
        return gone(ctx)
    return View(text=label(row) + "\n" + details(ctx, row['content'], row['date']),
                buttons=[Button(ctx.t("edit_content"), "set", reminder_id),
                         Button(ctx.t("edit_date"), "date", reminder_id),
                         Button(ctx.t("delete"), "delete", reminder_id)],
                argument=str(reminder_id))


@module.callback("delete")
def open_delete(ctx: Ctx) -> View:
    return removal(ctx)


@module.view("delete", parent="one", title="delete")
def removal(ctx: Ctx) -> View:
    reminder_id = wanted_id(ctx)
    row = reminder_of(ctx, reminder_id)
    if row is None:
        return gone(ctx)
    return View(text=ctx.t("sure") + "\n" + details(ctx, row['content'], row['date']),
                buttons=[Button(ctx.t("core:yes_button"), "delete_confirmed", reminder_id)],
                argument=str(reminder_id))


@module.callback("delete_confirmed")
def confirm_delete(ctx: Ctx) -> View:
    reminder_id = wanted_id(ctx)
    if reminder_of(ctx, reminder_id) is None:
        return gone(ctx)
    remove(ctx, reminder_id)
    ctx.close_screen()
    return View(text=ctx.t("deleted"))


def gone(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone"))


# ----- assistant -----

@module.action("add", parameters={'content': str, 'date': str}, is_confirmed=True)
def act_add(ctx: Ctx, content: str, date: str) -> Outcome:
    content = content.strip()
    date, problem = checked_date(ctx, date)
    problem = wrong_content(ctx, content) or problem
    if problem:
        return Outcome.refused(problem)
    return Outcome.ask(ctx.t("add_sure") + "\n" + details(ctx, content, date), lambda: added(ctx, content, date))


def added(ctx: Ctx, content: str, date: str) -> str:
    insert(ctx, content, date)
    return ctx.t("done") + "\n" + details(ctx, content, date)


@module.action("list")
def act_list(ctx: Ctx) -> Outcome:
    rows = ctx.db.query_all("SELECT id, date, content, is_notified FROM " + table(ctx) + " WHERE user_id = ? "
                            "ORDER BY is_notified, CASE WHEN is_notified = 0 THEN date END, date DESC LIMIT ?;",
                            (ctx.user.id, listed_limit))
    return Outcome.done([{'reminder_id': row['id'], 'date': row['date'], 'content': row['content'],
                          'is_sent': bool(row['is_notified'])} for row in rows])


@module.action("edit", parameters={'reminder_id': int, 'content': str, 'date': str}, optional=["content", "date"],
               is_confirmed=True)
def act_edit(ctx: Ctx, reminder_id: int, content: str | None, date: str | None) -> Outcome:
    row = reminder_of(ctx, reminder_id)
    if row is None:
        return Outcome.refused(ctx.t("missing"))
    if content is None and date is None:
        return Outcome.refused(ctx.t("unchanged"))
    text = row['content'] if content is None else content.strip()
    when, problem = (row['date'], "") if date is None else checked_date(ctx, date)
    problem = wrong_content(ctx, text) or problem
    if problem:
        return Outcome.refused(problem)
    return Outcome.ask(ctx.t("edit_sure") + "\n" + details(ctx, text, when), lambda: edited(ctx, row, text, when))


def edited(ctx: Ctx, row, content: str, date: str) -> str:
    change(ctx, row, content, date)
    return ctx.t("changed") + "\n" + details(ctx, content, date)


@module.action("delete", parameters={'reminder_id': int}, is_confirmed=True)
def act_delete(ctx: Ctx, reminder_id: int) -> Outcome:
    row = reminder_of(ctx, reminder_id)
    if row is None:
        return Outcome.refused(ctx.t("missing"))
    return Outcome.ask(ctx.t("sure") + "\n" + details(ctx, row['content'], row['date']),
                       lambda: deleted(ctx, reminder_id))


def deleted(ctx: Ctx, reminder_id: int) -> str:
    remove(ctx, reminder_id)
    return ctx.t("deleted")


@module.context()
def summary(ctx: Ctx) -> str:
    rows = ctx.db.query_all("SELECT date, content FROM " + table(ctx) + " WHERE user_id = ? AND is_notified = 0 "
                            "ORDER BY date LIMIT ?;", (ctx.user.id, upcoming_limit))
    if not rows:
        return ""
    return ctx.t("upcoming") + ":\n" + "\n".join(escape(row['date'] + " - " + row['content']) for row in rows)


# ----- notifying -----

@module.job(interval=interval, name="check", is_aligned=True)
def check_reminders(ctx: JobCtx) -> None:
    now = datetime.now()
    for row in due_reminders(ctx, now):
        moment = parse_date(row['date'])
        if moment is None:
            continue
        key = "due" if now - moment <= timedelta(seconds=delayed_after) else "delayed"
        notify(ctx, row, key)


def due_reminders(ctx: JobCtx, now: datetime) -> list:
    return ctx.db.query_all(
        "SELECT id, user_id, date, content FROM " + ctx.db.table("reminders") +
        " WHERE is_notified = 0 AND date <= ? ORDER BY date;", (now.strftime(date_format),))


def notify(ctx: JobCtx, row, key: str) -> None:
    language = ctx.language_of(row['user_id'])
    text = (mark + "<b>" + ctx.t("title", language) + ":</b>\n\n" + ctx.t(key, language) + "\n"
            + labelled(ctx.t("labels.content", language), row['content']) + "\n"
            + labelled(ctx.t("labels.date", language), row['date']))
    if not ctx.send(row['user_id'], View(text=text)):
        return
    ctx.db.execute("UPDATE " + ctx.db.table("reminders") + " SET is_notified = 1 WHERE id = ?;",
                   (row['id'],))
    ctx.log("Reminder " + str(row['id']) + " sent")
