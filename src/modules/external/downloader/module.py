import os
import shutil
from urllib.parse import urlparse

import yt_dlp

from core.api import Ctx, Module, Role, View

module = Module(name="downloader")

priority = 20
mark = "📥 "
schemes = ("http", "https")
leftovers = (".part", ".ytdl")
name_template = "%(title).80B.%(ext)s"
merged_format = "bestvideo*+bestaudio/best"
single_format = "best[ext=mp4]/best"
browser_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")


def is_link(text: str) -> bool:
    parts = text.split()
    if len(parts) != 1:
        return False
    address = urlparse(parts[0])
    return address.scheme in schemes and bool(address.netloc)


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def hint() -> str:
    return "" if has_ffmpeg() else " ffmpeg is not installed, so only ready-made files can be taken."


def downloaded_file(path: str, limit: int) -> str | None:
    for name in sorted(os.listdir(path)):
        full_path = os.path.join(path, name)
        if not os.path.isfile(full_path) or name.endswith(leftovers):
            continue
        return full_path if os.path.getsize(full_path) <= limit else None
    return None


def build_options(path: str, limit: int) -> dict:
    return {'quiet': True, 'noprogress': True, 'no_warnings': True, 'noplaylist': True,
            'merge_output_format': "mp4", 'outtmpl': os.path.join(path, name_template),
            'format': merged_format if has_ffmpeg() else single_format,
            'http_headers': {'User-Agent': browser_agent},
            'max_filesize': limit}


# noinspection PyTypeChecker
def download(url: str, path: str, limit: int) -> str | None:
    with yt_dlp.YoutubeDL(build_options(path, limit)) as tool:
        tool.extract_info(url, download=True)
    return downloaded_file(path, limit)


@module.command("downloader", role=Role.USER)
def command_downloader(ctx: Ctx) -> View:
    return View(text=ctx.t("how"), path=[mark + ctx.t("title")])


@module.match(is_link, priority=priority, role=Role.USER, is_background=True)
def take_link(ctx: Ctx) -> View | None:
    ctx.reply(View(text=ctx.t("working"), path=[mark + ctx.t("title")]))
    with ctx.workspace() as path:
        try:
            file_path = download(ctx.text.strip(), path, ctx.file_limit)
        except Exception as error:
            ctx.error("Could not download - " + type(error).__name__ + "." + hint(), str(error))
            return View(text=ctx.t("failed"), path=[mark + ctx.t("title")])
        if file_path is None:
            return View(text=ctx.t("too_big"), path=[mark + ctx.t("title")])
        ctx.send_file(file_path, "video")
        ctx.log("Downloaded a video")
    return None
