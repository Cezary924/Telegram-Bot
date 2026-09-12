from core.api import AdvancedCtx, Button, Module, View

module = Module(name="start")

linked_modules = ["help", "about"]


@module.command("start")
def command_start(ctx: AdvancedCtx) -> View:
    return View(
        text="*👋 " + ctx.t("greeting") + "!*\n\n" + ctx.t("welcome") + " " + ctx.config.bot_name + "! 🤖",
        buttons=[Button.command(ctx.t(name + ":name"), main_command(ctx, name))
                 for name in linked_modules if main_command(ctx, name)]
        + [Button.command(ctx.t("features_button"), "features")], heading=None)


@module.command("features")
def command_features(ctx: AdvancedCtx) -> View:
    listed = [entry(ctx, found) for found in ctx.registry.modules() if not found.is_internal]
    return View(text="\n".join(listed) or ctx.t("nothing"), heading=ctx.t("features_title"))


def main_command(ctx: AdvancedCtx, name: str) -> str:
    found = ctx.registry.get(name)
    return found.commands[0].name if found and found.commands else ""


def entry(ctx: AdvancedCtx, found: Module) -> str:
    command = found.commands[0].name if found.commands else ""
    return ("/" + command + " - " if command else "") + \
        ctx.t(found.name + ":" + found.title) + " - _" + ctx.t(found.name + ":" + found.description) + "_"
