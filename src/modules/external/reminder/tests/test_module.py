from datetime import datetime, timedelta

import pytest

from core.api import Ctx, JobCtx, Outcome, Role, User
from core.testing import make_callback, make_message, not_none
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


def refuse(app, refused: int) -> None:
    bot = app.services.bot
    sending = bot.send_message

    def send_message(chat_id, *arguments, **values):
        if chat_id == refused:
            raise RuntimeError("Forbidden: bot was blocked by the user")
        return sending(chat_id, *arguments, **values)

    bot.send_message = send_message


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
    assert "<i>0</i>" in bot.last.text
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


def test_a_refused_date_is_written_into_the_screen_that_asked(app, bot):
    send(app, "/reminder")
    click(app, bot, "reminder:set")
    send(app, content1)
    asked = bot.last.message_id
    send(app, "next tuesday")
    assert "I do not understand this date" in bot.last.text
    assert "Write when I should remind you" in bot.last.text
    assert bot.last.buttons[-1][1] == "core:close"
    assert (1, asked) in bot.deleted


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
    assert "Page <i>1</i> of <i>1</i>" in bot.last.text


def test_a_longer_list_is_split_into_pages(app, bot):
    fill(app, bot, reminder.page_size + 3)
    open_list(app, bot)
    labels = [text for text, _ in bot.last.buttons]
    assert len([one for one in labels if one.startswith(("🔔", "🔕"))]) == reminder.page_size
    assert "⬅️ Previous" in labels and "➡️ Next" in labels
    assert "Page <i>1</i> of <i>2</i>" in bot.last.text
    assert "<i>11</i> in total" in bot.last.text


def test_the_next_page_shows_the_rest(app, bot):
    fill(app, bot, reminder.page_size + 3)
    open_list(app, bot)
    click(app, bot, "reminder:manage:1")
    labels = [text for text, _ in bot.last.buttons]
    assert len([one for one in labels if one.startswith(("🔔", "🔕"))]) == 3
    assert "Page <i>2</i> of <i>2</i>" in bot.last.text


def test_a_page_past_the_end_falls_back_to_the_last_one(app, bot):
    fill(app, bot, reminder.page_size + 3)
    open_list(app, bot)
    click(app, bot, "reminder:manage:9")
    assert "Page <i>2</i> of <i>2</i>" in bot.last.text


def test_the_reminder_screen_shows_its_state(app, bot):
    set_one(app, bot)
    click(app, bot, "reminder:one:1")
    assert bot.last.text.startswith("<b>🔔 Reminders &gt; Manage reminders:</b>\n\n🔔 " + content1)


def test_the_furthest_away_comes_first(app, bot):
    set_one(app, bot, content="Soonest", date=later(1))
    set_one(app, bot, content="Latest", date=later(9))
    set_one(app, bot, content="Middle", date=later(5))
    open_list(app, bot)
    shown = [text for text, _ in bot.last.buttons if text.startswith(("🔔", "🔕"))]
    assert shown == ["🔔 Latest", "🔔 Middle", "🔔 Soonest"]


def test_a_reminder_that_cannot_be_delivered_does_not_hold_up_the_others(app, bot):
    app.storage.users.save(2, "Other", "Person", "other")
    app.storage.settings.set_language(2, "en")
    set_one(app, bot, content1)
    app.storage.database.execute("INSERT INTO " + table_of(app) + " (user_id, date, content) VALUES (?, ?, ?);",
                                 (2, later(), content2))
    make_due(app)
    refuse(app, 1)
    bot.clear()
    run_job(app)
    assert [message.chat_id for message in bot.sent] == [2]
    assert [row['is_notified'] for row in rows(app)] == [0, 1]


# ----- assistant -----

def as_user(app, user_id: int = 1) -> Ctx:
    person = User(user_id, "First", "Last", "username", Role.GUEST, "en", True)
    return Ctx(app.services, not_none(app.registry.get("reminder")), person)


def test_adding_asks_with_what_it_would_set(app, bot):
    date = later()
    outcome = reminder.act_add(as_user(app), " " + content1 + " ", date)
    assert outcome.status == "asking"
    assert outcome.result == ("Do you want me to set this reminder?\nContent: <i>" + content1 + "</i>\nDate: <i>"
                              + date + "</i>")
    assert rows(app) == []


def test_adding_sets_the_reminder_once_confirmed(app, bot):
    date = later()
    done = reminder.act_add(as_user(app), content1, date).then()
    assert done.startswith("The reminder has been set ✅\nContent:")
    assert [(row['user_id'], row['content'], row['date']) for row in rows(app)] == [(1, content1, date)]


