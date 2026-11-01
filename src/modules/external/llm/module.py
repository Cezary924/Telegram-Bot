import base64
import json
import os
import re
import sqlite3
import subprocess
import threading
import time
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta

import requests

from core.api import Action, Button, Ctx, Html, JobCtx, Module, Outcome, View, bold, escape, italic, labelled, plain

module = Module(name="llm", is_guarded=True, is_assistant=True, config_keys=["llm_url", "llm_model", "llm_prompt"],
                tokens=["llm_key"],
                icons={'name': "🤖", 'title': "🤖", 'new': "🆕", 'continue': "▶️", 'settings_button': "⚙️",
                       'thinking_mode': "💭", 'thinking_on': "💭", 'thinking_off': "⚡", 'waiting': "🔍",
                       'writing': "✍️", 'thinking': "💭", 'reasoning': "💭", 'history': "📜", 'resume': "▶️",
                       'export': "📄", 'delete': "🗑️", 'modules': "🧩",
                       'keeping': "⏳", 'wipe': "🗑️", 'conversation': "💬", 'previous': "⬅️", 'next': "➡️"},
                endings={'how': "💬", 'fresh_done': "✅", 'failed': "💔", 'empty': "🤷", 'not_configured': "🔧",
                         'busy': "⏳", 'resumed': "✅", 'deleted': "✅", 'wiped': "✅", 'gone': "💔",
                         'too_big': "📦", 'unreadable': "💔", 'unsupported': "🤷", 'confirm': "👇",
                         'cancelled': "❌"})

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
media_kinds = ("photo", "document", "sticker", "animation", "video", "video_note", "voice", "audio", "location",
               "venue", "contact", "poll", "dice")
filed_kinds = ("animation", "video", "video_note", "voice", "audio", "document")
frames_per_film = 4
frame_scale = "scale='min(768,iw)':-2"
sound_seconds = 180
writing_size = 1024 * 1024
writing_characters = 12000
description_size = 300
album_wait = 1.5
convert_timeout = 120
tool_rounds = 4
confirm_within = 24 * 60 * 60
action_prefix = "action."
action_role = "action"
speakers = {'user': "export_you", action_role: "export_action"}
off_prefix = "off."
note_size = 300
on_mark = "✅ "
off_mark = "⬜ "
weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
private_pattern = re.compile("|".join([
    r"system[ -]?(?:prompt|message|instruction|note|rule)s?", r"\bpromp[tc]", r"systemow",
    r"\bthe system (?:says|said|tells|told|wants|asks|asked|instructs|instructed|requires|notes|mentions|states)",
    r"developer (?:message|instruction|prompt)s?",
    r"\b(?:my|these|those|system|given|above|earlier|previous|the) (?:instructions|guidelines|rules) "
    r"(?:say|said|tell|told|state|stated|ask|asked|require|required|mention|mentioned|forbid|want)",
    r"\baccording to (?:the|my|these) (?:instructions|guidelines|rules|context)",
    r"\b(?:my|these|those|system|given|developer) (?:instructions|guidelines)",
    r"\bI(?:['’]m| am| was|['’]ve been| have been) (?:told|instructed|not allowed|forbidden)",
    r"\bI (?:must not|mustn['’]t|should not|shouldn['’]t|cannot|can['’]t) (?:reveal|mention|show|disclose)",
    r"\bnot to (?:reveal|mention|show|disclose)", r"\bonly for me\b", r"\btool names?\b", r"\bnames? of the tools\b",
    r"(?:moje|moich|moimi|te|tych|tymi|zgodnie z) (?:instrukcj|zasad|wytyczn)",
    r"(?:instrukcj|zasad|wytyczn)\w* (?:mówi|każ|zabrani|wymag|nakaz|zakaz|pozwal)",
    r"\b(?:kazano|napisano|powiedziano|polecono) mi",
    r"\b(?:nie wolno mi|nie mogę|nie powinienem|nie powinnam|mam nie|żeby nie) (?:ujawni|zdradz|pokaz|wspomin|podawa)",
    r"\btylko dla mnie\b", r"\bnazw\w* narzędzi"]), re.IGNORECASE)
