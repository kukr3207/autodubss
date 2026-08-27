"""Strong identifier types prevent accidental cross-entity lookups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Type, TypeVar
from uuid import UUID, uuid4

from ..validation import clean_text


I = TypeVar("I", bound="Identifier")


@dataclass(frozen=True)
class Identifier:
    value: str

    prefix = "id"

    def __post_init__(self) -> None:
        normalized = clean_text(self.value, self.__class__.__name__, max_length=96)
        object.__setattr__(self, "value", normalized)

    @classmethod
    def new(cls: Type[I]) -> I:
        return cls("%s_%s" % (cls.prefix, uuid4().hex))

    @classmethod
    def from_uuid(cls: Type[I], value: Any) -> I:
        parsed = value if isinstance(value, UUID) else UUID(str(value))
        return cls("%s_%s" % (cls.prefix, parsed.hex))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AccountId(Identifier):
    prefix = "acct"


@dataclass(frozen=True)
class OrderId(Identifier):
    prefix = "ord"


@dataclass(frozen=True)
class ClientOrderId(Identifier):
    prefix = "client"


@dataclass(frozen=True)
class TradeId(Identifier):
    prefix = "trade"


@dataclass(frozen=True)
class EventId(Identifier):
    prefix = "evt"
