from datetime import date, datetime, timedelta

import pytest

from core.api import Ctx, Role
from core.testing import make_callback, make_message
from modules.external.calculator import module as calculator
from modules.external.calculator.module import parse


def send(app, text: str):
    app.router.handle_message(make_message(text))


def click(app, bot, action: str):
    app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))


def labels(bot) -> list[str]:
    return [text for text, _ in bot.last.buttons]


def entries(app) -> list:
    return app.storage.database.query_all("SELECT * FROM " + app.storage.for_module("calculator").table("history") +
                                          " ORDER BY id;")


def as_user(app) -> Ctx:
    return Ctx(app.services, app.registry.get("calculator"), app.router.load_user(make_message("").from_user))


def day(offset: int = 0) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


# ----- converting -----

@pytest.mark.parametrize("text, unit, number", [
    ("5 km", "km", 5.0),
    ("5km", "km", 5.0),
    ("100 cm", "cm", 100.0),
    ("1.5h", "h", 1.5),
    ("90min", "min", 90.0),
    ("2 yr", "yr", 2.0),
    ("500 g", "g", 500.0),
    ("3 lb", "lb", 3.0),
    ("12 mo", "mo", 12.0),
])
def test_a_number_with_a_unit_is_understood(text, unit, number):
    found = parse(text)
    assert found is not None
    assert (found[1], found[2]) == (unit, number)


@pytest.mark.parametrize("text", ["5", "hello", "", "in", "https://youtu.be/5m", "km", "5 5"])
def test_anything_else_is_left_alone(text):
    assert parse(text) is None


def test_a_comma_is_a_decimal_point():
    found = parse("1,5 km")
    assert found is not None and found[2] == 1.5


@pytest.mark.parametrize("text", ["² km", "9" * 400 + " km"])
def test_what_only_looks_like_a_number_is_left_alone(text):
    assert parse(text) is None


@pytest.mark.parametrize("text, shown", [("1234567 km", "1234567 km"), ("0.00001 km", "0.00001 km")])
def test_very_big_and_very_small_amounts_keep_their_digits(app, bot, text, shown):
    send(app, text)
    assert shown in bot.last.text
    assert entries(app)[0]['query'] == shown
    assert "e+" not in bot.last.text and "e-" not in bot.last.text


def test_a_bare_number_does_not_reach_the_calculator(app, bot):
    app.storage.access.allow(1, "llm", False)
    send(app, "5")
    assert bot.last.text == "Sorry, I do not understand... 💔"


def test_a_length_is_converted_into_every_length(app, bot):
    send(app, "5 km")
    text = bot.last.text
    assert text.startswith("<b>🧮 Calculator:</b>\n\n<b>5 km</b>\n")
    assert "<i>m</i>: 5000" in text
    assert "<i>mm</i>: 5000000" in text
    assert "<i>mi</i>: 3.106855" in text


def test_a_mass_is_converted(app, bot):
    send(app, "1 kg")
    assert "<i>g</i>: 1000" in bot.last.text and "<i>dag</i>: 100\n" in bot.last.text
    assert "<i>t</i>: 0.001" in bot.last.text


def test_a_time_alone_stays_a_conversion(app, bot):
    send(app, "90 min")
    assert "<i>h</i>: 1.5" in bot.last.text and "<i>s</i>: 5400" in bot.last.text
    assert [row['kind'] for row in entries(app)] == ["conversion"]


def test_the_menu_only_tells_how_and_offers_the_history(app, bot):
    send(app, "/calculator")
    assert bot.last.text == "<b>🧮 Calculator:</b>\n\nTo calculate something, send me the calculation. " \
                            "Units are no problem for me either 😊"
    assert labels(bot) == ["📜 History", "✖️ Close"]


def test_an_arrow_converts_a_message_into_one_unit(app, bot):
    send(app, "5 km → mi")
    assert bot.last.text.endswith("<b>5 km</b>\n<i>mi</i>: 3.106855")


# ----- arithmetic -----

def test_amounts_of_one_kind_are_added_and_subtracted(app, bot):
    send(app, "2 kg + 30 dag")
    assert "Calculation: <i>2 kg + 30 dag</i>" in bot.last.text
    assert "Result: <i>2.3 kg · 230 dag</i>" in bot.last.text
    send(app, "3 km - 800 m")
    assert "Result: <i>2.2 km · 2200 m</i>" in bot.last.text
    assert [row['answer'] for row in entries(app)] == ["2.3 kg", "2.2 km"]


@pytest.mark.parametrize("text", ["5 km + 2 kg", "12.5 - 3.2", "12.50 - 3.20", "10.11 - 12.11", "od 10.11 do 12.11",
                                  "1-2", "123-456-789", "21:30", "from 9 to 5"])
