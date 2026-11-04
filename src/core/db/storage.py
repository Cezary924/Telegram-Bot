import os

from core.db.access import Access
from core.db.bot_state import BotState
from core.db.connection import Database
from core.db.module_db import ModuleDatabase
from core.db.module_state import ModuleState
from core.db.navigation import Navigation
from core.db.notifications import Notifications
from core.db.profiles import Profiles
from core.db.user_settings import UserSettings
from core.db.users import Users

schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.sql")
named_by_module = [("user_module_access", "module"), ("default_module_access", "module"), ("access_requests", "module"),
                   ("user_module_state", "module"), ("user_notifications", "source"), ("user_screens", "module"),
                   ("user_screen_arguments", "module")]


class Storage:
    def __init__(self, path: str) -> None:
        self.database = Database(path)
        with open(schema_file, encoding='utf8') as f:
            self.database.execute_script(f.read())
        self.users = Users(self.database)
        self.settings = UserSettings(self.database)
        self.notifications = Notifications(self.database, self.settings)
        self.access = Access(self.database)
        self.navigation = Navigation(self.database)
        self.module_state = ModuleState(self.database)
        self.state = BotState(self.database)
        self.profiles = Profiles(self.database)

    def for_module(self, module_name: str) -> ModuleDatabase:
        return ModuleDatabase(self.database, module_name)

    def take_over(self, old: str, new: str) -> None:
        for table, column in named_by_module:
            self.database.execute("UPDATE OR IGNORE " + table + " SET " + column + " = ? WHERE " + column + " = ?;",
                                  (new, old))
            self.database.execute("DELETE FROM " + table + " WHERE " + column + " = ?;", (old, ))
        before, after = self.for_module(old), self.for_module(new)
        taken = after.table_names()
        for name in before.table_names():
            renamed = after.table(name.removeprefix(before.prefix))
            if name.startswith(before.prefix) and renamed not in taken:
                self.database.execute("ALTER TABLE " + name + " RENAME TO " + renamed + ";")

    def close(self) -> None:
        self.database.close()
