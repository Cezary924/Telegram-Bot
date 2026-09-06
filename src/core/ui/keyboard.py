import telebot
from telebot.apihelper import ApiTelegramException

from core import callbacks

core_module_name = "core"
back_action = "back"
command_action = "command"


class Button:
    def __init__(self, text: str, action: str = "", *arguments: str | int,
                 url: str | None = None, module: str | None = None) -> None:
        self.text = text
        self.action = action
        self.arguments = arguments
        self.url = url
        self.module = module

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Button) and vars(self) == vars(other)

    def __repr__(self) -> str:
        return "Button(" + repr(self.text) + ", " + repr(self.action) + ")"

    @classmethod
    def back(cls, text: str) -> "Button":
        return cls(text, back_action, module=core_module_name)

    @classmethod
    def command(cls, text: str, name: str) -> "Button":
        return cls(text, command_action, name, module=core_module_name)


def render_button(button: Button, module_name: str) -> telebot.types.InlineKeyboardButton:
    if button.url is not None:
        return telebot.types.InlineKeyboardButton(text=button.text, url=button.url)
    data = callbacks.build(button.module or module_name, button.action, *button.arguments)
    return telebot.types.InlineKeyboardButton(text=button.text, callback_data=data)


def render_markup(buttons: list[Button], module_name: str,
                  columns: int = 1) -> telebot.types.InlineKeyboardMarkup | None:
    if not buttons:
        return None
    markup = telebot.types.InlineKeyboardMarkup(row_width=columns)
    markup.add(*[render_button(button, module_name) for button in buttons])
    return markup


def delete_message(bot: telebot.TeleBot, chat_id: int, message_id: int | None) -> None:
    if message_id is None:
        return
    try:
        bot.delete_message(chat_id, message_id)
    except ApiTelegramException:
        pass
