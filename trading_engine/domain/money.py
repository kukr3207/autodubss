"""Currency-aware monetary values based on decimal arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Dict

from ..errors import ValidationError
from ..validation import clean_code, decimal_value


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "INR"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", decimal_value(self.amount, "amount"))
        object.__setattr__(
            self,
            "currency",
            clean_code(self.currency, "currency", min_length=3, max_length=3),
        )

    @classmethod
    def zero(cls, currency: str = "INR") -> "Money":
        return cls(Decimal("0"), currency)

    def _check_currency(self, other: "Money") -> None:
        if not isinstance(other, Money) or other.currency != self.currency:
            raise ValidationError(
                "money currencies must match",
                details={
                    "leftCurrency": self.currency,
                    "rightCurrency": getattr(other, "currency", None),
                },
            )

    def __add__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, value: Any) -> "Money":
        return Money(self.amount * decimal_value(value, "multiplier"), self.currency)

    def __truediv__(self, value: Any) -> "Money":
        divisor = decimal_value(value, "divisor")
        if divisor == 0:
            raise ValidationError("divisor cannot be zero")
        return Money(self.amount / divisor, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def quantized(self, places: int = 2) -> "Money":
        if places < 0 or places > 12:
            raise ValidationError("places must be between zero and twelve")
        quantum = Decimal(1).scaleb(-places)
        return Money(self.amount.quantize(quantum, rounding=ROUND_HALF_EVEN), self.currency)

    def as_dict(self) -> Dict[str, str]:
        return {"amount": format(self.amount, "f"), "currency": self.currency}
