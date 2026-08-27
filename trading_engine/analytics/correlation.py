"""Covariance and correlation matrices for aligned return series."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from types import MappingProxyType
from typing import Dict, Iterable, Mapping, Sequence, Tuple

from ..errors import ValidationError
from .series import DecimalSeries


def average(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / len(values) if values else Decimal("0")


def covariance(pairs: Sequence[Tuple[Decimal, Decimal]]) -> Decimal:
    if len(pairs) < 2:
        return Decimal("0")
    left = average([pair[0] for pair in pairs])
    right = average([pair[1] for pair in pairs])
    return sum(
        ((x_value - left) * (y_value - right) for x_value, y_value in pairs),
        Decimal("0"),
    ) / Decimal(len(pairs) - 1)


def variance(values: Sequence[Decimal]) -> Decimal:
    return covariance(tuple((value, value) for value in values))


def correlation(left: DecimalSeries, right: DecimalSeries) -> Decimal:
    pairs = left.align(right)
    if len(pairs) < 2:
        return Decimal("0")
    left_variance = variance([pair[0] for pair in pairs])
    right_variance = variance([pair[1] for pair in pairs])
    if left_variance == 0 or right_variance == 0:
        return Decimal("0")
    denominator = Decimal(str(sqrt(float(left_variance * right_variance))))
    return covariance(pairs) / denominator


@dataclass(frozen=True)
class CorrelationMatrix:
    names: Tuple[str, ...]
    values: Mapping[str, Mapping[str, Decimal]]

    def __post_init__(self) -> None:
        names = tuple(self.names)
        if len(set(names)) != len(names):
            raise ValidationError("correlation matrix names must be unique")
        checked: Dict[str, Mapping[str, Decimal]] = {}
        for row in names:
            if row not in self.values:
                raise ValidationError("correlation matrix is missing a row")
            row_values = dict(self.values[row])
            if set(row_values) != set(names):
                raise ValidationError("correlation matrix row is incomplete")
            checked[row] = MappingProxyType(row_values)
        for left in names:
            if checked[left][left] != 1:
                raise ValidationError("correlation matrix diagonal must be one")
            for right in names:
                if checked[left][right] != checked[right][left]:
                    raise ValidationError("correlation matrix must be symmetric")
        object.__setattr__(self, "names", names)
        object.__setattr__(self, "values", MappingProxyType(checked))

    def get(self, left: str, right: str) -> Decimal:
        try:
            return self.values[left][right]
        except KeyError:
            raise KeyError("unknown correlation series")

    def as_dict(self):
        return {
            "names": list(self.names),
            "values": {
                row: {column: format(value, "f") for column, value in values.items()}
                for row, values in self.values.items()
            },
        }


def correlation_matrix(series: Iterable[DecimalSeries]) -> CorrelationMatrix:
    checked = tuple(series)
    if not checked:
        raise ValidationError("at least one series is required")
    if len({item.name for item in checked}) != len(checked):
        raise ValidationError("series names must be unique")
    values: Dict[str, Dict[str, Decimal]] = {}
    for left in checked:
        row = {}
        for right in checked:
            row[right.name] = Decimal("1") if left is right else correlation(left, right)
        values[left.name] = row
    return CorrelationMatrix(tuple(item.name for item in checked), values)
