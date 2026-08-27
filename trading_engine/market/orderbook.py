"""Price-level order book with deterministic update ordering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..errors import MarketDataError, ValidationError
from ..validation import aware_time, decimal_value, enum_value, integer_value
from ..domain.instruments import Instrument


class BookSide(Enum):
    BID = "bid"
    ASK = "ask"


@dataclass(frozen=True)
class PriceLevel:
    price: Decimal
    quantity: int
    order_count: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", decimal_value(self.price, "price", positive=True, allow_zero=False))
        object.__setattr__(self, "quantity", integer_value(self.quantity, "quantity", minimum=0))
        object.__setattr__(self, "order_count", integer_value(self.order_count, "order_count", minimum=0))
        if self.quantity == 0 and self.order_count != 0:
            raise ValidationError("empty levels must have zero orders")


@dataclass(frozen=True)
class BookSnapshot:
    instrument: Instrument
    sequence: int
    observed_at: datetime
    bids: Tuple[PriceLevel, ...]
    asks: Tuple[PriceLevel, ...]

    @property
    def best_bid(self) -> Optional[PriceLevel]:
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> Optional[PriceLevel]:
        return self.asks[0] if self.asks else None

    @property
    def midpoint(self) -> Optional[Decimal]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid.price + self.best_ask.price) / Decimal("2")

    @property
    def spread(self) -> Optional[Decimal]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask.price - self.best_bid.price


class OrderBook:
    def __init__(self, instrument: Instrument) -> None:
        if not isinstance(instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        self.instrument = instrument
        self._bids: Dict[Decimal, PriceLevel] = {}
        self._asks: Dict[Decimal, PriceLevel] = {}
        self._sequence = 0
        self._observed_at: Optional[datetime] = None
        self._lock = RLock()

    def _check_update(self, sequence: int, observed_at: datetime) -> Tuple[int, datetime]:
        checked_sequence = integer_value(sequence, "sequence", minimum=1)
        checked_time = aware_time(observed_at, "observed_at")
        if checked_sequence <= self._sequence:
            raise MarketDataError("book sequence must increase")
        if self._observed_at is not None and checked_time < self._observed_at:
            raise MarketDataError("book update time cannot move backwards")
        return checked_sequence, checked_time

    def replace(
        self,
        bids: Iterable[PriceLevel],
        asks: Iterable[PriceLevel],
        *,
        sequence: int,
        observed_at: datetime,
    ) -> BookSnapshot:
        checked_sequence, checked_time = self._check_update(sequence, observed_at)
        bid_map = self._validate_levels(bids)
        ask_map = self._validate_levels(asks)
        self._validate_cross(bid_map, ask_map)
        with self._lock:
            self._bids = bid_map
            self._asks = ask_map
            self._sequence = checked_sequence
            self._observed_at = checked_time
            return self.snapshot()

    def update(
        self,
        side: BookSide,
        level: PriceLevel,
        *,
        sequence: int,
        observed_at: datetime,
    ) -> BookSnapshot:
        checked_side = enum_value(side, BookSide, "side")
        if not isinstance(level, PriceLevel):
            raise ValidationError("level must be a PriceLevel")
        checked_sequence, checked_time = self._check_update(sequence, observed_at)
        with self._lock:
            bids = dict(self._bids)
            asks = dict(self._asks)
            target = bids if checked_side is BookSide.BID else asks
            if level.quantity == 0:
                target.pop(level.price, None)
            else:
                target[level.price] = level
            self._validate_cross(bids, asks)
            self._bids = bids
            self._asks = asks
            self._sequence = checked_sequence
            self._observed_at = checked_time
            return self.snapshot()

    @staticmethod
    def _validate_levels(levels: Iterable[PriceLevel]) -> Dict[Decimal, PriceLevel]:
        result: Dict[Decimal, PriceLevel] = {}
        for level in levels:
            if not isinstance(level, PriceLevel):
                raise ValidationError("all levels must be PriceLevel values")
            if level.quantity > 0:
                if level.price in result:
                    raise ValidationError("book prices cannot repeat")
                result[level.price] = level
        return result

    @staticmethod
    def _validate_cross(
        bids: Dict[Decimal, PriceLevel], asks: Dict[Decimal, PriceLevel]
    ) -> None:
        if bids and asks and max(bids) >= min(asks):
            raise MarketDataError("order book is crossed")

    def snapshot(self, depth: Optional[int] = None) -> BookSnapshot:
        checked_depth = None if depth is None else integer_value(depth, "depth", minimum=1)
        with self._lock:
            bids = [self._bids[price] for price in sorted(self._bids, reverse=True)]
            asks = [self._asks[price] for price in sorted(self._asks)]
            if checked_depth is not None:
                bids = bids[:checked_depth]
                asks = asks[:checked_depth]
            return BookSnapshot(
                instrument=self.instrument,
                sequence=self._sequence,
                observed_at=self._observed_at or datetime.min.replace(tzinfo=timezone.utc),
                bids=tuple(bids),
                asks=tuple(asks),
            )
