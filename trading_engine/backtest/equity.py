"""Portfolio equity observations and drawdown calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..errors import ValidationError
from ..validation import aware_time, decimal_value


@dataclass(frozen=True)
class EquityPoint:
    observed_at: datetime
    equity: Decimal
    cash: Decimal
    market_value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", aware_time(self.observed_at, "observed_at"))
        for field in ("equity", "cash", "market_value"):
            object.__setattr__(self, field, decimal_value(getattr(self, field), field))
        if self.equity != self.cash + self.market_value:
            raise ValidationError("equity must equal cash plus market value")

    def as_dict(self) -> Dict[str, str]:
        return {
            "observedAt": self.observed_at.isoformat(),
            "equity": format(self.equity, "f"),
            "cash": format(self.cash, "f"),
            "marketValue": format(self.market_value, "f"),
        }


class EquityCurve:
    def __init__(self, points: Iterable[EquityPoint] = ()) -> None:
        self._points: List[EquityPoint] = []
        for point in points:
            self.append(point)

    def append(self, point: EquityPoint) -> None:
        if not isinstance(point, EquityPoint):
            raise ValidationError("point must be EquityPoint")
        if self._points and point.observed_at <= self._points[-1].observed_at:
            raise ValidationError("equity observations must have increasing times")
        self._points.append(point)

    @property
    def points(self) -> Tuple[EquityPoint, ...]:
        return tuple(self._points)

    @property
    def initial_equity(self) -> Decimal:
        return self._points[0].equity if self._points else Decimal("0")

    @property
    def final_equity(self) -> Decimal:
        return self._points[-1].equity if self._points else Decimal("0")

    @property
    def total_return(self) -> Decimal:
        if not self._points or self.initial_equity == 0:
            return Decimal("0")
        return self.final_equity / self.initial_equity - Decimal("1")

    @property
    def max_drawdown(self) -> Decimal:
        peak: Optional[Decimal] = None
        maximum = Decimal("0")
        for point in self._points:
            peak = point.equity if peak is None else max(peak, point.equity)
            if peak > 0:
                maximum = max(maximum, (peak - point.equity) / peak)
        return maximum

    @property
    def drawdown_duration(self) -> int:
        peak = Decimal("-Infinity")
        current = 0
        longest = 0
        for point in self._points:
            if point.equity >= peak:
                peak = point.equity
                current = 0
            else:
                current += 1
                longest = max(longest, current)
        return longest

    def returns(self) -> Tuple[Decimal, ...]:
        result = []
        for previous, current in zip(self._points, self._points[1:]):
            if previous.equity == 0:
                result.append(Decimal("0"))
            else:
                result.append(current.equity / previous.equity - Decimal("1"))
        return tuple(result)
