import json
import re
import threading
import time
from collections.abc import Iterator
from datetime import datetime

import requests

from core.api import Button, Ctx, Module, View, escape, italic, labelled

module = Module(name="llm", is_guarded=True, config_keys=["llm_url", "llm_model"], tokens=["llm_key"],
                icons={'name': "🤖", 'title': "🤖", 'new': "🆕", 'continue': "▶️", 'settings_button': "⚙️",
                       'thinking_on': "💭", 'thinking_off': "⚡", 'waiting': "✍️", 'thinking': "💭",
                       'reasoning': "💭"},
                endings={'fresh_done': "✅", 'failed': "💔", 'empty': "🤷", 'not_configured': "🔧", 'busy': "⏳"})

priority = -100
continue_within = 15 * 60
ask_within = 60 * 60
history_messages = 30
history_characters = 24000
edit_every = 3.0
message_limit = 4096
part_size = 3500
live_tail = 3500
thinking_tail = 300
timeouts = (10, 900)
conversation_key = "conversation"
last_key = "last_at"
thinking_key = "thinking"
pending_prefix = "pending."
answering: set[int] = set()
answering_lock = threading.Lock()


def table(ctx: Ctx) -> str:
    return ctx.db.table("messages")


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
    number = current(ctx) + 1
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
            delta = ((json.loads(data).get('choices') or [{}])[0]).get('delta') or {}
            if delta.get('reasoning_content'):
                yield "thinking", delta['reasoning_content']
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


def live_text(ctx: Ctx, thinking: str, answer: str, started: float) -> str:
    if answer:
        return escape(tail(answer, live_tail))
    waited = " (" + str(int(time.monotonic() - started)) + " s)"
    if thinking:
        return ctx.t("thinking") + "…" + waited + "\n" + italic(tail(thinking.strip(), thinking_tail))
    return ctx.t("waiting") + "…" + waited


def folded(ctx: Ctx, thinking: str, seconds: int, room: int) -> str:
    if not thinking.strip() or room < 200:
        return ""
    title = ctx.t("reasoning") + " (" + str(seconds) + " s)"
    return "<blockquote expandable>" + escape(title + "\n" + tail(thinking.strip(), room - len(title) - 60)) + \
        "</blockquote>\n"


def talk(ctx: Ctx, conversation: int) -> None:
    live = ctx.reply_live(ctx.t("waiting") + "…")
    started, edited = time.monotonic(), 0.0
    thinking, answer = "", ""
    try:
        for kind, piece in stream(ctx, history(ctx, conversation), is_thinking(ctx)):
            if kind == "thinking":
                thinking += piece
            else:
                answer += piece
            if live is not None and time.monotonic() - edited >= edit_every:
                ctx.edit(live, live_text(ctx, thinking, answer, started))
                edited = time.monotonic()
    except (requests.RequestException, ValueError) as error:
        ctx.error("The language model did not answer - " + type(error).__name__, str(error))
        finish(ctx, live, [ctx.t("failed")])
        return
    if not answer.strip():
        finish(ctx, live, [ctx.t("empty")])
        return
    remember(ctx, conversation, "assistant", answer)
    parts = [to_html(part) for part in parts_of(answer.strip())]
    quote = folded(ctx, thinking, int(time.monotonic() - started), message_limit - len(parts[0]) - 100)
    finish(ctx, live, [quote + parts[0]] + parts[1:])
    ctx.log("Answered in conversation " + str(conversation))


def finish(ctx: Ctx, live: int | None, parts: list[str]) -> None:
    first, rest = parts[0], parts[1:]
    if live is None or not ctx.edit(live, first):
        rest = parts
    for part in rest:
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
    return View(text=ctx.t("how"), buttons=[Button(ctx.t("new"), "fresh"),
                                            Button.settings(ctx.t("settings_button"), module.name)])


@module.callback("fresh")
def start_fresh(ctx: Ctx) -> View:
    fresh(ctx)
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


@module.settings()
def settings(ctx: Ctx) -> View:
    now = labelled(ctx.t("settings_current"), ctx.t("thinking_on" if is_thinking(ctx) else "thinking_off"))
    return View(text=ctx.t("settings_text") + "\n\n" + now,
                buttons=[Button(ctx.t("thinking_off"), "thinking", "0"),
                         Button(ctx.t("thinking_on"), "thinking", "1")])


@module.callback("thinking")
def set_thinking(ctx: Ctx) -> View:
    wanted = ctx.arguments[0] if ctx.arguments else ""
    if wanted not in ("0", "1"):
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.state.set(thinking_key, wanted)
    ctx.log("Thinking turned " + ("on" if wanted == "1" else "off"))
    return settings(ctx)
