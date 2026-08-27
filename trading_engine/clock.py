"""Clock abstractions keep time-sensitive trading behavior testable."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from threading import RLock

from .validation import aware_time


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Return the current aware UTC time."""


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock(Clock):
    """Mutable clock intended for deterministic simulations and tests."""

    def __init__(self, current: datetime) -> None:
        self._current = aware_time(current, "current")
        self._lock = RLock()

    def now(self) -> datetime:
        with self._lock:
            return self._current

    def set(self, value: datetime) -> datetime:
        with self._lock:
            self._current = aware_time(value, "value")
            return self._current

    def advance(self, delta: timedelta) -> datetime:
        if not isinstance(delta, timedelta):
            raise TypeError("delta must be a timedelta")
        with self._lock:
            self._current = self._current + delta
            return self._current
