import threading

import pytest
import telebot
from telebot.apihelper import ApiTelegramException

from core.api import Button, Module, Role, View
from core.config import Config
from core.registry import Registry
from core.router import Router
from core.testing import FakeBot, make_callback, make_message, not_none

module1 = Module(name="module1")


@module1.command("command1")
def command1(_ctx) -> str:
    return "text1"


@module1.command("command2", role=Role.ADMIN)
def command2(_ctx) -> str:
    return "text2"


@module1.view("view1")
def view1(ctx) -> View:
    return View("screen1", buttons=[Button(ctx.t("core:yes_button"), "action1")])


@module1.view("view2")
def view2(_ctx) -> View:
    return View("screen2")


@module1.command("menu")
def menu(ctx) -> View:
    return view1(ctx)


@module1.callback("action1")
def action1(ctx) -> View:
    return view2(ctx)


@module1.state("view1")
def state1(ctx) -> str:
    return "state1 got " + ctx.text


@module1.match(lambda text: text.startswith("http"), priority=10)
def matcher1(_ctx) -> str:
    return "matcher1"


slow_started = threading.Event()
slow_may_finish = threading.Event()
slow_thread_names: list[str] = []


@module1.command("slow", is_background=True)
def slow(_ctx) -> str:
    slow_thread_names.append(threading.current_thread().name)
    slow_started.set()
    slow_may_finish.wait(2)
    return "slow done"


@module1.command("quick")
def quick(_ctx) -> str:
    slow_thread_names.append(threading.current_thread().name)
    return "quick done"


@module1.command("boom")
def boom(_ctx) -> str:
    raise RuntimeError("boom")


@pytest.fixture
def bot(services):
    services.bot = FakeBot()
    return services.bot


@pytest.fixture
def router(services, bot):
    services.catalog.load_core()
    services.registry = Registry()
    services.registry.add(module1)
    return Router(services)


@pytest.fixture
def settled(services):
    services.storage.users.save(1, "First", "Last", "username")
    services.storage.users.set_consent(1, True)
    services.storage.settings.set_language(1, "en")
    return 1


def core_text(services, key, language="en") -> str:
    return services.catalog.text("core", key, language)


def test_unknown_command(router, bot, services, settled):
    router.handle_message(make_message("/nope"))
    assert bot.last.text == core_text(services, "unknown_command")


def test_known_command_runs(router, bot, settled):
    router.handle_message(make_message("/command1"))
    assert bot.last.text == "text1"


def test_command_with_a_bot_mention_runs(router, bot, settled):
    router.handle_message(make_message("/command1@SomeBot"))
    assert bot.last.text == "text1"


def test_command_above_the_user_role_is_refused(router, bot, services, settled):
    router.handle_message(make_message("/command2"))
    assert bot.last.text == core_text(services, "permission_denied")


def test_command_runs_for_an_admin(router, bot, services, settled):
    services.storage.users.set_role(settled, Role.ADMIN)
    router.handle_message(make_message("/command2"))
    assert bot.last.text == "text2"


def test_a_new_user_is_asked_for_consent(router, bot, services):
    router.handle_message(make_message("/command1"))
    assert bot.last.text == core_text(services, "consent.question")
    assert [data for _, data in bot.last.buttons] == [
        "core:consent_language:pl", "core:consent_accept", "core:consent_decline"]


def test_a_new_user_is_registered(router, services):
    router.handle_message(make_message("/command1"))
    assert services.storage.users.exists(1)


def test_consent_is_asked_in_the_telegram_language(router, bot, services):
    router.handle_message(make_message("/command1", language_code="pl"))
    assert bot.last.text == core_text(services, "consent.question", "pl")


def test_accepting_consent_unlocks_the_bot(router, bot, services):
    router.handle_message(make_message("/command1"))
    router.handle_callback(make_callback("core:consent_accept"))
    assert services.storage.users.has_consent(1)
    assert bot.last.text == core_text(services, "consent.accepted")
    bot.clear()
    router.handle_message(make_message("/command1"))
    assert bot.last.text == "text1"


def test_declining_consent_keeps_the_bot_locked(router, bot, services):
    router.handle_message(make_message("/command1"))
    router.handle_callback(make_callback("core:consent_decline"))
    assert not services.storage.users.has_consent(1)
    assert bot.last.text == core_text(services, "consent.declined")


