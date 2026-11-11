import json
from dataclasses import replace
from datetime import date, datetime, timedelta

from core.api import (Answers, Button, Ctx, Module, Outcome, Question, View, age_limits, escape, italic, labelled,
                      past_moment, plain, sexes, years_before)
from core.chart import bar_values, canvas, date_ticks, palette, picture

module = Module(name="drinktracker", place=80, is_guarded=True, uses=["bodytracker", "breathalyser"],
                icons={'name': "🍺", 'add': "➕", 'sessions': "📜", 'chart': "📈", 'curve': "📈", 'custom': "✏️",
                       'drinks': "📝", 'my_body': "👤", 'edit_amount': "✏️", 'edit_when': "🕒", 'remove': "🗑️",
                       'previous': "⬅️", 'next': "➡️", 'settings_button': "⚙️", 'edit_name': "✏️", 'edit_emoji': "😀",
                       'edit_volume': "🥛", 'edit_strength': "💪", 'restore': "↩️", 'add_preset': "➕",
                       'remove_preset': "🗑️", 'restore_kinds': "↩️"},
                endings={'how': "😊", 'saved': "✅", 'body_saved': "✅", 'changed': "✅", 'deleted': "✅", 'empty': "🤷",
                         'chart_empty': "🤷", 'preset_saved': "✅", 'restored': "✅", 'preset_added': "✅",
                         'preset_removed': "✅", 'kinds_restored': "✅", 'gone': "💔"})

ethanol_density = 0.789
alcohol_kcal = 7.0
foods = ("empty", "little", "meal")
kinds = {'beer': ("🍺", 500.0, 5.0, 43.0), 'strong_beer': ("🍻", 500.0, 8.0, 65.0), 'cider': ("🍹", 400.0, 4.5, 47.0),
         'wine': ("🍷", 150.0, 13.0, 85.0), 'shot': ("🍸", 50.0, 40.0, 231.0), 'whisky': ("🥃", 40.0, 40.0, 231.0)}
custom_emoji = "🥤"
presets_key = "presets"
own_prefix = "own"
preset_fields = ("name", "emoji", "volume", "strength")
name_limit = 30
emoji_limit = 10
preset_limit = 20
drink_keys = ("kind", "volume", "strength", "when")
gap_hours = 8
fresh_hours = 24
week_days = 7
told_days = 14
volume_limits = (10, 2000)
strength_limits = (0.5, 96)
height_limits = (100, 250)
weight_limits = (30, 300)
chart_days = 30
page_size = 8
moment_format = "%Y-%m-%d %H:%M"


def drinks_table(ctx: Ctx) -> str:
    return ctx.db.table("drinks")


def sizes_table(ctx: Ctx) -> str:
    return ctx.db.table("sizes")


def grams_of(volume: float, strength: float) -> float:
    return volume * strength / 100 * ethanol_density


def kcal_of(kind: str, volume: float, grams: float) -> float:
    if kind not in kinds:
        return grams * alcohol_kcal
    return kinds[kind][3] * volume / 100 + (grams - grams_of(volume, kinds[kind][2])) * alcohol_kcal


def stored_presets(ctx: Ctx) -> dict:
    stored = ctx.state.get(presets_key)
    return json.loads(stored) if stored else {}


def store_presets(ctx: Ctx, stored: dict) -> None:
    ctx.state.set(presets_key, json.dumps(stored, ensure_ascii=False))


def presets(ctx: Ctx) -> dict[str, dict]:
    stored = stored_presets(ctx)
    found = {kind: {'name': ctx.t("kind." + kind), 'emoji': emoji, 'volume': volume, 'strength': strength}
             | stored.get(kind, {}) for kind, (emoji, volume, strength, _) in kinds.items()}
    return found | {kind: values for kind, values in stored.items() if kind not in kinds}


def usual(ctx: Ctx) -> dict[str, dict]:
    return {kind: found for kind, found in presets(ctx).items() if not found.get('hidden')}


# ----- the body -----

def tracked_size(ctx: Ctx) -> tuple | None:
    found = ctx.ask("bodytracker", "latest")
    if not found or found['weight'] is None or found['height'] is None:
        return None
    return found['height'], found['weight']


