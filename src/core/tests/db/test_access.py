import pytest

from core.roles import Role


@pytest.mark.parametrize("role, is_restricted, expected", [
    (Role.GUEST, False, False), (Role.GUEST, True, False),
    (Role.USER, False, True), (Role.USER, True, False),
    (Role.ADMIN, False, True), (Role.ADMIN, True, True)])
def test_without_any_choice_the_rank_decides(storage, user, role, is_restricted, expected):
    assert storage.access.is_allowed(user, "module1", role, is_restricted) == expected


def test_a_choice_wins_over_the_rank_both_ways(storage, user):
    storage.access.allow(user, "module1", True)
    assert storage.access.is_allowed(user, "module1", Role.GUEST, True)
    storage.access.allow(user, "module1", False)
    assert not storage.access.is_allowed(user, "module1", Role.USER, False)


def test_a_choice_never_closes_anything_for_an_admin(storage, user):
    storage.access.allow(user, "module1", False)
    assert storage.access.is_allowed(user, "module1", Role.ADMIN, True)


def test_the_default_list_round_trip(storage, user):
    storage.access.set_default("module1", True)
    storage.access.set_default("module1", True)
    assert storage.access.defaults() == {"module1"}
    assert storage.access.is_allowed(user, "module1", Role.GUEST, True)
    storage.access.set_default("module1", False)
    assert storage.access.defaults() == set()


def test_a_request_can_be_made_and_answered_only_once(storage, user):
    assert storage.access.ask(user, "module1")
    assert not storage.access.ask(user, "module1")
    assert storage.access.answer(user, "module1")
    assert not storage.access.answer(user, "module1")
    assert storage.access.ask(user, "module1")


def test_deleting_a_user_takes_their_access_and_requests_along(storage, user):
    storage.access.allow(user, "module1", True)
    storage.access.ask(user, "module2")
    storage.users.delete(user)
    assert storage.database.query_one("SELECT * FROM user_module_access;") is None
    assert storage.database.query_one("SELECT * FROM access_requests;") is None
