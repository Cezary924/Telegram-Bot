import pytest

from core.testing import not_none

module1_schema = """
CREATE TABLE IF NOT EXISTS module_module1_items (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    value TEXT
);
CREATE INDEX IF NOT EXISTS module_module1_items_by_user ON module_module1_items (user_id);
"""


@pytest.fixture
def module_db(storage):
    module_db = storage.for_module("module1")
    module_db.apply_schema(module1_schema)
    return module_db


def test_prefix_and_table_names(storage):
    module_db = storage.for_module("module1")
    assert module_db.prefix == "module_module1_"
    assert module_db.table("items") == "module_module1_items"


def test_apply_schema_creates_tables(module_db):
    assert module_db.table_names() == ["module_module1_items"]


def test_apply_schema_is_repeatable(module_db):
    module_db.apply_schema(module1_schema)
    assert module_db.table_names() == ["module_module1_items"]


@pytest.mark.parametrize("sql", [
    "CREATE TABLE items (id INTEGER PRIMARY KEY);",
    "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY);",
    "CREATE TABLE module_module2_items (id INTEGER PRIMARY KEY);",
    "CREATE TABLE module_module1_items (id INTEGER PRIMARY KEY);\nCREATE INDEX by_id ON module_module1_items (id);",
])
def test_apply_schema_rejects_unprefixed_objects(storage, sql):
    module_db = storage.for_module("module1")
    with pytest.raises(ValueError) as error:
        module_db.apply_schema(sql)
    assert "module_module1_" in str(error.value)


def test_rejected_schema_creates_nothing(storage):
    module_db = storage.for_module("module1")
    with pytest.raises(ValueError):
        module_db.apply_schema("CREATE TABLE items (id INTEGER PRIMARY KEY);")
    assert module_db.table_names() == []


def test_queries(module_db, user):
    module_db.execute("INSERT INTO module_module1_items (user_id, value) VALUES (?, ?);",
                      (user, "value1"))
    row = not_none(module_db.query_one("SELECT * FROM module_module1_items WHERE user_id = ?;", (user, )))
    assert row['value'] == "value1"
    assert len(module_db.query_all("SELECT * FROM module_module1_items;")) == 1


def test_module_tables_follow_user_deletion(module_db, storage, user):
    module_db.execute("INSERT INTO module_module1_items (user_id, value) VALUES (?, ?);",
                      (user, "value1"))
    storage.users.delete(user)
    assert module_db.query_all("SELECT * FROM module_module1_items;") == []


def test_table_names_are_isolated_between_modules(module_db, storage):
    other = storage.for_module("module2")
    other.apply_schema("CREATE TABLE module_module2_items (id INTEGER PRIMARY KEY);")
    assert module_db.table_names() == ["module_module1_items"]
    assert other.table_names() == ["module_module2_items"]


def test_drop_tables_removes_only_own(module_db, storage):
    other = storage.for_module("module2")
    other.apply_schema("CREATE TABLE module_module2_items (id INTEGER PRIMARY KEY);")
    module_db.drop_tables()
    assert module_db.table_names() == []
    assert other.table_names() == ["module_module2_items"]
    assert storage.users.get_all() == []