def own_size(ctx: Ctx) -> tuple | None:
    row = ctx.db.query_one("SELECT height, weight FROM " + sizes_table(ctx) + " WHERE user_id = ?;", (ctx.user.id,))
    return (row['height'], row['weight']) if row else None


def body_of(ctx: Ctx) -> tuple | None:
    profile, size = ctx.profile, tracked_size(ctx) or own_size(ctx)
    if profile.sex is None or profile.age is None or size is None:
        return None
    return profile.sex, profile.age, *size


def body_known(ctx: Ctx) -> dict:
    profile = ctx.profile
    return {key: value for key, value in (('sex', profile.sex), ('age', profile.age)) if value is not None}


body_questions = [Question("sex", "choice", choices=sexes), Question("age", low=age_limits[0], high=age_limits[1]),
                  Question("height", "height", low=height_limits[0], high=height_limits[1]),
                  Question("weight", "weight", low=weight_limits[0], high=weight_limits[1])]


@module.form("body", body_questions, parent="sessions", title="my_body")
@module.form("drink_body", body_questions, parent="kinds", title="my_body")
def body_given(ctx: Ctx, answers: Answers) -> View:
    ctx.set_profile(sex=answers['sex'])
    if 'age' in answers.typed:
        ctx.set_profile(born=years_before(date.today(), int(answers['age'])).isoformat())
    ctx.db.execute("INSERT INTO " + sizes_table(ctx) + " (user_id, height, weight) VALUES (?, ?, ?) "
                   "ON CONFLICT(user_id) DO UPDATE SET height = excluded.height, weight = excluded.weight;",
                   (ctx.user.id, answers['height'], answers['weight']))
    ctx.log("Own body data saved")
    if 'kind' in answers.values:
        return place(ctx, {key: answers[key] for key in drink_keys})
    found = sessions_page(ctx, 0)
    return replace(found, text=ctx.t("body_saved") + "\n\n" + found.text)


def ask_body(ctx: Ctx, drink: dict | None = None) -> View:
    return ctx.form("drink_body" if drink else "body", known=body_known(ctx) | (drink or {}),
                    offered=ctx.ask("bodytracker", "latest"))


# ----- sessions -----

def moment_of(row) -> datetime:
    return datetime.fromisoformat(row['drunk_at'])


def all_drinks(ctx: Ctx) -> list:
    return ctx.db.query_all("SELECT id, kind, volume, strength, grams, kcal, food, drunk_at FROM "
                            + drinks_table(ctx) + " WHERE user_id = ? ORDER BY drunk_at, id;", (ctx.user.id,))


def points_of(rows: list) -> list[tuple[str, float, str | None]]:
    return [(row['drunk_at'], row['grams'], row['food']) for row in rows]


def is_modelled(ctx: Ctx) -> bool:
    return ctx.has_module("breathalyser")


def by_gaps(rows: list) -> list[list]:
    found: list[list] = []
    for row in rows:
        if found and moment_of(row) - moment_of(found[-1][-1]) <= timedelta(hours=gap_hours):
            found[-1].append(row)
        else:
            found.append([row])
    return found


def split(ctx: Ctx, rows: list) -> list[list] | None:
    if not rows:
        return []
    if not is_modelled(ctx):
        return by_gaps(rows)
    body = body_of(ctx)
    if body is None:
        return None
    groups = ctx.ask("breathalyser", "sessions", points_of(rows), body)
    return [[rows[index] for index in group] for group in groups] if groups is not None else None


def sessions_of(ctx: Ctx) -> list[list] | None:
    return split(ctx, all_drinks(ctx))


def starts_session(ctx: Ctx, drink: dict) -> bool | None:
    moment = datetime.fromisoformat(drink['when'])
    earlier = [row for row in all_drinks(ctx) if moment_of(row) <= moment]
    added = {'id': 0, 'drunk_at': drink['when'], 'grams': grams_of(drink['volume'], drink['strength']), 'food': None}
    found = split(ctx, earlier + [added])
    return None if found is None else found[-1][0]['id'] == 0


def in_session(found: list[list], drink_id: int) -> list:
    return next((rows for rows in found if any(row['id'] == drink_id for row in rows)), [])


def session_with(ctx: Ctx, drink_id: int) -> list:
    return in_session(sessions_of(ctx) or [], drink_id)


