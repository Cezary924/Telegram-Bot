from core.api import Ctx, Module, Role

module = Module(name="module1", features=["feature1"], tokens=["token1"])


@module.command("command1", role=Role.USER)
def command1(ctx: Ctx) -> str:
    return ctx.t("key1")
