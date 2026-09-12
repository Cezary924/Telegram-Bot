from core.api import Button, Ctx, Module, Role, View

module = Module(name="demo")


@module.command("demo", role=Role.USER)
def command_demo(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(ctx.t("menu.text"),
                buttons=[Button(ctx.t("menu.open"), "open")])


@module.callback("open")
def open_details(ctx: Ctx) -> View:
    return details(ctx)


@module.view("details", parent="menu", title="details.title")
def details(ctx: Ctx) -> View:
    return View(ctx.t("details.text"))


@module.state("details")
def save_note(ctx: Ctx) -> str:
    ctx.state["note"] = ctx.text
    ctx.db.execute("INSERT INTO module_demo_notes (user_id, note) VALUES (?, ?);",
                   (ctx.user.id, ctx.text))
    return ctx.t("details.saved", note=ctx.text)
