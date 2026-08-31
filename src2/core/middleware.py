from core.context import User
from core.i18n import core_namespace
from core.roles import Role
from core.services import Services
from core.ui.keyboard import Button
from core.ui.view import View

consent_accept_action = "consent_accept"
consent_decline_action = "consent_decline"
consent_language_action = "consent_language"


def core_text(services: Services, key: str, language: str) -> str:
    return services.catalog.text(core_namespace, key, language)


def core_button(services: Services, key: str, language: str, action: str, *arguments: str) -> Button:
    return Button(core_text(services, key, language), action, *arguments, module=core_namespace)


def consent_view(services: Services, language: str) -> View:
    other_language = "en" if language == "pl" else "pl"
    return View(
        text=core_text(services, "consent.question", language),
        buttons=[
            core_button(services, "consent.language_switch", language,
                        consent_language_action, other_language),
            core_button(services, "consent.yes_button", language, consent_accept_action),
            core_button(services, "consent.no_button", language, consent_decline_action)])


def check_banned(services: Services, user: User) -> View | None:
    if user.role != Role.BANNED:
        return None
    return View(core_text(services, "banned_info", user.language), parse_mode=None)


def check_consent(services: Services, user: User) -> View | None:
    if user.has_consent:
        return None
    return consent_view(services, user.language)


def check_role(services: Services, user: User, required_role: Role) -> View | None:
    if user.role >= required_role:
        return None
    return View(core_text(services, "permission_denied", user.language))


def check(services: Services, user: User, required_role: Role) -> View | None:
    for blocked in [check_banned(services, user),
                    check_consent(services, user),
                    check_role(services, user, required_role)]:
        if blocked is not None:
            return blocked
    return None
