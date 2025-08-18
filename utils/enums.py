from enum import Enum


class StrEnum(str, Enum):
    def _generate_next_value_(self, start, count, last_values):
        return self

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value

    @classmethod
    def list_values(cls) -> list[str]:
        return [e.value for e in cls]

    @classmethod
    def list_names(cls) -> list[str]:
        return [e.name for e in cls]

    @classmethod
    def get_name_by_value(cls, value: str) -> str | None:
        for member in cls:
            if member.value == value:
                return member.name
        return None
