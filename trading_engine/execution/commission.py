"""Deterministic commission schedules shared by live previews and backtests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from ..errors import ValidationError
from ..validation import decimal_value
from ..domain.orders import OrderRequest


class CommissionModel(ABC):
    @abstractmethod
    def calculate(self, request: OrderRequest, price: Decimal, quantity: int) -> Decimal:
        pass


@dataclass(frozen=True)
class NoCommission(CommissionModel):
    def calculate(self, request: OrderRequest, price: Decimal, quantity: int) -> Decimal:
        return Decimal("0")


@dataclass(frozen=True)
class FlatCommission(CommissionModel):
    amount: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", decimal_value(self.amount, "amount", non_negative=True))

    def calculate(self, request: OrderRequest, price: Decimal, quantity: int) -> Decimal:
        return self.amount


@dataclass(frozen=True)
class PercentageCommission(CommissionModel):
    rate_percent: Decimal
    minimum: Decimal = Decimal("0")
    maximum: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rate_percent",
            decimal_value(self.rate_percent, "rate_percent", non_negative=True),
        )
        object.__setattr__(self, "minimum", decimal_value(self.minimum, "minimum", non_negative=True))
        object.__setattr__(self, "maximum", decimal_value(self.maximum, "maximum", non_negative=True))
        if self.maximum and self.minimum > self.maximum:
            raise ValidationError("minimum commission cannot exceed maximum")

    def calculate(self, request: OrderRequest, price: Decimal, quantity: int) -> Decimal:
        notional = request.instrument.notional(price, quantity)
        result = notional * self.rate_percent / Decimal("100")
        result = max(result, self.minimum)
        if self.maximum:
            result = min(result, self.maximum)
        return result


@dataclass(frozen=True)
class TieredCommission(CommissionModel):
    first_rate_percent: Decimal
    second_rate_percent: Decimal
    threshold: Decimal
    minimum: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        for field in ("first_rate_percent", "second_rate_percent", "minimum"):
            object.__setattr__(self, field, decimal_value(getattr(self, field), field, non_negative=True))
        object.__setattr__(
            self,
            "threshold",
            decimal_value(self.threshold, "threshold", positive=True, allow_zero=False),
        )

    def calculate(self, request: OrderRequest, price: Decimal, quantity: int) -> Decimal:
        notional = request.instrument.notional(price, quantity)
        first = min(notional, self.threshold)
        second = max(Decimal("0"), notional - self.threshold)
        result = first * self.first_rate_percent / Decimal("100")
        result += second * self.second_rate_percent / Decimal("100")
        return max(result, self.minimum)
