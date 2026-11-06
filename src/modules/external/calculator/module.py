import re
from dataclasses import replace
from datetime import datetime, timedelta

from core.api import Button, Ctx, Module, Outcome, View, bold, escape, italic, labelled, plain, read_moment

module = Module(name="calculator", place=100, is_guarded=True, formerly=["unitconverter"],
                icons={'name': "🧮", 'history': "📜", 'remove': "🗑️", 'previous': "⬅️", 'next': "➡️"},
                endings={'how': "😊", 'deleted': "✅", 'no_history': "🤷", 'gone': "💔"})

priority = 10

families = [
    {'mm': 1000, 'cm': 100, 'in': 39.37, 'dm': 10, 'ft': 3.281,
     'm': 1, 'km': 0.001, 'mi': 0.000621371},
    {'mg': 1000, 'dag': 0.1, 'g': 1, 'oz': 0.03527396, 'lb': 0.00220462,
     'kg': 0.001, 't': 0.000001},
    {'ms': 1000, 's': 1, 'min': 1 / 60, 'h': 1 / 3600, 'd': 1 / 86400,
     'wk': 1 / 604800, 'mo': 1 / 2592000, 'yr': 1 / 31536000},
]
time_family = 2

aliases = {'lbs': "lb", 'sec': "s", 'secs': "s", 'mins': "min", 'hr': "h", 'hrs': "h",
           'day': "d", 'days': "d", 'wks': "wk", 'mos': "mo", 'yrs': "yr"}

spoken = {'m': "min", 'minute': "min", 'minutes': "min", 'minuta': "min", 'minuty': "min", 'minut': "min",
          'hour': "h", 'hours': "h", 'godz': "h", 'godzina': "h", 'godziny': "h", 'godzin': "h",
          'dzień': "d", 'dni': "d", 'dnia': "d", 'second': "s", 'seconds': "s", 'sek': "s", 'sekundy': "s",
          'sekund': "s"}
time_words = {unit: unit for unit in families[time_family]} | aliases | spoken
duration_units = {written: 1 / families[time_family][unit]
                  for written, unit in time_words.items() if unit in families[time_family]}

longest = 100 * 365 * 86400
longest_number = 18
moment_format = "%Y-%m-%d %H:%M"
written_format = "%d.%m.%Y %H:%M"
weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
page_size = 8
history_size = 100
recent_size = 3
anchor = datetime(2000, 1, 1, 23, 59, 59)
settled_key = "settled"

clock = re.compile(r"(\d{1,3}):([0-5]\d)")
spelled = re.compile(r"(?:\d{1,15}(?:[.,]\d+)?\s*[^\W\d_]+\s*)+")
spelled_part = re.compile(r"(\d+(?:[.,]\d+)?)\s*([^\W\d_]+)")
iso_day = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
operator = re.compile(r"\s*([+\-−–—])\s*")
arrow = re.compile(r"(.+?)\s*(?:→|->|=>)\s*(.+)")
ranged = re.compile(r"(?:from|od)\s+(.+?)\s+(?:to|do)\s+(.+)", re.IGNORECASE)
written_time = re.compile(r".*\d:\d{2}")
present = re.compile(r"(?<!\w)(?:teraz|now)(?!\w)", re.IGNORECASE)


def table(ctx: Ctx) -> str:
    return ctx.db.table("history")


def written_units(family: dict) -> list[str]:
    known = list(family) + [written for written, unit in aliases.items() if unit in family]
    return sorted(known, key=lambda written: len(written), reverse=True)


def parse(text: str) -> tuple[dict, str, float] | None:
    compact = text.replace(" ", "").replace(",", ".")
    for family in families:
        for written in written_units(family):
            if written not in compact:
                continue
            number = compact.replace(written, "")
            if is_number(number):
                return family, aliases.get(written, written), float(number)
            break
    return None


def is_number(text: str) -> bool:
    return len(text) <= longest_number and text.replace(".", "", 1).isdecimal()


