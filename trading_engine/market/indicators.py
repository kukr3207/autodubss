"""Incremental and batch technical indicators used by strategies."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from typing import Deque, Iterable, List, Optional, Sequence, Tuple

from ..errors import ValidationError
from ..validation import decimal_value, integer_value
from .models import Bar


def simple_moving_average(values: Sequence[Decimal], period: int) -> Tuple[Optional[Decimal], ...]:
    checked = integer_value(period, "period", minimum=1)
    result: List[Optional[Decimal]] = []
    window: Deque[Decimal] = deque()
    total = Decimal("0")
    for raw in values:
        value = decimal_value(raw, "value")
        window.append(value)
        total += value
        if len(window) > checked:
            total -= window.popleft()
        result.append(total / checked if len(window) == checked else None)
    return tuple(result)


def exponential_moving_average(values: Sequence[Decimal], period: int) -> Tuple[Decimal, ...]:
    checked = integer_value(period, "period", minimum=1)
    if not values:
        return ()
    alpha = Decimal("2") / Decimal(checked + 1)
    current = decimal_value(values[0], "value")
    result = [current]
    for raw in values[1:]:
        value = decimal_value(raw, "value")
        current = value * alpha + current * (Decimal("1") - alpha)
        result.append(current)
    return tuple(result)


def true_ranges(bars: Sequence[Bar]) -> Tuple[Decimal, ...]:
    result: List[Decimal] = []
    previous_close: Optional[Decimal] = None
    for bar in bars:
        if not isinstance(bar, Bar):
            raise ValidationError("bars must contain Bar values")
        candidates = [bar.high - bar.low]
        if previous_close is not None:
            candidates.extend([abs(bar.high - previous_close), abs(bar.low - previous_close)])
        result.append(max(candidates))
        previous_close = bar.close
    return tuple(result)


def average_true_range(bars: Sequence[Bar], period: int = 14) -> Tuple[Optional[Decimal], ...]:
    return simple_moving_average(true_ranges(bars), period)


def returns(values: Sequence[Decimal]) -> Tuple[Decimal, ...]:
    if len(values) < 2:
        return ()
    checked = [decimal_value(value, "value", positive=True, allow_zero=False) for value in values]
    return tuple((current / previous) - Decimal("1") for previous, current in zip(checked, checked[1:]))


def sample_volatility(values: Sequence[Decimal]) -> Decimal:
    changes = returns(values)
    if len(changes) < 2:
        return Decimal("0")
    mean = sum(changes, Decimal("0")) / len(changes)
    variance = sum((value - mean) ** 2 for value in changes) / Decimal(len(changes) - 1)
    return Decimal(str(sqrt(float(variance))))


@dataclass
class RollingWindow:
    period: int

    def __post_init__(self) -> None:
        self.period = integer_value(self.period, "period", minimum=1)
        self._values: Deque[Decimal] = deque(maxlen=self.period)
        self._total = Decimal("0")

    def push(self, raw: Decimal) -> Optional[Decimal]:
        value = decimal_value(raw, "value")
        if len(self._values) == self.period:
            self._total -= self._values[0]
        self._values.append(value)
        self._total += value
        return self.mean

    @property
    def ready(self) -> bool:
        return len(self._values) == self.period

    @property
    def mean(self) -> Optional[Decimal]:
        if not self.ready:
            return None
        return self._total / self.period

    @property
    def minimum(self) -> Optional[Decimal]:
        return min(self._values) if self._values else None

    @property
    def maximum(self) -> Optional[Decimal]:
        return max(self._values) if self._values else None

    def values(self) -> Tuple[Decimal, ...]:
        return tuple(self._values)
