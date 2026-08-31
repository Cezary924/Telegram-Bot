import pytest

from core import paths
from core.config import Config, load_yaml_file


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "config_dir", str(tmp_path))
    monkeypatch.setattr(paths, "db_dir", str(tmp_path / "db"))
    (tmp_path / "config.yaml").write_text(
        "bot_name: Bot\ntelegram_username: someone\ngithub_username: user\ngithub_repo: repo\n",
        encoding='utf8')
    (tmp_path / "tokens.yaml").write_text(
        "telegram: 0:aaa\ntelegram_beta: 0:bbb\nrapidapi: ccc\n", encoding='utf8')
    return tmp_path


def test_load_yaml_file_reads_mapping(tmp_path):
    path = tmp_path / "x.yaml"
    path.write_text("a: 1\nb: two\n", encoding='utf8')
    assert load_yaml_file(str(path)) == {'a': 1, 'b': "two"}


def test_load_yaml_file_treats_empty_as_mapping(tmp_path):
    path = tmp_path / "x.yaml"
    path.write_text("", encoding='utf8')
    assert load_yaml_file(str(path)) == {}


def test_load_yaml_file_raises_when_required(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_yaml_file(str(tmp_path / "nope.yaml"))


def test_load_yaml_file_optional_returns_empty(tmp_path):
    assert load_yaml_file(str(tmp_path / "nope.yaml"), False) == {}


def test_settings(config_dir):
    config = Config()
    assert config.bot_name == "Bot"
    assert config.telegram_username == "someone"
    assert config.github_username == "user"
    assert config.github_repo == "repo"


def test_missing_setting_raises(config_dir):
    config = Config()
    with pytest.raises(KeyError):
        config.setting('nope')
    assert config.setting('nope', "fallback") == "fallback"


def test_tokens(config_dir):
    config = Config()
    assert config.token('rapidapi') == "ccc"
    assert config.has_token('rapidapi')
    assert not config.has_token('spotify_id')
    with pytest.raises(KeyError):
        config.token('spotify_id')


def test_worker_threads_have_a_default(config_dir):
    assert Config().worker_threads == 8


def test_worker_threads_can_be_set(config_dir):
    (config_dir / "config.yaml").write_text("bot_name: Bot\nworker_threads: 16\n", encoding='utf8')
    assert Config().worker_threads == 16


def test_worker_threads_never_drop_below_one(config_dir):
    (config_dir / "config.yaml").write_text("bot_name: Bot\nworker_threads: 0\n", encoding='utf8')
    assert Config().worker_threads == 1


def test_the_beta_token_is_optional(config_dir):
    (config_dir / "tokens.yaml").write_text("telegram: 0:aaa\n", encoding='utf8')
    assert Config().telegram_token == "0:aaa"
    with pytest.raises(KeyError) as error:
        _ = Config(True).telegram_token
    assert "telegram_beta" in str(error.value)


def test_beta_switches_name_token_and_database(config_dir):
    normal = Config()
    beta = Config(True)
    assert normal.bot_name == "Bot" and beta.bot_name == "BetaBot"
    assert normal.telegram_token == "0:aaa" and beta.telegram_token == "0:bbb"
    assert normal.database_file.endswith("bot.db")
    assert beta.database_file.endswith("bot-beta.db")


def test_modules_all_enabled_without_file(config_dir):
    config = Config()
    assert config.is_module_enabled('tiktok')
    assert config.is_module_enabled('anything')


def test_modules_file_only_disables_listed_ones(config_dir):
    (config_dir / "modules.yaml").write_text("youtube: false\ntiktok: true\n", encoding='utf8')
    config = Config()
    assert not config.is_module_enabled('youtube')
    assert config.is_module_enabled('tiktok')
    assert config.is_module_enabled('reminder')


def test_listed_modules(config_dir):
    assert Config().listed_modules() == []
    (config_dir / "modules.yaml").write_text("youtube: false\ntiktok: true\n", encoding='utf8')
    assert Config().listed_modules() == ["tiktok", "youtube"]
