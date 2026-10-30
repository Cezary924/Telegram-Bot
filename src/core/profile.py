import math
import re
from dataclasses import dataclass
from datetime import date, datetime

sexes = ("female", "male", "other", "undisclosed")
weight_units = {'kg': "kg", 'lb': "lb"}
height_units = {'cm': "cm", 'ftin': "ft in"}
age_limits = (18, 120)
pound = 0.45359237
inch = 2.54
number_pattern = re.compile(r"\d+(?:[.,]\d+)?")


def number(text: str) -> float | None:
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None


def years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def age_on(born: str, day: date) -> int:
    birth = date.fromisoformat(born)
    return day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day))


def read_born(text: str, today: date) -> str | None:
    text = text.strip()
    if text.isdigit() and len(text) <= 3:
        age = int(text)
        return years_before(today, age).isoformat() if age_limits[0] <= age <= age_limits[1] else None
    for pattern in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            born = datetime.strptime(text, pattern).date()
        except ValueError:
            continue
        return born.isoformat() if age_limits[0] <= age_on(born.isoformat(), today) <= age_limits[1] else None
    return None


def feet_and_inches(centimetres: float) -> tuple[int, int]:
    inches = round(centimetres / inch)
    return inches // 12, inches % 12


@dataclass(frozen=True)
class Profile:
    sex: str | None = None
    born: str | None = None
    weight_unit: str = "kg"
    height_unit: str = "cm"

    @property
    def age(self) -> int | None:
        return age_on(self.born, date.today()) if self.born else None

    @property
    def weight_name(self) -> str:
        return weight_units[self.weight_unit]

    @property
    def height_name(self) -> str:
        return height_units[self.height_unit]

    def in_weight_unit(self, kilograms: float) -> float:
        return kilograms / pound if self.weight_unit == "lb" else kilograms

    def weight(self, kilograms: float) -> str:
        return "{:.1f} {}".format(self.in_weight_unit(kilograms), self.weight_name)

    def height(self, centimetres: float) -> str:
        if self.height_unit == "ftin":
            feet, inches = feet_and_inches(centimetres)
            return str(feet) + " ft " + str(inches) + " in"
        return "{:.0f} cm".format(centimetres)

    def read_weight(self, text: str) -> float | None:
        value = number(text.lower().removesuffix(self.weight_name).strip())
        if value is None:
            return None
        return value * pound if self.weight_unit == "lb" else value

    def read_height(self, text: str) -> float | None:
        if self.height_unit == "cm":
            return number(text.lower().removesuffix("cm").strip())
        found = [number(part) for part in number_pattern.findall(text)]
        if not 1 <= len(found) <= 2 or (len(found) == 2 and found[1] >= 12):
            return None
        return (found[0] * 12 + (found[1] if len(found) == 2 else 0)) * inch

    def weight_limit(self, kilograms: float, is_low: bool) -> str:
        value = self.in_weight_unit(kilograms)
        return "{:.0f} {}".format(math.ceil(value - 1e-9) if is_low else math.floor(value + 1e-9), self.weight_name)
