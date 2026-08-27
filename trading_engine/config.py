"""Environment-based configuration without credentials in source control."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional

from .errors import ConfigurationError
from .validation import clean_text, decimal_value, integer_value
from .risk.models import RiskLimits


def _required(environment: Mapping[str, str], key: str) -> str:
    value = environment.get(key)
    if value is None or not value.strip():
        raise ConfigurationError(
            "required environment variable is missing",
            details={"variable": key},
        )
    return value.strip()


def _boolean(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError("boolean setting has an invalid value", details={"value": value})


def _integer(environment: Mapping[str, str], key: str, default: int) -> int:
    raw = environment.get(key)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigurationError("integer setting has an invalid value", details={"variable": key})
    try:
        return integer_value(value, key, minimum=1)
    except Exception as exc:
        raise ConfigurationError(str(exc), details={"variable": key})


def _decimal(environment: Mapping[str, str], key: str, default: Decimal) -> Decimal:
    raw = environment.get(key)
    if raw is None:
        return default
    try:
        return decimal_value(raw, key, positive=True, allow_zero=False)
    except Exception as exc:
        raise ConfigurationError(str(exc), details={"variable": key})


@dataclass(frozen=True)
class BrokerSettings:
    provider: str
    account: str
    api_key: str
    api_secret: str
    paper_trading: bool = True

    def __post_init__(self) -> None:
        for field in ("provider", "account"):
            object.__setattr__(self, field, clean_text(getattr(self, field), field, max_length=300))
        for field in ("api_key", "api_secret"):
            value = getattr(self, field)
            if not isinstance(value, str):
                raise ConfigurationError("%s must be a string" % field)
            object.__setattr__(self, field, value.strip())
        if not self.paper_trading and (not self.api_key or not self.api_secret):
            raise ConfigurationError("live broker settings require credentials")

    def public_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "account": self.account,
            "paperTrading": self.paper_trading,
            "credentialsConfigured": bool(self.api_key and self.api_secret),
        }


@dataclass(frozen=True)
class EngineSettings:
    environment: str
    broker: BrokerSettings
    risk_limits: RiskLimits
    audit_directory: str
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        object.__setattr__(self, "environment", clean_text(self.environment, "environment", max_length=40).lower())
        if not isinstance(self.broker, BrokerSettings):
            raise ConfigurationError("broker settings are invalid")
        if not isinstance(self.risk_limits, RiskLimits):
            raise ConfigurationError("risk limits are invalid")
        object.__setattr__(self, "audit_directory", clean_text(self.audit_directory, "audit_directory"))
        level = clean_text(self.log_level, "log_level", max_length=20).upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError("unsupported log level")
        object.__setattr__(self, "log_level", level)

    def public_dict(self) -> Dict[str, Any]:
        return {
            "environment": self.environment,
            "broker": self.broker.public_dict(),
            "riskLimits": self.risk_limits.as_dict(),
            "auditDirectory": self.audit_directory,
            "logLevel": self.log_level,
        }


def load_settings(environment: Optional[Mapping[str, str]] = None) -> EngineSettings:
    values = dict(os.environ if environment is None else environment)
    broker = BrokerSettings(
        provider=values.get("TRADING_BROKER", "simulated"),
        account=values.get("TRADING_ACCOUNT", "paper"),
        api_key=(values.get("TRADING_API_KEY") or ""),
        api_secret=(values.get("TRADING_API_SECRET") or ""),
        paper_trading=_boolean(values.get("TRADING_PAPER"), True),
    )
    if not broker.paper_trading:
        broker = BrokerSettings(
            broker.provider,
            broker.account,
            _required(values, "TRADING_API_KEY"),
            _required(values, "TRADING_API_SECRET"),
            False,
        )
    limits = RiskLimits(
        max_order_quantity=_integer(values, "RISK_MAX_ORDER_QUANTITY", 1000),
        max_order_notional=_decimal(values, "RISK_MAX_ORDER_NOTIONAL", Decimal("1000000")),
        max_position_quantity=_integer(values, "RISK_MAX_POSITION_QUANTITY", 5000),
        max_gross_exposure=_decimal(values, "RISK_MAX_GROSS_EXPOSURE", Decimal("5000000")),
        max_net_exposure=_decimal(values, "RISK_MAX_NET_EXPOSURE", Decimal("2500000")),
        max_daily_loss=_decimal(values, "RISK_MAX_DAILY_LOSS", Decimal("100000")),
        max_open_orders=_integer(values, "RISK_MAX_OPEN_ORDERS", 100),
        max_quote_age_seconds=_integer(values, "RISK_MAX_QUOTE_AGE_SECONDS", 30),
        price_band_percent=_decimal(values, "RISK_PRICE_BAND_PERCENT", Decimal("10")),
    )
    return EngineSettings(
        environment=values.get("TRADING_ENVIRONMENT", "development"),
        broker=broker,
        risk_limits=limits,
        audit_directory=values.get("TRADING_AUDIT_DIRECTORY", "var/audit"),
        log_level=values.get("TRADING_LOG_LEVEL", "INFO"),
    )
