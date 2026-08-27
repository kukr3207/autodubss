"""Execution-price models with bounded, explicit slippage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from ..errors import ValidationError
from ..validation import decimal_value, integer_value
from ..domain.orders import OrderRequest, Side
from ..market.models import Quote


class SlippageModel(ABC):
    @abstractmethod
    def execution_price(self, request: OrderRequest, quote: Quote, quantity: int) -> Decimal:
        pass


@dataclass(frozen=True)
class NoSlippage(SlippageModel):
    def execution_price(self, request: OrderRequest, quote: Quote, quantity: int) -> Decimal:
        return quote.executable_price(request.side)


@dataclass(frozen=True)
class FixedBasisPointSlippage(SlippageModel):
    basis_points: Decimal

    def __post_init__(self) -> None:
        value = decimal_value(self.basis_points, "basis_points", non_negative=True)
        if value > Decimal("10000"):
            raise ValidationError("basis_points cannot exceed 10000")
        object.__setattr__(self, "basis_points", value)

    def execution_price(self, request: OrderRequest, quote: Quote, quantity: int) -> Decimal:
        reference = quote.executable_price(request.side)
        adjustment = reference * self.basis_points / Decimal("10000")
        raw = reference + adjustment if request.side is Side.BUY else reference - adjustment
        return request.instrument.contract.round_price(raw)


@dataclass(frozen=True)
class VolumeImpactSlippage(SlippageModel):
    basis_points_per_lot: Decimal = Decimal("0.5")
    max_basis_points: Decimal = Decimal("50")

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "basis_points_per_lot",
            decimal_value(self.basis_points_per_lot, "basis_points_per_lot", non_negative=True),
        )
        object.__setattr__(
            self,
            "max_basis_points",
            decimal_value(self.max_basis_points, "max_basis_points", non_negative=True),
        )
        if self.max_basis_points > Decimal("10000"):
            raise ValidationError("max_basis_points cannot exceed 10000")

    def execution_price(self, request: OrderRequest, quote: Quote, quantity: int) -> Decimal:
        checked = integer_value(quantity, "quantity", minimum=1)
        lots = Decimal(checked) / request.instrument.contract.lot_size
        impact = min(lots * self.basis_points_per_lot, self.max_basis_points)
        return FixedBasisPointSlippage(impact).execution_price(request, quote, checked)
