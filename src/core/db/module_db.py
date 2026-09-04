import re
import sqlite3

from core.db.connection import Database

created_object_pattern = re.compile(
    r"\bCREATE\s+(?:TEMP\s+|TEMPORARY\s+)?(?:UNIQUE\s+)?(?:TABLE|INDEX|VIEW|TRIGGER)\s+"
    r"(?:IF\s+NOT\s+EXISTS\s+)?[\"'`\[]?([A-Za-z0-9_]+)", re.IGNORECASE)


class ModuleDatabase:
    def __init__(self, database: Database, module_name: str) -> None:
        self._db = database
        self.module_name = module_name
        self.prefix = "module_" + module_name + "_"

    def table(self, name: str) -> str:
        return self.prefix + name

    def apply_schema(self, sql: str) -> None:
        for name in created_object_pattern.findall(sql):
            if not name.startswith(self.prefix):
                raise ValueError("Module '" + self.module_name + "' creates '" + name +
                                 "' without the required '" + self.prefix + "' prefix")
        self._db.execute_script(sql)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._db.execute(sql, params)

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self._db.query_one(sql, params)

    def query_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._db.query_all(sql, params)

    def table_names(self) -> list[str]:
        return self._db.table_names(self.prefix)

    def drop_tables(self) -> None:
        for name in self.table_names():
            self._db.execute("DROP TABLE IF EXISTS " + name + ";")
