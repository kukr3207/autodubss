"""Risk limits, violations, and immutable decision reports."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from ..errors import ValidationError
from ..validation import decimal_value, enum_value, integer_value
from ..domain.orders import OrderRequest


class RiskSeverity(Enum):
    WARNING = "warning"
    BLOCK = "block"


@dataclass(frozen=True)
class RiskLimits:
    max_order_quantity: int = 1000
    max_order_notional: Decimal = Decimal("1000000")
    max_position_quantity: int = 5000
    max_gross_exposure: Decimal = Decimal("5000000")
    max_net_exposure: Decimal = Decimal("2500000")
    max_daily_loss: Decimal = Decimal("100000")
    max_open_orders: int = 100
    max_quote_age_seconds: int = 30
    price_band_percent: Decimal = Decimal("10")

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_order_quantity",
            integer_value(self.max_order_quantity, "max_order_quantity", minimum=1),
        )
        object.__setattr__(
            self,
            "max_position_quantity",
            integer_value(self.max_position_quantity, "max_position_quantity", minimum=1),
        )
        object.__setattr__(
            self,
            "max_open_orders",
            integer_value(self.max_open_orders, "max_open_orders", minimum=1),
        )
        object.__setattr__(
            self,
            "max_quote_age_seconds",
            integer_value(self.max_quote_age_seconds, "max_quote_age_seconds", minimum=1),
        )
        for field in (
            "max_order_notional",
            "max_gross_exposure",
            "max_net_exposure",
            "max_daily_loss",
            "price_band_percent",
        ):
            object.__setattr__(
                self,
                field,
                decimal_value(getattr(self, field), field, positive=True, allow_zero=False),
            )
        if self.max_net_exposure > self.max_gross_exposure:
            raise ValidationError("max_net_exposure cannot exceed max_gross_exposure")
        if self.price_band_percent > Decimal("100"):
            raise ValidationError("price_band_percent cannot exceed 100")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "maxOrderQuantity": self.max_order_quantity,
            "maxOrderNotional": format(self.max_order_notional, "f"),
            "maxPositionQuantity": self.max_position_quantity,
            "maxGrossExposure": format(self.max_gross_exposure, "f"),
            "maxNetExposure": format(self.max_net_exposure, "f"),
            "maxDailyLoss": format(self.max_daily_loss, "f"),
            "maxOpenOrders": self.max_open_orders,
            "maxQuoteAgeSeconds": self.max_quote_age_seconds,
            "priceBandPercent": format(self.price_band_percent, "f"),
        }


@dataclass(frozen=True)
class RiskViolation:
    rule: str
    message: str
    severity: RiskSeverity
    observed: Optional[str] = None
    limit: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.rule, str) or not self.rule.strip():
            raise ValidationError("risk rule cannot be blank")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValidationError("risk message cannot be blank")
        object.__setattr__(self, "rule", self.rule.strip())
        object.__setattr__(self, "message", self.message.strip())
        object.__setattr__(self, "severity", enum_value(self.severity, RiskSeverity, "severity"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity.value,
            "observed": self.observed,
            "limit": self.limit,
        }


@dataclass(frozen=True)
class RiskDecision:
    request: OrderRequest
    violations: Tuple[RiskViolation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.request, OrderRequest):
            raise ValidationError("request must be an OrderRequest")
        copied = tuple(self.violations)
        if not all(isinstance(item, RiskViolation) for item in copied):
            raise ValidationError("violations must contain RiskViolation values")
        object.__setattr__(self, "violations", copied)

    @property
    def allowed(self) -> bool:
        return not any(item.severity is RiskSeverity.BLOCK for item in self.violations)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "request": self.request.as_dict(),
            "violations": [item.as_dict() for item in self.violations],
        }
