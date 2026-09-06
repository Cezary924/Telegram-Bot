import ast
import importlib
import os
import re
import sys
from importlib.metadata import packages_distributions

import yaml

from core import callbacks, paths
from core.db.module_db import created_object_pattern
from core.i18n import default_language, load_locale_file, supported_languages
from core.loader import discover, external_package, internal_package, locales_name, manifest_name, schema_name
from core.module import Module

allowed_core_imports = {"core.api", "core.testing"}
tests_name = "tests"
requirements_name = "requirements.txt"
version_pattern = re.compile(r"[<>=!~;\[ ]")


def import_modules(directory: str, package: str, is_internal: bool) -> list[Module]:
    modules = []
    for name in discover(directory):
        try:
            imported = importlib.import_module(package + "." + name + "." + manifest_name)
        except ImportError:
            continue
        module = getattr(imported, manifest_name, None)
        if isinstance(module, Module):
            module.is_internal = is_internal
            module.path = os.path.join(directory, name)
            modules.append(module)
    return modules


def all_modules() -> list[Module]:
    return (import_modules(paths.internal_modules_dir, internal_package, True) +
            import_modules(paths.external_modules_dir, external_package, False))


def check_manifest(module: Module) -> list[str]:
    problems = []
    if os.path.basename(module.path) != module.name:
        problems.append("the manifest name does not match the directory '" +
                        os.path.basename(module.path) + "'")
    if module.name in module.requires:
        problems.append("the module requires itself")
    return problems


def check_locales(module: Module) -> list[str]:
    directory = os.path.join(module.path, locales_name)
    if not os.path.isdir(directory):
        return ["there is no '" + locales_name + "' directory"] if module.commands else []
    files = sorted(name for name in os.listdir(directory) if name.endswith(".yaml"))
    if default_language + ".yaml" not in files:
        return ["there is no '" + default_language + ".yaml' translation"]
    problems = []
    wanted = {language + ".yaml" for language in supported_languages()}
    for name in sorted(wanted - set(files)):
        problems.append("there is no '" + name + "' translation")
    for name in sorted(set(files) - wanted):
        problems.append("'" + name + "' is not a language the Bot supports")
    keys = {name: set(load_locale_file(os.path.join(directory, name))) for name in files}
    expected = keys[default_language + ".yaml"]
    for name, found in keys.items():
        for key in sorted(expected - found):
            problems.append("'" + name + "' is missing the key '" + key + "'")
        for key in sorted(found - expected):
            problems.append("'" + name + "' has the extra key '" + key + "'")
    for key in [module.title, module.description]:
        if key not in expected:
            problems.append("there is no '" + key + "' key for the module listing")
    for command in module.commands:
        if command.description not in expected:
            problems.append("command '" + command.name + "' has no description key '" +
                            command.description + "'")
    return problems


def check_yaml_traps(module: Module) -> list[str]:
    directory = os.path.join(module.path, locales_name)
    if not os.path.isdir(directory):
        return []
    problems = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".yaml"):
            continue
        with open(os.path.join(directory, name), encoding='utf8') as f:
            data = yaml.load(f, Loader=yaml.Loader) or {}
        for key, value in flat_pairs(data):
            if isinstance(key, bool):
                problems.append("'" + name + "' has a key YAML read as a boolean - quote it")
            if isinstance(value, bool):
                problems.append("'" + name + "' has the value of '" + str(key) +
                                "' read as a boolean - quote it")
            if isinstance(value, dict):
                continue
    return problems


def flat_pairs(data: dict):
    for key, value in data.items():
        yield key, value
        if isinstance(value, dict):
            yield from flat_pairs(value)


def check_callbacks(module: Module) -> list[str]:
    return ["callback '" + callback.action + "' leaves no room for arguments"
            for callback in module.callbacks
            if callbacks.room_for_arguments(module.name, callback.action) < 0]


def check_schema(module: Module) -> list[str]:
    path = os.path.join(module.path, schema_name)
    if not os.path.isfile(path):
        return []
    with open(path, encoding='utf8') as f:
        created = created_object_pattern.findall(f.read())
    return ["'" + name + "' is missing the '" + module.table_prefix + "' prefix"
            for name in created if not name.startswith(module.table_prefix)]


def imported_names(path: str) -> list[str]:
    with open(path, encoding='utf8') as f:
        tree = ast.parse(f.read(), path)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.extend(node.module + "." + alias.name for alias in node.names)
    return names


def is_import_allowed(name: str, module: Module) -> bool:
    if name.startswith("core."):
        return any(name == allowed or name.startswith(allowed + ".") for allowed in allowed_core_imports)
    if name.startswith(internal_package + ".") or name.startswith(external_package + "."):
        return name.split(".")[2] in module.requires + [module.name]
    return True


def check_imports(module: Module) -> list[str]:
    if module.is_internal:
        return []
    problems = []
    for directory, _, files in os.walk(module.path):
        for file_name in sorted(files):
            if not file_name.endswith(".py"):
                continue
            for name in imported_names(os.path.join(directory, file_name)):
                if not is_import_allowed(name, module):
                    problems.append("'" + file_name + "' imports '" + name + "'")
    return problems


def normalized(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def declared_packages(module: Module) -> set[str]:
    path = os.path.join(module.path, requirements_name)
    if not os.path.isfile(path):
        return set()
    names = set()
    with open(path, encoding='utf8') as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line and not line.startswith("-"):
                names.add(normalized(version_pattern.split(line)[0]))
    return names


def runtime_files(module: Module) -> list[str]:
    files = []
    for directory, _, names in os.walk(module.path):
        parts = os.path.relpath(directory, module.path).split(os.sep)
        if tests_name in parts:
            continue
        files += [os.path.join(directory, name) for name in sorted(names) if name.endswith(".py")]
    return files


def imported_packages(module: Module) -> set[str]:
    local = ("core", internal_package.split(".")[0])
    found = set()
    for path in runtime_files(module):
        for name in imported_names(path):
            root = name.split(".")[0]
            if root not in local and root not in sys.stdlib_module_names:
                found.add(root)
    return found


def distributions_of(name: str) -> set[str]:
    known = packages_distributions().get(name)
    return {normalized(one) for one in known} if known else {normalized(name)}


def check_requirements(module: Module) -> list[str]:
    declared = declared_packages(module)
    return ["'" + name + "' is imported but no package providing it is in '" +
            requirements_name + "'"
            for name in sorted(imported_packages(module))
            if not distributions_of(name) & declared]


def check_tests(module: Module) -> list[str]:
    if os.path.isdir(os.path.join(module.path, tests_name)):
        return []
    return ["there is no '" + tests_name + "' directory"]


checks = [check_manifest, check_locales, check_yaml_traps, check_callbacks, check_schema,
          check_imports, check_requirements, check_tests]


def check(module: Module) -> list[str]:
    return [problem for run in checks for problem in run(module)]
