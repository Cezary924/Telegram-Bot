import os
import shutil
import subprocess
from functools import cache
from urllib.parse import urlparse

import yt_dlp

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
merged_format = "bestvideo*+bestaudio/best"
single_format = "best[ext=mp4]/best"
audio_format = "bestaudio/best"
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
        if not os.path.isfile(full_path) or name.endswith(leftovers):
            continue
        return full_path if os.path.getsize(full_path) <= limit else None
    return None


def build_options(path: str, limit: int, kind: str = video) -> dict:
    options: dict[str, object] = {'quiet': True, 'noprogress': True, 'no_warnings': True, 'noplaylist': True,
                                  'outtmpl': os.path.join(path, name_template),
                                  'http_headers': {'User-Agent': browser_agent},
                                  'max_filesize': limit}
    if kind == audio:
        options['format'] = audio_format
        options['postprocessors'] = [{'key': "FFmpegExtractAudio", 'preferredcodec': "mp3",
                                      'preferredquality': "192"}]
    else:
        options['format'] = merged_format if has_ffmpeg() else single_format
        options['merge_output_format'] = "mp4"
    return options


# noinspection PyTypeChecker
def download(url: str, path: str, limit: int, kind: str = video) -> str | None:
    with yt_dlp.YoutubeDL(build_options(path, limit, kind)) as tool:
        tool.extract_info(url, download=True)
    return downloaded_file(path, limit)


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
