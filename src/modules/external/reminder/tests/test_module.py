from datetime import datetime, timedelta

import pytest

from core.api import JobCtx
from core.testing import make_callback, make_message
from modules.external.reminder import module as reminder

content1 = "Buy milk"
content2 = "Buy bread"


def later(days: int = 1) -> str:
    return (datetime.now() + timedelta(days=days)).strftime(reminder.date_format)


def send(app, text: str):
    app.router.handle_message(make_message(text))


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))


def rows(app):
    return app.storage.database.query_all("SELECT * FROM " + table_of(app) + " ORDER BY id;")


def set_one(app, bot, content: str = content1, date: str = "") -> str:
    date = date or later()
    send(app, "/reminder")
    click(app, bot, "reminder:set")
    send(app, content)
    send(app, date)
    return date


def make_due(app, minutes: int = 1) -> None:
    moment = (datetime.now() - timedelta(minutes=minutes)).strftime(reminder.date_format)
    app.storage.database.execute("UPDATE " + table_of(app) + " SET date = ?;", (moment,))


def table_of(app) -> str:
    return app.storage.for_module("reminder").table("reminders")


def run_job(app):
    reminder.check_reminders(JobCtx(app.services, app.registry.get("reminder")))


@pytest.mark.parametrize("text, is_valid", [
    ("2027-01-05 09:30", True),
    ("2027-01-05 9:30", True),
    ("2027-13-05 09:30", False),
    ("2027-01-05", False),
    ("tomorrow", False),
    ("", False),
])
def test_only_a_full_date_is_understood(text, is_valid):
    assert (reminder.parse_date(text) is not None) == is_valid


def test_the_menu_counts_what_is_set(app, bot):
    send(app, "/reminder")
    assert "_0_" in bot.last.text
    assert [text for text, _ in bot.last.buttons][:1] == ["Set a reminder"]


def test_managing_shows_up_only_with_something_to_manage(app, bot):
    send(app, "/reminder")
    assert "Manage reminders" not in [text for text, _ in bot.last.buttons]
    set_one(app, bot)
    send(app, "/reminder")
    assert "Manage reminders" in [text for text, _ in bot.last.buttons]


def test_a_reminder_is_stored_with_its_owner(app, bot):
    date = set_one(app, bot)
    stored = rows(app)
    assert len(stored) == 1
    assert (stored[0]['user_id'], stored[0]['content'], stored[0]['date']) == (1, content1, date)
    assert stored[0]['is_notified'] == 0
    assert "has been set" in bot.last.text


def test_a_date_that_makes_no_sense_is_refused(app, bot):
    send(app, "/reminder")
    click(app, bot, "reminder:set")
    send(app, content1)
    send(app, "next tuesday")
    assert "I do not understand this date" in bot.last.text
    assert rows(app) == []


def test_a_date_in_the_past_is_refused(app, bot):
    send(app, "/reminder")
    click(app, bot, "reminder:set")
    send(app, content1)
    send(app, later(-1))
    assert "in the past" in bot.last.text
    assert rows(app) == []


def test_the_date_screen_survives_a_wrong_answer(app, bot):
    send(app, "/reminder")
    click(app, bot, "reminder:set")
    send(app, content1)
    send(app, "nonsense")
    date = later()
    send(app, date)
    assert rows(app)[0]['date'] == date


def test_empty_content_is_refused(app, bot):
    send(app, "/reminder")
    click(app, bot, "reminder:set")
    send(app, "   ")
    assert "between 1 and" in bot.last.text


def test_content_longer_than_the_limit_is_refused(app, bot):
    send(app, "/reminder")
    click(app, bot, "reminder:set")
    send(app, "x" * (reminder.content_limit + 1))
    assert "between 1 and" in bot.last.text


def test_the_content_can_be_changed(app, bot):
    set_one(app, bot)
    send(app, "/reminder")
    click(app, bot, "reminder:manage")
    click(app, bot, "reminder:one:1")
    click(app, bot, "reminder:set:1")
    send(app, content2)
    assert "has been changed" in bot.last.text
    assert rows(app)[0]['content'] == content2


def test_the_date_can_be_changed(app, bot):
    set_one(app, bot)
    click(app, bot, "reminder:date:1")
    date = later(5)
    send(app, date)
    assert rows(app)[0]['date'] == date


def test_a_due_reminder_is_sent_and_marked(app, bot):
    set_one(app, bot)
    make_due(app)
    bot.clear()
    run_job(app)
    assert "It is time!" in bot.last.text
    assert content1 in bot.last.text
    assert rows(app)[0]['is_notified'] == 1


def test_a_long_overdue_reminder_says_so(app, bot):
    set_one(app, bot)
    make_due(app, minutes=120)
    bot.clear()
    run_job(app)
    assert "could not reach you earlier" in bot.last.text


def test_nothing_is_sent_twice(app, bot):
    set_one(app, bot)
    make_due(app)
    run_job(app)
    bot.clear()
    run_job(app)
    assert bot.sent == []


