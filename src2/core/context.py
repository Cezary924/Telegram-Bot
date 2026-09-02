import os
import sqlite3
import telebot
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from core import paths
from core.config import Config
from core.db.module_db import ModuleDatabase
from core.db.user_settings import UserSettings
from core.db.users import Users
from core.i18n import supported_languages
from core.log import print_error, print_log
from core.module import Module
from core.registry import Registry
from core.roles import Role
from core.services import Services
from core.version import Version
from core.ui.keyboard import delete_message
from core.utils import not_none


@dataclass(frozen=True)
class User:
    id: int
    first_name: str
    last_name: str
    username: str
    role: Role
    language: str
    has_consent: bool = False

    @property
    def label(self) -> str:
        return self.first_name + " (" + str(self.id) + ")"


def user_from_row(row: sqlite3.Row, language: str) -> User:
    return User(row['id'], row['first_name'], row['last_name'], row['username'],
                Role.from_value(row['role']), language, bool(row['has_consent']))


class UserState:
    def __init__(self, services: Services, module_name: str, user_id: int) -> None:
        self._state = services.storage.module_state
        self._module_name = module_name
        self._user_id = user_id

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._state.get(self._user_id, self._module_name, key, default)

    def set(self, key: str, value: str | None) -> None:
        self._state.set(self._user_id, self._module_name, key, value)

    def delete(self, key: str) -> None:
        self._state.delete(self._user_id, self._module_name, key)

    def all(self) -> dict[str, str | None]:
        return self._state.get_all(self._user_id, self._module_name)

    def clear(self) -> None:
        self._state.clear(self._user_id, self._module_name)

    def __getitem__(self, key: str) -> str | None:
        return self.get(key)

    def __setitem__(self, key: str, value: str | None) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


class UserNavigation:
    def __init__(self, services: Services, module_name: str, user_id: int) -> None:
        self._navigation = services.storage.navigation
        self._module_name = module_name
        self._user_id = user_id

    def push(self, view: str, argument: str | None = None, message_id: int | None = None) -> int:
        return self._navigation.push(self._user_id, self._module_name, view, argument, message_id)

    def pop(self) -> sqlite3.Row | None:
        return self._navigation.pop(self._user_id)

    def top(self) -> sqlite3.Row | None:
        return self._navigation.top(self._user_id)

    def depth(self) -> int:
        return self._navigation.depth(self._user_id)

    def set_message_id(self, message_id: int) -> None:
        self._navigation.set_message_id(self._user_id, message_id)

    def clear(self) -> None:
        self._navigation.clear(self._user_id)


def send_to(services: Services, module_name: str, user_id: int, view) -> None:
    from core.ui.view import View, render
    if isinstance(view, str):
        view = View(view, parse_mode=None)
    language = services.storage.settings.get_language(user_id)
    return_text = services.catalog.text("core", "return_button", language)
    text, markup = render(view, module_name, return_text)
    is_silent = not services.storage.settings.has_notifications(user_id)
    bot = not_none(services.bot, "the bot is not built yet")
    bot.send_message(user_id, text, parse_mode=view.parse_mode,
                     reply_markup=markup, disable_notification=is_silent)


class Ctx:
    def __init__(self, services: Services, module: Module, user: User,
                 message: telebot.types.Message | None = None,
                 arguments: tuple[str, ...] = ()) -> None:
        self._services = services
        self.module = module
        self.user = user
        self.message = message
        self.arguments = arguments
        self.state = UserState(services, module.name, user.id)
        self.nav = UserNavigation(services, module.name, user.id)
        self.db = ModuleDatabase(services.storage.database, module.name)

    @property
    def text(self) -> str:
        return (self.message.text or "") if self.message is not None else ""

    def t(self, key: str, /, **values) -> str:
        return self._services.catalog.text(self.module.name, key, self.user.language, **values)

    def token(self, name: str) -> str:
        if name not in self.module.tokens:
            raise PermissionError("Module '" + self.module.name + "' did not declare token '" + name + "'")
        return self._services.config.token(name)

    def reply(self, view) -> None:
        send_to(self._services, self.module.name, self.user.id, view)

    def close_screen(self) -> None:
        top = self.nav.pop()
        if top is not None and self._services.bot is not None:
            delete_message(self._services.bot, self.user.id, top['message_id'])

    def log(self, info: str, message_text: str = "") -> None:
        print_log(info + ": " + self.user.label + ".", message_text)

    def error(self, info: str, message_text: str = "") -> None:
        print_error(info + " in '" + self.module.name + "'.", message_text)

    @contextmanager
    def workspace(self):
        path = paths.make_dir(os.path.join(paths.temp_dir, self.module.name, uuid.uuid4().hex))
        try:
            yield path
        finally:
            paths.remove_dir(path)


class JobCtx:
    def __init__(self, services: Services, module: Module) -> None:
        self._services = services
        self.module = module
        self.db = ModuleDatabase(services.storage.database, module.name)

    @property
    def uptime(self) -> timedelta:
        return datetime.now() - self._services.started_at

    @property
    def languages(self) -> list[tuple[str, str]]:
        catalog = self._services.catalog
        return [(language, catalog.label(language)) for language in supported_languages()]

    def language_of(self, user_id: int) -> str:
        return self._services.storage.settings.get_language(user_id)

    def t(self, key: str, language: str, /, **values) -> str:
        return self._services.catalog.text(self.module.name, key, language, **values)

    def send(self, user_id: int, view) -> None:
        send_to(self._services, self.module.name, user_id, view)

    def log(self, info: str) -> None:
        print_log(info + " in '" + self.module.name + "'.")

    def error(self, info: str, message_text: str = "") -> None:
        print_error(info + " in '" + self.module.name + "'.", message_text)


class AdvancedCtx(Ctx):
    @property
    def users(self) -> Users:
        return self._services.storage.users

    @property
    def settings(self) -> UserSettings:
        return self._services.storage.settings

    @property
    def registry(self) -> Registry:
        return self._services.registry

    @property
    def config(self) -> Config:
        return self._services.config

    @property
    def version(self) -> Version:
        return self._services.version

    @property
    def uptime(self) -> timedelta:
        return datetime.now() - self._services.started_at

    @property
    def languages(self) -> list[tuple[str, str]]:
        catalog = self._services.catalog
        return [(language, catalog.label(language)) for language in supported_languages()]

    def language_of(self, user_id: int) -> str:
        return self._services.storage.settings.get_language(user_id)

    def text_for(self, user_id: int, key: str, /, **values) -> str:
        return self._services.catalog.text(self.module.name, key, self.language_of(user_id), **values)

    def notify(self, user_id: int, view) -> None:
        send_to(self._services, self.module.name, user_id, view)

    def use_language(self, language: str) -> None:
        self._services.storage.settings.set_language(self.user.id, language)
        self.user = replace(self.user, language=language)


def create_context(services: Services, module: Module, user: User,
                   message: telebot.types.Message | None = None,
                   arguments: tuple[str, ...] = ()) -> Ctx:
    if module.is_internal:
        return AdvancedCtx(services, module, user, message, arguments)
    return Ctx(services, module, user, message, arguments)
