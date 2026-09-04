import random

from core.api import Ctx, Module, Role, View

module = Module(name="crystalball")

verdicts = [("sure", "✅"), ("maybe", "❔"), ("nope", "❌")]
answers_per_verdict = 5


@module.command("crystalball", role=Role.USER)
def command_crystalball(ctx: Ctx) -> View:
    verdict, mark = random.choice(verdicts)
    answer = random.randint(1, answers_per_verdict)
    return View(text=ctx.t(verdict + "." + str(answer)) + " " + mark, path=["🔮 " + ctx.t("title")])
