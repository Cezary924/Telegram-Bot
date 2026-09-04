from typing import TypeVar

Value = TypeVar("Value")


def not_none(value: Value | None, message: str = "expected a value, got none") -> Value:
    if value is None:
        raise ValueError(message)
    return value
