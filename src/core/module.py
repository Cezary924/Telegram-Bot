import re
from dataclasses import dataclass, field, replace
from typing import Callable

from core import callbacks
from core.form import Form, Question, offer_key, press, screen, take
from core.roles import Role
from core.ui.view import View

name_pattern = re.compile(r"[a-z][a-z0-9_]*")
action_pattern = re.compile(r"[a-z][a-z0-9_]*")
command_pattern = re.compile(r"[a-z][a-z0-9_]*")
parameter_pattern = re.compile(r"[a-z][a-z0-9_]*")
parameter_types: dict[type, str] = {str: "string", int: "integer", float: "number", bool: "boolean"}
exposed_pattern = re.compile(r"[a-z][a-z0-9_]*")

settings_view = "settings"
settings_hub = "settings"
settings_hub_view = "menu"
settings_list_view = "modules"
settings_origin = "settings.origin"


@dataclass(frozen=True)
class SettingsScreen:
    view: str
    role: Role


@dataclass(frozen=True)
class Command:
    name: str
    handler: Callable
    role: Role
    description: str
    is_background: bool


@dataclass(frozen=True)
class Callback:
    action: str
    handler: Callable
    role: Role
    is_background: bool


@dataclass(frozen=True)
class Matcher:
    predicate: Callable
    handler: Callable
    role: Role
    priority: int
    order: int
    is_background: bool
    media: tuple[str, ...] = ()
    is_personal: bool = False


@dataclass(frozen=True)
class State:
    name: str
    handler: Callable
    role: Role
    is_background: bool


@dataclass(frozen=True)
class ViewHandler:
    name: str
    handler: Callable
    parent: str = ""
    title: str = ""


@dataclass(frozen=True)
class Outcome:
    status: str
    result: str | list | dict = ""
    then: Callable[[], str] | None = None

    @classmethod
    def done(cls, result: str | list | dict) -> "Outcome":
        return cls("done", result)

    @classmethod
    def refused(cls, problem: str) -> "Outcome":
        return cls("refused", problem)

    @classmethod
    def ask(cls, question: str, then: Callable[[], str]) -> "Outcome":
        return cls("asking", question, then)


@dataclass(frozen=True)
class Action:
    name: str
    handler: Callable
    tool: str
    parameters: dict[str, type]
    description: str
    role: Role
    is_confirmed: bool
    optional: tuple[str, ...] = ()

    @staticmethod
    def key(parameter: str) -> str:
        return "parameters." + parameter

    def type_of(self, parameter: str) -> str:
        return parameter_types[self.parameters[parameter]]


@dataclass(frozen=True)
class Exposed:
    handler: Callable
    is_writing: bool = False


@dataclass(frozen=True)
class Job:
    name: str
    handler: Callable
    interval: int
    is_aligned: bool = False


