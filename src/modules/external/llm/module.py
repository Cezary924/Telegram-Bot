import json
import os
import re
import sqlite3
import threading
import time
from collections.abc import Iterator
from datetime import datetime, timedelta

import requests

from core.api import Button, Ctx, JobCtx, Module, View, escape, italic, labelled

module = Module(name="llm", is_guarded=True, config_keys=["llm_url", "llm_model"], tokens=["llm_key"],
                icons={'name': "🤖", 'title': "🤖", 'new': "🆕", 'continue': "▶️", 'settings_button': "⚙️",
                       'thinking_mode': "💭", 'thinking_on': "💭", 'thinking_off': "⚡", 'waiting': "🔍", 'writing': "✍️", 'thinking': "💭",
                       'reasoning': "💭", 'history': "📜", 'resume': "▶️", 'export': "📄", 'delete': "🗑️",
                       'keeping': "⏳", 'wipe': "🗑️", 'conversation': "💬", 'previous': "⬅️", 'next': "➡️"},
                endings={'how': "💬", 'fresh_done': "✅", 'failed': "💔", 'empty': "🤷", 'not_configured': "🔧",
                         'busy': "⏳", 'resumed': "✅", 'deleted': "✅", 'wiped': "✅", 'gone': "💔"})

priority = -100
continue_within = 15 * 60
ask_within = 60 * 60
history_messages = 30
history_characters = 24000
edit_every = 3.0
tick = 1.5
message_limit = 4096
part_size = 3500
live_tail = 3500
thinking_tail = 300
timeouts = (10, 900)
conversation_key = "conversation"
last_key = "last_at"
thinking_key = "thinking"
pending_prefix = "pending."
page_size = 8
title_size = 40
opening_size = 300
keep_choices = [0, 7, 30, 90]
default_keep = 90
forget_every = 60 * 60
date_format = "%Y-%m-%d %H:%M"
answering: set[int] = set()
answering_lock = threading.Lock()


def table(ctx: Ctx | JobCtx) -> str:
    return ctx.db.table("messages")


def settings_table(ctx: Ctx | JobCtx) -> str:
    return ctx.db.table("settings")


def is_chat(text: str) -> bool:
    return bool(text.strip()) and not text.startswith("/")


def seconds_since(ctx: Ctx) -> float | None:
    last = ctx.state.get(last_key)
    if not last:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(last)).total_seconds()
    except ValueError:
        return None


def current(ctx: Ctx) -> int:
    value = ctx.state.get(conversation_key) or "0"
    return int(value) if value.isdigit() else 0


def fresh(ctx: Ctx) -> int:
    row = ctx.db.query_one("SELECT MAX(conversation) AS top FROM " + table(ctx) + " WHERE user_id = ?;",
                           (ctx.user.id,))
    number = max(current(ctx), (row['top'] if row is not None else None) or 0) + 1
    ctx.state.set(conversation_key, str(number))
    ctx.state.set(last_key, datetime.now().isoformat(timespec="seconds"))
    return number


def remember(ctx: Ctx, conversation: int, role: str, content: str) -> None:
    ctx.db.execute("INSERT INTO " + table(ctx) + " (user_id, conversation, role, content, created_at) "
                   "VALUES (?, ?, ?, ?, ?);",
                   (ctx.user.id, conversation, role, content, datetime.now().isoformat(timespec="seconds")))


def history(ctx: Ctx, conversation: int) -> list[dict]:
    rows = ctx.db.query_all("SELECT role, content FROM " + table(ctx) + " WHERE user_id = ? AND conversation = ? "
                            "ORDER BY id DESC LIMIT ?;", (ctx.user.id, conversation, history_messages))
    kept, total = [], 0
    for row in rows:
        total += len(row['content'])
        if kept and total > history_characters:
            break
        kept.append({'role': row['role'], 'content': row['content']})
    return list(reversed(kept))


