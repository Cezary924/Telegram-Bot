import pytest
import telebot
from telebot.apihelper import ApiTelegramException

from core.testing import not_none
from core.ui.keyboard import Button, delete_message, render_button, render_markup


def test_button_defaults():
    button = Button("text1")
    assert button.text == "text1"
    assert button.action == "" and button.arguments == ()
    assert button.url is None and button.module is None


def test_button_takes_arguments_positionally():
    button = Button("text1", "action1", 42, "value1")
    assert button.arguments == (42, "value1")


def test_buttons_compare_by_value():
    assert Button("text1", "action1") == Button("text1", "action1")
    assert Button("text1", "action1") != Button("text1", "action2")
    assert Button("text1", "action1") != "text1"


def test_render_callback_button():
    rendered = render_button(Button("text1", "action1"), "module1")
    assert rendered.text == "text1"
    assert rendered.callback_data == "module1:action1"


def test_render_callback_button_with_arguments():
    rendered = render_button(Button("text1", "action1", 42), "module1")
    assert rendered.callback_data == "module1:action1:42"


def test_render_url_button():
    rendered = render_button(Button("text1", url="https://example.com"), "module1")
    assert rendered.url == "https://example.com"
    assert rendered.callback_data is None


def test_button_can_point_at_another_module():
    rendered = render_button(Button("text1", "action1", module="module2"), "module1")
    assert rendered.callback_data == "module2:action1"


def test_back_button_belongs_to_the_core():
    rendered = render_button(Button.back("text1"), "module1")
    assert rendered.callback_data == "core:back"


def test_render_button_rejects_data_over_the_limit():
    with pytest.raises(ValueError):
        render_button(Button("text1", "action1", "x" * 64), "module1")


def test_render_markup_puts_one_button_per_row():
    markup = not_none(render_markup([Button("text1", "action1"), Button("text2", "action2")], "module1"))
    assert [len(row) for row in markup.keyboard] == [1, 1]


def test_render_markup_groups_into_columns():
    buttons = [Button("text" + str(index), "action" + str(index)) for index in range(4)]
    markup = not_none(render_markup(buttons, "module1", columns=2))
    assert [len(row) for row in markup.keyboard] == [2, 2]


def test_render_markup_without_buttons():
    assert render_markup([], "module1") is None


def test_buttons_are_readable_when_a_test_fails():
    assert repr(Button("text1", "action1")) == "Button('text1', 'action1')"


def test_command_button_belongs_to_the_core():
    rendered = render_button(Button.command("text1", "help"), "module1")
    assert rendered.callback_data == "core:command:help"


def test_delete_message_swallows_a_refusal(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise ApiTelegramException("deleteMessage", "",
                                   {'error_code': 400, 'description': "can't be deleted"})

    bot = telebot.TeleBot("0:aaa", validate_token=False)
    monkeypatch.setattr(bot, "delete_message", refuse)
    delete_message(bot, 1, 500)


def test_delete_message_ignores_a_missing_id(monkeypatch):
    deleted = []
    bot = telebot.TeleBot("0:aaa", validate_token=False)
    monkeypatch.setattr(bot, "delete_message", lambda chat_id, message_id: deleted.append(chat_id))
    delete_message(bot, 1, None)
    assert deleted == []


def test_delete_message_deletes(monkeypatch):
    deleted = []
    bot = telebot.TeleBot("0:aaa", validate_token=False)
    monkeypatch.setattr(bot, "delete_message",
                        lambda chat_id, message_id: deleted.append((chat_id, message_id)))
    delete_message(bot, 1, 500)
    assert deleted == [(1, 500)]
