from datetime import datetime, timedelta

import pytest

from core.api import Ctx, Outcome
from core.testing import make_callback, make_message
from modules.external.bmi import module as bmi


@pytest.fixture
def lonely(tmp_path, request):
    (tmp_path / "modules.yaml").write_text("bodytracker: false\n", encoding='utf8')
    return request.getfixturevalue("app")


def send(app, text: str):
    app.router.handle_message(make_message(text))


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))
    app.router.wait_for_tasks()


def as_user(app) -> Ctx:
    return Ctx(app.services, app.registry.get("bmi"), app.router.load_user(make_message("").from_user))


def labels(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def track(app, weight: float = 80.0, height: float | None = 180.0, days_ago: int = 0):
    tracker = app.storage.for_module("bodytracker")
    moment = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
    app.storage.database.execute("INSERT INTO " + tracker.table("weights") +
                                 " (user_id, weight, measured_at) VALUES (1, ?, ?);", (weight, moment))
    if height is not None:
        app.storage.database.execute("INSERT INTO " + tracker.table("heights") +
                                     " (user_id, height, measured_at) VALUES (1, ?, ?);", (height, moment))


def tracked_weights(app) -> list[float]:
    return [row['weight'] for row in app.storage.database.query_all(
        "SELECT weight FROM " + app.storage.for_module("bodytracker").table("weights") + " ORDER BY id;")]


@pytest.mark.parametrize("weight, height, value", [(70, 175, 22.86), (100, 180, 30.86), (45, 170, 15.57)])
def test_the_index_is_weight_over_height_squared(weight, height, value):
    assert round(bmi.bmi(weight, height), 2) == value


@pytest.mark.parametrize("value, name", [
    (15.9, "severe_thinness"), (16.0, "underweight"), (18.4, "underweight"), (18.5, "normal"),
    (24.9, "normal"), (25.0, "overweight"), (30.0, "obesity_1"), (35.0, "obesity_2"), (40.0, "obesity_3")])
def test_the_categories_follow_the_who_limits(value, name):
    assert bmi.category(value) == name


def test_the_command_opens_a_menu_without_any_result(app, bot):
    track(app)
    send(app, "/bmi")
    assert "24.7" not in bot.last.text and "80" not in bot.last.text
    assert labels(bot) == ["🧮 Work it out", "📜 History", "📈 Chart", "✖️ Close"]
    assert bot.last.text.endswith("😊")


def test_without_the_tracker_it_is_a_plain_calculator(lonely):
    bot = lonely.services.bot
    send(lonely, "/bmi")
    assert labels(bot) == ["🧮 Work it out", "✖️ Close"]
    click(lonely, bot, "bmi:count")
    assert "Write the height" in bot.last.text
    send(lonely, "very tall")
    assert "between 50 cm and 250 cm" in bot.last.text
    send(lonely, "175")
    send(lonely, "70,5")
    assert "<i>23.0</i>" in bot.last.text and "<i>Normal weight</i>" in bot.last.text
    assert "Weight: <i>70.5 kg</i>\n" in bot.last.text and "from your saved details" not in bot.last.text
    assert labels(bot) == []


def test_saved_data_is_offered_without_showing_it(app, bot):
    track(app)
    send(app, "/bmi")
    click(app, bot, "bmi:count")
    assert "80" not in bot.last.text and labels(bot)[:2] == ["Use it", "Type everything"]
    click(app, bot, "bmi:body:offer:1")
    assert "<i>24.7</i>" in bot.last.text
    assert "Weight: <i>80.0 kg</i> (from your saved details)" in bot.last.text
    assert "Height: <i>180 cm</i> (from your saved details)" in bot.last.text
    assert labels(bot) == []


def test_a_stale_weight_is_not_offered_and_is_asked_for(app, bot):
    track(app, days_ago=31)
    send(app, "/bmi")
    click(app, bot, "bmi:count")
    click(app, bot, "bmi:body:offer:1")
    assert "Write the weight" in bot.last.text
    send(app, "82")
    assert "Height: <i>180 cm</i> (from your saved details)" in bot.last.text
    assert labels(bot) == ["💾 Save the new details about me"]
    result = bot.last.message_id
    click(app, bot, "bmi:save::82")
    assert "Saved" in bot.last.text
    assert bot.unbuttoned == [(1, result)]
    assert tracked_weights(app) == [80, 82]


def test_declined_data_is_for_someone_else_and_never_saved(app, bot):
    track(app)
    send(app, "/bmi")
    click(app, bot, "bmi:count")
    click(app, bot, "bmi:body:offer:0")
    send(app, "160")
    send(app, "50")
    assert "<i>19.5</i>" in bot.last.text and labels(bot) == []
    assert tracked_weights(app) == [80]


def test_without_access_to_the_tracker_nothing_is_offered(app, bot):
    track(app)
    app.storage.access.allow(1, "bodytracker", False)
    send(app, "/bmi")
    assert labels(bot) == ["🧮 Work it out", "✖️ Close"]
    click(app, bot, "bmi:count")
    assert "Write the height" in bot.last.text


def test_the_history_comes_from_the_tracker(app, bot):
    track(app, 90, days_ago=40)
    track(app, 81)
    send(app, "/bmi")
    click(app, bot, "bmi:history")
    assert "<i>2</i>" in bot.last.text and "<b>25.0</b>" in bot.last.text
    click(app, bot, "core:back")
    menu = bot.last.message_id
    click(app, bot, "bmi:chart")
    assert bot.last.photo[:8] == b"\x89PNG\r\n\x1a\n" and bot.deleted == [(1, menu)]
    day, before = (moment.strftime("%Y-%m-%d") for moment in (datetime.now(), datetime.now() - timedelta(days=40)))
    assert bot.last.text == "<b>🩺 BMI &gt; 📈 Chart:</b>\n\n" + before + " - 27.8\n" + day + " - 25.0"
    assert labels(bot) == ["🔙 Back", "🏠 Menu", "✖️ Close"]
    click(app, bot, "core:back")
    assert bot.last.photo is None and bot.last.text.endswith("😊")


def test_heights_and_weights_follow_the_units_of_the_user(app, bot):
    app.storage.profiles.set(1, "weight_unit", "lb")
    app.storage.profiles.set(1, "height_unit", "ftin")
    send(app, "/bmi")
    click(app, bot, "bmi:count")
    assert "Write the height (ft in)" in bot.last.text
    send(app, "5 11")
    assert "Write the weight (lb)" in bot.last.text
    send(app, "176")
    assert "<i>24.5</i>" in bot.last.text
    assert "Weight: <i>176.0 lb</i>" in bot.last.text and "Height: <i>5 ft 11 in</i>" in bot.last.text


def test_the_chart_is_a_png():
    assert bmi.draw([(datetime.now() - timedelta(days=5), 26.1), (datetime.now(), 24.8)], "BMI")[:8] == \
        b"\x89PNG\r\n\x1a\n"


def test_old_weights_use_the_height_of_their_time(app, bot):
    track(app, 72, 170, days_ago=400)
    track(app, 81, 180)
    assert [round(value, 1) for _, value in bmi.tracked_points(as_user(app))] == [24.9, 25.0]


# ----- assistant -----

def test_the_summary_gives_the_latest_index(app, bot):
    assert bmi.summary(as_user(app)) == ""
    track(app, 81)
    assert bmi.summary(as_user(app)) == "BMI: <i>25.0, Overweight (" + datetime.now().strftime("%Y-%m-%d") + ")</i>"


def test_the_assistant_counts_with_what_it_is_given_or_what_is_saved(app, bot):
    assert bmi.act_count(as_user(app), 70, None).status == "refused"
    track(app, 81)
    assert bmi.act_count(as_user(app), 70, None) == Outcome.done({'bmi': 21.6, 'category': "Normal weight",
                                                                  'weight_kg': 70, 'height_cm': 180})
    assert bmi.act_count(as_user(app), None, None).result['bmi'] == 25.0
    assert bmi.act_count(as_user(app), 70, 500).status == "refused"
