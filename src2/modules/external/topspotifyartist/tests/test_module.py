import pytest

from core.api import Role
from core.testing import make_message
from modules.external.topspotifyartist import module as game


@pytest.fixture(autouse=True)
def empty_chart():
    game.chart.artists = []
    game.chart.token = ""
    yield
    game.chart.artists = []


def artist(name: str, genre: str = "Pop", song: str = "A song") -> game.Artist:
    return game.Artist(name=name, link="https://kworb.net/spotify/artist/" + name,
                       song=song, song_link="https://open.spotify.com/" + name,
                       genre=genre, is_detailed=True)


@pytest.fixture
def playing(app, monkeypatch):
    monkeypatch.setattr(game, "fetch_chart", lambda: [
        artist("Bad Bunny", "Reggaeton"), artist("Drake", "Rap"), artist("Taylor Swift", "Pop")])
    monkeypatch.setattr(game, "fetch_details", lambda ctx, wanted: None)
    monkeypatch.setattr(game.random, "randrange", lambda size: 1)
    app.storage.settings.set_language(1, "en")
    return app


def start(app):
    app.router.handle_message(make_message("/topspotifyartist"))
    app.router.wait_for_tasks()


def say(app, text: str):
    app.router.handle_message(make_message(text))
    app.router.wait_for_tasks()


def test_the_module_declares_only_the_spotify_tokens(app):
    assert app.registry.get("topspotifyartist").tokens == ["spotify_id", "spotify_secret"]


def test_starting_a_round_opens_a_screen(playing, bot):
    start(playing)
    assert bot.last.text.startswith("*ᯤ Guess the Spotify artist:*")
    assert "You have 5 chances" in bot.last.text
    assert playing.storage.navigation.depth(1) == 1
    assert playing.storage.module_state.get(1, "topspotifyartist", "target") == "1"


def test_an_unknown_name_costs_nothing(playing, bot):
    start(playing)
    say(playing, "Nobody At All")
    assert "I do not know this artist" in bot.last.text
    assert playing.storage.module_state.get(1, "topspotifyartist", "left") == "5"


def test_a_wrong_guess_shows_the_hints(playing, bot):
    start(playing)
    say(playing, "Taylor Swift")
    text = bot.last.text
    assert "Wrong! 👎 Chances left: 4" in text
    assert "Nickname: _Taylor Swift_ ⬆️" in text
    assert "Genre: _Pop_ 🆖" in text
    assert "Monthly listeners: _#3_ ⬆️" in text


def test_the_hints_point_the_other_way_too(playing, bot):
    start(playing)
    say(playing, "Bad Bunny")
    text = bot.last.text
    assert "Nickname: _Bad Bunny_ ⬇️" in text
    assert "Monthly listeners: _#1_ ⬇️" in text


def test_guessing_right_ends_the_round(playing, bot):
    start(playing)
    say(playing, "Drake")
    text = bot.last.text
    assert "Correct! 👍" in text
    assert "Nickname: _Drake_ 🆗" in text
    assert "Most streamed song: _A song (https://open.spotify.com/Drake)_" in text
    assert "You have guessed the artist" in text
    assert playing.storage.navigation.depth(1) == 0


def test_the_name_is_matched_without_case(playing, bot):
    start(playing)
    say(playing, "  drake  ")
    assert "Correct! 👍" in bot.last.text


def test_running_out_of_chances_reveals_the_artist(playing, bot):
    start(playing)
    for _ in range(5):
        say(playing, "Taylor Swift")
    text = bot.last.text
    assert "you have not guessed the artist" in text
    assert "Nickname: _Drake_" in text
    assert "Most streamed song: _A song" in text
    assert playing.storage.navigation.depth(1) == 0


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
    say(playing, "Drake")
    assert "Dobrze! 👍" in bot.last.text


def test_the_chart_is_fetched_once(playing, bot, monkeypatch):
    calls = []
    monkeypatch.setattr(game, "fetch_chart", lambda: calls.append(1) or [artist("Drake")])
    start(playing)
    start(playing)
    assert len(calls) == 1


