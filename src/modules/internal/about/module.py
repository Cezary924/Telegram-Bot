from datetime import datetime
from urllib.parse import parse_qs, urlparse

import requests

from core.api import AdvancedCtx, Module, View
from core.version import Version

module = Module(name="about")

first_year = 2023
timeout = 10


@module.command("about", is_background=True)
def command_about(ctx: AdvancedCtx) -> View:
    return View(
        text="*" + ctx.config.bot_name + "*\n"
             + line(ctx, "labels.description", ctx.t("tagline"))
             + line(ctx, "labels.creator", "@" + ctx.config.github_username)
             + line(ctx, "labels.version", str(ctx.version))
             + line(ctx, "labels.status", version_status(ctx))
             + "GitHub Repo: " + repository_url(ctx) + "\n"
             + "© _" + str(first_year) + " - " + str(datetime.now().year) + "_",
        path=[ctx.t("title")])


def line(ctx: AdvancedCtx, key: str, value: str) -> str:
    return ctx.t(key) + ": _" + value + "_\n"


def repository_url(ctx: AdvancedCtx) -> str:
    return "https://github.com/" + ctx.config.github_username + "/" + ctx.config.github_repo + "/"


def fetch(url: str):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response


def api_url(ctx: AdvancedCtx, path: str) -> str:
    return ("https://api.github.com/repos/" + ctx.config.github_username + "/"
            + ctx.config.github_repo + path)


def published_commits(ctx: AdvancedCtx) -> int:
    links = fetch(api_url(ctx, "/commits?per_page=1")).links
    return int(parse_qs(urlparse(links["last"]["url"]).query)["page"][0])


def published_tag(ctx: AdvancedCtx) -> str:
    return str(fetch(api_url(ctx, "/releases/latest")).json()['tag_name'])


def version_status(ctx: AdvancedCtx) -> str:
    try:
        published = published_commits(ctx)
        if published == ctx.version.commits:
            return ctx.t("up_to_date")
        newest = Version(published_tag(ctx), published)
    except Exception as error:
        ctx.error("Could not read the published version - " + type(error).__name__ + ".", str(error))
        return ctx.t("core:error")
    key = "ahead" if ctx.version.commits > published else "behind"
    return ctx.t(key, version=str(newest))
