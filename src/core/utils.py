import re
from typing import TypeVar

Value = TypeVar("Value")

token_pattern = re.compile(r"\d{6,12}:[A-Za-z0-9_-]{30,}")
hidden_token = "<hidden>"


def without_secrets(text: str) -> str:
    return token_pattern.sub(hidden_token, text)


def not_none(value: Value | None, message: str = "expected a value, got none") -> Value:
    if value is None:
        raise ValueError(message)
    return value
