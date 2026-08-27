"""Bounded, thread-safe in-memory market-data history."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from ..errors import MarketDataError, ValidationError
from ..validation import aware_time, integer_value
from .models import Bar, Quote, TradeTick


class MarketDataStore:
    def __init__(self, max_records_per_instrument: int = 10000) -> None:
        self.max_records = integer_value(
            max_records_per_instrument,
            "max_records_per_instrument",
            minimum=1,
            maximum=1000000,
        )
        self._quotes: Dict[str, Deque[Quote]] = defaultdict(
            lambda: deque(maxlen=self.max_records)
        )
        self._ticks: Dict[str, Deque[TradeTick]] = defaultdict(
            lambda: deque(maxlen=self.max_records)
        )
        self._bars: Dict[Tuple[str, int], Deque[Bar]] = defaultdict(
            lambda: deque(maxlen=self.max_records)
        )
        self._lock = RLock()

    @staticmethod
    def _append_ordered(records: Deque, item: object, observed_at: datetime) -> None:
        if records:
            latest = getattr(records[-1], "observed_at", getattr(records[-1], "opened_at", None))
            if observed_at < latest:
                raise MarketDataError("market data must be appended chronologically")
        records.append(item)

    def append_quote(self, quote: Quote) -> None:
        if not isinstance(quote, Quote):
            raise ValidationError("quote must be a Quote")
        with self._lock:
            self._append_ordered(self._quotes[quote.instrument.key], quote, quote.observed_at)

    def append_tick(self, tick: TradeTick) -> None:
        if not isinstance(tick, TradeTick):
            raise ValidationError("tick must be a TradeTick")
        with self._lock:
            self._append_ordered(self._ticks[tick.instrument.key], tick, tick.observed_at)

    def append_bar(self, bar: Bar) -> None:
        if not isinstance(bar, Bar):
            raise ValidationError("bar must be a Bar")
        interval = int(bar.interval.total_seconds())
        key = (bar.instrument.key, interval)
        with self._lock:
            records = self._bars[key]
            if records and bar.opened_at <= records[-1].opened_at:
                raise MarketDataError("bars must have increasing open times")
            records.append(bar)

    def latest_quote(
        self,
        instrument_key: str,
        *,
        at: Optional[datetime] = None,
        max_age: Optional[timedelta] = None,
    ) -> Quote:
        with self._lock:
            records = self._quotes.get(instrument_key)
            if not records:
                raise MarketDataError(
                    "no quote available",
                    details={"instrument": instrument_key},
                )
            if at is None:
                quote = records[-1]
            else:
                current = aware_time(at, "at")
                quote = next((item for item in reversed(records) if item.observed_at <= current), None)
                if quote is None:
                    raise MarketDataError("no quote was observed by the requested time")
            if max_age is not None:
                current = (
                    aware_time(at, "at")
                    if at is not None
                    else datetime.now(timezone.utc)
                )
                if quote.is_stale(current, max_age):
                    raise MarketDataError("latest quote is stale")
            return quote

    def quote_history(
        self,
        instrument_key: str,
        *,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Tuple[Quote, ...]:
        checked_start = aware_time(start, "start") if start is not None else None
        checked_end = aware_time(end, "end") if end is not None else None
        if checked_start and checked_end and checked_end < checked_start:
            raise ValidationError("end cannot predate start")
        checked_limit = None if limit is None else integer_value(limit, "limit", minimum=1)
        with self._lock:
            items = [
                quote
                for quote in self._quotes.get(instrument_key, ())
                if (checked_start is None or quote.observed_at >= checked_start)
                and (checked_end is None or quote.observed_at <= checked_end)
            ]
        if checked_limit is not None:
            items = items[-checked_limit:]
        return tuple(items)

    def tick_history(self, instrument_key: str, limit: Optional[int] = None) -> Tuple[TradeTick, ...]:
        checked_limit = None if limit is None else integer_value(limit, "limit", minimum=1)
        with self._lock:
            items = list(self._ticks.get(instrument_key, ()))
        if checked_limit is not None:
            items = items[-checked_limit:]
        return tuple(items)

    def bar_history(
        self,
        instrument_key: str,
        interval: timedelta,
        *,
        limit: Optional[int] = None,
    ) -> Tuple[Bar, ...]:
        if not isinstance(interval, timedelta) or interval <= timedelta(0):
            raise ValidationError("interval must be positive")
        checked_limit = None if limit is None else integer_value(limit, "limit", minimum=1)
        key = (instrument_key, int(interval.total_seconds()))
        with self._lock:
            items = list(self._bars.get(key, ()))
        if checked_limit is not None:
            items = items[-checked_limit:]
        return tuple(items)

    def instruments(self) -> Tuple[str, ...]:
        with self._lock:
            keys = set(self._quotes) | set(self._ticks)
            keys.update(key[0] for key in self._bars)
        return tuple(sorted(keys))

    def clear(self, instrument_key: Optional[str] = None) -> int:
        with self._lock:
            if instrument_key is None:
                count = sum(map(len, self._quotes.values()))
                count += sum(map(len, self._ticks.values()))
                count += sum(map(len, self._bars.values()))
                self._quotes.clear()
                self._ticks.clear()
                self._bars.clear()
                return count
            count = len(self._quotes.pop(instrument_key, ()))
            count += len(self._ticks.pop(instrument_key, ()))
            for key in [item for item in self._bars if item[0] == instrument_key]:
                count += len(self._bars.pop(key))
            return count