@dataclass
class Module:
    name: str
    title: str = "name"
    description: str = "description"
    requires: list[str] = field(default_factory=list)
    uses: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)
    config_keys: list[str] = field(default_factory=list)
    notifications: str = ""
    is_guarded: bool = False
    is_assistant: bool = False
    place: int = 1000
    icons: dict[str, str] = field(default_factory=dict)
    endings: dict[str, str] = field(default_factory=dict)

    commands: list[Command] = field(default_factory=list, init=False)
    callbacks: list[Callback] = field(default_factory=list, init=False)
    matchers: list[Matcher] = field(default_factory=list, init=False)
    states: list[State] = field(default_factory=list, init=False)
    views: list[ViewHandler] = field(default_factory=list, init=False)
    jobs: list[Job] = field(default_factory=list, init=False)
    actions: list[Action] = field(default_factory=list, init=False)
    exposed: dict[str, Exposed] = field(default_factory=dict, init=False)
    forms: dict[str, Form] = field(default_factory=dict, init=False)
    settings_screen: SettingsScreen | None = field(default=None, init=False)
    summary: Callable | None = field(default=None, init=False)

    is_internal: bool = field(default=False, init=False)
    path: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if not name_pattern.fullmatch(self.name):
            raise ValueError("Module name must be lowercase letters, digits and underscores: " + self.name)

    @property
    def table_prefix(self) -> str:
        return "module_" + self.name + "_"

    def command(self, name: str, role: Role = Role.GUEST, description: str | None = None,
                is_background: bool = False) -> Callable:
        if not command_pattern.fullmatch(name):
            raise ValueError("Command name must be lowercase letters, digits and underscores: " + name)
        if any(command.name == name for command in self.commands):
            raise ValueError("Module '" + self.name + "' declares command '" + name + "' twice")

        def decorator(handler: Callable) -> Callable:
            self.commands.append(Command(name, handler, role, description or "commands." + name,
                                         is_background))
            return handler

        return decorator

    def callback(self, action: str, role: Role = Role.GUEST, is_background: bool = False) -> Callable:
        if not action_pattern.fullmatch(action):
            raise ValueError("Callback action must be lowercase letters, digits and underscores: " + action)
        if any(callback.action == action for callback in self.callbacks):
            raise ValueError("Module '" + self.name + "' declares callback '" + action + "' twice")
        if callbacks.room_for_arguments(self.name, action) < 0:
            raise ValueError("Callback '" + self.name + callbacks.separator + action + "' exceeds " +
                             str(callbacks.max_length) + " bytes")

        def decorator(handler: Callable) -> Callable:
            self.callbacks.append(Callback(action, handler, role, is_background))
            return handler

        return decorator

    def match(self, predicate: Callable, priority: int = 0, role: Role = Role.GUEST,
              is_background: bool = False, media: tuple[str, ...] = (), is_personal: bool = False) -> Callable:
        def decorator(handler: Callable) -> Callable:
            self.matchers.append(Matcher(predicate, handler, role, priority, len(self.matchers),
                                         is_background, media, is_personal))
            return handler

        return decorator

    def state(self, name: str, role: Role = Role.GUEST, is_background: bool = False) -> Callable:
        if any(state.name == name for state in self.states):
            raise ValueError("Module '" + self.name + "' declares state '" + name + "' twice")

        def decorator(handler: Callable) -> Callable:
            self.states.append(State(name, handler, role, is_background))
            return handler

        return decorator

    def view(self, name: str, parent: str = "", title: str = "") -> Callable:
        if any(view.name == name for view in self.views):
            raise ValueError("Module '" + self.name + "' declares view '" + name + "' twice")
        if parent == name:
            raise ValueError("View '" + name + "' in '" + self.name + "' is its own parent")

        def decorator(handler: Callable) -> Callable:
            def stamped(*arguments, **values) -> View:
                result = handler(*arguments, **values)
                return replace(result, name=name) if isinstance(result, View) else result

            self.views.append(ViewHandler(name, stamped, parent, title))
            return stamped

        return decorator

    def settings(self, role: Role = Role.GUEST) -> Callable:
        if self.settings_screen is not None:
            raise ValueError("Module '" + self.name + "' declares settings twice")
        register = self.view(settings_view)
        self.settings_screen = SettingsScreen(settings_view, role)
        return register

    def is_settings(self, name: str) -> bool:
        branch = self.branch(name)
        return (self.settings_screen is not None and self.name != settings_hub
                and bool(branch) and branch[0].name == self.settings_screen.view)

    def view_named(self, name: str) -> ViewHandler | None:
        return next((view for view in self.views if view.name == name), None)

    def parent_of(self, name: str) -> str:
        found = self.view_named(name)
        return found.parent if found else ""

    def branch(self, name: str) -> list[ViewHandler]:
        walked: list[ViewHandler] = []
        seen: set[str] = set()
        current = name
        while current and current not in seen:
            found = self.view_named(current)
            if found is None:
                break
            seen.add(current)
            walked.append(found)
            current = found.parent
        return list(reversed(walked))

    def job(self, interval: int, name: str | None = None, is_aligned: bool = False) -> Callable:
        if interval <= 0:
            raise ValueError("Job interval must be positive: " + str(interval))

        def decorator(handler: Callable) -> Callable:
            self.jobs.append(Job(name or handler.__name__, handler, interval, is_aligned))
            return handler

        return decorator

    def action(self, name: str, parameters: dict[str, type] | None = None, description: str | None = None,
               role: Role = Role.GUEST, is_confirmed: bool = False, optional: list[str] | None = None) -> Callable:
        if not action_pattern.fullmatch(name):
            raise ValueError("Action name must be lowercase letters, digits and underscores: " + name)
        if any(action.name == name for action in self.actions):
            raise ValueError("Module '" + self.name + "' declares action '" + name + "' twice")
        for parameter, kind in (parameters or {}).items():
            if not parameter_pattern.fullmatch(parameter) or kind not in parameter_types:
                raise ValueError("Action '" + name + "' in '" + self.name + "' has a wrong parameter: " + parameter)
            if "user" in parameter.split("_"):
                raise ValueError("Action '" + name + "' in '" + self.name + "' acts only for the user who asks, "
                                 "it cannot take: " + parameter)
        for parameter in optional or []:
            if parameter not in (parameters or {}):
                raise ValueError("Action '" + name + "' in '" + self.name + "' has no parameter: " + parameter)

        def decorator(handler: Callable) -> Callable:
            self.actions.append(Action(name, handler, self.name + "_" + name, dict(parameters or {}),
                                       description or "actions." + name, role, is_confirmed, tuple(optional or [])))
            return handler

        return decorator

    def context(self) -> Callable:
        if self.summary is not None:
            raise ValueError("Module '" + self.name + "' declares context twice")

        def decorator(handler: Callable) -> Callable:
            self.summary = handler
            return handler

        return decorator

    def expose(self, name: str, is_writing: bool = False) -> Callable:
        if not exposed_pattern.fullmatch(name):
            raise ValueError("Exposed name must be lowercase letters, digits and underscores: " + name)
        if name in self.exposed:
            raise ValueError("Module '" + self.name + "' exposes '" + name + "' twice")

        def decorator(handler: Callable) -> Callable:
            self.exposed[name] = Exposed(handler, is_writing)
            return handler

        return decorator

    def form(self, name: str, questions: list[Question], parent: str = "", title: str = "",
             is_background: bool = False) -> Callable:
        if not questions:
            raise ValueError("Form '" + name + "' in '" + self.name + "' asks nothing")
        callbacks.build(self.name, name, offer_key, "1")
        for question in questions:
            for answer in question.answers:
                callbacks.build(self.name, name, question.key, answer)

        def decorator(handler: Callable) -> Callable:
            found = Form(name, tuple(questions), handler, is_background)
            self.view(name, parent, title)(lambda ctx: screen(ctx, found))
            self.state(name, is_background=is_background)(lambda ctx: take(ctx, found))
            self.callback(name, is_background=is_background)(lambda ctx: press(ctx, found))
            self.forms[name] = found
            return handler

        return decorator

    @property
    def partners(self) -> list[str]:
        return self.requires + [name for name in self.uses if name not in self.requires]

    def callback_data(self, action: str, *arguments: str | int) -> str:
        return callbacks.build(self.name, action, *arguments)
