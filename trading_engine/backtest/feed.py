"""Chronological historical feeds with duplicate and range checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from ..errors import ValidationError
from ..validation import aware_time
from ..market.models import Bar, Quote


@dataclass(frozen=True)
class HistoricalFrame:
    bar: Bar
    quote: Quote

    def __post_init__(self) -> None:
        if not isinstance(self.bar, Bar) or not isinstance(self.quote, Quote):
            raise ValidationError("historical frames require a bar and quote")
        if self.bar.instrument.key != self.quote.instrument.key:
            raise ValidationError("historical bar and quote instruments must match")
        if self.quote.observed_at > self.bar.closed_at:
            raise ValidationError("frame quote cannot be observed after bar close")

    @property
    def time(self) -> datetime:
        return self.bar.closed_at


class HistoricalFeed:
    def __init__(self, frames: Iterable[HistoricalFrame]) -> None:
        checked = list(frames)
        if not all(isinstance(frame, HistoricalFrame) for frame in checked):
            raise ValidationError("feed must contain HistoricalFrame values")
        ordered = sorted(checked, key=lambda frame: (frame.time, frame.bar.instrument.key))
        if ordered != checked:
            raise ValidationError("historical frames must be chronological")
        seen = set()
        for frame in checked:
            identity = (frame.time, frame.bar.instrument.key)
            if identity in seen:
                raise ValidationError("feed cannot contain duplicate frames")
            seen.add(identity)
        self._frames = tuple(checked)

    def __iter__(self) -> Iterator[HistoricalFrame]:
        return iter(self._frames)

    def __len__(self) -> int:
        return len(self._frames)

    @property
    def start(self) -> Optional[datetime]:
        return self._frames[0].time if self._frames else None

    @property
    def end(self) -> Optional[datetime]:
        return self._frames[-1].time if self._frames else None

    @property
    def instruments(self) -> Tuple[str, ...]:
        return tuple(sorted({frame.bar.instrument.key for frame in self._frames}))

    def between(self, start: datetime, end: datetime) -> "HistoricalFeed":
        checked_start = aware_time(start, "start")
        checked_end = aware_time(end, "end")
        if checked_end < checked_start:
            raise ValidationError("end cannot predate start")
        return HistoricalFeed(
            frame for frame in self._frames if checked_start <= frame.time <= checked_end
        )

    def for_instrument(self, instrument_key: str) -> "HistoricalFeed":
        return HistoricalFeed(
            frame for frame in self._frames if frame.bar.instrument.key == instrument_key
        )

    @classmethod
    def from_bars(cls, bars: Sequence[Bar], spread_percent="0.05") -> "HistoricalFeed":
        from decimal import Decimal
        from ..validation import decimal_value

        spread = decimal_value(spread_percent, "spread_percent", non_negative=True)
        frames = []
        for bar in bars:
            half = bar.close * spread / Decimal("200")
            quote = Quote(
                instrument=bar.instrument,
                bid=bar.close - half,
                ask=bar.close + half,
                bid_size=max(bar.volume, 1),
                ask_size=max(bar.volume, 1),
                observed_at=bar.closed_at,
                provider="historical",
            )
            frames.append(HistoricalFrame(bar, quote))
        return cls(frames)
