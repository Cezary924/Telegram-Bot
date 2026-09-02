import os
import sqlite3

import pytest

from core import loader, paths
from core.app import App
from core.roles import Role
from core.testing import FakeBot, make_message
from core.version import Version
from core.tests.conftest import fixtures_dir, fixtures_package


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "config_dir", str(tmp_path))
    monkeypatch.setattr(paths, "db_dir", str(tmp_path / "db"))
    monkeypatch.setattr(paths, "internal_modules_dir", os.path.join(fixtures_dir, "internal"))
    monkeypatch.setattr(paths, "external_modules_dir", os.path.join(fixtures_dir, "external"))
    monkeypatch.setattr(loader, "internal_package", fixtures_package + ".internal")
    monkeypatch.setattr(loader, "external_package", fixtures_package + ".external")
    (tmp_path / "config.yaml").write_text(
        "bot_name: Bot\ngithub_username: someone\ngithub_repo: repo\n", encoding='utf8')
    (tmp_path / "tokens.yaml").write_text("telegram: 0:aaa\ntelegram_beta: 0:bbb\ntoken1: value1\n",
                                          encoding='utf8')
    app = App()
    app.services.bot = FakeBot()
    yield app
    try:
        app.storage.close()
    except sqlite3.ProgrammingError:
        pass


def test_core_locales_are_ready(app):
    assert app.catalog.languages() == ["en", "pl"]
    assert app.catalog.text("core", "yes_button", "pl") == "✅ Tak"


def test_database_lives_next_to_the_others(app, tmp_path):
    assert app.storage.database.path == str(tmp_path / "db" / "bot.db")


def test_beta_uses_its_own_database(tmp_path, monkeypatch, app):
    beta = App(is_beta=True)
    assert beta.storage.database.path.endswith("bot-beta.db")
    assert beta.config.bot_name == "BetaBot"
    beta.storage.close()


def test_modules_are_loaded(app):
    app.load_modules()
    assert app.registry.names() == ["module1", "module2"]
    assert app.catalog.text("module1", "key1", "pl") == "jeden"


def test_module_schemas_are_applied(app):
    app.load_modules()
    assert app.storage.for_module("module1").table_names() == ["module_module1_items"]


def test_jobs_reach_the_scheduler(app):
    app.load_modules()
    assert app.scheduler.names() == ["module2.job1"]


def test_commands_are_published_per_language(app):
    app.load_modules()
    app.publish_commands()
    assert app.services.bot.commands["en"] == ["command1", "command2"]
    assert app.services.bot.commands["pl"] == ["command1", "command2"]


def test_admins_are_notified(app):
    app.storage.users.save(1, "First", "Last", "username")
    app.storage.users.save(2, "Other", "Person", "other")
    app.storage.users.set_role(2, Role.ADMIN)
    app.storage.settings.set_language(2, "pl")
    app.notify_admins("bot_started")
    assert [(message.chat_id, message.text) for message in app.services.bot.sent] == [
        (2, app.catalog.text("core", "bot_started", "pl"))]


def test_the_router_answers_a_loaded_command(app):
    app.load_modules()
    app.storage.users.save(1, "First", "Last", "username")
    app.storage.users.set_consent(1, True)
    app.storage.users.set_role(1, Role.USER)
    app.router.handle_message(make_message("/command1"))
    assert app.services.bot.last.text == "one"


def test_an_unknown_command_falls_back(app):
    app.load_modules()
    app.storage.users.save(1, "First", "Last", "username")
    app.storage.users.set_consent(1, True)
    app.router.handle_message(make_message("/nope"))
    assert app.services.bot.last.text == app.catalog.text("core", "unknown_command", "en")


def test_build_bot_wires_the_router(app):
    app.load_modules()
    app.services.bot = None
    bot = app.build_bot()
    assert app.services.bot is bot
    assert bot.threaded and len(bot.message_handlers) == 1 and len(bot.callback_query_handlers) == 1