def test_what_is_not_a_calculation_is_left_alone(app, bot, text):
    app.storage.access.allow(1, "llm", False)
    send(app, text)
    assert bot.last.text == "Sorry, I do not understand... 💔"


def test_a_sum_of_durations_shows_a_breakdown_and_totals(app, bot):
    send(app, "1:20 + 2:45 + 0:35")
    assert "Calculation: <i>1 h 20 min + 2 h 45 min + 35 min</i>" in bot.last.text
    assert "Result: <i>4 h 40 min</i>" in bot.last.text
    assert "Altogether: <i>4.67 h · 280 min</i>" in bot.last.text
    send(app, "300 ms + 150 ms")
    assert "Result: <i>450 ms</i>" in bot.last.text
    send(app, "2 d + 10 h 30 min")
    assert "Result: <i>2 d 10 h 30 min</i>" in bot.last.text and "<i>58.5 h · 3510 min</i>" in bot.last.text


# ----- time -----

@pytest.mark.parametrize("text", ["21:30 - 06:15", "od 21:30 do 6:15", "from 21:30 to 6:15", "21:30 → 06:15",
                                  "21:30-6:15", "Od 21:30 do 6:15"])
def test_the_difference_of_two_times_runs_into_the_next_day(app, bot, text):
    send(app, text)
    assert "From: <i>" + day() + " 21:30</i>" in bot.last.text
    assert "To: <i>" + day(1) + " 06:15</i>" in bot.last.text
    assert "Difference: <i>8 h 45 min</i>" in bot.last.text
    assert "Altogether: <i>8.75 h · 525 min</i>" in bot.last.text


def test_a_later_time_stays_on_the_same_day(app, bot):
    send(app, "06:15 - 21:30")
    assert "Difference: <i>15 h 15 min</i>" in bot.last.text and "To: <i>" + day() + " 21:30</i>" in bot.last.text


def test_the_same_time_twice_is_no_time_at_all(app, bot):
    send(app, "21:30 - 21:30")
    assert entries(app)[0]['query'] == day() + " 21:30 → " + day() + " 21:30"
    assert "0 min" in bot.last.text


def test_dates_are_taken_without_and_with_the_year(app, bot):
    send(app, "30.10.2026 21:30 - 01.11.2026 08:00")
    assert "Difference: <i>1 d 10 h 30 min</i>" in bot.last.text
    assert "Altogether: <i>34.5 h · 2070 min</i>" in bot.last.text


def test_now_stands_for_this_minute(app, bot, monkeypatch):
    monkeypatch.setattr(calculator, "this_minute", lambda: datetime(2026, 11, 10, 14, 0))
    send(app, "teraz + 2 h")
    assert "From: <i>2026-11-10 14:00</i>" in bot.last.text and "2026-11-10 16:00</i>" in bot.last.text
    send(app, "Now - 18:30")
    assert "Difference: <i>4 h 30 min</i>" in bot.last.text
    send(app, "od 8:00 do teraz")
    assert "From: <i>2026-11-10 08:00</i>" in bot.last.text and "Difference: <i>6 h</i>" in bot.last.text
    assert entries(app)[0]['query'] == "2026-11-10 14:00 + 2 h"


def test_a_date_after_new_year_comes_after_one_before_it():
    now = datetime(2026, 11, 10, 14, 0)
    assert calculator.span("31.12 23:00", "01.01 01:00", now) == (datetime(2026, 12, 31, 23, 0),
                                                                  datetime(2027, 1, 1, 1, 0))


def test_an_earlier_date_with_a_year_is_not_moved():
    now = datetime(2026, 11, 10, 14, 0)
    assert calculator.span("10.11.2026 10:00", "09.11.2026 08:00", now) == (datetime(2026, 11, 10, 10, 0),
                                                                            datetime(2026, 11, 9, 8, 0))


def test_a_time_before_a_later_date_belongs_to_the_evening_before():
    now = datetime(2026, 11, 10, 14, 0)
    assert calculator.span("21:30", "12.11.2026 08:00", now) == (datetime(2026, 11, 11, 21, 30),
                                                                 datetime(2026, 11, 12, 8, 0))


def test_a_moment_with_a_date_or_a_spelled_duration_is_moved(app, bot):
    year = date.today().year
    send(app, "30.10 21:30 + 3h 20min")
    moved = datetime(year, 10, 31, 0, 50)
    assert "Result: <i>" + moved.strftime("%A") + ", " + moved.strftime("%Y-%m-%d %H:%M") + "</i>" in bot.last.text
    send(app, "21:30 + 3 h")
    assert "From: <i>" + day() + " 21:30</i>" in bot.last.text and day(1) + " 00:30</i>" in bot.last.text
    send(app, "30.10.2026 21:30 - 3 dni")
    assert "Subtracted: <i>3 d</i>" in bot.last.text and "2026-10-27 21:30" in bot.last.text
    send(app, "30.10.2026 21:30 + 200 yr")
    assert "That is too long, keep it under 100 years" in bot.last.text


