def test_missing_key_returns_default(storage, user):
    assert storage.module_state.get(user, "module1", "key1") is None
    assert storage.module_state.get(user, "module1", "key1", "default") == "default"


def test_set_and_get(storage, user):
    storage.module_state.set(user, "module1", "key1", "value1")
    assert storage.module_state.get(user, "module1", "key1") == "value1"


def test_set_overwrites(storage, user):
    storage.module_state.set(user, "module1", "key1", "value1")
    storage.module_state.set(user, "module1", "key1", "value2")
    assert storage.module_state.get(user, "module1", "key1") == "value2"


def test_state_is_scoped_to_the_module(storage, user):
    storage.module_state.set(user, "module1", "key1", "value1")
    storage.module_state.set(user, "module2", "key1", "value2")
    assert storage.module_state.get(user, "module1", "key1") == "value1"
    assert storage.module_state.get(user, "module2", "key1") == "value2"


def test_get_all_for_a_module(storage, user):
    storage.module_state.set(user, "module1", "key1", "value1")
    storage.module_state.set(user, "module1", "key2", "value2")
    storage.module_state.set(user, "module2", "key1", "value3")
    assert storage.module_state.get_all(user, "module1") == {'key1': "value1", 'key2': "value2"}


def test_delete_one_key(storage, user):
    storage.module_state.set(user, "module1", "key1", "value1")
    storage.module_state.set(user, "module1", "key2", "value2")
    storage.module_state.delete(user, "module1", "key1")
    assert storage.module_state.get(user, "module1", "key1") is None
    assert storage.module_state.get(user, "module1", "key2") == "value2"


def test_clear_leaves_other_modules_alone(storage, user):
    storage.module_state.set(user, "module1", "key1", "value1")
    storage.module_state.set(user, "module2", "key1", "value2")
    storage.module_state.clear(user, "module1")
    assert storage.module_state.get_all(user, "module1") == {}
    assert storage.module_state.get(user, "module2", "key1") == "value2"