def test_the_job_refreshes_the_chart(app, monkeypatch, capsys):
    monkeypatch.setattr(game, "fetch_chart", lambda: [artist("Drake"), artist("Sia")])
    name, handler, interval = [job for job in app.scheduler._jobs if "topspotifyartist" in job[0]][0]
    assert interval == 24 * 3600
    handler()
    assert len(game.chart.artists) == 2
    assert "Chart refreshed with 2 artists" in capsys.readouterr().out


def test_a_failing_refresh_keeps_the_old_chart(app, monkeypatch, capsys):
    game.chart.artists = [artist("Drake")]

    def refuse():
        raise ConnectionError("no network")

    monkeypatch.setattr(game, "fetch_chart", refuse)
    _, handler, _ = [job for job in app.scheduler._jobs if "topspotifyartist" in job[0]][0]
    handler()
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
  <tr><td class="text"><a href="artist/aaa_songs.html">Bad Bunny</a></td></tr>
  <tr><td class="text"><a href="artist/bbb_songs.html">Drake</a></td></tr>
  <tr><td class="nothing">no link here</td></tr>
</tbody></table>
"""

artist_page = b"""
<table><tbody><tr><td><div><a href="https://open.spotify.com/track/1">A song</a></div></td></tr></tbody></table>
"""


def test_the_chart_page_is_parsed(monkeypatch):
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=chart_page))
    artists = game.fetch_chart()
    assert [one.name for one in artists] == ["Bad Bunny", "Drake"]
    assert artists[0].link == "https://kworb.net/spotify/artist/aaa_songs.html"


def test_the_chart_stops_at_the_size_limit(monkeypatch):
    monkeypatch.setattr(game, "chart_size", 1)
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=chart_page))
    assert len(game.fetch_chart()) == 1


def test_the_artist_page_gives_the_song_and_the_genre(app, monkeypatch):
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=artist_page))
    monkeypatch.setattr(game, "fetch_genre", lambda ctx, wanted: "Rap")
    drake = game.Artist("Drake", "https://kworb.net/spotify/artist/bbb_songs.html")
    game.fetch_details(context_for(app), drake)
    assert drake.song == "A song"
    assert drake.song_link == "https://open.spotify.com/track/1"
    assert drake.genre == "Rap" and drake.is_detailed


def test_the_genre_comes_from_spotify(app, monkeypatch):
    monkeypatch.setattr(game, "fetch_token", lambda ctx: "a-token")
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(payload={'genres': ["hip hop"]}))
    drake = game.Artist("Drake", "https://kworb.net/spotify/artist/bbb_songs.html")
    assert game.fetch_genre(context_for(app), drake) == "Hip hop"


def test_an_artist_without_a_genre(app, monkeypatch):
    monkeypatch.setattr(game, "fetch_token", lambda ctx: "a-token")
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(payload={'genres': []}))
    drake = game.Artist("Drake", "https://kworb.net/spotify/artist/bbb_songs.html")
    assert game.fetch_genre(context_for(app), drake) == ""


def test_a_stale_token_is_refreshed_once(app, monkeypatch):
    tokens = []
    answers = [Answer(status=401), Answer(payload={'genres': ["pop"]})]
    monkeypatch.setattr(game, "fetch_token", lambda ctx: tokens.append(1) or "a-token")
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: answers.pop(0))
    drake = game.Artist("Drake", "https://kworb.net/spotify/artist/bbb_songs.html")
    assert game.fetch_genre(context_for(app), drake) == "Pop"
    assert len(tokens) == 2


def context_for(app):
    from core.api import Ctx, User
    person = User(1, "First", "Last", "username", Role.USER, "en", True)
    return Ctx(app.services, app.registry.get("topspotifyartist"), person)


def test_a_page_without_the_table_is_refused(monkeypatch):
    monkeypatch.setattr(game, "http_get", lambda url, headers=None: Answer(content=b"<html></html>"))
    with pytest.raises(ValueError):
        game.fetch_chart()
