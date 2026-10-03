from core.db.connection import Database
from core.db.user_settings import UserSettings


class Notifications:
    def __init__(self, database: Database, settings: UserSettings) -> None:
        self._db = database
        self._settings = settings

    def is_loud(self, user_id: int, source: str) -> bool:
        row = self._db.query_one("SELECT is_loud FROM user_notifications WHERE user_id = ? AND source = ?;",
                                 (user_id, source))
        return bool(row['is_loud']) if row else self._settings.has_notifications(user_id)

    def set_loud(self, user_id: int, source: str, is_loud: bool) -> None:
        self._db.execute("""
            INSERT INTO user_notifications (user_id, source, is_loud) VALUES (?, ?, ?)
            ON CONFLICT(user_id, source) DO UPDATE SET is_loud = excluded.is_loud; """,
                         (user_id, source, int(is_loud)))

    def set_all(self, user_id: int, sources: list[str], is_loud: bool) -> None:
        self._settings.set_notifications(user_id, is_loud)
        for source in sources:
            self.set_loud(user_id, source, is_loud)

    def is_blocked(self, user_id: int) -> bool:
        return self._db.query_one("SELECT user_id FROM user_notification_blocks WHERE user_id = ?;",
                                  (user_id, )) is not None

    def set_blocked(self, user_id: int, is_blocked: bool) -> None:
        if is_blocked:
            self._db.execute("INSERT OR IGNORE INTO user_notification_blocks (user_id) VALUES (?);", (user_id, ))
        else:
            self._db.execute("DELETE FROM user_notification_blocks WHERE user_id = ?;", (user_id, ))
