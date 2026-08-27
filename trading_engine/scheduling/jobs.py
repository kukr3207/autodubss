"""Job definitions, run outcomes, and retry policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Dict, Mapping, Optional

from ..errors import ValidationError
from ..validation import aware_time, clean_text, enum_value, integer_value


class JobStatus(Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    initial_delay: timedelta = timedelta(seconds=5)
    multiplier: int = 2
    maximum_delay: timedelta = timedelta(minutes=5)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempts", integer_value(self.attempts, "attempts", minimum=1, maximum=20))
        object.__setattr__(self, "multiplier", integer_value(self.multiplier, "multiplier", minimum=1, maximum=10))
        if self.initial_delay < timedelta(0):
            raise ValidationError("initial_delay cannot be negative")
        if self.maximum_delay < self.initial_delay:
            raise ValidationError("maximum_delay cannot be below initial_delay")

    def delay_after(self, failed_attempt: int) -> timedelta:
        checked = integer_value(failed_attempt, "failed_attempt", minimum=1)
        seconds = self.initial_delay.total_seconds() * self.multiplier ** (checked - 1)
        return min(timedelta(seconds=seconds), self.maximum_delay)


@dataclass(frozen=True)
class Job:
    job_id: str
    name: str
    run_at: datetime
    handler: Callable[[Mapping[str, Any]], Any]
    payload: Mapping[str, Any]
    retry_policy: RetryPolicy = RetryPolicy()

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_id", clean_text(self.job_id, "job_id", max_length=100))
        object.__setattr__(self, "name", clean_text(self.name, "name", max_length=100))
        object.__setattr__(self, "run_at", aware_time(self.run_at, "run_at"))
        if not callable(self.handler):
            raise ValidationError("handler must be callable")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        if not isinstance(self.retry_policy, RetryPolicy):
            raise ValidationError("retry_policy must be RetryPolicy")


@dataclass(frozen=True)
class JobRun:
    job_id: str
    attempt: int
    status: JobStatus
    started_at: datetime
    finished_at: datetime
    result: Optional[Any] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempt", integer_value(self.attempt, "attempt", minimum=1))
        object.__setattr__(self, "status", enum_value(self.status, JobStatus, "status"))
        object.__setattr__(self, "started_at", aware_time(self.started_at, "started_at"))
        object.__setattr__(self, "finished_at", aware_time(self.finished_at, "finished_at"))
        if self.finished_at < self.started_at:
            raise ValidationError("finished_at cannot predate started_at")
        if self.status is JobStatus.FAILED and not self.error:
            raise ValidationError("failed runs require an error")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id,
            "attempt": self.attempt,
            "status": self.status.value,
            "startedAt": self.started_at.isoformat(),
            "finishedAt": self.finished_at.isoformat(),
            "result": self.result,
            "error": self.error,
        }
