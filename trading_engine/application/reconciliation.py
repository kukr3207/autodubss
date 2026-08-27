"""Compare local orders and positions with broker-side snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ..errors import ValidationError
from ..validation import decimal_value, enum_value, integer_value
from ..domain.orders import Order
from ..domain.portfolio import PortfolioSnapshot
from ..execution.broker import BrokerOrder


class DifferenceKind(Enum):
    MISSING_LOCAL = "missing_local"
    MISSING_BROKER = "missing_broker"
    STATUS_MISMATCH = "status_mismatch"
    QUANTITY_MISMATCH = "quantity_mismatch"
    POSITION_MISMATCH = "position_mismatch"


@dataclass(frozen=True)
class ReconciliationDifference:
    kind: DifferenceKind
    entity_id: str
    local_value: Optional[str]
    remote_value: Optional[str]
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", enum_value(self.kind, DifferenceKind, "kind"))
        if not self.entity_id or not self.message:
            raise ValidationError("reconciliation differences need an id and message")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "entityId": self.entity_id,
            "localValue": self.local_value,
            "remoteValue": self.remote_value,
            "message": self.message,
        }


@dataclass(frozen=True)
class ReconciliationReport:
    order_differences: Tuple[ReconciliationDifference, ...]
    position_differences: Tuple[ReconciliationDifference, ...]

    @property
    def clean(self) -> bool:
        return not self.order_differences and not self.position_differences

    def as_dict(self) -> Dict[str, Any]:
        return {
            "clean": self.clean,
            "orderDifferences": [item.as_dict() for item in self.order_differences],
            "positionDifferences": [item.as_dict() for item in self.position_differences],
        }


def reconcile_orders(
    local_orders: Iterable[Order],
    broker_orders: Iterable[BrokerOrder],
) -> Tuple[ReconciliationDifference, ...]:
    local = {
        item.broker_order_id: item
        for item in local_orders
        if item.broker_order_id is not None
    }
    remote = {item.broker_order_id: item for item in broker_orders}
    result = []
    for identifier in sorted(set(local) | set(remote)):
        left = local.get(identifier)
        right = remote.get(identifier)
        if left is None:
            result.append(
                ReconciliationDifference(
                    DifferenceKind.MISSING_LOCAL,
                    identifier,
                    None,
                    right.state.value,
                    "broker order is absent from the local repository",
                )
            )
            continue
        if right is None:
            result.append(
                ReconciliationDifference(
                    DifferenceKind.MISSING_BROKER,
                    identifier,
                    left.status.value,
                    None,
                    "local order is absent from the broker snapshot",
                )
            )
            continue
        if left.status.value != right.state.value:
            result.append(
                ReconciliationDifference(
                    DifferenceKind.STATUS_MISMATCH,
                    identifier,
                    left.status.value,
                    right.state.value,
                    "local and broker order states differ",
                )
            )
        if left.filled_quantity != right.filled_quantity:
            result.append(
                ReconciliationDifference(
                    DifferenceKind.QUANTITY_MISMATCH,
                    identifier,
                    str(left.filled_quantity),
                    str(right.filled_quantity),
                    "local and broker filled quantities differ",
                )
            )
    return tuple(result)


def reconcile_positions(
    portfolio: PortfolioSnapshot,
    broker_quantities: Mapping[str, int],
) -> Tuple[ReconciliationDifference, ...]:
    local = {position.instrument.key: position.quantity for position in portfolio.positions}
    remote = {
        key: integer_value(value, "broker quantity")
        for key, value in broker_quantities.items()
    }
    result = []
    for key in sorted(set(local) | set(remote)):
        left = local.get(key, 0)
        right = remote.get(key, 0)
        if left != right:
            result.append(
                ReconciliationDifference(
                    DifferenceKind.POSITION_MISMATCH,
                    key,
                    str(left),
                    str(right),
                    "local and broker position quantities differ",
                )
            )
    return tuple(result)


def reconcile(
    local_orders: Iterable[Order],
    broker_orders: Iterable[BrokerOrder],
    portfolio: PortfolioSnapshot,
    broker_quantities: Mapping[str, int],
) -> ReconciliationReport:
    return ReconciliationReport(
        reconcile_orders(local_orders, broker_orders),
        reconcile_positions(portfolio, broker_quantities),
    )
