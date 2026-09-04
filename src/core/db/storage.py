import os

from core.db.bot_state import BotState
from core.db.connection import Database
from core.db.module_db import ModuleDatabase
from core.db.module_state import ModuleState
from core.db.navigation import Navigation
from core.db.user_settings import UserSettings
from core.db.users import Users

schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.sql")


class Storage:
    def __init__(self, path: str) -> None:
        self.database = Database(path)
        with open(schema_file, encoding='utf8') as f:
            self.database.execute_script(f.read())
        self.users = Users(self.database)
        self.settings = UserSettings(self.database)
        self.navigation = Navigation(self.database)
        self.module_state = ModuleState(self.database)
        self.state = BotState(self.database)

    def for_module(self, module_name: str) -> ModuleDatabase:
        return ModuleDatabase(self.database, module_name)

    def close(self) -> None:
        self.database.close()
