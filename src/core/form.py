import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from core.ui.keyboard import Button
from core.ui.view import View

kinds = ("number", "text", "choice", "moment", "weight", "height")
offer_key = "offer"
clear_answer = "-"
default_offer = "core:form.offer"
state_prefix = "form."
moment_choices = (0, 30, 60, 120)
time_formats = ("%H:%M", "%H.%M")
moment_formats = time_formats + ("%Y-%m-%d %H:%M", "%Y-%m-%d %H.%M", "%d.%m.%Y %H:%M", "%d.%m.%Y %H.%M")
key_pattern = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class Question:
    key: str
    kind: str = "number"
    low: float = 0.0
    high: float = 0.0
    choices: tuple[str, ...] = ()
    text: str = ""
    labels: str = ""
    back: int | None = 48
    parse: Callable | None = None
    problem: str = ""
    clear: str = ""
    is_needed: Callable | None = None

    def __post_init__(self) -> None:
        if not key_pattern.fullmatch(self.key):
            raise ValueError("Question key must be lowercase letters, digits and underscores: " + self.key)
        if any(not key_pattern.fullmatch(choice) for choice in self.choices):
            raise ValueError("Choices of '" + self.key + "' must be lowercase letters, digits and underscores")
        if self.kind not in kinds:
            raise ValueError("Unknown kind of question: " + self.kind)
        if self.key == offer_key:
            raise ValueError("A question cannot be called '" + offer_key + "'")
        if self.kind == "choice" and not self.choices:
            raise ValueError("Question '" + self.key + "' offers no choices")

    @property
    def text_key(self) -> str:
        return self.text or "ask." + self.key

    @property
    def labels_key(self) -> str:
        return self.labels or self.key

    @property
    def answers(self) -> list[str]:
        if self.kind == "moment":
            return [str(max(moment_choices))]
        return list(self.choices) + ([clear_answer] if self.clear else [])


@dataclass(frozen=True)
class Problem:
    key: str
    values: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Answers:
    values: dict
    typed: tuple[str, ...] = ()
    declined: tuple[str, ...] = ()

    def __getitem__(self, key: str):
        return self.values[key]

    def get(self, key: str, default=None):
        return self.values.get(key, default)

    def new(self, keys) -> dict:
        return {key: self.values[key] for key in keys if key in self.typed and key not in self.declined}


@dataclass(frozen=True)
class Form:
    name: str
    questions: tuple[Question, ...]
    handler: Callable
    is_background: bool = False


def number(text: str) -> float | None:
    try:
        return float(text.strip().replace(",", ".").rstrip("%").strip())
    except ValueError:
        return None


def read_moment(text: str, now: datetime | None = None, is_future: bool = False) -> datetime | None:
    now = now or datetime.now()
    for pattern in moment_formats:
        try:
            moment = datetime.strptime(" ".join(text.split()), pattern)
        except ValueError:
            continue
        if pattern in time_formats:
            moment = now.replace(hour=moment.hour, minute=moment.minute, second=0, microsecond=0)
            if is_future and moment <= now:
                moment += timedelta(days=1)
            if not is_future and moment > now:
                moment -= timedelta(days=1)
        return moment
    return None


def parse_moment(text: str, now: datetime, back: int | None) -> datetime | None:
    moment = read_moment(text, now)
    earliest = now - timedelta(hours=back) if back is not None else datetime.min
    return moment if moment is not None and earliest <= moment <= now else None


def past_moment(text: str) -> str | None:
    moment = parse_moment(text, datetime.now(), None)
    return moment.isoformat(timespec="seconds") if moment is not None else None


def wording(values: dict) -> dict:
    return {key: value for key, value in values.items() if isinstance(value, (str, int, float))}


def load(ctx, form: Form) -> dict:
    stored = ctx.state.get(state_prefix + form.name)
    return json.loads(stored) if stored else {'values': {}, 'typed': [], 'offers': [], 'declined': []}


def keep(ctx, form: Form, data: dict) -> None:
    ctx.state.set(state_prefix + form.name, json.dumps(data))


