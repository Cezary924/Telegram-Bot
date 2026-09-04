import os
import pytest

from core import loader, paths
from core.app import App
from core.roles import Role
from core.testing import FakeBot, make_callback, make_message
from core.tests.conftest import fixtures_dir, fixtures_package
from core.utils import not_none

journey_dir = os.path.join(fixtures_dir, "journey")
journey_package = fixtures_package + ".journey"


@pytest.fixture(scope="class")
def app(tmp_path_factory):
    directory = tmp_path_factory.mktemp("journey")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(paths, "config_dir", str(directory))
        patch.setattr(paths, "db_dir", str(directory / "db"))
        patch.setattr(paths, "internal_modules_dir", os.path.join(journey_dir, "internal"))
        patch.setattr(paths, "external_modules_dir", os.path.join(journey_dir, "external"))
        patch.setattr(loader, "internal_package", journey_package + ".internal")
        patch.setattr(loader, "external_package", journey_package + ".external")
        (directory / "config.yaml").write_text("bot_name: Bot\n", encoding='utf8')
        (directory / "tokens.yaml").write_text("telegram: 0:aaa\n", encoding='utf8')
        application = App()
        application.services.bot = FakeBot()
        application.load_modules()
        yield application
        application.storage.close()


def core_text(app, key, language="pl"):
    return app.catalog.text("core", key, language)


def module_text(app, key, language="pl", **values):
    return app.catalog.text("demo", key, language, **values)


class TestUserJourney:
    """One user, one database, twelve steps - each test builds on the one before it."""

    def test_01_the_bot_starts_with_the_demo_module(self, app):
        assert app.registry.names() == ["demo"]
        assert app.storage.for_module("demo").table_names() == ["module_demo_notes"]

    def test_02_a_stranger_is_asked_for_consent_in_their_own_language(self, app):
        app.router.handle_message(make_message("/demo", language_code="pl"))
        assert app.services.bot.last.text == core_text(app, "consent.question")
        assert app.storage.users.exists(1)
        assert not app.storage.users.has_consent(1)

    def test_03_switching_the_language_is_remembered(self, app):
        screen = app.services.bot.last.message_id
        app.router.handle_callback(make_callback("core:consent_language:en", message_id=screen))
        assert app.storage.settings.get_language(1) == "en"
        app.router.handle_callback(make_callback("core:consent_language:pl", message_id=screen))
        assert app.storage.settings.get_language(1) == "pl"

    def test_04_accepting_unlocks_the_bot(self, app):
        app.router.handle_callback(make_callback("core:consent_accept"))
        assert app.storage.users.has_consent(1)
        assert app.services.bot.last.text == core_text(app, "consent.accepted")

    def test_05_a_guest_still_cannot_run_a_user_command(self, app):
        app.router.handle_message(make_message("/demo"))
        assert app.services.bot.last.text == core_text(app, "permission_denied")
        assert app.storage.navigation.depth(1) == 0

    def test_06_a_promoted_user_gets_the_menu(self, app):
        app.storage.users.set_role(1, Role.USER)
        app.router.handle_message(make_message("/demo"))
        assert app.services.bot.last.text == "*Demo:*\n\n" + module_text(app, "menu.text")
        assert app.storage.navigation.depth(1) == 1
        assert not_none(app.storage.navigation.top(1))['view'] == "menu"

    def test_07_the_screen_carries_a_back_button(self, app):
        assert app.services.bot.last.buttons == [
            (module_text(app, "menu.open"), "demo:open"),
            (core_text(app, "return_button"), "core:back")]

    def test_08_going_deeper_replaces_the_message(self, app):
        screen = app.services.bot.last.message_id
        app.router.handle_callback(make_callback("demo:open", message_id=screen))
        assert (1, screen) in app.services.bot.deleted
        assert app.storage.navigation.depth(1) == 2
        assert not_none(app.storage.navigation.top(1))['view'] == "details"

    def test_09_a_message_on_that_screen_reaches_its_state_handler(self, app):
        app.router.handle_message(make_message("first note"))
        assert app.services.bot.last.text == module_text(app, "details.saved", note="first note")
        assert app.storage.module_state.get(1, "demo", "note") == "first note"
        rows = app.storage.for_module("demo").query_all("SELECT * FROM module_demo_notes;")
        assert [row['note'] for row in rows] == ["first note"]

    def test_10_going_back_rebuilds_the_parent_screen(self, app):
        top = not_none(app.storage.navigation.top(1))
        app.router.handle_callback(make_callback("core:back", message_id=top['message_id']))
        assert app.services.bot.last.text == "*Demo:*\n\n" + module_text(app, "menu.text")
        assert app.storage.navigation.depth(1) == 1

    def test_11_going_back_again_closes_the_menu(self, app):
        top = not_none(app.storage.navigation.top(1))
        app.router.handle_callback(make_callback("core:back", message_id=top['message_id']))
        assert app.services.bot.last.text == core_text(app, "menu_closed")
        assert app.storage.navigation.depth(1) == 0

    def test_12_a_ban_stops_everything_the_user_does(self, app):
        app.storage.users.set_role(1, Role.BANNED)
        app.router.handle_message(make_message("/demo"))
        assert app.services.bot.last.text == core_text(app, "banned_info")
        app.router.handle_message(make_message("anything"))
        assert app.services.bot.last.text == core_text(app, "banned_info")

    def test_13_lifting_the_ban_restores_the_menu(self, app):
        app.storage.users.set_role(1, Role.USER)
        app.router.handle_message(make_message("/demo"))
        assert app.services.bot.last.text == "*Demo:*\n\n" + module_text(app, "menu.text")

    def test_14_deleting_the_user_clears_every_trace(self, app):
        app.storage.users.delete(1)
        assert not app.storage.users.exists(1)
        assert app.storage.navigation.depth(1) == 0
        assert app.storage.module_state.get(1, "demo", "note") is None
        assert app.storage.for_module("demo").query_all("SELECT * FROM module_demo_notes;") == []
