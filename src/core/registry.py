from core.module import Callback, Command, Job, Matcher, Module, State, ViewHandler


class Registry:
    def __init__(self) -> None:
        self._modules: dict[str, Module] = {}
        self._commands: dict[str, Module] = {}

    def add(self, module: Module) -> None:
        if module.name in self._modules:
            raise ValueError("Module '" + module.name + "' is already registered")
        for command in module.commands:
            owner = self._commands.get(command.name)
            if owner is not None:
                raise ValueError("Command '" + command.name + "' is declared by '" + owner.name +
                                 "' and '" + module.name + "'")
        self._modules[module.name] = module
        for command in module.commands:
            self._commands[command.name] = module

    def get(self, name: str) -> Module | None:
        return self._modules.get(name)

    def modules(self) -> list[Module]:
        return [self._modules[name] for name in sorted(self._modules)]

    def names(self) -> list[str]:
        return sorted(self._modules)

    def command(self, name: str) -> tuple[Module, Command] | None:
        module = self._commands.get(name)
        if module is None:
            return None
        return module, next(command for command in module.commands if command.name == name)

    def commands(self) -> list[tuple[Module, Command]]:
        pairs = [(module, command) for module in self._modules.values() for command in module.commands]
        return sorted(pairs, key=lambda pair: pair[1].name)

    def callback(self, module_name: str, action: str) -> tuple[Module, Callback] | None:
        module = self._modules.get(module_name)
        if module is None:
            return None
        for callback in module.callbacks:
            if callback.action == action:
                return module, callback
        return None

    def state(self, module_name: str, name: str) -> tuple[Module, State] | None:
        module = self._modules.get(module_name)
        if module is None:
            return None
        for state in module.states:
            if state.name == name:
                return module, state
        return None

    def view(self, module_name: str, name: str) -> tuple[Module, ViewHandler] | None:
        module = self._modules.get(module_name)
        if module is None:
            return None
        for view in module.views:
            if view.name == name:
                return module, view
        return None

    def matchers(self) -> list[tuple[Module, Matcher]]:
        pairs = [(module, matcher) for module in self._modules.values() for matcher in module.matchers]
        return sorted(pairs, key=lambda pair: (-pair[1].priority, pair[0].name, pair[1].order))

    def jobs(self) -> list[tuple[Module, Job]]:
        return [(module, job) for module in self.modules() for job in module.jobs]
