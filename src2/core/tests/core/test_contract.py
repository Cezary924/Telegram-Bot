import os
import pytest

from core import contract
from core.module import Callback, Module
from core.roles import Role
from core.tests.conftest import fixtures_dir


def fixture_module(name: str, directory: str = "external", is_internal: bool = False) -> Module:
    module = Module(name=name)
    module.path = os.path.join(fixtures_dir, directory, name)
    module.is_internal = is_internal
    return module


def test_manifest_name_must_match_the_directory():
    module = fixture_module("module2")
    assert contract.check_manifest(module) == []
    module.path = os.path.join(fixtures_dir, "external", "elsewhere")
    assert "does not match the directory" in contract.check_manifest(module)[0]


def test_a_module_cannot_require_itself():
    module = fixture_module("module2")
    module.requires = ["module2"]
    assert "requires itself" in contract.check_manifest(module)[0]


def test_locales_of_a_healthy_module(tmp_path):
    module = fixture_module("module1", "internal", True)
    assert contract.check_locales(module) == []


def test_locales_must_cover_every_language(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    (tmp_path / "locales").mkdir()
    (tmp_path / "locales" / "en.yaml").write_text("key1: one\nkey2: two\n", encoding='utf8')
    (tmp_path / "locales" / "pl.yaml").write_text("key1: jeden\nkey3: trzy\n", encoding='utf8')
    problems = contract.check_locales(module)
    assert "'pl.yaml' is missing the key 'key2'" in problems
    assert "'pl.yaml' has the extra key 'key3'" in problems


def test_locales_need_the_default_language(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    (tmp_path / "locales").mkdir()
    (tmp_path / "locales" / "pl.yaml").write_text("key1: jeden\n", encoding='utf8')
    assert "no 'en.yaml'" in contract.check_locales(module)[0]


def test_the_module_needs_a_name_and_a_description_key(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    (tmp_path / "locales").mkdir()
    (tmp_path / "locales" / "en.yaml").write_text("key1: one\n", encoding='utf8')
    module.command("command1")(lambda ctx: None)
    problems = contract.check_locales(module)
    assert "there is no 'name' key for the module listing" in problems
    assert "there is no 'description' key for the module listing" in problems


def test_a_command_needs_a_description_key(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    module.command("command1")(lambda ctx: None)
    (tmp_path / "locales").mkdir()
    (tmp_path / "locales" / "en.yaml").write_text(
        "name: One\ndescription: The first one\n", encoding='utf8')
    assert "no description key 'commands.command1'" in contract.check_locales(module)[0]


def test_a_module_without_commands_may_skip_locales(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    assert contract.check_locales(module) == []


def test_callbacks_must_leave_room_for_arguments():
    short = Module(name="module1")
    short.callback("action1")(lambda ctx: None)
    assert contract.check_callbacks(short) == []
    long_name = Module(name="m" * 40)
    long_name.callbacks.append(Callback("a" * 30, lambda ctx: None, Role.GUEST, False))
    assert "leaves no room" in contract.check_callbacks(long_name)[0]


def test_schema_tables_must_be_prefixed(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    assert contract.check_schema(module) == []
    (tmp_path / "schema.sql").write_text("CREATE TABLE items (id INTEGER PRIMARY KEY);", encoding='utf8')
    assert "'items' is missing the 'module_module1_' prefix" in contract.check_schema(module)[0]


def test_a_correct_schema_passes(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    (tmp_path / "schema.sql").write_text(
        "CREATE TABLE module_module1_items (id INTEGER PRIMARY KEY);", encoding='utf8')
    assert contract.check_schema(module) == []


@pytest.mark.parametrize("line, is_allowed", [
    ("from core.api import Module", True),
    ("from core.testing import FakeBot", True),
    ("from core.db.connection import Database", False),
    ("from core.config import Config", False),
    ("import core.router", False),
    ("import requests", True),
    ("import os, sys", True),
])
def test_an_external_module_may_only_import_the_facade(tmp_path, line, is_allowed):
    module = Module(name="module1")
    module.path = str(tmp_path)
    (tmp_path / "module.py").write_text(line + "\n", encoding='utf8')
    assert (contract.check_imports(module) == []) == is_allowed


def test_an_internal_module_may_import_anything(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    module.is_internal = True
    (tmp_path / "module.py").write_text("from core.db.connection import Database\n", encoding='utf8')
    assert contract.check_imports(module) == []


def test_another_module_may_be_imported_only_when_required(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    (tmp_path / "module.py").write_text(
        "from modules.external.downloads import send_start\n", encoding='utf8')
    assert "imports 'modules.external.downloads.send_start'" in contract.check_imports(module)[0]
    module.requires = ["downloads"]
    assert contract.check_imports(module) == []


def test_a_module_needs_tests(tmp_path):
    module = Module(name="module1")
    module.path = str(tmp_path)
    assert "no 'tests' directory" in contract.check_tests(module)[0]
    (tmp_path / "tests").mkdir()
    assert contract.check_tests(module) == []


def test_every_real_module_meets_the_contract():
    for module in contract.all_modules():
        assert contract.check(module) == [], "module '" + module.name + "'"
