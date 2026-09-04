import pytest
import sqlite3

from core.db.connection import Database, now_text
from core.testing import not_none


@pytest.fixture
def database():
    database = Database(":memory:")
    database.execute_script("CREATE TABLE things (id INTEGER PRIMARY KEY, name TEXT);")
    yield database
    database.close()


def test_now_text_format():
    text = now_text()
    assert len(text) == 19
    assert text[4] == '-' and text[10] == ' ' and text[13] == ':'


def test_execute_and_query(database):
    database.execute("INSERT INTO things (name) VALUES (?);", ("first", ))
    database.execute("INSERT INTO things (name) VALUES (?);", ("second", ))
    assert not_none(database.query_one("SELECT name FROM things WHERE id = 1;"))['name'] == "first"
    assert len(database.query_all("SELECT * FROM things;")) == 2


def test_query_one_returns_none_when_empty(database):
    assert database.query_one("SELECT * FROM things WHERE id = 99;") is None


def test_rows_are_accessible_by_column_name(database):
    database.execute("INSERT INTO things (name) VALUES (?);", ("first", ))
    row = not_none(database.query_one("SELECT * FROM things;"))
    assert row['name'] == "first"
    assert row['id'] == 1


def test_foreign_keys_are_enforced(database):
    database.execute_script("""
        CREATE TABLE parents (id INTEGER PRIMARY KEY);
        CREATE TABLE children (id INTEGER PRIMARY KEY,
            parent_id INTEGER REFERENCES parents(id) ON DELETE CASCADE); """)
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO children (parent_id) VALUES (?);", (404, ))


def test_table_names_can_be_filtered(database):
    database.execute_script("CREATE TABLE module_module1_items (id INTEGER PRIMARY KEY);")
    assert database.table_names("module_module1_") == ["module_module1_items"]
    assert "things" in database.table_names()


def test_creates_directory_for_the_file(tmp_path):
    path = str(tmp_path / "nested" / "bot.db")
    database = Database(path)
    database.close()
    assert (tmp_path / "nested" / "bot.db").is_file()
