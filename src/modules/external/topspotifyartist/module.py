import random
import threading
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from core.api import Ctx, JobCtx, Module, Role, View

module = Module(name="topspotifyartist")

chart_url = "https://kworb.net/spotify/listeners.html"
artist_prefix = "https://kworb.net/spotify/"
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
    streams: int = 0
    tracks: int = 0
    is_detailed: bool = False


@dataclass
class Chart:
    artists: list[Artist] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


chart = Chart()


def http_get(url: str, headers: dict | None = None):
    return requests.get(url, headers=headers, timeout=timeout)


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


def fetch_details(artist: Artist) -> None:
    response = http_get(artist.link)
    response.raise_for_status()
    page = BeautifulSoup(response.content, "html.parser")
    cell = page.select("tbody tr td div")
    if cell:
        artist.song = cell[0].get_text()
        link = cell[0].find("a", href=True)
        artist.song_link = attribute(link, "href") if link else ""
    totals = career_totals(page)
    artist.streams = totals.get("Streams", 0)
    artist.tracks = totals.get("Tracks", 0)
    artist.is_detailed = True


def career_totals(page) -> dict[str, int]:
    found = {}
    for row in page.select("table tr"):
        cells = [cell.get_text(strip=True) for cell in row.select("td")]
        if len(cells) >= 2 and cells[0] in ("Streams", "Tracks"):
            found[cells[0]] = number(cells[1])
    return found


def number(text: str) -> int:
    digits = text.replace(",", "").strip()
    return int(digits) if digits.isdigit() else 0


def compact(value: int) -> str:
    for size, suffix in ((10 ** 9, "B"), (10 ** 6, "M"), (10 ** 3, "K")):
        if value >= size:
            return "{:.1f}".format(value / size) + suffix
    return str(value)


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
        return View(text=ctx.t("core:error"))
    ctx.state.set("target", str(random.randrange(len(artists))))
    ctx.state.set("left", str(chances))
    return game(ctx)


@module.view("game")
def game(ctx: Ctx) -> View:
    return View(text=ctx.t("how", chances=ctx.state.get("left") or str(chances)))


@module.state("game", role=Role.USER, is_background=True)
def guess(ctx: Ctx) -> View:
    target = int(ctx.state.get("target", "-1"))
    left = int(ctx.state.get("left", "0"))
    artists = chart.artists
    if not artists or not 0 <= target < len(artists) or left <= 0:
        ctx.close_screen()
        return View(text=ctx.t("core:error"))
    found = find(artists, ctx.text)
    if found is None:
        return ctx.retry(ctx.t("unknown"))
    guessed: int = found
    try:
        detail(artists, guessed, target)
    except Exception as error:
        ctx.error("Could not read the artist - " + type(error).__name__ + ".", str(error))
        return View(text=ctx.t("core:error"))
    if guessed == target:
        ctx.close_screen()
        return View(text=ctx.t("correct") + "\n" + compare(ctx, artists, guessed, target)
                    + "\n" + song_line(ctx, artists[target]) + "\n" + ctx.t("victory"))
    left -= 1
    ctx.state.set("left", str(left))
    if left > 0:
        return View(text=ctx.t("wrong", left=str(left)) + "\n" + compare(ctx, artists, guessed, target))
    ctx.close_screen()
    return View(text=ctx.t("defeat") + "\n" + describe(ctx, artists, target)
                + "\n" + song_line(ctx, artists[target]))


def find(artists: list[Artist], text: str) -> int | None:
    wanted = text.strip().casefold()
    for index, artist in enumerate(artists):
        if artist.name.casefold() == wanted:
            return index
    return None


def detail(artists: list[Artist], *indexes: int) -> None:
    for index in indexes:
        if not artists[index].is_detailed:
            fetch_details(artists[index])


def mark(guessed, wanted) -> str:
    if guessed == wanted:
        return " 🆗"
    return " ⬆️" if wanted > guessed else " ⬇️"


def top_down_mark(guessed, wanted) -> str:
    return mark(wanted, guessed)


def describe(ctx: Ctx, artists: list[Artist], index: int) -> str:
    artist = artists[index]
    return (ctx.t("nickname") + ": _" + artist.name + "_\n"
            + ctx.t("streams") + ": _" + compact(artist.streams) + "_\n"
            + ctx.t("tracks") + ": _" + str(artist.tracks) + "_\n"
            + ctx.t("listeners") + ": _#" + str(index + 1) + "_")


def compare(ctx: Ctx, artists: list[Artist], guessed: int, wanted: int) -> str:
    one, other = artists[guessed], artists[wanted]
    return (ctx.t("nickname") + ": _" + one.name + "_" + top_down_mark(one.name, other.name) + "\n"
            + ctx.t("streams") + ": _" + compact(one.streams) + "_" + mark(one.streams, other.streams) + "\n"
            + ctx.t("tracks") + ": _" + str(one.tracks) + "_" + mark(one.tracks, other.tracks) + "\n"
            + ctx.t("listeners") + ": _#" + str(guessed + 1) + "_" + top_down_mark(guessed, wanted))


def song_line(ctx: Ctx, artist: Artist) -> str:
    if not artist.song:
        return ""
    return ctx.t("song") + ": _" + artist.song + (" (" + artist.song_link + ")" if artist.song_link else "") + "_"
