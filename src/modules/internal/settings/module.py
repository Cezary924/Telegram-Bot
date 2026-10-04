from core.api import AdvancedCtx, Button, Module, Role, View, labelled

module = Module(name="settings",
                icons={'name': "⚙️", 'title': "⚙️", 'notifications': "🛎️", 'notifications_all_loud': "🔊",
                       'notifications_all_silent': "🔕", 'notifications_block': "⛔", 'notifications_unblock': "✅",
                       'language': "🌐", 'deletedata': "🗑️"},
                endings={'notifications_text': "🔕", 'language_changed': "✅", 'deletedata_done': "✅"})

loud_mark = "🔊"
silent_mark = "🔕"


@module.command("settings")
def command_settings(ctx: AdvancedCtx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: AdvancedCtx) -> View:
    buttons = [Button(ctx.t("language"), "language"),
               Button(ctx.t("deletedata"), "deletedata")]
    buttons.insert(0, Button(ctx.t("notifications"), "notifications"))
    buttons[-1:-1] = [Button.settings(ctx.t(found.name + ":" + found.title), found.name)
                      for found in ctx.registry.modules()
                      if found.settings_screen is not None and may_open(ctx, found)]
    return View(text=ctx.t("menu") + ":", buttons=buttons)


def may_open(ctx: AdvancedCtx, found: Module) -> bool:
    role = found.settings_screen.role if found.settings_screen is not None else Role.ADMIN
    return ctx.can_use(found.name) if role == Role.USER else ctx.user.role >= role


@module.callback("notifications")
def open_notifications(ctx: AdvancedCtx) -> View:
    return notifications(ctx)


def sources(ctx: AdvancedCtx) -> list[tuple[str, str]]:
    return [("core", ctx.t("core:notifications_label"))] + \
        [(found.name, ctx.t(found.name + ":" + found.notifications))
         for found in ctx.registry.modules() if found.notifications]


@module.view("notifications", parent="menu", title="notifications")
def notifications(ctx: AdvancedCtx) -> View:
    listed = sources(ctx)
    loud = [name for name, _ in listed if ctx.notifications.is_loud(ctx.user.id, name)]
    is_blocked = ctx.notifications.is_blocked(ctx.user.id)
    count = labelled(ctx.t("notifications_count"), str(len(loud)) + "/" + str(len(listed)))
    text = ctx.t("notifications_blocked") if is_blocked else ctx.t("notifications_text") + "\n\n" + count
    buttons = [Button(label + " " + (loud_mark if name in loud else silent_mark), "notifications_toggle", name)
               for name, label in listed]
    buttons += [Button(ctx.t("notifications_all_loud"), "notifications_all", "1"),
                Button(ctx.t("notifications_all_silent"), "notifications_all", "0"),
                Button(ctx.t("notifications_unblock" if is_blocked else "notifications_block"),
                       "notifications_block", "0" if is_blocked else "1")]
    return View(text=text, buttons=buttons)


@module.callback("notifications_toggle")
def toggle_notifications(ctx: AdvancedCtx) -> View:
    source = ctx.arguments[0] if ctx.arguments else ""
    if source not in [name for name, _ in sources(ctx)]:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    is_loud = not ctx.notifications.is_loud(ctx.user.id, source)
    ctx.notifications.set_loud(ctx.user.id, source, is_loud)
    ctx.log("Notifications from '" + source + "' turned " + ("loud" if is_loud else "silent"))
    return notifications(ctx)


@module.callback("notifications_all")
def set_all_notifications(ctx: AdvancedCtx) -> View:
    is_loud = bool(ctx.arguments) and ctx.arguments[0] == "1"
    ctx.notifications.set_all(ctx.user.id, [name for name, _ in sources(ctx)], is_loud)
    ctx.log("All notifications turned " + ("loud" if is_loud else "silent"))
    return notifications(ctx)


@module.callback("notifications_block")
def block_notifications(ctx: AdvancedCtx) -> View:
    is_blocked = bool(ctx.arguments) and ctx.arguments[0] == "1"
    ctx.notifications.set_blocked(ctx.user.id, is_blocked)
    ctx.log("Notifications " + ("blocked" if is_blocked else "unblocked"))
    return notifications(ctx)


@module.callback("language")
def open_language(ctx: AdvancedCtx) -> View:
    return language(ctx)


@module.view("language", parent="menu", title="language")
def language(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("language_question") + ":",
                buttons=[Button(label, "language_set", code) for code, label in ctx.languages])


@module.callback("language_set")
def set_language(ctx: AdvancedCtx) -> View:
    wanted = ctx.arguments[0] if ctx.arguments else ""
    if wanted not in [code for code, _ in ctx.languages]:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.use_language(wanted)
    ctx.log("Language changed to " + wanted)
    ctx.close_screen()
    return View(text=ctx.t("language_changed"))


@module.callback("deletedata")
def open_deletedata(ctx: AdvancedCtx) -> View:
    return deletedata(ctx)


@module.view("deletedata", parent="menu", title="deletedata")
def deletedata(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("deletedata_question"),
                buttons=[Button(ctx.t("core:yes_button"), "deletedata_confirmed")])


@module.callback("deletedata_confirmed")
def delete_data(ctx: AdvancedCtx) -> View:
    ctx.close_screen()
    ctx.users.delete(ctx.user.id)
    ctx.log("Data deleted")
    return View(text=ctx.t("deletedata_done"))