def is_asked(question: Question, values: dict) -> bool:
    return question.key not in values and (question.is_needed is None or question.is_needed(values))


def next_question(form: Form, data: dict) -> Question | None:
    return next((question for question in form.questions if is_asked(question, data['values'])), None)


def fits(question: Question, value) -> bool:
    if question.parse is not None:
        return True
    if question.kind == "choice":
        return value in question.choices
    if question.kind in ("number", "weight", "height"):
        is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
        return is_number and question.low <= value <= question.high
    return True


def usable(form: Form, known: dict, offered: dict | None) -> dict:
    questions = {question.key: question for question in form.questions}
    found = {key: value for key, value in (offered or {}).items()
             if value is not None and key not in known and (key not in questions or fits(questions[key], value))}
    return found if any(key in questions for key in found) else {}


def offers_of(form: Form, known: dict, offered: dict | list | None) -> list[dict]:
    groups = offered if isinstance(offered, list) else [(default_offer, offered)] if offered else []
    found = [{'text': text, 'values': usable(form, known, values), 'keys': list(values or {})}
             for text, values in groups]
    return [offer for offer in found if offer['values']]


def origin_of(ctx) -> str | None:
    current = ctx.nav.current()
    if current is None or current['module'] != ctx.module.name:
        return None
    if current['view'] not in ctx.module.forms:
        return current['view']
    stored = ctx.state.get(state_prefix + current['view'])
    return json.loads(stored).get('origin') if stored else None


def start(ctx, form: Form, known: dict | None, offered: dict | list | None):
    known = known or {}
    keep(ctx, form, {'values': dict(known), 'typed': [], 'offers': offers_of(form, known, offered),
                     'declined': [], 'origin': origin_of(ctx)})
    return advance(ctx, form)


def advance(ctx, form: Form):
    data = load(ctx, form)
    if data['offers'] or next_question(form, data) is not None:
        return ctx.module.view_named(form.name).handler(ctx)
    data['is_done'] = True
    keep(ctx, form, data)
    try:
        return form.handler(ctx, Answers(data['values'], tuple(data['typed']), tuple(data['declined'])))
    finally:
        if load(ctx, form).get('is_done'):
            ctx.state.delete(state_prefix + form.name)


def opened_from(storage, user_id: int, module: str, view: str) -> str | None:
    stored = storage.module_state.get(user_id, module, state_prefix + view)
    return json.loads(stored).get('origin') if stored else None


def forget(storage, user_id: int, kept: tuple[str, str] | None = None) -> None:
    storage.module_state.forget_prefixed(user_id, state_prefix,
                                         (kept[0], state_prefix + kept[1]) if kept is not None else None)


def moments(question: Question) -> list[int]:
    return [minutes for minutes in moment_choices if question.back is None or minutes <= question.back * 60]


