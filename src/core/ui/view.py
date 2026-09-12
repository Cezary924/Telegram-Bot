import telebot
from dataclasses import dataclass, field

from core.ui.keyboard import Button, render_button, render_markup


@dataclass(frozen=True)
class View:
    text: str
    buttons: list[Button] = field(default_factory=list)
    heading: str | None = ""
    name: str = ""
    argument: str | None = None
    columns: int = 1
    parse_mode: str | None = "Markdown"

    @property
    def is_screen(self) -> bool:
        return bool(self.name)


def render_text(view: View, heading: list[str]) -> str:
    if view.heading is None:
        return view.text
    parts = [view.heading] if view.heading else heading
    if not parts:
        return view.text
    return "*" + " > ".join(parts) + ":*\n\n" + view.text


def render(view: View, module_name: str, controls: list[Button] | None = None,
           heading: list[str] | None = None) -> tuple[str, telebot.types.InlineKeyboardMarkup | None]:
    markup = render_markup(view.buttons, module_name, view.columns)
    if view.is_screen and controls:
        markup = markup or telebot.types.InlineKeyboardMarkup()
        markup.row(*[render_button(one, module_name) for one in controls])
    return render_text(view, heading or []), markup