def test_a_time_plus_a_clock_asks_what_was_meant(app, bot):
    send(app, "21:30 + 1:20")
    assert "Do you mean a time of day or two durations?" in bot.last.text
    assert bot.last.buttons == [("Time 21:30 + 1 h 20 min", "calculator:either:time:1290:4800"),
                                ("Sum of durations", "calculator:either:sum:1290:4800")]
    asked = bot.last.message_id
    click(app, bot, "calculator:either:time:1290:4800")
    assert "From: <i>" + day() + " 21:30</i>" in bot.last.text and ", " + day() + " 22:50</i>" in bot.last.text
    assert (1, asked) in bot.unbuttoned
    send(app, "21:30 + 1:20")
    asked = bot.last.message_id
    click(app, bot, "calculator:either:sum:1290:4800")
    assert "Result: <i>22 h 50 min</i>" in bot.last.text
    app.router.handle_callback(make_callback("calculator:either:sum:1290:4800", message_id=asked))
    assert "Result" not in bot.last.text
    assert [row['kind'] for row in entries(app)] == ["shift", "calculation"]


def test_a_tampered_choice_does_nothing(app, bot):
    send(app, "21:30 + 1:20")
    click(app, bot, "calculator:either:time:9999:1")
    assert "Do you mean" not in bot.last.text
    assert entries(app) == []


# ----- history -----

def test_the_history_starts_empty(app, bot):
    send(app, "/calculator")
    click(app, bot, "calculator:history")
    assert bot.last.text.endswith("Nothing has been calculated yet 🤷")


def test_the_history_lists_every_kind_newest_first(app, bot):
    for text in ("5 km", "2 kg + 30 dag", "21:30 - 06:15", "30.10.2026 21:30 + 3 h"):
        send(app, text)
    send(app, "/calculator")
    click(app, bot, "calculator:history")
    assert "Page <i>1</i> of <i>1</i>, <i>4</i> calculations" in bot.last.text
    assert labels(bot)[:4] == ["2026-10-30 21:30 + 3 h = 2026-10-31 00:30",
                               day() + " 21:30 → " + day(1) + " 06:15 = 8 h 45 min",
                               "2 kg + 30 dag = 2.3 kg", "5 km"]
    click(app, bot, "calculator:entry:" + str(entries(app)[1]['id']))
    assert "Result: <i>2.3 kg · 230 dag</i>" in bot.last.text and "Counted: <i>" + day() in bot.last.text
    assert labels(bot)[0] == "🗑️ Delete"


def test_the_history_goes_a_page_at_a_time(app, bot):
    for minutes in range(10):
        send(app, str(minutes + 1) + " min + 1 h")
    send(app, "/calculator")
    click(app, bot, "calculator:history")
    assert "Page <i>1</i> of <i>2</i>, <i>10</i> calculations" in bot.last.text
    assert labels(bot)[calculator.page_size:][:2] == ["⬅️ Previous", "➡️ Next"]
    click(app, bot, "calculator:history:1")
    assert "Page <i>2</i> of <i>2</i>" in bot.last.text and labels(bot)[1] == "1 min + 1 h = 1 h 1 min"


def test_the_history_keeps_only_the_latest(app, bot, monkeypatch):
    monkeypatch.setattr(calculator, "history_size", 3)
    for minutes in range(5):
        send(app, str(minutes + 1) + " min + 1 h")
    assert [row['query'] for row in entries(app)] == ["3 min + 1 h", "4 min + 1 h", "5 min + 1 h"]


def test_a_calculation_can_be_deleted(app, bot):
    send(app, "2 kg + 30 dag")
    send(app, "3 km - 800 m")
    first = str(entries(app)[0]['id'])
    send(app, "/calculator")
    click(app, bot, "calculator:history")
    click(app, bot, "calculator:entry:" + first)
    click(app, bot, "calculator:delete:" + first)
    assert "Do you really want to delete this calculation?" in bot.last.text and "2.3 kg" in bot.last.text
    click(app, bot, "calculator:delete_confirmed:" + first)
    assert "has been deleted" in bot.last.text and "<i>1</i> calculations" in bot.last.text
    assert [row['query'] for row in entries(app)] == ["3 km - 800 m"]


def test_someone_else_cannot_touch_a_calculation(app, bot):
    send(app, "2 kg + 30 dag")
    entry = str(entries(app)[0]['id'])
    app.router.load_user(make_message("", user_id=2).from_user)
    app.storage.database.execute("UPDATE " + app.storage.for_module("calculator").table("history") +
                                 " SET user_id = 2;")
    for action in ("entry", "delete", "delete_confirmed"):
        click(app, bot, "calculator:" + action + ":" + entry)
        assert "This calculation is no longer there" in bot.last.text
    assert len(entries(app)) == 1


