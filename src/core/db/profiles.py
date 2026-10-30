from core.db.connection import Database
from core.profile import Profile

columns = ("sex", "born", "weight_unit", "height_unit")


class Profiles:
    def __init__(self, database: Database) -> None:
        self._db = database

    def get(self, user_id: int) -> Profile:
        row = self._db.query_one("SELECT sex, born, weight_unit, height_unit FROM user_profiles WHERE user_id = ?;",
                                 (user_id, ))
        return Profile(row['sex'], row['born'], row['weight_unit'], row['height_unit']) if row else Profile()

    def set(self, user_id: int, column: str, value: str | None) -> None:
        if column not in columns:
            raise ValueError("Unknown profile column: " + column)
        self._db.execute("INSERT INTO user_profiles (user_id, " + column + ") VALUES (?, ?) "
                         "ON CONFLICT(user_id) DO UPDATE SET " + column + " = excluded." + column + ";",
                         (user_id, value))
