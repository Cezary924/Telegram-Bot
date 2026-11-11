from datetime import date, datetime, timedelta

from core.api import Ctx
from core.testing import make_callback, make_message
from modules.external.counter import module as counter


def send(app, text: str):
    app.router.handle_message(make_message(text))
    app.router.wait_for_tasks()


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))
    app.router.wait_for_tasks()


def labels(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def table(app, name: str) -> str:
    return app.storage.for_module("counter").table(name)


def counters(app):
    return app.storage.database.query_all("SELECT * FROM " + table(app, "counters") + " ORDER BY id;")


def changes(app):
    return app.storage.database.query_all("SELECT * FROM " + table(app, "changes") + " ORDER BY id;")


def amounts(app) -> list[float]:
    return [row['amount'] for row in changes(app)]


def make(app, bot, name: str, step: str = "-", goal: str = "-", period: str = "never"):
    send(app, "/counter")
    click(app, bot, "counter:new")
    send(app, name)
    for key, answer in (("step", step), ("goal", goal)):
        if answer == "-":
            click(app, bot, "counter:create:" + key + ":-")
        else:
            send(app, answer)
    click(app, bot, "counter:create:period:" + period)


def counted_at(app, amount: float, moment: datetime, counter_id: int = 1):
    app.storage.database.execute("INSERT INTO " + table(app, "changes") + " (counter_id, user_id, amount, changed_at) "
                                 "VALUES (?, 1, ?, ?);", (counter_id, amount, moment.isoformat(timespec="seconds")))


def as_user(app) -> Ctx:
    return Ctx(app.services, app.registry.get("counter"), app.router.load_user(make_message("").from_user))


def value(app, counter_id: int = 1) -> float:
    ctx = as_user(app)
    return counter.value_of(ctx, counter.counter_of(ctx, counter_id), datetime.now())


# ----- menu and making counters -----

def test_the_command_opens_a_menu_without_any_data(app, bot):
    send(app, "/counter")
    assert bot.last.text == "<b>🔢 Counters:</b>\n\nCreate counters and count anything you like 😊"
    assert labels(bot)[:2] == ["➕ New counter", "⚙️ Settings"]
    make(app, bot, "Coffee ☕")
    counted_at(app, 3, datetime.now())
    send(app, "/counter")
    assert "3" not in bot.last.text
    assert labels(bot)[:3] == ["Coffee ☕", "➕ New counter", "⚙️ Settings"]


def test_a_counter_is_asked_for_until_it_makes_sense(app, bot):
    send(app, "/counter")
    click(app, bot, "counter:new")
    assert "Write a name for the counter" in bot.last.text
    send(app, "x" * 31)
    assert "Write between 1 and 30 characters" in bot.last.text
    send(app, "123 ☕")
    assert "A name needs at least one letter" in bot.last.text
    send(app, "Coffee +1")
    assert "cannot begin or end with a plus or minus and a number" in bot.last.text
    send(app, "  Push-ups  ")
    assert "How much should one tap" in bot.last.text and labels(bot)[0] == "One at a time"
    send(app, "0")
    assert "Write a number between 0.01 and 1000" in bot.last.text
    send(app, "10")
    assert "Write the goal" in bot.last.text and labels(bot)[0] == "No goal"
    send(app, "200000")
    assert "Write a number between 0.01 and 100000" in bot.last.text
    send(app, "100")
    assert labels(bot)[:4] == ["Never", "Every day", "Every week", "Every month"]
    click(app, bot, "counter:create:period:daily")
    assert [(row['name'], row['step'], row['goal'], row['period']) for row in counters(app)] == \
        [("Push-ups", 10, 100, "daily")]
    assert bot.last.text == "<b>🔢 Counters:</b>\n\nThe counter has been made ✅\n\n<b>Push-ups</b>\n" \
                            "<b>0 / 100</b> today\n▱▱▱▱▱▱▱▱▱▱ 0%"
    assert labels(bot)[:7] == ["➖ 10", "➕ 10", "✍️ Type an amount", "✏️ Edit", "📜 History", "📈 Chart",
                               "🗑️ Delete"]


def test_a_counter_without_a_step_or_a_goal_counts_by_one(app, bot):
    make(app, bot, "Coffee ☕")
    assert [(row['step'], row['goal'], row['period']) for row in counters(app)] == [(1, None, "never")]
    assert "<b>0</b> in total" in bot.last.text and "▱" not in bot.last.text


def test_a_name_is_taken_whatever_the_case_and_the_emoji(app, bot):
    make(app, bot, "Coffee ☕")
    send(app, "/counter")
    click(app, bot, "counter:new")
    send(app, "COFFEE")
    assert "You already have a counter called COFFEE" in bot.last.text
    send(app, "Tea 🍵")
    assert "How much should one tap" in bot.last.text


def test_back_from_a_new_counter_returns_to_the_menu(app, bot):
    send(app, "/counter")
    click(app, bot, "counter:new")
    send(app, "Coffee")
    click(app, bot, "core:back")
    assert bot.last.text == "<b>🔢 Counters:</b>\n\nCreate counters and count anything you like 😊"
    assert counters(app) == []


def test_there_is_a_limit_of_counters(app, bot):
    for number in range(counter.counter_limit):
        app.storage.database.execute("INSERT INTO " + table(app, "counters") + " (user_id, name, step, period) "
                                     "VALUES (1, ?, 1, 'never');", ("Counter " + chr(97 + number),))
    send(app, "/counter")
    click(app, bot, "counter:new")
    assert bot.last.text.startswith("<b>🔢 Counters:</b>\n\nYou already have 20 counters, delete one")
    assert len(counters(app)) == counter.counter_limit


# ----- counting -----

def test_plus_and_minus_count_by_the_step(app, bot):
    make(app, bot, "Water", step="0,5")
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:minus:1")
    assert amounts(app) == [0.5, 0.5, -0.5]
    assert "<b>0.5</b> in total" in bot.last.text and labels(bot)[:2] == ["➖ 0.5", "➕ 0.5"]


def test_any_amount_can_be_typed(app, bot):
    make(app, bot, "Push-ups")
    click(app, bot, "counter:amount:1")
    assert "Write how much to add, like 5" in bot.last.text
    send(app, "lots")
    assert "Write a number, like 5 or -2" in bot.last.text
    send(app, "0")
    assert "Write a number other than zero" in bot.last.text
    send(app, "200000")
    assert "Write a number between -100000 and 100000" in bot.last.text
    send(app, "+ 25")
    assert bot.last.text.startswith("<b>🔢 Counters:</b>\n\nCounted +25\n\n<b>Push-ups</b>\n<b>25</b> in total")
    click(app, bot, "counter:amount:1")
    send(app, "-2,5")
    click(app, bot, "counter:amount:1")
    send(app, "3")
    assert amounts(app) == [25, -2.5, 3] and "<b>25.5</b>" in bot.last.text


def test_back_from_an_amount_returns_to_the_counter(app, bot):
    make(app, bot, "Push-ups")
    click(app, bot, "counter:amount:1")
    click(app, bot, "core:back")
    assert "<b>Push-ups</b>" in bot.last.text and labels(bot)[0] == "➖ 1"


def test_reaching_the_goal_is_told_once_a_period(app, bot):
    make(app, bot, "Coffee ☕", goal="2", period="daily")
    click(app, bot, "counter:plus:1")
    assert "reached" not in bot.last.text and "▰▰▰▰▰▱▱▱▱▱ 50%" in bot.last.text
    click(app, bot, "counter:plus:1")
    assert bot.last.text.startswith("<b>🔢 Counters:</b>\n\nThe goal has been reached 🎉\n\n<b>Coffee ☕</b>\n"
                                    "<b>2 / 2</b> today\n▰▰▰▰▰▰▰▰▰▰ 100%")
    click(app, bot, "counter:plus:1")
    assert "reached" not in bot.last.text and "150%" in bot.last.text
    click(app, bot, "counter:minus:1")
    click(app, bot, "counter:minus:1")
    click(app, bot, "counter:plus:1")
    assert "reached" not in bot.last.text
    yesterday = counter.period_start("daily", datetime.now() - timedelta(days=1), 0).isoformat(timespec="seconds")
    app.storage.module_state.set(1, "counter", "reached.1", yesterday)
    click(app, bot, "counter:minus:1")
    click(app, bot, "counter:plus:1")
    assert "The goal has been reached 🎉" in bot.last.text


def test_a_goal_taken_back_can_be_reached_again(app, bot):
    make(app, bot, "Coffee", goal="2", period="daily")
    send(app, "coffee +2")
    click(app, bot, "counter:undo:" + str(changes(app)[-1]['id']))
    send(app, "coffee +2")
    assert "The goal has been reached 🎉" in bot.last.text
    last = str(changes(app)[-1]['id'])
    send(app, "/counter")
    click(app, bot, "counter:history:1")
    click(app, bot, "counter:erase:" + last)
    click(app, bot, "counter:erase_confirmed:" + last)
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:plus:1")
    assert "The goal has been reached 🎉" in bot.last.text
    click(app, bot, "counter:history:1")
    click(app, bot, "counter:amend:" + str(changes(app)[-1]['id']))
    send(app, "-1")
    send(app, "coffee +2")
    assert "The goal has been reached 🎉" in bot.last.text


def test_a_new_goal_can_be_reached_again(app, bot):
    make(app, bot, "Coffee ☕", goal="1", period="daily")
    click(app, bot, "counter:plus:1")
    assert "reached" in bot.last.text
    click(app, bot, "counter:goal:1")
    send(app, "2")
    click(app, bot, "core:back")
    click(app, bot, "counter:amount:1")
    send(app, "1")
    assert "Counted +1\nThe goal has been reached 🎉" in bot.last.text


# ----- periods -----

def test_a_period_starts_where_it_should():
    sunday = datetime(2026, 11, 1, 15, 30)
    assert counter.period_start("daily", sunday, 0) == datetime(2026, 11, 1)
    assert counter.period_start("weekly", sunday, 0) == datetime(2026, 10, 26)
    assert counter.period_start("weekly", sunday, 6) == datetime(2026, 11, 1)
    assert counter.period_start("weekly", datetime(2026, 10, 31, 23, 59), 6) == datetime(2026, 10, 25)
    assert counter.period_start("monthly", sunday, 0) == datetime(2026, 11, 1)
    assert counter.period_start("monthly", datetime(2026, 10, 31, 23, 59), 0) == datetime(2026, 10, 1)
    assert counter.period_start("never", sunday, 0) == datetime.min


def counted_around(app, period: str, week: int = 0):
    start = counter.period_start(period, datetime.now(), week)
    counted_at(app, 5, start - timedelta(minutes=1))
    counted_at(app, 2, start)


def test_a_daily_counter_starts_from_zero_at_midnight(app, bot):
    make(app, bot, "Coffee", period="daily")
    counted_around(app, "daily")
    assert value(app) == 2
    send(app, "/counter")
    click(app, bot, "counter:one:1")
    assert "<b>2</b> today" in bot.last.text


def test_a_weekly_counter_starts_from_zero_on_the_first_day_of_the_week(app, bot):
    make(app, bot, "Runs", period="weekly")
    counted_around(app, "weekly")
    assert value(app) == 2
    send(app, "/counter")
    click(app, bot, "core:settings:counter")
    assert "First day of the week: <i>Monday</i>" in bot.last.text
    click(app, bot, "counter:set_week")
    assert labels(bot)[:2] == ["Monday", "Sunday"]
    click(app, bot, "counter:week:week:sunday")
    assert "First day of the week: <i>Sunday</i>" in bot.last.text
    app.storage.database.execute("DELETE FROM " + table(app, "changes") + ";")
    counted_around(app, "weekly", 6)
    assert value(app) == 2


def test_a_monthly_counter_starts_from_zero_on_the_first_of_the_month(app, bot):
    make(app, bot, "Books", period="monthly")
    counted_around(app, "monthly")
    assert value(app) == 2


def test_a_counter_that_never_starts_again_counts_everything(app, bot):
    make(app, bot, "Books")
    counted_around(app, "monthly")
    assert value(app) == 7


def test_past_periods_stay_in_the_history(app, bot):
    make(app, bot, "Coffee", period="daily")
    counted_around(app, "daily")
    send(app, "/counter")
    click(app, bot, "counter:history:1")
    assert "<i>2</i> entries" in bot.last.text and labels(bot)[1].endswith(" - +5")


# ----- editing a counter -----

def test_a_counter_can_be_edited(app, bot):
    make(app, bot, "Coffee ☕", goal="8", period="daily")
    make(app, bot, "Tea")
    send(app, "/counter")
    click(app, bot, "counter:one:1")
    click(app, bot, "counter:edit:1")
    assert bot.last.text == "<b>🔢 Counters &gt; ✏️ Edit:</b>\n\nName: <i>Coffee ☕</i>\nStep: <i>1</i>\n" \
                            "Goal: <i>8</i>\nReset: <i>Every day</i>"
    assert labels(bot)[:4] == ["🏷️ Name", "👣 Step", "🎯 Goal", "🔄 Reset"]
    click(app, bot, "counter:name:1")
    send(app, "tea")
    assert "You already have a counter called tea" in bot.last.text
    send(app, "coffee")
    assert "The counter has been changed ✅" in bot.last.text and "Name: <i>coffee</i>" in bot.last.text
    click(app, bot, "counter:step:1")
    send(app, "2000")
    assert "between 0.01 and 1000" in bot.last.text
    send(app, "0.25")
    click(app, bot, "counter:goal:1")
    click(app, bot, "counter:regoal:goal:-")
    assert "Goal: <i>Not set</i>" in bot.last.text
    click(app, bot, "counter:period:1")
    click(app, bot, "counter:reperiod:period:weekly")
    assert [(row['name'], row['step'], row['goal'], row['period']) for row in counters(app)][0] == \
        ("coffee", 0.25, None, "weekly")


def test_back_from_an_edit_returns_to_the_edit_screen(app, bot):
    make(app, bot, "Coffee")
    click(app, bot, "counter:edit:1")
    click(app, bot, "counter:step:1")
    click(app, bot, "core:back")
    assert bot.last.text.startswith("<b>🔢 Counters &gt; ✏️ Edit:</b>")
    click(app, bot, "core:back")
    assert "<b>Coffee</b>" in bot.last.text


def test_a_counter_is_deleted_with_its_history_once_confirmed(app, bot):
    make(app, bot, "Coffee")
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:delete:1")
    assert bot.last.text.startswith("<b>🔢 Counters &gt; 🗑️ Delete:</b>\n\nDo you really want to delete this counter")
    assert counters(app)
    click(app, bot, "counter:delete_confirmed:1")
    assert bot.last.text == "<b>🔢 Counters:</b>\n\nThe counter has been deleted ✅\n\n" \
                            "Create counters and count anything you like 😊"
    assert counters(app) == [] and changes(app) == []
    click(app, bot, "counter:one:1")
    assert "This counter is no longer there" in bot.last.text


def test_someone_else_cannot_touch_a_counter(app, bot):
    make(app, bot, "Coffee")
    click(app, bot, "counter:plus:1")
    app.router.load_user(make_message("", user_id=2).from_user)
    app.storage.database.execute("UPDATE " + table(app, "counters") + " SET user_id = 2;")
    app.storage.database.execute("UPDATE " + table(app, "changes") + " SET user_id = 2;")
    for action in ("one", "plus", "minus", "amount", "edit", "name", "step", "goal", "period", "delete",
                   "delete_confirmed", "history", "chart", "open"):
        click(app, bot, "counter:" + action + ":1")
        assert "This counter is no longer there" in bot.last.text
    for action in ("entry", "amend", "move", "erase", "erase_confirmed"):
        click(app, bot, "counter:" + action + ":1")
        assert "This entry is no longer there" in bot.last.text
    assert len(counters(app)) == 1 and amounts(app) == [1]


# ----- history -----

def test_entries_are_listed_newest_first_a_page_at_a_time(app, bot):
    make(app, bot, "Push-ups")
    for hours in range(10):
        counted_at(app, hours + 1, datetime.now() - timedelta(hours=hours + 1))
    send(app, "/counter")
    click(app, bot, "counter:one:1")
    click(app, bot, "counter:history:1")
    assert bot.last.text == "<b>🔢 Counters &gt; 📜 History:</b>\n\n<b>Push-ups</b>\nTap an entry to change or " \
                            "delete it. Page <i>1</i> of <i>2</i>, <i>10</i> entries"
    assert labels(bot)[0].endswith(" - +1") and labels(bot)[counter.page_size:][:2] == ["⬅️ Previous", "➡️ Next"]
    click(app, bot, "counter:history:1:1")
    assert "Page <i>2</i> of <i>2</i>" in bot.last.text and labels(bot)[1].endswith(" - +10")
    click(app, bot, "counter:entry:10")
    click(app, bot, "core:back")
    assert "Page <i>2</i> of <i>2</i>" in bot.last.text
    click(app, bot, "core:back")
    assert "<b>Push-ups</b>\n<b>55</b> in total" in bot.last.text


def test_an_empty_history_says_so(app, bot):
    make(app, bot, "Push-ups")
    click(app, bot, "counter:history:1")
    assert bot.last.text.endswith("Nothing has been counted yet 🤷")


def test_an_entry_can_be_changed(app, bot):
    make(app, bot, "Push-ups")
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:history:1")
    click(app, bot, "counter:entry:1")
    assert "Counter: <i>Push-ups</i>\nAmount: <i>+1</i>" in bot.last.text
    assert labels(bot)[:3] == ["✏️ Change the amount", "🕒 Change the date and time", "🗑️ Delete"]
    click(app, bot, "counter:amend:1")
    send(app, "0")
    assert "Write a number other than zero" in bot.last.text
    send(app, "-3")
    assert "The entry has been changed ✅" in bot.last.text and "Amount: <i>-3</i>" in bot.last.text
    click(app, bot, "counter:move:1")
    send(app, "soon")
    assert "Write a time that has passed" in bot.last.text
    send(app, "30.10.2026 13.15")
    assert changes(app)[0]['amount'] == -3 and changes(app)[0]['changed_at'] == "2026-10-30T13:15:00"


def test_an_entry_is_deleted_once_confirmed(app, bot):
    make(app, bot, "Push-ups")
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:history:1")
    click(app, bot, "counter:erase:2")
    assert "Do you really want to delete this entry?" in bot.last.text
    assert amounts(app) == [1, 1]
    click(app, bot, "counter:erase_confirmed:2")
    assert "The entry has been deleted ✅\n\n<b>Push-ups</b>\nTap an entry" in bot.last.text
    assert "<i>1</i> entries" in bot.last.text and amounts(app) == [1]


# ----- the chart -----

def test_a_daily_chart_tells_the_days_and_the_goal(app, bot):
    make(app, bot, "Coffee ☕", goal="8", period="daily")
    counted_at(app, 3, datetime.now() - timedelta(days=1))
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:chart:1")
    assert bot.last.photo[:8] == b"\x89PNG\r\n\x1a\n"
    assert bot.last.text == "<b>🔢 Counters &gt; 📈 Chart:</b>\n\nGoal: <i>8</i>\n" + \
        (date.today() - timedelta(days=1)).isoformat() + " - 3\n" + date.today().isoformat() + " - 2"


def test_a_weekly_and_a_monthly_chart_add_up_each_period(app, bot):
    make(app, bot, "Runs", period="weekly")
    make(app, bot, "Books", period="monthly")
    week = counter.period_start("weekly", datetime.now(), 0)
    month = counter.period_start("monthly", datetime.now(), 0)
    for counter_id in (1, 2):
        counted_at(app, 1, datetime.now(), counter_id)
        counted_at(app, 2, datetime.now(), counter_id)
    send(app, "/counter")
    click(app, bot, "counter:chart:1")
    assert bot.last.text.endswith("\n\n" + week.date().isoformat() + " - 3")
    click(app, bot, "counter:chart:2")
    assert bot.last.text.endswith("\n\n" + month.strftime("%Y-%m") + " - 3")


def test_a_chart_of_a_counter_that_never_starts_again_runs_on(app, bot):
    make(app, bot, "Books")
    counted_at(app, 10, datetime.now() - timedelta(days=60))
    counted_at(app, 2, datetime.now())
    send(app, "/counter")
    click(app, bot, "counter:chart:1")
    assert bot.last.photo is not None and bot.last.text.endswith("\n\n" + date.today().isoformat() + " - 12")


def test_the_calculator_keeps_its_messages_and_leaves_the_counters_theirs(app, bot):
    make(app, bot, "Coffee")
    make(app, bot, "km")
    for text in ("2 kg + 300 g", "5 km", "1:20 + 2:45 + 0:35"):
        send(app, text)
        assert "Calculator" in bot.last.text
    assert amounts(app) == []
    send(app, "coffee +1")
    send(app, "km +2")
    assert amounts(app) == [1, 2]


def test_a_name_with_dollars_does_not_break_the_chart(app, bot):
    make(app, bot, "Cost $x^$", period="daily")
    click(app, bot, "counter:plus:1")
    click(app, bot, "counter:chart:1")
    assert bot.last.photo is not None


def test_an_empty_chart_says_so(app, bot):
    make(app, bot, "Books", period="daily")
    counted_at(app, 10, datetime.now() - timedelta(days=60))
    send(app, "/counter")
    click(app, bot, "counter:chart:1")
    assert bot.last.photo is None and bot.last.text.endswith("Nothing has been counted in the time the chart shows 🤷")


def test_a_chart_starts_a_day_before_the_first_entry():
    now = datetime(2026, 11, 10, 14, 0)
    assert counter.starts_of("daily", now, 0, datetime(2026, 11, 8, 9, 0)) == [
        datetime(2026, 11, day) for day in (7, 8, 9, 10)]
    assert counter.starts_of("weekly", now, 0, datetime(2026, 11, 10, 9, 0)) == [datetime(2026, 11, 9)]
    assert counter.starts_of("weekly", now, 0, datetime(2026, 11, 9, 9, 0)) == [datetime(2026, 11, 2),
                                                                                datetime(2026, 11, 9)]
    assert counter.starts_of("monthly", now, 0, datetime(2026, 11, 1, 9, 0)) == [datetime(2026, 10, 1),
                                                                                 datetime(2026, 11, 1)]


def test_an_old_counter_keeps_the_chart_to_its_last_days():
    now = datetime(2026, 11, 10, 14, 0)
    assert len(counter.starts_of("daily", now, 0, datetime(2025, 1, 1))) == counter.chart_days
    assert len(counter.starts_of("monthly", now, 0, datetime(2025, 1, 1))) == counter.chart_periods


def test_a_chart_marks_the_values_worth_reading():
    assert counter.value_labels([0, 2, 0, 1.5], False) == ["", "2", "", "1.5"]
    assert counter.value_labels([0, 2, 2, 3], True) == ["0", "2", "", "3"]


def test_bars_tell_whether_each_period_reached_the_goal():
    reached, missed, running = counter.colors['reached'], counter.colors['missed'], counter.colors['count']
    assert counter.bar_colors([5, 2, 4, 1], 4) == [reached, missed, reached, running]
    assert counter.bar_colors([5, 4], 4) == [reached, reached]
    assert counter.bar_colors([5, 2], None) == [running, running]


def test_the_chart_is_a_png():
    for is_running in (True, False):
        drawn = counter.draw([(datetime(2026, 10, 31), 3.0), (datetime(2026, 11, 1), -1.0)], 8.0,
                             {'title': "Coffee", 'goal': "Goal"}, is_running, "daily")
        assert drawn[:8] == b"\x89PNG\r\n\x1a\n"


# ----- plain messages -----

def test_a_message_counts_when_it_names_a_counter(app, bot):
    make(app, bot, "Coffee ☕", goal="8", period="daily")
    make(app, bot, "Push-ups")
    make(app, bot, "Kawa")
    for text in ("coffee +1", "COFFEE ☕ +2", "+2 push-ups", "kawa -1", "kawa +0,5", "Push-ups+3"):
        send(app, text)
    assert amounts(app) == [1, 2, 2, -1, 0.5, 3]
    send(app, "coffee +1")
    assert bot.last.text == "<b>🔢 Counters:</b>\n\nCounted +1\nCoffee ☕: <i>4 / 8 today</i>\n▰▰▰▰▰▱▱▱▱▱ 50%"
    assert labels(bot) == ["↩️ Undo", "🔢 Open the counter"]


def test_a_name_with_a_hyphen_and_a_number_is_a_name(app, bot):
    make(app, bot, "Top-10")
    send(app, "top-10 +1")
    assert amounts(app) == [1] and "Top-10: <i>1 in total</i>" in bot.last.text


def test_a_message_naming_no_counter_is_left_to_others(app, bot):
    make(app, bot, "Coffee")
    for text in ("tea +1", "5 km", "2 kg + 300 g", "coffee", "coffee 1", "coffee +0", "coffee +200000", "10 + 2"):
        send(app, text)
        assert not bot.last.text.startswith("<b>🔢 Counters"), text
    assert changes(app) == []


def test_a_message_from_someone_without_access_is_left_to_others(app, bot):
    make(app, bot, "Coffee")
    app.storage.access.allow(1, "counter", False)
    send(app, "coffee +1")
    assert changes(app) == [] and not bot.last.text.startswith("<b>🔢 Counters")


def test_a_counted_message_can_be_undone(app, bot):
    make(app, bot, "Coffee", goal="2", period="daily")
    send(app, "coffee +2")
    assert "The goal has been reached 🎉" in bot.last.text
    click(app, bot, "counter:undo:1")
    assert bot.last.text == "<b>🔢 Counters:</b>\n\nTaken back +2 ✅\nCoffee: <i>0 / 2 today</i>\n▱▱▱▱▱▱▱▱▱▱ 0%"
    assert changes(app) == [] and bot.unbuttoned
    click(app, bot, "counter:undo:1")
    assert "This entry is no longer there" in bot.last.text


def test_an_old_undo_never_takes_back_a_newer_entry(app, bot):
    make(app, bot, "Coffee")
    send(app, "coffee +1")
    old = bot.last.buttons[0][1]
    click(app, bot, "counter:undo:" + str(changes(app)[-1]['id']))
    send(app, "coffee +5")
    click(app, bot, old)
    assert amounts(app) == [5] and "This entry is no longer there" in bot.last.text


def test_a_counted_message_opens_its_counter(app, bot):
    make(app, bot, "Coffee")
    send(app, "coffee +2")
    click(app, bot, "counter:open:1")
    assert "<b>Coffee</b>\n<b>2</b> in total" in bot.last.text and labels(bot)[0] == "➖ 1"


def test_a_message_on_a_screen_goes_to_the_screen(app, bot):
    make(app, bot, "Coffee")
    click(app, bot, "counter:amount:1")
    send(app, "coffee +1")
    assert "Write a number, like 5 or -2" in bot.last.text and changes(app) == []


# ----- the assistant -----

def test_the_summary_tells_the_state_of_the_counters(app, bot):
    assert counter.summary(as_user(app)) == ""
    make(app, bot, "Coffee ☕", goal="8", period="daily")
    make(app, bot, "<Books> & co")
    counted_at(app, 3, datetime.now())
    assert counter.summary(as_user(app)) == "Coffee ☕: <i>3 / 8 today</i>\n&lt;Books&gt; &amp; co: <i>0 in total</i>"


def test_the_assistant_counts_once_confirmed(app, bot):
    make(app, bot, "Coffee ☕", goal="2", period="daily")
    outcome = counter.act_add(as_user(app), "coffee", 2)
    assert outcome.status == "asking"
    assert outcome.result == "Count this?\nCounter: <i>Coffee ☕</i>\nAmount: <i>+2</i>\nAfter that: <i>2 / 2</i>"
    assert changes(app) == []
    assert outcome.then() == "Counted +2\nCoffee ☕: <i>2 / 2 today</i>\n▰▰▰▰▰▰▰▰▰▰ 100%\nThe goal has been reached 🎉"
    assert amounts(app) == [2]


def test_the_assistant_is_checked_like_the_screens(app, bot):
    make(app, bot, "Coffee")
    assert str(counter.act_add(as_user(app), "tea", 1).result).startswith("There is no counter with this name")
    assert counter.act_add(as_user(app), "coffee", 0).result == "Write a number other than zero"
    assert counter.act_add(as_user(app), "coffee", 1e6).status == "refused"
    assert counter.act_history(as_user(app), "tea").status == "refused"


def test_the_assistant_lists_the_counters_and_reads_a_history(app, bot):
    make(app, bot, "Coffee ☕", goal="8", period="daily")
    counted_at(app, 1, datetime(2026, 10, 30, 8, 0))
    counted_at(app, 2, datetime.now().replace(microsecond=0))
    assert counter.act_list(as_user(app)).result == [{'name': "Coffee ☕", 'value': 2, 'step': 1, 'goal': 8,
                                                      'starts_from_zero': "daily"}]
    found = counter.act_history(as_user(app), "COFFEE").result
    assert found['name'] == "Coffee ☕" and found['value'] == 2 and found['starts_from_zero'] == "daily"
    assert found['changes'][0] == {'when': "2026-10-30T08:00:00", 'amount': 1} and len(found['changes']) == 2


# ----- languages and data -----

def test_everything_speaks_polish(app, bot):
    app.storage.settings.set_language(1, "pl")
    send(app, "/counter")
    assert bot.last.text.startswith("<b>🔢 Liczniki:</b>\n\nZakładaj liczniki i licz, co tylko chcesz 😊")
    assert labels(bot)[:2] == ["➕ Nowy licznik", "⚙️ Ustawienia"]
    click(app, bot, "counter:new")
    send(app, "123")
    assert "Nazwa musi mieć przynajmniej jedną literę" in bot.last.text
    send(app, "Kawa ☕")
    click(app, bot, "counter:create:step:-")
    send(app, "2")
    assert labels(bot)[:4] == ["Nigdy", "Codziennie", "Co tydzień", "Co miesiąc"]
    click(app, bot, "counter:create:period:daily")
    assert "Licznik został założony ✅\n\n<b>Kawa ☕</b>\n<b>0 / 2</b> dzisiaj" in bot.last.text
    send(app, "kawa +2")
    assert "Zapisano +2\nKawa ☕: <i>2 / 2 dzisiaj</i>" in bot.last.text and "Cel został osiągnięty 🎉" in bot.last.text
    assert labels(bot) == ["↩️ Cofnij", "🔢 Otwórz licznik"]


def test_wiping_a_user_takes_their_counters_with_them(app, bot):
    make(app, bot, "Coffee")
    click(app, bot, "counter:plus:1")
    app.storage.users.delete(1)
    assert counters(app) == [] and changes(app) == []
