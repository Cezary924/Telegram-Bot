from core.roles import Role


def test_a_guest_has_nothing_until_let_in(storage, user):
    assert not storage.access.is_allowed(user, "module1", Role.GUEST)
    storage.access.allow(user, "module1", True)
    assert storage.access.is_allowed(user, "module1", Role.GUEST)
    storage.access.allow(user, "module1", False)
    assert not storage.access.is_allowed(user, "module1", Role.GUEST)


def test_an_admin_has_everything_whatever_was_chosen(storage, user):
    storage.access.allow(user, "module1", False)
    assert storage.access.is_allowed(user, "module1", Role.ADMIN)


def test_the_default_list_round_trip(storage, user):
    storage.access.set_default("module1", True)
    storage.access.set_default("module1", True)
    assert storage.access.defaults() == {"module1"}
    assert storage.access.is_allowed(user, "module1", Role.GUEST)
    storage.access.set_default("module1", False)
    assert storage.access.defaults() == set()


def test_a_module_taken_away_wins_over_the_default_list(storage, user):
    storage.access.set_default("module1", True)
    storage.access.allow(user, "module1", False)
    assert not storage.access.is_allowed(user, "module1", Role.GUEST)


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
