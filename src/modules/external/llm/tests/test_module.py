from datetime import datetime, timedelta

import pytest
import requests

from core.api import Ctx, Role, User
from core.testing import make_callback, make_message
from modules.external.llm import module as llm

real_stream = llm.stream


class Model:
    def __init__(self):
        self.asked: list[list[dict]] = []
        self.thinking: list[bool] = []
        self.answer: list[tuple[str, str]] = [("answer", "Hello there")]
        self.error: Exception | None = None

    def stream(self, _ctx, messages, thinking):
        self.asked.append([dict(one) for one in messages])
        self.thinking.append(thinking)
        if self.error is not None:
            raise self.error
        yield from self.answer


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
    return app


def say(app, text: str, message_id: int = 100):
    app.router.handle_message(make_message(text, message_id=message_id))
    app.router.wait_for_tasks()


def press(app, data: str):
    app.router.handle_callback(make_callback(data, message_id=app.services.bot.last.message_id))
    app.router.wait_for_tasks()


def stored(app) -> list[tuple[int, str, str]]:
    return [(row['conversation'], row['role'], row['content']) for row in app.storage.database.query_all(
        "SELECT * FROM " + app.storage.for_module("llm").table("messages") + " ORDER BY id;")]


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

def test_a_message_is_answered_in_one_message_rewritten_in_place(chat, bot, model):
    say(chat, "hello")
    assert model.asked == [[{'role': "user", 'content': "hello"}]]
    assert len(bot.sent) == 1
    assert bot.last.text == "Hello there"
    assert stored(chat) == [(1, "user", "hello"), (1, "assistant", "Hello there")]


def test_thinking_is_off_by_default_and_on_when_chosen(chat, bot, model):
    say(chat, "hello")
    chat.storage.module_state.set(1, "llm", "thinking", "1")
    say(chat, "again")
    assert model.thinking == [False, True]


def test_thinking_is_folded_above_the_answer(chat, bot, model):
    chat.storage.module_state.set(1, "llm", "thinking", "1")
    model.answer = [("thinking", "Two and <two>"), ("answer", "Four")]
    say(chat, "2+2?")
    assert bot.last.text.startswith("<blockquote expandable>💭 Reasoning (")
    assert "Two and &lt;two&gt;</blockquote>\nFour" in bot.last.text
    assert stored(chat)[-1] == (1, "assistant", "Four")


def test_a_long_answer_comes_in_several_messages(chat, bot, model):
    model.answer = [("answer", ("a" * 3000 + "\n\n") * 3)]
    say(chat, "write a lot")
    assert len(bot.sent) == 3
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
    assert "Now: <i>⚡ Without thinking</i>" in bot.last.text
    press(chat, "llm:thinking:1")
    assert "Now: <i>💭 With thinking</i>" in bot.last.text
    assert chat.storage.module_state.get(1, "llm", "thinking") == "1"


def test_an_unknown_thinking_choice_is_refused(chat, bot, model):
    say(chat, "/settings")
    press(chat, "core:settings:llm")
    press(chat, "llm:thinking:2")
    assert chat.storage.module_state.get(1, "llm", "thinking") is None


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


def wire(chat, monkeypatch, lines: list[str]) -> tuple[dict, list]:
    sent = {}

    def post(url, json, headers, stream, timeout):
        sent.update(url=url, json=json, headers=headers, stream=stream, timeout=timeout)
        return Response(lines)

    monkeypatch.setattr("modules.external.llm.module.requests.post", post)
    ctx = Ctx(chat.services, chat.registry.get("llm"), User(1, "First", "Last", "username", Role.GUEST, "en", True))
    return sent, list(real_stream(ctx, [{'role': "user", 'content': "hi"}], True))


def test_the_stream_is_read_as_server_sent_events(chat, monkeypatch):
    sent, pieces = wire(chat, monkeypatch, ['data: {"choices":[{"delta":{"reasoning_content":"so"}}]}', "",
                                            'data: {"choices":[{"delta":{"content":"Hi"}}]}', "data: [DONE]",
                                            'data: {"choices":[{"delta":{"content":"never"}}]}'])
    assert pieces == [("thinking", "so"), ("answer", "Hi")]
    assert sent['url'] == "http://model.local/v1/chat/completions"
    assert sent['json']['model'] == "small" and sent['json']['stream'] is True
    assert sent['json']['chat_template_kwargs'] == {'enable_thinking': True}


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