def carries_a_unit(text: str) -> bool:
    return parse(text) is not None


def number_text(value: float) -> str:
    pattern = "{:.6f}" if value == 0 or abs(value) >= 0.001 else "{:.12f}"
    return pattern.format(round(value, 12) + 0.0).rstrip("0").rstrip(".")


def amount_text(number: float, unit: str) -> str:
    return number_text(number) + " " + unit


# ----- durations and moments -----

def seconds_of(text: str) -> float | None:
    text = text.strip().lower()
    found = clock.fullmatch(text)
    if found is not None:
        return int(found[1]) * 3600 + int(found[2]) * 60
    if not spelled.fullmatch(text):
        return None
    parts = spelled_part.findall(text)
    if any(unit not in duration_units for _, unit in parts):
        return None
    return sum(float(number.replace(",", ".")) * duration_units[unit] for number, unit in parts)


def has_units(text: str) -> bool:
    return clock.fullmatch(text.strip()) is None and seconds_of(text) is not None


def duration_text(seconds: float) -> str:
    left = round(abs(seconds) * 1000)
    parts = [(left // 86400000, "d"), (left % 86400000 // 3600000, "h"), (left % 3600000 // 60000, "min"),
             (left % 60000 // 1000, "s"), (left % 1000, "ms")]
    shown = " ".join(str(amount) + " " + unit for amount, unit in parts if amount)
    return ("−" if seconds < 0 and shown else "") + (shown or "0 min")


def hours_and_minutes(seconds: float) -> tuple[float, float]:
    return round(seconds / 3600, 2), round(seconds / 60, 2)


def totals_text(seconds: float) -> str:
    hours, minutes = hours_and_minutes(seconds)
    return number_text(hours) + " h · " + number_text(minutes) + " min"


def this_minute() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


def end_of(day: datetime) -> datetime:
    return day.replace(hour=23, minute=59, second=59, microsecond=0)


def is_moment(text: str) -> bool:
    return read_moment(text) is not None


def is_written_moment(text: str) -> bool:
    return written_time.fullmatch(text) is not None and is_moment(text)


def has_date(text: str) -> bool:
    return read_moment(text, anchor) == read_moment(text, anchor + timedelta(days=1))


def moment_text(moment: datetime) -> str:
    return moment.strftime(moment_format)


def end_after(end: str, first: datetime) -> datetime | None:
    if read_moment(end, first) == first:
        return first
    last = read_moment(end, first, True)
    if last is None or last >= first:
        return last
    return read_moment(end, first.replace(year=first.year + 1, month=1, day=1), True) or last


def span(start: str | None, end: str | None, now: datetime) -> tuple[datetime, datetime] | None:
    first = now if start is None else read_moment(start, end_of(now))
    if first is None:
        return None
    last = now if end is None else end_after(end, first)
    if last is None:
        return None
    return (first if start is None or has_date(start) else read_moment(start, last) or first), last


def shifted(start: str | None, seconds: float, now: datetime) -> tuple[datetime, datetime] | None:
    first = now if start is None else read_moment(start, end_of(now))
    if first is None or abs(seconds) > longest:
        return None
    try:
        return first, first + timedelta(seconds=seconds)
    except OverflowError:
        return None


def difference_query(start: str | None, end: str | None, now: datetime) -> str:
    found = span(start, end, now)
    return "" if found is None else moment_text(found[0]) + " → " + moment_text(found[1])


def shift_query(start: str | None, seconds: float, now: datetime) -> str:
    found = shifted(start, seconds, now)
    if found is None:
        return ""
    return moment_text(found[0]) + (" + " if seconds >= 0 else " - ") + duration_text(abs(seconds))


# ----- arithmetic -----

def terms_of(text: str) -> list[tuple[int, str]]:
    pieces = operator.split(iso_day.sub(r"\1/\2/\3", " ".join(text.split())))
    marks = [1] + [1 if mark == "+" else -1 for mark in pieces[1::2]]
    return [(mark, piece.replace("/", "-")) for mark, piece in zip(marks, pieces[0::2])]


def quantity(text: str) -> tuple[int, float, str] | None:
    found = parse(text)
    if found is not None:
        family, unit, number = found
        return families.index(family), number / family[unit], unit
    seconds = seconds_of(text)
    return None if seconds is None else (time_family, seconds, "")


def parts_of(text: str) -> list[tuple[int, int, float, str]]:
    parts = []
    for mark, term in terms_of(text):
        found = quantity(term)
        if found is None:
            return []
        parts.append((mark, *found))
    return parts


def is_mixed(parts: list[tuple[int, int, float, str]]) -> bool:
    return len({family for _, family, _, _ in parts}) > 1


def part_text(family: int, value: float, unit: str) -> str:
    return amount_text(value * families[family][unit], unit) if unit else duration_text(value)


def expression_text(parts: list[tuple[int, int, float, str]]) -> str:
    return " ".join(("" if index == 0 else "+ " if mark > 0 else "- ") + part_text(family, value, unit)
                    for index, (mark, family, value, unit) in enumerate(parts))


def total_of(parts: list[tuple[int, int, float, str]]) -> float:
    return sum(mark * value for mark, _, value, _ in parts)


def in_units(parts: list[tuple[int, int, float, str]]) -> list[str]:
    family, total = families[parts[0][1]], total_of(parts)
    if parts[0][1] == time_family:
        return [duration_text(total)]
    return [amount_text(total * family[unit], unit) for unit in dict.fromkeys(unit for _, _, _, unit in parts)]


def signed_seconds(terms: list[tuple[int, str]]) -> float | None:
    total = 0.0
    for mark, term in terms:
        seconds = seconds_of(term)
        if seconds is None:
            return None
        total += mark * seconds
    return total


# ----- reading a message -----

def moment_math(first: str, rest: list[tuple[int, str]]) -> dict:
    mark, second = rest[0]
    if len(rest) == 1 and mark < 0 and is_written_moment(second):
        return {'kind': "difference", 'start': first, 'end': second}
    seconds = signed_seconds(rest)
    if seconds is None:
        return {}
    at = clock.fullmatch(first)
    if at is None or has_date(first) or any(has_units(term) for _, term in rest):
        return {'kind': "shift", 'start': first, 'seconds': seconds}
    if len(rest) == 1 and mark > 0:
        return {'kind': "either", 'start': first, 'at': int(at[1]) * 60 + int(at[2]), 'seconds': seconds}
    return {}


def ends_of(start: str, end: str, is_arrow: bool) -> dict:
    if is_written_moment(start) and is_written_moment(end):
        return {'kind': "difference", 'start': start, 'end': end}
    found = parse(start)
    target = aliases.get(end, end)
    if not is_arrow or found is None or target not in found[0]:
        return {}
    return {'kind': "conversion", 'amount': amount_text(found[2], found[1]), 'unit': target}


def calculation(text: str) -> dict:
    text = present.sub(this_minute().strftime(written_format), " ".join(text.split()))
    for pattern in (ranged, arrow):
        found = pattern.fullmatch(text)
        if found is not None:
            return ends_of(found[1], found[2], pattern is arrow)
    terms = terms_of(text)
    if len(terms) < 2 or not all(term for _, term in terms):
        return {}
    if is_written_moment(terms[0][1]):
        found = moment_math(terms[0][1], terms[1:])
        if found:
            return found
    parts = parts_of(text)
    return {'kind': "calculation", 'text': text} if parts and not is_mixed(parts) else {}


def is_calculation(text: str) -> bool:
    return bool(calculation(text))


def query_of(found: dict, now: datetime) -> str:
    if found['kind'] == "difference":
        return difference_query(found['start'], found['end'], now)
    if found['kind'] == "shift":
        return shift_query(found['start'], found['seconds'], now)
    if found['kind'] == "conversion":
        return found['amount'] + " → " + found['unit']
    return expression_text(parts_of(found['text']))


# ----- results -----

def conversion_lines(_ctx: Ctx, query: str) -> tuple[list[str], str]:
    amount, _, target = query.partition(" → ")
    found = parse(amount)
    if found is None:
        return [], ""
    family, unit, number = found
    base = number / family[unit]
    if target not in family:
        return [bold(amount_text(number, unit))] + [italic(name) + ": " + number_text(base * factor)
                                                    for name, factor in family.items()], ""
    answer = amount_text(base * family[target], target)
    return [bold(amount_text(number, unit)), italic(target) + ": " + number_text(base * family[target])], answer


def calculation_lines(ctx: Ctx, query: str) -> tuple[list[str], str]:
    parts = parts_of(query)
    if not parts or is_mixed(parts):
        return [], ""
    shown = in_units(parts)
    lines = [labelled(ctx.t("labels.calculation"), expression_text(parts)),
             labelled(ctx.t("labels.result"), " · ".join(shown))]
    if parts[0][1] == time_family:
        lines.append(labelled(ctx.t("labels.altogether"), totals_text(total_of(parts))))
    return lines, shown[0]


def difference_lines(ctx: Ctx, query: str) -> tuple[list[str], str]:
    start, _, end = query.partition(" → ")
    first, last = read_moment(start), read_moment(end)
    if first is None or last is None:
        return [], ""
    seconds = abs((last - first).total_seconds())
    return [labelled(ctx.t("labels.from"), moment_text(first)), labelled(ctx.t("labels.to"), moment_text(last)),
            labelled(ctx.t("labels.difference"), duration_text(seconds)),
            labelled(ctx.t("labels.altogether"), totals_text(seconds))], duration_text(seconds)


def weekday_text(ctx: Ctx, moment: datetime) -> str:
    return plain(ctx.t("weekdays." + weekdays[moment.weekday()])) + ", " + moment_text(moment)


def shift_lines(ctx: Ctx, query: str) -> tuple[list[str], str]:
    (_, start), *rest = terms_of(query)
    seconds = signed_seconds(rest)
    if seconds is None or not rest:
        return [], ""
    found = shifted(start, seconds, this_minute())
    if found is None:
        return [], ""
    first, last = found
    return [labelled(ctx.t("labels.from"), moment_text(first)),
            labelled(ctx.t("labels.added" if seconds >= 0 else "labels.subtracted"), duration_text(abs(seconds))),
            labelled(ctx.t("labels.result"), weekday_text(ctx, last))], moment_text(last)


results = {'conversion': conversion_lines, 'calculation': calculation_lines, 'difference': difference_lines,
           'shift': shift_lines}


def evaluate(ctx: Ctx, kind: str, query: str) -> tuple[list[str], str]:
    return results[kind](ctx, query) if kind in results and query else ([], "")


def answered(ctx: Ctx, kind: str, query: str) -> View:
    lines, answer = evaluate(ctx, kind, query)
    if not lines:
        return View(text=ctx.t("too_long" if kind == "shift" else "wrong_expression"))
    ctx.db.execute("INSERT INTO " + table(ctx) + " (user_id, kind, query, answer, made_at) VALUES (?, ?, ?, ?, ?);",
                   (ctx.user.id, kind, query, answer, datetime.now().isoformat(timespec="seconds")))
    ctx.db.execute("DELETE FROM " + table(ctx) + " WHERE user_id = ? AND id NOT IN (SELECT id FROM " + table(ctx) +
                   " WHERE user_id = ? ORDER BY made_at DESC, id DESC LIMIT ?);",
                   (ctx.user.id, ctx.user.id, history_size))
    ctx.log(kind.capitalize() + " counted")
    return View(text="\n".join(lines))


# ----- menu -----

@module.command("calculator")
def command_calculator(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(text=ctx.t("how"), buttons=[Button(ctx.t("history"), "history")])


@module.match(carries_a_unit, priority=priority)
def convert(ctx: Ctx) -> View | None:
    found = parse(ctx.text)
    if found is None:
        return None
    return answered(ctx, "conversion", amount_text(found[2], found[1]))


@module.match(is_calculation, priority=priority)
def calculate_message(ctx: Ctx) -> View | None:
    found = calculation(ctx.text)
    if not found:
        return None
    if found['kind'] == "either":
        return View(text=ctx.t("either.text"), buttons=[
            Button(ctx.t("either.time", start=found['start'], duration=duration_text(found['seconds'])), "either",
                   "time", found['at'], round(found['seconds'])),
            Button(ctx.t("either.sum"), "either", "sum", found['at'], round(found['seconds']))])
    return answered(ctx, found['kind'], query_of(found, this_minute()))


@module.callback("either")
def settle(ctx: Ctx) -> View:
    kind, at, seconds = (tuple(ctx.arguments) + ("", "", ""))[:3]
    pressed = str(ctx.message.message_id) if ctx.message is not None else ""
    if kind not in ("time", "sum") or not at.isdigit() or int(at) >= 24 * 60 or not seconds.isdigit() \
            or (pressed and ctx.state.get(settled_key) == pressed):
        return View(ctx.t("core:not_working_buttons"), heading=None)
    if ctx.message is not None:
        ctx.state.set(settled_key, pressed)
        ctx.remove_buttons(ctx.message.message_id)
    if kind == "sum":
        return answered(ctx, "calculation", duration_text(int(at) * 60) + " + " + duration_text(int(seconds)))
    start = str(int(at) // 60).zfill(2) + ":" + str(int(at) % 60).zfill(2)
    return answered(ctx, "shift", shift_query(start, int(seconds), this_minute()))


# ----- history -----

def wanted_number(ctx: Ctx) -> int:
    return int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0


def entry_of(ctx: Ctx, entry_id: int):
    return ctx.db.query_one("SELECT id, kind, query, answer, made_at FROM " + table(ctx) +
                            " WHERE id = ? AND user_id = ?;", (entry_id, ctx.user.id))


def entries_of(ctx: Ctx, limit: int = -1) -> list:
    return ctx.db.query_all("SELECT id, kind, query, answer, made_at FROM " + table(ctx) +
                            " WHERE user_id = ? ORDER BY made_at DESC, id DESC LIMIT ?;", (ctx.user.id, limit))


def row_text(row) -> str:
    return row['query'] + (" = " + row['answer'] if row['answer'] else "")


@module.callback("history")
def open_history(ctx: Ctx) -> View:
    return history(ctx)


@module.view("history", parent="menu", title="history")
def history(ctx: Ctx) -> View:
    return entries_page(ctx, wanted_number(ctx))


def entries_page(ctx: Ctx, wanted: int) -> View:
    rows = entries_of(ctx)
    if not rows:
        return View(text=ctx.t("no_history"), name="history")
    pages = -(-len(rows) // page_size)
    page = min(wanted, pages - 1)
    buttons = [Button(escape(row_text(row)), "entry", row['id'])
               for row in rows[page * page_size:(page + 1) * page_size]]
    if pages > 1:
        buttons += [Button(ctx.t("previous"), "history", max(0, page - 1)),
                    Button(ctx.t("next"), "history", min(pages - 1, page + 1))]
    return View(text=ctx.t("pick", page=italic(page + 1), pages=italic(pages), total=italic(len(rows))),
                buttons=buttons, name="history", argument=str(page))


def entry_lines(ctx: Ctx, row) -> list[str]:
    lines = evaluate(ctx, row['kind'], row['query'])[0] or [escape(row_text(row))]
    return lines + ["", labelled(ctx.t("labels.made"), row['made_at'].replace("T", " ")[:16])]


@module.callback("entry")
def open_entry(ctx: Ctx) -> View:
    return entry(ctx)


@module.view("entry", parent="history", title="entry")
def entry(ctx: Ctx) -> View:
    row = entry_of(ctx, wanted_number(ctx))
    if row is None:
        return gone(ctx)
    return View(text="\n".join(entry_lines(ctx, row)), argument=str(row['id']),
                buttons=[Button(ctx.t("remove"), "delete", row['id'])])


@module.callback("delete")
def open_delete(ctx: Ctx) -> View:
    row = entry_of(ctx, wanted_number(ctx))
    if row is None:
        return gone(ctx)
    return View(text=ctx.t("sure") + "\n" + "\n".join(entry_lines(ctx, row)), name="entry", argument=str(row['id']),
                buttons=[Button(ctx.t("core:yes_button"), "delete_confirmed", row['id'])])


@module.callback("delete_confirmed")
def confirm_delete(ctx: Ctx) -> View:
    wanted = wanted_number(ctx)
    if not ctx.db.execute("DELETE FROM " + table(ctx) + " WHERE id = ? AND user_id = ?;",
                          (wanted, ctx.user.id)).rowcount:
        return gone(ctx)
    ctx.log("Calculation " + str(wanted) + " deleted")
    found = entries_page(ctx, 0)
    return replace(found, text=ctx.t("deleted") + "\n\n" + found.text)


def gone(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone"))


# ----- the assistant -----

@module.context()
def summary(ctx: Ctx) -> str:
    rows = entries_of(ctx, recent_size)
    if not rows:
        return ""
    return ctx.t("context.recent") + ":\n" + "\n".join(escape(row_text(row)) for row in rows)


@module.action("convert", parameters={'amount': str, 'unit': str}, optional=["unit"])
def act_convert(ctx: Ctx, amount: str, unit: str | None) -> Outcome:
    found = parse(amount)
    if found is None:
        return Outcome.refused(ctx.t("wrong_amount"))
    family, written, number = found
    base = number / family[written]
    if unit is None:
        return Outcome.done({'amount': amount_text(number, written),
                             'results': [amount_text(base * factor, name) for name, factor in family.items()]})
    target = aliases.get(unit.strip(), unit.strip())
    if target not in family:
        return Outcome.refused(ctx.t("wrong_unit", units=", ".join(family)))
    return Outcome.done({'amount': amount_text(number, written), 'result': amount_text(base * family[target], target)})


@module.action("calculate", parameters={'expression': str})
def act_calculate(ctx: Ctx, expression: str) -> Outcome:
    parts = parts_of(expression)
    if not parts:
        return Outcome.refused(ctx.t("wrong_expression"))
    if is_mixed(parts):
        return Outcome.refused(ctx.t("mixed"))
    body: dict = {'calculation': expression_text(parts), 'result': " · ".join(in_units(parts))}
    if parts[0][1] == time_family:
        body['hours'], body['minutes'] = hours_and_minutes(total_of(parts))
    return Outcome.done(body)


@module.action("difference", parameters={'start': str, 'end': str}, optional=["start", "end"])
def act_difference(ctx: Ctx, start: str | None, end: str | None) -> Outcome:
    found = span(start, end, this_minute())
    if found is None:
        return Outcome.refused(ctx.t("wrong_moment"))
    first, last = found
    seconds = abs((last - first).total_seconds())
    hours, minutes = hours_and_minutes(seconds)
    return Outcome.done({'from': moment_text(first), 'to': moment_text(last), 'difference': duration_text(seconds),
                         'hours': hours, 'minutes': minutes})


@module.action("shift", parameters={'start': str, 'duration': str, 'is_subtracted': bool},
               optional=["start", "is_subtracted"])
def act_shift(ctx: Ctx, start: str | None, duration: str, is_subtracted: bool | None) -> Outcome:
    seconds = seconds_of(duration)
    if seconds is None:
        return Outcome.refused(ctx.t("wrong_duration"))
    found = shifted(start, -seconds if is_subtracted else seconds, this_minute())
    if found is None:
        return Outcome.refused(ctx.t("wrong_moment") if seconds <= longest else ctx.t("too_long"))
    first, last = found
    return Outcome.done({'from': moment_text(first), 'result': moment_text(last),
                         'weekday': plain(ctx.t("weekdays." + weekdays[last.weekday()]))})
