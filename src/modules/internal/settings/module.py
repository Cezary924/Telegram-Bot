from datetime import date

from core.api import (AdvancedCtx, Answers, Button, Module, Question, Role, View, age_limits, italic, labelled,
                      read_born, sexes)

module = Module(name="settings", place=40,
                icons={'name': "⚙️", 'title': "⚙️", 'notifications': "🛎️", 'notifications_all_loud': "🔊",
                       'notifications_all_silent': "🔕", 'notifications_block': "⛔", 'notifications_unblock': "✅",
                       'language': "🌐", 'profile': "👤", 'set_sex': "🚻", 'set_born': "🎂", 'weight_unit': "⚖️",
                       'height_unit': "📏", 'modules': "🧩", 'previous': "⬅️", 'next': "➡️", 'clear_born': "🙈",
                       'deletedata': "🗑️"},
                endings={'notifications_text': "🔕", 'language_changed': "✅", 'deletedata_done': "✅"})

loud_mark = "🔊"
silent_mark = "🔕"
page_size = 8


@module.command("settings")
def command_settings(ctx: AdvancedCtx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: AdvancedCtx) -> View:
    buttons = [Button(ctx.t("notifications"), "notifications"),
               Button(ctx.t("language"), "language"),
               Button(ctx.t("profile"), "profile")]
    if with_settings(ctx):
        buttons.append(Button(ctx.t("modules"), "modules"))
    return View(text=ctx.t("menu") + ":", buttons=buttons + [Button(ctx.t("deletedata"), "deletedata")])


def with_settings(ctx: AdvancedCtx) -> list[Module]:
    return [found for found in ctx.registry.modules() if found.settings_screen is not None and may_open(ctx, found)]


def may_open(ctx: AdvancedCtx, found: Module) -> bool:
    role = found.settings_screen.role if found.settings_screen is not None else Role.ADMIN
    return ctx.user.role >= role and (not found.is_guarded or role >= Role.ADMIN or ctx.can_use(found.name))


@module.callback("modules")
def open_modules(ctx: AdvancedCtx) -> View:
    return modules(ctx)


@module.view("modules", parent="menu", title="modules")
def modules(ctx: AdvancedCtx) -> View:
    found = with_settings(ctx)
    pages = max(1, -(-len(found) // page_size))
    wanted = ctx.arguments[0] if ctx.arguments and ctx.arguments[0].isdigit() else "0"
    page = min(int(wanted), pages - 1)
    buttons = [Button.settings(ctx.t(each.name + ":" + each.title), each.name)
               for each in found[page * page_size:(page + 1) * page_size]]
    if pages > 1:
        buttons += [Button(ctx.t("previous"), "modules", max(0, page - 1)),
                    Button(ctx.t("next"), "modules", min(pages - 1, page + 1))]
    text = ctx.t("modules_text") if pages == 1 else \
        ctx.t("modules_text") + "\n" + ctx.t("modules_page", page=italic(page + 1), pages=italic(pages))
    return View(text=text, buttons=buttons, argument=str(page))


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


@module.callback("profile")
def open_profile(ctx: AdvancedCtx) -> View:
    return profile(ctx)


@module.view("profile", parent="menu", title="profile")
def profile(ctx: AdvancedCtx) -> View:
    found = ctx.profile
    unknown = ctx.t("profile_unknown")
    lines = [labelled(ctx.t("labels.sex"), ctx.t("sex." + found.sex) if found.sex else unknown),
             labelled(ctx.t("labels.born"), "{} ({})".format(found.born, found.age) if found.born else unknown),
             labelled(ctx.t("labels.weight_unit"), found.weight_name),
             labelled(ctx.t("labels.height_unit"), found.height_name)]
    buttons = [Button(ctx.t("set_sex"), "set_sex"), Button(ctx.t("set_born"), "set_born"),
               Button(ctx.t("weight_unit") + ": " + found.weight_name, "weight_unit"),
               Button(ctx.t("height_unit") + ": " + found.height_name, "height_unit")]
    return View(text=ctx.t("profile_text") + "\n\n" + "\n".join(lines), buttons=buttons)


@module.callback("set_sex")
def open_sex(ctx: AdvancedCtx) -> View:
    return ctx.form("sex")


@module.form("sex", [Question("sex", "choice", choices=sexes)], parent="profile", title="set_sex")
def sex_given(ctx: AdvancedCtx, answers: Answers) -> View:
    ctx.set_profile(sex=answers['sex'])
    ctx.log("Sex set")
    return profile(ctx)


@module.callback("set_born")
def open_born(ctx: AdvancedCtx) -> View:
    return ctx.form("born", known={'low': age_limits[0], 'high': age_limits[1]})


@module.form("born", [Question("born", parse=lambda text, values: read_born(text, date.today()), problem="wrong_born",
                               clear="clear_born")], parent="profile", title="set_born")
def born_given(ctx: AdvancedCtx, answers: Answers) -> View:
    ctx.set_profile(born=answers['born'])
    ctx.log("Birth date " + ("set" if answers['born'] else "forgotten"))
    return profile(ctx)


@module.callback("weight_unit")
def switch_weight_unit(ctx: AdvancedCtx) -> View:
    ctx.set_profile(weight_unit="lb" if ctx.profile.weight_unit == "kg" else "kg")
    ctx.log("Weight unit set to " + ctx.profile.weight_unit)
    return profile(ctx)


@module.callback("height_unit")
def switch_height_unit(ctx: AdvancedCtx) -> View:
    ctx.set_profile(height_unit="ftin" if ctx.profile.height_unit == "cm" else "cm")
    ctx.log("Height unit set to " + ctx.profile.height_unit)
    return profile(ctx)


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
