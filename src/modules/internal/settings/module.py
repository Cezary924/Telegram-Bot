from core.api import AdvancedCtx, Button, Module, Role, View

module = Module(name="settings")


@module.command("settings")
def command_settings(ctx: AdvancedCtx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: AdvancedCtx) -> View:
    buttons = [Button(ctx.t("language"), "language"),
               Button(ctx.t("deletedata"), "deletedata")]
    if ctx.user.role >= Role.USER:
        buttons.insert(0, Button(ctx.t("notifications"), "notifications"))
    return View(text=ctx.t("menu"), path=[ctx.t("title")], buttons=buttons)


@module.callback("notifications", role=Role.USER)
def open_notifications(ctx: AdvancedCtx) -> View:
    return notifications(ctx)


@module.view("notifications")
def notifications(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("notifications_question"),
                path=[ctx.t("title"), ctx.t("notifications")],
                buttons=[Button(ctx.t("core:yes_button"), "notifications_set", "1"),
                         Button(ctx.t("core:no_button"), "notifications_set", "0")],
                columns=2)


@module.callback("notifications_set", role=Role.USER)
def set_notifications(ctx: AdvancedCtx) -> View:
    wanted = ctx.arguments and ctx.arguments[0] == "1"
    ctx.settings.set_notifications(ctx.user.id, wanted)
    ctx.log("Notifications turned " + ("on" if wanted else "off"))
    ctx.close_screen()
    return View(text=ctx.t("notifications_on" if wanted else "notifications_off"),
                path=[ctx.t("title"), ctx.t("notifications")])


@module.callback("language")
def open_language(ctx: AdvancedCtx) -> View:
    return language(ctx)


@module.view("language")
def language(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("language_question"),
                path=[ctx.t("title"), ctx.t("language")],
                buttons=[Button(label, "language_set", code) for code, label in ctx.languages])


@module.callback("language_set")
def set_language(ctx: AdvancedCtx) -> View:
    wanted = ctx.arguments[0] if ctx.arguments else ""
    if wanted not in [code for code, _ in ctx.languages]:
        return View(ctx.t("core:not_working_buttons"), parse_mode=None)
    ctx.use_language(wanted)
    ctx.log("Language changed to " + wanted)
    ctx.close_screen()
    return View(text=ctx.t("language_changed"), path=[ctx.t("title"), ctx.t("language")])


@module.callback("deletedata")
def open_deletedata(ctx: AdvancedCtx) -> View:
    return deletedata(ctx)


@module.view("deletedata")
def deletedata(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("deletedata_question"),
                path=[ctx.t("title"), ctx.t("deletedata")],
                buttons=[Button(ctx.t("core:yes_button"), "deletedata_confirmed")])


@module.callback("deletedata_confirmed")
def delete_data(ctx: AdvancedCtx) -> View:
    ctx.close_screen()
    ctx.users.delete(ctx.user.id)
    ctx.log("Data deleted")
    return View(text=ctx.t("deletedata_done"), path=[ctx.t("title"), ctx.t("deletedata")])
