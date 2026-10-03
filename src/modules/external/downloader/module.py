import copy
import os
import re
import shutil
import subprocess
from functools import cache
from urllib.parse import urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from core.api import Button, Ctx, Module, Role, View, labelled

module = Module(name="downloader",
                icons={'name': "📥", 'format_video': "🎬", 'format_audio': "🎵", 'format_ask': "❓",
                       'settings_button': "⚙️"},
                endings={'how': "😊", 'working': "⏳", 'failed': "💔", 'too_big': "💔"})

priority = 20
mark = "📥 "
schemes = ("http", "https")
leftovers = (".part", ".ytdl")
name_template = "%(title).80B.%(ext)s"
audio_format = "bestaudio/best"
sound_template = "%(artist).60B - %(track).80B.%(ext)s"
thumbnails = (".jpg", ".jpeg", ".png", ".webp")
top_bitrate = 192
lowest_bitrate = 32
fallback_heights = (1080, 720, 480, 360, 240, 144)
redirects = 5
video = "video"
audio = "audio"
ask = "ask"
choices = (video, audio, ask)
format_key = "format"
link_prefix = "link."
browser_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


def is_link(text: str) -> bool:
    parts = text.split()
    if len(parts) != 1:
        return False
    address = urlparse(parts[0])
    return address.scheme in schemes and bool(address.netloc)


@cache
def has_ffmpeg() -> bool:
    found = shutil.which("ffmpeg")
    if found is None:
        return False
    try:
        return subprocess.run([found, "-version"], capture_output=True, timeout=10).returncode == 0
    except OSError:
        return False


def hint() -> str:
    return "" if has_ffmpeg() else " (ffmpeg is missing or does not run, so only ready-made files can be taken)"


def downloaded_file(path: str, limit: int) -> str | None:
    for name in sorted(os.listdir(path)):
        full_path = os.path.join(path, name)
        if not os.path.isfile(full_path) or name.endswith(leftovers) or name.endswith(thumbnails):
            continue
        return full_path if os.path.getsize(full_path) <= limit else None
    return None


def clear(path: str) -> None:
    for name in os.listdir(path):
        full_path = os.path.join(path, name)
        if os.path.isfile(full_path):
            os.remove(full_path)


def build_options(path: str, limit: int, kind: str = video) -> dict:
    options: dict[str, object] = {'quiet': True, 'noprogress': True, 'no_warnings': True, 'noplaylist': True,
                                  'outtmpl': os.path.join(path, name_template),
                                  'http_headers': {'User-Agent': browser_agent},
                                  'max_filesize': limit}
    if kind == audio:
        options['format'] = audio_format
        options['outtmpl'] = os.path.join(path, sound_template)
        options['writethumbnail'] = True
        options['postprocessors'] = [
            {'key': "FFmpegExtractAudio", 'preferredcodec': "mp3", 'preferredquality': str(top_bitrate)},
            {'key': "FFmpegMetadata"},
            {'key': "FFmpegThumbnailsConvertor", 'format': "jpg"},
            {'key': "EmbedThumbnail"}]
    else:
        options['format'] = video_format()
        options['merge_output_format'] = "mp4"
    return options


def video_format(height: int | None = None) -> str:
    cap = "[height<=" + str(height) + "]" if height else ""
    return "bv*" + cap + "+ba/b" + cap if has_ffmpeg() else "b" + cap + "[ext=mp4]/b" + cap


def heights(info: dict) -> list[int]:
    found = {one.get('height') for one in info.get('formats') or [] if one.get('height')}
    return sorted(found, reverse=True)[1:] if found else list(fallback_heights)


def estimated_size(selected: dict) -> int | None:
    total = 0
    for part in selected.get('requested_formats') or [selected]:
        size = part.get('filesize') or part.get('filesize_approx')
        if not isinstance(size, (int, float)):
            return None
        total += int(size)
    return total


def bitrate(duration, limit: int) -> int:
    if not duration:
        return top_bitrate
    fitting = int(limit * 8 * 0.95 / duration / 1000)
    return max(lowest_bitrate, min(top_bitrate, fitting))


suffix_pattern = re.compile(r"\s*[(\[][^)\]]*(official|video|audio|lyric|visuali[sz]er|hd|4k)[^)\]]*[)\]]",
                            re.IGNORECASE)


def tags(info: dict) -> tuple[str, str]:
    title = (info.get('title') or "").strip()
    if info.get('artist') and info.get('track'):
        return str(info['artist']), str(info['track'])
    if " - " in title:
        artist, track = title.split(" - ", 1)
        return artist.strip(), suffix_pattern.sub("", track).strip() or track.strip()
    channel = info.get('channel') or info.get('uploader') or ""
    return channel.removesuffix(" - Topic").strip(), suffix_pattern.sub("", title).strip() or title


