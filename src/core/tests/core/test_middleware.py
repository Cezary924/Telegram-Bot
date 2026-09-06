import pytest

from core import middleware
from core.context import User
from core.roles import Role
from core.testing import not_none
from core.ui.view import render


@pytest.fixture
def loaded(services):
    services.catalog.load_core()
    return services


def person(role: Role = Role.USER, has_consent: bool = True, language: str = "en") -> User:
    return User(1, "First", "Last", "username", role, language, has_consent)


def test_a_settled_user_passes(loaded):
    assert middleware.check(loaded, person(), Role.USER) is None


def test_banned_user_is_stopped(loaded):
    blocked = not_none(middleware.check(loaded, person(Role.BANNED), Role.GUEST))
    assert blocked.text == loaded.catalog.text("core", "banned_info", "en")
    assert blocked.buttons == []


def test_banned_user_is_stopped_in_their_language(loaded):
    blocked = not_none(middleware.check(loaded, person(Role.BANNED, language="pl"), Role.GUEST))
    assert blocked.text == loaded.catalog.text("core", "banned_info", "pl")


def test_ban_wins_over_a_missing_consent(loaded):
    blocked = not_none(middleware.check(loaded, person(Role.BANNED, has_consent=False), Role.GUEST))
    assert blocked.text == loaded.catalog.text("core", "banned_info", "en")


def test_missing_consent_shows_the_agreement(loaded):
    blocked = not_none(middleware.check(loaded, person(has_consent=False), Role.GUEST))
    assert blocked.text == loaded.catalog.text("core", "consent.question", "en")
    _, markup = render(blocked, "core")
    assert [button[0].callback_data for button in not_none(markup).keyboard] == [
        "core:consent_language:pl", "core:consent_accept", "core:consent_decline"]


def test_consent_offers_the_other_language(loaded):
    blocked = not_none(middleware.check(loaded, person(has_consent=False, language="pl"), Role.GUEST))
    _, markup = render(blocked, "core")
    buttons = [(button[0].text, button[0].callback_data) for button in not_none(markup).keyboard]
    assert buttons[0] == (loaded.catalog.text("core", "consent.language_switch", "pl"),
                          "core:consent_language:en")


def test_consent_is_not_a_screen(loaded):
    blocked = not_none(middleware.check(loaded, person(has_consent=False), Role.GUEST))
    assert not blocked.is_screen


def test_missing_consent_wins_over_a_missing_role(loaded):
    blocked = not_none(middleware.check(loaded, person(Role.GUEST, has_consent=False), Role.ADMIN))
    assert blocked.text == loaded.catalog.text("core", "consent.question", "en")


def test_too_low_role_is_stopped(loaded):
    blocked = not_none(middleware.check(loaded, person(Role.USER), Role.ADMIN))
    assert blocked.text == loaded.catalog.text("core", "permission_denied", "en")


@pytest.mark.parametrize("role, required, is_allowed", [
    (Role.GUEST, Role.GUEST, True),
    (Role.GUEST, Role.USER, False),
    (Role.USER, Role.GUEST, True),
    (Role.USER, Role.USER, True),
    (Role.USER, Role.ADMIN, False),
    (Role.ADMIN, Role.ADMIN, True),
    (Role.ADMIN, Role.GUEST, True),
])
def test_role_ladder(loaded, role, required, is_allowed):
    assert (middleware.check_role(loaded, person(role), required) is None) == is_allowed
