import pytest

from core.roles import Role
from core.testing import make_callback, make_message
from modules.internal.admin import module as admin


@pytest.fixture
def boss(app):
    app.storage.users.set_role(1, Role.ADMIN)
    return app


def open_menu(app):
    app.router.handle_message(make_message("/admin"))


def press(app, data: str):
    app.router.handle_callback(make_callback(data, message_id=app.services.bot.last.message_id))


def add_people(app, count: int, role: Role = Role.USER) -> None:
    for number in range(2, 2 + count):
        app.storage.users.save(number, "Person" + str(number), "Last", "user" + str(number))
        app.storage.users.set_role(number, role)


def test_only_an_admin_may_open_the_menu(app, bot):
    open_menu(app)
    assert bot.last.text.startswith("Sorry, you cannot use this command")


def test_the_menu_lists_every_section(boss, bot):
    open_menu(boss)
    assert bot.last.text == "*🛠️ Admin:*\n\nSelect the task of the following:"
    assert [data for _, data in bot.last.buttons] == [
        "admin:users", "admin:statistics", "admin:announcement",
        "admin:alerts", "admin:modules", "admin:bot", "core:back"]


def test_the_user_list_pages_through_people(boss, bot):
    add_people(boss, 20)
    open_menu(boss)
    press(boss, "admin:users")
    press(boss, "admin:list:0")
    assert "Page 1 of 3, 21 users in total" in bot.last.text
    assert len([data for _, data in bot.last.buttons if data.startswith("admin:user:")]) == 8
    press(boss, "admin:list:1")
    assert "Page 2 of 3" in bot.last.text


def test_a_short_list_has_no_paging_buttons(boss, bot):
    add_people(boss, 2)
    open_menu(boss)
    press(boss, "admin:users")
    press(boss, "admin:list:0")
    assert "Page 1 of 1, 3 users in total" in bot.last.text
    assert not [data for _, data in bot.last.buttons if data.startswith("admin:list:")]


def test_searching_by_id_opens_the_user(boss, bot):
    add_people(boss, 1)
    open_menu(boss)
    press(boss, "admin:users")
    press(boss, "admin:search")
    boss.router.handle_message(make_message("2"))
    assert "Person2 (2)" in bot.last.text
    assert "Rank: _User_" in bot.last.text


def test_searching_for_somebody_who_is_not_there(boss, bot):
    open_menu(boss)
    press(boss, "admin:users")
    press(boss, "admin:search")
    boss.router.handle_message(make_message("999"))
    assert "has not been found" in bot.last.text


def test_searching_for_nonsense(boss, bot):
    open_menu(boss)
    press(boss, "admin:users")
    press(boss, "admin:search")
    boss.router.handle_message(make_message("not a number"))
    assert "has not been found" in bot.last.text


def test_a_forwarded_message_reveals_the_sender(boss, bot):
    add_people(boss, 1)
    open_menu(boss)
    press(boss, "admin:users")
    press(boss, "admin:forward")
    boss.router.handle_message(make_message("hello", forward_from=2))
    assert "Person2 (2)" in bot.last.text


def test_a_forward_from_a_hidden_account_says_so(boss, bot):
    open_menu(boss)
    press(boss, "admin:users")
    press(boss, "admin:forward")
    boss.router.handle_message(make_message("hello", is_forwarded=True))
    assert "hides their account" in bot.last.text


def test_promoting_takes_effect_at_once(boss, bot):
    add_people(boss, 1, Role.GUEST)
    open_menu(boss)
    press(boss, "admin:user:2")
    press(boss, "admin:role:2")
    press(boss, "admin:role_set:2:1")
    assert boss.storage.users.get_role(2) == Role.USER
    assert "The rank has been changed to _User_" in bot.last.text


def test_the_user_is_told_about_the_new_rank(boss, bot):
    add_people(boss, 1, Role.GUEST)
    boss.storage.settings.set_language(2, "pl")
    open_menu(boss)
    press(boss, "admin:user:2")
    press(boss, "admin:role:2")
    screen = bot.last.message_id
    bot.clear()
    boss.router.handle_callback(make_callback("admin:role_set:2:1", message_id=screen))
    told = [message for message in bot.sent if message.chat_id == 2]
    assert told and told[0].text == "Zmieniono Twoją rangę na: _Użytkownik_"


def test_lowering_the_rank_asks_first(boss, bot):
    add_people(boss, 1, Role.USER)
    open_menu(boss)
    press(boss, "admin:user:2")
    press(boss, "admin:role:2")
    press(boss, "admin:role_set:2:0")
    assert "Are you sure you want to lower the rank" in bot.last.text
    assert boss.storage.users.get_role(2) == Role.USER
    press(boss, "admin:role_confirmed:2:0")
    assert boss.storage.users.get_role(2) == Role.GUEST