def test_worker_threads_reach_the_bot(app, tmp_path):
    (tmp_path / "config.yaml").write_text("bot_name: Bot\nworker_threads: 5\n", encoding='utf8')
    fresh = App()
    fresh.load_modules()
    assert fresh.build_bot().worker_pool.num_threads == 5
    fresh.storage.close()


def test_a_job_reaches_its_handler_through_the_scheduler(app, capsys):
    app.load_modules()
    name, handler, interval = app.scheduler._jobs[0]
    assert name == "module2.job1" and interval == 3600
    handler()
    assert "Tick in 'module2'." in capsys.readouterr().out


def test_publishing_commands_survives_a_refusing_bot(app, capsys):
    app.load_modules()

    def refuse(*_args, **_kwargs):
        raise RuntimeError("boom")

    app.services.bot.set_my_commands = refuse
    app.publish_commands()
    assert "Could not publish the command list - RuntimeError." in capsys.readouterr().out


def test_notifying_admins_survives_a_blocked_chat(app, capsys):
    app.storage.users.save(2, "Other", "Person", "other")
    app.storage.users.set_role(2, Role.ADMIN)

    def refuse(*_args, **_kwargs):
        raise RuntimeError("boom")

    app.services.bot.send_message = refuse
    app.notify_admins("bot_started")
    assert "Could not notify the admin - RuntimeError." in capsys.readouterr().out


def test_stopping_closes_everything(app):
    app.load_modules()
    app.scheduler.start()
    with pytest.raises(SystemExit) as exit_code:
        app.stop()
    assert exit_code.value.code == 0
    assert not app.services.bot.is_polling


def test_the_first_run_only_remembers_the_version(app, bot):
    app.services.version = Version("v1.2", 100)
    app.storage.users.save(2, "Other", "Person", "other")
    app.announce_update()
    assert app.storage.state.get("version") == "v1.2 (100)"
    assert bot.sent == []


def test_a_changed_version_is_announced_to_the_users(app, bot):
    app.storage.state.set("version", "v1.1 (80)")
    app.services.version = Version("v1.2", 100)
    app.storage.users.save(2, "Other", "Person", "other")
    app.storage.settings.set_language(2, "pl")
    app.announce_update()
    assert app.storage.state.get("version") == "v1.2 (100)"
    assert [message.chat_id for message in bot.sent] == [2]
    assert bot.last.text.startswith("Bot został zaktualizowany")


def test_an_unchanged_version_says_nothing(app, bot):
    app.services.version = Version("v1.2", 100)
    app.storage.state.set("version", "v1.2 (100)")
    app.storage.users.save(2, "Other", "Person", "other")
    app.announce_update()
    assert bot.sent == []


def test_a_user_with_notifications_off_is_not_told(app, bot):
    app.storage.state.set("version", "v1.1 (80)")
    app.services.version = Version("v1.2", 100)
    app.storage.users.save(2, "Other", "Person", "other")
    app.storage.settings.set_notifications(2, False)
    app.announce_update()
    assert [message.chat_id for message in bot.sent] == []


def test_the_update_message_links_to_the_release(app, bot):
    app.storage.state.set("version", "v1.1 (80)")
    app.services.version = Version("v1.2", 100)
    app.storage.users.save(2, "Other", "Person", "other")
    app.announce_update()
    assert bot.last.text.endswith("\n\nhttps://github.com/someone/repo/releases/tag/v1.2")


def test_an_unknown_version_carries_no_link(app, bot):
    app.storage.state.set("version", "v1.1 (80)")
    app.services.version = Version()
    app.storage.users.save(2, "Other", "Person", "other")
    app.announce_update()
    assert "https://" not in bot.last.text


def test_a_missing_github_config_carries_no_link(app, bot, tmp_path):
    (tmp_path / "config.yaml").write_text("bot_name: DemoBot\n", encoding='utf8')
    fresh = App()
    fresh.services.bot = bot
    fresh.services.version = Version("v1.2", 100)
    fresh.storage.state.set("version", "v1.1 (80)")
    fresh.storage.users.save(2, "Other", "Person", "other")
    fresh.announce_update()
    assert "https://" not in bot.last.text
    fresh.storage.close()
