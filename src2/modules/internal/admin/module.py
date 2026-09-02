import os
import signal

import telebot

from core.api import AdvancedCtx, Button, Module, Role, View
from core import paths
from core.loader import discover

module = Module(name="admin")

page_size = 8
log_lines = 30
alerts_key = "alerts"
manageable_roles = [Role.BANNED, Role.GUEST, Role.USER, Role.ADMIN]


@module.command("admin", role=Role.ADMIN)
def command_admin(ctx: AdvancedCtx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("menu"), path=[ctx.t("title")],
                buttons=[Button(ctx.t("users"), "users"),
                         Button(ctx.t("statistics"), "statistics"),
                         Button(ctx.t("announcement"), "announcement"),
                         Button(ctx.t("alerts"), "alerts"),
                         Button(ctx.t("modules"), "modules"),
                         Button(ctx.t("bot"), "bot")])


# ----- users -----

@module.callback("users", role=Role.ADMIN)
def open_users(ctx: AdvancedCtx) -> View:
    return users(ctx)


@module.view("users")
def users(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("users_menu"), path=[ctx.t("title"), ctx.t("users")],
                buttons=[Button(ctx.t("users_list"), "list", 0),
                         Button(ctx.t("users_search"), "search"),
                         Button(ctx.t("users_forward"), "forward")])


@module.callback("list", role=Role.ADMIN)
def open_list(ctx: AdvancedCtx) -> View:
    return listing(ctx)


