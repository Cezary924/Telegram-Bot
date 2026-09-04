import pytest

from core.testing import FakeBot, make_callback, make_message, make_storage, not_none
from core.ui.keyboard import Button
from core.ui.view import render_markup


def test_not_none_passes_a_value_through():
    assert not_none("value1") == "value1"


def test_not_none_fails_on_none():
    with pytest.raises(ValueError) as error:
        not_none(None, "the row vanished")
    assert "the row vanished" in str(error.value)


def test_make_storage_is_ready_to_use():
    storage = make_storage()
    storage.users.save(1, "First", "Last", "username")
    assert storage.users.exists(1)
    storage.close()


def test_make_message():
    message = make_message("/start", user_id=7, language_code="pl")
    assert message.text == "/start"
    assert not_none(message.from_user).id == 7
    assert message.chat.id == 7
    assert not_none(message.from_user).language_code == "pl"


def test_make_callback():
    callback = make_callback("module1:action1:42", user_id=7, message_id=500)
    assert callback.data == "module1:action1:42"
    assert not_none(callback.from_user).id == 7
    assert not_none(callback.message).message_id == 500


def test_send_message_is_recorded():
    bot = FakeBot()
    bot.send_message(1, "text1", parse_mode="Markdown")
    assert bot.last.chat_id == 1
    assert bot.last.text == "text1"
    assert bot.last.parse_mode == "Markdown"


def test_message_ids_grow():
    bot = FakeBot()
    first = bot.send_message(1, "text1")
    second = bot.send_message(1, "text2")
    assert second.message_id > first.message_id
    assert bot.texts() == ["text1", "text2"]


def test_buttons_are_readable():
    bot = FakeBot()
    markup = render_markup([Button("text1", "action1"), Button("text2", "action2")], "module1")
    bot.send_message(1, "text1", reply_markup=markup)
    assert bot.last.buttons == [("text1", "module1:action1"), ("text2", "module1:action2")]


def test_silent_messages_are_recorded():
    bot = FakeBot()
    bot.send_message(1, "text1")
    bot.send_message(1, "text2", disable_notification=True)
    assert [message.is_silent for message in bot.sent] == [False, True]


def test_a_message_without_buttons():
    bot = FakeBot()
    bot.send_message(1, "text1")
    assert bot.last.buttons == []


def test_edits_and_deletes_are_recorded():
    bot = FakeBot()
    bot.edit_message_text("text1", 1, 500)
    bot.delete_message(1, 500)
    bot.answer_callback_query("1", "text2")
    assert bot.edited[0].text == "text1" and bot.edited[0].message_id == 500
    assert bot.deleted == [(1, 500)]
    assert bot.answered == [("1", "text2")]


def test_clear():
    bot = FakeBot()
    bot.send_message(1, "text1")
    bot.delete_message(1, 500)
    bot.clear()
    assert bot.sent == [] and bot.deleted == []
