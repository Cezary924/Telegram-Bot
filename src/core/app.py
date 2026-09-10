import signal
import sys
from datetime import datetime
from threading import Thread

import telebot

from core.config import Config
from core.context import JobCtx, send_to
from core.db.storage import Storage
from core.i18n import Catalog, core_namespace
from core.loader import Loader
from core.log import LoadingString, Logger, print_banner, print_error, print_log
from core.registry import Registry
from core.roles import Role
from core.router import Router
from core.scheduler import Scheduler
from core.services import Services
from core.ui.view import View
from core.utils import not_none, without_secrets
from core.version import read as read_version

version_key = "version"
stopped_key = "stopped_at"
told_key = "stop_told"
quiet_restart = 120.0


class App:
    def __init__(self, is_beta: bool = False) -> None:
        self.config = Config(is_beta)
        self.catalog = Catalog()
        self.catalog.load_core()
        self.storage = Storage(self.config.database_file)
        self.services = Services(self.config, self.catalog, self.storage, Registry(),
                                 version=read_version())
        self.loader = Loader(self.config, self.catalog, self.storage)
        self.router = Router(self.services)
        self.scheduler = Scheduler()
        self.logger: Logger | None = None

    @property
    def registry(self) -> Registry:
        return self.services.registry

    @property
    def bot(self) -> telebot.TeleBot:
        return not_none(self.services.bot, "the bot is not built yet")

    def load_modules(self) -> None:
        self.loader.load_all(self.registry)
        for module, job in self.registry.jobs():
            job_ctx = JobCtx(self.services, module)
            self.scheduler.add(module.name + "." + job.name,
                               lambda handler=job.handler, given=job_ctx: handler(given),
                               job.interval, job.is_aligned)

    def build_bot(self) -> telebot.TeleBot:
        bot = telebot.TeleBot(self.config.telegram_token, num_threads=self.config.worker_threads)
        self.services.bot = bot
        self.router.register(bot)
        return bot

    def publish_commands(self) -> None:
        for language in self.catalog.languages():
            commands = [telebot.types.BotCommand(command.name,
                                                 self.catalog.text(module.name, command.description, language))
                        for module, command in self.registry.commands()
                        if command.role <= Role.USER]
            if not commands:
                return
            try:
                self.bot.set_my_commands(commands, language_code=language)
            except Exception as error:
                print_error("Could not publish the command list - " + type(error).__name__ + ".", str(error))

    def announce_update(self) -> None:
        current = str(self.services.version)
        previous = self.storage.state.get(version_key)
        if previous == current:
            return
        self.storage.state.set(version_key, current)
        if previous is None:
            return
        print_log("The version changed from " + previous + " to " + current + ".")
        link = self.release_url()
        for row in self.storage.users.get_all():
            if not self.storage.settings.has_notifications(row['id']):
                continue
            text = self.catalog.text(core_namespace, "bot_updated",
                                     self.storage.settings.get_language(row['id']))
            send_to(self.services, core_namespace, row['id'], View(text + link))

    def release_url(self) -> str:
        user = self.config.github_username
        repository = self.config.github_repo
        tag = self.services.version.tag
        if not user or not repository or not tag:
            return ""
        return "\n\n" + "https://github.com/" + user + "/" + repository + "/releases/tag/" + tag

    def notify_admins(self, key: str, detail: str = "") -> bool:
        reached = False
        for row in self.storage.users.get_by_role(Role.ADMIN):
            language = self.storage.settings.get_language(row['id'])
            text = self.catalog.text(core_namespace, key, language)
            try:
                self.bot.send_message(row['id'], text + ("\n" + detail if detail else ""))
                reached = True
            except Exception as error:
                print_error("Could not notify the admin - " + type(error).__name__ + ".", str(error))
        return reached

    def away_for(self, stopped_at: str) -> float:
        try:
            return (datetime.now() - datetime.fromisoformat(stopped_at)).total_seconds()
        except ValueError:
            return quiet_restart

    def announce_start(self) -> None:
        stopped_at = self.storage.state.get(stopped_key)
        was_told = self.storage.state.get(told_key) == "1"
        self.storage.state.set(told_key, "0")
        away = self.away_for(stopped_at) if stopped_at is not None else quiet_restart
        if not was_told and away < quiet_restart:
            print_log("Back after " + str(round(away)) +
                      "s away, so nobody is told the Bot is back.")
            return
        self.notify_admins("bot_started")

    def start(self) -> None:
        logger = Logger()
        self.logger = logger
        sys.stdout = logger
        logger.hold()
        loading = LoadingString()
        Thread(target=loading.run, daemon=True).start()
        self.load_modules()
        self.build_bot()
        loading.stop()

        self.publish_commands()
        self.scheduler.start()
        with logger.direct():
            print_banner(self.config.bot_name, True)
        logger.release()
        self.announce_start()
        self.announce_update()

        for number in (signal.SIGINT, signal.SIGTERM):
            signal.signal(number, lambda caught, frame: self.stop())
        self.poll()

    def poll(self) -> None:
        try:
            self.bot.infinity_polling(timeout=100)
        except KeyboardInterrupt:
            self.stop()
        except Exception as error:
            print_error("Polling stopped - " + type(error).__name__ + ".", str(error))
            self.stop(1, type(error).__name__ + ": " + without_secrets(str(error)))

    def stop(self, code: int = 0, failure: str = "") -> None:
        self.storage.state.set(stopped_key, datetime.now().isoformat(timespec="seconds"))
        self.storage.state.set(told_key, "0")
        if self.services.bot is not None:
            told = self.notify_admins("bot_failed", failure) if failure \
                else self.notify_admins("bot_stopped")
            self.storage.state.set(told_key, "1" if told else "0")
        self.router.wait_for_tasks(2.0)
        self.scheduler.stop()
        if self.services.bot is not None:
            self.services.bot.stop_polling()
        self.storage.close()
        print_banner(self.config.bot_name, False)
        if self.logger is not None:
            self.logger.close()
        sys.exit(code)
