def test_a_source_follows_the_old_switch_until_it_is_set(storage, user):
    assert storage.notifications.is_loud(user, "reminder")
    storage.settings.set_notifications(user, False)
    assert not storage.notifications.is_loud(user, "reminder")


def test_one_source_can_differ_from_the_rest(storage, user):
    storage.notifications.set_loud(user, "reminder", False)
    assert not storage.notifications.is_loud(user, "reminder")
    assert storage.notifications.is_loud(user, "admin")


def test_setting_all_reaches_sources_set_earlier_and_later(storage, user):
    storage.notifications.set_loud(user, "reminder", True)
    storage.notifications.set_all(user, ["reminder"], False)
    assert not storage.notifications.is_loud(user, "reminder")
    assert not storage.notifications.is_loud(user, "added_later")


def test_blocking_round_trip(storage, user):
    assert not storage.notifications.is_blocked(user)
    storage.notifications.set_blocked(user, True)
    storage.notifications.set_blocked(user, True)
    assert storage.notifications.is_blocked(user)
    storage.notifications.set_blocked(user, False)
    assert not storage.notifications.is_blocked(user)


def test_deleting_a_user_takes_their_choices_along(storage, user):
    storage.notifications.set_loud(user, "reminder", False)
    storage.notifications.set_blocked(user, True)
    storage.users.delete(user)
    assert storage.database.query_one("SELECT * FROM user_notifications;") is None
    assert storage.database.query_one("SELECT * FROM user_notification_blocks;") is None
