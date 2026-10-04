import pytest

from core.api import Module, Role, View
from core.registry import Registry
from core.router import Router
from core.testing import FakeBot, make_callback, make_message

reached: list[str] = []


def build(name: str) -> Module:
    module = Module(name=name, is_guarded=True)

    @module.command(name)
    def command(_ctx) -> View:
        reached.append(name + ":command")
        return screen(_ctx)

    @module.view("screen")
    def screen(_ctx) -> View:
        return View("screen of " + name)

    @module.callback("press")
    def press(_ctx) -> None:
        reached.append(name + ":callback")

    @module.state("screen")
    def answer(_ctx) -> None:
        reached.append(name + ":state")

    @module.match(lambda text: text == "say " + name)
    def match(_ctx) -> None:
        reached.append(name + ":matcher")

    @module.settings()
    def settings(_ctx) -> View:
        reached.append(name + ":settings")
        return View("settings of " + name)

    return module


open_module = build("plain")
secret_module = build("secret")
free_module = Module(name="free")


@free_module.command("free")
def command_free(_ctx) -> str:
    reached.append("free:command")
    return "free"


@pytest.fixture
def bot(services):
    services.bot = FakeBot()
    return services.bot


@pytest.fixture
def router(services, bot):
    reached.clear()
    services.catalog.load_core()
    for name in ("plain", "secret", "free"):
        services.catalog.add(name, "en", {'name': name.title()})
    services.registry = Registry()
    for module in (open_module, secret_module, free_module):
        services.registry.add(module)
    return Router(services)


def person(services, user_id: int, role: Role) -> int:
    services.storage.users.save(user_id, "Person" + str(user_id), "", "user" + str(user_id))
    services.storage.users.set_consent(user_id, True)
    services.storage.users.set_role(user_id, role)
    services.storage.settings.set_language(user_id, "en")
    return user_id


def every_way_in(router, user_id: int, name: str) -> list[str]:
    reached.clear()
    router.handle_message(make_message("say " + name, user_id=user_id))
    router.handle_message(make_message("/" + name, user_id=user_id))
    router.handle_message(make_message("an answer", user_id=user_id))
    router.handle_callback(make_callback(name + ":press", user_id=user_id))
    router.handle_callback(make_callback("core:settings:" + name, user_id=user_id))
    return list(reached)


everything = ["matcher", "command", "state", "callback", "settings"]


def reached_for(name: str) -> list[str]:
    return [name + ":" + way for way in everything]


def test_a_guest_reaches_nothing_guarded(router, services):
    user = person(services, 2, Role.GUEST)
    assert every_way_in(router, user, "plain") == []
    assert every_way_in(router, user, "secret") == []


def test_a_guest_still_reaches_a_free_module(router, services):
    user = person(services, 2, Role.GUEST)
    router.handle_message(make_message("/free", user_id=user))
    assert reached == ["free:command"]


def test_a_grant_opens_exactly_one_module(router, services):
    user = person(services, 2, Role.GUEST)
    services.storage.access.allow(user, "secret", True)
    assert every_way_in(router, user, "secret") == reached_for("secret")
    assert every_way_in(router, user, "plain") == []


def test_a_module_taken_away_again_closes(router, services):
    user = person(services, 2, Role.GUEST)
    services.storage.access.allow(user, "plain", True)
    services.storage.access.allow(user, "plain", False)
    assert every_way_in(router, user, "plain") == []


def test_the_default_list_opens_a_module_for_every_guest(router, services):
    services.storage.access.set_default("secret", True)
    user = person(services, 2, Role.GUEST)
    assert every_way_in(router, user, "secret") == reached_for("secret")
    assert every_way_in(router, user, "plain") == []


def test_a_taken_away_module_wins_over_the_default_list(router, services):
    services.storage.access.set_default("plain", True)
    user = person(services, 2, Role.GUEST)
    services.storage.access.allow(user, "plain", False)
    assert every_way_in(router, user, "plain") == []


def test_an_admin_reaches_everything(router, services):
    user = person(services, 2, Role.ADMIN)
    assert every_way_in(router, user, "plain") == reached_for("plain")
    assert every_way_in(router, user, "secret") == reached_for("secret")


def test_a_banned_person_reaches_nothing_even_with_a_grant(router, services):
    user = person(services, 2, Role.BANNED)
    services.storage.access.allow(user, "secret", True)
    assert every_way_in(router, user, "secret") == []


def test_a_person_without_consent_reaches_nothing_even_with_a_grant(router, services):
    user = person(services, 2, Role.GUEST)
    services.storage.users.set_consent(user, False)
    services.storage.access.allow(user, "secret", True)
    assert every_way_in(router, user, "secret") == []


def test_an_answer_on_an_open_screen_is_guarded_as_well(router, services):
    user = person(services, 2, Role.GUEST)
    services.storage.access.allow(user, "secret", True)
    router.handle_message(make_message("/secret", user_id=user))
    services.storage.access.allow(user, "secret", False)
    reached.clear()
    router.handle_message(make_message("something", user_id=user))
    assert reached == []