@pytest.mark.parametrize("content, date, problem", [
    ("", later(), "The content has to be between 1 and 200 characters long"),
    ("x" * 201, later(), "The content has to be between 1 and 200 characters long"),
    (content1, "tomorrow at 3", "I do not understand this date, write it like this: <i>"),
    (content1, later(-1), "I cannot remind you about something in the past"),
])
def test_adding_is_checked_the_same_way_as_on_the_screens(app, bot, content, date, problem):
    outcome = reminder.act_add(as_user(app), content, date)
    assert outcome.status == "refused" and str(outcome.result).startswith(problem)


def test_the_list_gives_the_model_plain_values(app, bot):
    date = set_one(app, bot)
    assert reminder.act_list(as_user(app)) == Outcome.done([{'reminder_id': 1, 'date': date, 'content': content1,
                                                             'is_sent': False}])
    assert reminder.act_list(as_user(app, 2)) == Outcome.done([])


def test_deleting_asks_and_deletes_once_confirmed(app, bot):
    set_one(app, bot)
    outcome = reminder.act_delete(as_user(app), 1)
    assert outcome.status == "asking" and str(outcome.result).startswith("Do you really want to delete this reminder?")
    assert len(rows(app)) == 1
    assert outcome.then() == "The reminder has been deleted ✅"
    assert rows(app) == []


def test_nobody_deletes_a_reminder_of_someone_else(app, bot):
    set_one(app, bot)
    assert reminder.act_delete(as_user(app, 2), 1) == \
        Outcome.refused("There is no such reminder - it may have been deleted or the number is wrong")
    assert len(rows(app)) == 1


def test_the_summary_tells_the_next_reminders(app, bot):
    assert reminder.summary(as_user(app)) == ""
    dates = {days: set_one(app, bot, content, later(days))
             for days, content in [(3, "third"), (1, "<first>"), (2, "second"), (4, "fourth")]}
    assert reminder.summary(as_user(app)) == "The next reminders:\n" + "\n".join(
        [dates[1] + " - &lt;first&gt;", dates[2] + " - second", dates[3] + " - third"])
    assert reminder.summary(as_user(app, 2)) == ""


def test_editing_asks_with_the_reminder_as_it_would_be(app, bot):
    first = set_one(app, bot)
    date = later(2)
    outcome = reminder.act_edit(as_user(app), 1, None, date)
    assert outcome.result == ("Do you want me to change the reminder into this?\nContent: <i>" + content1 +
                              "</i>\nDate: <i>" + date + "</i>")
    assert rows(app)[0]['date'] == first
    assert outcome.then().startswith("The reminder has been changed ✅")
    assert (rows(app)[0]['content'], rows(app)[0]['date']) == (content1, date)


def test_editing_the_content_keeps_the_date(app, bot):
    date = set_one(app, bot)
    reminder.act_edit(as_user(app), 1, " " + content2 + " ", None).then()
    assert (rows(app)[0]['content'], rows(app)[0]['date']) == (content2, date)


def test_a_new_date_lets_a_sent_reminder_ring_again(app, bot):
    set_one(app, bot)
    app.storage.database.execute("UPDATE " + table_of(app) + " SET is_notified = 1;")
    reminder.act_edit(as_user(app), 1, content2, None).then()
    assert rows(app)[0]['is_notified'] == 1
    reminder.act_edit(as_user(app), 1, None, later(3)).then()
    assert rows(app)[0]['is_notified'] == 0


@pytest.mark.parametrize("content, date, problem", [
    (None, None, "Nothing to change - give a new content, a new date or both"),
    ("", None, "The content has to be between 1 and 200 characters long"),
    (None, "tomorrow", "I do not understand this date"),
    (None, later(-1), "I cannot remind you about something in the past"),
])
def test_editing_is_checked_the_same_way_as_on_the_screens(app, bot, content, date, problem):
    set_one(app, bot)
    outcome = reminder.act_edit(as_user(app), 1, content, date)
    assert outcome.status == "refused" and str(outcome.result).startswith(problem)


def test_nobody_edits_a_reminder_of_someone_else(app, bot):
    set_one(app, bot)
    assert reminder.act_edit(as_user(app, 2), 1, content2, None) == \
        Outcome.refused("There is no such reminder - it may have been deleted or the number is wrong")
    assert rows(app)[0]['content'] == content1


def test_the_list_for_the_model_starts_with_the_soonest_waiting_ones(app, bot, monkeypatch):
    monkeypatch.setattr(reminder, "listed_limit", 3)
    dates = [set_one(app, bot, "in " + str(days), later(days)) for days in (5, 1, 3, 2)]
    app.storage.database.execute("UPDATE " + table_of(app) + " SET is_notified = 1 WHERE content = 'in 1';")
    listed = reminder.act_list(as_user(app)).result
    assert isinstance(listed, list)
    assert [(one['content'], one['date'], one['is_sent']) for one in listed] == \
        [("in 2", dates[3], False), ("in 3", dates[2], False), ("in 5", dates[0], False)]
