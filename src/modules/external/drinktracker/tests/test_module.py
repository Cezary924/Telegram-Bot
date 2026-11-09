from datetime import date, datetime, timedelta

import pytest

from core.api import Ctx, years_before
from core.testing import make_callback, make_message
from modules.external.drinktracker import module as drinktracker


@pytest.fixture
def lonely(tmp_path, request):
    (tmp_path / "modules.yaml").write_text("bodytracker: false\n", encoding='utf8')
    return request.getfixturevalue("app")


@pytest.fixture
def plain(tmp_path, request):
    (tmp_path / "modules.yaml").write_text("breathalyser: false\n", encoding='utf8')
    return request.getfixturevalue("app")


def send(app, text: str):
    app.router.handle_message(make_message(text))
    app.router.wait_for_tasks()


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))
    app.router.wait_for_tasks()


def labels(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def drinks(app):
    return app.storage.database.query_all("SELECT * FROM " + app.storage.for_module("drinktracker").table("drinks") +
                                          " ORDER BY drunk_at;")


def describe(app, sex: str | None = "male", age: int | None = 30):
    app.storage.profiles.set(1, "sex", sex)
    app.storage.profiles.set(1, "born", years_before(date.today(), age).isoformat() if age else None)


def track(app, sex: str = "male"):
    tracker = app.storage.for_module("bodytracker")
    app.storage.database.execute("INSERT INTO " + tracker.table("weights") + " (user_id, weight, measured_at) "
                                 "VALUES (1, 80, ?);", (datetime.now().isoformat(timespec="seconds"),))
    app.storage.database.execute("INSERT INTO " + tracker.table("heights") + " (user_id, height, measured_at) "
                                 "VALUES (1, 180, ?);", (datetime.now().isoformat(timespec="seconds"),))
    describe(app, sex)


def hours_ago(hours: float) -> str:
    return (datetime.now() - timedelta(hours=hours)).strftime("%H:%M")


def ago(hours: float) -> str:
    return (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")


def add(app, bot, kind: str = "beer", when: str = "0", food: str | None = "little"):
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:add")
    click(app, bot, "drinktracker:kind:" + kind)
    if when.isdigit():
        click(app, bot, "drinktracker:drink:when:" + when)
    else:
        send(app, when)
    if food is not None:
        assert "starts a new session" in bot.last.text
        click(app, bot, "drinktracker:food:food:" + food)


def pour(app, hours: float, food: str | None = "empty"):
    moment = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")
    app.storage.database.execute("INSERT INTO " + app.storage.for_module("drinktracker").table("drinks") +
                                 " (user_id, kind, volume, strength, grams, kcal, food, drunk_at) "
                                 "VALUES (1, 'beer', 500, 5, 19.725, 215, ?, ?);", (food, moment))


def as_user(app) -> Ctx:
    return Ctx(app.services, app.registry.get("drinktracker"), app.router.load_user(make_message("").from_user))


def exposed(app, name: str, *arguments):
    return app.registry.get("drinktracker").exposed[name].handler(as_user(app), *arguments)


def open_session(app, bot):
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:sessions")
    click(app, bot, "drinktracker:session:" + str(drinks(app)[0]['id']))


def test_deleting_the_last_drink_stays_in_the_history(app, bot):
    track(app)
    add(app, bot)
    drink = str(drinks(app)[0]['id'])
    click(app, bot, "drinktracker:delete_confirmed:" + drink)
    assert bot.last.text.startswith("<b>🍺 Drink tracker &gt; 📜 History:</b>\n\nThe drink has been deleted ✅")
    assert [data for _, data in bot.last.buttons] == ["core:back", "core:home", "core:close"]


def test_pure_alcohol_and_energy_of_a_drink():
    assert round(drinktracker.grams_of(500, 5), 3) == 19.725
    assert drinktracker.kcal_of("beer", 500, 19.725) == 215
    assert round(drinktracker.kcal_of("custom", 100, 10), 1) == 70


def test_without_the_breathalyser_a_long_break_ends_a_session():
    rows = [{'drunk_at': moment} for moment in ("2026-10-30T20:00:00", "2026-10-31T03:59:00", "2026-10-31T12:00:00")]
    assert [len(group) for group in drinktracker.by_gaps(rows)] == [2, 1]


# ----- logging -----

def test_the_command_opens_a_menu_without_any_data(app, bot):
    send(app, "/drinktracker")
    assert labels(bot)[:5] == ["➕ Add a drink", "📜 History", "📈 Chart", "⚙️ Settings", "✖️ Close"]
    assert bot.last.text.endswith("Log your drinks and keep track of how much you drink 😊")


def test_the_first_drink_asks_for_the_body_once_when_there_is_no_tracker(lonely):
    bot = lonely.services.bot
    send(lonely, "/drinktracker")
    click(lonely, bot, "drinktracker:add")
    click(lonely, bot, "drinktracker:kind:beer")
    assert "When was it?" in bot.last.text and labels(bot)[:4] == ["Now", "30 min ago", "1 h ago", "2 h ago"]
    click(lonely, bot, "drinktracker:drink:when:30")
    assert "Pick your sex" in bot.last.text and "Settings" not in bot.last.text
    click(lonely, bot, "drinktracker:drink_body:sex:male")
    for text in ("30", "180", "80"):
        send(lonely, text)
    click(lonely, bot, "drinktracker:food:food:empty")
    assert "Drinks this session: <i>1</i>" in bot.last.text and "19.7 g" in bot.last.text
    add(lonely, bot, food=None)
    assert "Drinks this session: <i>2</i>" in bot.last.text
    assert [one['food'] for one in drinks(lonely)] == ["empty", None]
    assert lonely.storage.profiles.get(1).sex == "male" and lonely.storage.profiles.get(1).age == 30


def test_the_profile_is_never_asked_again(lonely):
    bot = lonely.services.bot
    describe(lonely, "female", 40)
    send(lonely, "/drinktracker")
    click(lonely, bot, "drinktracker:add")
    click(lonely, bot, "drinktracker:kind:beer")
    click(lonely, bot, "drinktracker:drink:when:0")
    assert "Write your height (cm)" in bot.last.text


def test_with_the_tracker_the_body_is_not_asked(app, bot):
    track(app)
    add(app, bot, food="meal")
    assert "215 kcal" in bot.last.text


def test_the_tracker_is_offered_when_the_profile_lacks_something(app, bot):
    track(app)
    describe(app, "male", None)
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:add")
    click(app, bot, "drinktracker:kind:beer")
    assert bot.last.text.startswith("<b>🍺 Drink tracker &gt; ➕ Add a drink:</b>")
    click(app, bot, "drinktracker:drink:when:0")
    assert labels(bot)[:2] == ["Use it", "Type everything"] and "180" not in bot.last.text
    click(app, bot, "drinktracker:drink_body:offer:1")
    assert "Write your age" in bot.last.text
    send(app, "30")
    assert "starts a new session" in bot.last.text


def test_an_own_drink_is_asked_for_until_it_makes_sense(app, bot):
    track(app)
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:add")
    click(app, bot, "drinktracker:kind:custom")
    send(app, "a lot")
    assert "between 10 and 2000" in bot.last.text
    send(app, "330")
    send(app, "120%")
    assert "between 0.5 and 96" in bot.last.text
    send(app, "12,5%")
    send(app, "tomorrow")
    assert "a time that has passed" in bot.last.text
    send(app, hours_ago(1).replace(":", "."))
    click(app, bot, "drinktracker:food:food:meal")
    drink = drinks(app)[0]
    assert (drink['kind'], drink['volume'], drink['strength'], drink['food']) == ("custom", 330, 12.5, "meal")
    assert drink['kcal'] == pytest.approx(drink['grams'] * 7)


def test_a_late_drink_between_two_sessions_joins_them(app, bot):
    track(app)
    add(app, bot, when=hours_ago(4))
    add(app, bot, food="empty")
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:sessions")
    assert "<i>2</i> sessions" in bot.last.text
    add(app, bot, when=hours_ago(2), food=None)
    assert "Drinks this session: <i>3</i>" in bot.last.text
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:sessions")
    assert "<i>1</i> sessions" in bot.last.text


def test_without_the_breathalyser_the_body_is_never_needed(plain):
    bot = plain.services.bot
    add(plain, bot, when=hours_ago(10))
    add(plain, bot, when=hours_ago(5), food=None)
    add(plain, bot, food=None)
    send(plain, "/drinktracker")
    click(plain, bot, "drinktracker:sessions")
    assert "<i>1</i> sessions" in bot.last.text
    click(plain, bot, "drinktracker:session:" + str(drinks(plain)[0]['id']))
    assert "Pure alcohol: <i>59.2 g</i>" in bot.last.text and "Estimate now" not in bot.last.text
    assert labels(bot)[0] == "📝 Drinks of this session"


# ----- sessions -----

def test_a_session_shows_its_drinks_and_estimate(app, bot):
    track(app)
    add(app, bot, when="60", food="empty")
    add(app, bot, "shot", food=None)
    open_session(app, bot)
    assert "🍺 Glass of beer, 500 ml, 5% - 19.7 g" in bot.last.text
    assert "🍸 Shot of vodka, 50 ml, 40% - 15.8 g" in bot.last.text
    assert "Estimate now" in bot.last.text and "mg/dm³" in bot.last.text
    assert "never tells you whether you can drive" in bot.last.text
    assert labels(bot)[:2] == ["📈 Curve", "📝 Drinks of this session"]
    session = bot.last.text
    click(app, bot, "drinktracker:curve:" + str(drinks(app)[0]['id']))
    assert bot.files == [] and bot.last.photo[:8] == b"\x89PNG\r\n\x1a\n"
    assert bot.last.text.startswith("<b>🍺 Drink tracker &gt; 📜 History &gt; Session &gt; 📈 Curve:</b>\n\n")
    assert " - 0.00‰ (0.00 mg/dm³)" in bot.last.text and "Peak: <i>" in bot.last.text
    click(app, bot, "core:back")
    assert bot.last.photo is None and bot.last.text == session


def test_a_drink_can_be_changed(app, bot):
    track(app)
    add(app, bot)
    drink = str(drinks(app)[0]['id'])
    open_session(app, bot)
    click(app, bot, "drinktracker:drinks:" + drink)
    click(app, bot, "drinktracker:entry:" + drink)
    assert labels(bot)[:3] == ["✏️ Change the amount and strength", "🕒 Change the date and time", "🗑️ Delete"]
    click(app, bot, "drinktracker:edit:" + drink)
    send(app, "330")
    send(app, "7")
    assert "The drink has been changed" in bot.last.text and "🍺 Glass of beer, 330 ml, 7%" in bot.last.text
    found = drinks(app)[0]
    assert found['grams'] == pytest.approx(drinktracker.grams_of(330, 7)) and found['kcal'] == pytest.approx(
        141.9 + (drinktracker.grams_of(330, 7) - drinktracker.grams_of(330, 5)) * 7)
    click(app, bot, "drinktracker:move:" + drink)
    send(app, ago(3))
    assert drinks(app)[0]['drunk_at'] == datetime.strptime(ago(3), "%Y-%m-%d %H:%M").isoformat()


def test_deleting_a_drink_can_split_a_session(app, bot):
    track(app)
    add(app, bot, when=hours_ago(4))
    add(app, bot, when=hours_ago(2), food=None)
    add(app, bot, food=None)
    middle = drinks(app)[1]['id']
    open_session(app, bot)
    click(app, bot, "drinktracker:delete:" + str(middle))
    assert "Do you really want to delete this drink?" in bot.last.text and len(drinks(app)) == 3
    click(app, bot, "drinktracker:delete_confirmed:" + str(middle))
    assert "has been deleted" in bot.last.text and "<i>2</i> sessions" in bot.last.text
    click(app, bot, "drinktracker:delete_confirmed:" + str(middle))
    assert "no longer there" in bot.last.text


def test_someone_else_cannot_touch_a_drink(app, bot):
    track(app)
    add(app, bot)
    drink = str(drinks(app)[0]['id'])
    app.router.load_user(make_message("", user_id=2).from_user)
    app.storage.database.execute("UPDATE " + app.storage.for_module("drinktracker").table("drinks") +
                                 " SET user_id = 2;")
    for action in ("session", "drinks", "entry", "edit", "move", "delete", "delete_confirmed"):
        click(app, bot, "drinktracker:" + action + ":" + drink)
        assert "no longer there" in bot.last.text
    assert len(drinks(app)) == 1


def test_many_sessions_are_split_into_pages(app, bot):
    track(app)
    for days in range(drinktracker.page_size + 2):
        pour(app, 24 * (days + 1))
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:sessions")
    assert "Page <i>1</i> of <i>2</i>, <i>10</i> sessions" in bot.last.text
    assert "⬅️ Previous" in labels(bot) and "➡️ Next" in labels(bot)
    click(app, bot, "drinktracker:sessions:1")
    assert len([one for one in labels(bot) if "Drinks" in one]) == 2


def test_sessions_need_the_body_only_with_the_breathalyser(lonely):
    bot = lonely.services.bot
    pour(lonely, 1)
    send(lonely, "/drinktracker")
    click(lonely, bot, "drinktracker:sessions")
    assert "a few details about you" in bot.last.text and labels(bot)[0] == "👤 My details"


# ----- over time -----

def test_the_history_sums_up_the_days_and_draws_them(app, bot):
    track(app)
    add(app, bot)
    add(app, bot, "wine", food=None)
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:chart")
    assert bot.last.photo[:8] == b"\x89PNG\r\n\x1a\n"
    assert bot.last.text == "<b>🍺 Drink tracker &gt; 📈 Chart:</b>\n\n" + date.today().isoformat() \
        + " - Drinks 2, pure alcohol 35 g, 342 kcal"


def test_an_empty_chart_says_so(app, bot):
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:chart")
    assert bot.last.photo is None and "No drinks in the last 30 days" in bot.last.text


def test_the_days_chart_is_a_png():
    assert drinktracker.draw_days([(date.today() - timedelta(days=1), 20.0), (date.today(), 0.0)], "Alcohol")[:8] \
        == b"\x89PNG\r\n\x1a\n"


# ----- sharing -----

def test_the_usual_drinks_are_listed_in_the_settings(app, bot):
    send(app, "/drinktracker")
    click(app, bot, "core:settings:drinktracker")
    assert bot.last.text.startswith("<b>⚙️ Settings &gt; 🧩 Modules &gt; 🍺 Drink tracker:</b>")
    assert labels(bot)[:6] == ["🍺 Glass of beer, 500 ml, 5%", "🍻 Glass of strong beer, 500 ml, 8%",
                               "🍹 Bottle of cider, 400 ml, 4.5%", "🍷 Glass of wine, 150 ml, 13%",
                               "🍸 Shot of vodka, 50 ml, 40%", "🥃 Glass of whisky, 40 ml, 40%"]
    click(app, bot, "core:back")
    assert labels(bot)[3] == "⚙️ Settings"


def test_a_usual_drink_can_be_changed_and_restored(app, bot):
    track(app)
    send(app, "/drinktracker")
    click(app, bot, "core:settings:drinktracker")
    click(app, bot, "drinktracker:preset:beer")
    assert "Name: <i>Glass of beer</i>" in bot.last.text and "↩️ Restore the defaults" not in labels(bot)
    click(app, bot, "drinktracker:preset_edit:beer:name")
    send(app, "Pint <IPA>")
    click(app, bot, "drinktracker:preset_edit:beer:emoji")
    send(app, "beer")
    assert "Send just an emoji" in bot.last.text
    send(app, "🍻")
    click(app, bot, "drinktracker:preset_edit:beer:volume")
    send(app, "568")
    click(app, bot, "drinktracker:preset_edit:beer:strength")
    send(app, "4,5")
    assert "The drink has been changed ✅" in bot.last.text and "Name: <i>Pint &lt;IPA&gt;</i>" in bot.last.text
    assert "Volume: <i>568 ml</i>" in bot.last.text and "Strength: <i>4.5%</i>" in bot.last.text
    click(app, bot, "core:back")
    assert labels(bot)[0] == "🍻 Pint <IPA>, 568 ml, 4.5%"
    add(app, bot)
    assert (drinks(app)[0]['volume'], drinks(app)[0]['strength']) == (568, 4.5)
    send(app, "/drinktracker")
    click(app, bot, "core:settings:drinktracker")
    click(app, bot, "drinktracker:preset:beer")
    click(app, bot, "drinktracker:preset_restore:beer")
    assert "The drink is back to its defaults ✅" in bot.last.text and "Volume: <i>500 ml</i>" in bot.last.text


def test_the_assistant_takes_the_usual_drink_from_the_settings(app, bot):
    track(app)
    app.storage.module_state.set(1, "drinktracker", "presets", '{"wine": {"volume": 200, "strength": 11}}')
    outcome = drinktracker.act_add_drink(as_user(app), "wine", None, None, None, "little")
    assert "🍷 Glass of wine, 200 ml, 11%" in outcome.result


def test_a_drink_can_be_added_to_the_list_and_deleted_from_it(app, bot):
    track(app)
    send(app, "/drinktracker")
    click(app, bot, "core:settings:drinktracker")
    assert labels(bot)[6] == "➕ Add a drink"
    click(app, bot, "drinktracker:preset_add")
    assert bot.last.text.startswith("<b>⚙️ Settings &gt; 🧩 Modules &gt; 🍺 Drink tracker &gt; ➕ Add a drink:</b>")
    for text in ("Mead", "🍯", "200", "12"):
        send(app, text)
    assert "The drink has been added ✅" in bot.last.text and "Name: <i>Mead</i>" in bot.last.text
    assert "↩️ Restore the defaults" not in labels(bot)
    click(app, bot, "core:back")
    assert labels(bot)[6] == "🍯 Mead, 200 ml, 12%"
    add(app, bot, kind="own1")
    assert (drinks(app)[0]['kind'], drinks(app)[0]['volume']) == ("own1", 200)
    send(app, "/drinktracker")
    click(app, bot, "core:settings:drinktracker")
    for kind in ("own1", "beer"):
        click(app, bot, "drinktracker:preset:" + kind)
        click(app, bot, "drinktracker:preset_remove:" + kind)
        assert "Do you really want to delete this drink from the list?" in bot.last.text
        click(app, bot, "drinktracker:preset_removed:" + kind)
    assert "The drink has been deleted from the list ✅" in bot.last.text
    assert labels(bot)[0] == "🍻 Glass of strong beer, 500 ml, 8%" and "🍯 Mead, 200 ml, 12%" not in labels(bot)
    assert "↩️ Bring back the default drinks" in labels(bot)
    click(app, bot, "drinktracker:kind:own1")
    assert bot.last.text.startswith("Sorry, this button does not work anymore")
    assert drinktracker.drink_line(as_user(app), drinks(app)[0]).startswith("🍯 Mead, 200 ml, 12%")
    send(app, "/drinktracker")
    click(app, bot, "core:settings:drinktracker")
    click(app, bot, "drinktracker:restore_kinds")
    assert "The default drinks are back on the list ✅" in bot.last.text
    assert labels(bot)[0] == "🍺 Glass of beer, 500 ml, 5%" and "↩️ Bring back the default drinks" not in labels(bot)


def test_the_assistant_knows_the_own_drinks(app, bot):
    track(app)
    app.storage.module_state.set(1, "drinktracker", "presets",
                                 '{"beer": {"hidden": true}, "own1": {"name": "Mead", "emoji": "🍯", '
                                 '"volume": 200, "strength": 12}}')
    assert "own1 (🍯 Mead, 200 ml, 12%), custom" in drinktracker.summary(as_user(app))
    assert "- strong_beer (" in drinktracker.summary(as_user(app))
    assert "pick one of" in drinktracker.act_add_drink(as_user(app), "beer", None, None, None, "little").result
    outcome = drinktracker.act_add_drink(as_user(app), "own1", None, None, None, "little")
    assert "🍯 Mead, 200 ml, 12%" in outcome.result


def test_own_details_are_asked_for_by_the_sessions(app, bot):
    pour(app, 1)
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:sessions")
    click(app, bot, "drinktracker:my_body")
    assert bot.last.text.startswith("<b>🍺 Drink tracker &gt; 📜 History &gt; 👤 My details:</b>")
    click(app, bot, "drinktracker:body:sex:female")
    for text in ("30", "165", "60"):
        send(app, text)
    assert "Your details have been saved" in bot.last.text and "Page <i>1</i> of <i>1</i>" in bot.last.text
    assert drinktracker.body_of(as_user(app)) == ("female", 30, 165, 60)


def test_only_a_fresh_session_is_shared(app, bot):
    track(app)
    assert exposed(app, "session") is None
    add(app, bot, food="meal")
    shared = exposed(app, "session")
    assert [(round(grams, 1), food) for _, grams, food in shared['drinks']] == [(19.7, "meal")]
    old = (datetime.now() - timedelta(hours=25)).isoformat(timespec="seconds")
    app.storage.database.execute("UPDATE " + app.storage.for_module("drinktracker").table("drinks") +
                                 " SET drunk_at = ?;", (old,))
    assert exposed(app, "session") is None


def test_the_calories_of_each_day_are_shared(app, bot):
    track(app)
    add(app, bot)
    assert exposed(app, "kcal", date.today().isoformat()) == {date.today().isoformat(): 215}


def test_wiping_a_user_takes_their_drinks_and_details_with_them(app, bot):
    send(app, "/drinktracker")
    click(app, bot, "drinktracker:my_body")
    click(app, bot, "drinktracker:body:sex:female")
    for text in ("30", "165", "60"):
        send(app, text)
    add(app, bot)
    app.storage.users.delete(1)
    assert drinks(app) == []
    assert app.storage.database.query_all("SELECT * FROM " + app.storage.for_module("drinktracker").table("sizes")
                                          + ";") == []


# ----- assistant -----

def test_the_summary_tells_the_session_and_the_week(app, bot):
    assert drinktracker.summary(as_user(app)) == ""
    track(app)
    add(app, bot, when=hours_ago(2))
    found = drinktracker.summary(as_user(app)).split("\n")
    assert found[0].startswith("Session since " + ago(2) + " - drinks 1, pure alcohol 20 g, peak 0.")
    assert found[1] == "The last seven days - drinks 1, pure alcohol 20 g"


def test_without_the_breathalyser_the_summary_has_no_estimate(plain):
    pour(plain, 1)
    assert drinktracker.summary(as_user(plain)).split("\n")[0] == "Session since " + ago(1) \
        + " - drinks 1, pure alcohol 20 g"


def test_a_session_long_over_is_left_out_of_the_summary(app, bot):
    track(app)
    add(app, bot, when=ago(30))
    assert drinktracker.summary(as_user(app)) == "The last seven days - drinks 1, pure alcohol 20 g"


def test_the_assistant_asks_about_food_when_a_session_starts(app, bot):
    track(app)
    outcome = drinktracker.act_add_drink(as_user(app), "beer", None, None, None, None)
    assert outcome.status == "refused" and str(outcome.result).startswith("This drink starts a new session")
    outcome = drinktracker.act_add_drink(as_user(app), "beer", None, None, None, "meal")
    assert outcome.status == "asking" and "Food: <i>A big meal</i>" in outcome.result
    assert drinks(app) == []
    assert outcome.then().startswith("The drink has been logged ✅")
    assert [(row['kind'], row['volume'], row['food']) for row in drinks(app)] == [("beer", 500, "meal")]


def test_the_food_is_left_alone_in_the_middle_of_a_session(app, bot):
    track(app)
    add(app, bot, when=hours_ago(1))
    outcome = drinktracker.act_add_drink(as_user(app), "custom", 200, 13, None, "empty")
    assert outcome.status == "asking" and "Food" not in outcome.result
    outcome.then()
    assert [row['food'] for row in drinks(app)] == ["little", None]


@pytest.mark.parametrize("kind, volume, strength, when, problem", [
    ("mead", None, None, None, "I do not know this drink"),
    ("custom", 200, None, None, "For your own drink give"),
    ("custom", 5000, 5, None, "Write a number between 10 and 2000"),
    ("wine", None, None, "tomorrow", "Write a time that has passed"),
])
def test_the_assistant_is_checked_like_the_screens(app, bot, kind, volume, strength, when, problem):
    track(app)
    outcome = drinktracker.act_add_drink(as_user(app), kind, volume, strength, when, "little")
    assert outcome.status == "refused" and str(outcome.result).startswith(problem)


def test_without_a_body_the_assistant_cannot_place_a_drink(lonely):
    outcome = drinktracker.act_add_drink(as_user(lonely), "beer", None, None, None, "little")
    assert outcome.status == "refused" and str(outcome.result).startswith("The user has to give their sex and age")


def test_the_assistant_reads_the_last_days(app, bot):
    track(app)
    add(app, bot)
    assert drinktracker.act_days(as_user(app)).result == [{'day': date.today().isoformat(), 'drinks': 1,
                                                           'alcohol_grams': 20, 'kcal': 215}]
