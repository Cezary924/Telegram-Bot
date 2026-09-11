import sqlite3

from core.db.storage import Storage

schema_of_2_0_0 = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    role INTEGER NOT NULL DEFAULT 0,
    has_consent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_navigation_stacks (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    module TEXT NOT NULL,
    view TEXT NOT NULL,
    argument TEXT,
    message_id INTEGER,
    PRIMARY KEY (user_id, position)
);
"""


def database_of_2_0_0(tmp_path) -> str:
    path = str(tmp_path / "bot.db")
    connection = sqlite3.connect(path)
    connection.executescript(schema_of_2_0_0)
    when = "2026-01-01 10:00:00"
    connection.execute("""
        INSERT INTO users (id, first_name, last_name, username, role, has_consent, created_at, seen_at)
        VALUES (1, 'First', 'Last', 'username', 2, 1, ?, ?); """, (when, when))
    connection.execute("""
        INSERT INTO user_navigation_stacks (user_id, position, module, view, argument, message_id)
        VALUES (1, 0, 'module1', 'view1', NULL, 555); """)
    connection.commit()
    connection.close()
    return path


def test_a_database_from_2_0_0_gains_what_it_is_missing(tmp_path):
    storage = Storage(database_of_2_0_0(tmp_path))
    names = [row['name'] for row in storage.database.query_all(
        "SELECT name FROM sqlite_master WHERE type = 'table';")]
    assert "user_screens" in names and "user_screen_arguments" in names
    storage.close()


def test_a_database_from_2_0_0_keeps_what_it_had(tmp_path):
    storage = Storage(database_of_2_0_0(tmp_path))
    person = storage.users.get(1)
    assert person is not None and person['first_name'] == "First"
    assert storage.navigation.current(1) is None
    storage.close()


def test_a_database_from_2_0_0_takes_new_rows(tmp_path):
    storage = Storage(database_of_2_0_0(tmp_path))
    storage.navigation.set_current(1, "module1", "view2", None, 777)
    storage.navigation.remember(1, "module1", "view2", "3")
    current = storage.navigation.current(1)
    assert current is not None and current['message_id'] == 777
    assert storage.navigation.remembered(1, "module1", "view2") == "3"
    storage.close()