def test_wiping_a_user_takes_their_history_with_them(app, bot):
    send(app, "2 kg + 30 dag")
    app.storage.users.delete(1)
    assert entries(app) == []


# ----- access and languages -----

def test_a_guest_gets_no_calculation(app, bot):
    app.storage.access.allow(1, "calculator", False)
    app.storage.access.allow(1, "llm", False)
    for text in ("5 km", "21:30 - 06:15"):
        send(app, text)
        assert bot.last.text == "Sorry, I do not understand... 💔"
    send(app, "/calculator")
    assert ("🙋 Ask for access", "core:request:calculator") in bot.last.buttons


def test_it_speaks_polish(app, bot):
    app.storage.settings.set_language(1, "pl")
    send(app, "5 km")
    assert bot.last.text.startswith("<b>🧮 Kalkulator:</b>")
    send(app, "od 21:30 do 6:15")
    assert "Różnica: <i>8 h 45 min</i>" in bot.last.text and "Łącznie: <i>8.75 h · 525 min</i>" in bot.last.text
    send(app, "30.10.2026 21:30 + 3h 20min")
    assert "Wynik: <i>sobota, 2026-10-31 00:50</i>" in bot.last.text
    send(app, "21:30 + 1:20")
    assert labels(bot) == ["Godzina 21:30 + 1 h 20 min", "Suma czasów trwania"]
    send(app, "/calculator")
    assert "Aby coś obliczyć, wyślij mi działanie" in bot.last.text and labels(bot)[0] == "📜 Historia"


def test_a_screen_takes_the_message_before_the_calculator(app, bot):
    app.storage.users.set_role(1, Role.ADMIN)
    send(app, "/admin")
    for action in ["admin:users", "admin:search"]:
        click(app, bot, action)
    send(app, "5 km")
    assert "has not been found" in bot.last.text


# ----- assistant -----

def test_the_assistant_converts(app, bot):
    assert calculator.act_convert(as_user(app), "5 km", "m").result == {'amount': "5 km", 'result': "5000 m"}
    assert "3.106855 mi" in calculator.act_convert(as_user(app), "5 km", None).result['results']
    assert calculator.act_convert(as_user(app), "5 km", "kg").result == "Pick one of these units - mm, cm, in, dm, " \
                                                                        "ft, m, km, mi"
    assert calculator.act_convert(as_user(app), "a lot", None).status == "refused"


def test_the_assistant_calculates(app, bot):
    assert calculator.act_calculate(as_user(app), "2 kg + 30 dag").result == {'calculation': "2 kg + 30 dag",
                                                                              'result': "2.3 kg · 230 dag"}
    assert calculator.act_calculate(as_user(app), "1:20 + 2:45 + 0:35").result == {
        'calculation': "1 h 20 min + 2 h 45 min + 35 min", 'result': "4 h 40 min", 'hours': 4.67, 'minutes': 280}
    assert str(calculator.act_calculate(as_user(app), "5 km + 2 kg").result).startswith("These units do not go")
    assert calculator.act_calculate(as_user(app), "soon").status == "refused"


def test_the_assistant_counts_time_without_writing_anything(app, bot):
    found = calculator.act_difference(as_user(app), "22:00", "06:00").result
    assert found == {'from': day() + " 22:00", 'to': day(1) + " 06:00", 'difference': "8 h", 'hours': 8.0,
                     'minutes': 480}
    assert calculator.act_difference(as_user(app), "never", None).status == "refused"
    moved = calculator.act_shift(as_user(app), "30.10.2026 21:30", "3 h 20 min", None).result
    assert moved == {'from': "2026-10-30 21:30", 'result': "2026-10-31 00:50", 'weekday': "Saturday"}
    back = calculator.act_shift(as_user(app), "30.10.2026 21:30", "1:30", True).result
    assert back['result'] == "2026-10-30 20:00"
    assert str(calculator.act_shift(as_user(app), None, "a while", None).result).startswith("Write how long")
    assert str(calculator.act_shift(as_user(app), None, "200 yr", None).result).startswith("That is too long")
    assert entries(app) == []


def test_the_summary_tells_the_last_calculations(app, bot):
    assert calculator.summary(as_user(app)) == ""
    for text in ("5 km", "2 kg + 30 dag", "1:20 + 2:45 + 0:35", "3 km - 800 m"):
        send(app, text)
    assert calculator.summary(as_user(app)) == ("Latest calculations:\n3 km - 800 m = 2.2 km\n"
                                                "1 h 20 min + 2 h 45 min + 35 min = 4 h 40 min\n"
                                                "2 kg + 30 dag = 2.3 kg")
