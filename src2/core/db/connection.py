import os
import sqlite3
import threading
from datetime import datetime

from core import paths


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, path: str) -> None:
        if path != ":memory:":
            paths.make_dir(os.path.dirname(path))
        self.path = path
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON;")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(sql, params)
            self._connection.commit()
            return cursor

    def execute_script(self, sql: str) -> None:
        with self._lock:
            self._connection.executescript(sql)
            self._connection.commit()

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(sql, params).fetchone()

    def query_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._connection.execute(sql, params).fetchall()

    def table_names(self, prefix: str = "") -> list[str]:
        rows = self.query_all(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE ? ORDER BY name;",
            (prefix + "%", ))
        return [row['name'] for row in rows]

    def close(self) -> None:
        with self._lock:
            self._connection.commit()
            self._connection.close()
