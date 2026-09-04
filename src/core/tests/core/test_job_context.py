import pytest

from core.context import JobCtx
from core.module import Module
from core.testing import FakeBot
from core.ui.view import View


@pytest.fixture
def job_ctx(services, user):
    services.bot = FakeBot()
    services.catalog.load_core()
    services.catalog.add("module1", "pl", {'key1': "jeden"})
    services.catalog.add("module1", "en", {'key1': "one"})
    return JobCtx(services, Module(name="module1"))


def test_database_is_prefixed(job_ctx):
    assert job_ctx.db.prefix == "module_module1_"


def test_language_of_a_user(job_ctx, services, user):
    assert job_ctx.language_of(user) == "en"
    services.storage.settings.set_language(user, "pl")
    assert job_ctx.language_of(user) == "pl"


def test_text_in_a_given_language(job_ctx):
    assert job_ctx.t("key1", "pl") == "jeden"
    assert job_ctx.t("key1", "en") == "one"


def test_send_reaches_the_user(job_ctx, services, user):
    job_ctx.send(user, "text1")
    assert services.bot.last.chat_id == user
    assert services.bot.last.text == "text1"


def test_send_renders_a_view(job_ctx, services, user):
    job_ctx.send(user, View("text1", path=["one"]))
    assert services.bot.last.text == "*one:*\n\ntext1"


def test_send_respects_the_notification_setting(job_ctx, services, user):
    job_ctx.send(user, "text1")
    assert not services.bot.last.is_silent
    services.storage.settings.set_notifications(user, False)
    job_ctx.send(user, "text1")
    assert services.bot.last.is_silent


def test_log_names_the_module(job_ctx, capsys):
    job_ctx.log("Tick")
    assert "Tick in 'module1'." in capsys.readouterr().out


def test_error_names_the_module(job_ctx, capsys):
    job_ctx.error("Something broke")
    assert "ERROR: Something broke in 'module1'." in capsys.readouterr().out
