import pytest

from core.roles import Role


def test_values():
    assert Role.BANNED == -1
    assert Role.GUEST == 0
    assert Role.ADMIN == 2


def test_there_are_three_ranks():
    assert list(Role) == [Role.BANNED, Role.GUEST, Role.ADMIN]


def test_roles_are_ordered():
    assert Role.ADMIN > Role.GUEST > Role.BANNED


def test_locale_keys():
    assert Role.BANNED.key == "role_banned"
    assert Role.GUEST.key == "role_guest"
    assert Role.ADMIN.key == "role_admin"


@pytest.mark.parametrize("value, expected", [
    (-1, Role.BANNED),
    (0, Role.GUEST),
    (2, Role.ADMIN),
    ("2", Role.ADMIN),
    (1, Role.GUEST),
    (7, Role.GUEST),
    (None, Role.GUEST),
])
def test_from_value(value, expected):
    assert Role.from_value(value) == expected