sentence_end = re.compile(r"(?<=[.!?…])\s+")
answering: set[int] = set()
answering_lock = threading.Lock()
albums: dict[str, list[dict]] = {}
albums_lock = threading.Lock()
settling_lock = threading.Lock()


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


def remember(ctx: Ctx, conversation: int, role: str, content: str) -> int:
    return ctx.db.execute("INSERT INTO " + table(ctx) + " (user_id, conversation, role, content, created_at) "
                          "VALUES (?, ?, ?, ?, ?);",
                          (ctx.user.id, conversation, role, content,
                           datetime.now().isoformat(timespec="seconds"))).lastrowid or 0


def remember_action(ctx: Ctx, conversation: int, tool: str, arguments: dict, said: dict) -> None:
    remember(ctx, conversation, action_role, json.dumps({'tool': tool, 'arguments': arguments, 'said': said},
                                                        ensure_ascii=False, default=str))


def replayed(row: sqlite3.Row) -> list[dict]:
    if row['role'] != action_role:
        return [{'role': row['role'], 'content': row['content']}]
    done, call = json.loads(row['content']), "call_" + str(row['id'])
    return [{'role': "assistant", 'content': None,
             'tool_calls': [{'id': call, 'type': "function",
                             'function': {'name': done['tool'],
                                          'arguments': json.dumps(done['arguments'], ensure_ascii=False)}}]},
            {'role': "tool", 'tool_call_id': call, 'name': done['tool'],
             'content': json.dumps(done['said'], ensure_ascii=False)}]


def history(ctx: Ctx, conversation: int) -> list[dict]:
    rows = ctx.db.query_all("SELECT id, role, content FROM " + table(ctx) + " WHERE user_id = ? AND conversation = ? "
                            "ORDER BY id DESC LIMIT ?;", (ctx.user.id, conversation, history_messages))
    kept, total = [], 0
    for row in rows:
        total += len(row['content'])
        if kept and total > history_characters:
            break
        kept.append(replayed(row))
    return [message for messages in reversed(kept) for message in messages]


# ----- media -----

class Unreadable(Exception):
    pass


class TooBig(Exception):
    pass


class Unsupported(Exception):
    pass


def coordinates(location) -> str:
    return format(location.latitude, ".5f") + ", " + format(location.longitude, ".5f")


def item_of(ctx: Ctx) -> dict:
    kind = ctx.kind
    item: dict = {'kind': kind, 'text': ctx.text.strip()}
    if ctx.message is None or kind == "text":
        return item
    sent = getattr(ctx.message, kind)
    if kind == "photo":
        item.update(file_id=sent[-1].file_id, size=sent[-1].file_size or 0)
    elif kind == "sticker":
        item.update(file_id=sent.file_id, size=sent.file_size or 0, emoji=sent.emoji or "",
                    form="video" if sent.is_video else "animated" if sent.is_animated else "static")
    elif kind in filed_kinds:
        item.update(file_id=sent.file_id, size=sent.file_size or 0, mime=getattr(sent, 'mime_type', None) or "",
                    name=getattr(sent, 'file_name', None) or "", duration=getattr(sent, 'duration', None) or 0)
    elif kind == "location":
        item['details'] = coordinates(sent)
    elif kind == "venue":
        item['details'] = ", ".join(part for part in (sent.title, sent.address, coordinates(sent.location)) if part)
    elif kind == "contact":
        item['details'] = " ".join(part for part in (sent.first_name, sent.last_name, sent.phone_number) if part)
    elif kind == "poll":
        item['details'] = sent.question + ": " + " / ".join(option.text for option in sent.options)
    elif kind == "dice":
        item['details'] = sent.emoji + " " + str(sent.value)
    return item


def family(item: dict) -> str:
    kind, mime = item['kind'], item.get('mime', "")
    if kind == "photo" or (kind == "sticker" and item['form'] == "static") or \
            (kind == "document" and mime.startswith("image/")):
        return "picture"
    if kind in ("video", "animation", "video_note") or (kind == "sticker" and item['form'] == "video") or \
            (kind == "document" and mime.startswith("video/")):
        return "film"
    if kind in ("voice", "audio") or (kind == "document" and mime.startswith("audio/")):
        return "sound"
    return "file" if kind == "document" else "words"


