import re
from typing import TypeVar

Value = TypeVar("Value")

# A Telegram token is the bot id, a colon and a secret, and requests puts the whole URL it
# tried into the text of its errors. Anything written down or sent on goes through here first.
token_pattern = re.compile(r"bot\d+:[A-Za-z0-9_-]+")
hidden_token = "bot<hidden>"


def without_secrets(text: str) -> str:
    return token_pattern.sub(hidden_token, text)


def not_none(value: Value | None, message: str = "expected a value, got none") -> Value:
    if value is None:
        raise ValueError(message)
    return value
