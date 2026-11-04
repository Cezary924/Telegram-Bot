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

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    language TEXT NOT NULL DEFAULT 'en',
    has_notifications INTEGER NOT NULL DEFAULT 1,
    has_admin_alerts INTEGER NOT NULL DEFAULT 1
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


def test_a_user_who_turned_notifications_off_in_2_0_0_gets_everything_silently(tmp_path):
    path = database_of_2_0_0(tmp_path)
    connection = sqlite3.connect(path)
    connection.execute("INSERT INTO user_settings (user_id, has_notifications) VALUES (1, 0);")
    connection.commit()
    connection.close()
    storage = Storage(path)
    assert not storage.notifications.is_loud(1, "reminder")
    assert not storage.notifications.is_blocked(1)
    storage.notifications.set_loud(1, "reminder", True)
    assert storage.notifications.is_loud(1, "reminder")
    storage.close()


def renamed_storage() -> Storage:
    storage = Storage(":memory:")
    for user_id in (1, 2):
        storage.users.save(user_id, "First", "Last", "username")
    storage.access.allow(1, "old", True)
    storage.access.allow(2, "old", False)
    storage.access.allow(2, "new", True)
    storage.access.set_default("old", True)
    storage.access.ask(1, "old")
    storage.module_state.set(1, "old", "goal", "2000")
    storage.notifications.set_loud(1, "old", False)
    storage.navigation.set_current(1, "old", "menu", None, 5)
    storage.navigation.remember(1, "old", "history", "2")
    storage.database.execute("CREATE TABLE module_old_items (id INTEGER PRIMARY KEY, name TEXT);")
    storage.database.execute("INSERT INTO module_old_items (name) VALUES ('kept');")
    return storage


def test_a_new_name_takes_over_what_the_old_one_had():
    storage = renamed_storage()
    storage.take_over("old", "new")
    assert storage.access.is_allowed(1, "new", storage.users.get_role(1))
    assert storage.access.is_allowed(2, "new", storage.users.get_role(2))
    assert storage.access.defaults() == {"new"}
    assert not storage.access.ask(1, "new")
    assert storage.module_state.get(1, "new", "goal") == "2000"
    assert not storage.notifications.is_loud(1, "new")
    assert storage.navigation.current(1)['module'] == "new"
    assert storage.navigation.remembered(1, "new", "history") == "2"
    assert storage.database.query_all("SELECT name FROM module_new_items;")[0]['name'] == "kept"
    for table, column in [("user_module_access", "module"), ("access_requests", "module"),
                          ("user_notifications", "source"), ("user_module_state", "module")]:
        assert storage.database.query_all("SELECT * FROM " + table + " WHERE " + column + " = 'old';") == []
    assert storage.database.table_names("module_old") == []
    storage.close()


def test_taking_over_twice_changes_nothing_more():
    storage = renamed_storage()
    storage.take_over("old", "new")
    storage.database.execute("CREATE TABLE module_old_items (id INTEGER PRIMARY KEY, name TEXT);")
    storage.take_over("old", "new")
    assert storage.database.table_names("module_new") == ["module_new_items"]
    assert storage.database.table_names("module_old") == ["module_old_items"]
    assert storage.module_state.get(1, "new", "goal") == "2000"
    storage.close()