def test_a_reminder_still_ahead_is_left_alone(app, bot):
    set_one(app, bot)
    bot.clear()
    run_job(app)
    assert bot.sent == []
    assert rows(app)[0]['is_notified'] == 0


def test_the_notification_speaks_the_language_of_its_owner(app, bot):
    set_one(app, bot)
    make_due(app)
    app.storage.settings.set_language(1, "pl")
    bot.clear()
    run_job(app)
    assert "Już czas!" in bot.last.text


def test_a_changed_date_is_notified_again(app, bot):
    set_one(app, bot)
    make_due(app)
    run_job(app)
    assert rows(app)[0]['is_notified'] == 1
    click(app, bot, "reminder:date:1")
    send(app, later())
    assert rows(app)[0]['is_notified'] == 0


def test_deleting_asks_first(app, bot):
    set_one(app, bot)
    click(app, bot, "reminder:delete:1")
    assert "Do you really want to delete" in bot.last.text
    assert len(rows(app)) == 1


def test_a_confirmed_deletion_removes_it(app, bot):
    set_one(app, bot)
    click(app, bot, "reminder:delete:1")
    click(app, bot, "reminder:delete_confirmed:1")
    assert "has been deleted" in bot.last.text
    assert rows(app) == []


def test_a_reminder_of_someone_else_is_out_of_reach(app, bot):
    set_one(app, bot)
    app.storage.users.save(2, "Second", "", "someone")
    app.storage.database.execute("UPDATE " + table_of(app) + " SET user_id = 2;")
    click(app, bot, "reminder:one:1")
    assert "no longer there" in bot.last.text


def test_wiping_a_user_takes_their_reminders_with_them(app, bot):
    set_one(app, bot)
    app.storage.users.delete(1)
    assert rows(app) == []


def fill(app, bot, count: int) -> None:
    set_one(app, bot)
    extra = [(1, later(days), "Task " + str(days), 0) for days in range(2, count + 1)]
    for row in extra:
        app.storage.database.execute(
            "INSERT INTO " + table_of(app) + " (user_id, date, content, is_notified) "
            "VALUES (?, ?, ?, ?);", row)


def open_list(app, bot):
    send(app, "/reminder")
    click(app, bot, "reminder:manage")


def test_a_waiting_reminder_is_marked_apart_from_a_sent_one(app, bot):
    set_one(app, bot)
    open_list(app, bot)
    assert [text for text, _ in bot.last.buttons][0] == "🔔 " + content1
    make_due(app)
    run_job(app)
    open_list(app, bot)
    assert [text for text, _ in bot.last.buttons][0] == "🔕 " + content1


def test_the_list_fits_on_one_page_when_it_can(app, bot):
    fill(app, bot, reminder.page_size)
    open_list(app, bot)
    labels = [text for text, _ in bot.last.buttons]
    assert len([one for one in labels if one.startswith(("🔔", "🔕"))]) == reminder.page_size
    assert "⬅️ Previous" not in labels
    assert "Page _1_ of _1_" in bot.last.text


def test_a_longer_list_is_split_into_pages(app, bot):
    fill(app, bot, reminder.page_size + 3)
    open_list(app, bot)
    labels = [text for text, _ in bot.last.buttons]
    assert len([one for one in labels if one.startswith(("🔔", "🔕"))]) == reminder.page_size
    assert "⬅️ Previous" in labels and "➡️ Next" in labels
    assert "Page _1_ of _2_" in bot.last.text
    assert "_11_ in total" in bot.last.text


def test_the_next_page_shows_the_rest(app, bot):
    fill(app, bot, reminder.page_size + 3)
    open_list(app, bot)
    click(app, bot, "reminder:manage:1")
    labels = [text for text, _ in bot.last.buttons]
    assert len([one for one in labels if one.startswith(("🔔", "🔕"))]) == 3
    assert "Page _2_ of _2_" in bot.last.text


def test_a_page_past_the_end_falls_back_to_the_last_one(app, bot):
    fill(app, bot, reminder.page_size + 3)
    open_list(app, bot)
    click(app, bot, "reminder:manage:9")
    assert "Page _2_ of _2_" in bot.last.text


def test_the_reminder_screen_shows_its_state(app, bot):
    set_one(app, bot)
    click(app, bot, "reminder:one:1")
    assert bot.last.text.startswith("*🔔 Reminders > Manage reminders:*\n\n🔔 " + content1)


def test_the_furthest_away_comes_first(app, bot):
    set_one(app, bot, content="Soonest", date=later(1))
    set_one(app, bot, content="Latest", date=later(9))
    set_one(app, bot, content="Middle", date=later(5))
    open_list(app, bot)
    shown = [text for text, _ in bot.last.buttons if text.startswith(("🔔", "🔕"))]
    assert shown == ["🔔 Latest", "🔔 Middle", "🔔 Soonest"]
