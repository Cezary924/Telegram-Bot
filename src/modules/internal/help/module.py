from core.api import AdvancedCtx, Module, View

module = Module(name="help")


@module.command("help")
def command_help(ctx: AdvancedCtx) -> View:
    listed = [entry(ctx, found) for found in ctx.registry.modules() if found.is_internal]
    return View(text=ctx.t("intro") + "\n\n" + "\n".join(listed), path=[ctx.t("title")])


def entry(ctx: AdvancedCtx, found: Module) -> str:
    command = found.commands[0].name if found.commands else ""
    return ("/" + command + " - " if command else "") + \
        ctx.t(found.name + ":" + found.title) + " - _" + ctx.t(found.name + ":" + found.description) + "_"
