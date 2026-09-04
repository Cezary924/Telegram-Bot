from enum import IntEnum


class Role(IntEnum):
    BANNED = -1
    GUEST = 0
    USER = 1
    ADMIN = 2

    @property
    def key(self) -> str:
        return "role_" + self.name.lower()

    @classmethod
    def from_value(cls, value: int | str | None) -> "Role":
        if value is None:
            return cls.GUEST
        try:
            return cls(int(value))
        except (ValueError, TypeError):
            return cls.GUEST