def gathered(ctx: Ctx) -> list[dict]:
    item = item_of(ctx)
    group = ctx.message.media_group_id if ctx.message is not None else None
    if not group:
        return [item]
    with albums_lock:
        is_first = group not in albums
        albums.setdefault(group, []).append(item)
    if not is_first:
        return []
    time.sleep(album_wait)
    with albums_lock:
        return albums.pop(group)


def pending_items(stored: str) -> list[dict]:
    try:
        items = json.loads(stored)
    except ValueError:
        items = None
    return items if isinstance(items, list) else [{'kind': "text", 'text': stored}]


def note(ctx: Ctx, item: dict, description: str = "", body: str = "") -> str:
    if item['kind'] == "text":
        return item['text']
    about = ", ".join(part for part in (item.get('emoji', ""), item.get('name', ""), item.get('details', ""),
                                        description) if part)
    head = "[" + str(ctx.t("media." + item['kind'])) + (": " + about if about else "") + "]"
    return "\n".join(part for part in (head, body, item['text']) if part)


def converted(ctx: Ctx, data: bytes, arguments: list[str], output: str) -> list[bytes]:
    with ctx.workspace() as path:
        source = os.path.join(path, "source")
        with open(source, "wb") as handle:
            handle.write(data)
        try:
            done = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", source, *arguments,
                                   os.path.join(path, output)], capture_output=True, timeout=convert_timeout)
        except (OSError, subprocess.SubprocessError) as error:
            raise Unreadable(type(error).__name__ + " " + str(error)) from error
        if done.returncode != 0:
            raise Unreadable(done.stderr.decode("utf-8", "replace")[-300:])
        results = []
        for name in sorted(os.listdir(path)):
            if name != "source":
                with open(os.path.join(path, name), "rb") as handle:
                    results.append(handle.read())
        return results


def picture_part(data: bytes, mime: str) -> dict:
    return {'type': "image_url", 'image_url': {'url': "data:" + mime + ";base64," + base64.b64encode(data).decode()}}


def sound_part(data: bytes) -> dict:
    return {'type': "input_audio", 'input_audio': {'data': base64.b64encode(data).decode(), 'format': "wav"}}


def sound_of(ctx: Ctx, data: bytes) -> list[dict]:
    arguments = ["-vn", "-ac", "1", "-ar", "16000", "-t", str(sound_seconds)]
    return [sound_part(sound) for sound in converted(ctx, data, arguments, "sound.wav")]


def parts_for(ctx: Ctx, item: dict) -> tuple[str, list[dict]]:
    kind, what = item['kind'], family(item)
    if what == "words":
        return note(ctx, item), []
    if item.get('size', 0) > ctx.download_limit:
        raise TooBig(kind)
    data = ctx.download(item['file_id'])
    if data is None:
        raise Unreadable("Telegram gave no file")
    if what == "picture":
        if kind == "photo" or item.get('mime') in ("image/jpeg", "image/png"):
            return note(ctx, item), [picture_part(data, item.get('mime') or "image/jpeg")]
        return note(ctx, item), [picture_part(picture, "image/png") for picture in
                                 converted(ctx, data, ["-frames:v", "1", "-vf", frame_scale], "picture.png")]
    if what == "film":
        rate = "fps=" + str(frames_per_film) + "/" + str(item['duration']) if item.get('duration') else "fps=2"
        frames = converted(ctx, data, ["-vf", rate + "," + frame_scale, "-frames:v", str(frames_per_film)],
                           "frame%d.jpg")
        parts = [picture_part(frame, "image/jpeg") for frame in frames]
        if kind in ("video", "video_note", "document"):
            try:
                parts += sound_of(ctx, data)
            except Unreadable:
                pass
        return note(ctx, item), parts
    if what == "sound":
        return note(ctx, item), sound_of(ctx, data)
    if len(data) > writing_size or b"\0" in data:
        raise Unsupported(item.get('mime') or kind)
    try:
        writing = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Unsupported(item.get('mime') or kind) from error
    return note(ctx, item, body=writing[:writing_characters]), []


