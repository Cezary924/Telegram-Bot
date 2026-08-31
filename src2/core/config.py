import os

import yaml

from core import paths

default_worker_threads = 8


def load_yaml_file(path: str, is_required: bool = True) -> dict:
    if not os.path.isfile(path):
        if is_required:
            raise FileNotFoundError("Missing config file: " + path)
        return {}
    with open(path, encoding='utf8') as f:
        data = yaml.load(f, Loader=yaml.Loader)
    return data if data else {}


class Config:
    def __init__(self, is_beta: bool = False) -> None:
        self.is_beta = is_beta
        self._settings = load_yaml_file(paths.config_file("config.yaml"))
        self._tokens = load_yaml_file(paths.config_file("tokens.yaml"))
        self._modules = load_yaml_file(paths.config_file("modules.yaml"), False)

    def setting(self, name: str, default: str | None = None) -> str:
        value = self._settings.get(name, default)
        if value is None:
            raise KeyError("Missing setting in config.yaml: " + name)
        return str(value)

    def token(self, name: str) -> str:
        if name not in self._tokens:
            raise KeyError("Missing token in tokens.yaml: " + name)
        return str(self._tokens[name])

    def has_token(self, name: str) -> bool:
        return name in self._tokens

    def is_module_enabled(self, name: str) -> bool:
        return bool(self._modules.get(name, True))

    def listed_modules(self) -> list[str]:
        return sorted(str(name) for name in self._modules)

    @property
    def bot_name(self) -> str:
        name = self.setting('bot_name')
        return "Beta" + name if self.is_beta else name

    @property
    def telegram_username(self) -> str:
        return self.setting('telegram_username', "")

    @property
    def github_username(self) -> str:
        return self.setting('github_username', "")

    @property
    def github_repo(self) -> str:
        return self.setting('github_repo', "")

    @property
    def worker_threads(self) -> int:
        return max(1, int(self.setting('worker_threads', str(default_worker_threads))))

    @property
    def telegram_token(self) -> str:
        return self.token('telegram_beta' if self.is_beta else 'telegram')

    @property
    def database_file(self) -> str:
        return paths.db_file("bot-beta.db" if self.is_beta else "bot.db")
