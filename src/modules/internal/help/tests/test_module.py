from core.api import Module, Role
from core.testing import make_message


def add_module(app, name: str, command: str, title: str, description: str, is_internal: bool,
               role: Role = Role.GUEST) -> None:
    found = Module(name=name)
    found.command(command, role=role)(lambda ctx: "ran")
    found.is_internal = is_internal
    app.registry.add(found)
    app.catalog.add(name, "en", {'name': title, 'description': description})


def test_help_lists_every_internal_module_a_user_can_reach(app, bot):
    app.router.handle_message(make_message("/help"))
    text = bot.last.text
    assert text.startswith("*📃 Help:*\n\nHere is what I can do for you:\n\n")
    for found in app.registry.modules():
        open_commands = [one for one in found.commands if one.role <= Role.USER]
        if found.is_internal and open_commands:
            assert "/" + open_commands[0].name + " - " in text


def test_help_leaves_out_a_module_only_admins_can_reach(app, bot):
    add_module(app, "module1", "command1", "Module", "Does something", True, role=Role.ADMIN)
    app.router.handle_message(make_message("/help"))
    assert "/command1" not in bot.last.text
    assert "Does something" not in bot.last.text


def test_the_admin_command_stays_out_of_the_help(app, bot):
    app.storage.users.set_role(1, Role.ADMIN)
    app.router.handle_message(make_message("/help"))
    assert "/admin" not in bot.last.text


def test_a_module_names_the_first_command_a_user_can_run(app, bot):
    found = Module(name="module2")
    found.command("hidden1", role=Role.ADMIN)(lambda ctx: "ran")
    found.command("open1")(lambda ctx: "ran")
    found.is_internal = True
    app.registry.add(found)
    app.catalog.add("module2", "en", {'name': "Module", 'description': "Does something"})
    app.router.handle_message(make_message("/help"))
    assert "/open1 - Module" in bot.last.text
    assert "/hidden1" not in bot.last.text


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
    assert app.storage.navigation.current(1) is None
