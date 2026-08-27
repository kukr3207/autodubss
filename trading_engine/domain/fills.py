"""Execution fills and commission accounting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from ..errors import ValidationError
from ..validation import aware_time, clean_text, decimal_value, integer_value
from .identifiers import OrderId, TradeId
from .instruments import Instrument
from .money import Money
from .orders import Side


@dataclass(frozen=True)
class Fill:
    trade_id: TradeId
    order_id: OrderId
    instrument: Instrument
    side: Side
    quantity: int
    price: Decimal
    executed_at: datetime
    commission: Money = Money.zero()
    venue_trade_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.trade_id, TradeId):
            raise ValidationError("trade_id must be a TradeId")
        if not isinstance(self.order_id, OrderId):
            raise ValidationError("order_id must be an OrderId")
        if not isinstance(self.instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        if not isinstance(self.side, Side):
            raise ValidationError("side must be a Side")
        object.__setattr__(self, "quantity", self.instrument.validate_quantity(self.quantity))
        object.__setattr__(
            self,
            "price",
            decimal_value(self.price, "price", positive=True, allow_zero=False),
        )
        object.__setattr__(self, "executed_at", aware_time(self.executed_at, "executed_at"))
        if not isinstance(self.commission, Money):
            raise ValidationError("commission must be Money")
        if self.commission.currency != self.instrument.contract.price_currency:
            raise ValidationError("commission currency must match the instrument")
        if self.commission.amount < 0:
            raise ValidationError("commission cannot be negative")
        if self.venue_trade_id is not None:
            object.__setattr__(self, "venue_trade_id", clean_text(self.venue_trade_id, "venue_trade_id"))

    @property
    def signed_quantity(self) -> int:
        return self.quantity * self.side.sign

    @property
    def gross_value(self) -> Money:
        amount = self.instrument.notional(self.price, self.quantity)
        return Money(amount, self.instrument.contract.price_currency)

    @property
    def cash_effect(self) -> Money:
        gross = self.gross_value
        if self.side is Side.BUY:
            return -gross - self.commission
        return gross - self.commission

    def as_dict(self) -> Dict[str, Any]:
        return {
            "tradeId": str(self.trade_id),
            "orderId": str(self.order_id),
            "instrument": self.instrument.as_dict(),
            "side": self.side.value,
            "quantity": self.quantity,
            "price": format(self.price, "f"),
            "executedAt": self.executed_at.isoformat(),
            "commission": self.commission.as_dict(),
            "venueTradeId": self.venue_trade_id,
        }
