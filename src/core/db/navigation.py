import sqlite3

from core.db.connection import Database


class Navigation:
    def __init__(self, database: Database) -> None:
        self._db = database

    def depth(self, user_id: int) -> int:
        row = self._db.query_one(
            "SELECT COUNT(1) AS total FROM user_navigation_stacks WHERE user_id = ?;", (user_id, ))
        return row['total'] if row else 0

    def push(self, user_id: int, module: str, view: str,
             argument: str | None = None, message_id: int | None = None) -> int:
        position = self.depth(user_id)
        self._db.execute("""
            INSERT INTO user_navigation_stacks (user_id, position, module, view, argument, message_id)
            VALUES (?, ?, ?, ?, ?, ?); """,
                         (user_id, position, module, view, argument, message_id))
        return position

    def top(self, user_id: int) -> sqlite3.Row | None:
        return self._db.query_one("""
            SELECT * FROM user_navigation_stacks WHERE user_id = ?
            ORDER BY position DESC LIMIT 1; """, (user_id, ))

    def pop(self, user_id: int) -> sqlite3.Row | None:
        row = self.top(user_id)
        if row is None:
            return None
        self._db.execute("DELETE FROM user_navigation_stacks WHERE user_id = ? AND position = ?;",
                         (user_id, row['position']))
        return row

    def set_message_id(self, user_id: int, message_id: int) -> None:
        row = self.top(user_id)
        if row is None:
            return
        self._db.execute(
            "UPDATE user_navigation_stacks SET message_id = ? WHERE user_id = ? AND position = ?;",
            (message_id, user_id, row['position']))

    def clear(self, user_id: int) -> None:
        self._db.execute("DELETE FROM user_navigation_stacks WHERE user_id = ?;", (user_id, ))
