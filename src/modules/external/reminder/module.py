from datetime import datetime, timedelta

from core.api import Button, Ctx, JobCtx, Module, Role, View

module = Module(name="reminder")

mark = "🔔 "
interval = 60
delayed_after = 2 * interval
date_format = "%Y-%m-%d %H:%M"
content_limit = 200
content_key = "content"
page_size = 8
waiting_mark = "🔔 "
done_mark = "🔕 "


def parse_date(text: str) -> datetime | None:
    try:
        return datetime.strptime(text.strip(), date_format)
    except ValueError:
        return None


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
    return ctx.t("content") + ": _" + content + "_\n" + ctx.t("date") + ": _" + date + "_"


@module.command("reminder", role=Role.USER)
def command_reminder(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    rows = reminders_of(ctx)
    buttons = [Button(ctx.t("set"), "set")]
    if rows:
        buttons.append(Button(ctx.t("manage"), "manage"))
    return View(text=ctx.t("menu", count=str(len(rows))),
                buttons=buttons)


# ----- setting -----

@module.callback("set", role=Role.USER)
def open_content(ctx: Ctx) -> View:
    ctx.state.delete(content_key)
    return content_screen(ctx)


@module.view("content", parent="menu", title="content")
def content_screen(ctx: Ctx) -> View:
    reminder_id = wanted_id(ctx)
    return View(text=ctx.t("ask_content"),
                argument=str(reminder_id) if reminder_id else None)


@module.state("content", role=Role.USER)
def take_content(ctx: Ctx) -> View:
    text = ctx.text.strip()
    if not text or len(text) > content_limit:
        return ctx.retry(ctx.t("wrong_content", limit=str(content_limit)))
    reminder_id = wanted_id(ctx)
    if reminder_id:
        return save_content(ctx, reminder_id, text)
    ctx.state.set(content_key, text)
    return date_screen(ctx)


def save_content(ctx: Ctx, reminder_id: int, text: str) -> View:
    row = reminder_of(ctx, reminder_id)
    if row is None:
        return gone(ctx)
    ctx.db.execute("UPDATE " + table(ctx) + " SET content = ? WHERE id = ? AND user_id = ?;",
                   (text, reminder_id, ctx.user.id))
    ctx.close_screen()
    ctx.log("Reminder " + str(reminder_id) + " content changed")
    return View(text=ctx.t("changed") + "\n" + details(ctx, text, row['date']))


@module.callback("date", role=Role.USER)
def open_date(ctx: Ctx) -> View:
    return date_screen(ctx)


@module.view("date", parent="menu", title="date")
def date_screen(ctx: Ctx) -> View:
    reminder_id = wanted_id(ctx)
    return View(text=ctx.t("ask_date", example=example_date()),
                argument=str(reminder_id) if reminder_id else None)


def example_date() -> str:
    return (datetime.now() + timedelta(days=1)).strftime(date_format)


@module.state("date", role=Role.USER)
def take_date(ctx: Ctx) -> View:
    moment = parse_date(ctx.text)
    if moment is None:
        return ctx.retry(ctx.t("wrong_date", example=example_date()))
    if moment < datetime.now().replace(second=0, microsecond=0):
        return ctx.retry(ctx.t("past_date"))
    date = moment.strftime(date_format)
    reminder_id = wanted_id(ctx)
    if reminder_id:
        return save_date(ctx, reminder_id, date)
    return save_new(ctx, date)


def save_date(ctx: Ctx, reminder_id: int, date: str) -> View:
    row = reminder_of(ctx, reminder_id)
    if row is None:
        return gone(ctx)
    ctx.db.execute("UPDATE " + table(ctx) +
                   " SET date = ?, is_notified = 0 WHERE id = ? AND user_id = ?;",
                   (date, reminder_id, ctx.user.id))
    ctx.close_screen()
    ctx.log("Reminder " + str(reminder_id) + " date changed")
    return View(text=ctx.t("changed") + "\n" + details(ctx, row['content'], date))


def save_new(ctx: Ctx, date: str) -> View:
    content = ctx.state.get(content_key) or ""
    if not content:
        return gone(ctx)
    ctx.db.execute("INSERT INTO " + table(ctx) + " (user_id, date, content) VALUES (?, ?, ?);",
                   (ctx.user.id, date, content))
    ctx.state.delete(content_key)
    ctx.close_screen()
    ctx.log("Reminder set for " + date)
    return View(text=ctx.t("done") + "\n" + details(ctx, content, date))


# ----- managing -----

@module.callback("manage", role=Role.USER)
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
    return View(text=ctx.t("pick", page=str(page + 1), pages=str(pages), total=str(len(rows))),
                buttons=buttons, argument=str(page))


def wanted_page(ctx: Ctx) -> int:
    return int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0


def label(row) -> str:
    return (done_mark if row['is_notified'] else waiting_mark) + row['content']


@module.callback("one", role=Role.USER)
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


@module.callback("delete", role=Role.USER)
def open_delete(ctx: Ctx) -> View:
    return removal(ctx)


@module.view("delete", parent="menu", title="delete")
def removal(ctx: Ctx) -> View:
    reminder_id = wanted_id(ctx)
    row = reminder_of(ctx, reminder_id)
    if row is None:
        return gone(ctx)
    return View(text=ctx.t("sure") + "\n" + details(ctx, row['content'], row['date']),
                buttons=[Button(ctx.t("core:yes_button"), "delete_confirmed", reminder_id)],
                argument=str(reminder_id))


@module.callback("delete_confirmed", role=Role.USER)
def confirm_delete(ctx: Ctx) -> View:
    reminder_id = wanted_id(ctx)
    if reminder_of(ctx, reminder_id) is None:
        return gone(ctx)
    ctx.db.execute("DELETE FROM " + table(ctx) + " WHERE id = ? AND user_id = ?;",
                   (reminder_id, ctx.user.id))
    ctx.close_screen()
    ctx.log("Reminder " + str(reminder_id) + " deleted")
    return View(text=ctx.t("deleted"))


def gone(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone"))


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
    text = (mark + "*" + ctx.t("title", language) + ":*\n\n" + ctx.t(key, language) + "\n"
            + ctx.t("content", language) + ": _" + row['content'] + "_\n"
            + ctx.t("date", language) + ": _" + row['date'] + "_")
    ctx.send(row['user_id'], View(text=text))
    ctx.db.execute("UPDATE " + ctx.db.table("reminders") + " SET is_notified = 1 WHERE id = ?;",
                   (row['id'],))
    ctx.log("Reminder " + str(row['id']) + " sent")
