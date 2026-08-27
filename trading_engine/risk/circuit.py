"""Operational circuit breaker for broker and market-data failures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from threading import RLock
from typing import Any, Dict, Optional

from ..clock import Clock, SystemClock
from ..errors import ValidationError
from ..validation import aware_time, integer_value


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitSnapshot:
    state: CircuitState
    failures: int
    opened_at: Optional[datetime]
    retry_at: Optional[datetime]
    last_failure: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "failures": self.failures,
            "openedAt": None if self.opened_at is None else self.opened_at.isoformat(),
            "retryAt": None if self.retry_at is None else self.retry_at.isoformat(),
            "lastFailure": self.last_failure,
        }


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: timedelta = timedelta(seconds=30),
        *,
        clock: Optional[Clock] = None,
    ) -> None:
        self.failure_threshold = integer_value(
            failure_threshold, "failure_threshold", minimum=1
        )
        if not isinstance(recovery_timeout, timedelta) or recovery_timeout <= timedelta(0):
            raise ValidationError("recovery_timeout must be positive")
        self.recovery_timeout = recovery_timeout
        self.clock = clock or SystemClock()
        if not isinstance(self.clock, Clock):
            raise ValidationError("clock must implement Clock")
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: Optional[datetime] = None
        self._last_failure: Optional[str] = None
        self._trial_in_progress = False
        self._lock = RLock()

    def _refresh(self, at: datetime) -> None:
        if (
            self._state is CircuitState.OPEN
            and self._opened_at is not None
            and at >= self._opened_at + self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._trial_in_progress = False

    def allow(self, at: Optional[datetime] = None) -> bool:
        current = aware_time(at, "at") if at is not None else self.clock.now()
        with self._lock:
            self._refresh(current)
            if self._state is CircuitState.CLOSED:
                return True
            if self._state is CircuitState.OPEN:
                return False
            if self._trial_in_progress:
                return False
            self._trial_in_progress = True
            return True

    def record_success(self) -> CircuitSnapshot:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._opened_at = None
            self._last_failure = None
            self._trial_in_progress = False
            return self.snapshot()

    def record_failure(self, message: str, at: Optional[datetime] = None) -> CircuitSnapshot:
        current = aware_time(at, "at") if at is not None else self.clock.now()
        if not isinstance(message, str) or not message.strip():
            raise ValidationError("failure message cannot be blank")
        with self._lock:
            self._failures += 1
            self._last_failure = message.strip()
            self._trial_in_progress = False
            if self._state is CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = current
            return self.snapshot()

    def force_open(self, reason: str, at: Optional[datetime] = None) -> CircuitSnapshot:
        current = aware_time(at, "at") if at is not None else self.clock.now()
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError("reason cannot be blank")
        with self._lock:
            self._state = CircuitState.OPEN
            self._opened_at = current
            self._last_failure = reason.strip()
            self._trial_in_progress = False
            return self.snapshot()

    def reset(self) -> CircuitSnapshot:
        return self.record_success()

    def snapshot(self) -> CircuitSnapshot:
        with self._lock:
            retry_at = (
                None
                if self._opened_at is None
                else self._opened_at + self.recovery_timeout
            )
            return CircuitSnapshot(
                state=self._state,
                failures=self._failures,
                opened_at=self._opened_at,
                retry_at=retry_at,
                last_failure=self._last_failure,
            )
