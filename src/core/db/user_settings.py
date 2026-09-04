import sqlite3

from core.db.connection import Database

default_language = "en"


class UserSettings:
    def __init__(self, database: Database) -> None:
        self._db = database

    def get(self, user_id: int) -> sqlite3.Row | None:
        return self._db.query_one("SELECT * FROM user_settings WHERE user_id = ?;", (user_id, ))

    def get_language(self, user_id: int) -> str:
        row = self.get(user_id)
        return row['language'] if row else default_language

    def set_language(self, user_id: int, language: str) -> None:
        self._db.execute("""
            INSERT INTO user_settings (user_id, language) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET language = excluded.language; """,
                         (user_id, language))

    def has_notifications(self, user_id: int) -> bool:
        row = self.get(user_id)
        return bool(row['has_notifications']) if row else True

    def has_admin_alerts(self, user_id: int) -> bool:
        row = self.get(user_id)
        return bool(row['has_admin_alerts']) if row else True

    def set_admin_alerts(self, user_id: int, has_admin_alerts: bool) -> None:
        self._db.execute("""
            INSERT INTO user_settings (user_id, has_admin_alerts) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET has_admin_alerts = excluded.has_admin_alerts; """,
                         (user_id, int(has_admin_alerts)))

    def set_notifications(self, user_id: int, has_notifications: bool) -> None:
        self._db.execute("""
            INSERT INTO user_settings (user_id, has_notifications) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET has_notifications = excluded.has_notifications; """,
                         (user_id, int(has_notifications)))
