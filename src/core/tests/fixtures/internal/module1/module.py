from core.api import Ctx, Module

module = Module(name="module1", is_guarded=True, tokens=["token1"])


@module.command("command1")
def command1(ctx: Ctx) -> str:
    return ctx.t("key1")