def describe(ctx: Ctx, item: dict, parts: list[dict]) -> str:
    asked = [{'role': "user", 'content': [{'type': "text", 'text': str(ctx.t("describe." + family(item)))}] + parts}]
    said = ""
    try:
        for kind, piece in stream(ctx, asked, False):
            if kind == "answer" and isinstance(piece, str):
                said += piece
    except (requests.RequestException, ValueError) as error:
        ctx.error("The language model did not describe a " + item['kind'] + " - " + type(error).__name__, str(error))
        return ""
    return " ".join(said.split())[:description_size]


def is_thinking(ctx: Ctx) -> bool:
    return ctx.state.get(thinking_key) == "1"


def gather(calls: dict[int, dict], pieces: list[dict]) -> None:
    for piece in pieces:
        index = piece.get('index')
        call = calls.setdefault(index if isinstance(index, int) else len(calls),
                                {'id': "", 'name': "", 'arguments': ""})
        function = piece.get('function') or {}
        given = function.get('arguments') or ""
        call['id'] = call['id'] or piece.get('id') or ""
        call['name'] = call['name'] or function.get('name') or ""
        call['arguments'] += given if isinstance(given, str) else json.dumps(given, ensure_ascii=False)


def stream(ctx: Ctx, messages: list[dict], thinking: bool,
           tools: list[dict] | None = None) -> Iterator[tuple[str, str | list[dict]]]:
    headers = {'Authorization': "Bearer " + ctx.token("llm_key")} if ctx.has_token("llm_key") else {}
    payload = {'model': ctx.setting("llm_model") or "", 'messages': messages, 'stream': True,
               'chat_template_kwargs': {'enable_thinking': thinking}}
    if not thinking:
        payload['reasoning_effort'] = "none"
    if tools:
        payload['tools'] = tools
    url = (ctx.setting("llm_url") or "").rstrip("/") + "/chat/completions"
    calls: dict[int, dict] = {}
    finished = ""
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
            if event.get('type') == "mcp_tool_result":
                calls.clear()
                finished = ""
                yield "tool", ""
                continue
            first = (event.get('choices') or [{}])[0]
            delta = first.get('delta') or {}
            if delta.get('tool_calls'):
                gather(calls, delta['tool_calls'])
                yield "tool", ""
            thought = delta.get('reasoning_content') or delta.get('reasoning') or ""
            if thought:
                yield "thinking", thought
            if delta.get('content'):
                yield "answer", delta['content']
            finished = first.get('finish_reason') or finished
    if finished == "tool_calls" and calls:
        yield "calls", [call | {'id': call['id'] or "call_" + uuid.uuid4().hex[:12]}
                        for _, call in sorted(calls.items())]


# ----- assistant -----

def bare(ctx: Ctx, key: str) -> str:
    return plain(ctx.t(key))


def is_open(ctx: Ctx, name: str) -> bool:
    return ctx.state.get(off_prefix + name) != "1"


def sharing(ctx: Ctx) -> list[Module]:
    acting = {found.name for found, _ in ctx.assistant.actions()}
    return [found for found in ctx.assistant.modules()
            if found.name != module.name and (found.name in acting or found.summary is not None)]


def offered(ctx: Ctx) -> list[tuple[Module, Action]]:
    return [(found, action) for found, action in ctx.assistant.actions()
            if found.name != module.name and is_open(ctx, found.name)]


def tools_for(ctx: Ctx, actions: list[tuple[Module, Action]]) -> list[dict]:
    return [{'type': "function",
             'function': {'name': action.tool, 'description': bare(ctx, found.name + ":" + action.description),
                          'parameters': {'type': "object",
                                         'properties': {name: {'type': action.type_of(name),
                                                               'description': bare(ctx, found.name + ":" +
                                                                                   action.key(name))}
                                                        for name in action.parameters},
                                         'required': [name for name in action.parameters
                                                      if name not in action.optional]}}}
            for found, action in actions]


