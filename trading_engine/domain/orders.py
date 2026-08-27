"""Order requests and the order lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Set

from ..errors import OrderStateError, ValidationError
from ..validation import aware_time, clean_text, decimal_value, enum_value, integer_value
from .identifiers import AccountId, ClientOrderId, OrderId
from .instruments import Instrument


class Side(Enum):
    BUY = "buy"
    SELL = "sell"

    @property
    def sign(self) -> int:
        return 1 if self is Side.BUY else -1


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


class OrderStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

    @property
    def terminal(self) -> bool:
        return self in {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        }


_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
    },
}


@dataclass(frozen=True)
class OrderRequest:
    account_id: AccountId
    client_order_id: ClientOrderId
    instrument: Instrument
    side: Side
    quantity: int
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    strategy_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, AccountId):
            raise ValidationError("account_id must be an AccountId")
        if not isinstance(self.client_order_id, ClientOrderId):
            raise ValidationError("client_order_id must be a ClientOrderId")
        if not isinstance(self.instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        object.__setattr__(self, "side", enum_value(self.side, Side, "side"))
        object.__setattr__(self, "quantity", self.instrument.validate_quantity(self.quantity))
        object.__setattr__(self, "order_type", enum_value(self.order_type, OrderType, "order_type"))
        object.__setattr__(
            self,
            "time_in_force",
            enum_value(self.time_in_force, TimeInForce, "time_in_force"),
        )
        if self.limit_price is not None:
            object.__setattr__(self, "limit_price", self.instrument.contract.round_price(self.limit_price))
        if self.stop_price is not None:
            object.__setattr__(self, "stop_price", self.instrument.contract.round_price(self.stop_price))
        if self.strategy_id is not None:
            object.__setattr__(self, "strategy_id", clean_text(self.strategy_id, "strategy_id", max_length=80))
        self._validate_prices()

    def _validate_prices(self) -> None:
        if self.order_type is OrderType.MARKET:
            if self.limit_price is not None or self.stop_price is not None:
                raise ValidationError("market orders cannot include limit or stop prices")
        elif self.order_type is OrderType.LIMIT:
            if self.limit_price is None or self.stop_price is not None:
                raise ValidationError("limit orders require only a limit price")
        elif self.order_type is OrderType.STOP:
            if self.stop_price is None or self.limit_price is not None:
                raise ValidationError("stop orders require only a stop price")
        elif self.order_type is OrderType.STOP_LIMIT:
            if self.stop_price is None or self.limit_price is None:
                raise ValidationError("stop-limit orders require stop and limit prices")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "accountId": str(self.account_id),
            "clientOrderId": str(self.client_order_id),
            "instrument": self.instrument.as_dict(),
            "side": self.side.value,
            "quantity": self.quantity,
            "orderType": self.order_type.value,
            "timeInForce": self.time_in_force.value,
            "limitPrice": None if self.limit_price is None else format(self.limit_price, "f"),
            "stopPrice": None if self.stop_price is None else format(self.stop_price, "f"),
            "strategyId": self.strategy_id,
        }


@dataclass(frozen=True)
class Order:
    order_id: OrderId
    request: OrderRequest
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    filled_quantity: int = 0
    average_fill_price: Optional[Decimal] = None
    broker_order_id: Optional[str] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.order_id, OrderId):
            raise ValidationError("order_id must be an OrderId")
        if not isinstance(self.request, OrderRequest):
            raise ValidationError("request must be an OrderRequest")
        object.__setattr__(self, "status", enum_value(self.status, OrderStatus, "status"))
        object.__setattr__(self, "created_at", aware_time(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", aware_time(self.updated_at, "updated_at"))
        if self.updated_at < self.created_at:
            raise ValidationError("updated_at cannot predate created_at")
        filled = integer_value(
            self.filled_quantity,
            "filled_quantity",
            minimum=0,
            maximum=self.request.quantity,
        )
        object.__setattr__(self, "filled_quantity", filled)
        if self.average_fill_price is not None:
            object.__setattr__(
                self,
                "average_fill_price",
                decimal_value(
                    self.average_fill_price,
                    "average_fill_price",
                    positive=True,
                    allow_zero=False,
                ),
            )
        if bool(filled) != (self.average_fill_price is not None):
            raise ValidationError("filled orders require an average fill price")
        if self.status is OrderStatus.FILLED and filled != self.request.quantity:
            raise ValidationError("filled status requires the full requested quantity")
        if self.status is OrderStatus.PARTIALLY_FILLED and not (0 < filled < self.request.quantity):
            raise ValidationError("partially filled status requires a partial quantity")
        if self.broker_order_id is not None:
            object.__setattr__(self, "broker_order_id", clean_text(self.broker_order_id, "broker_order_id"))
        if self.message is not None:
            object.__setattr__(self, "message", clean_text(self.message, "message", max_length=300))

    @property
    def remaining_quantity(self) -> int:
        return self.request.quantity - self.filled_quantity

    def transition(
        self,
        status: OrderStatus,
        at: datetime,
        *,
        broker_order_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> "Order":
        target = enum_value(status, OrderStatus, "status")
        when = aware_time(at, "at")
        if when < self.updated_at:
            raise OrderStateError("order updates cannot move backwards in time")
        allowed: Set[OrderStatus] = _TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise OrderStateError(
                "invalid order transition from %s to %s" % (self.status.value, target.value),
                details={"from": self.status.value, "to": target.value},
            )
        return replace(
            self,
            status=target,
            updated_at=when,
            broker_order_id=broker_order_id or self.broker_order_id,
            message=message,
        )

    def apply_fill(self, quantity: int, price: Any, at: datetime) -> "Order":
        when = aware_time(at, "at")
        if self.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
            raise OrderStateError("only accepted orders can be filled")
        if when < self.updated_at:
            raise OrderStateError("fill time cannot predate the latest order update")
        fill_quantity = integer_value(quantity, "quantity", minimum=1, maximum=self.remaining_quantity)
        fill_price = decimal_value(price, "price", positive=True, allow_zero=False)
        previous_value = (self.average_fill_price or Decimal("0")) * self.filled_quantity
        total_quantity = self.filled_quantity + fill_quantity
        average = (previous_value + fill_price * fill_quantity) / total_quantity
        status = OrderStatus.FILLED if total_quantity == self.request.quantity else OrderStatus.PARTIALLY_FILLED
        return replace(
            self,
            status=status,
            updated_at=when,
            filled_quantity=total_quantity,
            average_fill_price=average,
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "orderId": str(self.order_id),
            "request": self.request.as_dict(),
            "status": self.status.value,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "filledQuantity": self.filled_quantity,
            "remainingQuantity": self.remaining_quantity,
            "averageFillPrice": (
                None if self.average_fill_price is None else format(self.average_fill_price, "f")
            ),
            "brokerOrderId": self.broker_order_id,
            "message": self.message,
        }