def test_banning_asks_first(boss, bot):
    add_people(boss, 1, Role.USER)
    open_menu(boss)
    press(boss, "admin:user:2")
    press(boss, "admin:role:2")
    press(boss, "admin:role_set:2:-1")
    assert "Are you sure" in bot.last.text
    press(boss, "admin:role_confirmed:2:-1")
    assert boss.storage.users.get_role(2) == Role.BANNED


def test_the_current_rank_is_not_offered_again(boss, bot):
    add_people(boss, 1, Role.USER)
    open_menu(boss)
    press(boss, "admin:user:2")
    press(boss, "admin:role:2")
    assert "admin:role_set:2:1" not in [data for _, data in bot.last.buttons]
    assert len([data for _, data in bot.last.buttons if "role_set" in data]) == 3


def test_deleting_a_user_asks_first(boss, bot):
    add_people(boss, 1)
    open_menu(boss)
    press(boss, "admin:user:2")
    press(boss, "admin:wipe:2")
    assert "cannot be undone" in bot.last.text
    assert boss.storage.users.exists(2)
    press(boss, "admin:wipe_confirmed:2")
    assert not boss.storage.users.exists(2)
    assert "has been deleted" in bot.last.text


def test_statistics_count_everyone(boss, bot):
    add_people(boss, 3, Role.USER)
    add_people(boss, 0)
    boss.storage.users.set_consent(2, True)
    open_menu(boss)
    press(boss, "admin:statistics")
    assert "User: _3_" in bot.last.text
    assert "Admin: _1_" in bot.last.text
    assert "Users in total: _4_" in bot.last.text
    assert "With the agreement: _2_" in bot.last.text
    assert "Running for: _0d 0h 0m_" in bot.last.text


def test_an_announcement_reaches_the_others(boss, bot):
    add_people(boss, 2)
    boss.storage.settings.set_notifications(3, False)
    open_menu(boss)
    press(boss, "admin:announcement")
    bot.clear()
    boss.router.handle_message(make_message("The Bot will rest tonight"))
    boss.router.wait_for_tasks()
    reached = [message.chat_id for message in bot.sent if message.chat_id != 1]
    assert reached == [2]
    assert bot.sent[0].text == "The Bot will rest tonight"
    assert "reached _1_ users" in bot.last.text


def test_alerts_can_be_turned_off(boss, bot):
    open_menu(boss)
    press(boss, "admin:alerts")
    assert "Alerts about new Users are on" in bot.last.text
    press(boss, "admin:alerts_set:0")
    assert not boss.storage.settings.has_admin_alerts(1)
    assert "are now off" in bot.last.text


def test_the_bot_screen_shows_the_version(boss, bot):
    open_menu(boss)
    press(boss, "admin:bot")
    assert "Version: _" in bot.last.text
    assert [data for _, data in bot.last.buttons] == ["admin:log", "admin:restart", "core:back"]


def test_the_log_screen_reads_the_newest_file(boss, bot, tmp_path, monkeypatch):
    monkeypatch.setattr(admin.paths, "log_dir", str(tmp_path))
    (tmp_path / "log_2026-01-01.log").write_text("older\n", encoding='utf8')
    (tmp_path / "log_2026-01-02.log").write_text("line one\nline two\n", encoding='utf8')
    open_menu(boss)
    press(boss, "admin:bot")
    press(boss, "admin:log")
    assert bot.last.text.endswith("```\nline one\nline two\n```")


def test_the_log_screen_survives_an_empty_directory(boss, bot, tmp_path, monkeypatch):
    monkeypatch.setattr(admin.paths, "log_dir", str(tmp_path))
    open_menu(boss)
    press(boss, "admin:bot")
    press(boss, "admin:log")
    assert bot.last.text.endswith("There is nothing in the log yet.")


def test_restarting_asks_first(boss, bot, monkeypatch):
    stopped = []
    monkeypatch.setattr(admin, "stop_process", lambda: stopped.append(True))
    open_menu(boss)
    press(boss, "admin:bot")
    press(boss, "admin:restart")
    assert "Are you sure you want to restart" in bot.last.text
    assert not stopped
    press(boss, "admin:restart_confirmed")
    assert stopped == [True]
    assert "restarting" in bot.last.text


def test_going_back_walks_up_the_whole_tree(boss, bot):
    open_menu(boss)
    press(boss, "admin:users")
    press(boss, "admin:list:0")
    assert boss.storage.navigation.depth(1) == 3
    press(boss, "core:back")
    assert bot.last.text.startswith("*🛠️ Admin > 🙋 Users:*")
    press(boss, "core:back")
    assert bot.last.text.startswith("*🛠️ Admin:*")
    press(boss, "core:back")
    assert bot.last.text == "The menu has been closed"
