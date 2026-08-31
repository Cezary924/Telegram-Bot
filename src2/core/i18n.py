import os
import yaml

from core import paths
from core.log import print_error

core_namespace = "core"
core_locales_dir: str = os.path.join(paths.core_dir, "locales")
default_language = "en"
namespace_separator = ":"


def flatten(data: dict, prefix: str = "") -> dict[str, str]:
    texts = {}
    for key, value in data.items():
        text_key = prefix + str(key)
        if isinstance(value, dict):
            texts.update(flatten(value, text_key + "."))
        elif value is not None:
            texts[text_key] = str(value).replace(r'\n', '\n')
    return texts


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
        self._reported: set[str] = set()

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
        return self.load_directory(core_namespace, core_locales_dir)

    def has(self, namespace: str, key: str, language: str) -> bool:
        return full_key(namespace, key) in self._texts.get(language, {})

    def text(self, namespace: str, key: str, language: str, **values) -> str:
        wanted = full_key(namespace, key)
        for candidate in [language, default_language]:
            text = self._texts.get(candidate, {}).get(wanted)
            if text is not None:
                return text.format(**values) if values else text
        if wanted not in self._reported:
            self._reported.add(wanted)
            print_error("Missing translation - " + wanted + " (" + language + ").")
        return wanted

    def languages(self) -> list[str]:
        return sorted(self._texts.keys())

    def keys(self, namespace: str, language: str) -> set[str]:
        prefix = namespace + namespace_separator
        return {key[len(prefix):] for key in self._texts.get(language, {}) if key.startswith(prefix)}

    def namespaces(self) -> set[str]:
        return {key.split(namespace_separator, 1)[0]
                for texts in self._texts.values() for key in texts}