def is_thinking(ctx: Ctx) -> bool:
    return ctx.state.get(thinking_key) == "1"


def stream(ctx: Ctx, messages: list[dict], thinking: bool) -> Iterator[tuple[str, str]]:
    headers = {'Authorization': "Bearer " + ctx.token("llm_key")} if ctx.has_token("llm_key") else {}
    payload = {'model': ctx.setting("llm_model") or "", 'messages': messages, 'stream': True,
               'chat_template_kwargs': {'enable_thinking': thinking}}
    if not thinking:
        payload['reasoning_effort'] = "none"
    url = (ctx.setting("llm_url") or "").rstrip("/") + "/chat/completions"
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=timeouts) as response:
        response.raise_for_status()
        for raw in response.iter_lines():
            line = raw.decode("utf-8", "replace")
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            event = json.loads(data)
            delta = ((event.get('choices') or [{}])[0]).get('delta') or {}
            if delta.get('tool_calls') or event.get('type') == "mcp_tool_result":
                yield "tool", ""
            thought = delta.get('reasoning_content') or delta.get('reasoning') or ""
            if thought:
                yield "thinking", thought
            if delta.get('content'):
                yield "answer", delta['content']


def inline(text: str) -> str:
    lines = []
    for line in escape(text).split("\n"):
        heading = re.match(r"^#{1,6}\s+(.*)$", line)
        line = "<b>" + heading.group(1) + "</b>" if heading else re.sub(r"^(\s*)[*-]\s+", r"\1• ", line)
        lines.append(line)
    html = "\n".join(lines)
    html = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", html)
    return re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", html)


def to_html(text: str) -> str:
    pieces = re.split(r"```[^\n]*\n?(.*?)```", text, flags=re.DOTALL)
    return "".join("<pre>" + escape(piece.strip("\n")) + "</pre>" if number % 2 else inline(piece)
                   for number, piece in enumerate(pieces))


def parts_of(text: str) -> list[str]:
    parts, part = [], ""
    for paragraph in text.split("\n\n"):
        while len(paragraph) > part_size:
            if part:
                parts.append(part)
                part = ""
            parts.append(paragraph[:part_size])
            paragraph = paragraph[part_size:]
        if part and len(part) + len(paragraph) + 2 > part_size:
            parts.append(part)
            part = ""
        part = part + "\n\n" + paragraph if part else paragraph
    if part:
        parts.append(part)
    return parts


def tail(text: str, size: int) -> str:
    return text if len(text) <= size else "…" + text[-size:]


def live_text(ctx: Ctx, thinking: str, answer: str, frame: int) -> str:
    dots = "." * (frame % 3 + 1)
    if answer:
        return ctx.t("writing") + dots + "\n\n" + escape(tail(answer, live_tail))
    if thinking:
        return ctx.t("thinking") + dots + "\n\n" + italic(tail(thinking.strip(), thinking_tail))
    return ctx.t("waiting") + dots


def folded(ctx: Ctx, thinking: str, room: int) -> str:
    if not thinking.strip() or room < 200:
        return ""
    title = ctx.t("reasoning")
    return "<blockquote expandable>" + escape(title + "\n" + tail(thinking.strip(), room - len(title) - 60)) + \
        "</blockquote>\n"


def delivered(ctx: Ctx, thinking: str, answer: str) -> list[str]:
    parts = [to_html(part) for part in parts_of(answer.strip())]
    return [folded(ctx, thinking, message_limit - len(parts[0]) - 100) + parts[0]] + parts[1:]


