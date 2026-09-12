import pytest

from core.api import Role
from core.testing import make_message, not_none
from modules.external.topspotifyartist import module as game


@pytest.fixture(autouse=True)
def empty_chart():
    game.chart.artists = []
    game.chart.token = ""
    yield
    game.chart.artists = []


def artist(name: str, streams: int = 10 ** 9, tracks: int = 50, song: str = "A song") -> game.Artist:
    slug = name.replace(" ", "")
    return game.Artist(name=name, link="https://kworb.net/spotify/artist/" + slug,
                       song=song, song_link="https://open.spotify.com/" + slug,
                       streams=streams, tracks=tracks, is_detailed=True)


@pytest.fixture
def playing(app, monkeypatch):
    monkeypatch.setattr(game, "fetch_chart", lambda: [
        artist("Ariana Grande", streams=10 ** 9, tracks=40),
        artist("Demi Lovato", streams=3 * 10 ** 9, tracks=120)])
    monkeypatch.setattr(game, "fetch_details", lambda wanted: None)
    monkeypatch.setattr(game.random, "randrange", lambda size: 1)
    app.storage.settings.set_language(1, "en")
    return app


def start(app):
    app.router.handle_message(make_message("/topspotifyartist"))
    app.router.wait_for_tasks()


def say(app, text: str):
    app.router.handle_message(make_message(text))
    app.router.wait_for_tasks()


def test_the_module_asks_for_no_tokens(app):
    assert app.registry.get("topspotifyartist").tokens == []


def test_starting_a_round_opens_a_screen(playing, bot):
    start(playing)
    assert bot.last.text.startswith("*ᯤ Guess the Spotify artist:*")
    assert "You have 5 chances" in bot.last.text
    assert playing.storage.navigation.current(1) is not None
    assert playing.storage.module_state.get(1, "topspotifyartist", "target") == "1"


def test_an_unknown_name_costs_nothing(playing, bot):
    start(playing)
    say(playing, "Nobody At All")
    assert "I do not know this artist" in bot.last.text
    assert playing.storage.module_state.get(1, "topspotifyartist", "left") == "5"


def test_an_unknown_name_keeps_the_board_asking(playing, bot):
    start(playing)
    say(playing, "Ariana Grande")
    say(playing, "Nobody At All")
    assert "I do not know this artist" in bot.last.text
    assert "You have 4 chances" in bot.last.text
    assert playing.storage.navigation.current(1)['view'] == "game"


def test_a_wrong_guess_shows_the_hints(playing, bot):
    start(playing)
    say(playing, "Ariana Grande")
    text = bot.last.text
    assert "Wrong! 👎 Chances left: 4" in text
    assert "Nickname: _Ariana Grande_ ⬇️" in text
    assert "Streams in total: _1.0B_ ⬆️" in text
    assert "Number of tracks: _40_ ⬆️" in text
    assert "Monthly listeners: _#1_ ⬇️" in text


def test_the_hints_point_the_other_way_too(playing, bot, monkeypatch):
    monkeypatch.setattr(game.random, "randrange", lambda size: 0)
    start(playing)
    say(playing, "Demi Lovato")
    text = bot.last.text
    assert "Nickname: _Demi Lovato_ ⬆️" in text
    assert "Streams in total: _3.0B_ ⬇️" in text
    assert "Number of tracks: _120_ ⬇️" in text
    assert "Monthly listeners: _#2_ ⬆️" in text


def test_guessing_right_ends_the_round(playing, bot):
    start(playing)
    say(playing, "Demi Lovato")
    text = bot.last.text
    assert "Correct! 👍" in text
    assert "Nickname: _Demi Lovato_ 🆗" in text
    assert "Most streamed song: _A song (https://open.spotify.com/DemiLovato)_" in text
    assert "You have guessed the artist" in text
    assert playing.storage.navigation.current(1) is None


def test_the_name_is_matched_without_case(playing, bot):
    start(playing)
    say(playing, "  demi lovato  ")
    assert "Correct! 👍" in bot.last.text


def test_running_out_of_chances_reveals_the_artist(playing, bot):
    start(playing)
    for _ in range(5):
        say(playing, "Ariana Grande")
    text = bot.last.text
    assert "you have not guessed the artist" in text
    assert "Nickname: _Demi Lovato_" in text
    assert "Most streamed song: _A song" in text
    assert playing.storage.navigation.current(1) is None


def test_a_broken_chart_says_so(app, bot, monkeypatch):
    def refuse():
        raise ConnectionError("no network")

    monkeypatch.setattr(game, "fetch_chart", refuse)
    app.router.handle_message(make_message("/topspotifyartist"))
    app.router.wait_for_tasks()
    assert bot.last.text.endswith("Error. Please, try again later.")


