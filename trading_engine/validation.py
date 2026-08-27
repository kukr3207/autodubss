"""Small validation helpers used by immutable domain records."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Optional, Type, TypeVar

from .errors import ValidationError


E = TypeVar("E", bound=Enum)


def clean_text(value: Any, field: str, *, max_length: Optional[int] = None) -> str:
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % field)
    result = value.strip()
    if not result:
        raise ValidationError("%s cannot be blank" % field)
    if max_length is not None and len(result) > max_length:
        raise ValidationError(
            "%s cannot exceed %d characters" % (field, max_length),
            details={"field": field, "maxLength": max_length},
        )
    return result


def clean_code(
    value: Any,
    field: str,
    *,
    min_length: int = 1,
    max_length: int = 32,
) -> str:
    result = clean_text(value, field, max_length=max_length).upper()
    if len(result) < min_length:
        raise ValidationError("%s is too short" % field)
    if not all(character.isalnum() or character in "-_." for character in result):
        raise ValidationError("%s contains unsupported characters" % field)
    return result


def decimal_value(
    value: Any,
    field: str,
    *,
    positive: bool = False,
    non_negative: bool = False,
    allow_zero: bool = True,
) -> Decimal:
    if isinstance(value, bool):
        raise ValidationError("%s must be numeric" % field)
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("%s must be numeric" % field)
    if not result.is_finite():
        raise ValidationError("%s must be finite" % field)
    if positive and (result < 0 or (result == 0 and not allow_zero)):
        raise ValidationError("%s must be positive" % field)
    if non_negative and result < 0:
        raise ValidationError("%s cannot be negative" % field)
    return result


def integer_value(
    value: Any,
    field: str,
    *,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % field)
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (field, minimum))
    if maximum is not None and value > maximum:
        raise ValidationError("%s must be at most %d" % (field, maximum))
    return value


def aware_time(value: Any, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("%s must be a datetime" % field)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("%s must include a timezone" % field)
    return value.astimezone(timezone.utc)


def enum_value(value: Any, enum_type: Type[E], field: str) -> E:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value).strip().lower())
    except (TypeError, ValueError):
        choices = [member.value for member in enum_type]
        raise ValidationError(
            "%s must be one of %s" % (field, ", ".join(choices)),
            details={"field": field, "choices": choices},
        )


def finite_float(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValidationError("%s must be numeric" % field)
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValidationError("%s must be numeric" % field)
    if not math.isfinite(result):
        raise ValidationError("%s must be finite" % field)
    return result
