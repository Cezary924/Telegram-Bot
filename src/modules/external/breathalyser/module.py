import io
import itertools
import math
import re
from datetime import date, datetime, timedelta

from matplotlib.dates import DateFormatter, date2num
from matplotlib.figure import Figure

from core.api import (Answers, Button, Ctx, Module, Outcome, Problem, Question, View, age_limits, bold, labelled,
                      plain, sexes, years_before)

module = Module(name="breathalyser", place=90, is_guarded=True, uses=["bodytracker", "drinktracker"],
                icons={'name': "🌬️", 'count': "🧮", 'settings_button': "⚙️", 'save_new': "💾", 'warning': "⚠️",
                       'rates': "⏱️"},
                endings={'how': "😊", 'saved': "✅"})

ethanol_density = 0.789
blood_water = 0.8
breath_ratio = 2.0
foods = {'empty': (3.8, 1.0), 'little': (2.3, 1.2), 'meal': (1.4, 1.39)}
default_food = "little"
michaelis = 0.05
eliminations = [0.10, 0.12, 0.15, 0.17, 0.20]
default_elimination = 0.15
after_use = 0.2
insobriety = 0.5
saved_keys = ("sex", "age", "height", "weight")
limits = {'age': age_limits, 'height': (100, 250), 'weight': (30, 300)}
hours_limit = 48
volume_limits = (10.0, 3000.0)
strength_limits = (0.5, 96.0)
drinks_limit = 30
step_hours = 1 / 60
horizon_hours = 72.0
absorbed_hours = 6.0
sober_level = 0.005
settled = 0.001
caption_step = timedelta(minutes=30)
moment_format = "%Y-%m-%d %H:%M"
elimination_key = "elimination"
number_pattern = re.compile(r"\d+(?:[.,]\d+)?")
run_pattern = re.compile(r"\d+(?:[.,]\d+)*")
separator_pattern = re.compile(r"[+;\n]|,(?!\d)|(?<!\d),")
readings_limit = 256
colors = {'surface': "#fcfcfb", 'ink': "#0b0b0b", 'muted': "#898781", 'grid': "#e1e0d9", 'axis': "#c3c2b7",
          'line': "#2a78d6", 'after_use': "#fab219", 'insobriety': "#d03b3b"}


# ----- the model -----

def grams_of(volume: float, strength: float) -> float:
    return volume * strength / 100 * ethanol_density


def body_water(sex: str, age: float, height: float, weight: float) -> float:
    if sex == "male":
        return 2.447 - 0.09516 * age + 0.1074 * height + 0.3362 * weight
    return -2.097 + 0.1069 * height + 0.2466 * weight


def per_gram(body: tuple) -> float:
    return blood_water / body_water(*body)


def waiting(drinks: list[tuple[float, float, str]], moment: float) -> float:
    return sum(grams * math.exp(-foods[food][0] * max(0.0, moment - start)) for start, grams, food in drinks)


def burning(drinks: list[tuple[float, float, str]], elimination: float) -> float:
    return elimination * foods[drinks[0][2]][1] if drinks else elimination


def step(drinks: list[tuple[float, float, str]], factor: float, rate: float, level: float, previous: float,
         moment: float) -> float:
    absorbed = sum(grams * (math.exp(-foods[food][0] * max(0.0, previous - start))
                            - math.exp(-foods[food][0] * max(0.0, moment - start)))
                   for start, grams, food in drinks)
    return max(0.0, level + absorbed * factor - rate * (moment - previous) * level / (michaelis + level))


def is_cleared(drinks: list[tuple[float, float, str]], factor: float, level: float, moment: float) -> bool:
    return level < sober_level and waiting(drinks, moment) * factor < settled


def advance(drinks: list[tuple[float, float, str]], factor: float, rate: float, level: float, since: float,
            until: float) -> float:
    while since < until:
        moment = min(until, since + step_hours)
        level, since = step(drinks, factor, rate, level, since, moment), moment
    return level


def simulate(drinks: list[tuple[float, float, str]], factor: float, elimination: float) -> list[tuple[float, float]]:
    last = max((start for start, _, _ in drinks), default=0.0)
    rate = burning(drinks, elimination)
    level, points = 0.0, [(0.0, 0.0)]
    while points[-1][0] < horizon_hours:
        previous = points[-1][0]
        moment = previous + step_hours
        level = step(drinks, factor, rate, level, previous, moment)
        if moment > last and is_cleared(drinks, factor, level, moment):
            points.append((moment, 0.0))
            break
        points.append((moment, level))
    return points


