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
    assert bot.last.text == "*⚙️ Settings:*\n\nSelect the setting of the following:"
    assert [data for _, data in bot.last.buttons] == [
        "settings:notifications", "settings:language", "settings:deletedata", "core:close"]


def test_a_guest_is_not_offered_notifications(app, bot):
    app.storage.users.set_role(1, Role.GUEST)
    open_menu(app)
    assert "settings:notifications" not in [data for _, data in bot.last.buttons]


def test_the_menu_is_a_screen(app):
    open_menu(app)
    assert app.storage.navigation.current(1) is not None
    assert not_none(app.storage.navigation.current(1))['view'] == "menu"


def test_turning_notifications_on(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    assert bot.last.text == "*⚙️ Settings > 🛎️ Notifications:*\n\nDo you want notifications to be turned on?"
    press(app, "settings:notifications_set:1")
    assert bot.last.text == "*⚙️ Settings:*\n\nNotifications have been enabled ✅"
    assert app.storage.settings.has_notifications(1)


def test_turning_notifications_off(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    press(app, "settings:notifications_set:0")
    assert bot.last.text.endswith("Notifications have been disabled ❌")
    assert not app.storage.settings.has_notifications(1)


def test_answering_closes_the_question_screen(app, bot):
    open_menu(app)
    press(app, "settings:notifications")
    question = bot.last.message_id
    press(app, "settings:notifications_set:1")
    assert (1, question) in bot.deleted
    assert app.storage.navigation.current(1) is None


def test_changing_the_language_answers_in_the_new_one(app, bot):
    open_menu(app)
    press(app, "settings:language")
    assert [text for text, _ in bot.last.buttons][:2] == ["🇬🇧 English", "🇵🇱 Polski"]
    press(app, "settings:language_set:pl")
    assert bot.last.text == "*⚙️ Ustawienia:*\n\nZmieniono język ✅"
    assert app.storage.settings.get_language(1) == "pl"


def test_the_menu_speaks_the_new_language_afterwards(app, bot):
    open_menu(app)
    press(app, "settings:language")
    press(app, "settings:language_set:pl")
    open_menu(app)
    assert bot.last.text == "*⚙️ Ustawienia:*\n\nWybierz opcję z podanych:"


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
    assert bot.last.text.startswith("*⚙️ Settings:*")
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