# ----- what the other modules read -----

@module.expose("session")
def session(ctx: Ctx) -> dict | None:
    found = sessions_of(ctx)
    if not found or datetime.now() - moment_of(found[-1][-1]) > timedelta(hours=fresh_hours):
        return None
    return {'drinks': points_of(found[-1])}


@module.expose("kcal")
def kcal(ctx: Ctx, since: str) -> dict[str, float]:
    return {row['day']: row['kcal'] for row in daily(ctx, date.fromisoformat(since))}


# ----- menu -----

@module.command("drinktracker")
def command_drinktracker(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(text=ctx.t("how"),
                buttons=[Button(ctx.t("add"), "add"), Button(ctx.t("sessions"), "sessions"),
                         Button(ctx.t("chart"), "chart"), Button.settings(ctx.t("settings_button"), module.name)])


# ----- adding a drink -----

def shown(found: dict, volume: float, strength: float) -> str:
    return found['emoji'] + " " + found['name'] + ", {:g} ml, {:g}%".format(volume, strength)


def kind_name(ctx: Ctx, kind: str, volume: float, strength: float, known: dict | None = None) -> str:
    found = (known or presets(ctx)).get(kind) or {'emoji': custom_emoji, 'name': ctx.t("kind.custom")}
    return shown(found, volume, strength)


def usual_name(found: dict) -> str:
    return shown(found, found['volume'], found['strength'])


@module.callback("add")
def open_kinds(ctx: Ctx) -> View:
    return kinds_screen(ctx)


@module.view("kinds", parent="menu", title="add")
def kinds_screen(ctx: Ctx) -> View:
    return View(text=ctx.t("ask.kind"),
                buttons=[Button(escape(usual_name(found)), "kind", kind) for kind, found in usual(ctx).items()]
                + [Button(ctx.t("custom"), "kind", "custom")])


@module.callback("kind")
def pick_kind(ctx: Ctx) -> View:
    kind = ctx.arguments[0] if ctx.arguments else ""
    if kind == "custom":
        return ctx.form("drink", known={'kind': kind})
    found = usual(ctx).get(kind)
    if found is None:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    return ctx.form("drink", known={'kind': kind, 'volume': found['volume'], 'strength': found['strength']})


volume_question = Question("volume", low=volume_limits[0], high=volume_limits[1])
strength_question = Question("strength", low=strength_limits[0], high=strength_limits[1])
when_question = Question("when", "moment", back=None)


@module.form("drink", [volume_question, strength_question, when_question], parent="kinds")
def drink_given(ctx: Ctx, answers: Answers) -> View:
    return place(ctx, {key: answers[key] for key in drink_keys})


def place(ctx: Ctx, drink: dict) -> View:
    starts = starts_session(ctx, drink)
    if starts is None:
        return ask_body(ctx, drink)
    if starts:
        return ctx.form("food", known=drink)
    return save(ctx, drink, None)


@module.form("food", [Question("food", "choice", choices=foods, labels="food_level")], parent="kinds", title="food")
def food_given(ctx: Ctx, answers: Answers) -> View:
    return save(ctx, {key: answers[key] for key in drink_keys}, answers['food'])


def insert(ctx: Ctx, drink: dict, food: str | None) -> int:
    grams = grams_of(drink['volume'], drink['strength'])
    return ctx.db.execute("INSERT INTO " + drinks_table(ctx) + " (user_id, kind, volume, strength, grams, kcal, food, "
                          "drunk_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                          (ctx.user.id, drink['kind'], drink['volume'], drink['strength'], grams,
                           kcal_of(drink['kind'], drink['volume'], grams), food, drink['when'])).lastrowid


def drink_lines(ctx: Ctx, drink: dict, food: str | None) -> list[str]:
    grams = grams_of(drink['volume'], drink['strength'])
    lines = [labelled(ctx.t("labels.drink"), kind_name(ctx, drink['kind'], drink['volume'], drink['strength'])),
             labelled(ctx.t("labels.when"), datetime.fromisoformat(drink['when']).strftime(moment_format)),
             labelled(ctx.t("labels.alcohol"), "{:.1f} g".format(grams)),
             labelled(ctx.t("labels.energy"), "{:.0f} kcal".format(kcal_of(drink['kind'], drink['volume'], grams)))]
    return lines + ([labelled(ctx.t("food"), ctx.t("food_level." + food))] if food else [])


