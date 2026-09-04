import telebot
from dataclasses import dataclass, field

from core.ui.keyboard import Button, render_button, render_markup


@dataclass(frozen=True)
class View:
    text: str
    buttons: list[Button] = field(default_factory=list)
    path: list[str] = field(default_factory=list)
    name: str = ""
    argument: str | None = None
    columns: int = 1
    parse_mode: str | None = "Markdown"

    @property
    def is_screen(self) -> bool:
        return bool(self.name)


def render_text(view: View) -> str:
    if not view.path:
        return view.text
    return "*" + " > ".join(view.path) + ":*\n\n" + view.text


def render(view: View, module_name: str,
           return_text: str = "") -> tuple[str, telebot.types.InlineKeyboardMarkup | None]:
    markup = render_markup(view.buttons, module_name, view.columns)
    if view.is_screen:
        markup = markup or telebot.types.InlineKeyboardMarkup()
        markup.row(render_button(Button.back(return_text), module_name))
    return render_text(view), markup
