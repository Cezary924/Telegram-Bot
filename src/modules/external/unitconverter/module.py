from core.api import Ctx, Module, Role, View

module = Module(name="unitconverter")

priority = 10

families = [
    {'mm': 1000, 'cm': 100, 'in': 39.37, 'dm': 10, 'ft': 3.281,
     'm': 1, 'km': 0.001, 'mi': 0.000621371},
    {'mg': 1000, 'dag': 10, 'g': 1, 'oz': 0.03527396, 'lb': 0.00220462,
     'kg': 0.001, 't': 0.000001},
    {'ms': 1000, 's': 1, 'min': 1 / 60, 'h': 1 / 3600, 'd': 1 / 86400,
     'wk': 1 / 604800, 'mo': 1 / 2592000, 'yr': 1 / 31536000},
]


def parse(text: str) -> tuple[dict, str, float] | None:
    compact = text.replace(" ", "")
    for family in families:
        for unit in sorted(family, key=len, reverse=True):
            if unit not in compact:
                continue
            number = compact.replace(unit, "")
            if is_number(number):
                return family, unit, float(number)
            break
    return None


def is_number(text: str) -> bool:
    return text.replace(".", "", 1).isdigit()


def carries_a_unit(text: str) -> bool:
    return parse(text) is not None


@module.command("unitconverter", role=Role.USER)
def command_unitconverter(ctx: Ctx) -> View:
    return View(text=ctx.t("how"), path=["🧮 " + ctx.t("title")])


@module.match(carries_a_unit, priority=priority, role=Role.USER)
def convert(ctx: Ctx) -> View | None:
    found = parse(ctx.text)
    if found is None:
        return None
    family, unit, number = found
    base = number / family[unit]
    lines = "\n".join("_" + name + "_: " + "{:g}".format(base * factor)
                      for name, factor in family.items())
    return View(text="*" + "{:g}".format(number) + " " + unit + "*\n" + lines,
                path=["🧮 " + ctx.t("title")])