# noinspection PyTypeChecker
def resolve(options: dict, info: dict, wanted: str) -> dict | None:
    with YoutubeDL({**options, 'format': wanted}) as tool:
        try:
            return dict(tool.process_ie_result(copy.deepcopy(info), download=False))
        except DownloadError:
            return None


# noinspection PyTypeChecker
def fetch(options: dict, info: dict) -> None:
    with YoutubeDL(options) as tool:
        tool.process_ie_result(copy.deepcopy(info), download=True)


def video_formats(options: dict, info: dict, limit: int) -> list[str]:
    fitting = []
    for height in [None] + heights(info):
        wanted = video_format(height)
        selected = resolve(options, info, wanted)
        if selected is None:
            continue
        size = estimated_size(selected)
        if size is None or size <= limit:
            fitting.append(wanted)
    return fitting


# noinspection PyTypeChecker
def look_up(options: dict, url: str) -> dict:
    with YoutubeDL(options) as tool:
        info = dict(tool.extract_info(url, download=False, process=False))
        for _ in range(redirects):
            if info.get('_type') != "url":
                break
            info = dict(tool.extract_info(info['url'], download=False, process=False))
    return info


def download(url: str, path: str, limit: int, kind: str = video) -> str | None:
    options = build_options(path, limit, kind)
    info = look_up(options, url)
    if kind == audio:
        info['artist'], info['track'] = tags(info)
        options['postprocessors'][0]['preferredquality'] = str(bitrate(info.get('duration'), limit))
        fetch(options, info)
        return downloaded_file(path, limit)
    for wanted in video_formats(options, info, limit):
        fetch({**options, 'format': wanted}, info)
        found = downloaded_file(path, limit)
        if found is not None:
            return found
        clear(path)
    return None


def chosen(ctx: Ctx) -> str:
    wanted = ctx.state.get(format_key)
    return wanted if wanted in choices else video


def deliver(ctx: Ctx, url: str, kind: str) -> View | None:
    ctx.reply(View(text=ctx.t("working")))
    with ctx.workspace() as path:
        try:
            file_path = download(url, path, ctx.file_limit, kind)
        except Exception as error:
            ctx.error("Could not download - " + type(error).__name__ + hint(), str(error))
            return View(text=ctx.t("failed"))
        if file_path is None:
            return View(text=ctx.t("too_big"))
        ctx.send_file(file_path, kind)
        ctx.log("Downloaded " + ("a video" if kind == video else "a sound"))
    return None


@module.command("downloader", role=Role.USER)
def command_downloader(ctx: Ctx) -> View:
    return View(text=ctx.t("how"), buttons=[Button.settings(ctx.t("settings_button"), module.name)])


@module.match(is_link, priority=priority, role=Role.USER, is_background=True)
def take_link(ctx: Ctx) -> View | None:
    url = ctx.text.strip()
    if chosen(ctx) != ask:
        return deliver(ctx, url, chosen(ctx))
    asked = str(ctx.message.message_id) if ctx.message is not None else "0"
    ctx.state.set(link_prefix + asked, url)
    return choice(ctx, asked)


@module.view("choice")
def choice(ctx: Ctx, asked: str = "") -> View:
    asked = asked or (ctx.arguments[-1] if ctx.arguments else "")
    return View(text=ctx.t("choose"),
                buttons=[Button(ctx.t("format_video"), "take", video, asked),
                         Button(ctx.t("format_audio"), "take", audio, asked)],
                argument=asked, columns=2)


@module.callback("take", role=Role.USER, is_background=True)
def take_choice(ctx: Ctx) -> View | None:
    kind, asked = (ctx.arguments + ("", ""))[:2]
    url = ctx.state.get(link_prefix + asked)
    if kind not in (video, audio) or not url:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.state.delete(link_prefix + asked)
    ctx.close_screen()
    return deliver(ctx, url, kind)


@module.settings(role=Role.USER)
def settings(ctx: Ctx) -> View:
    current = labelled(ctx.t("settings_current"), ctx.t("format_" + chosen(ctx)))
    return View(text=ctx.t("settings_text") + "\n\n" + current,
                buttons=[Button(ctx.t("format_" + one), "format", one) for one in choices])


@module.callback("format", role=Role.USER)
def set_format(ctx: Ctx) -> View:
    wanted = ctx.arguments[0] if ctx.arguments else ""
    if wanted not in choices:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.state.set(format_key, wanted)
    ctx.log("Download format set to " + wanted)
    return settings(ctx)
