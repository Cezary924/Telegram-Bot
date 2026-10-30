from datetime import date

from core.api import Module, Profile, View, years_before
from core.roles import Role
from core.testing import make_callback, make_message
from core.utils import not_none


def open_menu(app):
    app.router.handle_message(make_message("/settings"))
    return app.services.bot.last.message_id


def press(app, data: str):
    app.router.handle_callback(make_callback(data, message_id=app.services.bot.last.message_id))


settings_modules = ["downloader", "llm"]


def test_the_menu_lists_every_setting(app, bot):
    open_menu(app)
    assert bot.last.text == "<b>⚙️ Settings:</b>\n\nSelect the setting of the following:"
    assert [data for _, data in bot.last.buttons] == [
        "settings:notifications", "settings:language", "settings:profile", "settings:modules", "settings:deletedata",
        "core:close"]


def test_the_modules_are_listed_in_their_order(app, bot):
    open_menu(app)
    press(app, "settings:modules")
    assert bot.last.text == "<b>⚙️ Settings &gt; 🧩 Modules:</b>\n\nChoose a module to change its settings"
    assert [data for _, data in bot.last.buttons] == \
        ["core:settings:" + name for name in settings_modules] + ["core:back", "core:home", "core:close"]


def test_without_any_module_settings_there_is_no_list(app, bot):
    app.storage.users.set_role(1, Role.GUEST)
    for name in settings_modules:
        app.storage.access.allow(1, name, False)
    open_menu(app)
    assert "settings:modules" not in [data for _, data in bot.last.buttons]


def test_a_guest_is_offered_notifications_too(app, bot):
    app.storage.users.set_role(1, Role.GUEST)
    open_menu(app)
    assert "settings:notifications" in [data for _, data in bot.last.buttons]
    press(app, "settings:notifications")
    assert "Choose what may make a sound" in bot.last.text


def test_the_menu_is_a_screen(app):
    open_menu(app)
    assert app.storage.navigation.current(1) is not None
    assert not_none(app.storage.navigation.current(1))['view'] == "menu"


def notification_buttons(bot) -> list[str]:
    return [text for text, data in bot.last.buttons if data.startswith("settings:notifications_toggle")]


