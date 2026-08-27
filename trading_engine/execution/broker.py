"""Broker gateway contracts and transport-neutral responses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from ..errors import ValidationError
from ..validation import aware_time, clean_text, decimal_value, enum_value, integer_value
from ..domain.identifiers import OrderId
from ..domain.orders import OrderRequest, OrderStatus


class BrokerOrderState(Enum):
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class BrokerFill:
    quantity: int
    price: Decimal
    executed_at: datetime
    venue_trade_id: Optional[str] = None
    commission: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", integer_value(self.quantity, "quantity", minimum=1))
        object.__setattr__(self, "price", decimal_value(self.price, "price", positive=True, allow_zero=False))
        object.__setattr__(self, "executed_at", aware_time(self.executed_at, "executed_at"))
        object.__setattr__(self, "commission", decimal_value(self.commission, "commission", non_negative=True))
        if self.venue_trade_id is not None:
            object.__setattr__(self, "venue_trade_id", clean_text(self.venue_trade_id, "venue_trade_id"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "quantity": self.quantity,
            "price": format(self.price, "f"),
            "executedAt": self.executed_at.isoformat(),
            "venueTradeId": self.venue_trade_id,
            "commission": format(self.commission, "f"),
        }


@dataclass(frozen=True)
class BrokerOrder:
    broker_order_id: str
    state: BrokerOrderState
    updated_at: datetime
    fills: Tuple[BrokerFill, ...] = ()
    message: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "broker_order_id", clean_text(self.broker_order_id, "broker_order_id"))
        object.__setattr__(self, "state", enum_value(self.state, BrokerOrderState, "state"))
        object.__setattr__(self, "updated_at", aware_time(self.updated_at, "updated_at"))
        fills = tuple(self.fills)
        if not all(isinstance(fill, BrokerFill) for fill in fills):
            raise ValidationError("fills must contain BrokerFill values")
        if tuple(sorted(fills, key=lambda fill: fill.executed_at)) != fills:
            raise ValidationError("broker fills must be chronological")
        object.__setattr__(self, "fills", fills)
        if self.message is not None:
            object.__setattr__(self, "message", clean_text(self.message, "message", max_length=300))

    @property
    def filled_quantity(self) -> int:
        return sum(fill.quantity for fill in self.fills)


class BrokerGateway(ABC):
    """Minimal interface implemented by live and simulated brokers."""

    name = "broker"

    @abstractmethod
    def submit(self, order_id: OrderId, request: OrderRequest) -> BrokerOrder:
        pass

    @abstractmethod
    def cancel(self, broker_order_id: str) -> BrokerOrder:
        pass

    @abstractmethod
    def get(self, broker_order_id: str) -> BrokerOrder:
        pass

    @abstractmethod
    def list_open(self) -> Tuple[BrokerOrder, ...]:
        pass
