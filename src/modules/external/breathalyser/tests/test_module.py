from datetime import datetime, timedelta

import pytest

from core.api import Ctx
from core.testing import make_callback, make_message
from modules.external.breathalyser import module as breathalyser


@pytest.fixture
def lonely(tmp_path, request):
    (tmp_path / "modules.yaml").write_text("bodytracker: false\ndrinktracker: false\n", encoding='utf8')
    return request.getfixturevalue("app")


def send(app, text: str):
    app.router.handle_message(make_message(text))
    app.router.wait_for_tasks()


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))
    app.router.wait_for_tasks()


def labels(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def track(app, sex: str | None = "male", days_ago: int = 0):
    tracker = app.storage.for_module("bodytracker")
    moment = (datetime.now() - timedelta(days=days_ago)).isoformat(timespec="seconds")
    app.storage.database.execute("INSERT INTO " + tracker.table("weights") + " (user_id, weight, measured_at) "
                                 "VALUES (1, 80, ?);", (moment,))
    app.storage.database.execute("INSERT INTO " + tracker.table("heights") + " (user_id, height, measured_at) "
                                 "VALUES (1, 180, ?);", (datetime.now().isoformat(timespec="seconds"),))
    app.storage.profiles.set(1, "sex", sex)
    app.storage.profiles.set(1, "born", "1990-01-01")


def drink(app, hours_ago: float = 1.0, own_body: bool = False):
    drinks = app.storage.for_module("drinktracker")
    moment = (datetime.now() - timedelta(hours=hours_ago)).isoformat(timespec="seconds")
    app.storage.database.execute("INSERT INTO " + drinks.table("drinks") + " (user_id, kind, volume, strength, grams, "
                                 "kcal, food, drunk_at) VALUES (1, 'beer', 500, 5, 19.725, 215, 'empty', ?);",
                                 (moment,))
    if own_body:
        app.storage.profiles.set(1, "sex", "female")
        app.storage.profiles.set(1, "born", "1990-01-01")
        app.storage.database.execute("INSERT INTO " + drinks.table("sizes") + " (user_id, height, weight) "
                                     "VALUES (1, 165, 60);")


def tracked(app) -> tuple:
    tracker = app.storage.for_module("bodytracker")
    height = app.storage.database.query_one("SELECT height FROM " + tracker.table("heights") + " ORDER BY id DESC;")
    weights = app.storage.database.query_all("SELECT weight FROM " + tracker.table("weights") + ";")
    return (height['height'] if height else None, app.storage.profiles.get(1).sex), [one['weight'] for one in weights]


def answer_all(app, bot, drinks: str = "500 5 + 500 5", hours: str = "1"):
    click(app, bot, "breathalyser:estimate:sex:male")
    for text in ("30", "180", "80", drinks, hours):
        send(app, text)
    click(app, bot, "breathalyser:estimate:food:empty")


# ----- the model -----

def test_watson_and_widmark_give_the_classic_numbers():
    factor = breathalyser.per_gram(("male", 30, 180, 80))
    assert round(breathalyser.body_water("male", 30, 180, 80), 2) == 45.82
    assert 20 * factor == pytest.approx(0.349, abs=0.001)


def test_an_undisclosed_sex_counts_as_female():
    female = breathalyser.per_gram(("female", 30, 180, 80))
    assert breathalyser.per_gram(("other", 30, 180, 80)) == female
    assert breathalyser.per_gram(("undisclosed", 30, 180, 80)) == female
    assert female > breathalyser.per_gram(("male", 30, 180, 80))


def test_food_lowers_the_peak_and_speeds_up_the_clearing():
    factor = breathalyser.per_gram(("male", 30, 180, 80))
    curves = {food: breathalyser.simulate([(0, 40, food)], factor, 0.15) for food in breathalyser.foods}
    peaks = {food: breathalyser.peak(points) for food, points in curves.items()}
    assert peaks['empty'][1] > peaks['little'][1] > peaks['meal'][1]
    assert peaks['empty'][0] < peaks['little'][0] < peaks['meal'][0]
    assert curves['meal'][-1][0] < curves['empty'][-1][0]


def test_the_clearing_slows_down_near_the_end():
    factor = breathalyser.per_gram(("male", 30, 180, 80))
    points = breathalyser.simulate([(0, 60, "empty")], factor, 0.15)
    top_moment, _ = breathalyser.peak(points)
    falling = [(moment, level) for moment, level in points if moment > top_moment + 2]
    assert falling[0][1] - breathalyser.level_at(points, falling[0][0] + 1) == pytest.approx(0.15, abs=0.01)
    low = next(moment for moment, level in falling if level <= 0.1)
    assert points[-1][0] - low > 1.5 * 0.1 / 0.15


def test_the_elimination_shortens_the_curve():
    factor = breathalyser.per_gram(("male", 30, 180, 80))
    slow = breathalyser.simulate([(0, 40, "empty")], factor, 0.10)
    fast = breathalyser.simulate([(0, 40, "empty")], factor, 0.20)
    assert fast[-1][0] < slow[-1][0] and fast[-1][1] == slow[-1][1] == 0


def test_the_level_at_a_moment_is_read_from_the_curve():
    points = [(0.0, 0.0), (0.5, 0.3), (1.0, 0.25)]
    assert breathalyser.level_at(points, 0.4) == 0.3
    assert breathalyser.level_at(points, 2) == 0


@pytest.mark.parametrize("text, expected", [
    ("500 5", [19.725]),
    ("500 5 + 50 40", [19.725, 15.78]),
    ("500ml 5%; 150 12,5", [19.725, 14.79]),
    ("500 5,50 40", [19.725, 15.78]),
    ("500 5, 50 40", [19.725, 15.78]),
    ("500 5+50 40", [19.725, 15.78]),
    ("500 4,5,50 40", [17.75, 15.78]),
    ("330 5,5 330 4,5", [14.32, 11.72]),
    ("500 5 50 40", [19.725, 15.78]),
    ("500", None),
    ("500 + 5", None),
    ("5 500", None),
    ("", None),
])
def test_drinks_are_read_as_millilitres_and_percent(text, expected):
    found = breathalyser.parse_drinks(text)
    assert (found is None and expected is None) or found == pytest.approx(expected, abs=0.01)


def test_drinks_are_spread_evenly_from_the_first_to_the_last():
    assert breathalyser.spread([10, 20, 30], 3, "meal") == [(0, 10, "meal"), (1.5, 20, "meal"), (3, 30, "meal")]
    assert breathalyser.spread([10], 3, "meal") == [(0, 10, "meal")]


def test_a_timeline_keeps_the_last_known_food():
    first, found = breathalyser.timeline([("2026-10-30T20:00:00", 20, None), ("2026-10-30T21:30:00", 15, "meal"),
                                          ("2026-10-30T22:00:00", 10, None)])
    assert first == datetime(2026, 10, 30, 20) and found == [(0, 20, "little"), (1.5, 15, "meal"), (2, 10, "meal")]


def test_the_level_is_shown_in_the_blood_and_in_the_breath():
    assert breathalyser.shown_level(0.5) == "0.50‰ (0.25 mg/dm³)"


def test_drinks_far_apart_make_separate_sessions():
    drinks = [("2026-10-30T20:00:00", 20, "empty"), ("2026-10-30T21:00:00", 20, None),
              ("2026-10-31T20:00:00", 20, None), ("2026-11-02T20:00:00", 100, None), ("2026-11-02T23:00:00", 5, None)]
    assert breathalyser.split(drinks, breathalyser.per_gram(("male", 30, 180, 80)), 0.15) == [[0, 1], [2], [3, 4]]


def test_a_drink_after_sobering_up_starts_a_new_session():
    factor = breathalyser.per_gram(("male", 30, 180, 80))
    sober = breathalyser.simulate([(0, 20, "empty")], factor, 0.15)[-1][0]
    first = datetime(2026, 10, 30, 20)
    drinks = [(first.isoformat(), 20, "empty"), ((first + timedelta(hours=sober - 0.1)).isoformat(), 20, None),
              ((first + timedelta(hours=sober + 5)).isoformat(), 20, None)]
    assert breathalyser.split(drinks, factor, 0.15) == [[0, 1], [2]]


# ----- estimating -----

def test_the_command_shows_no_data_and_warns(app, bot):
    track(app)
    send(app, "/breathalyser")
    assert "180" not in bot.last.text and "never tells you whether you can drive" in bot.last.text
    assert labels(bot)[0] == "🧮 Estimate"


def test_entering_by_hand_asks_again_until_it_makes_sense(lonely):
    bot = lonely.services.bot
    send(lonely, "/breathalyser")
    click(lonely, bot, "breathalyser:count")
    send(lonely, "male")
    assert "Pick one of the buttons" in bot.last.text
    click(lonely, bot, "breathalyser:estimate:sex:other")
    send(lonely, "15")
    assert "between 18 and 120" in bot.last.text
    for text in ("30", "170", "65"):
        send(lonely, text)
    send(lonely, "two beers")
    assert "millilitres and percent, at most 30 drinks" in bot.last.text
    send(lonely, "500 5 + 500 5")
    send(lonely, "100")
    assert "between 0 and 48" in bot.last.text
    send(lonely, "1,5")
    assert "How many hours ago was the last drink?" in bot.last.text
    send(lonely, "2")
    assert "from 0 to 1.5" in bot.last.text
    send(lonely, "0")
    click(lonely, bot, "breathalyser:estimate:food:little")
    assert bot.files == [] and bot.last.photo[:8] == b"\x89PNG\r\n\x1a\n"
    text = bot.last.text
    assert "Estimate now" in text and "Sex: <i>Other</i>\n" in text and "Pure alcohol: <i>39.5 g</i>\n" in text
    first, last = (datetime.now() - timedelta(hours=hours) for hours in (1.5, 0))
    assert "First drink: <i>" + first.strftime("%Y-%m-%d %H:%M") in text
    assert "Last drink: <i>" + last.strftime("%Y-%m-%d %H:%M") in text
    assert "mg/dm³)</i>" in text and "<b>0.50‰ (0.25 mg/dm³)</b>" in text
    assert "state of insobriety." in text and "in the breath" not in text
    assert "never tells you whether you can drive" in text and "Peak: " in text and " - 0.00‰" not in text
    assert labels(bot) == ["💾 Save the new details about me"]


def test_one_drink_has_no_last_one_to_ask_about(lonely):
    bot = lonely.services.bot
    send(lonely, "/breathalyser")
    click(lonely, bot, "breathalyser:count")
    click(lonely, bot, "breathalyser:estimate:sex:male")
    for text in ("30", "180", "80", "500 5", "1"):
        send(lonely, text)
    assert "How much had been eaten" in bot.last.text
    click(lonely, bot, "breathalyser:estimate:food:meal")
    assert "Last drink" not in bot.last.text and bot.last.photo is not None


def test_the_body_and_the_drinks_are_offered_apart(app, bot):
    track(app)
    drink(app)
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:count")
    assert "details about yourself" in bot.last.text and "80" not in bot.last.text
    assert labels(bot)[:2] == ["Use it", "Type everything"]
    click(app, bot, "breathalyser:estimate:offer:1")
    assert "drinks from your current session" in bot.last.text and "19.7" not in bot.last.text
    click(app, bot, "breathalyser:estimate:offer:1")
    text = bot.last.text
    assert "Weight: <i>80.0 kg</i> (from your saved details)" in text
    assert "Pure alcohol: <i>19.7 g</i> (from the drink tracker)" in text and "<i>Empty stomach</i>" in text
    assert labels(bot) == []


def test_the_body_tracker_leaves_the_drinks_to_ask_and_offers_saving(app, bot):
    track(app, sex=None)
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:count")
    click(app, bot, "breathalyser:estimate:offer:1")
    assert "Pick the sex" in bot.last.text
    click(app, bot, "breathalyser:estimate:sex:female")
    send(app, "500 5")
    send(app, "1")
    click(app, bot, "breathalyser:estimate:food:meal")
    assert "Sex: <i>Female</i>\n" in bot.last.text
    assert labels(bot) == ["💾 Save the new details about me"]
    result = bot.last.message_id
    click(app, bot, "breathalyser:save:female:::")
    assert "Saved ✅" in bot.last.text
    assert bot.unbuttoned == [(1, result)]
    assert tracked(app)[0] == (180, "female")


def test_my_body_with_other_drinks(app, bot):
    track(app)
    drink(app)
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:count")
    click(app, bot, "breathalyser:estimate:offer:1")
    click(app, bot, "breathalyser:estimate:offer:0")
    assert "Write what was drunk" in bot.last.text
    send(app, "500 5 + 500 5 + 500 5")
    send(app, "2")
    send(app, "1")
    click(app, bot, "breathalyser:estimate:food:little")
    text = bot.last.text
    assert "Weight: <i>80.0 kg</i> (from your saved details)" in text and "Pure alcohol: <i>59.2 g</i>\n" in text
    assert labels(bot) == []


def test_without_the_body_tracker_the_profile_and_the_session_are_offered(app, bot):
    drink(app, own_body=True)
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:count")
    click(app, bot, "breathalyser:estimate:offer:1")
    assert "drinks from your current session" in bot.last.text
    click(app, bot, "breathalyser:estimate:offer:1")
    assert "Write the height (cm)" in bot.last.text


def test_someone_else_is_typed_in_full_and_never_saved(app, bot):
    track(app)
    drink(app)
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:count")
    click(app, bot, "breathalyser:estimate:offer:0")
    click(app, bot, "breathalyser:estimate:offer:0")
    answer_all(app, bot)
    assert "from the" not in bot.last.text and labels(bot) == []
    assert tracked(app) == ((180, "male"), [80])


def test_a_stale_weight_and_no_access_offer_nothing(app, bot):
    track(app, days_ago=40)
    app.storage.access.allow(1, "bodytracker", False)
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:count")
    click(app, bot, "breathalyser:estimate:offer:1")
    assert "Write the height (cm)" in bot.last.text
    app.storage.profiles.set(1, "sex", None)
    app.storage.profiles.set(1, "born", None)
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:count")
    assert "Pick the sex" in bot.last.text


def test_the_body_follows_the_units_of_the_user(app, bot):
    track(app)
    app.storage.profiles.set(1, "weight_unit", "lb")
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:count")
    click(app, bot, "breathalyser:estimate:offer:1")
    send(app, "500 5")
    send(app, "1")
    click(app, bot, "breathalyser:estimate:food:little")
    assert "Weight: <i>176.4 lb</i> (from your saved details)" in bot.last.text


def test_the_curve_takes_the_color_of_each_state():
    assert breathalyser.color_of(0.1) == breathalyser.colors['sober']
    assert breathalyser.color_of(0.3) == breathalyser.colors['after_use']
    assert breathalyser.color_of(0.5) == breathalyser.colors['insobriety']
    runs = breathalyser.colored_runs([(0, 0.0), (1, 0.8)], [0.2, 0.5], breathalyser.color_of)
    assert [color for _, _, color in runs] == [breathalyser.colors[key] for key in ("sober", "after_use", "insobriety")]


def test_the_curve_is_a_png():
    start = datetime.now() - timedelta(hours=1)
    points = breathalyser.simulate([(0, 40, "meal")], breathalyser.per_gram(("female", 30, 165, 60)), 0.15)
    drawn = breathalyser.draw([(start + timedelta(hours=moment), level) for moment, level in points], datetime.now(),
                              {key: key for key in ("title", "now", "after_use", "insobriety", "sober")})
    assert drawn[:8] == b"\x89PNG\r\n\x1a\n"


def test_the_clearing_rate_is_a_setting(app, bot):
    send(app, "/breathalyser")
    click(app, bot, "breathalyser:rates")
    assert "Most people are between 0.10 and 0.20" in bot.last.text
    click(app, bot, "breathalyser:elimination:0.12")
    assert "<i>0.12‰ an hour</i>" in bot.last.text and "‰/h" not in bot.last.text
    assert app.storage.module_state.get(1, "breathalyser", "elimination") == "0.12"


# ----- assistant -----

def as_user(app) -> Ctx:
    return Ctx(app.services, app.registry.get("breathalyser"), app.router.load_user(make_message("").from_user))


def test_the_assistant_estimates_with_the_saved_body(app, bot):
    track(app)
    found = breathalyser.act_estimate(as_user(app), "500 5 + 500 5", 1, None, "empty", None, None, None, None).result
    assert isinstance(found, dict)
    assert 0.15 < found['now_promille'] < 0.6 and found['peak_promille'] >= found['now_promille']
    assert found['sober_at'] > datetime.now().strftime("%Y-%m-%d %H:%M")
    assert found['now_breath_mg_per_dm3'] == pytest.approx(found['now_promille'] / 2, abs=0.01)
    assert "This is only an estimate" in found['warning']


def test_the_assistant_is_checked_like_the_screens(app, bot):
    missing = breathalyser.act_estimate(as_user(app), "500 5", 1, None, "empty", None, None, None, None)
    assert str(missing.result).startswith("Some details are missing")
    unread = breathalyser.act_estimate(as_user(app), "lots", 1, None, "empty", "male", 30, 180, 80)
    assert str(unread.result).startswith("Write each drink")
    assert breathalyser.act_estimate(as_user(app), "500 5", 1, None, "pizza", "male", 30, 180, 80).status == "refused"
    assert breathalyser.act_estimate(as_user(app), "500 5", 1, None, "meal", "male", 12, 180, 80).status == "refused"
    assert breathalyser.act_estimate(as_user(app), "500 5", 1, 2, "meal", "male", 30, 180, 80).status == "refused"


def test_the_assistant_spreads_the_drinks_up_to_the_last_one(app, bot):
    track(app)
    later = breathalyser.act_estimate(as_user(app), "500 5 + 500 5", 3, 2, "empty", None, None, None, None).result
    now = breathalyser.act_estimate(as_user(app), "500 5 + 500 5", 3, 0, "empty", None, None, None, None).result
    assert later['peak_at'] < now['peak_at']
