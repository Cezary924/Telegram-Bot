from core.api import Module, Role
from core.registry import Registry
from core.testing import make_callback, make_message
from modules.internal.start import module as start


def add_feature(app, name: str, command: str, title: str, description: str) -> Module:
    feature = Module(name=name)
    feature.command(command)(lambda ctx: "ran")
    app.registry.add(feature)
    app.catalog.add(name, "en", {'name': title, 'description': description})
    return feature


def test_the_module_is_loaded(app):
    assert "start" in app.registry.names()
    assert app.registry.command("start") is not None
    assert app.registry.command("features") is not None


def test_start_greets_the_user_by_the_bot_name(app, bot):
    app.router.handle_message(make_message("/start"))
    assert bot.last.text == "*👋 Hi!*\n\nThis is DemoBot! 🤖"


def test_start_offers_the_feature_list(app, bot):
    app.router.handle_message(make_message("/start"))
    assert ("✨ Bot Features", "core:command:features") in bot.last.buttons


def test_start_links_only_to_modules_that_are_loaded(app, bot, monkeypatch):
    monkeypatch.setattr(start, "linked_modules", ["nothing"])
    app.router.handle_message(make_message("/start"))
    assert [data for _, data in bot.last.buttons] == ["core:command:features"]


def test_start_links_to_a_module_that_is_loaded(app, bot, monkeypatch):
    monkeypatch.setattr(start, "linked_modules", ["demo"])
    add_feature(app, "demo", "demo", "Demo", "does things")
    app.registry.get("demo").is_internal = True
    app.router.handle_message(make_message("/start"))
    assert [data for _, data in bot.last.buttons] == ["core:command:demo", "core:command:features"]


def test_start_is_meant_to_link_to_help_and_about():
    assert start.linked_modules == ["help", "about"]


def test_a_button_runs_the_command_behind_it(app, bot):
    app.router.handle_message(make_message("/start"))
    app.router.handle_callback(make_callback("core:command:features", message_id=bot.last.message_id))
    assert bot.last.text.startswith("*✨ Bot Features:*")


def test_features_lists_external_modules(app, bot):
    add_feature(app, "something", "something", "Something", "Does something")
    app.router.handle_message(make_message("/features"))
    assert bot.last.text.startswith("*✨ Bot Features:*\n\n")
    assert "/something - Something - _Does something_" in bot.last.text
    for found in app.registry.modules():
        if not found.is_internal and found.commands:
            assert "/" + found.commands[0].name + " - " in bot.last.text


def test_features_leaves_out_internal_modules(app, bot):
    add_feature(app, "tiktok", "tiktok", "TikTok", "Downloads video from TikTok")
    app.router.handle_message(make_message("/features"))
    assert "/start" not in bot.last.text and "/about" not in bot.last.text


def test_features_says_so_when_nothing_is_on(app, bot):
    internal_only = Registry()
    for found in app.registry.modules():
        if found.is_internal:
            internal_only.add(found)
    app.services.registry = internal_only
    app.router.handle_message(make_message("/features"))
    assert bot.last.text == "*✨ Bot Features:*\n\nNo features are turned on right now."


def test_features_speaks_polish(app, bot):
    app.storage.settings.set_language(1, "pl")
    app.router.handle_message(make_message("/features"))
    assert bot.last.text.startswith("*✨ Funkcje Bota:*")


def test_a_guest_may_start(app, bot):
    app.storage.users.set_role(1, Role.GUEST)
    app.router.handle_message(make_message("/start"))
    assert bot.last.text.startswith("*👋 Hi!*")


def test_neither_screen_goes_on_the_navigation_stack(app):
    app.router.handle_message(make_message("/start"))
    app.router.handle_message(make_message("/features"))
    assert app.storage.navigation.current(1) is None


def test_the_commands_are_published_to_telegram(app, bot):
    app.publish_commands()
    assert "start" in bot.commands["en"] and "features" in bot.commands["en"]