def test_switching_the_consent_language_edits_the_message(router, bot, services):
    router.handle_message(make_message("/command1"))
    router.handle_callback(make_callback("core:consent_language:pl", message_id=500))
    assert bot.edited[0].message_id == 500
    assert bot.edited[0].text == core_text(services, "consent.question", "pl")


def test_switching_the_consent_language_is_remembered(router, bot, services):
    router.handle_message(make_message("/command1"))
    router.handle_callback(make_callback("core:consent_language:pl", message_id=bot.last.message_id))
    assert services.storage.settings.get_language(1) == "pl"
    router.handle_callback(make_callback("core:consent_accept"))
    assert bot.last.text == core_text(services, "consent.accepted", "pl")


def test_consent_in_the_telegram_language_is_remembered(router, bot, services):
    router.handle_message(make_message("/command1", language_code="pl"))
    router.handle_callback(make_callback("core:consent_accept", language_code="pl"))
    assert services.storage.settings.get_language(1) == "pl"
    assert bot.last.text == core_text(services, "consent.accepted", "pl")


def test_a_banned_user_is_stopped(router, bot, services, settled):
    services.storage.users.set_role(settled, Role.BANNED)
    router.handle_message(make_message("/command1"))
    assert bot.last.text == core_text(services, "banned_info")


