def test_a_missing_key_returns_the_default(storage):
    assert storage.state.get("version") is None
    assert storage.state.get("version", "v1.0") == "v1.0"


def test_set_and_get(storage):
    storage.state.set("version", "v1.2 (100)")
    assert storage.state.get("version") == "v1.2 (100)"


def test_set_overwrites(storage):
    storage.state.set("version", "v1.2 (100)")
    storage.state.set("version", "v1.3 (120)")
    assert storage.state.get("version") == "v1.3 (120)"


def test_keys_are_independent(storage):
    storage.state.set("version", "v1.2")
    storage.state.set("something", "else")
    assert storage.state.get("version") == "v1.2"
    assert storage.state.get("something") == "else"


def test_the_state_survives_a_user_being_deleted(storage, user):
    storage.state.set("version", "v1.2")
    storage.users.delete(user)
    assert storage.state.get("version") == "v1.2"
