from datetime import date, datetime, timedelta

import pytest

from core.api import Ctx, Outcome, Profile, plain, years_before
from core.testing import make_callback, make_message
from modules.external.bodytracker import module as bodytracker


def send(app, text: str):
    app.router.handle_message(make_message(text))


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))
    app.router.wait_for_tasks()


def labels_of(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def table_of(app, name: str) -> str:
    return app.storage.for_module("bodytracker").table(name)


def weights(app):
    return app.storage.database.query_all("SELECT * FROM " + table_of(app, "weights") + " ORDER BY id;")


def heights(app):
    return app.storage.database.query_all("SELECT * FROM " + table_of(app, "heights") + " ORDER BY id;")


def log_weight(app, bot, text: str, when: str = "0"):
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:log")
    send(app, text)
    if "When was it?" in bot.last.text:
        click(app, bot, "bodytracker:weight:when:" + when)


def set_height(app, bot, text: str):
    send(app, "/bodytracker")
    click(app, bot, "core:settings:bodytracker")
    click(app, bot, "bodytracker:set_height")
    send(app, text)
    click(app, bot, "bodytracker:height:when:0")


def measure(app, table: str, column: str, value: float, when: str):
    app.storage.database.execute("INSERT INTO " + table_of(app, table) + " (user_id, " + column + ", measured_at) "
                                 "VALUES (1, ?, ?);", (value, when))


def as_user(app) -> Ctx:
    return Ctx(app.services, app.registry.get("bodytracker"), app.router.load_user(make_message("").from_user),
               is_pressed=True)


def exposed(app, name: str, *arguments):
    return app.registry.get("bodytracker").exposed[name].handler(as_user(app), *arguments)


def test_the_command_opens_a_menu_without_any_data(app, bot):
    log_weight(app, bot, "80")
    send(app, "/bodytracker")
    assert "80" not in bot.last.text
    assert labels_of(bot)[:4] == ["➕ Log the weight", "📜 History", "📈 Chart", "⚙️ Settings"]
    assert bot.last.text.endswith("💪")


def test_a_weight_is_stored_in_kilograms(app, bot):
    log_weight(app, bot, "72,5")
    assert [row['weight'] for row in weights(app)] == [72.5]
    assert "72.5 kg" in bot.last.text


def test_a_wrong_weight_is_asked_again(app, bot):
    log_weight(app, bot, "heavy")
    assert "Write a weight between 20 kg and 400 kg" in bot.last.text
    send(app, "1000")
    assert "Write a weight between" in bot.last.text
    send(app, "80")
    click(app, bot, "bodytracker:weight:when:0")
    assert [row['weight'] for row in weights(app)] == [80]


def test_pounds_are_turned_into_kilograms(app, bot):
    app.storage.profiles.set(1, "weight_unit", "lb")
    log_weight(app, bot, "165")
    assert weights(app)[0]['weight'] == 74.84
    assert "165.0 lb" in bot.last.text


def test_a_weight_can_be_logged_afterwards(app, bot):
    log_weight(app, bot, "80", "120")
    measured = datetime.fromisoformat(weights(app)[0]['measured_at'])
    assert timedelta(minutes=119) < datetime.now() - measured < timedelta(minutes=121)
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:log")
    send(app, "79")
    send(app, (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"))
    assert "a time that has passed" in bot.last.text
    send(app, "05.01.2025 7.30")
    assert weights(app)[-1]['measured_at'] == "2025-01-05T07:30:00"


# ----- entries -----

def test_the_history_is_a_list_of_entries_newest_first(app, bot):
    for days in range(10):
        measure(app, "weights", "weight", 80 + days, (datetime.now() - timedelta(days=days)).isoformat())
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:history")
    assert "Page <i>1</i> of <i>2</i>, <i>10</i> entries" in bot.last.text
    assert labels_of(bot)[0].endswith(" - 80.0 kg")
    assert labels_of(bot)[bodytracker.page_size:][:3] == ["⬅️ Previous", "➡️ Next", "🔙 Back"]
    click(app, bot, "bodytracker:weights:1")
    assert "Page <i>2</i> of <i>2</i>" in bot.last.text and labels_of(bot)[1].endswith(" - 89.0 kg")


def test_an_entry_can_be_changed_and_moved(app, bot):
    log_weight(app, bot, "80")
    entry = str(weights(app)[0]['id'])
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:history")
    click(app, bot, "bodytracker:weight_entry:" + entry)
    assert labels_of(bot)[:3] == ["✏️ Change the value", "🕒 Change the date and time", "🗑️ Delete"]
    click(app, bot, "bodytracker:edit:weight:" + entry)
    send(app, "81,5")
    assert "The entry has been changed" in bot.last.text and "<i>81.5 kg</i>" in bot.last.text
    click(app, bot, "bodytracker:move:weight:" + entry)
    send(app, "2026-10-01 07:00")
    assert [(row['weight'], row['measured_at']) for row in weights(app)] == [(81.5, "2026-10-01T07:00:00")]


def test_an_entry_is_deleted_after_asking(app, bot):
    log_weight(app, bot, "80")
    log_weight(app, bot, "81")
    last = str(weights(app)[-1]['id'])
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:history")
    click(app, bot, "bodytracker:remove:weight:" + last)
    assert "Do you really want to delete this entry?" in bot.last.text and "81.0 kg" in bot.last.text
    assert len(weights(app)) == 2
    click(app, bot, "bodytracker:remove_confirmed:weight:" + last)
    assert "has been deleted" in bot.last.text and "<i>1</i> entries" in bot.last.text
    assert [row['weight'] for row in weights(app)] == [80]
    click(app, bot, "bodytracker:remove_confirmed:weight:" + last)
    assert "no longer there" in bot.last.text


def test_someone_else_cannot_touch_an_entry(app, bot):
    log_weight(app, bot, "80")
    entry = str(weights(app)[0]['id'])
    app.router.load_user(make_message("", user_id=2).from_user)
    app.storage.database.execute("UPDATE " + table_of(app, "weights") + " SET user_id = 2;")
    for action in ("weight_entry:", "edit:weight:", "move:weight:", "remove:weight:", "remove_confirmed:weight:"):
        click(app, bot, "bodytracker:" + action + entry)
        assert "This entry is no longer there" in bot.last.text
    click(app, bot, "bodytracker:edit:shoe:" + entry)
    assert "This entry is no longer there" in bot.last.text
    assert len(weights(app)) == 1


def test_an_empty_history_says_so(app, bot):
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:history")
    assert "No weight has been logged yet" in bot.last.text


# ----- the chart -----

def test_the_chart_is_sent_with_the_numbers(app, bot):
    measure(app, "weights", "weight", 80, "2026-10-01T08:00:00")
    measure(app, "weights", "weight", 79.2, "2026-10-29T08:00:00")
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:chart")
    assert bot.last.photo[:8] == b"\x89PNG\r\n\x1a\n" and bot.files == []
    assert bot.last.text == "<b>⚖️ Body tracker &gt; 📈 Chart:</b>\n\n2026-10-01 - 80.0 kg\n2026-10-29 - 79.2 kg"


def test_a_long_chart_keeps_the_first_and_the_latest_numbers(app, bot):
    for day in range(200):
        measure(app, "weights", "weight", 80, (datetime(2026, 1, 1) + timedelta(days=day)).isoformat())
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:chart")
    lines = bot.last.text.split("\n")
    assert len(plain(bot.last.text)) <= 1024 and lines[2] == "2026-01-01 - 80.0 kg" and lines[3] == "…"
    assert lines[-1] == "2026-07-19 - 80.0 kg"


def test_without_weights_the_chart_says_so(app, bot):
    send(app, "/bodytracker")
    click(app, bot, "bodytracker:chart")
    assert bot.last.photo is None and "No weight has been logged yet" in bot.last.text


def test_the_chart_is_a_png():
    now = datetime.now()
    assert bodytracker.draw([(now - timedelta(days=3), 80.0), (now, 79.2)], "Weight", "kg")[:8] == \
        b"\x89PNG\r\n\x1a\n"


# ----- settings -----

def test_the_height_is_in_the_settings(app, bot):
    send(app, "/bodytracker")
    click(app, bot, "core:settings:bodytracker")
    assert bot.last.text.startswith("<b>⚙️ Settings &gt; 🧩 Modules &gt; ⚖️ Body tracker:</b>")
    assert "Settings &gt; About me" in bot.last.text and "Height: <i>not given</i>" in bot.last.text
    assert labels_of(bot)[0] == "📏 Log the height" and "📜 Height history" not in labels_of(bot)
    click(app, bot, "bodytracker:set_height")
    send(app, "300")
    assert "Write a height between 50 cm and 250 cm" in bot.last.text
    send(app, "176")
    click(app, bot, "bodytracker:height:when:0")
    assert "The height has been logged ✅" in bot.last.text and "Height: <i>176 cm</i>" in bot.last.text
    assert app.storage.profiles.get(1) == Profile()


def test_a_height_in_feet_and_inches(app, bot):
    app.storage.profiles.set(1, "height_unit", "ftin")
    send(app, "/bodytracker")
    click(app, bot, "core:settings:bodytracker")
    click(app, bot, "bodytracker:set_height")
    assert "Write your height (ft in)" in bot.last.text
    send(app, "5 13")
    assert "Write a height between 1 ft 8 in and 8 ft 2 in" in bot.last.text
    send(app, "5'9\"")
    click(app, bot, "bodytracker:height:when:0")
    assert "<i>5 ft 9 in</i>" in bot.last.text
    assert heights(app)[0]['height'] == 175.26


def test_every_new_height_is_kept_with_its_date(app, bot):
    set_height(app, bot, "180")
    set_height(app, bot, "181")
    assert [row['height'] for row in heights(app)] == [180, 181]
    assert "<i>181 cm</i>" in bot.last.text and "📜 Height history" in labels_of(bot)
    assert exposed(app, "latest")['height'] == 181
    assert [height for _, height in exposed(app, "heights")] == [180, 181]
    click(app, bot, "bodytracker:heights")
    assert labels_of(bot)[0].endswith(" - 181 cm")


def test_back_from_the_settings_returns_where_they_were_opened(app, bot):
    send(app, "/bodytracker")
    click(app, bot, "core:settings:bodytracker")
    click(app, bot, "core:back")
    assert bot.last.text.startswith("<b>⚖️ Body tracker:</b>")
    click(app, bot, "core:settings:bodytracker")
    click(app, bot, "bodytracker:set_height")
    click(app, bot, "core:home")
    assert bot.last.text.startswith("<b>⚖️ Body tracker:</b>")
    send(app, "/settings")
    click(app, bot, "settings:modules")
    click(app, bot, "core:settings:bodytracker")
    click(app, bot, "core:back")
    assert bot.last.text.startswith("<b>⚙️ Settings &gt; 🧩 Modules:</b>")


def test_a_height_is_moved_under_the_height_history(app, bot):
    set_height(app, bot, "180")
    entry = str(heights(app)[0]['id'])
    click(app, bot, "bodytracker:heights")
    click(app, bot, "bodytracker:height_entry:" + entry)
    click(app, bot, "bodytracker:move:height:" + entry)
    assert bot.last.text.startswith("<b>⚙️ Settings &gt; 🧩 Modules &gt; ⚖️ Body tracker &gt; 📜 Height history &gt; ")
    send(app, "2026-01-02 08:00")
    assert heights(app)[0]['measured_at'] == "2026-01-02T08:00:00"
    click(app, bot, "core:back")
    assert labels_of(bot)[0].startswith("2026-01-02 08:00 - ")


# ----- what the other modules read -----

def test_only_a_fresh_weight_is_shared(app, bot):
    log_weight(app, bot, "80")
    assert exposed(app, "latest") == {'weight': 80, 'height': None}
    stale = (datetime.now() - timedelta(days=bodytracker.fresh_days + 1)).isoformat(timespec="seconds")
    app.storage.database.execute("UPDATE " + table_of(app, "weights") + " SET measured_at = ?;", (stale,))
    assert exposed(app, "latest")['weight'] is None
    assert exposed(app, "weights") == [(stale, 80)]


def test_other_modules_save_only_what_makes_sense(app, bot):
    assert exposed(app, "save", {'weight': 80.0, 'height': 180.0, 'sex': "male"}) == ["weight", "height"]
    assert exposed(app, "save", {'weight': 80.0, 'height': 900.0}) == ["weight"]
    assert [row['weight'] for row in weights(app)] == [80]
    assert exposed(app, "latest") == {'weight': 80, 'height': 180}
    assert app.storage.profiles.get(1).sex is None


def test_other_modules_do_not_repeat_the_same_height(app, bot):
    set_height(app, bot, "180")
    exposed(app, "save", {'height': 180.0})
    assert len(heights(app)) == 1


def test_saving_needs_a_pressed_button(app, bot):
    ctx = Ctx(app.services, app.registry.get("bmi"), app.router.load_user(make_message("").from_user))
    with pytest.raises(PermissionError):
        ctx.ask("bodytracker", "save", {'weight': 80.0})
    assert weights(app) == []


def test_wiping_a_user_takes_their_body_data_with_them(app, bot):
    log_weight(app, bot, "80")
    exposed(app, "save", {'height': 180.0})
    app.storage.users.delete(1)
    assert weights(app) == [] and heights(app) == []


# ----- assistant -----

def test_the_summary_tells_how_the_body_changed(app, bot):
    assert bodytracker.summary(as_user(app)) == ""
    measure(app, "heights", "height", 180, "2025-10-30T08:00:00")
    measure(app, "heights", "height", 181, "2026-10-30T08:00:00")
    measure(app, "weights", "weight", 85, "2025-01-01T08:00:00")
    measure(app, "weights", "weight", 82, "2026-09-01T08:00:00")
    measure(app, "weights", "weight", 80.5, "2026-10-29T08:00:00")
    app.storage.profiles.set(1, "sex", "female")
    app.storage.profiles.set(1, "born", years_before(date.today(), 30).isoformat())
    assert bodytracker.summary(as_user(app)) == "\n".join([
        "Weight: <i>80.5 kg (2026-10-29)</i>, before that 82.0 kg (2026-09-01), first measured 85.0 kg (2025-01-01)",
        "Height: <i>181 cm (2026-10-30)</i>, before that 180 cm (2025-10-30)",
        "Sex: <i>Female</i>", "Age: <i>30</i>"])


def test_the_summary_follows_the_units(app, bot):
    app.storage.profiles.set(1, "weight_unit", "lb")
    measure(app, "weights", "weight", 80, "2026-10-29T08:00:00")
    assert bodytracker.summary(as_user(app)) == "Weight: <i>176.4 lb (2026-10-29)</i>"


def test_the_assistant_logs_a_weight_once_confirmed(app, bot):
    outcome = bodytracker.act_log_weight(as_user(app), 80.5, "29.10.2026 8:00")
    assert outcome.status == "asking"
    assert outcome.result == "Log this weight?\nWeight: <i>80.5 kg</i>\nWhen: <i>2026-10-29 08:00</i>"
    assert weights(app) == []
    assert outcome.then().startswith("The weight has been logged ✅\nWeight:")
    assert [(row['weight'], row['measured_at']) for row in weights(app)] == [(80.5, "2026-10-29T08:00:00")]


def test_the_assistant_logs_a_height_for_now(app, bot):
    outcome = bodytracker.act_log_height(as_user(app), 181, None)
    assert str(outcome.result).startswith("Log this height?\nHeight: <i>181 cm</i>")
    outcome.then()
    measured = datetime.fromisoformat(heights(app)[0]['measured_at'])
    assert datetime.now() - measured < timedelta(minutes=1)


@pytest.mark.parametrize("weight, when, problem", [
    (10, None, "The weight has to be a number between 20 and 400 kg"),
    (80, "tomorrow", "Write a time that has passed"),
    (80, (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"), "Write a time that has passed"),
])
def test_the_assistant_is_checked_like_the_screens(app, bot, weight, when, problem):
    outcome = bodytracker.act_log_weight(as_user(app), weight, when)
    assert outcome.status == "refused" and str(outcome.result).startswith(problem)
    assert bodytracker.act_log_height(as_user(app), 300, None).status == "refused"


def test_the_assistant_reads_the_whole_history(app, bot):
    measure(app, "weights", "weight", 80, "2026-10-29T08:00:00")
    measure(app, "heights", "height", 181, "2026-10-30T08:00:00")
    assert bodytracker.act_history(as_user(app)) == Outcome.done({
        'weights_kg': [{'when': "2026-10-29T08:00:00", 'weight': 80}],
        'heights_cm': [{'when': "2026-10-30T08:00:00", 'height': 181}]})