def test_a_guest_may_not_play(app, bot):
    app.storage.users.set_role(1, Role.GUEST)
    app.router.handle_message(make_message("/topspotifyartist"))
    app.router.wait_for_tasks()
    assert bot.last.text.startswith("Sorry, you cannot use this command")


def test_it_speaks_polish(playing, bot):
    playing.storage.settings.set_language(1, "pl")
    start(playing)
    assert bot.last.text.startswith("*ᯤ Zgadnij artystę Spotify:*")
    say(playing, "Demi Lovato")
    assert "Dobrze! 👍" in bot.last.text


def test_the_chart_is_fetched_once(playing, bot, monkeypatch):
    calls = []
    monkeypatch.setattr(game, "fetch_chart", lambda: calls.append(1) or [artist("Demi Lovato")])
    start(playing)
    start(playing)
    assert len(calls) == 1


def test_the_job_refreshes_the_chart(app, monkeypatch, capsys):
    monkeypatch.setattr(game, "fetch_chart", lambda: [artist("Demi Lovato"), artist("Ariana Grande")])
    job = not_none(app.scheduler.find("topspotifyartist.refresh"))
    assert job.interval == 24 * 3600
    job.handler()
    assert len(game.chart.artists) == 2
    assert "Chart refreshed with 2 artists" in capsys.readouterr().out


def test_a_failing_refresh_keeps_the_old_chart(app, monkeypatch, capsys):
    game.chart.artists = [artist("Demi Lovato")]

    def refuse():
        raise ConnectionError("no network")

    monkeypatch.setattr(game, "fetch_chart", refuse)
    not_none(app.scheduler.find("topspotifyartist.refresh")).handler()
    assert len(game.chart.artists) == 1
    assert "Could not refresh the chart - ConnectionError." in capsys.readouterr().out


class Answer:
    def __init__(self, content: bytes = b"", payload=None, status: int = 200):
        self.content = content
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code != 200:
            raise ConnectionError("status " + str(self.status_code))

    def json(self):
        return self._payload


chart_page = b"""
<table class="sortable"><tbody>
  <tr><td class="text"><a href="artist/aaa_songs.html">Ariana Grande</a></td></tr>
  <tr><td class="text"><a href="artist/bbb_songs.html">Demi Lovato</a></td></tr>
  <tr><td class="nothing">no link here</td></tr>
</tbody></table>
"""

artist_page = b"""
<table><tr><td>Streams</td><td>58,285,640,135</td></tr>
       <tr><td>Tracks</td><td>124</td></tr></table>
<table><tbody><tr><td><div><a href="https://open.spotify.com/track/1">A song</a></div></td></tr></tbody></table>
"""


def test_the_chart_page_is_parsed(monkeypatch):
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=chart_page))
    artists = game.fetch_chart()
    assert [one.name for one in artists] == ["Ariana Grande", "Demi Lovato"]
    assert artists[0].link == "https://kworb.net/spotify/artist/aaa_songs.html"


def test_the_chart_stops_at_the_size_limit(monkeypatch):
    monkeypatch.setattr(game, "chart_size", 1)
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=chart_page))
    assert len(game.fetch_chart()) == 1


def test_the_artist_page_gives_the_song_and_the_career(monkeypatch):
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=artist_page))
    demi = game.Artist("Demi Lovato", "https://kworb.net/spotify/artist/bbb_songs.html")
    game.fetch_details(demi)
    assert demi.song == "A song"
    assert demi.song_link == "https://open.spotify.com/track/1"
    assert (demi.streams, demi.tracks) == (58285640135, 124)
    assert demi.is_detailed


def test_a_page_without_the_totals_leaves_them_at_zero(monkeypatch):
    page = b"<table><tbody><tr><td><div>A song</div></td></tr></tbody></table>"
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=page))
    demi = game.Artist("Demi Lovato", "https://kworb.net/spotify/artist/bbb_songs.html")
    game.fetch_details(demi)
    assert (demi.streams, demi.tracks) == (0, 0)


@pytest.mark.parametrize("text, value", [
    ("58,285,640,135", 58285640135), ("124", 124), ("", 0), ("n/a", 0), (" 1,000 ", 1000),
])
def test_a_number_survives_the_separators(text, value):
    assert game.number(text) == value


@pytest.mark.parametrize("value, shown", [
    (58285640135, "58.3B"), (130039198417, "130.0B"), (5_400_000, "5.4M"), (1200, "1.2K"), (7, "7"),
])
def test_a_big_number_is_shortened(value, shown):
    assert game.compact(value) == shown


def test_a_page_without_the_table_is_refused(monkeypatch):
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=b"<html></html>"))
    with pytest.raises(ValueError):
        game.fetch_chart()
