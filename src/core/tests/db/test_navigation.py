from core.testing import not_none


def test_nobody_is_on_a_screen_to_begin_with(storage, user):
    assert storage.navigation.current(user) is None


def test_the_current_screen_is_kept(storage, user):
    storage.navigation.set_current(user, "module1", "view1", "argument1", 500)
    current = not_none(storage.navigation.current(user))
    assert current['module'] == "module1"
    assert current['view'] == "view1"
    assert current['argument'] == "argument1"
    assert current['message_id'] == 500


def test_moving_on_replaces_the_current_screen(storage, user):
    storage.navigation.set_current(user, "module1", "view1", None, 500)
    storage.navigation.set_current(user, "module1", "view2", "argument1", 500)
    current = not_none(storage.navigation.current(user))
    assert (current['view'], current['argument']) == ("view2", "argument1")


def test_clearing_leaves_no_screen(storage, user):
    storage.navigation.set_current(user, "module1", "view1", None, 500)
    storage.navigation.clear(user)
    assert storage.navigation.current(user) is None


def test_a_screen_belongs_to_one_user(storage, user):
    storage.users.save(2, "Second", "", "someone")
    storage.navigation.set_current(user, "module1", "view1", None, 500)
    assert storage.navigation.current(2) is None


def test_a_screen_remembers_what_it_was_opened_with(storage, user):
    storage.navigation.remember(user, "module1", "list", "3")
    assert storage.navigation.remembered(user, "module1", "list") == "3"


def test_a_screen_never_opened_remembers_nothing(storage, user):
    assert storage.navigation.remembered(user, "module1", "list") is None


def test_what_a_screen_remembers_is_replaced_rather_than_doubled(storage, user):
    storage.navigation.remember(user, "module1", "list", "3")
    storage.navigation.remember(user, "module1", "list", "7")
    assert storage.navigation.remembered(user, "module1", "list") == "7"


def test_screens_remember_apart_from_one_another(storage, user):
    storage.navigation.remember(user, "module1", "list", "3")
    storage.navigation.remember(user, "module1", "people", "9")
    storage.navigation.remember(user, "module2", "list", "1")
    assert storage.navigation.remembered(user, "module1", "list") == "3"
    assert storage.navigation.remembered(user, "module1", "people") == "9"
    assert storage.navigation.remembered(user, "module2", "list") == "1"


def test_what_is_remembered_outlives_leaving_the_screen(storage, user):
    storage.navigation.remember(user, "module1", "list", "3")
    storage.navigation.clear(user)
    assert storage.navigation.remembered(user, "module1", "list") == "3"


def test_forgetting_wipes_what_every_screen_remembered(storage, user):
    storage.navigation.remember(user, "module1", "list", "3")
    storage.navigation.forget(user)
    assert storage.navigation.remembered(user, "module1", "list") is None