def saved_text(ctx: Ctx, drink: dict, added: int) -> str:
    return ctx.t("saved") + "\n" + "\n".join(drink_lines(ctx, drink, None)
                                             + [labelled(ctx.t("labels.in_session"), len(session_with(ctx, added)))])


def save(ctx: Ctx, drink: dict, food: str | None) -> View:
    added = insert(ctx, drink, food)
    ctx.close_screen()
    ctx.log("Drink logged")
    return View(text=saved_text(ctx, drink, added))


def gone(ctx: Ctx) -> View:
    ctx.close_screen()
    return View(text=ctx.t("gone"))


# ----- the assistant -----

@module.context()
def summary(ctx: Ctx) -> str:
    lines = []
    found = sessions_of(ctx) or []
    if found and datetime.now() - moment_of(found[-1][-1]) <= timedelta(hours=fresh_hours):
        rows = found[-1]
        values = {'started': moment_of(rows[0]).strftime(moment_format), 'drinks': len(rows),
                  'grams': "{:.0f}".format(sum(row['grams'] for row in rows))}
        body = body_of(ctx)
        estimated = ctx.ask("breathalyser", "curve", points_of(rows), body) if body else {}
        if estimated:
            lines.append(ctx.t("context.session", peak="{:.2f}‰".format(estimated['peak']),
                               peak_at=estimated['peak_at'].strftime("%H:%M"),
                               sober=estimated['sober_at'].strftime(moment_format), **values))
        else:
            lines.append(ctx.t("context.plain_session", **values))
    week = daily(ctx, date.today() - timedelta(days=week_days - 1))
    if week:
        lines.append(ctx.t("context.week", drinks=sum(row['drinks'] for row in week),
                           grams="{:.0f}".format(sum(row['grams'] for row in week))))
    if stored_presets(ctx):
        lines.append(ctx.t("context.kinds", kinds=kinds_told(usual(ctx))))
    return "\n".join(lines)


def kinds_told(found: dict[str, dict]) -> str:
    return ", ".join([kind + " (" + usual_name(values) + ")" for kind, values in found.items()] + ["custom"])


def wrong_drink(ctx: Ctx, kind: str, volume: float | None, strength: float | None) -> str:
    found = usual(ctx)
    if kind not in found and kind != "custom":
        return ctx.t("wrong_kind", kinds=kinds_told(found))
    if volume is None or strength is None:
        return ctx.t("custom_needs")
    if not volume_limits[0] <= volume <= volume_limits[1]:
        return ctx.t("core:form.range", low=volume_limits[0], high=volume_limits[1])
    if not strength_limits[0] <= strength <= strength_limits[1]:
        return ctx.t("core:form.range", low=strength_limits[0], high=strength_limits[1])
    return ""


@module.action("add_drink", parameters={'kind': str, 'volume': float, 'strength': float, 'when': str, 'food': str},
               optional=["volume", "strength", "when", "food"], is_confirmed=True)
def act_add_drink(ctx: Ctx, kind: str, volume: float | None, strength: float | None, when: str | None,
                  food: str | None) -> Outcome:
    found = usual(ctx).get(kind, {})
    volume = found.get('volume') if volume is None else volume
    strength = found.get('strength') if strength is None else strength
    moment = datetime.now().isoformat(timespec="seconds") if when is None else past_moment(when)
    problem = wrong_drink(ctx, kind, volume, strength) or ("" if moment else ctx.t("core:form.wrong_moment_any"))
    if problem:
        return Outcome.refused(problem)
    drink = {'kind': kind, 'volume': volume, 'strength': strength, 'when': moment}
    starts = starts_session(ctx, drink)
    if starts is None:
        return Outcome.refused(ctx.t("body_needed"))
    if not starts:
        food = None
    elif food not in foods:
        return Outcome.refused(ctx.t("food_needed", foods=", ".join(foods)))
    return Outcome.ask(ctx.t("add_sure") + "\n" + "\n".join(drink_lines(ctx, drink, food)),
                       lambda: drink_added(ctx, drink, food))


