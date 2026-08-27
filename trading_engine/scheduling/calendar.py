"""Exchange sessions and holiday-aware trading-day calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import FrozenSet, Iterable, Optional, Tuple

from ..errors import ValidationError
from ..validation import aware_time, clean_text, integer_value


@dataclass(frozen=True)
class TradingSession:
    calendar: str
    trading_date: date
    opens_at: datetime
    closes_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "calendar", clean_text(self.calendar, "calendar", max_length=40))
        if not isinstance(self.trading_date, date):
            raise ValidationError("trading_date must be a date")
        object.__setattr__(self, "opens_at", aware_time(self.opens_at, "opens_at"))
        object.__setattr__(self, "closes_at", aware_time(self.closes_at, "closes_at"))
        if self.closes_at <= self.opens_at:
            raise ValidationError("session close must follow open")

    def contains(self, value: datetime) -> bool:
        current = aware_time(value, "value")
        return self.opens_at <= current < self.closes_at

    @property
    def duration(self) -> timedelta:
        return self.closes_at - self.opens_at


class TradingCalendar:
    def __init__(
        self,
        name: str,
        *,
        opens_at: time = time(9, 15),
        closes_at: time = time(15, 30),
        utc_offset: timedelta = timedelta(hours=5, minutes=30),
        holidays: Iterable[date] = (),
        weekend_days: Iterable[int] = (5, 6),
    ) -> None:
        self.name = clean_text(name, "name", max_length=40)
        if not isinstance(opens_at, time) or not isinstance(closes_at, time):
            raise ValidationError("session bounds must be times")
        if opens_at.tzinfo is not None or closes_at.tzinfo is not None:
            raise ValidationError("session clock times must be naive")
        if closes_at <= opens_at:
            raise ValidationError("closes_at must follow opens_at")
        if not isinstance(utc_offset, timedelta):
            raise ValidationError("utc_offset must be a timedelta")
        if not timedelta(hours=-23, minutes=-59) <= utc_offset <= timedelta(hours=23, minutes=59):
            raise ValidationError("utc_offset is outside supported bounds")
        checked_holidays = frozenset(holidays)
        if not all(isinstance(value, date) for value in checked_holidays):
            raise ValidationError("holidays must contain dates")
        checked_weekends = frozenset(weekend_days)
        if not checked_weekends or not all(isinstance(value, int) and 0 <= value <= 6 for value in checked_weekends):
            raise ValidationError("weekend days must be integers from zero through six")
        self.opens_at = opens_at
        self.closes_at = closes_at
        self.utc_offset = utc_offset
        self.holidays: FrozenSet[date] = checked_holidays
        self.weekend_days: FrozenSet[int] = checked_weekends
        self._timezone = timezone(utc_offset, self.name)

    def is_trading_day(self, value: date) -> bool:
        if not isinstance(value, date):
            raise ValidationError("value must be a date")
        return value.weekday() not in self.weekend_days and value not in self.holidays

    def session(self, value: date) -> TradingSession:
        if not self.is_trading_day(value):
            raise ValidationError("date is not a trading day")
        local_open = datetime.combine(value, self.opens_at, self._timezone)
        local_close = datetime.combine(value, self.closes_at, self._timezone)
        return TradingSession(
            self.name,
            value,
            local_open.astimezone(timezone.utc),
            local_close.astimezone(timezone.utc),
        )

    def is_open(self, value: datetime) -> bool:
        current = aware_time(value, "value")
        local_date = current.astimezone(self._timezone).date()
        if not self.is_trading_day(local_date):
            return False
        return self.session(local_date).contains(current)

    def next_trading_day(self, value: date, *, include_current: bool = False) -> date:
        cursor = value if include_current else value + timedelta(days=1)
        for _ in range(370):
            if self.is_trading_day(cursor):
                return cursor
            cursor += timedelta(days=1)
        raise ValidationError("no trading day found within one year")

    def previous_trading_day(self, value: date, *, include_current: bool = False) -> date:
        cursor = value if include_current else value - timedelta(days=1)
        for _ in range(370):
            if self.is_trading_day(cursor):
                return cursor
            cursor -= timedelta(days=1)
        raise ValidationError("no trading day found within one year")

    def sessions(self, start: date, end: date) -> Tuple[TradingSession, ...]:
        if end < start:
            raise ValidationError("end cannot predate start")
        result = []
        cursor = start
        while cursor <= end:
            if self.is_trading_day(cursor):
                result.append(self.session(cursor))
            cursor += timedelta(days=1)
        return tuple(result)

    def next_open(self, value: datetime) -> datetime:
        current = aware_time(value, "value")
        local = current.astimezone(self._timezone)
        if self.is_trading_day(local.date()):
            today = self.session(local.date())
            if current < today.opens_at:
                return today.opens_at
            if today.contains(current):
                return current
        next_date = self.next_trading_day(local.date())
        return self.session(next_date).opens_at
