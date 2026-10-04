import random

from core.api import Ctx, Module, View

module = Module(name="crystalball", is_guarded=True,
                icons={'name': "🔮"})

verdicts = [("sure", "✅"), ("maybe", "❔"), ("nope", "❌")]
answers_per_verdict = 5


@module.command("crystalball")
def command_crystalball(ctx: Ctx) -> View:
    verdict, mark = random.choice(verdicts)
    answer = random.randint(1, answers_per_verdict)
    return View(text=ctx.t(verdict + "." + str(answer)) + " " + mark)