def entry(ctx: Ctx, found: Module) -> str:
    command = next((each.name for each in found.commands if ctx.user.role >= each.role), "")
    if not command:
        return ""
    return "/" + command + " - " + bare(ctx, found.name + ":" + found.title) + " - " + \
        bare(ctx, found.name + ":" + found.description)


def clock(ctx: Ctx) -> str:
    now = datetime.now().astimezone()
    offset = now.strftime("%z")
    return now.strftime(date_format) + ", " + bare(ctx, "weekdays." + weekdays[now.weekday()]) + ", " + \
        (now.tzname() or "") + " (UTC" + offset[:3] + ":" + offset[3:] + ")"


def prompt(ctx: Ctx, is_acting: bool) -> str:
    others = [found for found in ctx.assistant.modules() if found.name != module.name]
    listed = [line for line in (entry(ctx, found) for found in others) if line]
    known = [(found, ctx.assistant.context(found.name)) for found in others
             if found.summary is not None and is_open(ctx, found.name)]
    known = ["[" + bare(ctx, found.name + ":" + found.title) + "]\n" + text for found, text in known if text]
    name = " ".join(part for part in (ctx.user.first_name, ctx.user.last_name) if part)
    parts = [(ctx.setting("llm_prompt") or "").strip(),
             bare(ctx, "prompt.modules") + ":\n" + "\n".join(listed) if listed else "",
             bare(ctx, "prompt.actions") if is_acting else "",
             bare(ctx, "prompt.rules"),
             bare(ctx, "prompt.user") + ": " + name + ", " + bare(ctx, "core:language_label"),
             bare(ctx, "prompt.context") + ":\n" + "\n".join(known) if known else ""]
    return "\n\n".join(part for part in parts if part)


def stamped(ctx: Ctx, message: dict) -> dict:
    line = "[" + bare(ctx, "prompt.now") + ": " + clock(ctx) + "]\n"
    content = message['content']
    if isinstance(content, str):
        return message | {'content': line + content}
    return message | {'content': [{'type': "text", 'text': line + content[0]['text']}] + content[1:]}


def told(outcome: Outcome) -> dict:
    if outcome.status == "done":
        result = outcome.result
        return {'status': "done", 'result': result if isinstance(result, (list, dict)) else plain(result)}
    if outcome.status == "asking":
        return {'status': "pending_confirmation", 'summary': plain(str(outcome.result))}
    return {'status': "refused", 'problem': plain(str(outcome.result))}


def action_note(tool: str, said: dict) -> str:
    detail = said.get('result', said.get('summary', said.get('problem', "")))
    text = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False, default=str)
    return "[" + tool + " - " + said['status'] + ": " + shortened(text, note_size) + "]"


def arguments_of(call: dict) -> dict:
    try:
        arguments = json.loads(call['arguments'] or "{}")
    except ValueError:
        return {}
    return arguments if isinstance(arguments, dict) else {}


def expired() -> str:
    return (datetime.now() - timedelta(seconds=confirm_within)).isoformat(timespec="seconds")


def forget_pending(ctx: Ctx) -> None:
    oldest = expired()
    for key, value in ctx.state.all().items():
        if key.startswith(action_prefix) and json.loads(value or "{}").get('at', "") < oldest:
            ctx.state.delete(key)


def perform(ctx: Ctx, conversation: int, found: Module, action: Action, call: dict, done: list[tuple],
            asking: dict[str, View]) -> dict:
    arguments = arguments_of(call)
    outcome = ctx.assistant.act(found.name, action.name, arguments)
    asked = action.tool + ":" + str(outcome.result)
    if outcome.status == "asking" and asked not in asking:
        forget_pending(ctx)
        key, title = uuid.uuid4().hex[:12], ctx.t(found.name + ":" + found.title)
        ctx.state.set(action_prefix + key, json.dumps({'module': found.name, 'action': action.name, 'tool': action.tool,
                                                       'arguments': arguments, 'conversation': conversation,
                                                       'title': title, 'question': outcome.result,
                                                       'at': datetime.now().isoformat(timespec="seconds")},
                                                      ensure_ascii=False))
        asking[asked] = View(text=str(outcome.result), heading=title, columns=2,
                             buttons=[Button(ctx.t("core:yes_button"), "confirm", key),
                                      Button(ctx.t("core:no_button"), "cancel", key)])
    said = told(outcome)
    done.append((action.tool, arguments, said))
    ctx.log("Action " + action.tool + " " + said['status'])
    return said


