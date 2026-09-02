import pytest
import sqlite3


def test_defaults_for_unknown_user(storage):
    assert storage.settings.get(99) is None
    assert storage.settings.get_language(99) == "en"
    assert storage.settings.has_notifications(99)


def test_defaults_for_user_without_settings(storage, user):
    assert storage.settings.get_language(user) == "en"
    assert storage.settings.has_notifications(user)


def test_language_round_trip(storage, user):
    storage.settings.set_language(user, "pl")
    assert storage.settings.get_language(user) == "pl"
    storage.settings.set_language(user, "en")
    assert storage.settings.get_language(user) == "en"


def test_notifications_round_trip(storage, user):
    storage.settings.set_notifications(user, False)
    assert not storage.settings.has_notifications(user)
    storage.settings.set_notifications(user, True)
    assert storage.settings.has_notifications(user)


def test_settings_are_independent(storage, user):
    storage.settings.set_language(user, "pl")
    storage.settings.set_notifications(user, False)
    assert storage.settings.get_language(user) == "pl"
    assert not storage.settings.has_notifications(user)


def test_settings_require_an_existing_user(storage):
    with pytest.raises(sqlite3.IntegrityError):
        storage.settings.set_language(404, "pl")


def test_admin_alerts_are_on_by_default(storage, user):
    assert storage.settings.has_admin_alerts(user)
    assert storage.settings.has_admin_alerts(99)


def test_admin_alerts_round_trip(storage, user):
    storage.settings.set_admin_alerts(user, False)
    assert not storage.settings.has_admin_alerts(user)
    storage.settings.set_admin_alerts(user, True)
    assert storage.settings.has_admin_alerts(user)


def test_admin_alerts_are_independent_of_the_other_settings(storage, user):
    storage.settings.set_admin_alerts(user, False)
    storage.settings.set_notifications(user, True)
    storage.settings.set_language(user, "pl")
    assert not storage.settings.has_admin_alerts(user)
    assert storage.settings.has_notifications(user)
    assert storage.settings.get_language(user) == "pl"
