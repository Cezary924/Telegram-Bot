import pytest

from core import callbacks


def test_build_joins_the_parts():
    assert callbacks.build("module1", "action1") == "module1:action1"
    assert callbacks.build("module1", "action1", "42") == "module1:action1:42"
    assert callbacks.build("module1", "action1", "42", "7") == "module1:action1:42:7"


def test_build_accepts_non_string_arguments():
    assert callbacks.build("module1", "action1", 42) == "module1:action1:42"


def test_build_rejects_data_over_the_telegram_limit():
    with pytest.raises(ValueError):
        callbacks.build("module1", "action1", "x" * 64)


def test_build_counts_bytes_not_characters():
    with pytest.raises(ValueError):
        callbacks.build("module1", "action1", "ą" * 30)


def test_parse_splits_the_parts():
    assert callbacks.parse("module1:action1") == ("module1", "action1", [])
    assert callbacks.parse("module1:action1:42") == ("module1", "action1", ["42"])
    assert callbacks.parse("module1:action1:42:7") == ("module1", "action1", ["42", "7"])


def test_parse_rejects_malformed_data():
    with pytest.raises(ValueError):
        callbacks.parse("module1")


def test_build_and_parse_round_trip():
    data = callbacks.build("module1", "action1", "42", "7")
    assert callbacks.parse(data) == ("module1", "action1", ["42", "7"])


def test_room_for_arguments():
    assert callbacks.room_for_arguments("module1", "action1") == 64 - len("module1:action1:")
    assert callbacks.room_for_arguments("m", "a") == 64 - len("m:a:")


def test_room_for_arguments_goes_negative_instead_of_raising():
    assert callbacks.room_for_arguments("m" * 40, "a" * 30) < 0
