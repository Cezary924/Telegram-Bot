from core.testing import not_none


def test_empty_stack(storage, user):
    assert storage.navigation.depth(user) == 0
    assert storage.navigation.top(user) is None
    assert storage.navigation.pop(user) is None


def test_push_and_top(storage, user):
    storage.navigation.push(user, "module1", "view1")
    row = not_none(storage.navigation.top(user))
    assert row['module'] == "module1"
    assert row['view'] == "view1"
    assert row['argument'] is None
    assert storage.navigation.depth(user) == 1


def test_stack_order(storage, user):
    storage.navigation.push(user, "module1", "view1")
    storage.navigation.push(user, "module1", "view2")
    storage.navigation.push(user, "module1", "view3", "argument1")
    assert storage.navigation.depth(user) == 3
    assert not_none(storage.navigation.top(user))['view'] == "view3"
    assert not_none(storage.navigation.pop(user))['argument'] == "argument1"
    assert not_none(storage.navigation.pop(user))['view'] == "view2"
    assert not_none(storage.navigation.top(user))['view'] == "view1"
    assert storage.navigation.depth(user) == 1


def test_positions_are_reused_after_pop(storage, user):
    storage.navigation.push(user, "module1", "view1")
    storage.navigation.push(user, "module1", "view2")
    storage.navigation.pop(user)
    assert storage.navigation.push(user, "module1", "view3") == 1
    assert not_none(storage.navigation.top(user))['view'] == "view3"


def test_message_id(storage, user):
    storage.navigation.push(user, "module1", "view1", message_id=500)
    assert not_none(storage.navigation.top(user))['message_id'] == 500
    storage.navigation.set_message_id(user, 600)
    assert not_none(storage.navigation.top(user))['message_id'] == 600


def test_set_message_id_on_empty_stack_does_nothing(storage, user):
    storage.navigation.set_message_id(user, 600)
    assert storage.navigation.top(user) is None


def test_clear(storage, user):
    storage.navigation.push(user, "module1", "view1")
    storage.navigation.push(user, "module1", "view2")
    storage.navigation.clear(user)
    assert storage.navigation.depth(user) == 0


def test_stacks_are_per_user(storage, user):
    storage.users.save(2)
    storage.navigation.push(user, "module1", "view1")
    storage.navigation.push(2, "module2", "view1")
    assert not_none(storage.navigation.top(user))['module'] == "module1"
    assert not_none(storage.navigation.top(2))['module'] == "module2"
    storage.navigation.clear(user)
    assert storage.navigation.depth(2) == 1
