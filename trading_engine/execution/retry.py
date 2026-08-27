"""Bounded retry executor for transient broker operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, List, Optional, Tuple, TypeVar

from ..errors import BrokerError, ValidationError
from ..validation import integer_value


T = TypeVar("T")


@dataclass(frozen=True)
class BrokerRetryPolicy:
    attempts: int = 3
    initial_delay: timedelta = timedelta(milliseconds=100)
    multiplier: int = 2
    maximum_delay: timedelta = timedelta(seconds=2)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempts", integer_value(self.attempts, "attempts", minimum=1, maximum=10))
        object.__setattr__(self, "multiplier", integer_value(self.multiplier, "multiplier", minimum=1, maximum=10))
        if self.initial_delay < timedelta(0):
            raise ValidationError("initial_delay cannot be negative")
        if self.maximum_delay < self.initial_delay:
            raise ValidationError("maximum_delay cannot be below initial_delay")

    def delays(self) -> Tuple[timedelta, ...]:
        result = []
        current = self.initial_delay
        for _ in range(max(0, self.attempts - 1)):
            result.append(min(current, self.maximum_delay))
            current = min(
                timedelta(seconds=current.total_seconds() * self.multiplier),
                self.maximum_delay,
            )
        return tuple(result)


@dataclass(frozen=True)
class RetryAttempt:
    number: int
    error: BrokerError
    next_delay: Optional[timedelta]


class BrokerRetryExecutor:
    def __init__(
        self,
        policy: BrokerRetryPolicy = BrokerRetryPolicy(),
        *,
        wait: Optional[Callable[[timedelta], None]] = None,
        observer: Optional[Callable[[RetryAttempt], None]] = None,
    ) -> None:
        if not isinstance(policy, BrokerRetryPolicy):
            raise ValidationError("policy must be BrokerRetryPolicy")
        self.policy = policy
        self.wait = wait or (lambda delay: None)
        self.observer = observer

    def run(self, operation: Callable[[], T]) -> T:
        if not callable(operation):
            raise ValidationError("operation must be callable")
        delays = self.policy.delays()
        for attempt in range(1, self.policy.attempts + 1):
            try:
                return operation()
            except BrokerError as exc:
                delay = delays[attempt - 1] if attempt <= len(delays) else None
                if self.observer is not None:
                    self.observer(RetryAttempt(attempt, exc, delay))
                if not exc.retryable or delay is None:
                    raise
                self.wait(delay)
        raise AssertionError("retry loop exhausted without returning or raising")
