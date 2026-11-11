from datetime import datetime, timedelta

import pytest

from core.context import Ctx
from core.form import Answers, Problem, Question, moments, number, parse_moment, past_moment, read_moment
from core.module import Module
from core.testing import make_callback, make_message
from core.ui.keyboard import Button
from core.ui.view import View

texts = {'name': "Survey", 'description': "Asks", 'commands.survey': "Ask", 'ask.sex': "Your sex?",
         'ask.age': "Your age?", 'ask.when': "When?", 'ask.code': "Your code?", 'code_wrong': "Not a code",
         'ask.note': "Note for {code}",
         'sex.female': "Female", 'sex.male': "Male"}


@pytest.fixture
def offered() -> dict:
    return {}


@pytest.fixture
def known() -> dict:
    return {}


@pytest.fixture
def survey(app, offered, known):
    module = Module(name="survey")

    @module.command("survey")
    def command_survey(ctx):
        return ctx.form("body", known=dict(known), offered=offered.get('groups') or dict(offered))

    @module.form("body", [Question("sex", "choice", choices=("female", "male")), Question("age", low=18, high=120),
                          Question("when", "moment", back=24)], title="name")
    def done(_ctx, answers):
        return View(text="done " + str(sorted(answers.values.items())) + " typed " + ",".join(answers.typed)
                    + (" declined " + ",".join(answers.declined) if answers.declined else ""))

    app.registry.add(module)
    app.catalog.add("survey", "en", texts)
    return module


def send(app, text: str):
    app.router.handle_message(make_message(text))


def click(app, action: str):
    app.router.handle_callback(make_callback(action, message_id=app.services.bot.last.message_id))


def labels(app) -> list[str]:
    return [text for text, _ in app.services.bot.last.buttons]


def test_a_question_is_checked():
    with pytest.raises(ValueError):
        Question("age", "date")
    with pytest.raises(ValueError):
        Question("offer")
    with pytest.raises(ValueError):
        Question("sex", "choice")


def test_a_question_key_and_its_choices_fit_into_a_button():
    with pytest.raises(ValueError):
        Question("Age")
    with pytest.raises(ValueError):
        Question("sex", "choice", choices=("a:b",))
    with pytest.raises(ValueError):
        Module(name="survey").form("body", [Question("sex", "choice", choices=("x" * 60,))])


def test_a_form_asks_something():
    with pytest.raises(ValueError):
        Module(name="survey").form("body", [])


def test_a_form_brings_its_screen_answers_and_buttons():
    module = Module(name="survey")
    module.form("body", [Question("age", low=1, high=2)], parent="", title="name")(lambda ctx, answers: None)
    assert module.view_named("body") is not None
    assert [state.name for state in module.states] == ["body"]
    assert [callback.action for callback in module.callbacks] == ["body"]


@pytest.mark.parametrize("text, expected", [("72", 72), ("72,5", 72.5), ("12.5%", 12.5), ("a lot", None)])
def test_a_number_takes_a_comma_and_a_percent(text, expected):
    assert number(text) == expected


@pytest.mark.parametrize("text, now, expected", [
    ("21:30", datetime(2026, 10, 30, 22, 0), datetime(2026, 10, 30, 21, 30)),
    ("23:30", datetime(2026, 10, 30, 22, 0), datetime(2026, 10, 29, 23, 30)),
    ("2026-10-30 08:15", datetime(2026, 10, 30, 22, 0), datetime(2026, 10, 30, 8, 15)),
    ("2026-10-30 23:00", datetime(2026, 10, 30, 22, 0), None),
    ("2026-10-27 08:15", datetime(2026, 10, 30, 22, 0), None),
    ("half past nine", datetime(2026, 10, 30, 22, 0), None),
])
def test_a_moment_has_passed_and_is_not_too_old(text, now, expected):
    assert parse_moment(text, now, 48) == expected


@pytest.mark.parametrize("text, expected", [
    ("21.30", datetime(2026, 10, 30, 21, 30)),
    ("30.10.2026 08:15", datetime(2026, 10, 30, 8, 15)),
    ("30.10.2026  8.15", datetime(2026, 10, 30, 8, 15)),
    ("2026-10-30 08.15", datetime(2026, 10, 30, 8, 15)),
])
def test_a_moment_takes_the_polish_way_of_writing_it(text, expected):
    assert parse_moment(text, datetime(2026, 10, 30, 22, 0), 48) == expected


