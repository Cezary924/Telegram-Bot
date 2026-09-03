import base64
import random
import threading
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from core.api import Ctx, JobCtx, Module, Role, View

module = Module(name="topspotifyartist", tokens=["spotify_id", "spotify_secret"])

chart_url = "https://kworb.net/spotify/listeners.html"
artist_prefix = "https://kworb.net/spotify/"
token_url = "https://accounts.spotify.com/api/token"
api_url = "https://api.spotify.com/v1/artists/"
timeout = 10
chart_size = 200
chances = 5
refresh_hours = 24


@dataclass
class Artist:
    name: str
    link: str
    song: str = ""
    song_link: str = ""
    genre: str = ""
    is_detailed: bool = False


@dataclass
class Chart:
    artists: list[Artist] = field(default_factory=list)
    token: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)


chart = Chart()


def http_get(url: str, headers: dict | None = None):
    return requests.get(url, headers=headers, timeout=timeout)


def http_post(url: str, data: dict, headers: dict):
    return requests.post(url, data=data, headers=headers, timeout=timeout)


def attribute(tag, name: str) -> str:
    value = tag.get(name)
    return value if isinstance(value, str) else ""


def fetch_chart() -> list[Artist]:
    response = http_get(chart_url)
    response.raise_for_status()
    table = BeautifulSoup(response.content, "html.parser").find(class_="sortable")
    if table is None:
        raise ValueError("the chart page carries no table")
    artists = []
    for row in table.select("tbody tr"):
        cell = row.find(class_="text")
        links = cell.select("a") if cell else []
        if links:
            artists.append(Artist(links[0].get_text(), artist_prefix + attribute(links[0], "href")))
        if len(artists) >= chart_size:
            break
    return artists


def fetch_token(ctx: Ctx) -> str:
    secret = ctx.token("spotify_id") + ":" + ctx.token("spotify_secret")
    headers = {'Authorization': "Basic " + base64.b64encode(secret.encode("ascii")).decode("ascii")}
    response = http_post(token_url, {'grant_type': "client_credentials"}, headers)
    response.raise_for_status()
    return str(response.json()['access_token'])


def fetch_details(ctx: Ctx, artist: Artist) -> None:
    response = http_get(artist.link)
    response.raise_for_status()
    cell = BeautifulSoup(response.content, "html.parser").select("tbody tr td div")
    if cell:
        artist.song = cell[0].get_text()
        link = cell[0].find("a", href=True)
        artist.song_link = attribute(link, "href") if link else ""
    artist.genre = fetch_genre(ctx, artist)
    artist.is_detailed = True


def fetch_genre(ctx: Ctx, artist: Artist) -> str:
    identifier = artist.link.split("/artist/")[-1].split("_songs")[0]
    for attempt in range(2):
        if not chart.token or attempt:
            chart.token = fetch_token(ctx)
        response = http_get(api_url + identifier, {'Authorization': "Bearer " + chart.token})
        if response.status_code == 200:
            genres = response.json().get('genres') or []
            return str(genres[0]).capitalize() if genres else ""
    return ""


def ready_chart() -> list[Artist]:
    with chart.lock:
        if not chart.artists:
            chart.artists = fetch_chart()
    return chart.artists


@module.job(interval=refresh_hours * 3600, name="refresh")
def refresh_chart(ctx: JobCtx) -> None:
    try:
        artists = fetch_chart()
    except Exception as error:
        ctx.error("Could not refresh the chart - " + type(error).__name__ + ".", str(error))
        return
    with chart.lock:
        chart.artists = artists
    ctx.log("Chart refreshed with " + str(len(artists)) + " artists")


@module.command("topspotifyartist", role=Role.USER, is_background=True)
def command_topspotifyartist(ctx: Ctx) -> View:
    try:
        artists = ready_chart()
    except Exception as error:
        ctx.error("Could not read the chart - " + type(error).__name__ + ".", str(error))
        return View(text=ctx.t("core:error"), path=[ctx.t("title")])
    ctx.state.set("target", str(random.randrange(len(artists))))
    ctx.state.set("left", str(chances))
    return game(ctx)


@module.view("game")
def game(ctx: Ctx) -> View:
    return View(text=ctx.t("how", chances=str(chances)), path=[ctx.t("title")])


@module.state("game", role=Role.USER, is_background=True)
def guess(ctx: Ctx) -> View:
    target = int(ctx.state.get("target", "-1"))
    left = int(ctx.state.get("left", "0"))
    artists = chart.artists
    if not artists or not 0 <= target < len(artists) or left <= 0:
        ctx.close_screen()
        return View(text=ctx.t("core:error"), path=[ctx.t("title")])
    found = find(artists, ctx.text)
    if found is None:
        return View(text=ctx.t("unknown"), path=[ctx.t("title")])
    guessed: int = found
    try:
        detail(ctx, artists, guessed, target)
    except Exception as error:
        ctx.error("Could not read the artist - " + type(error).__name__ + ".", str(error))
        return View(text=ctx.t("core:error"), path=[ctx.t("title")])
    if guessed == target:
        ctx.close_screen()
        return View(text=ctx.t("correct") + "\n" + compare(ctx, artists, guessed, target)
                    + "\n" + song_line(ctx, artists[target]) + "\n" + ctx.t("victory"),
                    path=[ctx.t("title")])
    left -= 1
    ctx.state.set("left", str(left))
    if left > 0:
        return View(text=ctx.t("wrong", left=str(left)) + "\n" + compare(ctx, artists, guessed, target),
                    path=[ctx.t("title")])
    ctx.close_screen()
    return View(text=ctx.t("defeat") + "\n" + describe(ctx, artists, target)
                + "\n" + song_line(ctx, artists[target]), path=[ctx.t("title")])


def find(artists: list[Artist], text: str) -> int | None:
    wanted = text.strip().casefold()
    for index, artist in enumerate(artists):
        if artist.name.casefold() == wanted:
            return index
    return None


def detail(ctx: Ctx, artists: list[Artist], *indexes: int) -> None:
    for index in indexes:
        if not artists[index].is_detailed:
            fetch_details(ctx, artists[index])


def mark(guessed, wanted) -> str:
    return " 🆗" if guessed == wanted else (" ⬆️" if guessed > wanted else " ⬇️")


def describe(ctx: Ctx, artists: list[Artist], index: int) -> str:
    artist = artists[index]
    return (ctx.t("nickname") + ": _" + artist.name + "_\n"
            + ctx.t("genre") + ": _" + (artist.genre or "???") + "_\n"
            + ctx.t("listeners") + ": _#" + str(index + 1) + "_")


def compare(ctx: Ctx, artists: list[Artist], guessed: int, wanted: int) -> str:
    one, other = artists[guessed], artists[wanted]
    return (ctx.t("nickname") + ": _" + one.name + "_" + mark(one.name, other.name) + "\n"
            + ctx.t("genre") + ": _" + (one.genre or "???") + "_"
            + (" 🆗" if one.genre == other.genre else " 🆖") + "\n"
            + ctx.t("listeners") + ": _#" + str(guessed + 1) + "_" + mark(guessed, wanted))


def song_line(ctx: Ctx, artist: Artist) -> str:
    if not artist.song:
        return ""
    return ctx.t("song") + ": _" + artist.song + (" (" + artist.song_link + ")" if artist.song_link else "") + "_"
