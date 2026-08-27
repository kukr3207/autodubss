"""Attribute portfolio profit and loss to instruments and strategies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ..errors import ValidationError
from ..validation import decimal_value
from ..domain.fills import Fill
from ..domain.orders import Order
from ..domain.portfolio import PortfolioSnapshot


@dataclass(frozen=True)
class AttributionItem:
    key: str
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    commissions: Decimal
    trade_count: int

    @property
    def net_pnl(self) -> Decimal:
        return self.realized_pnl + self.unrealized_pnl - self.commissions

    def as_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "realizedPnl": format(self.realized_pnl, "f"),
            "unrealizedPnl": format(self.unrealized_pnl, "f"),
            "commissions": format(self.commissions, "f"),
            "netPnl": format(self.net_pnl, "f"),
            "tradeCount": self.trade_count,
        }


@dataclass(frozen=True)
class AttributionReport:
    by_instrument: Mapping[str, AttributionItem]
    by_strategy: Mapping[str, AttributionItem]

    def __post_init__(self) -> None:
        object.__setattr__(self, "by_instrument", MappingProxyType(dict(self.by_instrument)))
        object.__setattr__(self, "by_strategy", MappingProxyType(dict(self.by_strategy)))

    @property
    def net_pnl(self) -> Decimal:
        return sum((item.net_pnl for item in self.by_instrument.values()), Decimal("0"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "netPnl": format(self.net_pnl, "f"),
            "byInstrument": {
                key: item.as_dict() for key, item in sorted(self.by_instrument.items())
            },
            "byStrategy": {
                key: item.as_dict() for key, item in sorted(self.by_strategy.items())
            },
        }


def _items(
    values: Mapping[str, Dict[str, Any]],
) -> Dict[str, AttributionItem]:
    return {
        key: AttributionItem(
            key,
            decimal_value(item.get("realized", 0), "realized"),
            decimal_value(item.get("unrealized", 0), "unrealized"),
            decimal_value(item.get("commissions", 0), "commissions", non_negative=True),
            int(item.get("trades", 0)),
        )
        for key, item in values.items()
    }


def attribute(
    portfolio: PortfolioSnapshot,
    fills: Iterable[Fill],
    orders: Iterable[Order],
) -> AttributionReport:
    if not isinstance(portfolio, PortfolioSnapshot):
        raise ValidationError("portfolio must be PortfolioSnapshot")
    checked_fills = tuple(fills)
    checked_orders = tuple(orders)
    order_strategies = {
        str(order.order_id): order.request.strategy_id or "manual"
        for order in checked_orders
    }
    instrument_values: Dict[str, Dict[str, Any]] = {}
    strategy_values: Dict[str, Dict[str, Any]] = {}
    for position in portfolio.positions:
        item = instrument_values.setdefault(position.instrument.key, {})
        item["realized"] = position.realized_pnl
        item["unrealized"] = position.unrealized_pnl.amount
    for fill in checked_fills:
        if not isinstance(fill, Fill):
            raise ValidationError("fills must contain Fill values")
        instrument = instrument_values.setdefault(fill.instrument.key, {})
        instrument["commissions"] = instrument.get("commissions", Decimal("0")) + fill.commission.amount
        instrument["trades"] = instrument.get("trades", 0) + 1
        strategy_key = order_strategies.get(str(fill.order_id), "unknown")
        strategy = strategy_values.setdefault(strategy_key, {})
        strategy["commissions"] = strategy.get("commissions", Decimal("0")) + fill.commission.amount
        strategy["trades"] = strategy.get("trades", 0) + 1
    total_realized = sum(
        (position.realized_pnl for position in portfolio.positions), Decimal("0")
    )
    total_unrealized = sum(
        (position.unrealized_pnl.amount for position in portfolio.positions), Decimal("0")
    )
    if strategy_values:
        trade_total = sum(item.get("trades", 0) for item in strategy_values.values())
        for item in strategy_values.values():
            weight = Decimal(item.get("trades", 0)) / trade_total
            item["realized"] = total_realized * weight
            item["unrealized"] = total_unrealized * weight
    return AttributionReport(_items(instrument_values), _items(strategy_values))
