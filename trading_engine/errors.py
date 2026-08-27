"""Error types shared by the trading engine.

The web application can translate these exceptions into HTTP responses without
having to inspect implementation-specific messages.  Details are copied and
frozen so callers cannot mutate an exception after it has been raised.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Sequence


class TradingEngineError(Exception):
    """Base class for expected engine failures."""

    code = "trading_engine_error"

    def __init__(
        self,
        message: str,
        *,
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = str(message)
        self.details = MappingProxyType(dict(details or {}))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


class ValidationError(TradingEngineError):
    code = "validation_error"


class ConfigurationError(TradingEngineError):
    code = "configuration_error"


class MarketDataError(TradingEngineError):
    code = "market_data_error"


class OrderStateError(TradingEngineError):
    code = "order_state_error"


class DuplicateRequestError(TradingEngineError):
    code = "duplicate_request"


class BrokerError(TradingEngineError):
    code = "broker_error"

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        merged = dict(details or {})
        merged["retryable"] = bool(retryable)
        super().__init__(message, details=merged)
        self.retryable = bool(retryable)


class RiskRejectedError(TradingEngineError):
    code = "risk_rejected"

    def __init__(self, message: str, violations: Sequence[Mapping[str, Any]]) -> None:
        copied = tuple(dict(item) for item in violations)
        super().__init__(message, details={"violations": list(copied)})
        self.violations = copied
