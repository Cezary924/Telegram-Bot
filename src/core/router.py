import sqlite3
from threading import Thread
from typing import Callable

import telebot
from telebot.apihelper import ApiTelegramException

from core import callbacks, middleware
from core.context import User, controls_for, create_context, heading_for, send_to, user_from_row
from core.i18n import core_namespace, default_language
from core.log import print_error, print_log
from core.module import Module
from core.roles import Role
from core.services import Services
from core.ui.keyboard import back_action, close_action, command_action, delete_message, home_action
from core.ui.view import View, render
from core.utils import not_none


class Router:
    def __init__(self, services: Services) -> None:
        self._services = services
        self._tasks: list[Thread] = []
        self._has_admin = False

    @property
    def _bot(self) -> telebot.TeleBot:
        return not_none(self._services.bot, "the bot is not built yet")

    def core_text(self, key: str, language: str) -> str:
        return self._services.catalog.text(core_namespace, key, language)

    def language_for(self, user_id: int, telegram_language: str | None) -> str:
        row = self._services.storage.settings.get(user_id)
        if row is not None:
            return row['language']
        return "pl" if (telegram_language or "").startswith("pl") else default_language

    def promote_first_admin(self, from_user: telebot.types.User) -> None:
        if self._has_admin:
            return
        wanted = self._services.config.telegram_username.strip().lstrip("@")
        if not wanted or self._services.storage.users.get_by_role(Role.ADMIN):
            self._has_admin = True
            return
        if (from_user.username or "").casefold() != wanted.casefold():
            return
        self._services.storage.users.set_role(from_user.id, Role.ADMIN)
        self._has_admin = True
        print_log("@" + wanted + " (" + str(from_user.id) + ") is now the first Admin.")

    def load_user(self, from_user: telebot.types.User) -> User:
        users = self._services.storage.users
        is_new = users.save(from_user.id, from_user.first_name or "", from_user.last_name or "",
                            from_user.username or "")
        self.promote_first_admin(from_user)
        language = self.language_for(from_user.id, from_user.language_code)
        user = user_from_row(not_none(users.get(from_user.id)), language)
        if is_new:
            self.alert_admins(user)
        return user

    def alert_admins(self, user: User) -> None:
        settings = self._services.storage.settings
        for admin in self._services.storage.users.get_by_role(Role.ADMIN):
            if not settings.has_admin_alerts(admin['id']):
                continue
            text = self._services.catalog.text(core_namespace, "new_user",
                                               settings.get_language(admin['id']),
                                               name=user.first_name, id=str(user.id))
            send_to(self._services, core_namespace, admin['id'], View(text))

    def send(self, user: User, module_name: str, view: View) -> telebot.types.Message:
        heading = heading_for(self._services, module_name, view, user.language)
        controls = controls_for(self._services, module_name, view, user.language)
        text, markup = render(view, module_name, controls, heading)
        return self._bot.send_message(user.id, text, parse_mode=view.parse_mode,
                                      reply_markup=markup)

    def send_core(self, user: User, key: str) -> None:
        self.send(user, core_namespace, View(self.core_text(key, user.language), parse_mode=None))

    def close_screen(self, user: User) -> None:
        navigation = self._services.storage.navigation
        current = navigation.current(user.id)
        if current is not None:
            delete_message(self._bot, user.id, current['message_id'])
        navigation.clear(user.id)

    def show(self, user: User, module_name: str, view: View, anchor: int | None) -> int:
        heading = heading_for(self._services, module_name, view, user.language)
        controls = controls_for(self._services, module_name, view, user.language)
        text, markup = render(view, module_name, controls, heading)
        if anchor is not None:
            try:
                self._bot.edit_message_text(text, user.id, anchor, parse_mode=view.parse_mode,
                                            reply_markup=markup)
                return anchor
            except ApiTelegramException as error:
                if "not modified" in str(error):
                    return anchor
        return self._bot.send_message(user.id, text, parse_mode=view.parse_mode,
                                      reply_markup=markup).message_id

    def open_screen(self, user: User, module_name: str, view: View, is_typed: bool = False) -> None:
        navigation = self._services.storage.navigation
        current = navigation.current(user.id)
        anchor = current['message_id'] if current is not None else None
        if is_typed:
            self.close_screen(user)
            anchor = None
        navigation.remember(user.id, module_name, view.name, view.argument)
        navigation.set_current(user.id, module_name, view.name, view.argument,
                               self.show(user, module_name, view, anchor))

    def present(self, user: User, module_name: str, result, is_typed: bool = False) -> None:
        if result is None:
            return
        view = View(result, heading=None) if isinstance(result, str) else result
        if not isinstance(view, View):
            return
        if view.is_screen:
            self.open_screen(user, module_name, view, is_typed)
            return
        self.send(user, module_name, view)

    def run(self, module: Module, handler, role: Role, user: User,
            message: telebot.types.Message | None = None, arguments: tuple[str, ...] = (),
            is_background: bool = False, is_typed: bool = False) -> None:
        blocked = middleware.check(self._services, user, role)
        if blocked is not None:
            self.send(user, core_namespace, blocked)
            return
        ctx = create_context(self._services, module, user, message, arguments)
        if is_background:
            self.start_task(module, handler, ctx, user, is_typed)
            return
        self.execute(module, handler, ctx, user, is_typed)

    def start_task(self, module: Module, handler, ctx, user: User, is_typed: bool = False) -> None:
        self._tasks = [task for task in self._tasks if task.is_alive()]
        task = Thread(target=self.execute, args=(module, handler, ctx, user, is_typed), daemon=True,
                      name="task-" + module.name)
        self._tasks.append(task)
        task.start()

    def wait_for_tasks(self, timeout: float = 5.0) -> None:
        for task in list(self._tasks):
            task.join(timeout)

    def execute(self, module: Module, handler, ctx, user: User, is_typed: bool = False) -> None:
        try:
            result = handler(ctx)
            self.present(ctx.user, module.name, result, is_typed)
        except Exception as error:
            print_error("Handler failed in '" + module.name + "' - " + type(error).__name__ + ".",
                        str(error))
            self.send_core(user, "error")

    def gate(self, user: User) -> bool:
        blocked = middleware.check(self._services, user, Role.GUEST)
        if blocked is None:
            return True
        self.send(user, core_namespace, blocked)
        return False

    def handle_message(self, message: telebot.types.Message) -> None:
        if message.from_user is None:
            return
        user = self.load_user(message.from_user)
        text = message.text or ""
        print_log("Message: " + user.label + ".", text)
        if not self.gate(user):
            return
        if text.startswith("/"):
            self.handle_command(user, message, text)
            return
        if self.handle_state(user, message):
            return
        if self.handle_matchers(user, message):
            return
        self.send_core(user, "unknown_message")

    def handle_command(self, user: User, message: telebot.types.Message, text: str) -> None:
        name = text[1:].split()[0].split("@")[0].lower() if len(text) > 1 else ""
        found = self._services.registry.command(name)
        if found is None:
            self.send_core(user, "unknown_command")
            return
        self.close_screen(user)
        module, command = found
        self.run(module, command.handler, command.role, user, message,
                 is_background=command.is_background, is_typed=True)

    def handle_state(self, user: User, message: telebot.types.Message) -> bool:
        current = self._services.storage.navigation.current(user.id)
        if current is None:
            return False
        found = self._services.registry.state(current['module'], current['view'])
        if found is None:
            return False
        module, state = found
        self.run(module, state.handler, state.role, user, message,
                 (current['argument'],) if current['argument'] else (), state.is_background,
                 is_typed=True)
        return True

    def handle_matchers(self, user: User, message: telebot.types.Message) -> bool:
        for module, matcher in self._services.registry.matchers():
            try:
                if not matcher.predicate(message.text or ""):
                    continue
            except Exception as error:
                print_error("Matcher failed in '" + module.name + "' - " +
                            type(error).__name__ + ".", str(error))
                continue
            self.run(module, matcher.handler, matcher.role, user, message,
                     is_background=matcher.is_background, is_typed=True)
            return True
        return False

    def answer(self, callback: telebot.types.CallbackQuery) -> None:
        try:
            self._bot.answer_callback_query(callback.id)
        except ApiTelegramException as error:
            print_error("Could not answer a button press - " + type(error).__name__ + ".", str(error))

    def handle_callback(self, callback: telebot.types.CallbackQuery) -> None:
        self.answer(callback)
        user = self.load_user(callback.from_user)
        print_log("Callback: " + user.label + ".", callback.data or "")
        screen = callback.message
        if not isinstance(screen, telebot.types.Message):
            self.send_core(user, "not_working_buttons")
            return
        try:
            module_name, action, arguments = callbacks.parse(callback.data or "")
        except ValueError:
            self.send_core(user, "not_working_buttons")
            return
        if module_name == core_namespace:
            if middleware.check_banned(self._services, user) is None:
                self.handle_core_callback(user, screen, action, arguments)
            else:
                self.send_core(user, "banned_info")
            return
        if not self.gate(user):
            return
        found = self._services.registry.callback(module_name, action)
        if found is None:
            self.send_core(user, "not_working_buttons")
            return
        module, entry = found
        self.run(module, entry.handler, entry.role, user, screen, tuple(arguments),
                 entry.is_background)

    def handle_core_callback(self, user: User, screen: telebot.types.Message,
                             action: str, arguments: list[str]) -> None:
        if action == back_action:
            self.handle_back(user, screen)
        elif action == home_action:
            self.handle_home(user, screen)
        elif action == close_action:
            self.handle_close(user, screen)
        elif action == middleware.consent_accept_action:
            self.accept_consent(user)
        elif action == middleware.consent_decline_action:
            self.send_core(user, "consent.declined")
        elif action == command_action and arguments:
            self.handle_command(user, screen, "/" + arguments[0])
        elif action == middleware.consent_language_action and arguments:
            self.switch_consent_language(user, screen, arguments[0])
        else:
            self.send_core(user, "not_working_buttons")

    def leave_screen(self, user: User, screen: telebot.types.Message) -> sqlite3.Row | None:
        current = self._services.storage.navigation.current(user.id)
        if current is None or current['message_id'] != screen.message_id:
            self.send_core(user, "not_working_buttons")
            return None
        return current

    def open_named(self, user: User, module: Module, name: str,
                   screen: telebot.types.Message) -> None:
        found = self._services.registry.view(module.name, name)
        if found is None:
            self.close_screen(user)
            self.send_core(user, "not_working_buttons")
            return
        argument = self._services.storage.navigation.remembered(user.id, module.name, name)
        ctx = create_context(self._services, module, user, screen,
                             (argument,) if argument else ())
        self.present(user, module.name, found[1].handler(ctx))

    def step_out(self, user: User, screen: telebot.types.Message, to_root: bool) -> None:
        current = self.leave_screen(user, screen)
        if current is None:
            return
        module = self._services.registry.get(current['module'])
        if module is None:
            self.close_screen(user)
            self.send_core(user, "not_working_buttons")
            return
        branch = module.branch(current['view'])
        name = branch[0].name if to_root and branch else module.parent_of(current['view'])
        if not name or name == current['view']:
            self.close_screen(user)
            self.send_core(user, "menu_closed")
            return
        self.open_named(user, module, name, screen)

    def handle_back(self, user: User, screen: telebot.types.Message) -> None:
        self.step_out(user, screen, False)

    def handle_home(self, user: User, screen: telebot.types.Message) -> None:
        self.step_out(user, screen, True)

    def handle_close(self, user: User, screen: telebot.types.Message) -> None:
        if self.leave_screen(user, screen) is None:
            return
        self.close_screen(user)
        self.send_core(user, "menu_closed")

    def accept_consent(self, user: User) -> None:
        self._services.storage.users.set_consent(user.id, True)
        self._services.storage.settings.set_language(user.id, user.language)
        self.send_core(user, "consent.accepted")

    def switch_consent_language(self, user: User, screen: telebot.types.Message,
                                language: str) -> None:
        self._services.storage.settings.set_language(user.id, language)
        switched = middleware.consent_view(self._services, language)
        text, markup = render(switched, core_namespace)
        self._bot.edit_message_text(text, user.id, screen.message_id,
                                    parse_mode=switched.parse_mode, reply_markup=markup)

    @staticmethod
    def guarded(handler: Callable) -> Callable:
        def take(update) -> None:
            try:
                handler(update)
            except Exception as error:
                print_error("Handling an update failed - " + type(error).__name__ + ".", str(error))

        return take

    def register(self, bot: telebot.TeleBot) -> None:
        bot.callback_query_handler(func=lambda callback: True)(self.guarded(self.handle_callback))
        bot.message_handler(func=lambda message: True,
                            content_types=['text'])(self.guarded(self.handle_message))
