"""Component health registry for operations and readiness checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from threading import RLock
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

from ..clock import Clock, SystemClock
from ..errors import ValidationError
from ..validation import aware_time, clean_text, enum_value


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: HealthStatus
    checked_at: datetime
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name", max_length=80))
        object.__setattr__(self, "status", enum_value(self.status, HealthStatus, "status"))
        object.__setattr__(self, "checked_at", aware_time(self.checked_at, "checked_at"))
        object.__setattr__(self, "details", dict(self.details or {}))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "checkedAt": self.checked_at.isoformat(),
            "message": self.message,
            "details": dict(self.details or {}),
        }


@dataclass(frozen=True)
class HealthReport:
    status: HealthStatus
    checked_at: datetime
    checks: Tuple[HealthCheck, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "checkedAt": self.checked_at.isoformat(),
            "checks": [check.as_dict() for check in self.checks],
        }


class HealthRegistry:
    def __init__(self, *, clock: Optional[Clock] = None) -> None:
        self.clock = clock or SystemClock()
        self._probes: Dict[str, Callable[[], HealthCheck]] = {}
        self._lock = RLock()

    def register(self, name: str, probe: Callable[[], HealthCheck]) -> None:
        key = clean_text(name, "name", max_length=80)
        if not callable(probe):
            raise ValidationError("health probe must be callable")
        with self._lock:
            if key in self._probes:
                raise ValidationError("health probe already exists")
            self._probes[key] = probe

    def remove(self, name: str) -> bool:
        with self._lock:
            return self._probes.pop(name, None) is not None

    def check(self) -> HealthReport:
        results = []
        with self._lock:
            probes = tuple(sorted(self._probes.items()))
        for name, probe in probes:
            try:
                result = probe()
                if not isinstance(result, HealthCheck):
                    raise TypeError("probe did not return HealthCheck")
                results.append(result)
            except Exception as exc:
                results.append(
                    HealthCheck(
                        name,
                        HealthStatus.UNHEALTHY,
                        self.clock.now(),
                        "%s: %s" % (exc.__class__.__name__, exc),
                    )
                )
        statuses = {item.status for item in results}
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        return HealthReport(overall, self.clock.now(), tuple(results))
