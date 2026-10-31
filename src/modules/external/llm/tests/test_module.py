import base64
import json
import re
import time
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from core.api import Ctx, JobCtx, Module, Outcome, Role, User
from core.testing import make_callback, make_message, not_none
from modules.external.llm import module as llm

real_stream = llm.stream
stamp = re.compile(r"^\[(?:Now it is|Teraz jest): [^\n\]]*]\n")
health_modules = ("bmi", "bodytracker")


def unstamped(message: dict, clocks: list[str]) -> dict:
    content = message['content']
    if message['role'] != "user":
        return dict(message)
    text = content if isinstance(content, str) else content[0]['text']
    found = stamp.match(text)
    if found is None:
        return dict(message)
    clocks.append(found.group(0))
    rest = text[found.end():]
    return message | {'content': rest if isinstance(content, str) else [content[0] | {'text': rest}] + content[1:]}


class Model:
    def __init__(self):
        self.asked: list[list[dict]] = []
        self.systems: list[str] = []
        self.clocks: list[str] = []
        self.tools: list[list[dict] | None] = []
        self.thinking: list[bool] = []
        self.answer: list[tuple] = [("answer", "Hello there")]
        self.script: list[list[tuple]] = []
        self.error: Exception | None = None

    def stream(self, _ctx, messages, thinking, tools=None):
        self.systems += [one['content'] for one in messages if one['role'] == "system"]
        self.asked.append([unstamped(one, self.clocks) for one in messages if one['role'] != "system"])
        self.tools.append(tools)
        self.thinking.append(thinking)
        if self.error is not None:
            raise self.error
        yield from self.script.pop(0) if self.script else self.answer


@pytest.fixture
def model(monkeypatch) -> Model:
    fake = Model()
    monkeypatch.setattr(llm, "stream", fake.stream)
    return fake


def configure(app, monkeypatch, tokens: dict | None = None, **settings) -> None:
    def setting(name, default=None):
        value = settings.get(name, default)
        if value is None:
            raise KeyError(name)
        return value

    def token(name):
        if name not in (tokens or {}):
            raise KeyError(name)
        return (tokens or {})[name]

    monkeypatch.setattr(app.config, "setting", setting)
    monkeypatch.setattr(app.config, "token", token)
    monkeypatch.setattr(app.config, "has_token", lambda name: name in (tokens or {}))


@pytest.fixture
def chat(app, model, monkeypatch):
    configure(app, monkeypatch, llm_url="http://model.local/v1", llm_model="small")
    app.storage.access.allow(1, "llm", True)
    for name in health_modules:
        app.storage.access.allow(1, name, False)
    return app


def say(app, text: str, message_id: int = 100):
    app.router.handle_message(make_message(text, message_id=message_id))
    app.router.wait_for_tasks()


def press(app, data: str):
    sent = app.services.bot.sent
    app.router.handle_callback(make_callback(data, message_id=sent[-1].message_id) if sent else make_callback(data))
    app.router.wait_for_tasks()


def stored(app) -> list[tuple[int, str, str]]:
    return [(row['conversation'], row['role'], row['content']) for row in app.storage.database.query_all(
        "SELECT * FROM " + app.storage.for_module("llm").table("messages") + " ORDER BY id;")]


def answers(bot) -> list[str]:
    return [message.text for message in bot.sent if (message.chat_id, message.message_id) not in bot.deleted]


def loud(bot) -> list[str]:
    return [message.text for message in bot.sent if not message.is_silent]