def talk(ctx: Ctx, conversation: int) -> None:
    live = ctx.reply_live(live_text(ctx, "", "", 0), is_silent=True)
    messages, thinks = history(ctx, conversation), is_thinking(ctx)
    rounds, failures = [{'thinking': "", 'answer': ""}], []

    def read() -> None:
        try:
            for kind, piece in stream(ctx, messages, thinks):
                latest = rounds[-1]
                if kind != "tool":
                    latest[kind] += piece
                elif latest['answer'].strip():
                    rounds.append({'thinking': "", 'answer': ""})
                elif latest['thinking'].strip() and not latest['thinking'].endswith("\n\n"):
                    latest['thinking'] = latest['thinking'].rstrip() + "\n\n"
        except (requests.RequestException, ValueError) as error:
            failures.append(error)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    shown, frame, edited = 0, 0, time.monotonic()
    while True:
        reader.join(tick)
        if not reader.is_alive():
            break
        frame += 1
        if shown < len(rounds) - 1:
            finish(ctx, live, delivered(ctx, rounds[shown]['thinking'], rounds[shown]['answer']))
            shown += 1
            live, edited = ctx.reply_live(live_text(ctx, "", "", frame), is_silent=True), time.monotonic()
            continue
        showing = rounds[shown]
        if live is not None and (not showing['answer'] or time.monotonic() - edited >= edit_every):
            ctx.edit(live, live_text(ctx, showing['thinking'], showing['answer'], frame))
            edited = time.monotonic()
    if failures:
        ctx.error("The language model did not answer - " + type(failures[0]).__name__, str(failures[0]))
        finish(ctx, live, [ctx.t("failed")])
        return
    answers = [each['answer'].strip() for each in rounds if each['answer'].strip()]
    if not answers:
        finish(ctx, live, [ctx.t("empty")])
        return
    remember(ctx, conversation, "assistant", "\n\n".join(answers))
    for index, left in enumerate(rounds[shown:]):
        target = live if index == 0 else None
        if left['answer'].strip():
            finish(ctx, target, delivered(ctx, left['thinking'], left['answer']))
        elif target is not None:
            finish(ctx, target, [ctx.t("empty")])
    ctx.log("Answered in conversation " + str(conversation))


def finish(ctx: Ctx, live: int | None, parts: list[str]) -> None:
    if live is not None and not ctx.remove(live) and ctx.edit(live, parts[0]):
        parts = parts[1:]
    for part in parts:
        ctx.reply_live(part)


def answer_in(ctx: Ctx, conversation: int, text: str) -> View | None:
    with answering_lock:
        if ctx.user.id in answering:
            return View(text=ctx.t("busy"))
        answering.add(ctx.user.id)
    try:
        remember(ctx, conversation, "user", text)
        ctx.state.set(last_key, datetime.now().isoformat(timespec="seconds"))
        talk(ctx, conversation)
    finally:
        with answering_lock:
            answering.discard(ctx.user.id)
    return None


