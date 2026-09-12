import sqlite3

from core.db.connection import Database


class Navigation:
    def __init__(self, database: Database) -> None:
        self._db = database

    def current(self, user_id: int) -> sqlite3.Row | None:
        return self._db.query_one("SELECT * FROM user_screens WHERE user_id = ?;", (user_id, ))

    def set_current(self, user_id: int, module: str, view: str,
                    argument: str | None, message_id: int) -> None:
        self._db.execute("""
            INSERT INTO user_screens (user_id, module, view, argument, message_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                module = excluded.module, view = excluded.view,
                argument = excluded.argument, message_id = excluded.message_id; """,
                         (user_id, module, view, argument, message_id))

    def clear(self, user_id: int) -> None:
        self._db.execute("DELETE FROM user_screens WHERE user_id = ?;", (user_id, ))

    def remember(self, user_id: int, module: str, view: str, argument: str | None) -> None:
        self._db.execute("""
            INSERT INTO user_screen_arguments (user_id, module, view, argument)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, module, view) DO UPDATE SET argument = excluded.argument; """,
                         (user_id, module, view, argument))

    def remembered(self, user_id: int, module: str, view: str) -> str | None:
        row = self._db.query_one("""
            SELECT argument FROM user_screen_arguments
            WHERE user_id = ? AND module = ? AND view = ?; """, (user_id, module, view))
        return row['argument'] if row else None

    def forget(self, user_id: int) -> None:
        self._db.execute("DELETE FROM user_screen_arguments WHERE user_id = ?;", (user_id, ))
