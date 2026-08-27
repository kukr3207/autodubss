"""Strategy outputs are explicit, serializable, and free of broker concerns."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Mapping, Optional

from ..errors import ValidationError
from ..validation import aware_time, clean_text, decimal_value, enum_value
from ..domain.instruments import Instrument


class SignalAction(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    EXIT = "exit"


@dataclass(frozen=True)
class Signal:
    strategy_id: str
    instrument: Instrument
    action: SignalAction
    generated_at: datetime
    strength: Decimal = Decimal("1")
    reference_price: Optional[Decimal] = None
    reason: Optional[str] = None
    metadata: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", clean_text(self.strategy_id, "strategy_id", max_length=80))
        if not isinstance(self.instrument, Instrument):
            raise ValidationError("instrument must be an Instrument")
        object.__setattr__(self, "action", enum_value(self.action, SignalAction, "action"))
        object.__setattr__(self, "generated_at", aware_time(self.generated_at, "generated_at"))
        strength = decimal_value(self.strength, "strength", non_negative=True)
        if strength > 1:
            raise ValidationError("strength cannot exceed one")
        object.__setattr__(self, "strength", strength)
        if self.reference_price is not None:
            object.__setattr__(
                self,
                "reference_price",
                decimal_value(self.reference_price, "reference_price", positive=True, allow_zero=False),
            )
        if self.reason is not None:
            object.__setattr__(self, "reason", clean_text(self.reason, "reason", max_length=300))
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    @property
    def actionable(self) -> bool:
        return self.action is not SignalAction.HOLD

    def as_dict(self) -> Dict[str, Any]:
        return {
            "strategyId": self.strategy_id,
            "instrument": self.instrument.as_dict(),
            "action": self.action.value,
            "generatedAt": self.generated_at.isoformat(),
            "strength": format(self.strength, "f"),
            "referencePrice": (
                None if self.reference_price is None else format(self.reference_price, "f")
            ),
            "reason": self.reason,
            "metadata": dict(self.metadata or {}),
        }
