from core.api import Module, View
from core.roles import Role
from core.testing import make_callback, make_message
from core.utils import not_none


def open_menu(app):
    app.router.handle_message(make_message("/settings"))
    return app.services.bot.last.message_id


def press(app, data: str):
    app.router.handle_callback(make_callback(data, message_id=app.services.bot.last.message_id))


def test_the_menu_lists_every_setting(app, bot):
    open_menu(app)
    assert bot.last.text == "<b>⚙️ Settings:</b>\n\nSelect the setting of the following:"
    assert [data for _, data in bot.last.buttons] == [
        "settings:notifications", "settings:language", "core:settings:downloader", "settings:deletedata",
        "core:close"]


def test_a_guest_is_not_offered_notifications(app, bot):
    app.storage.users.set_role(1, Role.GUEST)
    open_menu(app)
    assert "settings:notifications" not in [data for _, data in bot.last.buttons]


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


def add_module_with_settings(app, role: Role) -> None:
    extra = Module(name="extra")
    extra.settings(role=role)(lambda ctx: View("extra settings"))
    app.catalog.add("extra", "en", {'name': "🧩 Extra"})
    app.registry.add(extra)


def test_a_module_with_settings_is_listed_before_data_deletion(app, bot):
    add_module_with_settings(app, Role.USER)
    open_menu(app)
    assert [data for _, data in bot.last.buttons] == [
        "settings:notifications", "settings:language", "core:settings:downloader", "core:settings:extra",
        "settings:deletedata",
        "core:close"]
    assert "🧩 Extra" in [text for text, _ in bot.last.buttons]


def test_module_settings_above_the_user_role_are_not_listed(app, bot):
    add_module_with_settings(app, Role.ADMIN)
    open_menu(app)
    assert "core:settings:extra" not in [data for _, data in bot.last.buttons]


def test_module_settings_open_under_the_menu(app, bot):
    add_module_with_settings(app, Role.USER)
    open_menu(app)
    press(app, "core:settings:extra")
    assert bot.last.text == "<b>⚙️ Settings &gt; 🧩 Extra:</b>\n\nextra settings"
    press(app, "core:back")
    assert bot.last.text == "<b>⚙️ Settings:</b>\n\nSelect the setting of the following:"
