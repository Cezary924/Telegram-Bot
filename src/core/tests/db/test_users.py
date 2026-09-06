from core.roles import Role
from core.testing import not_none


def test_save_creates_a_guest(storage):
    storage.users.save(1, "First", "Last", "username")
    row = not_none(storage.users.get(1))
    assert row['first_name'] == "First"
    assert row['username'] == "username"
    assert storage.users.get_role(1) == Role.GUEST
    assert not storage.users.has_consent(1)


def test_save_updates_names_and_keeps_role(storage, user):
    storage.users.set_role(user, Role.ADMIN)
    storage.users.save(user, "Changed", "Renamed", "renamed")
    row = not_none(storage.users.get(user))
    assert row['first_name'] == "Changed"
    assert row['last_name'] == "Renamed"
    assert storage.users.get_role(user) == Role.ADMIN


def test_save_keeps_creation_date(storage, user):
    created_at = not_none(storage.users.get(user))['created_at']
    storage.users.save(user, "Changed")
    assert not_none(storage.users.get(user))['created_at'] == created_at


def test_exists_and_get_for_unknown_user(storage):
    assert not storage.users.exists(99)
    assert storage.users.get(99) is None
    assert storage.users.get_role(99) == Role.GUEST
    assert not storage.users.has_consent(99)


def test_role_round_trip(storage, user):
    for role in [Role.BANNED, Role.USER, Role.ADMIN, Role.GUEST]:
        storage.users.set_role(user, role)
        assert storage.users.get_role(user) == role


def test_consent_round_trip(storage, user):
    storage.users.set_consent(user, True)
    assert storage.users.has_consent(user)
    storage.users.set_consent(user, False)
    assert not storage.users.has_consent(user)


def test_get_all_is_ordered(storage):
    for user_id in [30, 10, 20]:
        storage.users.save(user_id)
    assert [row['id'] for row in storage.users.get_all()] == [10, 20, 30]


def test_get_by_role(storage):
    storage.users.save(1)
    storage.users.save(2)
    storage.users.set_role(2, Role.ADMIN)
    assert [row['id'] for row in storage.users.get_by_role(Role.ADMIN)] == [2]
    assert [row['id'] for row in storage.users.get_by_role(Role.GUEST)] == [1]


def test_count_by_role(storage):
    for user_id, role in [(1, Role.GUEST), (2, Role.USER), (3, Role.USER), (4, Role.ADMIN)]:
        storage.users.save(user_id)
        storage.users.set_role(user_id, role)
    assert storage.users.count_by_role() == {Role.GUEST: 1, Role.USER: 2, Role.ADMIN: 1}


def test_delete_removes_the_user(storage, user):
    storage.users.delete(user)
    assert not storage.users.exists(user)


def test_delete_cascades_to_every_user_table(storage, user):
    storage.settings.set_language(user, "pl")
    storage.navigation.push(user, "module1", "view1")
    storage.module_state.set(user, "module1", "key1", "value1")
    storage.users.delete(user)
    assert storage.settings.get(user) is None
    assert storage.navigation.top(user) is None
    assert storage.module_state.get(user, "module1", "key1") is None


def test_save_says_whether_the_user_is_new(storage):
    assert storage.users.save(1, "First", "Last", "username")
    assert not storage.users.save(1, "First", "Last", "username")
