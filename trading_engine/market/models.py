"""Validated market-data records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from ..errors import ValidationError
from ..validation import aware_time, clean_text, decimal_value, integer_value
from ..domain.instruments import Instrument


@dataclass(frozen=True)
class Quote:
    instrument: Instrument
    bid: Decimal
    ask: Decimal
    bid_size: int
    ask_size: int
    observed_at: datetime
    provider: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        object.__setattr__(self, "bid", decimal_value(self.bid, "bid", positive=True, allow_zero=False))
        object.__setattr__(self, "ask", decimal_value(self.ask, "ask", positive=True, allow_zero=False))
        if self.ask < self.bid:
            raise ValidationError("ask cannot be below bid")
        object.__setattr__(self, "bid_size", integer_value(self.bid_size, "bid_size", minimum=0))
        object.__setattr__(self, "ask_size", integer_value(self.ask_size, "ask_size", minimum=0))
        object.__setattr__(self, "observed_at", aware_time(self.observed_at, "observed_at"))
        object.__setattr__(self, "provider", clean_text(self.provider, "provider", max_length=60).lower())

    @property
    def midpoint(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    def executable_price(self, side: Any) -> Decimal:
        from ..domain.orders import Side

        if side is Side.BUY:
            return self.ask
        if side is Side.SELL:
            return self.bid
        raise ValidationError("side must be buy or sell")

    def is_stale(self, at: datetime, max_age: timedelta) -> bool:
        current = aware_time(at, "at")
        if max_age <= timedelta(0):
            raise ValidationError("max_age must be positive")
        return self.observed_at > current or current - self.observed_at > max_age

    def as_dict(self) -> Dict[str, Any]:
        return {
            "instrument": self.instrument.as_dict(),
            "bid": format(self.bid, "f"),
            "ask": format(self.ask, "f"),
            "bidSize": self.bid_size,
            "askSize": self.ask_size,
            "midpoint": format(self.midpoint, "f"),
            "spread": format(self.spread, "f"),
            "observedAt": self.observed_at.isoformat(),
            "provider": self.provider,
        }


@dataclass(frozen=True)
class TradeTick:
    instrument: Instrument
    price: Decimal
    quantity: int
    observed_at: datetime
    provider: str
    trade_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        object.__setattr__(self, "price", decimal_value(self.price, "price", positive=True, allow_zero=False))
        object.__setattr__(self, "quantity", integer_value(self.quantity, "quantity", minimum=1))
        object.__setattr__(self, "observed_at", aware_time(self.observed_at, "observed_at"))
        object.__setattr__(self, "provider", clean_text(self.provider, "provider", max_length=60).lower())
        if self.trade_id is not None:
            object.__setattr__(self, "trade_id", clean_text(self.trade_id, "trade_id", max_length=100))


@dataclass(frozen=True)
class Bar:
    instrument: Instrument
    interval: timedelta
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    trade_count: int
    provider: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        if not isinstance(self.interval, timedelta) or self.interval <= timedelta(0):
            raise ValidationError("interval must be a positive timedelta")
        object.__setattr__(self, "opened_at", aware_time(self.opened_at, "opened_at"))
        object.__setattr__(self, "closed_at", aware_time(self.closed_at, "closed_at"))
        if self.closed_at <= self.opened_at:
            raise ValidationError("closed_at must follow opened_at")
        if self.closed_at - self.opened_at != self.interval:
            raise ValidationError("bar times must span exactly one interval")
        prices = {}
        for field in ("open", "high", "low", "close"):
            prices[field] = decimal_value(
                getattr(self, field), field, positive=True, allow_zero=False
            )
            object.__setattr__(self, field, prices[field])
        if prices["high"] < max(prices["open"], prices["close"]):
            raise ValidationError("high must contain open and close")
        if prices["low"] > min(prices["open"], prices["close"]):
            raise ValidationError("low must contain open and close")
        if prices["high"] < prices["low"]:
            raise ValidationError("high cannot be below low")
        object.__setattr__(self, "volume", integer_value(self.volume, "volume", minimum=0))
        object.__setattr__(self, "trade_count", integer_value(self.trade_count, "trade_count", minimum=0))
        object.__setattr__(self, "provider", clean_text(self.provider, "provider", max_length=60).lower())

    @property
    def typical_price(self) -> Decimal:
        return (self.high + self.low + self.close) / Decimal("3")

    @property
    def range(self) -> Decimal:
        return self.high - self.low

    def as_dict(self) -> Dict[str, Any]:
        return {
            "instrument": self.instrument.as_dict(),
            "intervalSeconds": int(self.interval.total_seconds()),
            "openedAt": self.opened_at.isoformat(),
            "closedAt": self.closed_at.isoformat(),
            "open": format(self.open, "f"),
            "high": format(self.high, "f"),
            "low": format(self.low, "f"),
            "close": format(self.close, "f"),
            "volume": self.volume,
            "tradeCount": self.trade_count,
            "provider": self.provider,
        }
