import re
from dataclasses import dataclass, field, replace
from typing import Callable

from core import callbacks
from core.roles import Role
from core.ui.view import View

name_pattern = re.compile(r"[a-z][a-z0-9_]*")
action_pattern = re.compile(r"[a-z][a-z0-9_]*")
command_pattern = re.compile(r"[a-z][a-z0-9_]*")


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


@dataclass(frozen=True)
class Job:
    name: str
    handler: Callable
    interval: int


@dataclass
class Module:
    name: str
    title: str = "name"
    description: str = "description"
    requires: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)

    commands: list[Command] = field(default_factory=list, init=False)
    callbacks: list[Callback] = field(default_factory=list, init=False)
    matchers: list[Matcher] = field(default_factory=list, init=False)
    states: list[State] = field(default_factory=list, init=False)
    views: list[ViewHandler] = field(default_factory=list, init=False)
    jobs: list[Job] = field(default_factory=list, init=False)

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
              is_background: bool = False) -> Callable:
        def decorator(handler: Callable) -> Callable:
            self.matchers.append(Matcher(predicate, handler, role, priority, len(self.matchers),
                                         is_background))
            return handler
        return decorator

    def state(self, name: str, role: Role = Role.GUEST, is_background: bool = False) -> Callable:
        if any(state.name == name for state in self.states):
            raise ValueError("Module '" + self.name + "' declares state '" + name + "' twice")

        def decorator(handler: Callable) -> Callable:
            self.states.append(State(name, handler, role, is_background))
            return handler
        return decorator

    def view(self, name: str) -> Callable:
        if any(view.name == name for view in self.views):
            raise ValueError("Module '" + self.name + "' declares view '" + name + "' twice")

        def decorator(handler: Callable) -> Callable:
            def stamped(*arguments, **values) -> View:
                result = handler(*arguments, **values)
                return replace(result, name=name) if isinstance(result, View) else result
            self.views.append(ViewHandler(name, stamped))
            return stamped
        return decorator

    def job(self, interval: int, name: str | None = None) -> Callable:
        if interval <= 0:
            raise ValueError("Job interval must be positive: " + str(interval))

        def decorator(handler: Callable) -> Callable:
            self.jobs.append(Job(name or handler.__name__, handler, interval))
            return handler
        return decorator

    def callback_data(self, action: str, *arguments: str | int) -> str:
        return callbacks.build(self.name, action, *arguments)
