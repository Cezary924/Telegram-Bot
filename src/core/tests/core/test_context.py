import os
import pytest

from core import paths
from core.context import AdvancedCtx, Ctx, User, create_context, user_from_row
from core.module import Module
from core.roles import Role
from core.testing import FakeBot, make_message, not_none
from core.ui.view import View
from core.version import Version


@pytest.fixture
def module():
    return Module(name="module1", tokens=["token1"])


@pytest.fixture
def person():
    return User(1, "First", "Last", "username", Role.USER, "pl")


@pytest.fixture
def ctx(services, module, person, user):
    services.catalog.add("module1", "pl", {'key1': "jeden", 'key2': "witaj {name}"})
    services.catalog.add("module1", "en", {'key1': "one"})
    return Ctx(services, module, person)


def test_user_from_row(storage, user):
    person = user_from_row(not_none(storage.users.get(user)), "pl")
    assert person.id == 1
    assert person.first_name == "First"
    assert person.role == Role.GUEST
    assert person.language == "pl"


def test_user_label(person):
    assert person.label == "First (1)"


def test_text_uses_the_module_namespace_and_user_language(ctx):
    assert ctx.t("key1") == "jeden"


def test_text_falls_back_to_the_default_language(ctx):
    ctx._services.catalog.add("module1", "en", {'key3': "three"})
    assert ctx.t("key3") == "three"


def test_text_formats_values(ctx):
    assert ctx.t("key2", name="world") == "witaj world"


def test_declared_token_is_available(ctx):
    assert ctx.token("token1") == "value1"


def test_undeclared_token_is_refused(ctx):
    with pytest.raises(PermissionError) as error:
        ctx.token("token2")
    assert "module1" in str(error.value)


def test_telegram_token_is_refused(ctx):
    with pytest.raises(PermissionError):
        ctx.token("telegram")


def test_state_is_scoped_to_the_module_and_user(ctx, services):
    ctx.state.set("key1", "value1")
    assert ctx.state.get("key1") == "value1"
    assert services.storage.module_state.get(1, "module1", "key1") == "value1"
    assert services.storage.module_state.get(1, "module2", "key1") is None


def test_state_behaves_like_a_dictionary(ctx):
    ctx.state["key1"] = "value1"
    assert ctx.state["key1"] == "value1"
    assert "key1" in ctx.state
    assert "key9" not in ctx.state
    ctx.state.delete("key1")
    assert ctx.state.get("key1") is None


def test_state_all_and_clear(ctx):
    ctx.state.set("key1", "value1")
    ctx.state.set("key2", "value2")
    assert ctx.state.all() == {'key1': "value1", 'key2': "value2"}
    ctx.state.clear()
    assert ctx.state.all() == {}


def test_navigation_reads_the_screen_the_user_is_on(ctx, services):
    services.storage.navigation.set_current(1, "module1", "view1", "argument1", 500)
    current = not_none(ctx.nav.current())
    assert current['module'] == "module1"
    assert current['view'] == "view1"
    assert current['argument'] == "argument1"


def test_navigation_reads_what_a_screen_of_this_module_remembers(ctx, services):
    services.storage.navigation.remember(1, "module1", "list", "3")
    services.storage.navigation.remember(1, "module2", "list", "9")
    assert ctx.nav.remembered("list") == "3"


def test_navigation_clears_the_screen(ctx, services):
    services.storage.navigation.set_current(1, "module1", "view1", None, 500)
    ctx.nav.clear()
    assert ctx.nav.current() is None


def test_database_is_prefixed(ctx):
    assert ctx.db.prefix == "module_module1_"
    assert ctx.db.table("items") == "module_module1_items"


def test_workspace_is_created_and_removed(ctx, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "temp_dir", str(tmp_path))
    with ctx.workspace() as directory:
        assert os.path.isdir(directory)
        assert directory.startswith(os.path.join(str(tmp_path), "module1"))
        with open(os.path.join(directory, "file1.txt"), "w") as f:
            f.write("value1")
    assert not os.path.isdir(directory)


def test_workspace_is_removed_after_an_error(ctx, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "temp_dir", str(tmp_path))
    with pytest.raises(RuntimeError):
        with ctx.workspace() as directory:
            raise RuntimeError("boom")
    assert not os.path.isdir(directory)


def test_workspaces_do_not_collide(ctx, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "temp_dir", str(tmp_path))
    with ctx.workspace() as first, ctx.workspace() as second:
        assert first != second


def write_file(tmp_path, name: str = "file1.mp4") -> str:
    full_path = os.path.join(str(tmp_path), name)
    with open(full_path, "wb") as f:
        f.write(b"data")
    return full_path


@pytest.fixture
def sending(ctx, services):
    services.bot = FakeBot()
    return ctx


def test_a_file_is_sent_as_the_kind_asked_for(sending, services, tmp_path):
    sending.send_file(write_file(tmp_path), "video")
    sent = services.bot.files[0]
    assert (sent.chat_id, sent.kind, sent.name) == (1, "video", "file1.mp4")


def test_a_file_is_a_document_by_default(sending, services, tmp_path):
    sending.send_file(write_file(tmp_path))
    assert services.bot.files[0].kind == "document"


def test_a_file_carries_its_caption(sending, services, tmp_path):
    sending.send_file(write_file(tmp_path), "video", "caption1")
    assert services.bot.files[0].caption == "caption1"


def test_a_file_of_an_unknown_kind_is_refused(sending, tmp_path):
    with pytest.raises(ValueError):
        sending.send_file(write_file(tmp_path), "hologram")


def test_a_file_is_silent_when_notifications_are_off(sending, services, storage, user, tmp_path):
    storage.settings.set_notifications(user, False)
    sending.send_file(write_file(tmp_path), "video")
    assert services.bot.files[0].is_silent


