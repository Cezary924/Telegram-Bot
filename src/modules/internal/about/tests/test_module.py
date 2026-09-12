import pytest
import requests

from core.context import AdvancedCtx, User
from core.roles import Role
from core.testing import make_message, not_none
from core.version import Version
from modules.internal.about import module as about


@pytest.fixture
def known_version(app):
    app.services.version = Version("v1.2", 100)
    app.storage.settings.set_language(1, "en")
    return app


@pytest.fixture
def offline(monkeypatch):
    def refuse(_url):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(about, "fetch", refuse)


def use_published(monkeypatch, commits: int, tag: str = "v1.3"):
    monkeypatch.setattr(about, "published_commits", lambda ctx: commits)
    monkeypatch.setattr(about, "published_tag", lambda ctx: tag)


def test_the_module_is_loaded(app):
    assert "about" in app.registry.names()


def test_about_runs_in_the_background(app):
    _, command = app.registry.command("about")
    assert command.is_background


def test_about_shows_the_bot_details(known_version, monkeypatch):
    use_published(monkeypatch, 100)
    known_version.router.handle_message(make_message("/about"))
    known_version.router.wait_for_tasks()
    text = known_version.services.bot.last.text
    assert text.startswith("*ℹ️ About The Bot:*\n\n*DemoBot*\n")
    assert "Description: _Multifunctional Telegram Bot_" in text
    assert "Version: _v1.2 (100)_" in text
    assert "GitHub Repo: https://github.com/" in text
    assert "© _2023 - " in text


def test_about_reports_being_up_to_date(known_version, monkeypatch):
    use_published(monkeypatch, 100)
    known_version.router.handle_message(make_message("/about"))
    known_version.router.wait_for_tasks()
    assert "Version status: _Up-to-date 😊_" in known_version.services.bot.last.text


def test_about_reports_being_behind(known_version, monkeypatch):
    use_published(monkeypatch, 120, "v1.3")
    known_version.router.handle_message(make_message("/about"))
    known_version.router.wait_for_tasks()
    assert "Version status: _Outdated (Up-to-date v1.3 (120))_" in known_version.services.bot.last.text


def test_about_reports_being_ahead(known_version, monkeypatch):
    use_published(monkeypatch, 80, "v1.1")
    known_version.router.handle_message(make_message("/about"))
    known_version.router.wait_for_tasks()
    assert "Version status: _Beta (Stable v1.1 (80))_" in known_version.services.bot.last.text


def test_about_survives_a_missing_network(known_version, offline, capsys):
    known_version.router.handle_message(make_message("/about"))
    known_version.router.wait_for_tasks()
    text = known_version.services.bot.last.text
    assert "Version status: _Error. Please, try again later._" in text
    assert "Version: _v1.2 (100)_" in text
    assert "Could not read the published version - ConnectionError." in capsys.readouterr().out


def test_about_speaks_polish(known_version, monkeypatch):
    use_published(monkeypatch, 100)
    known_version.storage.settings.set_language(1, "pl")
    known_version.router.handle_message(make_message("/about"))
    known_version.router.wait_for_tasks()
    text = known_version.services.bot.last.text
    assert text.startswith("*ℹ️ Informacje o Bocie:*")
    assert "Wersja: _v1.2 (100)_" in text
    assert "Status wersji: _Aktualna 😊_" in text


def test_about_is_not_a_screen(known_version, monkeypatch):
    use_published(monkeypatch, 100)
    known_version.router.handle_message(make_message("/about"))
    known_version.router.wait_for_tasks()
    assert known_version.storage.navigation.current(1) is None


class Answer:
    def __init__(self, links=None, payload=None):
        self.links = links or {}
        self._payload = payload or {}

    def json(self):
        return self._payload


def context_for(app) -> AdvancedCtx:
    person = User(1, "First", "Last", "username", Role.USER, "en", True)
    return AdvancedCtx(app.services, not_none(app.registry.get("about")), person)


def test_published_commits_reads_the_last_page_number(app, monkeypatch):
    link = "https://api.github.com/repositories/1/commits?per_page=1&page=851"
    monkeypatch.setattr(about, "fetch", lambda url: Answer(links={'last': {'url': link}}))
    assert about.published_commits(context_for(app)) == 851


def test_published_tag_reads_the_release_name(app, monkeypatch):
    monkeypatch.setattr(about, "fetch", lambda url: Answer(payload={'tag_name': "v15.2"}))
    assert about.published_tag(context_for(app)) == "v15.2"


def test_the_api_url_is_built_from_the_config(app):
    assert about.api_url(context_for(app), "/commits") == "https://api.github.com/repos/someone/repo/commits"


def test_the_repository_url_is_built_from_the_config(app):
    assert about.repository_url(context_for(app)) == "https://github.com/someone/repo/"
