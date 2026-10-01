import os
import yaml

from core import paths
from core.log import print_error
from core.ui.html import Html, escape

core_namespace = "core"
core_locales_dir: str = os.path.join(paths.core_dir, "locales")
default_language = "en"
namespace_separator = ":"
language_label_key = "language_label"

core_icons = {'return_button': "🔙", 'home_button': "🏠", 'close_button': "✖️", 'notifications_label': "🤖",
              'consent.agreement.title': "✋", 'consent.yes_button': "✅", 'consent.no_button': "❌"}
core_endings = {'banned_info': "😐", 'permission_denied.text': "😭", 'permission_denied.hint': "🧑‍🔬",
                'not_working_buttons': "😥", 'unknown_command': "💔", 'unknown_message': "💔", 'bot_updated': "🙏",
                'consent.agreement.text': "💝", 'consent.accepted.text': "💞", 'consent.accepted.ready': "🫡",
                'consent.declined.text': "😞", 'consent.declined.goodbye': "😄"}


def flatten(data: dict, prefix: str = "") -> dict[str, str]:
    texts = {}
    for key, value in data.items():
        text_key = prefix + str(key)
        if isinstance(value, dict):
            texts.update(flatten(value, text_key + "."))
        elif value is not None:
            texts[text_key] = str(value).replace(r'\n', '\n')
    return texts


def supported_languages() -> list[str]:
    if not os.path.isdir(core_locales_dir):
        return [default_language]
    return sorted(name[:-len(".yaml")] for name in os.listdir(core_locales_dir)
                  if name.endswith(".yaml"))


def full_key(namespace: str, key: str) -> str:
    if namespace_separator in key:
        return key
    return namespace + namespace_separator + key


def load_locale_file(path: str) -> dict[str, str]:
    with open(path, encoding='utf8') as f:
        data = yaml.load(f, Loader=yaml.Loader)
    return flatten(data) if data else {}


class Catalog:
    def __init__(self) -> None:
        self._texts: dict[str, dict[str, str]] = {}
        self._icons: dict[str, str] = {}
        self._endings: dict[str, str] = {}
        self._reported: set[str] = set()

    def add_marks(self, namespace: str, icons: dict[str, str], endings: dict[str, str]) -> None:
        self._icons.update({full_key(namespace, key): icon for key, icon in icons.items()})
        self._endings.update({full_key(namespace, key): ending for key, ending in endings.items()})

    def add(self, namespace: str, language: str, texts: dict[str, str]) -> None:
        catalog = self._texts.setdefault(language, {})
        for key, text in texts.items():
            catalog[namespace + namespace_separator + key] = text

    def load_directory(self, namespace: str, path: str) -> list[str]:
        if not os.path.isdir(path):
            return []
        languages = []
        for name in sorted(os.listdir(path)):
            if not name.endswith(".yaml"):
                continue
            language = name[: -len(".yaml")]
            self.add(namespace, language, load_locale_file(os.path.join(path, name)))
            languages.append(language)
        return languages

    def load_core(self) -> list[str]:
        self.add_marks(core_namespace, core_icons, core_endings)
        return self.load_directory(core_namespace, core_locales_dir)

    def has(self, namespace: str, key: str, language: str) -> bool:
        return full_key(namespace, key) in self._texts.get(language, {})

    def text(self, namespace: str, key: str, language: str, /, **values) -> Html:
        wanted = full_key(namespace, key)
        for candidate in [language, default_language]:
            text = self._texts.get(candidate, {}).get(wanted)
            if text is not None:
                safe = escape(text)
                safe = safe.format(**{name: escape(value) for name, value in values.items()}) if values else safe
                return Html(self.marked(wanted, safe))
        if wanted not in self._reported:
            self._reported.add(wanted)
            print_error("Missing translation - " + wanted + " (" + language + ").")
        return Html(wanted)

    def marked(self, key: str, text: str) -> str:
        icon, ending = self._icons.get(key), self._endings.get(key)
        return (icon + " " if icon else "") + text + (" " + ending if ending else "")

    def label(self, language: str) -> str:
        return self.text(core_namespace, language_label_key, language)

    def languages(self) -> list[str]:
        return sorted(self._texts.keys())

    def keys(self, namespace: str, language: str) -> set[str]:
        prefix = namespace + namespace_separator
        return {key[len(prefix):] for key in self._texts.get(language, {}) if key.startswith(prefix)}

    def namespaces(self) -> set[str]:
        return {key.split(namespace_separator, 1)[0]
                for texts in self._texts.values() for key in texts}
