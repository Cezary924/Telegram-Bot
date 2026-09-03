import pytest

from core.module import Module
from core.roles import Role


def handler(ctx):
    return ctx


@pytest.fixture
def module():
    return Module(name="module1")


def test_name_must_be_lowercase(module):
    assert module.name == "module1"
    for name in ["Module1", "module-1", "1module", "module 1", ""]:
        with pytest.raises(ValueError):
            Module(name=name)


def test_table_prefix(module):
    assert module.table_prefix == "module_module1_"


def test_defaults(module):
    assert module.title == "name" and module.description == "description"
    assert module.requires == [] and module.tokens == []
    assert module.features == []
    assert not module.is_internal


def test_declaration_lists_are_not_shared():
    first = Module(name="module1")
    first.command("command1")(handler)
    assert Module(name="module2").commands == []


def test_command_is_recorded(module):
    module.command("command1")(handler)
    assert len(module.commands) == 1
    command = module.commands[0]
    assert command.name == "command1"
    assert command.handler is handler
    assert command.role == Role.GUEST
    assert command.description == "commands.command1"


def test_command_keeps_the_handler_usable(module):
    decorated = module.command("command1")(handler)
    assert decorated is handler
    assert decorated("value1") == "value1"


def test_declarations_run_in_the_foreground_by_default(module):
    module.command("command1")(handler)
    module.callback("action1")(handler)
    module.state("view1")(handler)
    module.match(lambda text: True)(handler)
    assert not module.commands[0].is_background
    assert not module.callbacks[0].is_background
    assert not module.states[0].is_background
    assert not module.matchers[0].is_background


def test_declarations_can_ask_for_a_background_thread(module):
    module.command("command1", is_background=True)(handler)
    module.callback("action1", is_background=True)(handler)
    module.state("view1", is_background=True)(handler)
    module.match(lambda text: True, is_background=True)(handler)
    assert module.commands[0].is_background
    assert module.callbacks[0].is_background
    assert module.states[0].is_background
    assert module.matchers[0].is_background


def test_command_accepts_role_and_description(module):
    module.command("command1", role=Role.ADMIN, description="key1")(handler)
    assert module.commands[0].role == Role.ADMIN
    assert module.commands[0].description == "key1"


def test_command_rejects_a_bad_name(module):
    for name in ["Command1", "command-1", ""]:
        with pytest.raises(ValueError):
            module.command(name)


def test_command_cannot_be_declared_twice(module):
    module.command("command1")(handler)
    with pytest.raises(ValueError):
        module.command("command1")


def test_callback_is_recorded(module):
    module.callback("action1", role=Role.ADMIN)(handler)
    assert module.callbacks[0].action == "action1"
    assert module.callbacks[0].role == Role.ADMIN


def test_callback_cannot_be_declared_twice(module):
    module.callback("action1")(handler)
    with pytest.raises(ValueError):
        module.callback("action1")


def test_callback_rejects_a_bad_action(module):
    with pytest.raises(ValueError):
        module.callback("Action1")


def test_callback_rejects_a_name_that_leaves_no_room(module):
    long_module = Module(name="m" * 40)
    with pytest.raises(ValueError):
        long_module.callback("a" * 30)


def test_callback_data(module):
    module.callback("action1")(handler)
    assert module.callback_data("action1") == "module1:action1"
    assert module.callback_data("action1", 42) == "module1:action1:42"


def test_matcher_records_priority_and_order(module):
    def predicate(_text):
        return True

    module.match(predicate, priority=10)(handler)
    module.match(predicate)(handler)
    assert [matcher.priority for matcher in module.matchers] == [10, 0]
    assert [matcher.order for matcher in module.matchers] == [0, 1]
    assert module.matchers[0].predicate is predicate


def test_matchers_may_repeat(module):
    module.match(lambda text: True)(handler)
    module.match(lambda text: True)(handler)
    assert len(module.matchers) == 2


def test_state_is_recorded(module):
    module.state("view1", role=Role.USER)(handler)
    assert module.states[0].name == "view1"
    assert module.states[0].role == Role.USER


def test_state_cannot_be_declared_twice(module):
    module.state("view1")(handler)
    with pytest.raises(ValueError):
        module.state("view1")


def test_job_is_recorded(module):
    module.job(interval=60)(handler)
    assert module.jobs[0].name == "handler"
    assert module.jobs[0].interval == 60


def test_job_can_be_named(module):
    module.job(interval=60, name="job1")(handler)
    assert module.jobs[0].name == "job1"


def test_job_interval_must_be_positive(module):
    for interval in [0, -1]:
        with pytest.raises(ValueError):
            module.job(interval=interval)


def test_view_is_recorded(module):
    module.view("view1")(handler)
    assert [view.name for view in module.views] == ["view1"]


def test_view_cannot_be_declared_twice(module):
    module.view("view1")(handler)
    with pytest.raises(ValueError):
        module.view("view1")
