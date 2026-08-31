import importlib
import os

from core import paths
from core.i18n import Catalog
from core.log import print_error, print_log
from core.module import Module
from core.registry import Registry

internal_package = "modules.internal"
external_package = "modules.external"
manifest_name = "module"
locales_name = "locales"
schema_name = "schema.sql"


def discover(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        return []
    names = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if name.startswith("_") or not os.path.isdir(path):
            continue
        if os.path.isfile(os.path.join(path, manifest_name + ".py")):
            names.append(name)
    return names


class Loader:
    def __init__(self, config, catalog: Catalog, storage) -> None:
        self._config = config
        self._catalog = catalog
        self._storage = storage
        self.skipped: dict[str, str] = {}

    def _skip(self, name: str, reason: str) -> None:
        self.skipped[name] = reason
        print_error("Module '" + name + "' skipped - " + reason + ".")

    def import_module(self, package: str, directory: str, name: str, is_internal: bool) -> Module | None:
        try:
            imported = importlib.import_module(package + "." + name + "." + manifest_name)
        except ImportError as error:
            self._skip(name, "missing dependency (" + str(error) + ")")
            return None
        module = getattr(imported, manifest_name, None)
        if not isinstance(module, Module):
            self._skip(name, "no 'module' object in " + manifest_name + ".py")
            return None
        if module.name != name:
            self._skip(name, "declares the name '" + module.name + "'")
            return None
        module.is_internal = is_internal
        module.path = os.path.join(directory, name)
        return module

    def collect(self, directory: str, package: str, is_internal: bool) -> list[Module]:
        modules = []
        for name in discover(directory):
            if not is_internal and not self._config.is_module_enabled(name):
                continue
            module = self.import_module(package, directory, name, is_internal)
            if module is not None:
                modules.append(module)
        return modules

    def resolve(self, modules: list[Module]) -> list[Module]:
        kept = {module.name: module for module in modules}
        while True:
            missing = {name: requirement
                       for name, module in kept.items()
                       for requirement in module.requires if requirement not in kept}
            if not missing:
                return [module for module in modules if module.name in kept]
            for name, requirement in missing.items():
                self._skip(name, "requires '" + requirement + "'")
                del kept[name]

    def install(self, module: Module, registry: Registry) -> None:
        self._catalog.load_directory(module.name, os.path.join(module.path, locales_name))
        schema_path = os.path.join(module.path, schema_name)
        if os.path.isfile(schema_path):
            with open(schema_path, encoding='utf8') as f:
                self._storage.for_module(module.name).apply_schema(f.read())
        registry.add(module)

    def warn_about_unknown_entries(self, sources: list[tuple[str, str, bool]]) -> None:
        found = {name for directory, _, _ in sources for name in discover(directory)}
        for name in self._config.listed_modules():
            if name not in found:
                print_error("Module '" + name + "' is listed in modules.yaml but has no directory.")

    def load(self, registry: Registry, sources: list[tuple[str, str, bool]]) -> Registry:
        self.warn_about_unknown_entries(sources)
        modules = []
        for directory, package, is_internal in sources:
            modules.extend(self.collect(directory, package, is_internal))
        for module in self.resolve(modules):
            try:
                self.install(module, registry)
            except Exception as error:
                self._skip(module.name, str(error))
        print_log("Modules loaded: " + (", ".join(registry.names()) or "none") + ".")
        return registry

    def load_all(self, registry: Registry | None = None) -> Registry:
        return self.load(registry or Registry(), [
            (paths.internal_modules_dir, internal_package, True),
            (paths.external_modules_dir, external_package, False)])