def level_at(points: list[tuple[float, float]], hours: float) -> float:
    return next((level for moment, level in points if moment >= hours), 0.0)


def peak(points: list[tuple[float, float]]) -> tuple[float, float]:
    return max(points, key=lambda point: point[1])


def level_name(value: float) -> str:
    if value >= insobriety:
        return "insobriety"
    return "after_use" if value >= after_use else "below"


def shown_level(value: float) -> str:
    return "{:.2f}‰ ({:.2f} mg/dm³)".format(value, value / breath_ratio)


def number(text: str) -> float:
    return float(text.replace(",", "."))


def readings(run: str) -> list[list[float]]:
    pieces = re.split(r"([.,])", run)
    digits, marks = pieces[0::2], pieces[1::2]
    found = []
    for cuts in itertools.product((False, True), repeat=len(marks)):
        if any(cut and mark == "." for cut, mark in zip(cuts, marks)):
            continue
        numbers, current = [], [digits[0]]
        for cut, piece in zip(cuts, digits[1:]):
            if cut:
                numbers.append(current)
                current = [piece]
            else:
                current.append(piece)
        numbers.append(current)
        if all(len(one) <= 2 for one in numbers):
            found.append([float(".".join(one)) for one in numbers])
    found.sort(key=len)
    return found


def paired(values: list[float]) -> list[float] | None:
    if len(values) % 2:
        return None
    pairs = list(zip(values[0::2], values[1::2]))
    if not all(volume_limits[0] <= volume <= volume_limits[1] and strength_limits[0] <= strength <= strength_limits[1]
               for volume, strength in pairs):
        return None
    return [grams_of(volume, strength) for volume, strength in pairs]


def parse_part(part: str) -> list[float] | None:
    options = [readings(run) for run in run_pattern.findall(part)]
    if not options or math.prod(len(one) for one in options) > readings_limit:
        return None
    for chosen in sorted(itertools.product(*options), key=lambda picked: sum(len(one) for one in picked)):
        found = paired([value for one in chosen for value in one])
        if found is not None:
            return found
    return None


def parse_drinks(text: str) -> list[float] | None:
    found = []
    for part in separator_pattern.split(text):
        if not part.strip():
            continue
        drinks = parse_part(part)
        if drinks is None:
            return None
        found += drinks
    return found if 0 < len(found) <= drinks_limit else None


def read_last(text: str, values: dict) -> float | Problem:
    found = number_pattern.fullmatch(text.strip())
    value = number(found.group()) if found else -1.0
    if 0 <= value <= values['hours']:
        return value
    return Problem("wrong_last", {'hours': "{:g}".format(values['hours'])})


def spread(grams: list[float], hours: float, food: str) -> list[tuple[float, float, str]]:
    return [(hours * index / max(1, len(grams) - 1), one, food) for index, one in enumerate(grams)]


def timeline(drinks: list) -> tuple[datetime, list[tuple[float, float, str]]]:
    first = datetime.fromisoformat(drinks[0][0])
    found, food = [], default_food
    for moment, grams, eaten in drinks:
        food = eaten or food
        found.append(((datetime.fromisoformat(moment) - first).total_seconds() / 3600, grams, food))
    return first, found


def surely_sober(drinks: list[tuple[float, float, str]], hours: float, factor: float, rate: float) -> bool:
    total = sum(grams for _, grams, _ in drinks) * factor
    clearing = (total + michaelis * math.log(max(total / sober_level, 1.0))) / rate
    return hours - drinks[-1][0] > absorbed_hours + clearing


def split(drinks: list, factor: float, elimination: float) -> list[list[int]]:
    groups: list[list[int]] = []
    level, reached = 0.0, 0.0
    for index, (moment, _, _) in enumerate(drinks):
        if groups:
            first, model = timeline([drinks[one] for one in groups[-1]])
            hours = (datetime.fromisoformat(moment) - first).total_seconds() / 3600
            rate = burning(model, elimination)
            if not surely_sober(model, hours, factor, rate):
                level, reached = advance(model, factor, rate, level, reached, hours), hours
                if not is_cleared(model, factor, level, hours):
                    groups[-1].append(index)
                    continue
        groups.append([index])
        level, reached = 0.0, 0.0
    return groups


def per_hour(ctx: Ctx, rate: float) -> str:
    return "{:.2f}".format(rate) + ctx.t("per_hour")


def elimination_of(ctx: Ctx) -> float:
    return float(ctx.state.get(elimination_key) or default_elimination)


def curve_of(ctx: Ctx, drinks: list, body: tuple) -> tuple[datetime, list[tuple[float, float]]]:
    first, model = timeline(drinks)
    return first, simulate(model, per_gram(body), elimination_of(ctx))