def test_the_notifications_screen_lists_every_source(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    assert bot.last.text.startswith("<b>⚙️ Settings &gt; 🛎️ Notifications:</b>")
    assert "With sound: <i>3/3</i>" in bot.last.text
    assert notification_buttons(bot) == ["🤖 From the Bot 🔊", "📢 Announcements 🔊", "🔔 Reminders 🔊"]


def test_one_source_can_go_silent_in_place(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    screen = bot.last.message_id
    press(app, "settings:notifications_toggle:reminder")
    assert bot.last.message_id == screen
    assert "🔔 Reminders 🔕" in notification_buttons(bot)
    assert "With sound: <i>2/3</i>" in bot.last.text
    assert not app.storage.notifications.is_loud(1, "reminder")
    assert app.storage.notifications.is_loud(1, "admin")


def test_every_source_can_go_silent_at_once(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    press(app, "settings:notifications_all:0")
    assert "With sound: <i>0/3</i>" in bot.last.text
    assert not app.storage.settings.has_notifications(1)
    press(app, "settings:notifications_all:1")
    assert "With sound: <i>3/3</i>" in bot.last.text


def test_notifications_can_be_blocked_and_unblocked(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    press(app, "settings:notifications_block:1")
    assert "All notifications are blocked" in bot.last.text
    assert app.storage.notifications.is_blocked(1)
    assert "settings:notifications_block:0" in [data for _, data in bot.last.buttons]
    press(app, "settings:notifications_block:0")
    assert not app.storage.notifications.is_blocked(1)


def test_an_unknown_source_is_refused(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    press(app, "settings:notifications_toggle:nobody")
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"


def test_changing_the_language_answers_in_the_new_one(app, bot):
    open_menu(app)
    press(app, "settings:language")
    assert [text for text, _ in bot.last.buttons][:2] == ["🇬🇧 English", "🇵🇱 Polski"]
    press(app, "settings:language_set:pl")
    assert bot.last.text == "<b>⚙️ Ustawienia:</b>\n\nZmieniono język ✅"
    assert app.storage.settings.get_language(1) == "pl"


def test_the_menu_speaks_the_new_language_afterwards(app, bot):
    open_menu(app)
    press(app, "settings:language")
    press(app, "settings:language_set:pl")
    open_menu(app)
    assert bot.last.text == "<b>⚙️ Ustawienia:</b>\n\nWybierz opcję z podanych:"


def test_an_unknown_language_is_refused(app, bot):
    open_menu(app)
    press(app, "settings:language")
    press(app, "settings:language_set:de")
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"
    assert app.storage.settings.get_language(1) == "en"


def test_deleting_data_asks_first(app, bot):
    open_menu(app)
    press(app, "settings:deletedata")
    assert "This operation cannot be undone." in bot.last.text
    assert app.storage.users.exists(1)


def test_deleting_data_removes_everything(app, bot):
    open_menu(app)
    press(app, "settings:deletedata")
    press(app, "settings:deletedata_confirmed")
    assert bot.last.text.endswith("Your data has been deleted ✅")
    assert not app.storage.users.exists(1)
    assert app.storage.profiles.get(1) == Profile()
    assert app.storage.navigation.current(1) is None


def test_going_back_walks_up_the_menu(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    assert app.storage.navigation.current(1) is not None
    press(app, "core:back")
    assert bot.last.text.startswith("<b>⚙️ Settings:</b>")
    press(app, "core:back")
    assert bot.last.text == "The menu has been closed"
    assert app.storage.navigation.current(1) is None


def test_reopening_the_menu_does_not_stack_it(app, bot):
    open_menu(app)
    press(app, "settings:language")
    open_menu(app)
    assert app.storage.navigation.current(1) is not None
    press(app, "core:back")
    assert bot.last.text == "The menu has been closed"


def add_module_with_settings(app, role: Role = Role.GUEST, is_guarded: bool = True, name: str = "extra") -> None:
    extra = Module(name=name, is_guarded=is_guarded)
    extra.settings(role=role)(lambda ctx: View("extra settings"))
    app.catalog.add(name, "en", {'name': "🧪 " + name.capitalize()})
    app.registry.add(extra)
    app.storage.access.allow(1, name, True)


def open_modules(app):
    open_menu(app)
    press(app, "settings:modules")


def test_a_module_without_a_place_is_listed_last(app, bot):
    add_module_with_settings(app)
    open_modules(app)
    assert [data for _, data in bot.last.buttons][:-3] == \
        ["core:settings:" + name for name in settings_modules] + ["core:settings:extra"]
    assert "🧪 Extra" in [text for text, _ in bot.last.buttons]


def test_module_settings_above_the_user_role_are_not_listed(app, bot):
    add_module_with_settings(app, Role.ADMIN)
    open_modules(app)
    assert "core:settings:extra" not in [data for _, data in bot.last.buttons]


def test_a_long_list_of_modules_comes_a_page_at_a_time(app, bot):
    extras = ["extra" + str(number) for number in range(9 - len(settings_modules))]
    for name in extras:
        add_module_with_settings(app, name=name)
    open_modules(app)
    assert len([data for _, data in bot.last.buttons if data.startswith("core:settings:")]) == 8
    assert "Page <i>1</i> of <i>2</i>" in bot.last.text
    press(app, "settings:modules:1")
    assert [data for _, data in bot.last.buttons if data.startswith("core:settings:")] == \
        ["core:settings:" + extras[-1]]
    press(app, "core:settings:" + extras[-1])
    press(app, "core:back")
    assert "Page <i>2</i> of <i>2</i>" in bot.last.text


def test_module_settings_open_under_the_modules(app, bot):
    add_module_with_settings(app)
    open_modules(app)
    press(app, "core:settings:extra")
    assert bot.last.text == "<b>⚙️ Settings &gt; 🧩 Modules &gt; 🧪 Extra:</b>\n\nextra settings"
    press(app, "core:back")
    assert bot.last.text.startswith("<b>⚙️ Settings &gt; 🧩 Modules:</b>")
    press(app, "core:settings:extra")
    press(app, "core:home")
    assert bot.last.text == "<b>⚙️ Settings:</b>\n\nSelect the setting of the following:"


def open_profile(app):
    open_menu(app)
    press(app, "settings:profile")


def test_about_me_starts_empty_and_in_metric_units(app, bot):
    open_profile(app)
    assert "Sex: <i>not given</i>" in bot.last.text and "Date of birth: <i>not given</i>" in bot.last.text
    assert "Weight unit: <i>kg</i>" in bot.last.text and "Height unit: <i>cm</i>" in bot.last.text


def test_sex_and_age_are_saved_for_every_module(app, bot):
    open_profile(app)
    press(app, "settings:set_sex")
    press(app, "settings:sex:sex:female")
    assert "Sex: <i>Female</i>" in bot.last.text
    press(app, "settings:set_born")
    app.router.handle_message(make_message("30"))
    assert app.storage.profiles.get(1) == Profile("female", years_before(date.today(), 30).isoformat())
    assert app.storage.profiles.get(1).age == 30


def test_a_birth_date_can_be_written_the_polish_way(app):
    open_profile(app)
    press(app, "settings:set_born")
    app.router.handle_message(make_message("30.10.1990"))
    assert app.storage.profiles.get(1).born == "1990-10-30"


def test_an_age_outside_the_limits_is_asked_again(app, bot):
    open_profile(app)
    press(app, "settings:set_born")
    app.router.handle_message(make_message("12"))
    assert "an age between 18 and 120" in bot.last.text
    assert app.storage.profiles.get(1).born is None


def test_units_switch_back_and_forth(app, bot):
    open_profile(app)
    press(app, "settings:weight_unit")
    press(app, "settings:height_unit")
    assert "Weight unit: <i>lb</i>" in bot.last.text and "Height unit: <i>ft in</i>" in bot.last.text
    assert app.storage.profiles.get(1) == Profile(weight_unit="lb", height_unit="ftin")
    press(app, "settings:weight_unit")
    assert app.storage.profiles.get(1).weight_unit == "kg"


def test_the_birth_date_can_be_taken_back_on_its_own(app, bot):
    app.storage.profiles.set(1, "sex", "male")
    app.storage.profiles.set(1, "born", "1990-10-30")
    app.storage.profiles.set(1, "weight_unit", "lb")
    open_profile(app)
    press(app, "settings:set_born")
    assert ("🙈 Rather not say", "settings:born:born:-") in bot.last.buttons
    press(app, "settings:born:born:-")
    assert app.storage.profiles.get(1) == Profile("male", weight_unit="lb")
    assert "Date of birth: <i>not given</i>" in bot.last.text and "Sex: <i>Male</i>" in bot.last.text