def wired(call: dict) -> dict:
    return {'id': call['id'], 'type': "function",
            'function': {'name': call['name'], 'arguments': json.dumps(arguments_of(call), ensure_ascii=False)}}


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


def discreet(thinking: str) -> str:
    kept = []
    for line in thinking.split("\n"):
        shown = " ".join(sentence for sentence in sentence_end.split(line) if not private_pattern.search(sentence))
        if shown.strip() or not line.strip():
            kept.append(shown)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def live_text(ctx: Ctx, thinking: str, answer: str, frame: int) -> str:
    dots = "." * (frame % 3 + 1)
    if answer:
        return ctx.t("writing") + dots + "\n\n" + escape(tail(answer, live_tail))
    shown = discreet(thinking)
    if shown:
        return ctx.t("thinking") + dots + "\n\n" + italic(tail(shown, thinking_tail))
    return ctx.t("waiting") + dots


def folded(ctx: Ctx, thinking: str, room: int) -> str:
    shown = discreet(thinking)
    if not shown or room < 200:
        return ""
    title = ctx.t("reasoning")
    return "<blockquote expandable>" + escape(title + "\n" + tail(shown, room - len(title) - 60)) + "</blockquote>\n"


def delivered(ctx: Ctx, thinking: str, answer: str) -> list[str]:
    parts = [to_html(part) for part in parts_of(answer.strip())]
    return [folded(ctx, thinking, message_limit - len(parts[0]) - 100) + parts[0]] + parts[1:]


def talk(ctx: Ctx, conversation: int, live: int | None, attached: list[dict]) -> None:
    actions = offered(ctx)
    tools = {action.tool: (found, action) for found, action in actions}
    described = tools_for(ctx, actions)
    messages: list[dict] = [{'role': "system", 'content': prompt(ctx, bool(actions))}] + history(ctx, conversation)
    thinks = is_thinking(ctx)
    asked = max((index for index, each in enumerate(messages) if each['role'] == "user"), default=None)
    if asked is not None:
        if attached:
            messages[asked]['content'] = [{'type': "text", 'text': messages[asked]['content']}] + attached
        messages[asked] = stamped(ctx, messages[asked])
    rounds, failures, done, asking = [{'thinking': "", 'answer': ""}], [], [], {}

    def read() -> None:
        is_waiting = False
        try:
            for number in range(tool_rounds + 1):
                calls: list[dict] = []
                offer = described if number < tool_rounds and not is_waiting else None
                for kind, piece in stream(ctx, messages, thinks, offer):
                    latest = rounds[-1]
                    if isinstance(piece, list):
                        calls = [call for call in piece if call['name'] in tools]
                    elif kind != "tool":
                        latest[kind] += piece
                    elif latest['answer'].strip():
                        rounds.append({'thinking': "", 'answer': ""})
                    elif latest['thinking'].strip() and not latest['thinking'].endswith("\n\n"):
                        latest['thinking'] = latest['thinking'].rstrip() + "\n\n"
                if not calls or number == tool_rounds:
                    return
                results = [perform(ctx, conversation, *tools[call['name']], call, done, asking) for call in calls]
                is_waiting = all(result['status'] == "pending_confirmation" for result in results)
                messages.append({'role': "assistant", 'content': None, 'tool_calls': [wired(call) for call in calls]})
                messages.extend({'role': "tool", 'tool_call_id': call['id'], 'name': call['name'],
                                 'content': json.dumps(result, ensure_ascii=False, default=str)}
                                for call, result in zip(calls, results))
        except Exception as error:
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
            finish(ctx, live, delivered(ctx, rounds[shown]['thinking'], rounds[shown]['answer']), is_final=False)
            shown += 1
            live, edited = ctx.reply_live(live_text(ctx, "", "", frame), is_silent=True), time.monotonic()
            continue
        showing = rounds[shown]
        if live is not None and (not showing['answer'] or time.monotonic() - edited >= edit_every):
            ctx.edit(live, live_text(ctx, showing['thinking'], showing['answer'], frame))
            edited = time.monotonic()
    answers = [] if failures else [each['answer'].strip() for each in rounds if each['answer'].strip()]
    for tool, arguments, said in done:
        remember_action(ctx, conversation, tool, arguments, said)
    if answers:
        remember(ctx, conversation, "assistant", "\n\n".join(answers))
    if failures:
        ctx.error("The language model did not answer - " + type(failures[0]).__name__, str(failures[0]))
        finish(ctx, live, [ctx.t("failed")], is_final=not asking)
    elif not answers:
        finish(ctx, live, [ctx.t("confirm" if asking else "empty")], is_final=not asking)
    else:
        left = rounds[shown:]
        ending = max(index for index, each in enumerate(left) if index == 0 or each['answer'].strip())
        for index, each in enumerate(left):
            target = live if index == 0 else None
            if each['answer'].strip():
                finish(ctx, target, delivered(ctx, each['thinking'], each['answer']),
                       is_final=index == ending and not asking)
            elif target is not None:
                finish(ctx, target, [ctx.t("empty")], is_final=index == ending and not asking)
        ctx.log("Answered in conversation " + str(conversation))
    for view in asking.values():
        ctx.reply(view)