def report_lines(ctx: Ctx, first: datetime, points: list[tuple[float, float]], now: datetime) -> list[str]:
    sober = first + timedelta(hours=points[-1][0])
    top_moment, top = peak(points)
    lines = [labelled(ctx.t("labels.peak"), shown_level(top) + ", " + (first + timedelta(hours=top_moment))
                      .strftime(moment_format)),
             labelled(ctx.t("labels.sober"), sober.strftime(moment_format))]
    if now < sober:
        current = level_at(points, (now - first).total_seconds() / 3600)
        lines = [labelled(ctx.t("labels.now"), shown_level(current)),
                 labelled(ctx.t("labels.level"), ctx.t("level." + level_name(current)))] + lines
    return lines


def limits_text(ctx: Ctx) -> str:
    return ctx.t("limits", after_use=bold(shown_level(after_use)), insobriety=bold(shown_level(insobriety)))


def curve_lines(ctx: Ctx, first: datetime, points: list[tuple[float, float]]) -> list[str]:
    lines, wanted = [], first
    for moment, level in points:
        at = first + timedelta(hours=moment)
        if at >= wanted:
            lines.append(at.strftime("%H:%M") + " - " + shown_level(level))
            wanted = at + caption_step
    top_moment, top = peak(points)
    return lines + [labelled(ctx.t("labels.peak"), shown_level(top) + ", "
                             + (first + timedelta(hours=top_moment)).strftime("%H:%M"))]


def drawing(ctx: Ctx, first: datetime, points: list[tuple[float, float]]) -> bytes:
    now = datetime.now()
    sober = first + timedelta(hours=points[-1][0])
    return draw([(first + timedelta(hours=moment), level) for moment, level in points], now if now < sober else None,
                {key: plain(ctx.t("chart." + key)) for key in ("title", "now", "after_use", "insobriety", "sober")})


# ----- what the other modules read -----

@module.expose("sessions")
def sessions(ctx: Ctx, drinks: list, body: tuple) -> list[list[int]]:
    return split(drinks, per_gram(body), elimination_of(ctx))


@module.expose("curve")
def curve(ctx: Ctx, drinks: list, body: tuple) -> dict:
    first, points = curve_of(ctx, drinks, body)
    top_moment, top = peak(points)
    return {'peak': top, 'peak_at': first + timedelta(hours=top_moment),
            'sober_at': first + timedelta(hours=points[-1][0])}


@module.expose("report")
def report(ctx: Ctx, drinks: list, body: tuple) -> list[str]:
    first, points = curve_of(ctx, drinks, body)
    return report_lines(ctx, first, points, datetime.now()) + ["", limits_text(ctx), "", ctx.t("warning")]


@module.expose("chart")
def chart(ctx: Ctx, drinks: list, body: tuple) -> dict:
    first, points = curve_of(ctx, drinks, body)
    return {'photo': drawing(ctx, first, points), 'text': "\n".join(curve_lines(ctx, first, points))}


# ----- what is known -----

def known_body(ctx: Ctx) -> dict:
    found = ctx.ask("bodytracker", "latest") or {}
    profile = ctx.profile
    return {'sex': profile.sex, 'age': profile.age, 'height': found.get('height'), 'weight': found.get('weight')}


def offered(ctx: Ctx) -> list[tuple[str, dict]]:
    body = known_body(ctx)
    session = ctx.ask("drinktracker", "session")
    if not session:
        return [("offer.body", body)]
    first, last = (datetime.fromisoformat(session['drinks'][index][0]) for index in (0, -1))
    return [("offer.body", body),
            ("offer.drinks", {'drinks': session['drinks'], 'grams': [grams for _, grams, _ in session['drinks']],
                              'hours': min(hours_limit, hours_since(first)),
                              'last': min(hours_limit, hours_since(last)),
                              'food': session['drinks'][0][2] or default_food})]


def hours_since(moment: datetime) -> float:
    return (datetime.now() - moment).total_seconds() / 3600


def entered(answers: Answers) -> tuple[datetime, list[tuple[float, float, str]]]:
    if answers.get('drinks'):
        return timeline(answers['drinks'])
    first = datetime.now().replace(microsecond=0) - timedelta(hours=answers['hours'])
    return first, spread(answers['grams'], answers['hours'] - (answers.get('last') or 0.0), answers['food'])


# ----- menu -----

