import sqlite3

from core.db.connection import Database, now_text
from core.roles import Role


class Users:
    def __init__(self, database: Database) -> None:
        self._db = database

    def exists(self, user_id: int) -> bool:
        return self._db.query_one("SELECT 1 FROM users WHERE id = ?;", (user_id, )) is not None

    def get(self, user_id: int) -> sqlite3.Row | None:
        return self._db.query_one("SELECT * FROM users WHERE id = ?;", (user_id, ))

    def save(self, user_id: int, first_name: str = "", last_name: str = "", username: str = "") -> None:
        now = now_text()
        self._db.execute("""
            INSERT INTO users (id, first_name, last_name, username, created_at, seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                username = excluded.username,
                seen_at = excluded.seen_at; """,
                         (user_id, first_name, last_name, username, now, now))

    def get_role(self, user_id: int) -> Role:
        row = self._db.query_one("SELECT role FROM users WHERE id = ?;", (user_id, ))
        return Role.from_value(row['role']) if row else Role.GUEST

    def set_role(self, user_id: int, role: Role) -> None:
        self._db.execute("UPDATE users SET role = ? WHERE id = ?;", (int(role), user_id))

    def has_consent(self, user_id: int) -> bool:
        row = self._db.query_one("SELECT has_consent FROM users WHERE id = ?;", (user_id, ))
        return bool(row['has_consent']) if row else False

    def set_consent(self, user_id: int, has_consent: bool) -> None:
        self._db.execute("UPDATE users SET has_consent = ? WHERE id = ?;", (int(has_consent), user_id))

    def get_all(self) -> list[sqlite3.Row]:
        return self._db.query_all("SELECT * FROM users ORDER BY id;")

    def get_by_role(self, role: Role) -> list[sqlite3.Row]:
        return self._db.query_all("SELECT * FROM users WHERE role = ? ORDER BY id;", (int(role), ))

    def count_by_role(self) -> dict[Role, int]:
        rows = self._db.query_all("SELECT role, COUNT(1) AS total FROM users GROUP BY role;")
        return {Role.from_value(row['role']): row['total'] for row in rows}

    def delete(self, user_id: int) -> None:
        self._db.execute("DELETE FROM users WHERE id = ?;", (user_id, ))
