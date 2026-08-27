"""Position accounting with realized and unrealized profit and loss."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from ..errors import ValidationError
from ..validation import aware_time, decimal_value
from .fills import Fill
from .instruments import Instrument
from .money import Money


@dataclass(frozen=True)
class Position:
    instrument: Instrument
    quantity: int = 0
    average_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    last_price: Optional[Decimal] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            raise ValidationError("quantity must be an integer")
        object.__setattr__(self, "average_price", decimal_value(self.average_price, "average_price"))
        object.__setattr__(self, "realized_pnl", decimal_value(self.realized_pnl, "realized_pnl"))
        if self.quantity == 0 and self.average_price != 0:
            raise ValidationError("flat positions must have a zero average price")
        if self.quantity != 0 and self.average_price <= 0:
            raise ValidationError("open positions require a positive average price")
        if self.last_price is not None:
            object.__setattr__(
                self,
                "last_price",
                decimal_value(self.last_price, "last_price", positive=True, allow_zero=False),
            )
        if self.updated_at is not None:
            object.__setattr__(self, "updated_at", aware_time(self.updated_at, "updated_at"))

    @property
    def market_price(self) -> Decimal:
        return self.last_price if self.last_price is not None else self.average_price

    @property
    def market_value(self) -> Money:
        amount = (
            self.market_price
            * self.quantity
            * self.instrument.contract.multiplier
        )
        return Money(amount, self.instrument.contract.price_currency)

    @property
    def unrealized_pnl(self) -> Money:
        amount = (
            (self.market_price - self.average_price)
            * self.quantity
            * self.instrument.contract.multiplier
        )
        return Money(amount, self.instrument.contract.price_currency)

    @property
    def total_pnl(self) -> Money:
        return Money(
            self.realized_pnl + self.unrealized_pnl.amount,
            self.instrument.contract.price_currency,
        )

    def mark(self, price: Any, at: datetime) -> "Position":
        marked = decimal_value(price, "price", positive=True, allow_zero=False)
        when = aware_time(at, "at")
        if self.updated_at is not None and when < self.updated_at:
            raise ValidationError("mark time cannot predate the position update")
        return replace(self, last_price=marked, updated_at=when)

    def apply(self, fill: Fill) -> "Position":
        if not isinstance(fill, Fill):
            raise ValidationError("fill must be a Fill")
        if fill.instrument.key != self.instrument.key:
            raise ValidationError("fill instrument does not match position")
        if self.updated_at is not None and fill.executed_at < self.updated_at:
            raise ValidationError("fills must be applied in chronological order")

        incoming = fill.signed_quantity
        current = self.quantity
        multiplier = self.instrument.contract.multiplier
        realized = self.realized_pnl - fill.commission.amount

        if current == 0 or (current > 0) == (incoming > 0):
            combined = current + incoming
            weighted = self.average_price * abs(current) + fill.price * abs(incoming)
            average = weighted / abs(combined)
        else:
            closing = min(abs(current), abs(incoming))
            direction = Decimal("1") if current > 0 else Decimal("-1")
            realized += (fill.price - self.average_price) * closing * direction * multiplier
            combined = current + incoming
            if combined == 0:
                average = Decimal("0")
            elif (combined > 0) == (current > 0):
                average = self.average_price
            else:
                average = fill.price

        return Position(
            instrument=self.instrument,
            quantity=combined,
            average_price=average,
            realized_pnl=realized,
            last_price=fill.price,
            updated_at=fill.executed_at,
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "instrument": self.instrument.as_dict(),
            "quantity": self.quantity,
            "averagePrice": format(self.average_price, "f"),
            "lastPrice": None if self.last_price is None else format(self.last_price, "f"),
            "marketValue": self.market_value.as_dict(),
            "realizedPnl": format(self.realized_pnl, "f"),
            "unrealizedPnl": self.unrealized_pnl.as_dict(),
            "totalPnl": self.total_pnl.as_dict(),
            "updatedAt": None if self.updated_at is None else self.updated_at.isoformat(),
        }
