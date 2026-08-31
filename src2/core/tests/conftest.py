import os
import pytest

from core import paths
from core.config import Config
from core.testing import make_storage
from core.i18n import Catalog
from core.registry import Registry
from core.services import Services

fixtures_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures")
fixtures_package = "core.tests.fixtures"


@pytest.fixture
def storage():
    storage = make_storage()
    yield storage
    storage.close()


@pytest.fixture
def user(storage):
    storage.users.save(1, "First", "Last", "username")
    return 1


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "config_dir", str(tmp_path))
    (tmp_path / "config.yaml").write_text("bot_name: Bot\n", encoding='utf8')
    (tmp_path / "tokens.yaml").write_text("telegram: 0:aaa\ntoken1: value1\ntoken2: value2\n",
                                          encoding='utf8')
    return Config()


@pytest.fixture
def services(config, storage):
    return Services(config, Catalog(), storage, Registry())


@pytest.fixture
def module_sources():
    return [(os.path.join(fixtures_dir, "internal"), fixtures_package + ".internal", True),
            (os.path.join(fixtures_dir, "external"), fixtures_package + ".external", False)]
