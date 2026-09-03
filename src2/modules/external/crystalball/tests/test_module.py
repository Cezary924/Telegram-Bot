import pytest

from core.api import Role
from core.testing import make_message
from modules.external.crystalball import module as crystalball


@pytest.fixture
def answers(app):
    return [app.catalog.text("crystalball", verdict + "." + str(number), "en")
            for verdict, _ in crystalball.verdicts
            for number in range(1, crystalball.answers_per_verdict + 1)]


def test_the_module_is_external(app):
    assert not app.registry.get("crystalball").is_internal


def test_it_answers_something_the_oracle_knows(app, bot, answers):
    app.router.handle_message(make_message("/crystalball"))
    body = bot.last.text.split("\n\n")[1]
    assert body[:-2] in answers


def test_every_answer_carries_its_mark(app, bot):
    marks = {mark for _, mark in crystalball.verdicts}
    for _ in range(30):
        app.router.handle_message(make_message("/crystalball"))
        assert bot.last.text[-1] in marks


def test_the_heading_names_the_oracle(app, bot):
    app.router.handle_message(make_message("/crystalball"))
    assert bot.last.text.startswith("*🔮 Crystal ball:*\n\n")


def test_it_speaks_polish(app, bot):
    app.storage.settings.set_language(1, "pl")
    app.router.handle_message(make_message("/crystalball"))
    assert bot.last.text.startswith("*🔮 Kryształowa kula:*")


def test_a_guest_may_not_ask(app, bot):
    app.storage.users.set_role(1, Role.GUEST)
    app.router.handle_message(make_message("/crystalball"))
    assert bot.last.text.startswith("Sorry, you cannot use this command")


def test_it_is_not_a_screen(app):
    app.router.handle_message(make_message("/crystalball"))
    assert app.storage.navigation.depth(1) == 0


def test_every_verdict_shows_up_eventually(app, bot, monkeypatch):
    seen = set()
    for index in range(len(crystalball.verdicts)):
        monkeypatch.setattr(crystalball.random, "choice", lambda options, chosen=index: options[chosen])
        monkeypatch.setattr(crystalball.random, "randint", lambda low, high: 1)
        app.router.handle_message(make_message("/crystalball"))
        seen.add(bot.last.text[-1])
    assert seen == {mark for _, mark in crystalball.verdicts}