def ago(ctx, minutes: int) -> str:
    if not minutes:
        return ctx.t("core:form.now")
    amount = str(minutes) + " min" if minutes < 60 else str(minutes // 60) + " h"
    return amount + " " + ctx.t("core:form.ago")


def screen(ctx, form: Form) -> View:
    data = load(ctx, form)
    if data['offers']:
        return View(text=ctx.t(data['offers'][0]['text']),
                    buttons=[Button(ctx.t("core:form.use"), form.name, offer_key, "1"),
                             Button(ctx.t("core:form.skip"), form.name, offer_key, "0")], columns=2)
    question = next_question(form, data) or form.questions[-1]
    text = ctx.t(question.text_key, **(wording(data['values']) | units_of(ctx, question)))
    cleared = [Button(ctx.t(question.clear), form.name, question.key, clear_answer)] if question.clear else []
    if question.kind == "choice":
        return View(text=text,
                    buttons=[Button(ctx.t(question.labels_key + "." + choice), form.name, question.key, choice)
                             for choice in question.choices] + cleared,
                    columns=2 if len(question.choices) % 2 == 0 and not cleared else 1)
    if question.kind == "moment":
        return View(text=text + "\n\n" + ctx.t("core:form.moment_hint"),
                    buttons=[Button(ago(ctx, minutes), form.name, question.key, minutes)
                             for minutes in moments(question)], columns=2)
    return View(text=text, buttons=cleared)


def units_of(ctx, question: Question) -> dict:
    profile = ctx.profile
    if question.kind == "weight":
        return {'unit': profile.weight_name, 'low': profile.weight_limit(question.low, True),
                'high': profile.weight_limit(question.high, False)}
    if question.kind == "height":
        return {'unit': profile.height_name, 'low': profile.height(question.low), 'high': profile.height(question.high)}
    return {}


def is_open(ctx, form: Form) -> bool:
    stored = ctx.state.get(state_prefix + form.name)
    return stored is not None and not json.loads(stored).get('is_done')


def take(ctx, form: Form):
    if not is_open(ctx, form):
        ctx.close_screen()
        return View(ctx.t("core:not_working_buttons"), heading=None)
    data = load(ctx, form)
    question = next_question(form, data)
    if data['offers'] or question is None or question.kind == "choice":
        return ctx.retry(ctx.t("core:form.pick"))
    if question.kind == "moment":
        moment = parse_moment(ctx.text, datetime.now(), question.back)
        if moment is None:
            if question.back is None:
                return ctx.retry(ctx.t("core:form.wrong_moment_any"))
            return ctx.retry(ctx.t("core:form.wrong_moment", hours=question.back))
        value = moment.isoformat(timespec="seconds")
    elif question.parse is not None:
        value = question.parse(ctx.text, data['values'])
        if isinstance(value, Problem):
            return ctx.retry(ctx.t(value.key, **(wording(data['values']) | value.values)))
        if value is None:
            return ctx.retry(ctx.t(question.problem or "core:form.pick", **wording(data['values'])))
    elif question.kind in ("weight", "height"):
        value = ctx.profile.read_weight(ctx.text) if question.kind == "weight" else ctx.profile.read_height(ctx.text)
        if value is None or not question.low <= value <= question.high:
            return ctx.retry(ctx.t("core:form." + question.kind + "_range", **units_of(ctx, question)))
        value = round(value, 2)
    elif question.kind == "text":
        value = ctx.text.strip()
        if not max(1, question.low) <= len(value) <= question.high:
            return ctx.retry(ctx.t("core:form.length", low="{:g}".format(max(1, question.low)),
                                   high="{:g}".format(question.high)))
    else:
        value = number(ctx.text)
        if value is None or not question.low <= value <= question.high:
            return ctx.retry(ctx.t("core:form.range", low="{:g}".format(question.low),
                                   high="{:g}".format(question.high)))
    return answer(ctx, form, data, question.key, value)


def answer(ctx, form: Form, data: dict, key: str, value):
    data['values'][key] = value
    data['typed'].append(key)
    keep(ctx, form, data)
    return advance(ctx, form)


def press(ctx, form: Form):
    key, value = (tuple(ctx.arguments) + ("", ""))[:2]
    if not is_open(ctx, form):
        return View(ctx.t("core:not_working_buttons"), heading=None)
    data = load(ctx, form)
    if key == offer_key and data['offers']:
        offer = data['offers'].pop(0)
        if value == "1":
            data['values'].update(offer['values'])
        else:
            data['declined'] += offer['keys']
        keep(ctx, form, data)
        return advance(ctx, form)
    question = next_question(form, data)
    if data['offers'] or question is None or question.key != key:
        return View(ctx.t("core:not_working_buttons"), heading=None)
    if question.kind == "choice" and value in question.choices:
        return answer(ctx, form, data, key, value)
    if question.clear and value == clear_answer:
        return answer(ctx, form, data, key, None)
    if question.kind == "moment" and value.isdigit() and int(value) in moments(question):
        moment = datetime.now().replace(microsecond=0) - timedelta(minutes=int(value))
        return answer(ctx, form, data, key, moment.isoformat(timespec="seconds"))
    return View(ctx.t("core:not_working_buttons"), heading=None)
