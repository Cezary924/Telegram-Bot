from core.db.connection import Database


class BotState:
    def __init__(self, database: Database) -> None:
        self._db = database

    def get(self, key: str, default: str | None = None) -> str | None:
        row = self._db.query_one("SELECT value FROM bot_state WHERE key = ?;", (key, ))
        return row['value'] if row else default

    def set(self, key: str, value: str) -> None:
        self._db.execute("""
            INSERT INTO bot_state (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value; """, (key, value))
