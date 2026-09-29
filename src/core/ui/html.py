import html
import re

tag_pattern = re.compile(r"<[^>]*>")


class Html(str):
    pass


def escape(text) -> str:
    return text if isinstance(text, Html) else html.escape(str(text), quote=False)


def bold(text) -> Html:
    return Html("<b>" + escape(text) + "</b>")


def italic(text) -> Html:
    return Html("<i>" + escape(text) + "</i>")


def plain(text: str) -> str:
    return html.unescape(tag_pattern.sub("", text))