def test_the_file_limit_is_the_one_telegram_allows(ctx):
    assert ctx.file_limit == 50 * 1024 * 1024


def test_log_names_the_user(ctx, capsys):
    ctx.log("Something happened")
    assert "Something happened: First (1)." in capsys.readouterr().out


def test_error_names_the_module(ctx, capsys):
    ctx.error("Something broke")
    assert "ERROR: Something broke in 'module1'." in capsys.readouterr().out


def test_internal_module_gets_the_advanced_context(services, module, person):
    module.is_internal = True
    ctx = create_context(services, module, person)
    assert isinstance(ctx, AdvancedCtx)
    assert ctx.users is services.storage.users
    assert ctx.settings is services.storage.settings
    assert ctx.registry is services.registry
    assert ctx.config is services.config


def test_external_module_gets_the_basic_context(services, module, person):
    ctx = create_context(services, module, person)
    assert isinstance(ctx, Ctx)
    assert not isinstance(ctx, AdvancedCtx)
    for name in ["users", "settings", "registry", "config"]:
        assert not hasattr(ctx, name)


def test_retrying_asks_the_same_screen_again_with_the_problem(services, module, person, user):
    @module.view("view1")
    def view1(_ctx):
        return View("What is your name?")

    services.registry.add(module)
    services.storage.navigation.set_current(1, "module1", "view1", None, 501)
    view = Ctx(services, module, person).retry("That is not a name")
    assert view.text == "That is not a name\n\nWhat is your name?"
    assert view.name == "view1"


def test_retrying_keeps_what_the_screen_remembered(services, module, person, user):
    @module.view("view1")
    def view1(ctx):
        return View("Page " + (ctx.arguments[0] if ctx.arguments else "?"))

    services.registry.add(module)
    services.storage.navigation.set_current(1, "module1", "view1", "3", 501)
    view = Ctx(services, module, person, arguments=("3",)).retry("Nope")
    assert view.text == "Nope\n\nPage 3"


def test_retrying_without_a_screen_only_says_the_problem(services, module, person, user):
    services.registry.add(module)
    view = Ctx(services, module, person).retry("Nope")
    assert view.text == "Nope"
    assert not view.is_screen


def test_retrying_a_screen_that_is_gone_only_says_the_problem(services, module, person, user):
    services.registry.add(module)
    services.storage.navigation.set_current(1, "module1", "view9", None, 501)
    view = Ctx(services, module, person).retry("Nope")
    assert view.text == "Nope"
    assert not view.is_screen


def test_closing_a_screen_takes_its_message_away(services, module, person, user):
    services.bot = FakeBot()
    ctx = Ctx(services, module, person)
    services.storage.navigation.set_current(1, "module1", "view1", None, 501)
    ctx.close_screen()
    assert services.bot.deleted == [(1, 501)]
    assert ctx.nav.current() is None


def test_closing_an_empty_screen_does_nothing(services, module, person, user):
    services.bot = FakeBot()
    Ctx(services, module, person).close_screen()
    assert services.bot.deleted == []


def test_an_internal_module_can_switch_the_user_language(services, module, person, user):
    module.is_internal = True
    services.catalog.add("module1", "pl", {'key1': "jeden"})
    services.catalog.add("module1", "en", {'key1': "one"})
    ctx = AdvancedCtx(services, module, person)
    assert ctx.t("key1") == "jeden"
    ctx.use_language("en")
    assert ctx.t("key1") == "one"
    assert services.storage.settings.get_language(1) == "en"


def test_an_internal_module_reads_another_user_language(services, module, person, user):
    module.is_internal = True
    services.storage.users.save(2, "Other", "Person", "other")
    services.storage.settings.set_language(2, "pl")
    services.catalog.add("module1", "pl", {'key1': "jeden"})
    services.catalog.add("module1", "en", {'key1': "one"})
    ctx = AdvancedCtx(services, module, person)
    assert ctx.language_of(2) == "pl"
    assert ctx.text_for(2, "key1") == "jeden"
    assert ctx.text_for(1, "key1") == "one"


def test_an_internal_module_notifies_another_user(services, module, person, user):
    services.bot = FakeBot()
    module.is_internal = True
    services.storage.users.save(2, "Other", "Person", "other")
    ctx = AdvancedCtx(services, module, person)
    ctx.notify(2, "text1")
    assert services.bot.last.chat_id == 2
    assert services.bot.last.text == "text1"
    assert services.bot.last.parse_mode is None


def test_notifying_respects_the_recipient_settings(services, module, person, user):
    services.bot = FakeBot()
    module.is_internal = True
    services.storage.users.save(2, "Other", "Person", "other")
    services.storage.settings.set_notifications(2, False)
    AdvancedCtx(services, module, person).notify(2, "text1")
    assert services.bot.last.is_silent


def test_the_version_reaches_an_internal_module(services, module, person):
    module.is_internal = True
    services.version = Version("v1.2", 100)
    assert str(AdvancedCtx(services, module, person).version) == "v1.2 (100)"


def test_a_forwarded_message_reveals_its_sender(services, module, person):
    ctx = Ctx(services, module, person, make_message("hello", forward_from=555))
    assert ctx.forwarded_from == 555


def test_a_hidden_sender_stays_hidden(services, module, person):
    ctx = Ctx(services, module, person, make_message("hello", is_forwarded=True))
    assert ctx.forwarded_from is None


def test_an_ordinary_message_was_not_forwarded(services, module, person):
    assert Ctx(services, module, person, make_message("hello")).forwarded_from is None
    assert Ctx(services, module, person).forwarded_from is None
