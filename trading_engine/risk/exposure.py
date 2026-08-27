"""Portfolio exposure calculations kept separate from policy decisions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Dict, Mapping, Optional

from ..errors import ValidationError
from ..domain.orders import OrderRequest
from ..domain.portfolio import PortfolioSnapshot
from ..market.models import Quote


@dataclass(frozen=True)
class ExposureSnapshot:
    gross: Decimal
    net: Decimal
    long: Decimal
    short: Decimal
    by_instrument: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        object.__setattr__(self, "by_instrument", MappingProxyType(dict(self.by_instrument)))

    def as_dict(self):
        return {
            "gross": format(self.gross, "f"),
            "net": format(self.net, "f"),
            "long": format(self.long, "f"),
            "short": format(self.short, "f"),
            "byInstrument": {
                key: format(value, "f") for key, value in sorted(self.by_instrument.items())
            },
        }


def portfolio_exposure(snapshot: PortfolioSnapshot) -> ExposureSnapshot:
    if not isinstance(snapshot, PortfolioSnapshot):
        raise ValidationError("snapshot must be a PortfolioSnapshot")
    values: Dict[str, Decimal] = {}
    for position in snapshot.positions:
        values[position.instrument.key] = position.market_value.amount
    long_value = sum((value for value in values.values() if value > 0), Decimal("0"))
    short_value = sum((-value for value in values.values() if value < 0), Decimal("0"))
    return ExposureSnapshot(
        gross=long_value + short_value,
        net=long_value - short_value,
        long=long_value,
        short=short_value,
        by_instrument=values,
    )


def projected_exposure(
    snapshot: PortfolioSnapshot,
    request: OrderRequest,
    quote: Quote,
) -> ExposureSnapshot:
    if request.instrument.key != quote.instrument.key:
        raise ValidationError("quote instrument must match the order request")
    current = portfolio_exposure(snapshot)
    values = dict(current.by_instrument)
    order_value = request.instrument.notional(
        quote.executable_price(request.side), request.quantity
    )
    signed_value = order_value * request.side.sign
    values[request.instrument.key] = values.get(request.instrument.key, Decimal("0")) + signed_value
    long_value = sum((value for value in values.values() if value > 0), Decimal("0"))
    short_value = sum((-value for value in values.values() if value < 0), Decimal("0"))
    return ExposureSnapshot(
        gross=long_value + short_value,
        net=long_value - short_value,
        long=long_value,
        short=short_value,
        by_instrument=values,
    )


def projected_position_quantity(snapshot: PortfolioSnapshot, request: OrderRequest) -> int:
    current = 0
    for position in snapshot.positions:
        if position.instrument.key == request.instrument.key:
            current = position.quantity
            break
    return current + request.quantity * request.side.sign
