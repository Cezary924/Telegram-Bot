import pytest

from core.api import Role
from core.testing import make_callback, make_message
from modules.external.unitconverter.module import parse


@pytest.mark.parametrize("text, unit, number", [
    ("5 km", "km", 5.0),
    ("5km", "km", 5.0),
    ("100 cm", "cm", 100.0),
    ("1.5h", "h", 1.5),
    ("90min", "min", 90.0),
    ("2 yr", "yr", 2.0),
    ("500 g", "g", 500.0),
    ("3 lb", "lb", 3.0),
    ("12 mo", "mo", 12.0),
])
def test_a_number_with_a_unit_is_understood(text, unit, number):
    found = parse(text)
    assert found is not None
    assert (found[1], found[2]) == (unit, number)


@pytest.mark.parametrize("text", ["5", "hello", "", "in", "https://youtu.be/5m", "km", "5 5"])
def test_anything_else_is_left_alone(text):
    assert parse(text) is None


def test_a_bare_number_does_not_reach_the_converter(app, bot):
    app.router.handle_message(make_message("5"))
    assert bot.last.text == "Sorry, I do not understand... 💔"


def test_a_length_is_converted_into_every_length(app, bot):
    app.router.handle_message(make_message("5 km"))
    text = bot.last.text
    assert text.startswith("*🧮 Unit converter:*\n\n*5 km*\n")
    assert "_m_: 5000" in text
    assert "_mm_: 5e+06" in text
    assert "_mi_: 3.10685" in text


def test_a_mass_is_converted(app, bot):
    app.router.handle_message(make_message("1 kg"))
    assert "_g_: 1000" in bot.last.text
    assert "_t_: 0.001" in bot.last.text


def test_a_time_is_converted(app, bot):
    app.router.handle_message(make_message("1 h"))
    assert "_min_: 60" in bot.last.text
    assert "_s_: 3600" in bot.last.text


def test_the_command_explains_how(app, bot):
    app.router.handle_message(make_message("/unitconverter"))
    assert bot.last.text.startswith("*🧮 Unit converter:*")
    assert "send me your number with its current unit" in bot.last.text


def test_a_guest_gets_no_conversion(app, bot):
    app.storage.users.set_role(1, Role.GUEST)
    app.router.handle_message(make_message("5 km"))
    assert bot.last.text.startswith("Sorry, you cannot use this command")


def test_it_speaks_polish(app, bot):
    app.storage.settings.set_language(1, "pl")
    app.router.handle_message(make_message("5 km"))
    assert bot.last.text.startswith("*🧮 Konwerter jednostek:*")


def test_a_screen_takes_the_message_before_the_converter(app, bot):
    app.storage.users.set_role(1, Role.ADMIN)
    app.router.handle_message(make_message("/admin"))
    for action in ["admin:users", "admin:search"]:
        app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))
    app.router.handle_message(make_message("5 km"))
    assert "has not been found" in bot.last.text
