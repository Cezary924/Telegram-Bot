from core.api import AdvancedCtx, Button, Module, Role, View, escape

module = Module(name="contact",
                icons={'name': "☎️", 'report': "📨", 'report_title': "📨"},
                endings={'contact': "📨", 'report_question.text': "🫡", 'report_question.hint': "🚀🪱",
                         'report_sent': "😁", 'no_admin': "😞"})


@module.command("contact")
def command_contact(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("contact", username="@" + ctx.config.telegram_username),
                buttons=[Button(ctx.t("report"), "report")])


@module.callback("report")
def open_report(ctx: AdvancedCtx) -> View:
    return report(ctx)


@module.command("report")
def command_report(ctx: AdvancedCtx) -> View:
    return report(ctx)


@module.view("report", title="report_title")
def report(ctx: AdvancedCtx) -> View:
    return View(text=ctx.t("report_question.text") + "\n" + ctx.t("report_question.hint"))


@module.state("report")
def forward_report(ctx: AdvancedCtx) -> str:
    admins = ctx.users.get_by_role(Role.ADMIN)
    ctx.close_screen()
    if not admins:
        ctx.error("A report could not be sent - there are no admins")
        return ctx.t("no_admin")
    for admin in admins:
        ctx.notify(admin['id'], ctx.text_for(admin['id'], "forwarded_to_admin",
                                             name=ctx.user.first_name, id=str(ctx.user.id))
                   + ":\n\n" + escape(ctx.text))
    ctx.log("Report forwarded to the Admin", ctx.text)
    return ctx.t("report_sent")
