import pytest

from core.roles import Role


def test_values():
    assert Role.BANNED == -1
    assert Role.GUEST == 0
    assert Role.USER == 1
    assert Role.ADMIN == 2


def test_roles_are_ordered():
    assert Role.ADMIN > Role.USER > Role.GUEST > Role.BANNED
    assert Role.ADMIN >= Role.USER


def test_locale_keys():
    assert Role.BANNED.key == "role_banned"
    assert Role.GUEST.key == "role_guest"
    assert Role.USER.key == "role_user"
    assert Role.ADMIN.key == "role_admin"


@pytest.mark.parametrize("value, expected", [
    (-1, Role.BANNED),
    (0, Role.GUEST),
    (2, Role.ADMIN),
    ("1", Role.USER),
    (7, Role.GUEST),
    (None, Role.GUEST),
])
def test_from_value(value, expected):
    assert Role.from_value(value) == expected
