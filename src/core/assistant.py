from core.context import User, create_context, is_available
from core.i18n import core_namespace
from core.log import print_error
from core.module import Action, Module, Outcome
from core.services import Services
from core.ui.html import plain

context_lines = 5
context_size = 400


def coerced(value, kind: type):
    if value is None or isinstance(value, (list, dict)):
        raise ValueError("no value")
    if kind is bool:
        if isinstance(value, bool):
            return value
        raise ValueError("not a boolean")
    if isinstance(value, bool):
        raise ValueError("a boolean")
    if kind is int:
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("not a whole number")
        return int(value) if isinstance(value, (int, float)) else int(str(value).strip())
    if kind is float:
        return float(value)
    return str(value)


class Assistant:
    def __init__(self, services: Services, user: User) -> None:
        self._services = services
        self._user = user

    def may_use(self, module: Module) -> bool:
        return is_available(self._services, self._user, module.name)

    def modules(self) -> list[Module]:
        return [module for module in self._services.registry.modules() if self.may_use(module)]

    def actions(self) -> list[tuple[Module, Action]]:
        return [(module, action) for module in self.modules() for action in module.actions
                if self._user.role >= action.role]

    def core_text(self, key: str, /, **values) -> str:
        return self._services.catalog.text(core_namespace, key, self._user.language, **values)

    def act(self, module_name: str, action_name: str, arguments: dict, is_confirmed: bool = False) -> Outcome:
        found = next(((module, action) for module, action in self.actions()
                      if module.name == module_name and action.name == action_name), None)
        if found is None:
            return Outcome.refused(self.core_text("assistant.unknown"))
        module, action = found
        try:
            values = {name: None if name in action.optional and arguments.get(name) is None
                      else coerced(arguments.get(name), kind) for name, kind in action.parameters.items()}
        except (TypeError, ValueError):
            optional = ", " + self.core_text("assistant.optional")
            expected = ", ".join(name + " (" + action.type_of(name) + (optional if name in action.optional else "")
                                 + ")" for name in action.parameters)
            return Outcome.refused(self.core_text("assistant.wrong_arguments", expected=expected))
        try:
            outcome = action.handler(create_context(self._services, module, self._user, is_pressed=is_confirmed),
                                     **values)
            if outcome.then is not None and (is_confirmed or not action.is_confirmed):
                return Outcome.done(outcome.then())
        except Exception as error:
            print_error("Action failed in '" + module.name + "' - " + type(error).__name__ + ".", str(error))
            return Outcome.refused(self.core_text("error"))
        return outcome

    def context(self, module_name: str) -> str:
        module = self._services.registry.get(module_name)
        if module is None or not self.may_use(module):
            return ""
        summary = module.summary
        if summary is None:
            return ""
        try:
            text = summary(create_context(self._services, module, self._user)) or ""
        except Exception as error:
            print_error("Context failed in '" + module.name + "' - " + type(error).__name__ + ".", str(error))
            return ""
        lines = [line.strip() for line in plain(text).split("\n") if line.strip()]
        return "\n".join(lines[:context_lines])[:context_size]
