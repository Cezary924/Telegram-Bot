import html
import re

tag_pattern = re.compile(r"<[^>]*>")


class Html(str):
    pass


def escape(text) -> str:
    return text if isinstance(text, Html) else html.escape(str(text), quote=False)


def bold(*parts) -> Html:
    return Html("<b>" + "".join(escape(part) for part in parts) + "</b>")


def italic(*parts) -> Html:
    return Html("<i>" + "".join(escape(part) for part in parts) + "</i>")


def labelled(label, value) -> Html:
    return Html(escape(label) + ": " + italic(value))


def plain(text: str) -> str:
    return html.unescape(tag_pattern.sub("", text))
