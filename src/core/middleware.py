from core.context import User, can_use
from core.i18n import core_namespace
from core.roles import Role
from core.services import Services
from core.ui.html import bold
from core.ui.keyboard import Button
from core.ui.view import View

consent_accept_action = "consent_accept"
consent_decline_action = "consent_decline"
consent_language_action = "consent_language"
request_action = "request"
grant_action = "grant"
refuse_action = "refuse"


def core_text(services: Services, key: str, language: str) -> str:
    return services.catalog.text(core_namespace, key, language)


def core_button(services: Services, key: str, language: str, action: str, *arguments: str | int) -> Button:
    return Button(core_text(services, key, language), action, *arguments, module=core_namespace)


def consent_view(services: Services, language: str) -> View:
    other_language = "en" if language == "pl" else "pl"
    return View(
        text=(bold(core_text(services, "consent.agreement.title", language), ":") + "\n\n"
              + core_text(services, "consent.agreement.text", language)),
        buttons=[
            core_button(services, "consent.language_switch", language,
                        consent_language_action, other_language),
            core_button(services, "consent.yes_button", language, consent_accept_action),
            core_button(services, "consent.no_button", language, consent_decline_action)])


def check_banned(services: Services, user: User) -> View | None:
    if user.role != Role.BANNED:
        return None
    return View(core_text(services, "banned_info", user.language))


def check_consent(services: Services, user: User) -> View | None:
    if user.has_consent:
        return None
    return consent_view(services, user.language)


def module_title(services: Services, module_name: str, language: str) -> str:
    module = services.registry.get(module_name)
    return services.catalog.text(module_name, module.title, language) if module is not None else module_name


def check_access(services: Services, user: User, module_name: str) -> View | None:
    if can_use(services, user, module_name):
        return None
    text = services.catalog.text(core_namespace, "access.denied", user.language,
                                 module=module_title(services, module_name, user.language))
    return View(text, buttons=[core_button(services, "access.request_button", user.language, request_action,
                                           module_name)])


def check_role(services: Services, user: User, required_role: Role, module_name: str = "") -> View | None:
    module = services.registry.get(module_name) if module_name else None
    if module is not None and module.is_guarded and required_role < Role.ADMIN:
        return check_access(services, user, module_name)
    if user.role >= required_role:
        return None
    return View(core_text(services, "permission_denied.text", user.language) + "\n\n"
                + core_text(services, "permission_denied.hint", user.language))


def check(services: Services, user: User, required_role: Role, module_name: str = "") -> View | None:
    for blocked in [check_banned(services, user),
                    check_consent(services, user),
                    check_role(services, user, required_role, module_name)]:
        if blocked is not None:
            return blocked
    return None
