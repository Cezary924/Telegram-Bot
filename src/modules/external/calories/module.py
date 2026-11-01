from datetime import date

from core.api import Answers, Button, Ctx, Module, Outcome, Question, View, age_limits, labelled, sexes, years_before

module = Module(name="calories", place=60, is_guarded=True, uses=["bodytracker"],
                icons={'name': "🔥", 'count': "🧮", 'save_new': "💾"},
                endings={'how': "😊", 'saved': "✅"})

activities = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55, 'active': 1.725, 'very_active': 1.9}
saved_keys = ("sex", "age", "height", "weight")
limits = {'age': age_limits, 'height': (100, 250), 'weight': (30, 300)}


def mifflin_st_jeor(sex: str, age: float, height: float, weight: float) -> float:
    return 10 * weight + 6.25 * height - 5 * age + (5 if sex == "male" else -161)


def kcal(value: float) -> str:
    return "{:.0f} kcal".format(value)


@module.expose("need")
def need(_ctx: Ctx, sex: str, age: float, height: float, weight: float, activity: str) -> float:
    return mifflin_st_jeor(sex, age, height, weight) * activities[activity]


@module.command("calories")
def command_calories(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(text=ctx.t("how"), buttons=[Button(ctx.t("count"), "count")])


def known_body(ctx: Ctx) -> dict:
    found = ctx.ask("bodytracker", "latest") or {}
    profile = ctx.profile
    return {'sex': profile.sex, 'age': profile.age, 'height': found.get('height'), 'weight': found.get('weight')}


@module.callback("count")
def count(ctx: Ctx) -> View:
    return ctx.form("need", offered=known_body(ctx))


@module.form("need", [Question("sex", "choice", choices=sexes),
                      Question("age", low=limits['age'][0], high=limits['age'][1]),
                      Question("height", "height", low=limits['height'][0], high=limits['height'][1]),
                      Question("weight", "weight", low=limits['weight'][0], high=limits['weight'][1]),
                      Question("activity", "choice", choices=tuple(activities))], parent="menu", title="count")
def counted(ctx: Ctx, answers: Answers) -> View:
    bmr = mifflin_st_jeor(answers['sex'], answers['age'], answers['height'], answers['weight'])
    ctx.close_screen()
    ctx.log("Daily need counted")
    return View(text="\n".join([
        labelled(ctx.t("labels.bmr"), kcal(bmr)),
        labelled(ctx.t("labels.need"), kcal(bmr * activities[answers['activity']])),
        "",
        labelled(ctx.t("labels.sex"), ctx.t("sex." + answers['sex'])) + source(ctx, answers, "sex"),
        labelled(ctx.t("labels.age"), "{:g}".format(answers['age'])) + source(ctx, answers, "age"),
        labelled(ctx.t("labels.height"), ctx.profile.height(answers['height'])) + source(ctx, answers, "height"),
        labelled(ctx.t("labels.weight"), ctx.profile.weight(answers['weight'])) + source(ctx, answers, "weight"),
        labelled(ctx.t("labels.activity"), ctx.t("activity." + answers['activity']))]),
        buttons=save_buttons(ctx, answers))


def source(ctx: Ctx, answers: Answers, key: str) -> str:
    return "" if key in answers.typed else " (" + ctx.t("from_tracker") + ")"


def shown(value) -> str:
    return value if isinstance(value, str) else "{:g}".format(value)


def save_buttons(ctx: Ctx, answers: Answers) -> list[Button]:
    new = {key: value for key, value in answers.new(saved_keys).items()
           if key in ("sex", "age") or ctx.has_module("bodytracker")}
    if not new:
        return []
    return [Button(ctx.t("save_new"), "save", *[shown(new[key]) if key in new else "" for key in saved_keys])]


def saved_values(arguments: tuple[str, ...]) -> dict:
    try:
        return {key: value if key == "sex" else float(value)
                for key, value in zip(saved_keys, arguments) if value}
    except ValueError:
        return {}


@module.callback("save")
def save(ctx: Ctx) -> View:
    values = saved_values(ctx.arguments)
    if not values or values.get('sex', sexes[0]) not in sexes \
            or not limits['age'][0] <= values.get('age', limits['age'][0]) <= limits['age'][1]:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    if 'sex' in values:
        ctx.set_profile(sex=values['sex'])
    if 'age' in values:
        ctx.set_profile(born=years_before(date.today(), int(values['age'])).isoformat())
    body = {key: values[key] for key in ("height", "weight") if key in values}
    if body:
        ctx.ask("bodytracker", "save", body)
    if ctx.message is not None:
        ctx.remove_buttons(ctx.message.message_id)
    ctx.log("Body data saved")
    return View(text=ctx.t("saved"))


# ----- the assistant -----

@module.action("need", parameters={'activity': str, 'sex': str, 'age': float, 'height': float, 'weight': float},
               optional=["sex", "age", "height", "weight"])
def act_need(ctx: Ctx, activity: str, sex: str | None, age: float | None, height: float | None,
             weight: float | None) -> Outcome:
    found = known_body(ctx)
    given = {'sex': sex, 'age': age, 'height': height, 'weight': weight}
    body: dict = {key: found.get(key) if value is None else value for key, value in given.items()}
    if activity not in activities or body['sex'] not in (None, *sexes):
        return Outcome.refused(ctx.t("wrong", activities=", ".join(activities), sexes=", ".join(sexes)))
    missing = [key for key, value in body.items() if value is None and key != "sex"]
    if missing:
        return Outcome.refused(ctx.t("missing", missing=", ".join(missing)))
    wrong = [key for key, (low, high) in limits.items() if not low <= body[key] <= high]
    if wrong:
        return Outcome.refused(ctx.t("out_of_range", wrong=", ".join(wrong)))
    sex = body['sex'] or "undisclosed"
    bmr = mifflin_st_jeor(sex, body['age'], body['height'], body['weight'])
    return Outcome.done({'bmr_kcal': round(bmr), 'need_kcal': round(bmr * activities[activity]), 'sex': sex,
                         'age': body['age'], 'height_cm': body['height'], 'weight_kg': body['weight']})
