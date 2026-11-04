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


def report(registry: Registry, is_internal: bool) -> None:
    names = [module.name for module in registry.modules() if module.is_internal == is_internal]
    kind = "Internal" if is_internal else "External"
    print_log(kind + " modules loaded: " + (", ".join(names) or "none") + ".")


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

    @staticmethod
    def ordered(modules: list[Module]) -> list[Module]:
        found = {module.name: module for module in modules}
        placed: dict[str, Module] = {}
        visiting: set[str] = set()

        def place(module: Module) -> None:
            if module.name in placed or module.name in visiting:
                return
            visiting.add(module.name)
            for name in module.partners:
                if name in found:
                    place(found[name])
            visiting.discard(module.name)
            placed[module.name] = module

        for module in modules:
            place(module)
        return list(placed.values())

    def install(self, module: Module, registry: Registry) -> None:
        for old in module.formerly:
            self._storage.take_over(old, module.name)
        self._catalog.load_directory(module.name, os.path.join(module.path, locales_name))
        self._catalog.add_marks(module.name, module.icons, module.endings)
        schema_path = os.path.join(module.path, schema_name)
        if os.path.isfile(schema_path):
            with open(schema_path, encoding='utf8') as f:
                self._storage.for_module(module.name).apply_schema(f.read())
        registry.add(module)

    def carry_over_switch(self, module: Module) -> None:
        listed = self._config.listed_modules()
        old = next((old for old in module.formerly if old in listed), None)
        if not module.is_internal and old is not None and module.name not in listed:
            self._config.set_module_enabled(module.name, self._config.is_module_enabled(old))

    def warn_about_unknown_entries(self, present: set[str], modules: list[Module]) -> None:
        found = present | {old for module in modules for old in module.formerly}
        for name in self._config.listed_modules():
            if name not in found:
                print_error("Module '" + name + "' is listed in modules.yaml but has no directory.")

    def load(self, registry: Registry, sources: list[tuple[str, str, bool]]) -> Registry:
        modules = []
        for directory, package, is_internal in sources:
            modules.extend(self.collect(directory, package, is_internal))
        present = {name for directory, _, _ in sources for name in discover(directory)}
        self.warn_about_unknown_entries(present, modules)
        for module in modules:
            self.carry_over_switch(module)
        modules = [module for module in modules if module.is_internal or self._config.is_module_enabled(module.name)]
        for module in self.ordered(self.resolve(modules)):
            failed = next((name for name in module.requires if name in self.skipped), None)
            if failed is not None:
                self._skip(module.name, "requires '" + failed + "'")
                continue
            kept = next((old for old in module.formerly if old in present), None)
            if kept is not None:
                self._skip(module.name, "was formerly '" + kept + "', which is still there")
                continue
            try:
                self.install(module, registry)
            except Exception as error:
                self._skip(module.name, str(error))
        report(registry, True)
        report(registry, False)
        return registry

    def load_all(self, registry: Registry | None = None) -> Registry:
        return self.load(registry or Registry(), [
            (paths.internal_modules_dir, internal_package, True),
            (paths.external_modules_dir, external_package, False)])