def last_written(app, minutes: int) -> None:
    moment = (datetime.now() - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    app.storage.module_state.set(1, "llm", "last_at", moment)


# ----- who may talk -----

def test_without_access_a_message_never_reaches_the_model(app, bot, model, monkeypatch):
    app.storage.access.allow(1, "llm", False)
    configure(app, monkeypatch, llm_url="http://model.local/v1")
    say(app, "hello")
    assert model.asked == []
    assert bot.last.text == "Sorry, I do not understand... 💔"


def test_without_access_the_command_offers_to_ask(app, bot, model):
    app.storage.access.allow(1, "llm", False)
    app.storage.users.set_role(1, Role.GUEST)
    say(app, "/llm")
    assert bot.last.text == "You do not have access to 🤖 Assistant yet 🔒"
    assert bot.last.buttons == [("🙋 Ask for access", "core:request:llm")]
    assert model.asked == []


@pytest.mark.parametrize("data", ["llm:fresh", "llm:pick:new:100", "llm:thinking:1", "core:settings:llm"])
def test_without_access_no_button_reaches_the_module(app, bot, model, data):
    app.storage.access.allow(1, "llm", False)
    app.storage.module_state.set(1, "llm", "pending.100", "hello")
    app.router.handle_callback(make_callback(data))
    app.router.wait_for_tasks()
    assert model.asked == []
    assert app.storage.module_state.get(1, "llm", "thinking") is None
    assert bot.last.text.startswith("You do not have access to")


def test_taking_access_away_stops_the_next_message(chat, bot, model):
    say(chat, "hello")
    chat.storage.access.allow(1, "llm", False)
    say(chat, "again")
    assert len(model.asked) == 1


def test_an_admin_talks_without_being_let_in(app, bot, model, monkeypatch):
    configure(app, monkeypatch, llm_url="http://model.local/v1")
    app.storage.users.set_role(1, Role.ADMIN)
    say(app, "hello")
    assert len(model.asked) == 1


def test_a_link_still_goes_to_the_downloader(chat, bot, model, monkeypatch):
    monkeypatch.setattr("modules.external.downloader.module.download", lambda _url, _path, _limit, _kind: [])
    say(chat, "https://example.com/watch")
    assert model.asked == []


# ----- answering -----

def test_a_quiet_status_gives_way_to_the_answer_in_a_new_message(chat, bot, model):
    say(chat, "hello")
    assert model.asked == [[{'role': "user", 'content': "hello"}]]
    status = bot.sent[0]
    assert status.is_silent and status.text == "🔍 Analyzing."
    assert bot.deleted == [(1, status.message_id)]
    assert answers(bot) == ["Hello there"]
    assert stored(chat) == [(1, "user", "hello"), (1, "assistant", "Hello there")]


def test_the_status_is_rewritten_when_it_cannot_be_deleted(chat, bot, model, monkeypatch):
    monkeypatch.setattr(Ctx, "remove", lambda *_args: False)
    say(chat, "hello")
    assert len(bot.sent) == 1 and bot.sent[0].is_silent
    assert bot.edited[-1].text == "Hello there"


def test_thinking_is_off_by_default_and_on_when_chosen(chat, bot, model):
    say(chat, "hello")
    chat.storage.module_state.set(1, "llm", "thinking", "1")
    say(chat, "again")
    assert model.thinking == [False, True]


def test_thinking_is_folded_above_the_answer(chat, bot, model):
    chat.storage.module_state.set(1, "llm", "thinking", "1")
    model.answer = [("thinking", "Two and <two>"), ("answer", "Four")]
    say(chat, "2+2?")
    assert bot.last.text.startswith("<blockquote expandable>💭 Reasoning\n")
    assert "Two and &lt;two&gt;</blockquote>\nFour" in bot.last.text
    assert stored(chat)[-1] == (1, "assistant", "Four")


def test_thinking_keeps_quiet_about_the_instructions():
    thinking = ("The user asks about the weather. The system prompt says I must not show ids. I will answer briefly.\n"
                "- According to the instructions, dates only when asked.\n- Answer in Polish.\n\n"
                "Użytkownik pyta o pogodę. Zgodnie z instrukcjami nie podaję godziny. Odpowiem krótko.")
    assert llm.discreet(thinking) == ("The user asks about the weather. I will answer briefly.\n- Answer in Polish.\n\n"
                                      "Użytkownik pyta o pogodę. Odpowiem krótko.")


def test_shown_thinking_leaves_out_the_instructions(chat, bot, model):
    chat.storage.module_state.set(1, "llm", "thinking", "1")
    model.answer = [("thinking", "Adding up. The system prompt tells me to be brief."), ("answer", "Four")]
    say(chat, "2+2?")
    assert "Adding up.</blockquote>\nFour" in bot.last.text and "prompt" not in bot.last.text
    model.answer = [("thinking", "My instructions say to be brief."), ("answer", "Four")]
    say(chat, "2+2?")
    assert bot.last.text == "Four"


def test_the_dots_move_while_the_model_is_silent(chat, bot, monkeypatch):
    def slow(_ctx, _messages, _thinking, _tools=None):
        time.sleep(0.1)
        yield "thinking", "hmm"
        time.sleep(0.1)
        yield "answer", "Fo"
        time.sleep(0.1)
        yield "answer", "ur"

    monkeypatch.setattr(llm, "stream", slow)
    monkeypatch.setattr(llm, "tick", 0.01)
    monkeypatch.setattr(llm, "edit_every", 0.01)
    say(chat, "2+2?")
    shown = [message.text for message in bot.edited]
    assert {"🔍 Analyzing.", "🔍 Analyzing..", "🔍 Analyzing..."} <= set(shown)
    assert {"💭 Thinking.\n\n<i>hmm</i>", "💭 Thinking..\n\n<i>hmm</i>"} <= set(shown)
    assert {"✍️ Writing.\n\nFo", "✍️ Writing..\n\nFo"} <= set(shown)
    assert bot.last.text.endswith("</blockquote>\nFour")


def test_text_before_a_search_stays_in_its_own_message(chat, bot, model):
    model.answer = [("answer", "Let me check."), ("tool", ""), ("tool", ""), ("answer", "Found it")]
    say(chat, "who was it?")
    assert [message.text for message in bot.shown[-2:]] == ["Let me check.", "Found it"]
    assert loud(bot) == ["Found it"]
    assert stored(chat)[-1] == (1, "assistant", "Let me check.\n\nFound it")


def test_a_search_before_any_text_keeps_one_message(chat, bot, model):
    model.answer = [("tool", ""), ("answer", "Found it")]
    say(chat, "who was it?")
    assert answers(bot) == ["Found it"]


def test_a_new_message_waits_for_the_search_while_it_runs(chat, bot, monkeypatch):
    def slow(_ctx, _messages, _thinking, _tools=None):
        yield "answer", "Let me check."
        yield "tool", ""
        time.sleep(0.1)
        yield "answer", "Found it"

    monkeypatch.setattr(llm, "stream", slow)
    monkeypatch.setattr(llm, "tick", 0.01)
    say(chat, "who was it?")
    shown = [message.text for message in bot.shown]
    assert answers(bot) == ["Let me check.", "Found it"]
    assert loud(bot) == ["Found it"]
    assert shown[shown.index("Let me check.") + 1].startswith("🔍 Analyzing.")
    assert shown[-1] == "Found it"


def test_thinking_around_a_search_is_parted_by_a_blank_line(chat, bot, model):
    chat.storage.module_state.set(1, "llm", "thinking", "1")
    model.answer = [("thinking", "First I search."), ("tool", ""), ("tool", ""), ("thinking", "Now I know."),
                    ("answer", "Four")]
    say(chat, "2+2?")
    assert len(answers(bot)) == 1
    assert "First I search.\n\nNow I know.</blockquote>\nFour" in bot.last.text


def test_a_long_answer_comes_in_several_messages(chat, bot, model):
    model.answer = [("answer", ("a" * 3000 + "\n\n") * 3)]
    say(chat, "write a lot")
    assert len(answers(bot)) == 3
    assert loud(bot) == answers(bot)[-1:]
    assert all(len(message.text) <= llm.message_limit for message in bot.shown)


def test_the_model_output_cannot_inject_markup(chat, bot, model):
    model.answer = [("answer", "<a href='x'>click</a> **bold** `code`")]
    say(chat, "hi")
    assert bot.last.text == "&lt;a href='x'&gt;click&lt;/a&gt; <b>bold</b> <code>code</code>"


def test_a_silent_model_is_reported_and_forgotten(chat, bot, model):
    model.error = requests.ConnectionError("refused")
    say(chat, "hello")
    assert bot.last.text == "The language model did not answer 💔"
    assert stored(chat) == [(1, "user", "hello")]


def test_an_empty_answer_is_reported(chat, bot, model):
    model.answer = [("thinking", "hmm")]
    say(chat, "hello")
    assert bot.last.text == "The language model returned nothing 🤷"


def test_without_an_address_the_model_is_not_asked(app, bot, model):
    app.storage.access.allow(1, "llm", True)
    say(app, "hello")
    assert bot.last.text.endswith("\n\nThe language model is not set up 🔧")
    assert model.asked == []


def test_a_second_message_waits_for_the_first_answer(chat, bot, model):
    llm.answering.add(1)
    try:
        say(chat, "hello")
    finally:
        llm.answering.discard(1)
    assert model.asked == []
    assert bot.last.text.endswith("\n\nI am still answering your previous message, please wait a moment ⏳")


# ----- media -----

def send(app, media: dict, caption: str = "", message_id: int = 100):
    app.router.handle_message(make_message(caption, message_id=message_id, media=media))
    app.router.wait_for_tasks()


def photo(file_id: str = "photo1", size: int = 100) -> dict:
    return {'photo': [{'file_id': file_id, 'file_unique_id': file_id, 'width': 90, 'height': 60, 'file_size': size}]}


def picture(data: bytes, mime: str = "image/jpeg") -> dict:
    return {'type': "image_url", 'image_url': {'url': "data:" + mime + ";base64," + base64.b64encode(data).decode()}}


def test_a_photo_goes_to_the_model_with_its_caption(chat, bot, model):
    bot.downloads["photo1"] = b"jpeg1"
    send(chat, photo(), "what is it?")
    assert model.asked[0][-1]['content'] == [{'type': "text", 'text': "[Photo]\nwhat is it?"}, picture(b"jpeg1")]
    assert answers(bot) == ["Hello there"]


def test_a_photo_is_kept_in_the_history_as_a_short_description(chat, bot, model):
    bot.downloads["photo1"] = b"jpeg1"
    send(chat, photo())
    asked_for = model.asked[1][0]['content']
    assert asked_for[0]['text'].startswith("Describe in one or two sentences what is in this picture")
    assert asked_for[1] == picture(b"jpeg1")
    assert stored(chat) == [(1, "user", "[Photo: Hello there]"), (1, "assistant", "Hello there")]


def test_the_next_message_sees_the_description_not_the_photo(chat, bot, model):
    bot.downloads["photo1"] = b"jpeg1"
    send(chat, photo(), "what is it?")
    say(chat, "and the colour?")
    assert model.asked[-1][0] == {'role': "user", 'content': "[Photo: Hello there]\nwhat is it?"}


def test_a_location_goes_as_words(chat, bot, model):
    send(chat, {'location': {'latitude': 51.15, 'longitude': 21.65}})
    assert model.asked == [[{'role': "user", 'content': "[Location: 51.15000, 21.65000]"}]]
    assert stored(chat)[0] == (1, "user", "[Location: 51.15000, 21.65000]")


def test_a_poll_goes_as_words(chat, bot, model):
    send(chat, {'poll': {'id': "1", 'question': "Tea?", 'type': "regular", 'total_voter_count': 0,
                         'is_closed': False, 'is_anonymous': True, 'allows_multiple_answers': False,
                         'options': [{'persistent_id': "1", 'text': "Yes", 'voter_count': 0},
                                     {'persistent_id': "2", 'text': "No", 'voter_count': 0}]}})
    assert model.asked[0][-1]['content'] == "[Poll: Tea?: Yes / No]"


def test_an_animated_sticker_goes_as_its_emoji(chat, bot, model):
    send(chat, {'sticker': {'file_id': "s1", 'file_unique_id': "s1", 'type': "regular", 'width': 512,
                            'height': 512, 'is_animated': True, 'is_video': False, 'emoji': "😀"}})
    assert model.asked[0][-1]['content'] == "[Sticker: 😀]"


def test_a_text_file_is_read_into_the_message(chat, bot, model):
    bot.downloads["doc1"] = "line one\nżółw".encode()
    send(chat, {'document': {'file_id': "doc1", 'file_unique_id': "doc1", 'file_name': "notes.txt",
                             'mime_type': "text/plain", 'file_size': 15}}, "sum it up")
    assert model.asked[0][-1]['content'] == "[File: notes.txt]\nline one\nżółw\nsum it up"
    assert len(model.asked) == 1


def test_a_file_it_cannot_read_is_refused(chat, bot, model):
    bot.downloads["doc1"] = b"%PDF-1.7\0\1\2"
    send(chat, {'document': {'file_id': "doc1", 'file_unique_id': "doc1", 'file_name': "a.pdf",
                             'mime_type': "application/pdf", 'file_size': 12}})
    assert answers(bot) == ["I cannot read this kind of file yet 🤷"]
    assert model.asked == [] and stored(chat) == []


def test_a_file_too_big_to_download_is_refused(chat, bot, model):
    send(chat, photo(size=21 * 1024 * 1024))
    assert answers(bot) == ["This file is too big - Telegram lets me download at most 20 MB 📦"]
    assert model.asked == []


def test_a_file_telegram_will_not_give_is_unreadable(chat, bot, model):
    send(chat, photo("missing"))
    assert answers(bot) == ["I could not read this message 💔"]
    assert model.asked == []


def test_a_voice_message_goes_as_sound(chat, bot, model, monkeypatch):
    bot.downloads["voice1"] = b"ogg1"
    seen = []

    def convert(_ctx, data, arguments, output):
        seen.append((data, output, arguments))
        return [b"wav1"]

    monkeypatch.setattr(llm, "converted", convert)
    send(chat, {'voice': {'file_id': "voice1", 'file_unique_id': "voice1", 'duration': 4}})
    assert seen[0][:2] == (b"ogg1", "sound.wav") and "16000" in seen[0][2]
    assert model.asked[0][-1]['content'][1] == {'type': "input_audio",
                                                'input_audio': {'data': base64.b64encode(b"wav1").decode(),
                                                                'format': "wav"}}
    assert model.asked[1][0]['content'][0]['text'].startswith("Write in one or two sentences what is said")


def test_a_video_goes_as_frames_and_its_sound(chat, bot, model, monkeypatch):
    bot.downloads["video1"] = b"mp4"
    monkeypatch.setattr(llm, "converted", lambda _ctx, _data, _arguments, output:
                        [b"f1", b"f2"] if output.startswith("frame") else [b"wav1"])
    send(chat, {'video': {'file_id': "video1", 'file_unique_id': "video1", 'width': 9, 'height': 6, 'duration': 8}})
    kinds = [part['type'] for part in model.asked[0][-1]['content']]
    assert kinds == ["text", "image_url", "image_url", "input_audio"]


def test_a_video_without_sound_still_goes_as_frames(chat, bot, model, monkeypatch):
    bot.downloads["video1"] = b"mp4"

    def convert(_ctx, _data, _arguments, output):
        if output == "sound.wav":
            raise llm.Unreadable("no audio stream")
        return [b"f1"]

    monkeypatch.setattr(llm, "converted", convert)
    send(chat, {'video': {'file_id': "video1", 'file_unique_id': "video1", 'width': 9, 'height': 6, 'duration': 8}})
    assert [part['type'] for part in model.asked[0][-1]['content']] == ["text", "image_url"]


def test_a_conversion_that_fails_is_unreadable(chat, bot, model, monkeypatch):
    bot.downloads["voice1"] = b"ogg1"
    failed = SimpleNamespace(returncode=1, stderr=b"bad data")
    monkeypatch.setattr(llm.subprocess, "run", lambda *_args, **_values: failed)
    send(chat, {'voice': {'file_id': "voice1", 'file_unique_id': "voice1", 'duration': 4}})
    assert answers(bot) == ["I could not read this message 💔"]
    assert model.asked == []


def test_a_conversion_without_ffmpeg_is_unreadable(chat, bot, model, monkeypatch):
    def missing(*_args, **_values):
        raise FileNotFoundError("ffmpeg")

    bot.downloads["voice1"] = b"ogg1"
    monkeypatch.setattr(llm.subprocess, "run", missing)
    send(chat, {'voice': {'file_id': "voice1", 'file_unique_id': "voice1", 'duration': 4}})
    assert answers(bot) == ["I could not read this message 💔"]


def test_an_album_is_one_message(chat, bot, model, monkeypatch):
    monkeypatch.setattr(llm, "album_wait", 0.2)
    bot.downloads.update(photo1=b"jpeg1", photo2=b"jpeg2")
    for number, file_id in enumerate(["photo1", "photo2"]):
        chat.router.handle_message(make_message("both?" if number == 0 else "", message_id=100 + number,
                                                media=photo(file_id) | {'media_group_id': "g1"}))
    chat.router.wait_for_tasks()
    both = [{'type': "text", 'text': "[Photo]\nboth?\n[Photo]"}, picture(b"jpeg1"), picture(b"jpeg2")]
    assert model.asked[0][-1]['content'] == both
    assert len(answers(bot)) == 1


def test_a_photo_waiting_for_the_choice_is_kept(chat, bot, model):
    bot.downloads["photo1"] = b"jpeg1"
    say(chat, "first")
    last_written(chat, 30)
    send(chat, photo(), "and this?", message_id=200)
    press(chat, "llm:pick:continue:200")
    assert model.asked[-2][-1]['content'] == [{'type': "text", 'text': "[Photo]\nand this?"}, picture(b"jpeg1")]


def test_a_text_waiting_from_before_still_works(chat, bot, model):
    say(chat, "first")
    chat.storage.module_state.set(1, "llm", "pending.200", "older")
    press(chat, "llm:pick:new:200")
    assert model.asked[-1] == [{'role': "user", 'content': "older"}]


# ----- conversations -----

def test_a_message_within_fifteen_minutes_carries_on(chat, bot, model):
    say(chat, "first")
    last_written(chat, 10)
    say(chat, "second")
    assert [one['content'] for one in model.asked[-1]] == ["first", "Hello there", "second"]


def test_after_an_hour_a_new_conversation_starts_on_its_own(chat, bot, model):
    say(chat, "first")
    last_written(chat, 61)
    say(chat, "second")
    assert model.asked[-1] == [{'role': "user", 'content': "second"}]
    assert stored(chat)[-1][0] == 2


def test_between_fifteen_minutes_and_an_hour_the_person_chooses(chat, bot, model):
    say(chat, "first")
    last_written(chat, 30)
    say(chat, "second", message_id=200)
    assert len(model.asked) == 1
    assert bot.last.text.endswith("Your last message was 30 minutes ago. "
                                  "Carry on with that conversation or start a new one?")
    assert [data for _, data in bot.last.buttons][:2] == ["llm:pick:continue:200", "llm:pick:new:200"]


def test_carrying_on_keeps_the_history(chat, bot, model):
    say(chat, "first")
    last_written(chat, 30)
    say(chat, "second", message_id=200)
    press(chat, "llm:pick:continue:200")
    assert [one['content'] for one in model.asked[-1]] == ["first", "Hello there", "second"]
    assert chat.storage.navigation.current(1) is None


def test_starting_anew_forgets_the_history(chat, bot, model):
    say(chat, "first")
    last_written(chat, 30)
    say(chat, "second", message_id=200)
    press(chat, "llm:pick:new:200")
    assert model.asked[-1] == [{'role': "user", 'content': "second"}]


def test_a_choice_is_used_only_once(chat, bot, model):
    say(chat, "first")
    last_written(chat, 30)
    say(chat, "second", message_id=200)
    choice = bot.last.message_id
    press(chat, "llm:pick:new:200")
    chat.router.handle_callback(make_callback("llm:pick:new:200", message_id=choice))
    chat.router.wait_for_tasks()
    assert len(model.asked) == 2


def test_the_new_conversation_button_starts_over(chat, bot, model):
    say(chat, "first")
    say(chat, "/llm")
    press(chat, "llm:fresh")
    say(chat, "second")
    assert model.asked[-1] == [{'role': "user", 'content': "second"}]


def test_the_history_keeps_to_its_size(chat, bot, model, monkeypatch):
    monkeypatch.setattr(llm, "history_characters", 25)
    for text in ["a" * 10, "b" * 10, "c" * 10]:
        say(chat, text)
    assert [one['content'] for one in model.asked[-1]] == ["Hello there", "c" * 10]


# ----- settings -----

def test_the_command_explains_and_leads_to_the_settings(chat, bot, model):
    say(chat, "/llm")
    assert "every message that is neither a command nor a link" in bot.last.text
    assert ("⚙️ Settings", "core:settings:llm") in bot.last.buttons


def test_thinking_is_switched_in_the_settings(chat, bot, model):
    say(chat, "/settings")
    press(chat, "core:settings:llm")
    assert "Thinking: <i>⚡ Without thinking</i>" in bot.last.text
    press(chat, "llm:thinking_mode")
    assert [data for _, data in bot.last.buttons][:2] == ["llm:thinking:0", "llm:thinking:1"]
    press(chat, "llm:thinking:1")
    assert "Thinking: <i>💭 With thinking</i>" in bot.last.text
    assert chat.storage.module_state.get(1, "llm", "thinking") == "1"


def test_an_unknown_thinking_choice_is_refused(chat, bot, model):
    say(chat, "/settings")
    press(chat, "core:settings:llm")
    press(chat, "llm:thinking:2")
    assert chat.storage.module_state.get(1, "llm", "thinking") is None


# ----- history -----

def add_conversation(app, number: int, text: str, days_ago: float = 0, user_id: int = 1) -> None:
    app.storage.users.save(user_id, "First", "Last", "user" + str(user_id))
    moment = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
    for role, content in [("user", text), ("assistant", "Answer to " + text)]:
        app.storage.database.execute(
            "INSERT INTO " + app.storage.for_module("llm").table("messages") +
            " (user_id, conversation, role, content, created_at) VALUES (?, ?, ?, ?, ?);",
            (user_id, number, role, content, moment))


def conversations_of(app, user_id: int = 1) -> list[int]:
    return [row['conversation'] for row in app.storage.database.query_all(
        "SELECT DISTINCT conversation FROM " + app.storage.for_module("llm").table("messages") +
        " WHERE user_id = ? ORDER BY conversation;", (user_id,))]


def labels(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def forget_old(app) -> None:
    llm.forget_old(JobCtx(app.services, app.registry.get("llm")))


def test_the_menu_leads_to_the_history(chat, bot, model):
    say(chat, "/llm")
    assert ("📜 Conversation history", "llm:history") in bot.last.buttons


def test_an_empty_history_says_so(chat, bot, model):
    say(chat, "/llm")
    press(chat, "llm:history")
    assert "You have no conversations yet" in bot.last.text


def test_the_history_lists_conversations_newest_first(chat, bot, model):
    say(chat, "first question")
    say(chat, "/llm")
    press(chat, "llm:fresh")
    say(chat, "second question")
    say(chat, "/llm")
    press(chat, "llm:history")
    found = labels(bot)
    assert "second question" in found[0] and "first question" in found[1]
    assert bot.last.buttons[0][1] == "llm:one:2"
    assert "Page <i>1</i> of <i>1</i>, <i>2</i> in total" in bot.last.text


def test_a_long_first_question_is_shortened_on_its_button(chat, bot, model):
    add_conversation(chat, 1, "word " * 30)
    say(chat, "/llm")
    press(chat, "llm:history")
    assert labels(bot)[0].endswith("…") and len(labels(bot)[0]) < 70


def test_the_history_is_split_into_pages(chat, bot, model):
    for number in range(1, 11):
        add_conversation(chat, number, "question " + str(number))
    say(chat, "/llm")
    press(chat, "llm:history")
    assert len([data for _, data in bot.last.buttons if data.startswith("llm:one:")]) == 8
    press(chat, "llm:history:1")
    assert [data for _, data in bot.last.buttons if data.startswith("llm:one:")] == ["llm:one:2", "llm:one:1"]


def test_a_conversation_shows_what_it_was_about(chat, bot, model):
    say(chat, "hello")
    press(chat, "llm:one:1")
    assert "Messages: <i>2</i>" in bot.last.text
    assert "First question: <i>hello</i>" in bot.last.text
    assert [data for _, data in bot.last.buttons][:3] == ["llm:resume:1", "llm:export:1", "llm:delete:1"]


def test_the_first_question_cannot_inject_markup(chat, bot, model):
    add_conversation(chat, 1, "<b>bold</b> & co")
    press(chat, "llm:one:1")
    assert "&lt;b&gt;bold&lt;/b&gt; &amp; co" in bot.last.text


def test_resuming_carries_on_an_older_conversation(chat, bot, model):
    add_conversation(chat, 1, "old question", days_ago=3)
    add_conversation(chat, 2, "newer question", days_ago=1)
    press(chat, "llm:resume:1")
    assert "Back to this conversation" in bot.last.text
    say(chat, "more")
    assert [one['content'] for one in model.asked[-1]] == ["old question", "Answer to old question", "more"]
    assert conversations_of(chat) == [1, 2]


def test_a_new_conversation_after_resuming_takes_a_new_number(chat, bot, model):
    add_conversation(chat, 1, "old question", days_ago=3)
    add_conversation(chat, 2, "newer question", days_ago=1)
    press(chat, "llm:resume:1")
    press(chat, "llm:fresh")
    say(chat, "brand new")
    assert model.asked[-1] == [{'role': "user", 'content': "brand new"}]
    assert conversations_of(chat) == [1, 2, 3]


def test_a_conversation_is_downloaded_as_a_file(chat, bot, model, monkeypatch):
    sent = []
    monkeypatch.setattr(Ctx, "send_file", lambda _ctx, path, _kind="document", _caption="": sent.append(
        (Path(path).name, Path(path).read_text(encoding="utf-8"))))
    say(chat, "zażółć")
    press(chat, "llm:export:1")
    name, content = sent[0]
    assert name.endswith(".txt") and "Conversation " in name
    assert "You\nzażółć" in content and "Assistant\nHello there" in content
    assert content.index("zażółć") < content.index("Hello there")


def test_deleting_a_conversation_asks_first(chat, bot, model):
    add_conversation(chat, 1, "first")
    add_conversation(chat, 2, "second")
    press(chat, "llm:delete:1")
    assert "Are you sure you want to delete this conversation?" in bot.last.text
    assert conversations_of(chat) == [1, 2]
    press(chat, "llm:delete_confirmed:1")
    assert conversations_of(chat) == [2]
    assert bot.last.text.endswith("The conversation has been deleted ✅")


def test_after_deleting_the_current_conversation_the_next_message_starts_anew(chat, bot, model):
    say(chat, "hello")
    press(chat, "llm:delete_confirmed:1")
    say(chat, "again")
    assert model.asked[-1] == [{'role': "user", 'content': "again"}]


@pytest.mark.parametrize("data", ["llm:delete_confirmed:1", "llm:wipe_confirmed"])
def test_nobody_is_asked_about_a_conversation_that_is_gone(chat, bot, model, data):
    say(chat, "hello")
    last_written(chat, 30)
    press(chat, data)
    say(chat, "again")
    assert "Carry on with that conversation" not in bot.last.text
    assert model.asked[-1] == [{'role': "user", 'content': "again"}]


def test_a_deleted_conversation_cannot_be_opened(chat, bot, model):
    press(chat, "llm:one:7")
    assert bot.last.text.endswith("This conversation is not here anymore 💔")


@pytest.mark.parametrize("data", ["llm:one:5", "llm:resume:5", "llm:export:5", "llm:delete:5",
                                  "llm:delete_confirmed:5"])
def test_nobody_reaches_a_conversation_of_someone_else(chat, bot, model, data):
    add_conversation(chat, 5, "secret", user_id=2)
    press(chat, data)
    assert bot.last.text.endswith("This conversation is not here anymore 💔")
    assert conversations_of(chat, user_id=2) == [5]
    assert bot.files == []
    assert chat.storage.module_state.get(1, "llm", "conversation") is None


def test_the_same_number_of_someone_else_stays_out_of_sight(chat, bot, model, monkeypatch):
    sent = []
    monkeypatch.setattr(Ctx, "send_file", lambda _ctx, path, _kind="document", _caption="": sent.append(
        Path(path).read_text(encoding="utf-8")))
    add_conversation(chat, 1, "secret", user_id=2)
    add_conversation(chat, 1, "mine")
    press(chat, "llm:one:1")
    assert "First question: <i>mine</i>" in bot.last.text and "Messages: <i>2</i>" in bot.last.text
    press(chat, "llm:export:1")
    assert "mine" in sent[0] and "secret" not in sent[0]
    press(chat, "llm:delete_confirmed:1")
    assert conversations_of(chat, user_id=2) == [1]


@pytest.mark.parametrize("data", ["llm:history", "llm:one:1", "llm:export:1", "llm:delete_confirmed:1",
                                  "llm:wipe_confirmed", "llm:keep:7", "llm:resume:1"])
def test_without_access_no_history_button_reaches_the_module(app, bot, model, data):
    add_conversation(app, 1, "secret")
    app.storage.access.allow(1, "llm", False)
    app.router.handle_callback(make_callback(data))
    app.router.wait_for_tasks()
    assert bot.last.text.startswith("You do not have access to")
    assert conversations_of(app) == [1]
    assert bot.files == []


# ----- keeping and wiping -----

def test_wiping_the_whole_history_asks_first(chat, bot, model):
    add_conversation(chat, 1, "first")
    add_conversation(chat, 2, "second")
    add_conversation(chat, 3, "theirs", user_id=2)
    say(chat, "/settings")
    press(chat, "core:settings:llm")
    press(chat, "llm:wipe")
    assert "Are you sure you want to delete all your conversations?" in bot.last.text
    assert "Conversations: <i>2</i>" in bot.last.text
    assert conversations_of(chat) == [1, 2]
    press(chat, "llm:wipe_confirmed")
    assert conversations_of(chat) == []
    assert conversations_of(chat, user_id=2) == [3]
    assert bot.last.text.endswith("The whole conversation history has been deleted ✅")


def test_wiping_an_empty_history_offers_nothing(chat, bot, model):
    press(chat, "llm:wipe")
    assert "You have no conversations yet" in bot.last.text
    assert "llm:wipe_confirmed" not in [data for _, data in bot.last.buttons]


def test_after_wiping_the_next_message_starts_anew(chat, bot, model):
    say(chat, "hello")
    press(chat, "llm:wipe_confirmed")
    say(chat, "again")
    assert model.asked[-1] == [{'role': "user", 'content': "again"}]


def test_the_history_is_kept_for_ninety_days_by_default(chat, bot, model):
    say(chat, "/settings")
    press(chat, "core:settings:llm")
    assert "Deleting old conversations: <i>After 90 days</i>" in bot.last.text


def test_the_time_of_keeping_is_chosen_in_the_settings(chat, bot, model):
    say(chat, "/settings")
    press(chat, "core:settings:llm")
    press(chat, "llm:keeping")
    assert [data for _, data in bot.last.buttons][:4] == ["llm:keep:0", "llm:keep:7", "llm:keep:30", "llm:keep:90"]
    press(chat, "llm:keep:7")
    assert "Deleting old conversations: <i>After 7 days</i>" in bot.last.text
    press(chat, "llm:keep:0")
    assert "Deleting old conversations: <i>Never</i>" in bot.last.text


def test_an_unknown_time_of_keeping_is_refused(chat, bot, model):
    press(chat, "llm:keep:5")
    say(chat, "/settings")
    press(chat, "core:settings:llm")
    assert "After 90 days" in bot.last.text


def test_old_conversations_are_forgotten(chat, bot, model):
    add_conversation(chat, 1, "too old", days_ago=91)
    add_conversation(chat, 2, "recent enough", days_ago=89)
    forget_old(chat)
    assert conversations_of(chat) == [2]


def test_everyone_is_forgotten_after_their_own_time(chat, bot, model):
    add_conversation(chat, 1, "a week and a day", days_ago=8, user_id=2)
    add_conversation(chat, 1, "ages ago", days_ago=400, user_id=3)
    llm_settings = chat.storage.for_module("llm").table("settings")
    chat.storage.database.execute("INSERT INTO " + llm_settings + " (user_id, keep_days) VALUES (2, 7), (3, 0);")
    forget_old(chat)
    assert conversations_of(chat, user_id=2) == []
    assert conversations_of(chat, user_id=3) == [1]


def test_a_conversation_counts_from_its_last_message(chat, bot, model):
    add_conversation(chat, 1, "started long ago", days_ago=100)
    add_conversation(chat, 1, "still going", days_ago=1)
    forget_old(chat)
    assert conversations_of(chat) == [1]


# ----- the wire -----

class Response:
    def __init__(self, lines: list[str]):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        pass

    def iter_lines(self):
        return iter(line.encode("utf-8") for line in self.lines)


def wire(chat, monkeypatch, lines: list[str], thinking: bool = True) -> tuple[dict, list]:
    sent = {}

    def post(url, **options):
        sent.update(url=url, **options)
        return Response(lines)

    monkeypatch.setattr("modules.external.llm.module.requests.post", post)
    ctx = Ctx(chat.services, chat.registry.get("llm"), User(1, "First", "Last", "username", Role.GUEST, "en", True))
    return sent, list(real_stream(ctx, [{'role': "user", 'content': "hi"}], thinking))


def test_the_stream_is_read_as_server_sent_events(chat, monkeypatch):
    sent, pieces = wire(chat, monkeypatch, ['data: {"choices":[{"delta":{"reasoning_content":"so"}}]}', "",
                                            'data: {"choices":[{"delta":{"content":"Hi"}}]}', "data: [DONE]",
                                            'data: {"choices":[{"delta":{"content":"never"}}]}'])
    assert pieces == [("thinking", "so"), ("answer", "Hi")]
    assert sent['url'] == "http://model.local/v1/chat/completions"
    assert sent['json']['model'] == "small" and sent['json']['stream'] is True
    assert sent['json']['chat_template_kwargs'] == {'enable_thinking': True}
    assert "reasoning_effort" not in sent['json']


def test_thinking_off_is_asked_for_in_both_ways(chat, monkeypatch):
    sent, _ = wire(chat, monkeypatch, ["data: [DONE]"], thinking=False)
    assert sent['json']['chat_template_kwargs'] == {'enable_thinking': False}
    assert sent['json']['reasoning_effort'] == "none"


def test_a_stream_with_tool_events_and_reasoning_is_read_too(chat, monkeypatch):
    _, pieces = wire(chat, monkeypatch, [
        'data: {"choices":[{"delta":{"reasoning":"so"}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"search"}}]}}]}',
        'data: {"type":"mcp_tool_result","name":"search","result":"Hi"}',
        'data: {"choices":[{"delta":{"content":"Hi"}}]}', "data: [DONE]"])
    assert pieces == [("thinking", "so"), ("tool", ""), ("tool", ""), ("answer", "Hi")]


def test_the_stream_is_read_as_utf_8_whatever_the_server_claims(chat, monkeypatch):
    _, pieces = wire(chat, monkeypatch, ['data: {"choices":[{"delta":{"content":"Paryż, łódź, ćma"}}]}'])
    assert pieces == [("answer", "Paryż, łódź, ćma")]


def test_no_key_is_sent_when_none_is_set(chat, monkeypatch):
    sent, _ = wire(chat, monkeypatch, ["data: [DONE]"])
    assert sent['headers'] == {}


def test_a_key_is_sent_when_one_is_set(chat, monkeypatch):
    configure(chat, monkeypatch, {'llm_key': "not-a-real-key"}, llm_url="http://model.local/v1", llm_model="small")
    sent, _ = wire(chat, monkeypatch, ["data: [DONE]"])
    assert sent['headers'] == {'Authorization': "Bearer not-a-real-key"}


def test_a_broken_line_from_the_server_counts_as_no_answer(chat, bot, monkeypatch):
    monkeypatch.setattr(llm, "stream", real_stream)
    monkeypatch.setattr("modules.external.llm.module.requests.post",
                        lambda *_args, **_values: Response(["data: {not json"]))
    say(chat, "hello")
    assert bot.last.text == "The language model did not answer 💔"


def test_our_tool_calls_are_gathered_when_the_round_ends_for_them(chat, monkeypatch):
    sent, pieces = wire(chat, monkeypatch, [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_7","type":"function",'
        '"function":{"name":"reminder_add","arguments":"{\\"content\\": \\"Buy"}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":" milk\\"}"}}]}}]}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":1,"function":{"name":"reminder_list"}}]}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}', "data: [DONE]"])
    first, second = pieces[-1][1]
    assert first == {'id': "call_7", 'name': "reminder_add", 'arguments': '{"content": "Buy milk"}'}
    assert second['id'].startswith("call_") and (second['name'], second['arguments']) == ("reminder_list", "")
    assert pieces[:-1] == [("tool", "")] * 3


def test_a_tool_call_without_an_index_is_still_read(chat, monkeypatch):
    _, pieces = wire(chat, monkeypatch, [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":null,"id":"c1","function":{"name":"reminder_list",'
        '"arguments":"{}"}}]},"finish_reason":"tool_calls"}]}', "data: [DONE]"])
    assert pieces[-1] == ("calls", [{'id': "c1", 'name': "reminder_list", 'arguments': "{}"}])


def test_tool_calls_of_the_server_itself_are_never_handed_over(chat, monkeypatch):
    _, pieces = wire(chat, monkeypatch, [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"s1","function":{"name":"search",'
        '"arguments":"{}"}}]},"finish_reason":"tool_calls"}]}',
        'data: {"type":"mcp_tool_result","name":"search","result":"Hi"}',
        'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":"stop"}]}', "data: [DONE]"])
    assert pieces == [("tool", ""), ("tool", ""), ("answer", "Hi")]


def test_tool_calls_count_only_when_the_round_ends_for_them(chat, monkeypatch):
    _, pieces = wire(chat, monkeypatch, [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","function":{"name":"reminder_list"}}]}}]}',
        'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":"stop"}]}', "data: [DONE]"])
    assert [kind for kind, _ in pieces] == ["tool", "answer"]


def test_tools_are_sent_only_when_there_are_some(chat, monkeypatch):
    sent = {}

    def post(_url, **options):
        sent.clear()
        sent.update(options['json'])
        return Response(["data: [DONE]"])

    monkeypatch.setattr("modules.external.llm.module.requests.post", post)
    ctx = Ctx(chat.services, chat.registry.get("llm"), User(1, "First", "Last", "username", Role.GUEST, "en", True))
    list(real_stream(ctx, [], False, [{'type': "function"}]))
    assert sent['tools'] == [{'type': "function"}]
    list(real_stream(ctx, [], False, []))
    assert "tools" not in sent


# ----- the assistant -----

def calls(*wanted: tuple[str, dict | str]) -> list[tuple]:
    return [("tool", ""), ("calls", [{'id': "call_" + str(number), 'name': name,
                                      'arguments': given if isinstance(given, str) else json.dumps(given)}
                                     for number, (name, given) in enumerate(wanted)])]


def reminders(app, user_id: int = 1) -> list[tuple[str, str]]:
    return [(row['content'], row['date']) for row in app.storage.database.query_all(
        "SELECT * FROM " + app.storage.for_module("reminder").table("reminders") + " WHERE user_id = ? ORDER BY id;",
        (user_id,))]


def tomorrow() -> str:
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d") + " 15:00"


def results(model, request: int = 1) -> list[dict]:
    return [json.loads(one['content']) for one in model.asked[request] if one['role'] == "tool"]


def tool_names(model, request: int = 0) -> list[str]:
    return [tool['function']['name'] for tool in model.tools[request] or []]


def add_reminder(model, content: str = "Collect the results", date: str = "") -> None:
    model.script = [calls(("reminder_add", {'content': content, 'date': date or tomorrow()})), []]


def test_the_system_prompt_tells_the_modules_the_user_and_the_time(chat, bot, model):
    say(chat, "hello")
    system = model.systems[0]
    assert "/reminder - 🔔 Reminders - Reminds you about anything at the time you set" in system
    assert "/llm" not in system and "/admin" not in system
    assert "The user: First Last, 🇬🇧 English" in system
    assert "Now it is" not in system
    assert model.asked[0] == [{'role': "user", 'content': "hello"}]


def test_the_time_comes_with_the_message_and_stays_out_of_the_history(chat, bot, model):
    say(chat, "hello")
    assert model.clocks[0].startswith("[Now it is: " + datetime.now().strftime("%Y-%m-%d"))
    assert model.clocks[0].endswith(")]\n")
    assert stored(chat)[0] == (1, "user", "hello")
    say(chat, "again")
    assert len(model.clocks) == 2


def test_the_time_comes_with_a_photo_too(chat, bot, model):
    bot.downloads["photo1"] = b"jpeg1"
    send(chat, photo(), "what is it?")
    assert model.clocks[0].startswith("[Now it is: ")
    assert model.asked[0][-1]['content'][0] == {'type': "text", 'text': "[Photo]\nwhat is it?"}


def test_the_configured_prompt_comes_first(chat, bot, model, monkeypatch):
    configure(chat, monkeypatch, llm_url="http://model.local/v1", llm_model="small", llm_prompt="You are Gemma.\n")
    say(chat, "hello")
    system = model.systems[0]
    assert system.startswith("You are Gemma.\n\nModules of this Telegram bot")


def test_the_prompt_is_in_the_language_of_the_user(chat, bot, model):
    chat.storage.settings.set_language(1, "pl")
    say(chat, "cześć")
    assert "Użytkownik: First Last, 🇵🇱 Polski" in model.systems[0]
    assert "/reminder - 🔔 Przypomnienia - " in model.systems[0]


def test_the_actions_go_as_tools(chat, bot, model):
    say(chat, "hello")
    assert tool_names(model) == ["reminder_add", "reminder_list", "reminder_edit", "reminder_delete"]
    adding = not_none(model.tools[0])[0]['function']
    assert adding['description'] == "Sets a reminder for the user, who confirms it with a button"
    assert adding['parameters'] == {
        'type': "object", 'required': ["content", "date"],
        'properties': {'content': {'type': "string", 'description': "What to remind about, up to 200 characters"},
                       'date': {'type': "string",
                                'description': "When to remind, in the local time, as YYYY-MM-DD HH:MM or "
                                               "DD.MM.YYYY HH:MM"}}}
    assert "With the tools you act in these modules" in model.systems[0]
    editing = not_none(model.tools[0])[2]['function']['parameters']
    assert list(editing['properties']) == ["reminder_id", "content", "date"]
    assert editing['required'] == ["reminder_id"]


def test_an_edit_leaves_out_what_stays_the_same(chat, bot, model):
    table = chat.storage.for_module("reminder").table("reminders")
    chat.storage.database.execute("INSERT INTO " + table + " (user_id, date, content) VALUES (1, ?, 'Buy milk');",
                                  (tomorrow(),))
    model.script = [calls(("reminder_edit", {'reminder_id': 1, 'content': "Buy bread"})), [("answer", "Confirm.")]]
    say(chat, "bread, not milk")
    press(chat, "llm:confirm:" + pending_key(chat))
    assert reminders(chat) == [("Buy bread", tomorrow())]


def test_the_context_of_the_modules_goes_into_the_prompt(chat, bot, model):
    model.script = [calls(("reminder_add", {'content': "Collect <the> results", 'date': tomorrow()})),
                    [("answer", "Confirm.")]]
    say(chat, "remind me")
    press(chat, "llm:confirm:" + pending_key(chat))
    say(chat, "what is next?")
    assert "What the modules know about the user:\n[🔔 Reminders]\nThe next reminders:\n" + tomorrow() + \
        " - Collect <the> results" in model.systems[-1]


def test_a_read_only_action_runs_and_its_result_goes_back(chat, bot, model):
    chat.storage.database.execute("INSERT INTO " + chat.storage.for_module("reminder").table("reminders") +
                                  " (user_id, date, content) VALUES (1, ?, 'Buy milk');", (tomorrow(),))
    model.script = [calls(("reminder_list", "")), [("answer", "You have one.")]]
    say(chat, "what reminders do I have?")
    assert len(model.asked) == 2
    assert model.asked[1][-2] == {'role': "assistant", 'content': None,
                                  'tool_calls': [{'id': "call_0", 'type': "function",
                                                  'function': {'name': "reminder_list", 'arguments': "{}"}}]}
    assert model.asked[1][-1]['tool_call_id'] == "call_0" and model.asked[1][-1]['name'] == "reminder_list"
    listed = [{'reminder_id': 1, 'date': tomorrow(), 'content': "Buy milk", 'is_sent': False}]
    assert results(model) == [{'status': "done", 'result': listed}]
    assert answers(bot) == ["You have one."]


def test_a_call_to_a_tool_that_is_not_ours_is_left_alone(chat, bot, model):
    model.script = [calls(("search", {'query': "x"})) + [("answer", "Found it")]]
    say(chat, "look it up")
    assert len(model.asked) == 1
    assert answers(bot) == ["Found it"]


def test_text_before_our_tool_stays_in_its_own_message(chat, bot, model):
    model.script = [[("answer", "Let me check.")] + calls(("reminder_list", {})), [("answer", "Nothing there.")]]
    say(chat, "anything?")
    assert answers(bot) == ["Let me check.", "Nothing there."]
    assert loud(bot) == ["Nothing there."]


def pending_key_or_none(app) -> str | None:
    return next((key for key in app.storage.module_state.get_all(1, "llm") if key.startswith("action.")), None)


def pending_key(app) -> str:
    return not_none(pending_key_or_none(app))[len("action."):]


def test_adding_a_reminder_waits_for_the_buttons(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow at 3 pm to collect the results")
    assert len(model.asked) == 2 and model.tools[1] is None
    assert reminders(chat) == []
    asked = bot.sent[-1]
    assert asked.text == ("<b>🔔 Reminders:</b>\n\nDo you want me to set this reminder?\nContent: <i>Collect the "
                          "results</i>\nDate: <i>" + tomorrow() + "</i>")
    key = pending_key(chat)
    assert asked.buttons == [("✅ Yes", "llm:confirm:" + key), ("❌ No", "llm:cancel:" + key)]
    assert answers(bot)[-2] == "Confirm it with the buttons below 👇"
    assert loud(bot) == [asked.text]


def test_yes_sets_the_reminder_and_says_so_in_place(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    asked = bot.sent[-1].message_id
    press(chat, "llm:confirm:" + pending_key(chat))
    assert reminders(chat) == [("Collect the results", tomorrow())]
    assert bot.edited[-1].message_id == asked and bot.edited[-1].markup is None
    assert bot.edited[-1].text == ("<b>🔔 Reminders:</b>\n\nThe reminder has been set ✅\nContent: <i>Collect the "
                                   "results</i>\nDate: <i>" + tomorrow() + "</i>")
    assert pending_key_or_none(chat) is None


def test_no_cancels_and_sets_nothing(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    press(chat, "llm:cancel:" + pending_key(chat))
    assert reminders(chat) == []
    assert bot.edited[-1].text.endswith("</i>\n\nCancelled ❌")
    assert pending_key_or_none(chat) is None


def test_a_button_works_only_once(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    key = pending_key(chat)
    press(chat, "llm:confirm:" + key)
    chat.router.handle_callback(make_callback("llm:confirm:" + key, message_id=bot.sent[-1].message_id))
    chat.router.wait_for_tasks()
    assert len(reminders(chat)) == 1
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"


def test_yes_checks_everything_again(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    key = pending_key(chat)
    pending = json.loads(chat.storage.module_state.get(1, "llm", "action." + key))
    pending['arguments']['date'] = "2020-01-01 10:00"
    chat.storage.module_state.set(1, "llm", "action." + key, json.dumps(pending))
    press(chat, "llm:confirm:" + key)
    assert reminders(chat) == []
    assert bot.edited[-1].text.startswith("<b>🔔 Reminders:</b>\n\nThis moment has already passed")


def test_a_reminder_deleted_meanwhile_cannot_be_deleted_by_yes(chat, bot, model):
    table = chat.storage.for_module("reminder").table("reminders")
    chat.storage.database.execute("INSERT INTO " + table + " (user_id, date, content) VALUES (1, ?, 'Buy milk');",
                                  (tomorrow(),))
    model.script = [calls(("reminder_delete", {'reminder_id': 1})), [("answer", "Confirm.")]]
    say(chat, "delete the milk one")
    assert bot.sent[-1].text.startswith("<b>🔔 Reminders:</b>\n\nDo you really want to delete this reminder?")
    chat.storage.database.execute("DELETE FROM " + table + ";")
    press(chat, "llm:confirm:" + pending_key(chat))
    assert bot.edited[-1].text == ("<b>🔔 Reminders:</b>\n\nThere is no such reminder - it may have been deleted or "
                                   "the number is wrong")


def test_a_wrong_value_goes_back_to_the_model_to_ask_again(chat, bot, model):
    model.script = [calls(("reminder_add", {'content': "Results", 'date': "tomorrow at 3"})),
                    [("answer", "When exactly?")]]
    say(chat, "remind me tomorrow")
    problem = results(model)[0]
    assert problem['status'] == "refused"
    assert problem['problem'].startswith("I do not understand this date, write it like ")
    assert pending_key_or_none(chat) is None and reminders(chat) == []
    assert answers(bot) == ["When exactly?"]


@pytest.mark.parametrize("given", ["{not json", '["Results"]', {'content': "Results"}])
def test_arguments_the_action_cannot_take_go_back_too(chat, bot, model, given):
    model.script = [calls(("reminder_add", given)), [("answer", "Sorry.")]]
    say(chat, "remind me")
    problem = "These arguments do not fit, the action takes content (string), date (string)"
    assert results(model) == [{'status': "refused", 'problem': problem}]


def test_without_access_to_a_module_its_actions_and_context_stay_away(chat, bot, model):
    chat.storage.access.allow(1, "reminder", False)
    model.script = [calls(("reminder_list", {})), [("answer", "No.")]]
    say(chat, "list them")
    assert tool_names(model) == []
    assert "/reminder" not in model.systems[0] and "With the tools" not in model.systems[0]
    assert len(model.asked) == 1


def test_access_taken_away_before_yes_stops_the_action(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    chat.storage.access.allow(1, "reminder", False)
    press(chat, "llm:confirm:" + pending_key(chat))
    assert reminders(chat) == []
    assert bot.edited[-1].text.endswith("The Bot has no such action for you")


def test_a_module_switched_off_in_the_settings_gives_nothing(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    press(chat, "llm:confirm:" + pending_key(chat))
    say(chat, "/settings")
    press(chat, "core:settings:llm")
    press(chat, "llm:modules")
    assert bot.last.buttons[0] == ("✅ 🔔 Reminders", "llm:share:reminder")
    press(chat, "llm:share:reminder")
    assert bot.last.buttons[0] == ("⬜ 🔔 Reminders", "llm:share:reminder")
    say(chat, "what is next?")
    assert tool_names(model, -1) == [] and "The next reminders" not in model.systems[-1]
    press(chat, "llm:share:reminder")
    say(chat, "and now?")
    assert tool_names(model, -1) == ["reminder_add", "reminder_list", "reminder_edit", "reminder_delete"]
    assert "The next reminders" in model.systems[-1]


def test_only_a_module_with_something_for_the_assistant_can_be_switched(chat, bot, model):
    press(chat, "llm:share:crystalball")
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"
    assert chat.storage.module_state.get(1, "llm", "off.crystalball") is None


def test_the_rounds_of_tools_are_capped(chat, bot, model):
    model.answer = calls(("reminder_list", {}))
    say(chat, "loop")
    assert len(model.asked) == llm.tool_rounds + 1
    assert [bool(tools) for tools in model.tools] == [True] * llm.tool_rounds + [False]
    assert answers(bot) == ["The language model returned nothing 🤷"]


def acted(app) -> list[tuple[str, dict, dict]]:
    return [(done['tool'], done['arguments'], done['said']) for done in
            (json.loads(content) for _, role, content in stored(app) if role == "action")]


def test_the_history_keeps_each_action_with_its_result(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    question = "Do you want me to set this reminder?\nContent: Collect the results\nDate: " + tomorrow()
    wanted = {'content': "Collect the results", 'date': tomorrow()}
    assert acted(chat) == [("reminder_add", wanted, {'status': "pending_confirmation", 'summary': question})]
    assert [role for _, role, _ in stored(chat)] == ["user", "action"]
    press(chat, "llm:confirm:" + pending_key(chat))
    assert acted(chat)[-1] == ("reminder_add", wanted, {'status': "confirmed", 'result': "The reminder has been set "
                                                        "✅\nContent: Collect the results\nDate: " + tomorrow()})


def test_the_model_sees_past_actions_as_its_own_tool_calls(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    press(chat, "llm:confirm:" + pending_key(chat))
    say(chat, "thanks")
    replayed = model.asked[-1][1:-1]
    assert [message['role'] for message in replayed] == ["assistant", "tool", "assistant", "tool"]
    first, result = replayed[0], replayed[1]
    assert first['content'] is None
    assert first['tool_calls'][0]['function'] == {'name': "reminder_add", 'arguments': json.dumps(
        {'content': "Collect the results", 'date': tomorrow()})}
    assert result['tool_call_id'] == first['tool_calls'][0]['id'] and result['name'] == "reminder_add"
    assert json.loads(result['content'])['status'] == "pending_confirmation"
    assert json.loads(replayed[3]['content'])['status'] == "confirmed"
    assert not any("[reminder_add" in str(message.get('content', "")) for message in model.asked[-1])


def test_a_cancelled_action_is_kept_too(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    press(chat, "llm:cancel:" + pending_key(chat))
    assert acted(chat)[-1][2] == {'status': "cancelled", 'summary': "Do you want me to set this reminder?\nContent: "
                                                                    "Collect the results\nDate: " + tomorrow()}


def test_an_action_without_an_answer_points_to_the_buttons(chat, bot, model):
    model.script = [calls(("reminder_add", {'content': "Results", 'date': tomorrow()})), []]
    say(chat, "remind me tomorrow")
    assert answers(bot)[-2] == "Confirm it with the buttons below 👇"
    assert [role for _, role, _ in stored(chat)] == ["user", "action"]


def test_an_action_done_before_a_failure_is_still_kept_and_offered(chat, bot, model, monkeypatch):
    def failing(_ctx, messages, _thinking, _tools=None):
        if messages[-1]['role'] == "tool":
            raise requests.ConnectionError("refused")
        yield from calls(("reminder_list", {}), ("reminder_add", {'content': "Results", 'date': tomorrow()}))

    monkeypatch.setattr(llm, "stream", failing)
    say(chat, "remind me tomorrow")
    assert answers(bot)[-2] == "The language model did not answer 💔"
    assert bot.sent[-1].buttons[0][1].startswith("llm:confirm:")
    statuses = [(tool, said['status']) for tool, _, said in acted(chat)]
    assert statuses == [("reminder_list", "done"), ("reminder_add", "pending_confirmation")]


def talker(app) -> Ctx:
    return Ctx(app.services, app.registry.get("llm"), User(1, "First", "Last", "username", Role.GUEST, "en", True))


def test_actions_count_neither_as_messages_nor_as_the_opening(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    row = not_none(llm.conversation_of(talker(chat), 1))
    assert (row['total'], row['opening']) == (1, "remind me tomorrow")


def test_the_exported_file_reads_an_action_plainly(chat, bot, model):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    text = llm.transcript(talker(chat), 1)
    assert "Assistant's action\n[reminder_add - pending_confirmation: Do you want me to set this reminder? " in text


def test_a_module_with_actions_only_for_admins_is_not_offered_to_switch(chat, bot, model, monkeypatch):
    found: Module = not_none(chat.registry.get("reminder"))
    monkeypatch.setattr(found, "actions", [replace(action, role=Role.ADMIN) for action in found.actions])
    monkeypatch.setattr(found, "summary", None)
    press(chat, "llm:modules")
    assert "llm:share:reminder" not in [data for _, data in bot.last.buttons]
    assert bot.last.text.endswith("None of your modules has anything for the assistant")


def test_the_same_action_asked_twice_in_one_answer_is_confirmed_once(chat, bot, model):
    wanted = {'content': "Results", 'date': tomorrow()}
    model.script = [calls(("reminder_add", wanted), ("reminder_add", dict(reversed(wanted.items())))), []]
    say(chat, "remind me tomorrow")
    assert len(model.asked) == 2
    assert len([message for message in bot.sent if message.buttons]) == 1
    assert len([key for key in chat.storage.module_state.get_all(1, "llm") if key.startswith("action.")]) == 1


def test_the_same_reminder_written_a_little_differently_is_confirmed_once(chat, bot, model):
    model.script = [calls(("reminder_add", {'content': "Results", 'date': tomorrow()})),
                    calls(("reminder_add", {'content': " Results ", 'date': tomorrow()})),
                    [("answer", "Confirm.")]]
    say(chat, "remind me tomorrow")
    assert len([message for message in bot.sent if message.buttons]) == 1


def with_handler(app, monkeypatch, name: str, handler) -> None:
    found = app.registry.get("reminder")
    monkeypatch.setattr(found, "actions", [replace(action, handler=handler) if action.name == name else action
                                           for action in found.actions])


def test_a_result_that_is_not_plain_json_still_reaches_the_model(chat, bot, model, monkeypatch):
    with_handler(chat, monkeypatch, "list", lambda _ctx: Outcome.done([{'when': datetime(2027, 1, 5, 9, 30)}]))
    model.script = [calls(("reminder_list", {})), [("answer", "One.")]]
    say(chat, "list them")
    assert results(model) == [{'status': "done", 'result': [{'when': "2027-01-05 09:30:00"}]}]
    assert answers(bot) == ["One."]


def test_a_crash_inside_the_loop_is_reported_as_no_answer(chat, bot, model, monkeypatch):
    def crash(*_args):
        raise RuntimeError("bug")

    monkeypatch.setattr(llm, "perform", crash)
    model.script = [calls(("reminder_list", {})), [("answer", "One.")]]
    say(chat, "list them")
    assert answers(bot) == ["The language model did not answer 💔"]


def test_the_outcome_comes_as_a_new_message_when_the_question_cannot_be_rewritten(chat, bot, model, monkeypatch):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    monkeypatch.setattr(Ctx, "edit", lambda *_args: False)
    press(chat, "llm:confirm:" + pending_key(chat))
    assert bot.last.text.startswith("<b>🔔 Reminders:</b>\n\nThe reminder has been set ✅")
    assert len(reminders(chat)) == 1


def test_our_call_after_a_server_search_needs_its_own_end_for_tools(chat, monkeypatch):
    _, pieces = wire(chat, monkeypatch, [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"s1","function":{"name":"search"}}]},'
        '"finish_reason":"tool_calls"}]}',
        'data: {"type":"mcp_tool_result","name":"search","result":"Hi"}',
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","function":{"name":"reminder_list"}}]}}]}',
        "data: [DONE]"])
    assert [kind for kind, _ in pieces] == ["tool", "tool", "tool"]


def test_calls_without_an_id_get_ids_that_never_repeat(chat, monkeypatch):
    lines = ['data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"reminder_list"}},'
             '{"index":1,"function":{"name":"reminder_list"}}]},"finish_reason":"tool_calls"}]}', "data: [DONE]"]
    first = wire(chat, monkeypatch, lines)[1][-1][1]
    second = wire(chat, monkeypatch, lines)[1][-1][1]
    ids = [call['id'] for call in first + second]
    assert len(set(ids)) == 4 and all(one.startswith("call_") for one in ids)


def test_arguments_that_are_not_json_go_back_to_the_server_as_json(chat, bot, model):
    model.script = [calls(("reminder_list", "{not json")), [("answer", "Sorry.")]]
    say(chat, "list them")
    assert model.asked[1][-2]['tool_calls'][0]['function']['arguments'] == "{}"


def test_after_only_confirmations_the_model_answers_the_rest_without_tools(chat, bot, model):
    model.script = [calls(("reminder_add", {'content': "Results", 'date': tomorrow()})),
                    [("answer", "And yes, it will be sunny.")]]
    say(chat, "remind me tomorrow, and will it be sunny?")
    assert len(model.asked) == 2 and model.tools[0] and model.tools[1] is None
    assert results(model) == [{'status': "pending_confirmation", 'summary': "Do you want me to set this reminder?\n"
                               "Content: Results\nDate: " + tomorrow()}]
    assert answers(bot)[-2] == "And yes, it will be sunny."
    assert bot.sent[-1].text.startswith("<b>🔔 Reminders:</b>") and bot.sent[-1].buttons
    assert [role for _, role, _ in stored(chat)] == ["user", "action", "assistant"]


def test_the_rules_keep_ids_dates_and_other_people_out_of_the_answer(chat, bot, model):
    say(chat, "hello")
    assert "never show them to the user" in model.systems[0]
    assert "give the date and time only when someone asks for them" in model.systems[0]
    assert "never guess or make up the data of other people" in model.systems[0]
    assert "The user sees your thinking too" in model.systems[0]


def test_a_read_next_to_a_confirmation_lets_the_model_answer(chat, bot, model):
    model.script = [calls(("reminder_list", {}), ("reminder_add", {'content': "Results", 'date': tomorrow()})),
                    [("answer", "Nothing yet, confirm the new one.")]]
    say(chat, "what do I have, and remind me tomorrow")
    assert [result['status'] for result in results(model)] == ["done", "pending_confirmation"]
    assert answers(bot)[-2] == "Nothing yet, confirm the new one."


def test_a_confirmation_older_than_a_day_no_longer_works(chat, bot, model, monkeypatch):
    add_reminder(model)
    say(chat, "remind me tomorrow")
    key = "action." + pending_key(chat)
    pending = json.loads(not_none(chat.storage.module_state.get(1, "llm", key)))
    old = (datetime.now() - timedelta(seconds=llm.confirm_within + 60)).isoformat(timespec="seconds")
    chat.storage.module_state.set(1, "llm", key, json.dumps(pending | {'at': old}))
    press(chat, "llm:confirm:" + key[len("action."):])
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"
    assert reminders(chat) == []


def test_old_confirmations_are_forgotten_when_a_new_one_comes(chat, bot, model):
    old = (datetime.now() - timedelta(seconds=llm.confirm_within + 60)).isoformat(timespec="seconds")
    chat.storage.module_state.set(1, "llm", "action.stale", json.dumps({'at': old}))
    chat.storage.module_state.set(1, "llm", "action.unknown", "{}")
    add_reminder(model)
    say(chat, "remind me tomorrow")
    keys = [key for key in chat.storage.module_state.get_all(1, "llm") if key.startswith("action.")]
    assert len(keys) == 1 and keys[0] not in ("action.stale", "action.unknown")