def test_an_answer_on_an_open_screen_goes_through_with_access(router, services):
    user = person(services, 2, Role.GUEST)
    services.storage.access.allow(user, "secret", True)
    router.handle_message(make_message("/secret", user_id=user))
    reached.clear()
    router.handle_message(make_message("something", user_id=user))
    assert reached == ["secret:state"]


def test_an_unknown_module_stays_closed_even_with_a_grant(services):
    user = person(services, 2, Role.GUEST)
    services.storage.access.allow(user, "nowhere", True)
    from core.context import User, can_use
    someone = User(user, "Person", "", "user", Role.GUEST, "en", True)
    assert not can_use(services, someone, "nowhere")


def test_being_refused_offers_to_ask(router, bot, services):
    user = person(services, 2, Role.GUEST)
    router.handle_message(make_message("/secret", user_id=user))
    assert bot.last.text == "You do not have access to Secret yet 🔒"
    assert bot.last.buttons == [("🙋 Ask for access", "core:request:secret")]


# ----- asking -----

@pytest.fixture
def boss(services) -> int:
    return person(services, 9, Role.ADMIN)


def ask(router, user_id: int, name: str = "secret"):
    router.handle_callback(make_callback("core:request:" + name, user_id=user_id))


def admin_buttons(bot, boss: int) -> list[str]:
    return [data for message in bot.sent if message.chat_id == boss for _, data in message.buttons]


def test_asking_reaches_every_admin_with_a_choice(router, bot, services, boss):
    user = person(services, 2, Role.GUEST)
    ask(router, user)
    to_boss = [message for message in bot.sent if message.chat_id == boss]
    assert to_boss[-1].text == "A request for access to Secret from First, ID 2"
    assert admin_buttons(bot, boss) == ["core:grant:2:secret", "core:refuse:2:secret"]
    assert bot.sent[-1].chat_id == user
    assert bot.sent[-1].text.startswith("Your request has been sent")


def test_asking_twice_does_not_bother_the_admin_again(router, bot, services, boss):
    user = person(services, 2, Role.GUEST)
    ask(router, user)
    ask(router, user)
    assert len([message for message in bot.sent if message.chat_id == boss]) == 1
    assert bot.last.text == "Your request is already waiting for the Administrator"


def test_granting_opens_the_module_and_tells_the_person(router, bot, services, boss):
    user = person(services, 2, Role.GUEST)
    ask(router, user)
    router.handle_callback(make_callback("core:grant:2:secret", user_id=boss, message_id=500))
    assert bot.edited[-1].message_id == 500 and bot.edited[-1].text.endswith("Access granted ✅")
    assert bot.edited[-1].markup is None
    assert any(message.chat_id == user and message.text == "You now have access to Secret ✅" for message in bot.sent)
    assert every_way_in(router, user, "secret") == reached_for("secret")


def test_refusing_keeps_the_module_closed_and_tells_the_person(router, bot, services, boss):
    user = person(services, 2, Role.GUEST)
    ask(router, user)
    router.handle_callback(make_callback("core:refuse:2:secret", user_id=boss))
    assert every_way_in(router, user, "secret") == []
    assert any(message.chat_id == user and "has been refused" in message.text for message in bot.sent)


def test_a_request_is_answered_only_once(router, bot, services, boss):
    user = person(services, 2, Role.GUEST)
    ask(router, user)
    router.handle_callback(make_callback("core:refuse:2:secret", user_id=boss))
    router.handle_callback(make_callback("core:grant:2:secret", user_id=boss))
    assert every_way_in(router, user, "secret") == []
    assert any(message.text == "This request has already been answered" for message in bot.sent)


def test_a_forged_grant_from_a_non_admin_does_nothing(router, services, boss):
    user = person(services, 2, Role.GUEST)
    ask(router, user)
    router.handle_callback(make_callback("core:grant:2:secret", user_id=user))
    assert every_way_in(router, user, "secret") == []


def test_a_grant_nobody_asked_for_does_nothing(router, services, boss):
    user = person(services, 2, Role.GUEST)
    router.handle_callback(make_callback("core:grant:2:secret", user_id=boss))
    assert every_way_in(router, user, "secret") == []


def test_a_grant_with_a_broken_id_does_nothing(router, bot, services, boss):
    router.handle_callback(make_callback("core:grant:someone:secret", user_id=boss))
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"


@pytest.mark.parametrize("name", ["free", "nowhere"])
def test_only_a_guarded_module_can_be_asked_for(router, bot, services, boss, name):
    user = person(services, 2, Role.GUEST)
    ask(router, user, name)
    assert [message for message in bot.sent if message.chat_id == boss] == []
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"


def test_asking_for_what_one_already_has_just_says_so(router, bot, services, boss):
    user = person(services, 2, Role.GUEST)
    services.storage.access.allow(user, "secret", True)
    ask(router, user)
    assert [message for message in bot.sent if message.chat_id == boss] == []
    assert bot.last.text == "You now have access to Secret ✅"


def test_a_banned_person_cannot_ask(router, bot, services, boss):
    user = person(services, 2, Role.BANNED)
    ask(router, user)
    assert [message for message in bot.sent if message.chat_id == boss] == []
