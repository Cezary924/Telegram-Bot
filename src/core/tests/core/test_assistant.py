import pytest

from core.context import Ctx, User
from core.module import Module, Outcome
from core.roles import Role
from core.testing import not_none


def person(role: Role = Role.GUEST) -> User:
    return User(1, "First", "Last", "username", role, "en", True)


@pytest.fixture
def saved() -> list[tuple[int, str]]:
    return []


@pytest.fixture
def notes(saved):
    module = Module(name="notes", is_guarded=True)

    @module.action("add", parameters={'text': str, 'count': int}, is_confirmed=True)
    def add(ctx, text: str, count: int) -> Outcome:
        if not text.strip():
            return Outcome.refused("empty")
        return Outcome.ask("add " + text + "?", lambda: saved.append((ctx.user.id, text * count)) or "added")

    @module.action("rename", parameters={'text': str, 'count': int}, optional=["count"])
    def rename(_ctx, text: str, count: int | None) -> Outcome:
        return Outcome.done("{}:{}".format(text, count))

    @module.action("count")
    def how_many(ctx) -> Outcome:
        return Outcome.done({'user': ctx.user.id, 'count': len(saved)})

    @module.action("touch")
    def touch(_ctx) -> Outcome:
        return Outcome.ask("touch?", lambda: "touched")

    @module.action("purge", role=Role.ADMIN, is_confirmed=True)
    def purge(_ctx) -> Outcome:
        return Outcome.ask("purge?", lambda: "purged")

    @module.action("broken")
    def broken(_ctx) -> Outcome:
        raise RuntimeError("bug")

    @module.context()
    def summary(_ctx) -> str:
        return "\n".join("line &lt;" + str(number) + "&gt;" for number in range(8)) + "\n\n"

    return module


@pytest.fixture
def assistant(services, user, notes):
    services.catalog.load_core()
    services.registry.add(notes)
    services.registry.add(Module(name="talker", is_assistant=True))
    services.storage.access.allow(user, "notes", True)
    return Ctx(services, not_none(services.registry.get("talker")), person()).assistant


def test_only_a_module_that_declared_it_reaches_the_assistant(services):
    ctx = Ctx(services, Module(name="module1"), person())
    with pytest.raises(PermissionError):
        _ = ctx.assistant


def test_the_actions_are_those_of_modules_the_user_may_use(assistant, services, user):
    assert [action.tool for _, action in assistant.actions()] == ["notes_add", "notes_rename", "notes_count",
                                                                  "notes_touch", "notes_broken"]
    services.storage.access.allow(user, "notes", False)
    assert assistant.actions() == []
    assert [module.name for module in assistant.modules()] == ["talker"]


def test_an_admin_gets_the_actions_for_admins(assistant, services, user):
    services.storage.users.set_role(user, Role.ADMIN)
    admin = Ctx(services, not_none(services.registry.get("talker")), person(Role.ADMIN)).assistant
    assert "notes_purge" in [action.tool for _, action in admin.actions()]


def test_a_confirmed_action_only_asks_at_first(assistant, saved):
    outcome = assistant.act("notes", "add", {'text': "milk", 'count': 2})
    assert (outcome.status, outcome.result) == ("asking", "add milk?")
    assert saved == []


def test_a_confirmed_action_runs_once_confirmed(assistant, saved):
    assert assistant.act("notes", "add", {'text': "milk", 'count': "2"}, is_confirmed=True) == Outcome.done("added")
    assert saved == [(1, "milkmilk")]


def test_an_action_that_needs_no_confirmation_runs_at_once(assistant):
    assert assistant.act("notes", "touch", {}) == Outcome.done("touched")


def test_a_read_only_action_runs_as_the_user(assistant):
    assert assistant.act("notes", "count", {'user': 2}) == Outcome.done({'user': 1, 'count': 0})


def test_the_module_validates_the_values(assistant, saved):
    assert assistant.act("notes", "add", {'text': " ", 'count': 1}, is_confirmed=True) == Outcome.refused("empty")
    assert saved == []


@pytest.mark.parametrize("arguments", [{'text': "milk"}, {'text': "milk", 'count': "two"},
                                       {'text': "milk", 'count': 1.5}, {'text': "milk", 'count': True},
                                       {'text': ["milk"], 'count': 1}])
def test_arguments_that_do_not_fit_are_refused(assistant, saved, arguments):
    outcome = assistant.act("notes", "add", arguments, is_confirmed=True)
    assert outcome == Outcome.refused("These arguments do not fit, the action takes text (string), count (integer)")
    assert saved == []


@pytest.mark.parametrize("module_name, action_name", [("notes", "missing"), ("missing", "add"), ("notes", "purge")])
def test_an_action_out_of_reach_is_refused(assistant, module_name, action_name):
    assert assistant.act(module_name, action_name, {}, is_confirmed=True) == \
        Outcome.refused("The Bot has no such action for you")


def test_access_taken_away_stops_a_confirmed_action(assistant, services, user, saved):
    services.storage.access.allow(user, "notes", False)
    assert assistant.act("notes", "add", {'text': "milk", 'count': 1}, is_confirmed=True).status == "refused"
    assert saved == []


def test_a_failing_action_is_refused_and_logged(assistant, capsys):
    assert assistant.act("notes", "broken", {}) == Outcome.refused("Error. Please, try again later.")
    assert "Action failed in 'notes' - RuntimeError." in capsys.readouterr().out


def test_the_context_is_plain_and_short(assistant, monkeypatch):
    assert assistant.context("notes") == "\n".join("line <" + str(number) + ">" for number in range(5))
    monkeypatch.setattr("core.assistant.context_size", 10)
    assert assistant.context("notes") == "line <0>\nl"


def test_the_context_needs_access(assistant, services, user):
    services.storage.access.allow(user, "notes", False)
    assert assistant.context("notes") == ""
    assert assistant.context("talker") == "" and assistant.context("missing") == ""


def test_a_failing_context_is_left_out(assistant, notes, capsys):
    notes.summary = lambda ctx: 1 / 0
    assert assistant.context("notes") == ""
    assert "Context failed in 'notes' - ZeroDivisionError." in capsys.readouterr().out


def test_an_optional_argument_left_out_comes_as_none(assistant):
    assert assistant.act("notes", "rename", {'text': "a"}) == Outcome.done("a:None")
    assert assistant.act("notes", "rename", {'text': "a", 'count': None}) == Outcome.done("a:None")
    assert assistant.act("notes", "rename", {'text': "a", 'count': "2"}) == Outcome.done("a:2")


def test_a_required_argument_is_still_required_beside_optional_ones(assistant):
    assert assistant.act("notes", "rename", {'count': 2}) == Outcome.refused(
        "These arguments do not fit, the action takes text (string), count (integer, optional)")
