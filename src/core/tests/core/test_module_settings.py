import pytest

from core.api import Button, Module, Role, View
from core.registry import Registry
from core.router import Router
from core.testing import FakeBot, make_callback, make_message, not_none

hub = Module(name="settings")


@hub.command("settings")
def command_settings(_ctx) -> View:
    return hub_menu(_ctx)


@hub.view("menu")
def hub_menu(_ctx) -> View:
    return View("hub")


owner = Module(name="owner", is_guarded=True)


@owner.settings()
def owner_settings(_ctx) -> View:
    return View("owner settings", buttons=[Button("deeper", "deeper")])


@owner.view("format", parent="settings", title="format_title")
def owner_format(_ctx) -> View:
    return View("format")


@owner.callback("deeper")
def deeper(ctx) -> View:
    return owner_format(ctx)


@owner.view("menu")
def owner_menu(_ctx) -> View:
    return View("owner menu")


@pytest.fixture
def bot(services):
    services.bot = FakeBot()
    return services.bot


@pytest.fixture
def router(services, bot):
    services.catalog.load_core()
    services.catalog.add("settings", "en", {'name': "Settings"})
    services.catalog.add("owner", "en", {'name': "Owner", 'format_title': "Format"})
    services.registry = Registry()
    services.registry.add(hub)
    services.registry.add(owner)
    return Router(services)


@pytest.fixture
def settled(services):
    services.storage.users.save(1, "First", "Last", "username")
    services.storage.users.set_consent(1, True)
    services.storage.access.allow(1, "owner", True)
    services.storage.settings.set_language(1, "en")
    return 1


def core_text(services, key) -> str:
    return services.catalog.text("core", key, "en")


def open_owner_settings(router, bot):
    router.handle_message(make_message("/settings"))
    router.handle_callback(make_callback("core:settings:owner", message_id=bot.last.message_id))


def test_settings_are_a_view_of_their_own():
    assert owner.settings_screen is not None
    assert owner.settings_screen.role == Role.GUEST and owner.is_guarded
    assert owner.view_named("settings") is not None


def test_settings_cannot_be_declared_twice():
    module = Module(name="twice")
    module.settings()(lambda ctx: View("one"))
    with pytest.raises(ValueError):
        module.settings()


def test_only_the_settings_branch_belongs_to_the_hub():
    assert owner.is_settings("settings") and owner.is_settings("format")
    assert not owner.is_settings("menu")
    assert not hub.is_settings("menu")


def test_settings_open_in_the_same_message(router, bot, services, settled):
    open_owner_settings(router, bot)
    assert bot.last.text.endswith("owner settings")
    assert len(bot.sent) == 1
    assert not_none(services.storage.navigation.current(1))['module'] == "owner"


def test_settings_sit_under_the_hub(router, bot, settled):
    open_owner_settings(router, bot)
    assert bot.last.text.startswith("<b>Settings &gt; Owner:</b>")
    assert [data for _, data in bot.last.buttons][-3:] == ["core:back", "core:home", "core:close"]


def test_back_from_settings_returns_to_the_hub(router, bot, services, settled):
    open_owner_settings(router, bot)
    router.handle_callback(make_callback("core:back", message_id=bot.last.message_id))
    assert bot.last.text.endswith("hub")
    assert not_none(services.storage.navigation.current(1))['module'] == "settings"


def test_a_screen_deeper_in_settings_goes_back_one_step(router, bot, settled):
    open_owner_settings(router, bot)
    router.handle_callback(make_callback("owner:deeper", message_id=bot.last.message_id))
    assert "Settings &gt; Owner &gt; Format" in bot.last.text
    router.handle_callback(make_callback("core:back", message_id=bot.last.message_id))
    assert bot.last.text.endswith("owner settings")


def test_home_from_deep_in_settings_returns_to_the_hub(router, bot, settled):
    open_owner_settings(router, bot)
    router.handle_callback(make_callback("owner:deeper", message_id=bot.last.message_id))
    router.handle_callback(make_callback("core:home", message_id=bot.last.message_id))
    assert bot.last.text.endswith("hub")


def test_a_screen_outside_settings_keeps_its_own_tree(router, bot, services, settled):
    router.handle_message(make_message("/settings"))
    services.storage.navigation.set_current(1, "owner", "menu", None, bot.last.message_id)
    router.handle_callback(make_callback("core:back", message_id=bot.last.message_id))
    assert bot.last.text == core_text(services, "menu_closed")


def test_settings_without_access_are_refused(router, bot, services, settled):
    services.storage.access.allow(1, "owner", False)
    open_owner_settings(router, bot)
    assert bot.last.text == "You do not have access to Owner yet 🔒"
    assert bot.last.buttons == [("🙋 Ask for access", "core:request:owner")]


def test_settings_of_an_unknown_module_are_refused(router, bot, services, settled):
    router.handle_message(make_message("/settings"))
    router.handle_callback(make_callback("core:settings:nobody", message_id=bot.last.message_id))
    assert bot.last.text == core_text(services, "not_working_buttons")


def test_without_a_hub_settings_stand_alone(services, bot, settled):
    services.catalog.load_core()
    services.catalog.add("owner", "en", {'name': "Owner"})
    services.registry = Registry()
    services.registry.add(owner)
    router = Router(services)
    router.handle_message(make_message("/settings"))
    router.handle_callback(make_callback("core:settings:owner", message_id=1))
    assert bot.last.text.startswith("<b>Owner:</b>")
    assert [data for _, data in bot.last.buttons][-1:] == ["core:close"]
