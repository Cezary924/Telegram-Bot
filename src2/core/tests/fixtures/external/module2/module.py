from core.api import Ctx, Module

module = Module(name="module2", requires=["module1"])


@module.command("command2")
def command2(ctx: Ctx) -> str:
    return ctx.t("key1")


@module.job(interval=3600, name="job1")
def job1(ctx) -> None:
    ctx.log("Tick")