def drink_added(ctx: Ctx, drink: dict, food: str | None) -> str:
    added = insert(ctx, drink, food)
    ctx.log("Drink logged by the assistant")
    return saved_text(ctx, drink, added)


@module.action("days")
def act_days(ctx: Ctx) -> Outcome:
    return Outcome.done([{'day': row['day'], 'drinks': row['drinks'], 'alcohol_grams': round(row['grams']),
                          'kcal': round(row['kcal'])}
                         for row in daily(ctx, date.today() - timedelta(days=told_days - 1))])


# ----- sessions -----

def wanted_id(ctx: Ctx) -> int:
    return int(ctx.arguments[0]) if ctx.arguments and ctx.arguments[0].isdigit() else 0


def need_body(ctx: Ctx) -> View:
    return View(text=ctx.t("need_body"), buttons=[Button(ctx.t("my_body"), "my_body")])


@module.callback("my_body")
def open_my_body(ctx: Ctx) -> View:
    return ask_body(ctx)


@module.callback("sessions")
def open_sessions(ctx: Ctx) -> View:
    return sessions(ctx)


@module.view("sessions", parent="menu", title="sessions")
def sessions(ctx: Ctx) -> View:
    return sessions_page(ctx, wanted_id(ctx))


def sessions_page(ctx: Ctx, wanted: int) -> View:
    found = sessions_of(ctx)
    if found is None:
        return replace(need_body(ctx), name="sessions")
    if not found:
        return View(text=ctx.t("empty"), name="sessions")
    found.reverse()
    pages = -(-len(found) // page_size)
    page = min(wanted, pages - 1)
    buttons = [Button(moment_of(rows[0]).strftime(moment_format) + " - " + labelled(ctx.t("labels.drinks"), len(rows)),
                      "session", rows[0]['id']) for rows in found[page * page_size:(page + 1) * page_size]]
    if pages > 1:
        buttons.append(Button(ctx.t("previous"), "sessions", max(0, page - 1)))
        buttons.append(Button(ctx.t("next"), "sessions", min(pages - 1, page + 1)))
    return View(text=ctx.t("pick", page=italic(page + 1), pages=italic(pages), total=italic(len(found))),
                buttons=buttons, name="sessions", argument=str(page))


@module.callback("session")
def open_session(ctx: Ctx) -> View:
    return session_screen(ctx)


@module.view("session", parent="sessions", title="session")
def session_screen(ctx: Ctx) -> View:
    found = sessions_of(ctx)
    if found is None:
        return need_body(ctx)
    rows = in_session(found, wanted_id(ctx))
    if not rows:
        return gone(ctx)
    known = presets(ctx)
    lines = [italic(moment_of(row).strftime("%H:%M")) + " " + drink_line(ctx, row, known) for row in rows]
    totals = [labelled(ctx.t("labels.alcohol"), "{:.1f} g".format(sum(row['grams'] for row in rows))),
              labelled(ctx.t("labels.energy"), "{:.0f} kcal".format(sum(row['kcal'] for row in rows)))]
    body = body_of(ctx)
    report = ctx.ask("breathalyser", "report", points_of(rows), body) if body else []
    buttons = [Button(ctx.t("drinks"), "drinks", rows[0]['id'])]
    if report:
        buttons.insert(0, Button(ctx.t("curve"), "curve", rows[0]['id']))
    return View(text="\n".join(lines + [""] + totals + ([""] + report if report else [])), buttons=buttons,
                argument=str(rows[0]['id']))


def drink_line(ctx: Ctx, row, known: dict | None = None) -> str:
    return escape(kind_name(ctx, row['kind'], row['volume'], row['strength'], known)) \
        + " - {:.1f} g".format(row['grams'])


@module.callback("curve", is_background=True)
def open_curve(ctx: Ctx) -> View:
    return curve(ctx)


@module.view("curve", parent="session", title="curve")
def curve(ctx: Ctx) -> View:
    rows = session_with(ctx, wanted_id(ctx))
    if not rows:
        return gone(ctx)
    body = body_of(ctx)
    drawn = ctx.ask("breathalyser", "chart", points_of(rows), body) if body else {}
    if not drawn:
        return need_body(ctx)
    ctx.log("Session curve shown")
    return View(text=drawn['text'], photo=drawn['photo'], argument=str(rows[0]['id']))


# ----- the drinks of a session -----

@module.callback("drinks")
def open_drinks(ctx: Ctx) -> View:
    return drinks_screen(ctx)


@module.view("drinks", parent="session", title="drinks")
def drinks_screen(ctx: Ctx) -> View:
    rows = session_with(ctx, wanted_id(ctx))
    if not rows:
        return gone(ctx)
    known = presets(ctx)
    return View(text=ctx.t("drinks_text"),
                buttons=[Button(moment_of(row).strftime("%H:%M") + " " + drink_line(ctx, row, known), "entry",
                                row['id']) for row in rows], argument=str(rows[0]['id']))


def drink_of(ctx: Ctx, drink_id: int):
    return ctx.db.query_one("SELECT id, kind, volume, strength, grams, kcal, food, drunk_at FROM " + drinks_table(ctx)
                            + " WHERE id = ? AND user_id = ?;", (drink_id, ctx.user.id))


def as_drink(row) -> dict:
    return {'kind': row['kind'], 'volume': row['volume'], 'strength': row['strength'], 'when': row['drunk_at']}


def drink_view(ctx: Ctx, row, line: str = "") -> View:
    text = "\n".join(drink_lines(ctx, as_drink(row), row['food']))
    return View(text=line + "\n\n" + text if line else text, name="entry", argument=str(row['id']),
                buttons=[Button(ctx.t("edit_amount"), "edit", row['id']), Button(ctx.t("edit_when"), "move", row['id']),
                         Button(ctx.t("remove"), "delete", row['id'])])


@module.callback("entry")
def open_drink(ctx: Ctx) -> View:
    return drink_screen(ctx)


@module.view("entry", parent="drinks", title="drink")
def drink_screen(ctx: Ctx) -> View:
    row = drink_of(ctx, wanted_id(ctx))
    return gone(ctx) if row is None else drink_view(ctx, row)


def changed(ctx: Ctx, drink_id: int, values: dict) -> View:
    row = drink_of(ctx, drink_id)
    if row is None:
        return gone(ctx)
    drink = as_drink(row) | values
    grams = grams_of(drink['volume'], drink['strength'])
    ctx.db.execute("UPDATE " + drinks_table(ctx) + " SET volume = ?, strength = ?, grams = ?, kcal = ?, drunk_at = ? "
                   "WHERE id = ? AND user_id = ?;", (drink['volume'], drink['strength'], grams,
                                                     kcal_of(drink['kind'], drink['volume'], grams), drink['when'],
                                                     drink_id, ctx.user.id))
    ctx.log("Drink " + str(drink_id) + " changed")
    return drink_view(ctx, drink_of(ctx, drink_id), ctx.t("changed"))


@module.callback("edit")
def open_edit(ctx: Ctx) -> View:
    if drink_of(ctx, wanted_id(ctx)) is None:
        return gone(ctx)
    return ctx.form("new_amount", known={'entry': wanted_id(ctx)})


@module.form("new_amount", [volume_question, strength_question], parent="entry", title="edit_amount")
def amount_edited(ctx: Ctx, answers: Answers) -> View:
    return changed(ctx, answers['entry'], {'volume': answers['volume'], 'strength': answers['strength']})


@module.callback("move")
def open_move(ctx: Ctx) -> View:
    if drink_of(ctx, wanted_id(ctx)) is None:
        return gone(ctx)
    return ctx.form("new_time", known={'entry': wanted_id(ctx)})


@module.form("new_time", [when_question], parent="entry", title="edit_when")
def moved(ctx: Ctx, answers: Answers) -> View:
    return changed(ctx, answers['entry'], {'when': answers['when']})


@module.callback("delete")
def open_delete(ctx: Ctx) -> View:
    row = drink_of(ctx, wanted_id(ctx))
    if row is None:
        return gone(ctx)
    return View(text=ctx.t("sure") + "\n" + labelled(ctx.t("labels.drink"), drink_line(ctx, row)) + "\n"
                + labelled(ctx.t("labels.when"), moment_of(row).strftime(moment_format)), name="entry",
                buttons=[Button(ctx.t("core:yes_button"), "delete_confirmed", row['id'])], argument=str(row['id']))


@module.callback("delete_confirmed")
def confirm_delete(ctx: Ctx) -> View:
    if drink_of(ctx, wanted_id(ctx)) is None:
        return gone(ctx)
    ctx.db.execute("DELETE FROM " + drinks_table(ctx) + " WHERE id = ? AND user_id = ?;", (wanted_id(ctx), ctx.user.id))
    ctx.log("Drink " + str(wanted_id(ctx)) + " deleted")
    found = sessions_page(ctx, 0)
    return replace(found, text=ctx.t("deleted") + "\n\n" + found.text)


# ----- drinks over time -----

def daily(ctx: Ctx, since: date) -> list:
    return ctx.db.query_all("SELECT substr(drunk_at, 1, 10) AS day, COUNT(*) AS drinks, SUM(grams) AS grams, "
                            "SUM(kcal) AS kcal FROM " + drinks_table(ctx) + " WHERE user_id = ? AND drunk_at >= ? "
                            "GROUP BY day ORDER BY day;", (ctx.user.id, since.isoformat()))


def draw_days(days: list[tuple[date, float]], title: str) -> bytes:
    figure, axes = canvas(title, "g", grid="y")
    moments = [day for day, _ in days]
    bars = axes.bar(moments, [grams for _, grams in days], width=0.8, color=palette['blue'])
    bar_values(axes, bars, ["{:.0f}".format(grams) if grams else "" for _, grams in days])
    date_ticks(axes, moments, "%d.%m")
    return picture(figure)


@module.callback("chart", is_background=True)
def open_chart(ctx: Ctx) -> View:
    return chart(ctx)


@module.view("chart", parent="menu", title="chart")
def chart(ctx: Ctx) -> View:
    since = date.today() - timedelta(days=chart_days - 1)
    rows = daily(ctx, since)
    if not rows:
        return View(text=ctx.t("chart_empty"))
    drunk = ctx.db.query_one("SELECT MIN(drunk_at) AS first FROM " + drinks_table(ctx) + " WHERE user_id = ?;",
                             (ctx.user.id,))['first']
    first = max(since, date.fromisoformat(drunk[:10]) - timedelta(days=1))
    grams = {row['day']: row['grams'] for row in rows}
    days = [first + timedelta(days=offset) for offset in range((date.today() - first).days + 1)]
    photo = draw_days([(day, grams.get(day.isoformat(), 0.0)) for day in days], plain(ctx.t("chart_title")))
    lines = [escape(row['day']) + " - " + ctx.t("day", drinks=row['drinks'], grams="{:.0f}".format(row['grams']),
                                                kcal="{:.0f}".format(row['kcal'])) for row in rows]
    ctx.log("Drinks chart shown")
    return View(text="\n".join(lines), photo=photo)


# ----- settings -----

@module.settings()
def settings(ctx: Ctx) -> View:
    found = usual(ctx)
    buttons = [Button(escape(usual_name(values)), "preset", kind) for kind, values in found.items()]
    if len(found) < preset_limit:
        buttons.append(Button(ctx.t("add_preset"), "preset_add"))
    if any(kind not in found for kind in kinds):
        buttons.append(Button(ctx.t("restore_kinds"), "restore_kinds"))
    return View(text=ctx.t("settings_text"), buttons=buttons)


def settings_with(ctx: Ctx, line: str) -> View:
    found = settings(ctx)
    return replace(found, text=line + "\n\n" + found.text, name="settings")


def wanted_kind(ctx: Ctx) -> str:
    return ctx.arguments[0] if ctx.arguments and ctx.arguments[0] in usual(ctx) else ""


def preset_view(ctx: Ctx, kind: str, line: str = "") -> View:
    found = presets(ctx)[kind]
    text = "\n".join([labelled(ctx.t("labels.name"), found['name']), labelled(ctx.t("labels.emoji"), found['emoji']),
                      labelled(ctx.t("labels.volume"), "{:g} ml".format(found['volume'])),
                      labelled(ctx.t("labels.strength"), "{:g}%".format(found['strength']))])
    buttons = [Button(ctx.t("edit_" + field), "preset_edit", kind, field) for field in preset_fields]
    if kind in kinds and stored_presets(ctx).get(kind):
        buttons.append(Button(ctx.t("restore"), "preset_restore", kind))
    buttons.append(Button(ctx.t("remove_preset"), "preset_remove", kind))
    return View(text=line + "\n\n" + text if line else text, buttons=buttons, name="preset", argument=kind)


@module.callback("preset")
def open_preset(ctx: Ctx) -> View:
    return preset_screen(ctx)


@module.view("preset", parent="settings", title="preset")
def preset_screen(ctx: Ctx) -> View:
    kind = wanted_kind(ctx)
    return preset_view(ctx, kind) if kind else gone(ctx)


@module.callback("preset_edit")
def open_preset_edit(ctx: Ctx) -> View:
    kind = wanted_kind(ctx)
    field = ctx.arguments[1] if len(ctx.arguments) > 1 else ""
    if not kind or field not in preset_fields:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    return ctx.form("preset_" + field, known={'kind': kind})


def read_emoji(text: str, _values: dict) -> str | None:
    found = text.strip()
    is_emoji = 0 < len(found) <= emoji_limit and not any(one.isalnum() or one.isspace() for one in found)
    return found if is_emoji else None


name_question = Question("name", "text", high=name_limit)
emoji_question = Question("emoji", parse=read_emoji, problem="wrong_emoji")


@module.form("preset_name", [name_question], parent="preset", title="edit_name")
@module.form("preset_emoji", [emoji_question], parent="preset", title="edit_emoji")
@module.form("preset_volume", [volume_question], parent="preset", title="edit_volume")
@module.form("preset_strength", [strength_question], parent="preset", title="edit_strength")
def preset_given(ctx: Ctx, answers: Answers) -> View:
    kind, stored = answers['kind'], stored_presets(ctx)
    stored[kind] = stored.get(kind, {}) | {field: answers[field] for field in preset_fields if field in answers.values}
    store_presets(ctx, stored)
    ctx.log("Drink '" + kind + "' changed in the settings")
    return preset_view(ctx, kind, ctx.t("preset_saved"))


@module.callback("preset_restore")
def restore_preset(ctx: Ctx) -> View:
    kind, stored = wanted_kind(ctx), stored_presets(ctx)
    if kind not in kinds:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    stored.pop(kind, None)
    store_presets(ctx, stored)
    ctx.log("Drink '" + kind + "' restored in the settings")
    return preset_view(ctx, kind, ctx.t("restored"))


@module.callback("preset_add")
def open_preset_add(ctx: Ctx) -> View:
    return ctx.form("preset_new")


@module.form("preset_new", [name_question, emoji_question, volume_question, strength_question], parent="settings",
             title="add_preset")
def preset_added(ctx: Ctx, answers: Answers) -> View:
    stored = stored_presets(ctx)
    kind = own_prefix + str(1 + sum(kind not in kinds for kind in stored))
    stored[kind] = {field: answers[field] for field in preset_fields}
    store_presets(ctx, stored)
    ctx.log("Drink '" + kind + "' added in the settings")
    return preset_view(ctx, kind, ctx.t("preset_added"))


@module.callback("preset_remove")
def open_preset_remove(ctx: Ctx) -> View:
    kind = wanted_kind(ctx)
    if not kind:
        return gone(ctx)
    return View(text=ctx.t("preset_sure") + "\n" + labelled(ctx.t("labels.drink"), usual_name(presets(ctx)[kind])),
                buttons=[Button(ctx.t("core:yes_button"), "preset_removed", kind)], name="preset", argument=kind)


@module.callback("preset_removed")
def remove_preset(ctx: Ctx) -> View:
    kind, stored = wanted_kind(ctx), stored_presets(ctx)
    if not kind:
        return gone(ctx)
    stored[kind] = stored.get(kind, {}) | {'hidden': True}
    store_presets(ctx, stored)
    ctx.log("Drink '" + kind + "' removed in the settings")
    return settings_with(ctx, ctx.t("preset_removed"))


@module.callback("restore_kinds")
def restore_kinds(ctx: Ctx) -> View:
    stored = stored_presets(ctx)
    for kind in kinds:
        stored.get(kind, {}).pop('hidden', None)
    store_presets(ctx, {kind: values for kind, values in stored.items() if values})
    ctx.log("Default drinks restored in the settings")
    return settings_with(ctx, ctx.t("kinds_restored"))
