import pytest

from core.roles import Role
from core.testing import make_callback, make_message


@pytest.fixture
def admin(app):
    app.storage.users.save(2, "Admin", "Person", "theadmin")
    app.storage.users.set_role(2, Role.ADMIN)
    app.storage.settings.set_language(2, "en")
    return 2


def test_contact_names_the_administrator(app, bot):
    app.router.handle_message(make_message("/contact"))
    assert bot.last.text.startswith("*☎️ Contact:*")
    assert "@" in bot.last.text
    assert [data for _, data in bot.last.buttons] == ["contact:report"]


def test_report_opens_a_screen_that_waits_for_the_message(app, bot):
    app.router.handle_message(make_message("/report"))
    assert bot.last.text.startswith("*☎️ Contact > 📨 Report:*")
    assert app.storage.navigation.depth(1) == 1


def test_the_contact_button_opens_the_same_screen(app, bot):
    app.router.handle_message(make_message("/contact"))
    app.router.handle_callback(make_callback("contact:report", message_id=bot.last.message_id))
    assert bot.last.text.startswith("*☎️ Contact > 📨 Report:*")


def test_a_report_reaches_the_admin(app, bot, admin):
    app.router.handle_message(make_message("/report"))
    bot.clear()
    app.router.handle_message(make_message("The downloader is broken"))
    forwarded = [message for message in bot.sent if message.chat_id == admin]
    assert len(forwarded) == 1
    assert forwarded[0].text == ("Hi, First (1) would like to send you this report-message:\n\n"
                                 "The downloader is broken")
    assert forwarded[0].parse_mode is None


def test_the_sender_is_told_it_went_through(app, bot, admin):
    app.router.handle_message(make_message("/report"))
    app.router.handle_message(make_message("value1"))
    assert bot.last.text == "Your report-message has been sent successfully 😁"
    assert app.storage.navigation.depth(1) == 0


def test_a_report_reaches_every_admin(app, bot, admin):
    app.storage.users.save(3, "Second", "Admin", "second")
    app.storage.users.set_role(3, Role.ADMIN)
    app.router.handle_message(make_message("/report"))
    bot.clear()
    app.router.handle_message(make_message("value1"))
    assert sorted(message.chat_id for message in bot.sent if message.chat_id != 1) == [2, 3]


def test_each_admin_reads_it_in_their_own_language(app, bot, admin):
    app.storage.settings.set_language(admin, "pl")
    app.router.handle_message(make_message("/report"))
    bot.clear()
    app.router.handle_message(make_message("value1"))
    forwarded = [message for message in bot.sent if message.chat_id == admin]
    assert forwarded[0].text.startswith("Cześć, First (1) chce przekazać Ci")


def test_a_report_with_markdown_characters_survives(app, bot, admin):
    app.router.handle_message(make_message("/report"))
    bot.clear()
    app.router.handle_message(make_message("the *_weird_* thing {broken}"))
    forwarded = [message for message in bot.sent if message.chat_id == admin]
    assert forwarded[0].text.endswith("the *_weird_* thing {broken}")


def test_a_silent_admin_gets_a_silent_message(app, bot, admin):
    app.storage.settings.set_notifications(admin, False)
    app.router.handle_message(make_message("/report"))
    bot.clear()
    app.router.handle_message(make_message("value1"))
    forwarded = [message for message in bot.sent if message.chat_id == admin]
    assert forwarded[0].is_silent


def test_without_an_admin_the_sender_is_told(app, bot, capsys):
    app.router.handle_message(make_message("/report"))
    app.router.handle_message(make_message("value1"))
    assert bot.last.text == "Sorry, your report-message could not be sent... Please, try again later 😞"
    assert "A report could not be sent - there are no admins." in capsys.readouterr().out


def test_a_message_outside_the_report_screen_is_not_forwarded(app, bot, admin):
    app.router.handle_message(make_message("just chatting"))
    assert not [message for message in bot.sent if message.chat_id == admin]
