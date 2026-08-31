from dataclasses import dataclass
import telebot

from core.db.storage import Storage
from core.utils import not_none

__all__ = ["FakeBot", "SentMessage", "make_callback", "make_message", "make_storage",
           "not_none", "reachable_date"]


def make_storage() -> Storage:
    return Storage(":memory:")


# Telegram marks a message the bot can no longer reach by dating it 0, and telebot turns
# such a message into InaccessibleMessage - so a reachable fake needs any real timestamp.
# This one is the first commit of this repository, 2023-04-14 13:15:48 +02:00.
reachable_date = 1681470948


def make_message(text: str, user_id: int = 1, message_id: int = 100,
                 language_code: str = "en") -> telebot.types.Message:
    return telebot.types.Message.de_json({
        'message_id': message_id,
        'from': {'id': user_id, 'is_bot': False, 'first_name': "First", 'last_name': "Last",
                 'username': "username", 'language_code': language_code},
        'chat': {'id': user_id, 'type': "private", 'first_name': "First"},
        'date': reachable_date, 'text': text})


def make_callback(data: str, user_id: int = 1, message_id: int = 100,
                  is_reachable: bool = True, language_code: str = "en") -> telebot.types.CallbackQuery:
    return telebot.types.CallbackQuery.de_json({
        'id': "1",
        'from': {'id': user_id, 'is_bot': False, 'first_name': "First", 'username': "username",
                 'language_code': language_code},
        'message': {'message_id': message_id, 'from': {'id': 9, 'is_bot': True, 'first_name': "Bot"},
                    'chat': {'id': user_id, 'type': "private"},
                    'date': reachable_date if is_reachable else 0, 'text': "screen"},
        'chat_instance': "x", 'data': data})


@dataclass
class SentMessage:
    chat_id: int
    text: str
    message_id: int
    parse_mode: str | None = None
    markup: telebot.types.InlineKeyboardMarkup | None = None
    is_silent: bool = False

    @property
    def buttons(self) -> list[tuple[str, str | None]]:
        if self.markup is None:
            return []
        return [(button.text, button.callback_data)
                for row in self.markup.keyboard for button in row]


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[SentMessage] = []
        self.edited: list[SentMessage] = []
        self.deleted: list[tuple[int, int]] = []
        self.answered: list[tuple[str, str | None]] = []
        self.commands: dict[str, list[str]] = {}
        self.is_polling = True
        self._message_id = 1000

    def send_message(self, chat_id: int, text: str, parse_mode: str | None = None,
                     reply_markup=None, disable_notification: bool = False) -> telebot.types.Message:
        self._message_id += 1
        self.sent.append(SentMessage(chat_id, text, self._message_id, parse_mode, reply_markup,
                                     disable_notification))
        return make_message(text, chat_id, self._message_id)

    def edit_message_text(self, text: str, chat_id: int, message_id: int,
                          parse_mode: str | None = None, reply_markup=None) -> None:
        self.edited.append(SentMessage(chat_id, text, message_id, parse_mode, reply_markup))

    def delete_message(self, chat_id: int, message_id: int) -> None:
        self.deleted.append((chat_id, message_id))

    def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> None:
        self.answered.append((callback_query_id, text))

    def set_my_commands(self, commands, language_code: str | None = None) -> None:
        self.commands[language_code or ""] = [command.command for command in commands]

    def stop_polling(self) -> None:
        self.is_polling = False

    @property
    def last(self) -> SentMessage:
        return self.sent[-1]

    def texts(self) -> list[str]:
        return [message.text for message in self.sent]

    def clear(self) -> None:
        self.sent.clear()
        self.edited.clear()
        self.deleted.clear()
        self.answered.clear()