@module.command("llm")
def command_llm(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(text=ctx.t("how"), buttons=[Button(ctx.t("new"), "fresh"),
                                            Button(ctx.t("history"), "history"),
                                            Button.settings(ctx.t("settings_button"), module.name)])


@module.callback("fresh")
def start_fresh(ctx: Ctx) -> View:
    fresh(ctx)
    ctx.close_screen()
    ctx.log("Conversation started anew")
    return View(text=ctx.t("fresh_done"))


@module.match(is_chat, priority=priority, is_background=True)
def take_message(ctx: Ctx) -> View | None:
    if not ctx.setting("llm_url"):
        ctx.error("There is no llm_url in config.yaml")
        return View(text=ctx.t("not_configured"))
    text = ctx.text.strip()
    since = seconds_since(ctx)
    if since is None or since > ask_within:
        return answer_in(ctx, fresh(ctx), text)
    if since < continue_within:
        return answer_in(ctx, current(ctx), text)
    asked = str(ctx.message.message_id) if ctx.message is not None else "0"
    ctx.state.set(pending_prefix + asked, text)
    return choice(ctx, asked, int(since // 60))


@module.view("choice")
def choice(ctx: Ctx, asked: str = "", minutes: int = 0) -> View:
    asked = asked or (ctx.arguments[-1] if ctx.arguments else "")
    return View(text=ctx.t("ask", minutes=minutes),
                buttons=[Button(ctx.t("continue"), "pick", "continue", asked),
                         Button(ctx.t("new"), "pick", "new", asked)],
                argument=asked, columns=2)


@module.callback("pick", is_background=True)
def pick(ctx: Ctx) -> View | None:
    kind, asked = (ctx.arguments + ("", ""))[:2]
    text = ctx.state.get(pending_prefix + asked)
    if kind not in ("continue", "new") or not text:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.state.delete(pending_prefix + asked)
    ctx.close_screen()
    return answer_in(ctx, current(ctx) if kind == "continue" else fresh(ctx), text)


# ----- history -----

def conversations(ctx: Ctx, number: int | None = None) -> list[sqlite3.Row]:
    only = " AND m.conversation = ?" if number is not None else ""
    return ctx.db.query_all(
        "SELECT m.conversation, MIN(m.created_at) AS started, MAX(m.created_at) AS last, COUNT(*) AS total, "
        "(SELECT f.content FROM " + table(ctx) + " f WHERE f.user_id = m.user_id AND f.conversation = m.conversation "
        "AND f.role = 'user' ORDER BY f.id LIMIT 1) AS opening FROM " + table(ctx) + " m WHERE m.user_id = ?" + only +
        " GROUP BY m.conversation ORDER BY MAX(m.id) DESC;", (ctx.user.id,) + ((number,) if number is not None else ()))


def conversation_of(ctx: Ctx, number: int) -> sqlite3.Row | None:
    rows = conversations(ctx, number)
    return rows[0] if rows else None


def wanted_number(ctx: Ctx) -> int:
    return int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0


def when(moment: str) -> str:
    try:
        return datetime.fromisoformat(moment).strftime(date_format)
    except (TypeError, ValueError):
        return moment or ""


def shortened(text: str, size: int) -> str:
    line = " ".join((text or "").split())
    return line if len(line) <= size else line[:size - 1].rstrip() + "…"


def label(row: sqlite3.Row) -> str:
    return when(row['started']) + " · " + escape(shortened(row['opening'], title_size))


def details(ctx: Ctx, row: sqlite3.Row) -> str:
    return "\n".join([labelled(ctx.t("labels.started"), when(row['started'])),
                      labelled(ctx.t("labels.last"), when(row['last'])),
                      labelled(ctx.t("labels.messages"), row['total']),
                      labelled(ctx.t("labels.opening"), shortened(row['opening'], opening_size))])


def gone(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone"))


def forget(ctx: Ctx, number: int | None = None) -> int:
    only = " AND conversation = ?" if number is not None else ""
    removed = ctx.db.execute("DELETE FROM " + table(ctx) + " WHERE user_id = ?" + only + ";",
                             (ctx.user.id,) + ((number,) if number is not None else ())).rowcount
    if number is None or number == current(ctx):
        ctx.state.delete(last_key)
    return removed


@module.callback("history")
def open_history(ctx: Ctx) -> View:
    return history_screen(ctx)


@module.view("history", parent="menu", title="history")
def history_screen(ctx: Ctx) -> View:
    rows = conversations(ctx)
    if not rows:
        return View(text=ctx.t("history_empty"))
    pages = max(1, -(-len(rows) // page_size))
    page = min(wanted_number(ctx), pages - 1)
    buttons = [Button(label(row), "one", row['conversation'])
               for row in rows[page * page_size:(page + 1) * page_size]]
    if pages > 1:
        buttons.append(Button(ctx.t("previous"), "history", max(0, page - 1)))
        buttons.append(Button(ctx.t("next"), "history", min(pages - 1, page + 1)))
    return View(text=ctx.t("pick.text") + "\n"
                + ctx.t("pick.page", page=italic(page + 1), pages=italic(pages), total=italic(len(rows))),
                buttons=buttons, argument=str(page))


@module.callback("one")
def open_one(ctx: Ctx) -> View:
    return one(ctx)


@module.view("one", parent="history", title="conversation")
def one(ctx: Ctx) -> View:
    number = wanted_number(ctx)
    row = conversation_of(ctx, number)
    if row is None:
        return gone(ctx)
    return View(text=details(ctx, row),
                buttons=[Button(ctx.t("resume"), "resume", number),
                         Button(ctx.t("export"), "export", number),
                         Button(ctx.t("delete"), "delete", number)],
                argument=str(number))


@module.callback("resume")
def resume(ctx: Ctx) -> View:
    number = wanted_number(ctx)
    if conversation_of(ctx, number) is None:
        return gone(ctx)
    ctx.state.set(conversation_key, str(number))
    ctx.state.set(last_key, datetime.now().isoformat(timespec="seconds"))
    ctx.close_screen()
    ctx.log("Conversation " + str(number) + " resumed")
    return View(text=ctx.t("resumed"))


def speaker(ctx: Ctx, role: str) -> str:
    return ctx.t("export_you") if role == "user" else ctx.t("export_assistant")


def transcript(ctx: Ctx, number: int) -> str:
    rows = ctx.db.query_all("SELECT role, content, created_at FROM " + table(ctx) +
                            " WHERE user_id = ? AND conversation = ? ORDER BY id;", (ctx.user.id, number))
    entries = ["[" + when(row['created_at']) + "] " + speaker(ctx, row['role']) + "\n" + row['content'] for row in rows]
    return "\n\n".join(entries) + "\n"


@module.callback("export")
def export(ctx: Ctx) -> View | None:
    number = wanted_number(ctx)
    row = conversation_of(ctx, number)
    if row is None:
        return gone(ctx)
    with ctx.workspace() as path:
        name = os.path.join(path, ctx.t("export_file") + " " + when(row['started']).replace(":", "-") + ".txt")
        with open(name, "w", encoding="utf-8") as handle:
            handle.write(transcript(ctx, number))
        ctx.send_file(name, "document")
    ctx.log("Conversation " + str(number) + " exported")
    return None


@module.callback("delete")
def open_delete(ctx: Ctx) -> View:
    return removal(ctx)


@module.view("delete", parent="one", title="delete")
def removal(ctx: Ctx) -> View:
    number = wanted_number(ctx)
    row = conversation_of(ctx, number)
    if row is None:
        return gone(ctx)
    return View(text=ctx.t("sure") + "\n\n" + details(ctx, row),
                buttons=[Button(ctx.t("core:yes_button"), "delete_confirmed", number)],
                argument=str(number))


@module.callback("delete_confirmed")
def confirm_delete(ctx: Ctx) -> View:
    number = wanted_number(ctx)
    if conversation_of(ctx, number) is None:
        return gone(ctx)
    forget(ctx, number)
    ctx.close_screen()
    ctx.log("Conversation " + str(number) + " deleted")
    return View(text=ctx.t("deleted"))


# ----- settings -----

def kept_days(ctx: Ctx) -> int:
    row = ctx.db.query_one("SELECT keep_days FROM " + settings_table(ctx) + " WHERE user_id = ?;", (ctx.user.id,))
    return row['keep_days'] if row is not None else default_keep


def keeping_name(ctx: Ctx, days: int) -> str:
    return ctx.t("keep_days", days=days) if days else ctx.t("keep_always")


@module.settings()
def settings(ctx: Ctx) -> View:
    now = "\n".join([labelled(ctx.t("labels.thinking"),
                              ctx.t("thinking_on" if is_thinking(ctx) else "thinking_off")),
                     labelled(ctx.t("labels.keeping"), keeping_name(ctx, kept_days(ctx)))])
    return View(text=ctx.t("settings_text") + "\n\n" + now,
                buttons=[Button(ctx.t("thinking_mode"), "thinking_mode"),
                         Button(ctx.t("keeping"), "keeping"),
                         Button(ctx.t("wipe"), "wipe")])


@module.callback("thinking_mode")
def open_thinking_mode(ctx: Ctx) -> View:
    return thinking_mode(ctx)


@module.view("thinking_mode", parent="settings", title="thinking_mode")
def thinking_mode(ctx: Ctx) -> View:
    now = labelled(ctx.t("labels.thinking"), ctx.t("thinking_on" if is_thinking(ctx) else "thinking_off"))
    return View(text=ctx.t("thinking_mode_text") + "\n\n" + now,
                buttons=[Button(ctx.t("thinking_off"), "thinking", "0"),
                         Button(ctx.t("thinking_on"), "thinking", "1")], columns=2)


@module.callback("thinking")
def set_thinking(ctx: Ctx) -> View:
    wanted = ctx.arguments[0] if ctx.arguments else ""
    if wanted not in ("0", "1"):
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.state.set(thinking_key, wanted)
    ctx.log("Thinking turned " + ("on" if wanted == "1" else "off"))
    return settings(ctx)


@module.callback("keeping")
def open_keeping(ctx: Ctx) -> View:
    return keeping(ctx)


@module.view("keeping", parent="settings", title="keeping")
def keeping(ctx: Ctx) -> View:
    now = labelled(ctx.t("labels.keeping"), keeping_name(ctx, kept_days(ctx)))
    return View(text=ctx.t("keeping_text") + "\n\n" + now,
                buttons=[Button(keeping_name(ctx, days), "keep", days) for days in keep_choices], columns=2)


@module.callback("keep")
def set_keeping(ctx: Ctx) -> View:
    wanted = ctx.arguments[0] if ctx.arguments else ""
    if not wanted.isdigit() or int(wanted) not in keep_choices:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.db.execute("INSERT INTO " + settings_table(ctx) + " (user_id, keep_days) VALUES (?, ?) "
                   "ON CONFLICT(user_id) DO UPDATE SET keep_days = excluded.keep_days;", (ctx.user.id, int(wanted)))
    ctx.log("History kept for " + wanted + " days")
    return settings(ctx)


@module.callback("wipe")
def open_wipe(ctx: Ctx) -> View:
    return wipe(ctx)


@module.view("wipe", parent="settings", title="wipe")
def wipe(ctx: Ctx) -> View:
    total = len(conversations(ctx))
    if not total:
        return View(text=ctx.t("history_empty"))
    return View(text=ctx.t("wipe_sure") + "\n\n" + labelled(ctx.t("labels.conversations"), total),
                buttons=[Button(ctx.t("core:yes_button"), "wipe_confirmed")])


@module.callback("wipe_confirmed")
def confirm_wipe(ctx: Ctx) -> View:
    removed = forget(ctx)
    ctx.close_screen()
    ctx.log("History wiped, " + str(removed) + " messages")
    return View(text=ctx.t("wiped"))


# ----- forgetting -----

@module.job(interval=forget_every, name="forget")
def forget_old(ctx: JobCtx) -> None:
    kept = {row['user_id']: row['keep_days']
            for row in ctx.db.query_all("SELECT user_id, keep_days FROM " + settings_table(ctx) + ";")}
    now = datetime.now()
    removed = 0
    for row in ctx.db.query_all("SELECT user_id, conversation, MAX(created_at) AS last FROM " + table(ctx) +
                                " GROUP BY user_id, conversation;"):
        days = kept.get(row['user_id'], default_keep)
        if days and row['last'] < (now - timedelta(days=days)).isoformat(timespec="seconds"):
            removed += ctx.db.execute("DELETE FROM " + table(ctx) + " WHERE user_id = ? AND conversation = ?;",
                                      (row['user_id'], row['conversation'])).rowcount
    if removed:
        ctx.log("Forgot " + str(removed) + " old messages")
