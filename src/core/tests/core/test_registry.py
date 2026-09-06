import pytest

from core.module import Module
from core.registry import Registry
from core.roles import Role
from core.testing import not_none


def handler(ctx):
    return ctx


@pytest.fixture
def registry():
    return Registry()


@pytest.fixture
def module1():
    module = Module(name="module1")
    module.command("command1", role=Role.USER)(handler)
    module.callback("action1")(handler)
    module.state("view1")(handler)
    module.match(lambda text: True, priority=10)(handler)
    module.job(interval=60, name="job1")(handler)
    return module


@pytest.fixture
def module2():
    module = Module(name="module2")
    module.command("command2")(handler)
    module.match(lambda text: True, priority=50)(handler)
    return module


def test_empty_registry(registry):
    assert registry.names() == []
    assert registry.modules() == []
    assert registry.matchers() == []
    assert registry.jobs() == []


def test_add_and_get(registry, module1):
    registry.add(module1)
    assert registry.get("module1") is module1
    assert registry.get("module9") is None


def test_modules_are_sorted_by_name(registry, module1, module2):
    registry.add(module2)
    registry.add(module1)
    assert registry.names() == ["module1", "module2"]
    assert [module.name for module in registry.modules()] == ["module1", "module2"]


def test_a_module_cannot_be_added_twice(registry, module1):
    registry.add(module1)
    with pytest.raises(ValueError):
        registry.add(module1)


def test_two_modules_cannot_share_a_command(registry, module1):
    other = Module(name="module2")
    other.command("command1")(handler)
    registry.add(module1)
    with pytest.raises(ValueError) as error:
        registry.add(other)
    assert "command1" in str(error.value)


def test_a_rejected_module_is_not_registered(registry, module1):
    other = Module(name="module2")
    other.command("command1")(handler)
    registry.add(module1)
    with pytest.raises(ValueError):
        registry.add(other)
    assert registry.names() == ["module1"]


def test_command_lookup(registry, module1):
    registry.add(module1)
    module, command = not_none(registry.command("command1"))
    assert module is module1
    assert command.role == Role.USER
    assert registry.command("command9") is None


def test_commands_are_sorted_by_name(registry, module1, module2):
    registry.add(module2)
    registry.add(module1)
    assert [command.name for _, command in registry.commands()] == ["command1", "command2"]


def test_callback_lookup(registry, module1):
    registry.add(module1)
    module, callback = not_none(registry.callback("module1", "action1"))
    assert module is module1 and callback.action == "action1"
    assert registry.callback("module1", "action9") is None
    assert registry.callback("module9", "action1") is None


def test_state_lookup(registry, module1):
    registry.add(module1)
    module, state = not_none(registry.state("module1", "view1"))
    assert module is module1 and state.name == "view1"
    assert registry.state("module1", "view9") is None
    assert registry.state("module9", "view1") is None


def test_matchers_run_from_the_highest_priority(registry, module1, module2):
    registry.add(module1)
    registry.add(module2)
    assert [(module.name, matcher.priority) for module, matcher in registry.matchers()] == [
        ("module2", 50), ("module1", 10)]


def test_matcher_order_does_not_depend_on_registration_order(registry, module1, module2):
    registry.add(module2)
    registry.add(module1)
    assert [module.name for module, _ in registry.matchers()] == ["module2", "module1"]


def test_matchers_with_equal_priority_are_ordered_by_module_then_declaration(registry):
    first = Module(name="module1")
    first.match(lambda text: True)(handler)
    first.match(lambda text: True)(handler)
    second = Module(name="module2")
    second.match(lambda text: True)(handler)
    registry.add(second)
    registry.add(first)
    assert [(module.name, matcher.order) for module, matcher in registry.matchers()] == [
        ("module1", 0), ("module1", 1), ("module2", 0)]


def test_jobs(registry, module1, module2):
    registry.add(module1)
    registry.add(module2)
    assert [(module.name, job.name) for module, job in registry.jobs()] == [("module1", "job1")]


def test_view_lookup(registry, module1):
    module1.view("view1")(handler)
    registry.add(module1)
    module, view = not_none(registry.view("module1", "view1"))
    assert module is module1 and view.name == "view1"
    assert registry.view("module1", "view9") is None
    assert registry.view("module9", "view1") is None