def finish(ctx: Ctx, live: int | None, parts: list[str], is_final: bool = True) -> None:
    if live is not None and not ctx.remove(live) and ctx.edit(live, parts[0]):
        parts = parts[1:]
    for number, part in enumerate(parts, 1):
        ctx.reply_live(part, is_silent=not is_final or number < len(parts))


def answer_in(ctx: Ctx, conversation: int, items: list[dict]) -> View | None:
    with answering_lock:
        if ctx.user.id in answering:
            return View(text=ctx.t("busy"))
        answering.add(ctx.user.id)
    try:
        answered = respond(ctx, conversation, items)
    finally:
        with answering_lock:
            answering.discard(ctx.user.id)
    if answered is not None and any(parts for _, _, parts in answered[1]):
        asked, prepared = answered
        texts = [note(ctx, item, describe(ctx, item, parts)) if parts else text for item, text, parts in prepared]
        ctx.db.execute("UPDATE " + table(ctx) + " SET content = ? WHERE id = ? AND user_id = ?;",
                       ("\n".join(texts), asked, ctx.user.id))
    return None


def respond(ctx: Ctx, conversation: int, items: list[dict]) -> tuple[int, list[tuple[dict, str, list[dict]]]] | None:
    live = ctx.reply_live(live_text(ctx, "", "", 0), is_silent=True)
    try:
        prepared = [(item, *parts_for(ctx, item)) for item in items]
    except (TooBig, Unsupported, Unreadable) as error:
        problem = "too_big" if isinstance(error, TooBig) else \
            "unsupported" if isinstance(error, Unsupported) else "unreadable"
        ctx.error("Could not take a " + items[0]['kind'] + " - " + type(error).__name__, str(error))
        finish(ctx, live, [ctx.t(problem)])
        return None
    asked = remember(ctx, conversation, "user", "\n".join(text for _, text, _ in prepared))
    ctx.state.set(last_key, datetime.now().isoformat(timespec="seconds"))
    talk(ctx, conversation, live, [part for _, _, parts in prepared for part in parts])
    return asked, prepared


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