def test_opening_a_screen_pushes_it_on_the_stack(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    top = not_none(services.storage.navigation.top(1))
    assert top['module'] == "module1" and top['view'] == "view1"
    assert top['message_id'] == bot.last.message_id
    assert bot.last.buttons[-1] == (core_text(services, "return_button"), "core:back")


def test_going_deeper_replaces_the_message(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    screen = bot.last.message_id
    router.handle_callback(make_callback("module1:action1", message_id=screen))
    assert bot.deleted == [(1, screen)]
    assert services.storage.navigation.depth(1) == 2
    assert not_none(services.storage.navigation.top(1))['view'] == "view2"


def test_going_back_restores_the_parent(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    router.handle_callback(make_callback("module1:action1", message_id=bot.last.message_id))
    router.handle_callback(make_callback("core:back", message_id=bot.last.message_id))
    assert bot.last.text == "screen1"
    assert services.storage.navigation.depth(1) == 1
    assert not_none(services.storage.navigation.top(1))['view'] == "view1"
    assert not_none(services.storage.navigation.top(1))['message_id'] == bot.last.message_id


def test_a_button_on_an_unreachable_message_is_refused(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    router.handle_callback(make_callback("module1:action1", is_reachable=False))
    assert bot.last.text == core_text(services, "not_working_buttons")
    assert services.storage.navigation.depth(1) == 1


def test_going_back_from_the_root_closes_the_menu(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    router.handle_callback(make_callback("core:back", message_id=bot.last.message_id))
    assert bot.last.text == core_text(services, "menu_closed")
    assert services.storage.navigation.depth(1) == 0


def test_going_back_from_an_old_message_is_refused(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    router.handle_callback(make_callback("core:back", message_id=999))
    assert bot.last.text == core_text(services, "not_working_buttons")
    assert services.storage.navigation.depth(1) == 1


def test_state_handler_takes_the_message_on_its_screen(router, bot, settled):
    router.handle_message(make_message("/menu"))
    router.handle_message(make_message("value1"))
    assert bot.last.text == "state1 got value1"


def test_matcher_runs_when_no_screen_claims_the_message(router, bot, settled):
    router.handle_message(make_message("https://example.com"))
    assert bot.last.text == "matcher1"


def test_a_screen_state_wins_over_a_matcher(router, bot, settled):
    router.handle_message(make_message("/menu"))
    router.handle_message(make_message("https://example.com"))
    assert bot.last.text == "state1 got https://example.com"


def test_unmatched_message_falls_back(router, bot, services, settled):
    router.handle_message(make_message("value1"))
    assert bot.last.text == core_text(services, "unknown_message")


def test_an_unknown_callback_is_refused(router, bot, services, settled):
    router.handle_callback(make_callback("module1:action9"))
    assert bot.last.text == core_text(services, "not_working_buttons")


def test_a_callback_of_an_unknown_module_is_refused(router, bot, services, settled):
    router.handle_callback(make_callback("module9:action1"))
    assert bot.last.text == core_text(services, "not_working_buttons")


def test_malformed_callback_data_is_refused(router, bot, services, settled):
    router.handle_callback(make_callback("module1"))
    assert bot.last.text == core_text(services, "not_working_buttons")


def test_every_callback_is_answered(router, bot, settled):
    router.handle_callback(make_callback("module1:action1"))
    assert bot.answered == [("1", None)]


def test_a_background_handler_does_not_block_the_router(router, bot, settled):
    slow_started.clear()
    slow_may_finish.clear()
    router.handle_message(make_message("/slow"))
    assert slow_started.wait(1)
    assert bot.sent == []
    slow_may_finish.set()
    for _ in range(200):
        if bot.sent:
            break
        threading.Event().wait(0.01)
    assert bot.last.text == "slow done"


def test_a_background_handler_runs_off_the_calling_thread(router, bot, settled):
    slow_thread_names.clear()
    slow_started.clear()
    slow_may_finish.set()
    router.handle_message(make_message("/slow"))
    assert slow_started.wait(1)
    assert slow_thread_names[0] == "task-module1"
    assert slow_thread_names[0] != threading.current_thread().name


def test_a_normal_handler_runs_on_the_calling_thread(router, bot, settled):
    slow_thread_names.clear()
    router.handle_message(make_message("/quick"))
    assert slow_thread_names == [threading.current_thread().name]
    assert bot.last.text == "quick done"


def test_a_failing_handler_does_not_kill_the_bot(router, bot, services, settled, capsys):
    router.handle_message(make_message("/boom"))
    assert bot.last.text == core_text(services, "error")
    assert "Handler failed in 'module1' - RuntimeError." in capsys.readouterr().out
    router.handle_message(make_message("/command1"))
    assert bot.last.text == "text1"


def test_a_banned_user_gets_nothing_but_the_ban_notice(router, bot, services, settled):
    services.storage.users.set_role(settled, Role.BANNED)
    for incoming in ["/command1", "/nope", "value1", "https://example.com"]:
        bot.clear()
        router.handle_message(make_message(incoming))
        assert bot.last.text == core_text(services, "banned_info")


def test_a_banned_user_cannot_press_buttons(router, bot, services, settled):
    services.storage.users.set_role(settled, Role.BANNED)
    for data in ["module1:action1", "core:back", "core:consent_accept"]:
        bot.clear()
        router.handle_callback(make_callback(data))
        assert bot.last.text == core_text(services, "banned_info")


def test_a_user_without_consent_is_asked_before_anything_else(router, bot, services):
    for incoming in ["/nope", "value1", "https://example.com"]:
        bot.clear()
        router.handle_message(make_message(incoming))
        assert bot.last.text == core_text(services, "consent.question")


def test_a_user_without_consent_can_still_answer_the_consent(router, bot, services):
    router.handle_message(make_message("/command1"))
    bot.clear()
    router.handle_callback(make_callback("core:consent_accept"))
    assert bot.last.text == core_text(services, "consent.accepted")


@module1.view("view3")
def view3(ctx) -> View:
    return View("screen3 for " + str(ctx.arguments), argument="42")


@module1.command("parametrised")
def parametrised(ctx) -> View:
    return view3(ctx)


@module1.match(lambda text: text == "boom-matcher")
def broken_matcher(_ctx) -> str:
    return "never"


def test_a_screen_argument_survives_going_back(router, bot, services, settled):
    router.handle_message(make_message("/parametrised"))
    assert not_none(services.storage.navigation.top(1))['argument'] == "42"
    router.handle_callback(make_callback("module1:action1", message_id=bot.last.message_id))
    router.handle_callback(make_callback("core:back", message_id=bot.last.message_id))
    assert bot.last.text == "screen3 for ('42',)"


def test_a_message_without_a_sender_is_ignored(router, bot, settled):
    message = make_message("value1")
    message.from_user = None
    router.handle_message(message)
    assert bot.sent == []


def test_a_screen_without_a_state_handler_falls_through_to_matchers(router, bot, settled):
    router.handle_message(make_message("/parametrised"))
    router.handle_message(make_message("https://example.com"))
    assert bot.last.text == "matcher1"


def test_a_failing_matcher_is_skipped(router, bot, services, settled, capsys):
    def explode(_text):
        raise RuntimeError("boom")

    services.registry.get("module1").matchers.insert(
        0, type(services.registry.get("module1").matchers[0])(
            explode, broken_matcher, Role.GUEST, 99, 0, False))
    router.handle_message(make_message("value1"))
    assert "Matcher failed in 'module1' - RuntimeError." in capsys.readouterr().out
    assert bot.last.text == core_text(services, "unknown_message")
    services.registry.get("module1").matchers.pop(0)


def test_an_unknown_core_action_is_refused(router, bot, services, settled):
    router.handle_callback(make_callback("core:nonsense"))
    assert bot.last.text == core_text(services, "not_working_buttons")


def test_going_back_to_a_view_that_no_longer_exists_clears_the_stack(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    router.handle_callback(make_callback("module1:action1", message_id=bot.last.message_id))
    services.storage.navigation.clear(1)
    services.storage.navigation.push(1, "module9", "gone", None, bot.last.message_id)
    services.storage.navigation.push(1, "module1", "view2", None, bot.last.message_id)
    router.handle_callback(make_callback("core:back", message_id=bot.last.message_id))
    assert bot.last.text == core_text(services, "not_working_buttons")
    assert services.storage.navigation.depth(1) == 0


def test_a_handler_returning_something_odd_sends_nothing(router, bot, settled):
    user = router.load_user(not_none(make_message("value1").from_user))
    router.present(user, "module1", 42)
    router.present(user, "module1", None)
    assert bot.sent == []


def test_an_undeletable_screen_does_not_break_navigation(router, bot, services, settled, monkeypatch):
    router.handle_message(make_message("/menu"))

    def refuse(*_args, **_kwargs):
        raise ApiTelegramException("deleteMessage", "",
                                   {'error_code': 400, 'description': "message can't be deleted"})

    monkeypatch.setattr(bot, "delete_message", refuse)
    router.handle_callback(make_callback("module1:action1", message_id=bot.last.message_id))
    assert services.storage.navigation.depth(1) == 2
    assert bot.last.text == "screen2"


def test_the_registered_handlers_route_an_update(router, services, settled):
    real_bot = telebot.TeleBot("0:aaa", validate_token=False)
    router.register(real_bot)
    real_bot.message_handlers[0]['function'](make_message("/command1"))
    assert services.bot.last.text == "text1"


def test_register_hooks_the_router_into_telebot(services, bot):
    real_bot = telebot.TeleBot("0:aaa", validate_token=False)
    router = Router(services)
    router.register(real_bot)
    assert len(real_bot.message_handlers) == 1
    assert len(real_bot.callback_query_handlers) == 1
    assert real_bot.message_handlers[0]['filters']['content_types'] == ['text']


def test_a_command_starts_a_fresh_navigation(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    router.handle_callback(make_callback("module1:action1", message_id=bot.last.message_id))
    assert services.storage.navigation.depth(1) == 2
    router.handle_message(make_message("/menu"))
    assert services.storage.navigation.depth(1) == 1
    assert not_none(services.storage.navigation.top(1))['view'] == "view1"


def test_a_repeated_command_does_not_stack_the_same_screen(router, bot, services, settled):
    for _ in range(3):
        router.handle_message(make_message("/menu"))
    assert services.storage.navigation.depth(1) == 1
    router.handle_callback(make_callback("core:back", message_id=bot.last.message_id))
    assert bot.last.text == core_text(services, "menu_closed")


def test_a_command_button_also_starts_fresh(router, bot, services, settled):
    router.handle_message(make_message("/menu"))
    router.handle_callback(make_callback("module1:action1", message_id=bot.last.message_id))
    router.handle_callback(make_callback("core:command:menu", message_id=bot.last.message_id))
    assert services.storage.navigation.depth(1) == 1


def test_a_new_user_is_announced_to_the_admins(router, bot, services, settled):
    services.storage.users.save(2, "Admin", "Person", "admin")
    services.storage.users.set_role(2, Role.ADMIN)
    bot.clear()
    router.handle_message(make_message("value1", user_id=3))
    announced = [message for message in bot.sent if message.chat_id == 2]
    assert len(announced) == 1
    assert "ID: _3_" in announced[0].text


def test_a_returning_user_is_not_announced(router, bot, services, settled):
    services.storage.users.save(2, "Admin", "Person", "admin")
    services.storage.users.set_role(2, Role.ADMIN)
    router.handle_message(make_message("value1", user_id=3))
    bot.clear()
    router.handle_message(make_message("value2", user_id=3))
    assert [message for message in bot.sent if message.chat_id == 2] == []


def test_an_admin_who_turned_alerts_off_is_left_alone(router, bot, services, settled):
    services.storage.users.save(2, "Admin", "Person", "admin")
    services.storage.users.set_role(2, Role.ADMIN)
    services.storage.settings.set_admin_alerts(2, False)
    bot.clear()
    router.handle_message(make_message("value1", user_id=3))
    assert [message for message in bot.sent if message.chat_id == 2] == []


def test_the_announcement_speaks_the_admin_language(router, bot, services, settled):
    services.storage.users.save(2, "Admin", "Person", "admin")
    services.storage.users.set_role(2, Role.ADMIN)
    services.storage.settings.set_language(2, "pl")
    bot.clear()
    router.handle_message(make_message("value1", user_id=3))
    announced = [message for message in bot.sent if message.chat_id == 2]
    assert announced[0].text.startswith("Bot poznał nowego użytkownika")


def test_a_matcher_sees_the_text_not_the_message(router, bot, services, settled):
    seen = []
    module1.matchers.insert(0, type(module1.matchers[0])(
        lambda text: seen.append(text) or False, matcher1, Role.GUEST, 99, 0, False))
    router.handle_message(make_message("value1"))
    module1.matchers.pop(0)
    assert seen == ["value1"]


@pytest.fixture
def named(tmp_path, services, bot):
    """A Router whose configuration names someone as the Bot owner."""

    def build(username: str) -> Router:
        (tmp_path / "config.yaml").write_text(
            "bot_name: Bot\ntelegram_username: " + username + "\n", encoding='utf8')
        services.config = Config()
        services.catalog.load_core()
        services.registry = Registry()
        services.registry.add(module1)
        return Router(services)

    return build


def test_the_person_named_in_the_config_becomes_the_first_admin(named, services):
    named("username").handle_message(make_message("/command1", user_id=7))
    assert services.storage.users.get_role(7) == Role.ADMIN


def test_a_leading_at_sign_and_letter_case_are_ignored(named, services):
    named('"@USERNAME"').handle_message(make_message("/command1", user_id=7))
    assert services.storage.users.get_role(7) == Role.ADMIN


def test_somebody_else_is_not_promoted(named, services):
    named("someone").handle_message(make_message("/command1", user_id=7))
    assert services.storage.users.get_role(7) == Role.GUEST


def test_nobody_is_promoted_when_an_admin_is_already_there(named, services):
    services.storage.users.save(9, "First", "Last", "admin1")
    services.storage.users.set_role(9, Role.ADMIN)
    named("username").handle_message(make_message("/command1", user_id=7))
    assert services.storage.users.get_role(7) == Role.GUEST


def test_nothing_happens_without_a_username_in_the_config(named, services):
    named("  ").handle_message(make_message("/command1", user_id=7))
    assert services.storage.users.get_by_role(Role.ADMIN) == []


def test_the_promotion_happens_only_once(named, services):
    router = named("username")
    router.handle_message(make_message("/command1", user_id=7))
    services.storage.users.set_role(7, Role.USER)
    router.handle_message(make_message("/command1", user_id=7))
    assert services.storage.users.get_role(7) == Role.USER


def refusing_bot(services, description: str):
    def refuse(*_arguments, **_values):
        raise ApiTelegramException("answerCallbackQuery", description,
                                   {'error_code': 400, 'description': description})

    services.bot.answer_callback_query = refuse
    return services.bot


def test_a_button_press_that_can_no_longer_be_answered_is_still_handled(router, services, settled):
    refusing_bot(services, "query is too old")
    router.handle_callback(make_callback("module1:action1"))
    assert "screen2" in services.bot.last.text


def test_the_failure_to_answer_is_logged(router, services, settled, capsys):
    refusing_bot(services, "query is too old")
    router.handle_callback(make_callback("module1:action1"))
    assert "Could not answer a button press" in capsys.readouterr().out


def test_a_broken_handler_never_reaches_the_polling_thread(router, capsys):
    def explode(_update) -> None:
        raise RuntimeError("boom")

    router.guarded(explode)(make_message("/command1"))
    assert "Handling an update failed - RuntimeError." in capsys.readouterr().out


def test_a_working_handler_passes_through_the_guard(router):
    seen = []
    router.guarded(seen.append)("update1")
    assert seen == ["update1"]
