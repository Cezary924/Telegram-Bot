import telebot
from dataclasses import dataclass, field, replace

from core.ui.html import escape, plain
from core.ui.keyboard import Button, render_button, render_markup

caption_limit = 1024


@dataclass(frozen=True)
class View:
    text: str
    buttons: list[Button] = field(default_factory=list)
    heading: str | None = ""
    name: str = ""
    argument: str | None = None
    columns: int = 1
    parse_mode: str | None = "HTML"
    photo: bytes | None = None

    @property
    def is_screen(self) -> bool:
        return bool(self.name)


def render_text(view: View, heading: list[str]) -> str:
    if view.heading is None:
        return view.text
    parts = [view.heading] if view.heading else heading
    if not parts:
        return view.text
    return "<b>" + escape(" > ").join(parts) + ":</b>\n\n" + view.text


def fitted(view: View, heading: list[str]) -> View:
    room = caption_limit - len(plain(render_text(replace(view, text=""), heading)))
    lines = view.text.split("\n")
    while len(plain("\n".join(lines))) > room and len(lines) > 2:
        lines = lines[:1] + ["…"] + lines[3 if lines[1] == "…" else 2:]
    text = "\n".join(lines)
    if len(plain(text)) > room:
        text = escape(plain(text)[:max(0, room - 1)]) + "…"
    return replace(view, text=text)


def render(view: View, module_name: str, controls: list[Button] | None = None,
           heading: list[str] | None = None) -> tuple[str, telebot.types.InlineKeyboardMarkup | None]:
    markup = render_markup(view.buttons, module_name, view.columns)
    if view.is_screen and controls:
        markup = markup or telebot.types.InlineKeyboardMarkup()
        markup.row(*[render_button(one, module_name) for one in controls])
    if view.photo is not None:
        view = fitted(view, heading or [])
    return render_text(view, heading or []), markup