@module.view("list")
def listing(ctx: AdvancedCtx) -> View:
    page = int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0
    people = ctx.users.get_all()
    pages = max(1, -(-len(people) // page_size))
    page = min(page, pages - 1)
    shown = people[page * page_size:(page + 1) * page_size]
    buttons = [Button(label(row), "user", row['id']) for row in shown]
    if pages > 1:
        buttons.append(Button(ctx.t("previous"), "list", max(0, page - 1)))
        buttons.append(Button(ctx.t("next"), "list", min(pages - 1, page + 1)))
    return View(text=ctx.t("users_list_text", page=str(page + 1), pages=str(pages),
                           total=str(len(people))),
                path=[ctx.t("title"), ctx.t("users"), ctx.t("users_list")],
                buttons=buttons, argument=str(page), columns=1 if pages == 1 else 2)


def label(row) -> str:
    return (row['first_name'] or "?") + " (" + str(row['id']) + ")"


@module.callback("search", role=Role.ADMIN)
def open_search(ctx: AdvancedCtx) -> View:
    return search(ctx)


@module.view("search")
def search(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("users_search_text"),
                path=[ctx.t("title"), ctx.t("users"), ctx.t("users_search")])


@module.state("search", role=Role.ADMIN)
def found_by_id(ctx: AdvancedCtx) -> View:
    if not ctx.text.strip().isdigit() or not ctx.users.exists(int(ctx.text.strip())):
        return View(text=ctx.t("users_search_missing"),
                    path=[ctx.t("title"), ctx.t("users"), ctx.t("users_search")])
    ctx.close_screen()
    return details(ctx, int(ctx.text.strip()))


@module.callback("forward", role=Role.ADMIN)
def open_forward(ctx: AdvancedCtx) -> View:
    return forward(ctx)


@module.view("forward")
def forward(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("users_forward_text"),
                path=[ctx.t("title"), ctx.t("users"), ctx.t("users_forward")])


@module.state("forward", role=Role.ADMIN)
def found_by_forward(ctx: AdvancedCtx) -> View:
    sender = forwarded_sender(ctx)
    if sender is None:
        return View(text=ctx.t("users_forward_missing"),
                    path=[ctx.t("title"), ctx.t("users"), ctx.t("users_forward")])
    ctx.close_screen()
    return details(ctx, sender)


def forwarded_sender(ctx: AdvancedCtx) -> int | None:
    origin = ctx.message.forward_origin if ctx.message is not None else None
    if isinstance(origin, telebot.types.MessageOriginUser):
        return origin.sender_user.id
    return None


@module.callback("user", role=Role.ADMIN)
def open_details(ctx: AdvancedCtx) -> View:
    return details(ctx)


@module.view("user")
def details(ctx: AdvancedCtx, user_id: int = 0) -> View:
    user_id = user_id or wanted_id(ctx)
    row = ctx.users.get(user_id)
    if row is None:
        return View(text=ctx.t("users_search_missing"), path=[ctx.t("title"), ctx.t("users")])
    role = Role.from_value(row['role'])
    return View(
        text=ctx.t("user_text", name=label(row), username="@" + (row['username'] or "?"),
                   role=ctx.t("core:" + role.key), consent=ctx.t("has_consent" if row['has_consent'] else "no_consent"),
                   language=ctx.language_of(user_id), seen=row['seen_at'], created=row['created_at']),
        path=[ctx.t("title"), ctx.t("users"), label(row)],
        buttons=[Button(ctx.t("user_role"), "role", user_id),
                 Button(ctx.t("user_wipe"), "wipe", user_id)],
        argument=str(user_id))


def wanted_id(ctx: AdvancedCtx) -> int:
    return int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0


@module.callback("role", role=Role.ADMIN)
def open_role(ctx: AdvancedCtx) -> View:
    return role_picker(ctx)


@module.view("role")
def role_picker(ctx: AdvancedCtx) -> View:
    user_id = wanted_id(ctx)
    current = ctx.users.get_role(user_id)
    return View(text=ctx.t("role_text", role=ctx.t("core:" + current.key)),
                path=[ctx.t("title"), ctx.t("users"), ctx.t("user_role")],
                buttons=[Button(ctx.t("core:" + role.key), "role_set", user_id, int(role))
                         for role in manageable_roles if role != current],
                argument=str(user_id))


@module.callback("role_set", role=Role.ADMIN)
def choose_role(ctx: AdvancedCtx) -> View:
    user_id, role = wanted_change(ctx)
    if role is None:
        return View(ctx.t("core:not_working_buttons"), parse_mode=None)
    if role > ctx.users.get_role(user_id):
        return apply_role(ctx, user_id, role)
    return View(text=ctx.t("role_confirm", role=ctx.t("core:" + role.key)),
                path=[ctx.t("title"), ctx.t("users"), ctx.t("user_role")],
                buttons=[Button(ctx.t("core:yes_button"), "role_confirmed", user_id, int(role))])


@module.callback("role_confirmed", role=Role.ADMIN)
def confirm_role(ctx: AdvancedCtx) -> View:
    user_id, role = wanted_change(ctx)
    if role is None:
        return View(ctx.t("core:not_working_buttons"), parse_mode=None)
    ctx.close_screen()
    return apply_role(ctx, user_id, role)


def wanted_change(ctx: AdvancedCtx) -> tuple[int, Role | None]:
    if len(ctx.arguments) < 2 or not ctx.arguments[0].isdigit():
        return 0, None
    user_id = int(ctx.arguments[0])
    role = Role.from_value(ctx.arguments[1])
    return user_id, role if str(int(role)) == ctx.arguments[1] else None


def apply_role(ctx: AdvancedCtx, user_id: int, role: Role) -> View:
    ctx.users.set_role(user_id, role)
    ctx.log("Role of " + str(user_id) + " changed to " + role.name)
    ctx.notify(user_id, ctx.text_for(user_id, "role_changed",
                                     role=ctx.text_for(user_id, "core:" + role.key)))
    return View(text=ctx.t("role_done", role=ctx.t("core:" + role.key)),
                path=[ctx.t("title"), ctx.t("users"), ctx.t("user_role")])


@module.callback("wipe", role=Role.ADMIN)
def open_wipe(ctx: AdvancedCtx) -> View:
    return wipe(ctx)


@module.view("wipe")
def wipe(ctx: AdvancedCtx) -> View:
    user_id = wanted_id(ctx)
    return View(text=ctx.t("wipe_text"),
                path=[ctx.t("title"), ctx.t("users"), ctx.t("user_wipe")],
                buttons=[Button(ctx.t("core:yes_button"), "wipe_confirmed", user_id)],
                argument=str(user_id))


@module.callback("wipe_confirmed", role=Role.ADMIN)
def confirm_wipe(ctx: AdvancedCtx) -> View:
    user_id = wanted_id(ctx)
    ctx.users.delete(user_id)
    ctx.log("Data of " + str(user_id) + " deleted")
    ctx.close_screen()
    return View(text=ctx.t("wipe_done"), path=[ctx.t("title"), ctx.t("users"), ctx.t("user_wipe")])


# ----- statistics -----

@module.callback("statistics", role=Role.ADMIN)
def open_statistics(ctx: AdvancedCtx) -> View:
    return statistics(ctx)


@module.view("statistics")
def statistics(ctx: AdvancedCtx) -> View:
    counts = ctx.users.count_by_role()
    people = "\n".join(ctx.t("core:" + role.key) + ": _" + str(counts.get(role, 0)) + "_"
                       for role in reversed(manageable_roles))
    return View(text=ctx.t("statistics_text", people=people,
                           total=str(sum(counts.values())), consent=str(ctx.users.count_with_consent()),
                           modules=str(len(ctx.registry.names())), version=str(ctx.version),
                           uptime=uptime_text(ctx)),
                path=[ctx.t("title"), ctx.t("statistics")])


def uptime_text(ctx: AdvancedCtx) -> str:
    seconds = int(ctx.uptime.total_seconds())
    return (str(seconds // 86400) + "d " + str(seconds // 3600 % 24) + "h "
            + str(seconds // 60 % 60) + "m")


# ----- announcement -----

@module.callback("announcement", role=Role.ADMIN)
def open_announcement(ctx: AdvancedCtx) -> View:
    return announcement(ctx)


@module.view("announcement")
def announcement(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("announcement_text"), path=[ctx.t("title"), ctx.t("announcement")])


@module.state("announcement", role=Role.ADMIN, is_background=True)
def send_announcement(ctx: AdvancedCtx) -> View:
    reached = 0
    for row in ctx.users.get_all():
        if row['id'] == ctx.user.id or not ctx.settings.has_notifications(row['id']):
            continue
        ctx.notify(row['id'], View(ctx.text, parse_mode=None))
        reached += 1
    ctx.log("Announcement sent to " + str(reached) + " users", ctx.text)
    ctx.close_screen()
    return View(text=ctx.t("announcement_done", reached=str(reached)),
                path=[ctx.t("title"), ctx.t("announcement")])


# ----- alerts -----

@module.callback("alerts", role=Role.ADMIN)
def open_alerts(ctx: AdvancedCtx) -> View:
    return alerts(ctx)


@module.view("alerts")
def alerts(ctx: AdvancedCtx) -> View:
    is_on = ctx.settings.has_admin_alerts(ctx.user.id)
    return View(text=ctx.t("alerts_text", state=ctx.t("turned_on" if is_on else "turned_off")),
                path=[ctx.t("title"), ctx.t("alerts")],
                buttons=[Button(ctx.t("core:yes_button"), "alerts_set", "1"),
                         Button(ctx.t("core:no_button"), "alerts_set", "0")],
                columns=2)


@module.callback("alerts_set", role=Role.ADMIN)
def set_alerts(ctx: AdvancedCtx) -> View:
    is_on = bool(ctx.arguments) and ctx.arguments[0] == "1"
    ctx.settings.set_admin_alerts(ctx.user.id, is_on)
    ctx.log("New user alerts turned " + ("on" if is_on else "off"))
    ctx.close_screen()
    return View(text=ctx.t("alerts_done", state=ctx.t("turned_on" if is_on else "turned_off")),
                path=[ctx.t("title"), ctx.t("alerts")])


# ----- modules -----

@module.callback("modules", role=Role.ADMIN)
def open_modules(ctx: AdvancedCtx) -> View:
    return modules(ctx)


@module.view("modules")
def modules(ctx: AdvancedCtx) -> View:
    found = discover(paths.external_modules_dir)
    buttons = [Button(("✅ " if ctx.config.is_module_enabled(name) else "❌ ") + name,
                      "module_toggle", name) for name in found]
    return View(text=ctx.t("modules_text") if found else ctx.t("modules_none"),
                path=[ctx.t("title"), ctx.t("modules")], buttons=buttons)


@module.callback("module_toggle", role=Role.ADMIN)
def toggle_module(ctx: AdvancedCtx) -> View:
    name = ctx.arguments[0] if ctx.arguments else ""
    if name not in discover(paths.external_modules_dir):
        return View(ctx.t("core:not_working_buttons"), parse_mode=None)
    wanted = not ctx.config.is_module_enabled(name)
    ctx.config.set_module_enabled(name, wanted)
    ctx.log("Module '" + name + "' turned " + ("on" if wanted else "off"))
    ctx.close_screen()
    return View(text=ctx.t("modules_done", module=name, state=ctx.t("turned_on" if wanted else "turned_off")),
                path=[ctx.t("title"), ctx.t("modules")],
                buttons=[Button(ctx.t("bot_restart"), "restart")])


# ----- bot -----

@module.callback("bot", role=Role.ADMIN)
def open_bot(ctx: AdvancedCtx) -> View:
    return bot_menu(ctx)


@module.view("bot")
def bot_menu(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("bot_text", version=str(ctx.version), uptime=uptime_text(ctx)),
                path=[ctx.t("title"), ctx.t("bot")],
                buttons=[Button(ctx.t("bot_log"), "log"),
                         Button(ctx.t("bot_restart"), "restart")])


@module.callback("log", role=Role.ADMIN)
def open_log(ctx: AdvancedCtx) -> View:
    return log(ctx)


@module.view("log")
def log(ctx: AdvancedCtx) -> View:
    tail = read_log()
    return View(text="```\n" + tail + "\n```" if tail else ctx.t("bot_log_none"),
                path=[ctx.t("title"), ctx.t("bot"), ctx.t("bot_log")])


def stop_process() -> None:
    os.kill(os.getpid(), signal.SIGINT)


def read_log() -> str:
    if not os.path.isdir(paths.log_dir):
        return ""
    files = sorted(name for name in os.listdir(paths.log_dir) if name.endswith(".log"))
    if not files:
        return ""
    with open(os.path.join(paths.log_dir, files[-1]), encoding='utf8', errors='replace') as f:
        return "".join(f.readlines()[-log_lines:]).strip()


@module.callback("restart", role=Role.ADMIN)
def open_restart(ctx: AdvancedCtx) -> View:
    return restart(ctx)


@module.view("restart")
def restart(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("bot_restart_text"),
                path=[ctx.t("title"), ctx.t("bot"), ctx.t("bot_restart")],
                buttons=[Button(ctx.t("core:yes_button"), "restart_confirmed")])


@module.callback("restart_confirmed", role=Role.ADMIN)
def confirm_restart(ctx: AdvancedCtx) -> None:
    ctx.close_screen()
    ctx.reply(View(text=ctx.t("bot_restart_done"), path=[ctx.t("title"), ctx.t("bot")]))
    ctx.log("Restart requested")
    stop_process()
