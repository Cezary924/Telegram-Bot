import pytest

from core import loader, paths
from core.app import App
from core.roles import Role
from core.testing import FakeBot


@pytest.fixture
def app(tmp_path, monkeypatch):
    """A Bot with every internal module loaded, an empty database and a fake Telegram."""
    monkeypatch.setattr(paths, "config_dir", str(tmp_path))
    monkeypatch.setattr(paths, "db_dir", str(tmp_path / "db"))
    monkeypatch.setattr(paths, "external_modules_dir", str(tmp_path / "external"))
    monkeypatch.setattr(loader, "external_package", "modules.external")
    (tmp_path / "config.yaml").write_text(
        "bot_name: DemoBot\ngithub_username: someone\ngithub_repo: repo\ntelegram_username: someone\n",
        encoding='utf8')
    (tmp_path / "tokens.yaml").write_text("telegram: 0:aaa\n", encoding='utf8')
    application = App()
    application.services.bot = FakeBot()
    application.load_modules()
    application.storage.users.save(1, "First", "Last", "username")
    application.storage.users.set_consent(1, True)
    application.storage.users.set_role(1, Role.USER)
    application.storage.settings.set_language(1, "en")
    yield application
    application.storage.close()


@pytest.fixture
def bot(app):
    """What the Bot sent, edited and deleted during the test."""
    return app.services.bot
