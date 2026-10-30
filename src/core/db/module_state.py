from core.db.connection import Database


class ModuleState:
    def __init__(self, database: Database) -> None:
        self._db = database

    def get(self, user_id: int, module: str, key: str, default: str | None = None) -> str | None:
        row = self._db.query_one(
            "SELECT value FROM user_module_state WHERE user_id = ? AND module = ? AND key = ?;",
            (user_id, module, key))
        return row['value'] if row else default

    def set(self, user_id: int, module: str, key: str, value: str | None) -> None:
        self._db.execute("""
            INSERT INTO user_module_state (user_id, module, key, value) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, module, key) DO UPDATE SET value = excluded.value; """,
                         (user_id, module, key, value))

    def get_all(self, user_id: int, module: str) -> dict[str, str | None]:
        rows = self._db.query_all(
            "SELECT key, value FROM user_module_state WHERE user_id = ? AND module = ?;",
            (user_id, module))
        return {row['key']: row['value'] for row in rows}

    def delete(self, user_id: int, module: str, key: str) -> None:
        self._db.execute(
            "DELETE FROM user_module_state WHERE user_id = ? AND module = ? AND key = ?;",
            (user_id, module, key))

    def clear(self, user_id: int, module: str) -> None:
        self._db.execute("DELETE FROM user_module_state WHERE user_id = ? AND module = ?;",
                         (user_id, module))

    def forget_prefixed(self, user_id: int, prefix: str, kept: tuple[str, str] | None = None) -> None:
        module, key = kept or ("", "")
        self._db.execute("DELETE FROM user_module_state WHERE user_id = ? AND substr(key, 1, ?) = ? "
                         "AND NOT (module = ? AND key = ?);", (user_id, len(prefix), prefix, module, key))
