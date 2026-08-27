"""Turn an ordered trade stream into fixed-size OHLCV bars."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from ..errors import MarketDataError, ValidationError
from .models import Bar, TradeTick


def floor_time(value: datetime, interval: timedelta) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("value must include a timezone")
    seconds = int(interval.total_seconds())
    if seconds <= 0:
        raise ValidationError("interval must be positive")
    utc = value.astimezone(timezone.utc)
    epoch_seconds = int(utc.timestamp())
    return datetime.fromtimestamp(epoch_seconds - epoch_seconds % seconds, timezone.utc)


@dataclass
class _PendingBar:
    tick: TradeTick
    opened_at: datetime
    interval: timedelta
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    trade_count: int

    @classmethod
    def start(cls, tick: TradeTick, interval: timedelta) -> "_PendingBar":
        opened = floor_time(tick.observed_at, interval)
        return cls(
            tick=tick,
            opened_at=opened,
            interval=interval,
            open=tick.price,
            high=tick.price,
            low=tick.price,
            close=tick.price,
            volume=tick.quantity,
            trade_count=1,
        )

    def add(self, tick: TradeTick) -> None:
        self.high = max(self.high, tick.price)
        self.low = min(self.low, tick.price)
        self.close = tick.price
        self.volume += tick.quantity
        self.trade_count += 1
        self.tick = tick

    def finish(self) -> Bar:
        return Bar(
            instrument=self.tick.instrument,
            interval=self.interval,
            opened_at=self.opened_at,
            closed_at=self.opened_at + self.interval,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            trade_count=self.trade_count,
            provider=self.tick.provider,
        )


class BarAggregator:
    def __init__(self, interval: timedelta, *, emit_empty: bool = False) -> None:
        if not isinstance(interval, timedelta) or interval <= timedelta(0):
            raise ValidationError("interval must be positive")
        self.interval = interval
        self.emit_empty = bool(emit_empty)
        self._pending: Optional[_PendingBar] = None
        self._latest_tick_time: Optional[datetime] = None

    def push(self, tick: TradeTick) -> Tuple[Bar, ...]:
        if not isinstance(tick, TradeTick):
            raise ValidationError("tick must be a TradeTick")
        if self._latest_tick_time is not None and tick.observed_at < self._latest_tick_time:
            raise MarketDataError("ticks must be aggregated chronologically")
        self._latest_tick_time = tick.observed_at
        if self._pending is None:
            self._pending = _PendingBar.start(tick, self.interval)
            return ()
        if tick.instrument.key != self._pending.tick.instrument.key:
            raise MarketDataError("an aggregator accepts one instrument")
        bucket = floor_time(tick.observed_at, self.interval)
        if bucket == self._pending.opened_at:
            self._pending.add(tick)
            return ()
        if bucket < self._pending.opened_at:
            raise MarketDataError("tick belongs to an earlier interval")

        completed: List[Bar] = [self._pending.finish()]
        if self.emit_empty:
            cursor = self._pending.opened_at + self.interval
            previous = self._pending
            while cursor < bucket:
                completed.append(
                    Bar(
                        instrument=previous.tick.instrument,
                        interval=self.interval,
                        opened_at=cursor,
                        closed_at=cursor + self.interval,
                        open=previous.close,
                        high=previous.close,
                        low=previous.close,
                        close=previous.close,
                        volume=0,
                        trade_count=0,
                        provider=previous.tick.provider,
                    )
                )
                cursor += self.interval
        self._pending = _PendingBar.start(tick, self.interval)
        return tuple(completed)

    def flush(self) -> Optional[Bar]:
        if self._pending is None:
            return None
        result = self._pending.finish()
        self._pending = None
        return result

    def reset(self) -> None:
        self._pending = None
        self._latest_tick_time = None
