from core.db.connection import Database
from core.roles import Role


class Access:
    def __init__(self, database: Database) -> None:
        self._db = database

    def is_allowed(self, user_id: int, module: str, role: Role) -> bool:
        if role >= Role.ADMIN:
            return True
        row = self._db.query_one("SELECT is_allowed FROM user_module_access WHERE user_id = ? AND module = ?;",
                                 (user_id, module))
        if row is not None:
            return bool(row['is_allowed'])
        return module in self.defaults()

    def allow(self, user_id: int, module: str, is_allowed: bool) -> None:
        self._db.execute("""
            INSERT INTO user_module_access (user_id, module, is_allowed) VALUES (?, ?, ?)
            ON CONFLICT(user_id, module) DO UPDATE SET is_allowed = excluded.is_allowed; """,
                         (user_id, module, int(is_allowed)))

    def defaults(self) -> set[str]:
        return {row['module'] for row in self._db.query_all("SELECT module FROM default_module_access;")}

    def set_default(self, module: str, is_default: bool) -> None:
        if is_default:
            self._db.execute("INSERT OR IGNORE INTO default_module_access (module) VALUES (?);", (module, ))
        else:
            self._db.execute("DELETE FROM default_module_access WHERE module = ?;", (module, ))

    def ask(self, user_id: int, module: str) -> bool:
        if self._db.query_one("SELECT user_id FROM access_requests WHERE user_id = ? AND module = ?;",
                              (user_id, module)) is not None:
            return False
        self._db.execute("INSERT INTO access_requests (user_id, module) VALUES (?, ?);", (user_id, module))
        return True

    def answer(self, user_id: int, module: str) -> bool:
        if self._db.query_one("SELECT user_id FROM access_requests WHERE user_id = ? AND module = ?;",
                              (user_id, module)) is None:
            return False
        self._db.execute("DELETE FROM access_requests WHERE user_id = ? AND module = ?;", (user_id, module))
        return True