@module.command("breathalyser")
def command_breathalyser(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(text=ctx.t("how") + "\n\n" + ctx.t("warning"),
                buttons=[Button(ctx.t("count"), "count"), Button.settings(ctx.t("settings_button"), module.name)])


@module.callback("count")
def count(ctx: Ctx) -> View:
    return ctx.form("estimate", known={'limit': drinks_limit}, offered=offered(ctx))


@module.form("estimate", [Question("sex", "choice", choices=sexes),
                          Question("age", low=limits['age'][0], high=limits['age'][1]),
                          Question("height", "height", low=limits['height'][0], high=limits['height'][1]),
                          Question("weight", "weight", low=limits['weight'][0], high=limits['weight'][1]),
                          Question("grams", parse=lambda text, values: parse_drinks(text), problem="wrong_drinks"),
                          Question("hours", low=0, high=hours_limit),
                          Question("last", parse=read_last, is_needed=lambda values: len(values['grams']) > 1),
                          Question("food", "choice", choices=tuple(foods), labels="food_level")],
             parent="menu", title="count", is_background=True)
def estimated(ctx: Ctx, answers: Answers) -> View:
    first, drinks = entered(answers)
    points = simulate(drinks, per_gram((answers['sex'], answers['age'], answers['height'], answers['weight'])),
                      elimination_of(ctx))
    ctx.close_screen()
    ctx.log("Alcohol estimated")
    return View(text="\n".join(report_lines(ctx, first, points, datetime.now())
                               + ["", *inputs(ctx, answers, first, drinks), "", limits_text(ctx), "",
                                  ctx.t("warning")]), photo=drawing(ctx, first, points),
                buttons=save_buttons(ctx, answers))


def source(ctx: Ctx, answers: Answers, key: str, tracker: str) -> str:
    return "" if key in answers.typed else " (" + ctx.t("from." + tracker) + ")"


def inputs(ctx: Ctx, answers: Answers, first: datetime, drinks: list) -> list[str]:
    profile = ctx.profile
    given = {'sex': ctx.t("sex." + answers['sex']), 'age': "{:g}".format(answers['age']),
             'height': profile.height(answers['height']), 'weight': profile.weight(answers['weight'])}
    body = [labelled(ctx.t("labels." + key), value) + source(ctx, answers, key, "body") for key, value in given.items()]
    drunk = source(ctx, answers, "grams", "drinks")
    last = [labelled(ctx.t("labels.last"), (first + timedelta(hours=drinks[-1][0])).strftime(moment_format)) + drunk]
    return body + [labelled(ctx.t("labels.alcohol"), "{:.1f} g".format(sum(grams for _, grams, _ in drinks))) + drunk,
                   labelled(ctx.t("labels.drinks"), len(drinks)) + drunk,
                   labelled(ctx.t("labels.first"), first.strftime(moment_format)) + drunk,
                   *(last if len(drinks) > 1 else []),
                   labelled(ctx.t("labels.food"), ctx.t("food_level." + drinks[0][2])) + drunk,
                   labelled(ctx.t("labels.elimination"), per_hour(ctx, elimination_of(ctx)))]


def savable(ctx: Ctx, answers: Answers) -> dict:
    new = answers.new(saved_keys)
    return {key: value for key, value in new.items() if key in ("sex", "age") or ctx.has_module("bodytracker")}


def save_buttons(ctx: Ctx, answers: Answers) -> list[Button]:
    new = savable(ctx, answers)
    if not new:
        return []
    return [Button(ctx.t("save_new"), "save", *[shown(new[key]) if key in new else "" for key in saved_keys])]


def shown(value) -> str:
    return value if isinstance(value, str) else "{:g}".format(value)


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


def draw(points: list[tuple[datetime, float]], now: datetime | None, texts: dict) -> bytes:
    figure = Figure(figsize=(8, 4.5), dpi=120, facecolor=colors['surface'])
    axes = figure.subplots()
    axes.set_facecolor(colors['surface'])
    top = max([level for _, level in points] + [insobriety]) * 1.15
    axes.axhspan(after_use, insobriety, color=colors['after_use'], alpha=0.18, linewidth=0)
    axes.axhspan(insobriety, top, color=colors['insobriety'], alpha=0.12, linewidth=0)
    for limit, key in ((after_use, "after_use"), (insobriety, "insobriety")):
        axes.annotate("{:g}‰ ".format(limit) + texts[key], (0.01, limit), xycoords=("axes fraction", "data"),
                      xytext=(0, 3), textcoords="offset points", color=colors['ink'], fontsize=8,
                      bbox={'facecolor': colors['surface'], 'edgecolor': "none", 'alpha': 0.8, 'pad': 1})
    moments = [moment for moment, _ in points]
    axes.plot(moments, [level for _, level in points], color=colors['line'], linewidth=2)
    if now is not None:
        axes.axvline(date2num(now), color=colors['muted'], linewidth=1, linestyle="--")
        axes.annotate(texts['now'], (now, top), xytext=(3, -12), textcoords="offset points", color=colors['muted'],
                      fontsize=8)
    axes.plot([moments[-1]], [0], marker="o", markersize=6, color=colors['line'])
    axes.annotate(texts['sober'] + " " + moments[-1].strftime("%H:%M"), (moments[-1], 0), xytext=(-4, 8),
                  textcoords="offset points", ha="right", color=colors['ink'], fontsize=8)
    axes.set_ylim(0, top)
    axes.set_title(texts['title'], color=colors['ink'], loc="left")
    axes.set_ylabel("‰", color=colors['muted'])
    axes.grid(axis="x", color=colors['grid'], linewidth=0.8)
    axes.tick_params(colors=colors['muted'])
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(colors['axis'])
    axes.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    figure.tight_layout()
    picture = io.BytesIO()
    figure.savefig(picture, format="png", facecolor=colors['surface'])
    return picture.getvalue()


# ----- the assistant -----

@module.action("estimate", parameters={'drinks': str, 'hours': float, 'last': float, 'food': str, 'sex': str,
                                       'age': float, 'height': float, 'weight': float},
               optional=["last", "sex", "age", "height", "weight"])
def act_estimate(ctx: Ctx, drinks: str, hours: float, last: float | None, food: str, sex: str | None,
                 age: float | None, height: float | None, weight: float | None) -> Outcome:
    found = known_body(ctx)
    given = {'sex': sex, 'age': age, 'height': height, 'weight': weight}
    body: dict = {key: found.get(key) if value is None else value for key, value in given.items()}
    grams = parse_drinks(drinks)
    if not grams:
        return Outcome.refused(ctx.t("wrong_drinks", limit=drinks_limit))
    if (food not in foods or body['sex'] not in (None, *sexes) or not 0 <= hours <= hours_limit
            or not 0 <= (last or 0.0) <= hours):
        return Outcome.refused(ctx.t("wrong", foods=", ".join(foods), sexes=", ".join(sexes), hours=hours_limit))
    missing = [key for key, value in body.items() if value is None and key != "sex"]
    if missing:
        return Outcome.refused(ctx.t("missing", missing=", ".join(missing)))
    if any(not low <= body[key] <= high for key, (low, high) in limits.items()):
        return Outcome.refused(ctx.t("out_of_range", low=limits['age'][0]))
    first = datetime.now().replace(microsecond=0) - timedelta(hours=hours)
    factor = per_gram((body['sex'] or "undisclosed", body['age'], body['height'], body['weight']))
    points = simulate(spread(grams, hours - (last or 0.0), food), factor, elimination_of(ctx))
    current = level_at(points, hours)
    top_moment, top = peak(points)
    return Outcome.done({'now_promille': round(current, 2), 'now_breath_mg_per_dm3': round(current / breath_ratio, 2),
                         'level': plain(ctx.t("level." + level_name(current))),
                         'peak_promille': round(top, 2),
                         'peak_at': (first + timedelta(hours=top_moment)).strftime(moment_format),
                         'sober_at': (first + timedelta(hours=points[-1][0])).strftime(moment_format),
                         'warning': plain(ctx.t("warning"))})


# ----- settings -----

@module.settings()
def settings(ctx: Ctx) -> View:
    now = labelled(ctx.t("labels.elimination"), per_hour(ctx, elimination_of(ctx)))
    return View(text=ctx.t("settings_text") + "\n\n" + now, buttons=[Button(ctx.t("rates"), "rates")])


@module.callback("rates")
def open_rates(ctx: Ctx) -> View:
    return rates(ctx)


@module.view("rates", parent="settings", title="rates")
def rates(ctx: Ctx) -> View:
    now = labelled(ctx.t("labels.elimination"), per_hour(ctx, elimination_of(ctx)))
    return View(text=ctx.t("rates_text") + "\n\n" + now,
                buttons=[Button("{:.2f}‰/h".format(rate), "elimination", "{:.2f}".format(rate))
                         for rate in eliminations], columns=3)


@module.callback("elimination")
def set_elimination(ctx: Ctx) -> View:
    wanted = ctx.arguments[0] if ctx.arguments else ""
    if wanted not in ["{:.2f}".format(rate) for rate in eliminations]:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    ctx.state.set(elimination_key, wanted)
    ctx.log("Elimination rate set to " + wanted)
    return settings(ctx)