@module.match(is_chat, priority=priority, is_background=True, media=media_kinds)
def take_message(ctx: Ctx) -> View | None:
    if not ctx.setting("llm_url"):
        ctx.error("There is no llm_url in config.yaml")
        return View(text=ctx.t("not_configured"))
    items = gathered(ctx)
    if not items:
        return None
    since = seconds_since(ctx)
    if since is None or since > ask_within:
        return answer_in(ctx, fresh(ctx), items)
    if since < continue_within:
        return answer_in(ctx, current(ctx), items)
    asked = str(ctx.message.message_id) if ctx.message is not None else "0"
    ctx.state.set(pending_prefix + asked, json.dumps(items, ensure_ascii=False))
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
    stored = ctx.state.get(pending_prefix + asked)
    if kind not in ("continue", "new") or not stored:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.state.delete(pending_prefix + asked)
    ctx.close_screen()
    return answer_in(ctx, current(ctx) if kind == "continue" else fresh(ctx), pending_items(stored))


@module.callback("confirm", is_background=True)
def confirm(ctx: Ctx) -> View | None:
    return settle(ctx, True)


@module.callback("cancel")
def cancel(ctx: Ctx) -> View | None:
    return settle(ctx, False)


def settle(ctx: Ctx, is_confirmed: bool) -> View | None:
    key = ctx.arguments[0] if ctx.arguments else ""
    with settling_lock:
        stored = ctx.state.get(action_prefix + key)
        ctx.state.delete(action_prefix + key)
    pending = json.loads(stored or "{}")
    if not pending or pending.get('at', "") < expired() or ctx.message is None:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    if is_confirmed:
        outcome = ctx.assistant.act(pending['module'], pending['action'], pending['arguments'], is_confirmed=True)
        said = told(outcome) | ({'status': "confirmed"} if outcome.status == "done" else {})
        text = str(outcome.result)
    else:
        said = {'status': "cancelled", 'summary': plain(pending['question'])}
        text = pending['question'] + "\n\n" + ctx.t("cancelled")
    shown = bold(Html(pending['title']), ":") + "\n\n" + text
    remember_action(ctx, pending['conversation'], pending['tool'], pending['arguments'], said)
    ctx.log("Action " + pending['tool'] + " " + said['status'])
    return None if ctx.edit(ctx.message.message_id, shown) else View(shown, heading=None)


# ----- history -----

def conversations(ctx: Ctx, number: int | None = None) -> list[sqlite3.Row]:
    only = " AND m.conversation = ?" if number is not None else ""
    return ctx.db.query_all(
        "SELECT m.conversation, MIN(m.created_at) AS started, MAX(m.created_at) AS last, "
        "SUM(m.role != '" + action_role + "') AS total, "
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
    return ctx.t(speakers.get(role, "export_assistant"))


def readable(row: sqlite3.Row) -> str:
    if row['role'] != action_role:
        return row['content']
    done = json.loads(row['content'])
    return action_note(done['tool'], done['said'])


def transcript(ctx: Ctx, number: int) -> str:
    rows = ctx.db.query_all("SELECT role, content, created_at FROM " + table(ctx) +
                            " WHERE user_id = ? AND conversation = ? ORDER BY id;", (ctx.user.id, number))
    entries = ["[" + when(row['created_at']) + "] " + speaker(ctx, row['role']) + "\n" + readable(row) for row in rows]
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
                         Button(ctx.t("modules"), "modules"),
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


@module.callback("modules")
def open_modules(ctx: Ctx) -> View:
    return modules_screen(ctx)


@module.view("modules", parent="settings", title="modules")
def modules_screen(ctx: Ctx) -> View:
    found = sharing(ctx)
    if not found:
        return View(text=ctx.t("modules_empty"))
    return View(text=ctx.t("modules_text"),
                buttons=[Button(mark(ctx, each.name) + ctx.t(each.name + ":" + each.title), "share", each.name)
                         for each in found])


def mark(ctx: Ctx, name: str) -> str:
    return on_mark if is_open(ctx, name) else off_mark


@module.callback("share")
def share(ctx: Ctx) -> View:
    wanted = ctx.arguments[0] if ctx.arguments else ""
    if wanted not in [each.name for each in sharing(ctx)]:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    if is_open(ctx, wanted):
        ctx.state.set(off_prefix + wanted, "1")
    else:
        ctx.state.delete(off_prefix + wanted)
    ctx.log("Assistant " + ("let into " if is_open(ctx, wanted) else "kept out of ") + wanted)
    return modules_screen(ctx)


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
