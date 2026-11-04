import importlib
import os
import pytest

from core.config import Config
from core.loader import Loader, discover
from core.module import Module
from core.registry import Registry
from core.testing import not_none
from core.tests.conftest import fixtures_dir


@pytest.fixture
def loader(services):
    return Loader(services.config, services.catalog, services.storage)


@pytest.fixture
def registry(loader, module_sources):
    return loader.load(Registry(), module_sources)


def load_with_modules_yaml(services, module_sources, config_dir, contents):
    (config_dir / "modules.yaml").write_text(contents, encoding='utf8')
    loader = Loader(Config(), services.catalog, services.storage)
    return loader.load(Registry(), module_sources)


def test_discover_finds_only_directories_with_a_manifest():
    assert discover(os.path.join(fixtures_dir, "external")) == [
        "module10", "module11", "module2", "module3", "module4", "module5", "module6", "module7", "module8"]
    assert discover(os.path.join(fixtures_dir, "internal")) == ["module1"]


def test_discover_ignores_a_missing_directory(tmp_path):
    assert discover(str(tmp_path / "nope")) == []


def test_loads_the_working_modules(registry):
    assert registry.names() == ["module1", "module11", "module2"]


def test_the_two_kinds_are_reported_apart(loader, module_sources, capsys):
    loader.load(Registry(), module_sources)
    out = capsys.readouterr().out
    assert "Internal modules loaded: module1." in out
    assert "External modules loaded: module11, module2." in out
    assert out.index("Internal modules") < out.index("External modules")


def test_a_kind_without_modules_says_so(loader, tmp_path, capsys):
    loader.load(Registry(), [(str(tmp_path), "nowhere", True), (str(tmp_path), "nowhere", False)])
    out = capsys.readouterr().out
    assert "Internal modules loaded: none." in out
    assert "External modules loaded: none." in out


def test_marks_internal_modules(registry):
    assert not_none(registry.get("module1")).is_internal
    assert not not_none(registry.get("module2")).is_internal


def test_records_the_module_path(registry):
    assert not_none(registry.get("module1")).path == os.path.join(fixtures_dir, "internal", "module1")


def test_skips_a_module_with_a_missing_dependency(loader, registry):
    assert "missing dependency" in loader.skipped["module4"]


def test_skips_a_module_without_a_module_object(loader, registry):
    assert "no 'module' object" in loader.skipped["module5"]


def test_skips_a_module_that_requires_a_missing_one(loader, registry):
    assert loader.skipped["module3"] == "requires 'module9'"


def test_skipping_cascades_to_dependent_modules(loader, registry):
    assert loader.skipped["module6"] == "requires 'module3'"
    assert "module6" not in registry.names()


def test_disabled_external_module_is_not_loaded(services, module_sources, config, tmp_path):
    registry = load_with_modules_yaml(services, module_sources, tmp_path, "module2: false\n")
    assert registry.names() == ["module1", "module11"]


def test_internal_modules_ignore_the_config(services, module_sources, config, tmp_path):
    registry = load_with_modules_yaml(services, module_sources, tmp_path, "module1: false\n")
    assert "module1" in registry.names()


def test_locales_are_loaded_into_the_catalog(registry, services):
    assert services.catalog.text("module1", "key1", "pl") == "jeden"
    assert services.catalog.text("module1", "key1", "en") == "one"


def test_schema_is_applied(registry, services):
    assert services.storage.for_module("module1").table_names() == ["module_module1_items"]


def test_a_module_without_a_schema_creates_no_tables(registry, services):
    assert services.storage.for_module("module2").table_names() == []


def test_declarations_reach_the_registry(registry):
    assert [command.name for _, command in registry.commands()] == ["command1", "command2"]


def test_a_module_loads_without_what_it_uses(loader, registry):
    assert "module11" in registry.names()
    assert "module11" not in loader.skipped


def test_a_module_whose_requirement_failed_to_install_is_skipped(loader, registry):
    assert loader.skipped["module10"] == "requires 'module8'"
    assert "module10" not in registry.names()


def test_what_a_module_requires_or_uses_is_installed_first(loader):
    first = Module(name="module1", uses=["module3"])
    second = Module(name="module2", requires=["module1"])
    third = Module(name="module3")
    assert [module.name for module in loader.ordered([first, second, third])] == ["module3", "module1", "module2"]


def test_modules_that_use_each_other_are_both_installed(loader):
    first = Module(name="module1", uses=["module2"])
    second = Module(name="module2", uses=["module1"])
    assert [module.name for module in loader.ordered([first, second])] == ["module2", "module1"]


def test_an_entry_without_a_directory_is_reported(services, module_sources, config, tmp_path, capsys):
    (tmp_path / "modules.yaml").write_text("module9: false\n", encoding='utf8')
    Loader(Config(), services.catalog, services.storage).load(Registry(), module_sources)
    assert "Module 'module9' is listed in modules.yaml but has no directory." in capsys.readouterr().out


def test_skips_a_module_whose_name_disagrees_with_its_directory(loader, registry):
    assert loader.skipped["module7"] == "declares the name 'renamed'"
    assert "renamed" not in registry.names()


def test_skips_a_module_whose_schema_breaks_the_prefix_rule(loader, registry):
    assert "module_module8_" in loader.skipped["module8"]
    assert "module8" not in registry.names()


def test_a_refused_schema_creates_no_tables(registry, services):
    assert services.storage.for_module("module8").table_names() == []
    assert "items" not in services.storage.database.table_names()


def fixture_module(name: str) -> Module:
    return importlib.import_module("core.tests.fixtures.external." + name + ".module").module


@pytest.fixture
def renamed(monkeypatch):
    found = fixture_module("module2")
    monkeypatch.setattr(found, "formerly", ["module0"])


def test_a_renamed_module_takes_over_its_old_data_on_start(services, module_sources, renamed):
    services.storage.users.save(1, "First", "Last", "username")
    services.storage.module_state.set(1, "module0", "key", "value")
    Loader(services.config, services.catalog, services.storage).load(Registry(), module_sources)
    assert services.storage.module_state.get(1, "module2", "key") == "value"


def test_an_old_name_turned_off_keeps_the_module_off(services, module_sources, config, tmp_path, renamed, capsys):
    registry = load_with_modules_yaml(services, module_sources, tmp_path, "module0: false\n")
    assert "module2" not in registry.names()
    assert "module0" not in capsys.readouterr().out
    assert not Config().is_module_enabled("module2")


def test_the_new_name_decides_once_it_is_listed(services, module_sources, config, tmp_path, renamed):
    registry = load_with_modules_yaml(services, module_sources, tmp_path, "module0: false\nmodule2: true\n")
    assert "module2" in registry.names()


def test_a_module_cannot_take_over_one_that_is_still_there(services, module_sources, monkeypatch):
    found = fixture_module("module11")
    monkeypatch.setattr(found, "formerly", ["module2"])
    services.storage.users.save(1, "First", "Last", "username")
    services.storage.module_state.set(1, "module2", "key", "value")
    loader = Loader(services.config, services.catalog, services.storage)
    registry = loader.load(Registry(), module_sources)
    assert loader.skipped["module11"] == "was formerly 'module2', which is still there"
    assert "module2" in registry.names()
    assert services.storage.module_state.get(1, "module2", "key") == "value"
