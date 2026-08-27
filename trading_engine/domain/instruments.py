"""Tradable instrument and contract specifications."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, Optional

from ..errors import ValidationError
from ..validation import clean_code, clean_text, decimal_value, enum_value, integer_value


class AssetClass(Enum):
    EQUITY = "equity"
    FUTURE = "future"
    OPTION = "option"
    FOREX = "forex"
    CRYPTO = "crypto"
    INDEX = "index"


@dataclass(frozen=True)
class ContractSpec:
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.01")
    multiplier: Decimal = Decimal("1")
    price_currency: str = "INR"

    def __post_init__(self) -> None:
        object.__setattr__(self, "lot_size", integer_value(self.lot_size, "lot_size", minimum=1))
        object.__setattr__(
            self,
            "tick_size",
            decimal_value(self.tick_size, "tick_size", positive=True, allow_zero=False),
        )
        object.__setattr__(
            self,
            "multiplier",
            decimal_value(self.multiplier, "multiplier", positive=True, allow_zero=False),
        )
        object.__setattr__(
            self,
            "price_currency",
            clean_code(self.price_currency, "price_currency", min_length=3, max_length=3),
        )

    def validate_quantity(self, quantity: int) -> int:
        result = integer_value(quantity, "quantity", minimum=1)
        if result % self.lot_size:
            raise ValidationError(
                "quantity must be a multiple of the lot size",
                details={"quantity": result, "lotSize": self.lot_size},
            )
        return result

    def round_price(self, price: Any) -> Decimal:
        value = decimal_value(price, "price", positive=True, allow_zero=False)
        ticks = (value / self.tick_size).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return ticks * self.tick_size


@dataclass(frozen=True)
class Instrument:
    symbol: str
    exchange: str
    asset_class: AssetClass
    contract: ContractSpec = ContractSpec()
    description: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", clean_code(self.symbol, "symbol", max_length=40))
        object.__setattr__(self, "exchange", clean_code(self.exchange, "exchange", max_length=20))
        object.__setattr__(self, "asset_class", enum_value(self.asset_class, AssetClass, "asset_class"))
        if not isinstance(self.contract, ContractSpec):
            raise ValidationError("contract must be a ContractSpec")
        if self.description is not None:
            object.__setattr__(self, "description", clean_text(self.description, "description", max_length=200))

    @property
    def key(self) -> str:
        return "%s:%s" % (self.exchange, self.symbol)

    def validate_quantity(self, quantity: int) -> int:
        return self.contract.validate_quantity(quantity)

    def notional(self, price: Any, quantity: int) -> Decimal:
        checked_price = decimal_value(price, "price", positive=True, allow_zero=False)
        checked_quantity = self.validate_quantity(quantity)
        return checked_price * checked_quantity * self.contract.multiplier

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "assetClass": self.asset_class.value,
            "description": self.description,
            "contract": {
                "lotSize": self.contract.lot_size,
                "tickSize": format(self.contract.tick_size, "f"),
                "multiplier": format(self.contract.multiplier, "f"),
                "priceCurrency": self.contract.price_currency,
            },
        }