def test_a_future_moment_puts_a_bare_time_ahead():
    now = datetime(2026, 10, 30, 22, 0)
    assert read_moment("21:30", now, is_future=True) == datetime(2026, 10, 31, 21, 30)
    assert read_moment("23.15", now, is_future=True) == datetime(2026, 10, 30, 23, 15)
    assert read_moment("29.10.2026 10:00", now, is_future=True) == datetime(2026, 10, 29, 10, 0)


def test_a_day_and_month_without_the_year_mean_the_current_year():
    now = datetime(2026, 10, 30, 22, 0)
    assert read_moment("30.10 21:30", now) == datetime(2026, 10, 30, 21, 30)
    assert read_moment("24.12  18.00", now, is_future=True) == datetime(2026, 12, 24, 18, 0)
    assert read_moment("29.02 10:00", now) is None
    assert parse_moment("30.10 23:00", now, 48) is None


def test_a_moment_without_a_limit_only_has_to_have_passed():
    now = datetime(2026, 10, 30, 22, 0)
    assert parse_moment("2020-01-01 08:00", now, None) == datetime(2020, 1, 1, 8, 0)
    assert parse_moment("2026-10-31 08:00", now, None) is None


def test_an_action_reads_a_past_moment_as_iso():
    assert past_moment("2020-01-01 08:00") == "2020-01-01T08:00:00"
    assert past_moment((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")) is None
    assert past_moment("tomorrow") is None


def test_a_moment_offers_only_the_buttons_within_its_limit():
    assert moments(Question("when", "moment", back=1)) == [0, 30, 60]
    assert moments(Question("when", "moment", back=None)) == [0, 30, 60, 120]


def test_answers_tell_what_was_typed_and_not_declined():
    assert Answers({'age': 30, 'sex': "male"}, ("age",)).new(["age", "sex"]) == {'age': 30}
    assert Answers({'age': 30, 'sex': "male"}, ("age", "sex"), ("age",)).new(["age", "sex"]) == {'sex': "male"}


def test_the_questions_are_asked_in_order_and_checked(app, survey):
    send(app, "/survey")
    assert app.services.bot.last.text.endswith("Your sex?") and labels(app)[:2] == ["Female", "Male"]
    send(app, "male")
    assert "Pick one of the buttons" in app.services.bot.last.text
    click(app, "survey:body:sex:male")
    send(app, "15")
    assert "Write a number between 18 and 120" in app.services.bot.last.text
    send(app, "30")
    assert labels(app)[:4] == ["Now", "30 min ago", "1 h ago", "2 h ago"]
    send(app, "yesterday")
    assert "at most 24 hours back" in app.services.bot.last.text
    click(app, "survey:body:when:60")
    moment = (datetime.now().replace(microsecond=0) - timedelta(minutes=60)).isoformat(timespec="seconds")
    assert app.services.bot.last.text.endswith("done " + str([('age', 30.0), ('sex', "male"), ('when', moment)])
                                               + " typed sex,age,when")


def test_saved_data_is_offered_without_showing_it(app, survey, offered):
    offered.update({'age': 41, 'sex': None})
    send(app, "/survey")
    assert "41" not in app.services.bot.last.text and labels(app)[:2] == ["Use it", "Type everything"]
    click(app, "survey:body:offer:1")
    click(app, "survey:body:sex:female")
    click(app, "survey:body:when:0")
    assert "('age', 41)" in app.services.bot.last.text and "typed sex,when" in app.services.bot.last.text


def test_declining_the_saved_data_asks_everything(app, survey, offered):
    offered.update({'age': 41})
    send(app, "/survey")
    click(app, "survey:body:offer:0")
    click(app, "survey:body:sex:female")
    send(app, "50")
    send(app, (datetime.now() - timedelta(hours=1)).strftime("%H:%M"))
    assert "('age', 50.0)" in app.services.bot.last.text and app.services.bot.last.text.endswith("declined age")


def test_known_values_are_not_asked_and_a_complete_form_answers_at_once(app, survey, known):
    known.update({'sex': "male", 'age': 30, 'when': "2026-10-30T20:00:00"})
    send(app, "/survey")
    assert "done" in app.services.bot.last.text and app.services.bot.last.text.endswith("typed ")


def test_nothing_saved_means_no_offer(app, survey, offered):
    offered.update({'age': None})
    send(app, "/survey")
    assert labels(app)[:2] == ["Female", "Male"]


def test_a_stale_button_is_refused(app, survey):
    send(app, "/survey")
    click(app, "survey:body:age:30")
    assert "button" in app.services.bot.last.text.lower()


def test_an_own_parser_has_its_own_problem(app):
    module = Module(name="survey")

    @module.command("survey")
    def command_survey(ctx):
        return ctx.form("code")

    @module.form("code", [Question("code", parse=lambda text, values: text if text.isdigit() else None,
                                   problem="code_wrong"), Question("note", "text", high=5)])
    def done(_ctx, answers):
        return View(text="code " + answers['code'] + " " + answers['note'])

    app.registry.add(module)
    app.catalog.add("survey", "en", texts)
    send(app, "/survey")
    send(app, "abc")
    assert "Not a code" in app.services.bot.last.text
    send(app, "123")
    assert "Note for 123" in app.services.bot.last.text
    send(app, "too long")
    assert "Write between 1 and 5 characters" in app.services.bot.last.text
    send(app, " ok ")
    assert app.services.bot.last.text.endswith("code 123 ok")


def test_an_unknown_form_is_an_error(app, survey):
    ctx = Ctx(app.services, survey, app.router.load_user(make_message("").from_user))
    with pytest.raises(LookupError):
        ctx.form("nothing")


def test_saved_data_that_fits_no_question_is_not_offered(app, survey, offered):
    offered.update({'height': 180})
    send(app, "/survey")
    assert labels(app)[:2] == ["Female", "Male"]


def test_saved_data_out_of_range_is_asked_for_again(app, survey, offered):
    offered.update({'age': 12, 'sex': "robot", 'height': 180})
    send(app, "/survey")
    assert labels(app)[:2] == ["Female", "Male"]


def test_a_button_of_a_finished_form_does_nothing(app, survey):
    send(app, "/survey")
    click(app, "survey:body:sex:male")
    send(app, "30")
    screen = app.services.bot.last.message_id
    click(app, "survey:body:when:0")
    assert app.services.bot.last.text.startswith("<b>Survey:</b>\n\ndone")
    app.router.handle_callback(make_callback("survey:body:when:0", message_id=screen))
    assert "button" in app.services.bot.last.text.lower()
    assert sum(text.count("done") for text in app.services.bot.texts()) == 1


def test_saved_data_can_be_offered_in_groups(app, survey, offered):
    offered.update({'groups': [("core:form.offer", {'sex': "male"}), ("core:form.offer", {'age': 41})]})
    send(app, "/survey")
    click(app, "survey:body:offer:1")
    assert labels(app)[:2] == ["Use it", "Type everything"]
    click(app, "survey:body:offer:0")
    send(app, "50")
    click(app, "survey:body:when:0")
    text = app.services.bot.last.text
    assert "('age', 50.0)" in text and "('sex', 'male')" in text and text.endswith("typed age,when declined age")


def test_an_own_parser_can_say_what_is_wrong(app):
    module = Module(name="survey")

    @module.command("survey")
    def command_survey(ctx):
        return ctx.form("code")

    @module.form("code", [Question("code", parse=lambda text, values: text if text.isdigit()
                                   else Problem("note_wrong", {'code': text}), problem="code_wrong")])
    def done(_ctx, answers):
        return View(text="code " + answers['code'])

    app.registry.add(module)
    app.catalog.add("survey", "en", texts | {'note_wrong': "{code} has letters"})
    send(app, "/survey")
    send(app, "abc")
    assert "abc has letters" in app.services.bot.last.text


def test_a_question_can_be_left_empty_with_its_own_button(app):
    module = Module(name="survey")

    @module.command("survey")
    def command_survey(ctx):
        return ctx.form("code")

    @module.form("code", [Question("code", parse=lambda text, values: text, clear="code_wrong"),
                          Question("sex", "choice", choices=("female", "male"), clear="code_wrong")])
    def done(_ctx, answers):
        return View(text="code " + str(answers['code']) + " sex " + str(answers['sex']))

    app.registry.add(module)
    app.catalog.add("survey", "en", texts)
    send(app, "/survey")
    assert app.services.bot.last.buttons[0] == ("Not a code", "survey:code:code:-")
    click(app, "survey:code:code:-")
    assert labels(app)[:3] == ["Female", "Male", "Not a code"]
    click(app, "survey:code:sex:-")
    assert app.services.bot.last.text.endswith("code None sex None")


def test_a_question_can_be_skipped_by_the_earlier_answers(app):
    module = Module(name="survey")

    @module.command("survey")
    def command_survey(ctx):
        return ctx.form("code")

    @module.form("code", [Question("age", low=1, high=99),
                          Question("note", "text", high=5, is_needed=lambda values: values['age'] > 10)])
    def done(_ctx, answers):
        return View(text="age {:g} note ".format(answers['age']) + str(answers.get('note')))

    app.registry.add(module)
    app.catalog.add("survey", "en", texts)
    send(app, "/survey")
    send(app, "5")
    assert app.services.bot.last.text.endswith("age 5 note None")
    send(app, "/survey")
    send(app, "50")
    send(app, "hi")
    assert app.services.bot.last.text.endswith("age 50 note hi")


@pytest.fixture
def body(app):
    module = Module(name="survey")

    @module.command("survey")
    def command_survey(ctx):
        return ctx.form("body")

    @module.form("body", [Question("weight", "weight", low=20, high=400),
                          Question("height", "height", low=50, high=250)])
    def done(_ctx, answers):
        return View(text="weight {weight} height {height}".format(**answers.values))

    app.registry.add(module)
    app.catalog.add("survey", "en", texts | {'ask.weight': "Weight in {unit}?", 'ask.height': "Height in {unit}?"})
    return module


def test_weight_and_height_follow_the_units_of_the_profile(app, body):
    app.storage.profiles.set(1, "weight_unit", "lb")
    app.storage.profiles.set(1, "height_unit", "ftin")
    send(app, "/survey")
    assert app.services.bot.last.text.endswith("Weight in lb?")
    send(app, "900")
    assert "Write a weight between 45 lb and 881 lb" in app.services.bot.last.text
    send(app, "176.4")
    assert app.services.bot.last.text.endswith("Height in ft in?")
    send(app, "9 ft")
    assert "Write a height between 1 ft 8 in and 8 ft 2 in" in app.services.bot.last.text
    send(app, "5 11")
    assert app.services.bot.last.text.endswith("weight 80.01 height 180.34")


def test_weight_and_height_are_kilograms_and_centimetres_by_default(app, body):
    send(app, "/survey")
    send(app, "80,5 kg")
    send(app, "181")
    assert app.services.bot.last.text.endswith("weight 80.5 height 181.0")


def test_leaving_a_form_forgets_its_answers(app, survey):
    send(app, "/survey")
    click(app, "survey:body:sex:male")
    assert app.storage.module_state.get(1, "survey", "form.body") is not None
    click(app, "core:close")
    assert app.storage.module_state.get(1, "survey", "form.body") is None


def test_a_typed_command_forgets_the_answers_of_an_open_form(app, survey):
    send(app, "/survey")
    click(app, "survey:body:sex:male")
    app.storage.module_state.set(1, "other", "form.other", "{}")
    app.storage.module_state.set(1, "other", "kept", "1")
    send(app, "/survey")
    assert app.storage.module_state.get(1, "other", "form.other") is None
    assert app.storage.module_state.get(1, "other", "kept") == "1"
    assert '"sex"' not in (app.storage.module_state.get(1, "survey", "form.body") or "")


@pytest.fixture
def flow(app):
    module = Module(name="survey")

    @module.command("survey")
    def command_survey(ctx):
        return start(ctx)

    @module.view("start")
    def start(_ctx):
        return View(text="Start", buttons=[Button("Go", "go")])

    @module.view("other", parent="start")
    def other(_ctx):
        return View(text="Other", buttons=[Button("Go", "go")])

    @module.callback("other")
    def open_other(ctx):
        return other(ctx)

    @module.callback("go")
    def go(ctx):
        return ctx.form("first")

    @module.form("first", [Question("age", low=18, high=120)], parent="start")
    def first_done(ctx, answers):
        return ctx.form("second", known=answers.values)

    @module.form("second", [Question("sex", "choice", choices=("female", "male"))], parent="first")
    def second_done(_ctx, _answers):
        return View(text="done")

    app.registry.add(module)
    app.catalog.add("survey", "en", texts)
    return module


def test_back_from_a_form_goes_to_the_screen_that_opened_it(app, flow):
    send(app, "/survey")
    click(app, "survey:other")
    click(app, "survey:go")
    assert app.services.bot.last.text.endswith("Your age?")
    click(app, "core:back")
    assert app.services.bot.last.text.endswith("Other")


def test_a_form_opened_by_another_form_goes_back_to_where_the_first_began(app, flow):
    send(app, "/survey")
    click(app, "survey:other")
    click(app, "survey:go")
    send(app, "30")
    assert app.services.bot.last.text.endswith("Your sex?")
    click(app, "core:back")
    assert app.services.bot.last.text.endswith("Other")
    assert app.storage.module_state.get(1, "survey", "form.second") is None
