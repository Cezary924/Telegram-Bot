from core.api import Module
from core.testing import make_message


def add_module(app, name: str, command: str, title: str, description: str, is_internal: bool) -> None:
    found = Module(name=name)
    found.command(command)(lambda ctx: "ran")
    found.is_internal = is_internal
    app.registry.add(found)
    app.catalog.add(name, "en", {'name': title, 'description': description})


def test_help_lists_every_internal_module(app, bot):
    app.router.handle_message(make_message("/help"))
    text = bot.last.text
    assert text.startswith("*📃 Help:*\n\nHere is what I can do for you:\n\n")
    for found in app.registry.modules():
        if found.is_internal and found.commands:
            assert "/" + found.commands[0].name + " - " in text


def test_an_entry_names_the_command_the_module_and_what_it_does(app, bot):
    app.router.handle_message(make_message("/help"))
    assert "/help - 📃 Help - _The list of the Bot commands_" in bot.last.text


def test_help_leaves_out_external_modules(app, bot):
    add_module(app, "tiktok", "tiktok", "TikTok", "Downloads video", False)
    app.router.handle_message(make_message("/help"))
    assert "/tiktok" not in bot.last.text


def test_help_picks_up_a_new_internal_module(app, bot):
    add_module(app, "something", "something", "Something", "Does something", True)
    app.router.handle_message(make_message("/help"))
    assert "/something - Something - _Does something_" in bot.last.text


def test_help_speaks_polish(app, bot):
    app.storage.settings.set_language(1, "pl")
    app.router.handle_message(make_message("/help"))
    assert bot.last.text.startswith("*📃 Pomoc:*\n\nOto co mogę dla Ciebie zrobić:")
    assert "/help - 📃 Pomoc - _Lista komend Bota_" in bot.last.text


def test_help_is_not_a_screen(app):
    app.router.handle_message(make_message("/help"))
    assert app.storage.navigation.depth(1) == 0
