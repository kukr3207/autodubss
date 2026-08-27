"""Aligned decimal time series used by portfolio analytics."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from ..errors import ValidationError
from ..validation import aware_time, clean_text, decimal_value, integer_value


@dataclass(frozen=True)
class Observation:
    observed_at: datetime
    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", aware_time(self.observed_at, "observed_at"))
        object.__setattr__(self, "value", decimal_value(self.value, "value"))


class DecimalSeries:
    def __init__(self, name: str, observations: Iterable[Observation] = ()) -> None:
        self.name = clean_text(name, "name", max_length=100)
        checked = tuple(observations)
        if not all(isinstance(item, Observation) for item in checked):
            raise ValidationError("series must contain Observation values")
        if tuple(sorted(checked, key=lambda item: item.observed_at)) != checked:
            raise ValidationError("series observations must be chronological")
        if len({item.observed_at for item in checked}) != len(checked):
            raise ValidationError("series times cannot repeat")
        self._items = checked

    def __iter__(self) -> Iterator[Observation]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @property
    def values(self) -> Tuple[Decimal, ...]:
        return tuple(item.value for item in self._items)

    @property
    def times(self) -> Tuple[datetime, ...]:
        return tuple(item.observed_at for item in self._items)

    def at(self, observed_at: datetime, *, exact: bool = False) -> Observation:
        checked = aware_time(observed_at, "observed_at")
        times = self.times
        index = bisect_left(times, checked)
        if index < len(times) and times[index] == checked:
            return self._items[index]
        if exact or index == 0:
            raise KeyError("series has no observation at the requested time")
        return self._items[index - 1]

    def between(self, start: datetime, end: datetime) -> "DecimalSeries":
        checked_start = aware_time(start, "start")
        checked_end = aware_time(end, "end")
        if checked_end < checked_start:
            raise ValidationError("end cannot predate start")
        return DecimalSeries(
            self.name,
            (
                item
                for item in self._items
                if checked_start <= item.observed_at <= checked_end
            ),
        )

    def differences(self) -> "DecimalSeries":
        return DecimalSeries(
            "%s differences" % self.name,
            (
                Observation(current.observed_at, current.value - previous.value)
                for previous, current in zip(self._items, self._items[1:])
            ),
        )

    def percentage_returns(self) -> "DecimalSeries":
        result = []
        for previous, current in zip(self._items, self._items[1:]):
            if previous.value == 0:
                raise ValidationError("cannot calculate a return from zero")
            result.append(
                Observation(
                    current.observed_at,
                    current.value / previous.value - Decimal("1"),
                )
            )
        return DecimalSeries("%s returns" % self.name, result)

    def rolling_mean(self, window: int) -> "DecimalSeries":
        checked = integer_value(window, "window", minimum=1)
        result = []
        total = Decimal("0")
        values: List[Decimal] = []
        for item in self._items:
            values.append(item.value)
            total += item.value
            if len(values) > checked:
                total -= values[-checked - 1]
            if len(values) >= checked:
                result.append(Observation(item.observed_at, total / checked))
        return DecimalSeries("%s %d-period mean" % (self.name, checked), result)

    def align(self, other: "DecimalSeries") -> Tuple[Tuple[Decimal, Decimal], ...]:
        if not isinstance(other, DecimalSeries):
            raise ValidationError("other must be DecimalSeries")
        left = {item.observed_at: item.value for item in self._items}
        right = {item.observed_at: item.value for item in other}
        return tuple((left[key], right[key]) for key in sorted(set(left) & set(right)))

    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "observations": [
                {"observedAt": item.observed_at.isoformat(), "value": format(item.value, "f")}
                for item in self._items
            ],
        }
