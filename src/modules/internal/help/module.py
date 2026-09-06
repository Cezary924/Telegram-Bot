from core.api import AdvancedCtx, Module, Role, View

module = Module(name="help")


@module.command("help")
def command_help(ctx: AdvancedCtx) -> View:
    listed = [entry(ctx, found) for found in ctx.registry.modules()
              if found.is_internal and is_listed(found)]
    return View(text=ctx.t("intro") + "\n\n" + "\n".join(listed), path=[ctx.t("title")])


def open_command(found: Module) -> str:
    for command in found.commands:
        if command.role <= Role.USER:
            return command.name
    return ""


def is_listed(found: Module) -> bool:
    return not found.commands or bool(open_command(found))


def entry(ctx: AdvancedCtx, found: Module) -> str:
    command = open_command(found)
    return ("/" + command + " - " if command else "") + \
        ctx.t(found.name + ":" + found.title) + " - _" + ctx.t(found.name + ":" + found.description) + "_"
