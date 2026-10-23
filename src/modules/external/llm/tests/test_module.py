import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import requests

from core.api import Ctx, JobCtx, Role, User
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
    sent = app.services.bot.sent
    app.router.handle_callback(make_callback(data, message_id=sent[-1].message_id) if sent else make_callback(data))
    app.router.wait_for_tasks()


def stored(app) -> list[tuple[int, str, str]]:
    return [(row['conversation'], row['role'], row['content']) for row in app.storage.database.query_all(
        "SELECT * FROM " + app.storage.for_module("llm").table("messages") + " ORDER BY id;")]


def answers(bot) -> list[str]:
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


def test_the_dots_move_while_the_model_is_silent(chat, bot, monkeypatch):
    def slow(_ctx, _messages, _thinking):
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
    assert stored(chat)[-1] == (1, "assistant", "Let me check.\n\nFound it")


def test_a_search_before_any_text_keeps_one_message(chat, bot, model):
    model.answer = [("tool", ""), ("answer", "Found it")]
    say(chat, "who was it?")
    assert answers(bot) == ["Found it"]


def test_a_new_message_waits_for_the_search_while_it_runs(chat, bot, monkeypatch):
    def slow(_ctx, _messages, _thinking):
        yield "answer", "Let me check."
        yield "tool", ""
        time.sleep(0.1)
        yield "answer", "Found it"

    monkeypatch.setattr(llm, "stream", slow)
    monkeypatch.setattr(llm, "tick", 0.01)
    say(chat, "who was it?")
    shown = [message.text for message in bot.shown]
    assert answers(bot) == ["Let me check.", "Found it"]
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

    def post(url, json, headers, stream, timeout):
        sent.update(url=url, json=json, headers=headers, stream=stream, timeout=timeout)
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
