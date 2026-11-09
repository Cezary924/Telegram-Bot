from datetime import date, datetime, timedelta

import pytest

from core.api import Ctx, years_before
from core.testing import make_callback, make_message
from modules.external.foodtracker import module as foodtracker


@pytest.fixture
def lonely(tmp_path, request):
    (tmp_path / "modules.yaml").write_text("bodytracker: false\ncalories: false\ndrinktracker: false\n",
                                           encoding='utf8')
    return request.getfixturevalue("app")


def send(app, text: str):
    app.router.handle_message(make_message(text))


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))
    app.router.wait_for_tasks()


def labels(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def meals(app):
    return app.storage.database.query_all("SELECT * FROM " + app.storage.for_module("foodtracker").table("meals") +
                                          " ORDER BY id;")


def eat(app, bot, kcal: str, when: str = "0"):
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:add")
    send(app, kcal)
    if when.isdigit():
        click(app, bot, "foodtracker:meal:when:" + when)
    else:
        send(app, when)


def track(app):
    tracker = app.storage.for_module("bodytracker")
    app.storage.database.execute("INSERT INTO " + tracker.table("weights") + " (user_id, weight, measured_at) "
                                 "VALUES (1, 80, ?);", (datetime.now().isoformat(timespec="seconds"),))
    app.storage.database.execute("INSERT INTO " + tracker.table("heights") + " (user_id, height, measured_at) "
                                 "VALUES (1, 180, ?);", (datetime.now().isoformat(timespec="seconds"),))
    app.storage.profiles.set(1, "sex", "male")
    app.storage.profiles.set(1, "born", years_before(date.today(), 30).isoformat())


def drink(app):
    drinks = app.storage.for_module("drinktracker")
    app.storage.database.execute("INSERT INTO " + drinks.table("drinks") + " (user_id, kind, volume, strength, grams, "
                                 "kcal, food, drunk_at) VALUES (1, 'beer', 500, 5, 19.725, 215, 'empty', ?);",
                                 (datetime.now().isoformat(timespec="seconds"),))


def test_the_command_opens_a_menu_without_any_data(app, bot):
    eat(app, bot, "500")
    send(app, "/foodtracker")
    assert "500" not in bot.last.text
    assert labels(bot)[:5] == ["➕ Add a meal", "📅 Today", "📜 History", "📈 Chart", "⚙️ Settings"]
    assert bot.last.text.endswith("😊")


def test_a_meal_is_asked_for_until_it_makes_sense(app, bot):
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:add")
    send(app, "a lot")
    assert "between 1 and 5000" in bot.last.text
    send(app, "450,5")
    assert "When was it?" in bot.last.text
    click(app, bot, "foodtracker:meal:when:0")
    assert [row['kcal'] for row in meals(app)] == [450.5]
    assert "<i>450 kcal</i>" in bot.last.text


def test_a_meal_can_be_logged_afterwards(app, bot):
    eat(app, bot, "300", (datetime.now() - timedelta(hours=26)).strftime("%Y-%m-%d %H:%M"))
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert meals(app)[0]['eaten_at'][:10] in (yesterday, (date.today() - timedelta(days=2)).isoformat())
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:today")
    assert "Food: <i>0 kcal</i>" in bot.last.text


def test_today_without_a_goal_says_where_to_set_it(lonely):
    bot = lonely.services.bot
    eat(lonely, bot, "500")
    send(lonely, "/foodtracker")
    click(lonely, bot, "foodtracker:today")
    assert "Food: <i>500 kcal</i>" in bot.last.text and "Alcohol" not in bot.last.text
    assert "Set a daily goal" in bot.last.text


def test_a_typed_goal_counts_what_is_left(lonely):
    bot = lonely.services.bot
    send(lonely, "/foodtracker")
    click(lonely, bot, "foodtracker:set_goal")
    send(lonely, "100")
    assert "between 500 and 6000" in bot.last.text
    send(lonely, "2000")
    assert "Goal: <i>2000 kcal</i>" in bot.last.text and labels(lonely.services.bot)[0] == "🎯 Type the goal"
    assert "🔄 Follow my body tracker" not in labels(bot)
    eat(lonely, bot, "500")
    eat(lonely, bot, "1700")
    send(lonely, "/foodtracker")
    click(lonely, bot, "foodtracker:today")
    assert "Over by: <i>200 kcal</i>" in bot.last.text
    last = str(meals(lonely)[-1]['id'])
    click(lonely, bot, "foodtracker:history")
    click(lonely, bot, "foodtracker:delete:" + last)
    assert "Do you really want to delete this meal?" in bot.last.text and "1700 kcal" in bot.last.text
    click(lonely, bot, "foodtracker:delete_confirmed:" + last)
    assert "has been deleted" in bot.last.text and "Page <i>1</i> of <i>1</i>, <i>1</i> meals" in bot.last.text
    send(lonely, "/foodtracker")
    click(lonely, bot, "foodtracker:today")
    assert "Left: <i>1500 kcal</i>" in bot.last.text


def test_the_goal_can_follow_the_body_tracker(app, bot):
    track(app)
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:auto_goal")
    assert labels(bot)[1] == "Light exercise one to three days a week"
    click(app, bot, "foodtracker:auto:activity:light")
    assert "Goal: <i>2448 kcal (from the body tracker, light exercise" in bot.last.text
    app.storage.database.execute("UPDATE " + app.storage.for_module("bodytracker").table("weights") +
                                 " SET weight = 90;")
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:today")
    assert "Goal: <i>2585 kcal" in bot.last.text


def test_meals_are_listed_newest_first_a_page_at_a_time(app, bot):
    for hours in range(10):
        eat(app, bot, str(100 + hours), (datetime.now() - timedelta(hours=hours + 1)).strftime("%Y-%m-%d %H:%M"))
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:history")
    assert "Page <i>1</i> of <i>2</i>, <i>10</i> meals" in bot.last.text
    assert labels(bot)[0].endswith(" - 100 kcal")
    assert labels(bot)[foodtracker.page_size:][:2] == ["⬅️ Previous", "➡️ Next"]
    click(app, bot, "foodtracker:history:1")
    assert "Page <i>2</i> of <i>2</i>" in bot.last.text and labels(bot)[1].endswith(" - 109 kcal")


def test_a_meal_can_be_changed(app, bot):
    eat(app, bot, "500")
    meal = str(meals(app)[0]['id'])
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:history")
    click(app, bot, "foodtracker:eaten:" + meal)
    assert labels(bot)[:3] == ["✏️ Change the calories", "🕒 Change the date and time", "🗑️ Delete"]
    click(app, bot, "foodtracker:edit:" + meal)
    send(app, "650")
    assert "The meal has been changed" in bot.last.text and "<i>650 kcal</i>" in bot.last.text
    click(app, bot, "foodtracker:move:" + meal)
    send(app, "30.10.2026 13.15")
    assert meals(app)[0]['kcal'] == 650 and meals(app)[0]['eaten_at'] == "2026-10-30T13:15:00"


def test_someone_else_cannot_touch_a_meal(app, bot):
    eat(app, bot, "500")
    meal = str(meals(app)[0]['id'])
    app.router.load_user(make_message("", user_id=2).from_user)
    app.storage.database.execute("UPDATE " + app.storage.for_module("foodtracker").table("meals") +
                                 " SET user_id = 2;")
    for action in ("eaten", "edit", "move", "delete", "delete_confirmed"):
        click(app, bot, "foodtracker:" + action + ":" + meal)
        assert "This meal is no longer there" in bot.last.text
    assert len(meals(app)) == 1


def test_a_goal_following_a_tracker_without_data_says_so(app, bot):
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:auto_goal")
    click(app, bot, "foodtracker:auto:activity:light")
    assert "Your age is missing in Settings &gt; About me, or your height or a recent weight" in bot.last.text


def test_alcohol_counts_into_the_day(app, bot):
    drink(app)
    eat(app, bot, "500")
    send(app, "/foodtracker")
    click(app, bot, "foodtracker:today")
    assert "Alcohol: <i>215 kcal</i>" in bot.last.text and "Together: <i>715 kcal</i>" in bot.last.text
    click(app, bot, "core:back")
    click(app, bot, "foodtracker:chart")
    assert bot.last.photo[:8] == b"\x89PNG\r\n\x1a\n"
    assert bot.last.text == "<b>🍽️ Food diary &gt; 📈 Chart:</b>\n\n" + date.today().isoformat() \
        + " - 715 kcal (of which 215 kcal from alcohol)"


def test_the_chart_tells_the_goal_and_says_when_the_month_is_empty(lonely):
    bot = lonely.services.bot
    lonely.storage.module_state.set(1, "foodtracker", "goal", "2000")
    send(lonely, "/foodtracker")
    click(lonely, bot, "foodtracker:chart")
    assert bot.last.photo is None and bot.last.text.endswith(":</b>\n\nNothing logged in the last 30 days 🤷")
    click(lonely, bot, "core:back")
    click(lonely, bot, "foodtracker:add")
    send(lonely, "500")
    click(lonely, bot, "foodtracker:meal:when:0")
    send(lonely, "/foodtracker")
    click(lonely, bot, "foodtracker:chart")
    assert bot.last.photo is not None
    assert bot.last.text.endswith(":</b>\n\nGoal: <i>2000 kcal</i>\n" + date.today().isoformat() + " - 500 kcal")


def test_the_chart_is_a_png():
    drawn = foodtracker.draw([(date.today() - timedelta(days=1), 1800.0, 215.0), (date.today(), 900.0, 0.0)], 2000.0,
                             {'title': "Calories", 'food': "Food", 'alcohol': "Alcohol", 'goal': "Goal"})
    assert drawn[:8] == b"\x89PNG\r\n\x1a\n"


def test_wiping_a_user_takes_their_meals_with_them(app, bot):
    eat(app, bot, "500")
    app.storage.users.delete(1)
    assert meals(app) == []


# ----- assistant -----

def as_user(app) -> Ctx:
    return Ctx(app.services, app.registry.get("foodtracker"), app.router.load_user(make_message("").from_user))


def test_the_summary_tells_today_and_the_goal(app, bot):
    assert foodtracker.summary(as_user(app)) == ""
    eat(app, bot, "600")
    assert foodtracker.summary(as_user(app)) == "Eaten and drunk today: <i>600 kcal</i>"
    app.storage.module_state.set(1, "foodtracker", "goal", "2000")
    assert foodtracker.summary(as_user(app)).endswith("\nGoal: <i>2000 kcal</i>")


def test_the_assistant_adds_a_meal_once_confirmed(app, bot):
    when = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    outcome = foodtracker.act_add_meal(as_user(app), 650, when)
    assert outcome.result == "Save this meal?\nMeal: <i>650 kcal</i>\nWhen: <i>" + when + "</i>"
    assert meals(app) == []
    assert "650 kcal" in outcome.then()
    assert [row['kcal'] for row in meals(app)] == [650]


def test_the_assistant_is_checked_like_the_screens(app, bot):
    assert foodtracker.act_add_meal(as_user(app), 0, None).result == "Write a number between 1 and 5000"
    assert foodtracker.act_add_meal(as_user(app), 500, "soon").status == "refused"


def test_the_assistant_reads_the_last_days(app, bot):
    eat(app, bot, "600")
    found = foodtracker.act_days(as_user(app)).result
    assert found == {'goal_kcal': None, 'days': [{'day': date.today().isoformat(), 'food_kcal': 600,
                                                  'alcohol_kcal': 0}]}
