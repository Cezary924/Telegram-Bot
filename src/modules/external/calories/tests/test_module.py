from datetime import datetime

import pytest

from core.api import Ctx
from core.testing import make_callback, make_message
from modules.external.calories import module as calories


@pytest.fixture
def lonely(tmp_path, request):
    (tmp_path / "modules.yaml").write_text("bodytracker: false\n", encoding='utf8')
    return request.getfixturevalue("app")


def send(app, text: str):
    app.router.handle_message(make_message(text))


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))


def labels(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def track(app, born: str | None = "1996-01-01", sex: str | None = "male"):
    tracker = app.storage.for_module("bodytracker")
    app.storage.database.execute("INSERT INTO " + tracker.table("weights") + " (user_id, weight, measured_at) "
                                 "VALUES (1, 80, ?);", (datetime.now().isoformat(timespec="seconds"),))
    app.storage.database.execute("INSERT INTO " + tracker.table("heights") + " (user_id, height, measured_at) "
                                 "VALUES (1, 180, ?);", (datetime.now().isoformat(timespec="seconds"),))
    app.storage.profiles.set(1, "sex", sex)
    app.storage.profiles.set(1, "born", born)


def tracked_born(app) -> str | None:
    return app.storage.profiles.get(1).born


@pytest.mark.parametrize("sex, value", [("male", 1780), ("female", 1614), ("other", 1614), ("undisclosed", 1614)])
def test_mifflin_st_jeor_counts_an_undisclosed_sex_as_female(sex, value):
    assert calories.mifflin_st_jeor(sex, 30, 180, 80) == value


def test_the_need_is_shared_for_any_activity(app):
    module = app.registry.get("calories")
    ctx = Ctx(app.services, module, app.router.load_user(make_message("").from_user))
    assert module.exposed['need'].handler(ctx, "male", 30, 180, 80, "very_active") == pytest.approx(1780 * 1.9)


def test_the_command_shows_no_data(app, bot):
    track(app)
    send(app, "/calories")
    assert "180" not in bot.last.text and labels(bot)[0] == "🧮 Work it out"


def test_without_the_tracker_everything_is_asked(lonely):
    bot = lonely.services.bot
    send(lonely, "/calories")
    click(lonely, bot, "calories:count")
    send(lonely, "30")
    assert "Pick one of the buttons" in bot.last.text
    click(lonely, bot, "calories:need:sex:male")
    send(lonely, "300")
    assert "between 18 and 120" in bot.last.text
    for text in ("30", "180", "80"):
        send(lonely, text)
    click(lonely, bot, "calories:need:activity:light")
    text = bot.last.text
    assert "Burnt at rest: <i>1780 kcal</i>" in text and "Daily need: <i>2448 kcal</i>" in text
    assert "Height: <i>180 cm</i>\n" in text and labels(bot) == ["💾 Save the new details about me"]
    assert [data for _, data in bot.last.buttons] == ["calories:save:male:30::"]
    click(lonely, bot, "calories:save:male:30::")
    assert lonely.storage.profiles.get(1).sex == "male" and lonely.storage.profiles.get(1).age == 30


def test_the_tracker_is_offered_and_named_in_the_result(app, bot):
    track(app)
    send(app, "/calories")
    click(app, bot, "calories:count")
    assert labels(bot)[:2] == ["Use it", "Type everything"]
    click(app, bot, "calories:need:offer:1")
    click(app, bot, "calories:need:activity:sedentary")
    assert "Weight: <i>80.0 kg</i> (from your saved details)" in bot.last.text and labels(bot) == []


def test_what_the_tracker_lacks_is_asked_and_may_be_saved(app, bot):
    track(app, born=None, sex=None)
    send(app, "/calories")
    click(app, bot, "calories:count")
    click(app, bot, "calories:need:offer:1")
    click(app, bot, "calories:need:sex:undisclosed")
    send(app, "30")
    click(app, bot, "calories:need:activity:sedentary")
    assert "Burnt at rest: <i>1614 kcal</i>" in bot.last.text
    assert labels(bot) == ["💾 Save the new details about me"]
    result = bot.last.message_id
    click(app, bot, "calories:save:undisclosed:30::")
    assert "Saved ✅" in bot.last.text
    assert bot.unbuttoned == [(1, result)] and tracked_born(app) is not None


def test_someone_else_is_never_saved(app, bot):
    track(app, born=None)
    send(app, "/calories")
    click(app, bot, "calories:count")
    click(app, bot, "calories:need:offer:0")
    click(app, bot, "calories:need:sex:female")
    for text in ("40", "165", "60"):
        send(app, text)
    click(app, bot, "calories:need:activity:moderate")
    assert labels(bot) == [] and tracked_born(app) is None


# ----- assistant -----

def as_user(app) -> Ctx:
    return Ctx(app.services, app.registry.get("calories"), app.router.load_user(make_message("").from_user))


def test_the_assistant_counts_with_the_saved_body(app, bot):
    assert str(calories.act_need(as_user(app), "light", None, None, None, None).result).startswith(
        "Some details are missing - age, height, weight")
    track(app)
    found = calories.act_need(as_user(app), "light", None, None, None, None).result
    assert isinstance(found, dict)
    assert found['sex'] == "male" and found['need_kcal'] == round((800 + 1125 - 5 * found['age'] + 5) * 1.375)
    assert calories.act_need(as_user(app), "light", "female", 30, 165, 60).result == {
        'bmr_kcal': 1320, 'need_kcal': 1815, 'sex': "female", 'age': 30, 'height_cm': 165, 'weight_kg': 60}


def test_the_assistant_is_checked_like_the_screens(app, bot):
    assert calories.act_need(as_user(app), "lazy", None, 30, 165, 60).status == "refused"
    assert calories.act_need(as_user(app), "light", "robot", 30, 165, 60).status == "refused"
    wrong = calories.act_need(as_user(app), "light", None, 30, 165, 600)
    assert str(wrong.result).startswith("These details look wrong")
