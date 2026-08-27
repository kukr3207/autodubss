"""Position sizing policies convert signals into valid contract quantities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from ..errors import ValidationError
from ..validation import decimal_value, integer_value
from ..domain.portfolio import PortfolioSnapshot
from .signals import Signal, SignalAction


class PositionSizer(ABC):
    @abstractmethod
    def quantity(self, signal: Signal, portfolio: PortfolioSnapshot) -> int:
        pass


@dataclass(frozen=True)
class FixedQuantitySizer(PositionSizer):
    units: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "units", integer_value(self.units, "units", minimum=1))

    def quantity(self, signal: Signal, portfolio: PortfolioSnapshot) -> int:
        if signal.action is SignalAction.HOLD:
            return 0
        lots = max(1, self.units // signal.instrument.contract.lot_size)
        return lots * signal.instrument.contract.lot_size


@dataclass(frozen=True)
class NotionalSizer(PositionSizer):
    target_notional: Decimal
    maximum_quantity: int = 100000

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_notional",
            decimal_value(self.target_notional, "target_notional", positive=True, allow_zero=False),
        )
        object.__setattr__(
            self,
            "maximum_quantity",
            integer_value(self.maximum_quantity, "maximum_quantity", minimum=1),
        )

    def quantity(self, signal: Signal, portfolio: PortfolioSnapshot) -> int:
        if signal.action is SignalAction.HOLD:
            return 0
        if signal.reference_price is None:
            raise ValidationError("notional sizing requires a reference price")
        contract_value = signal.reference_price * signal.instrument.contract.multiplier
        raw = int((self.target_notional / contract_value).to_integral_value(rounding=ROUND_DOWN))
        lot = signal.instrument.contract.lot_size
        result = raw - raw % lot
        return min(result, self.maximum_quantity - self.maximum_quantity % lot)


@dataclass(frozen=True)
class CashFractionSizer(PositionSizer):
    fraction: Decimal
    cash_currency: str = "INR"
    maximum_quantity: int = 100000

    def __post_init__(self) -> None:
        fraction = decimal_value(self.fraction, "fraction", positive=True, allow_zero=False)
        if fraction > 1:
            raise ValidationError("fraction cannot exceed one")
        object.__setattr__(self, "fraction", fraction)
        object.__setattr__(
            self,
            "maximum_quantity",
            integer_value(self.maximum_quantity, "maximum_quantity", minimum=1),
        )

    def quantity(self, signal: Signal, portfolio: PortfolioSnapshot) -> int:
        if signal.action is SignalAction.HOLD:
            return 0
        if signal.reference_price is None:
            raise ValidationError("cash sizing requires a reference price")
        available = portfolio.cash_balance(self.cash_currency).amount
        target = max(Decimal("0"), available * self.fraction)
        if target == 0:
            return 0
        return NotionalSizer(target, self.maximum_quantity).quantity(signal, portfolio)
