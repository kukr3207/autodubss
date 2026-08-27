"""Thread-safe account portfolio and cash ledger."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from threading import RLock
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ..errors import ValidationError
from ..validation import clean_code
from .fills import Fill
from .identifiers import AccountId, TradeId
from .money import Money
from .positions import Position


@dataclass(frozen=True)
class PortfolioSnapshot:
    account_id: AccountId
    cash: Mapping[str, Money]
    positions: Tuple[Position, ...]
    applied_trades: Tuple[TradeId, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, AccountId):
            raise ValidationError("account_id must be an AccountId")
        object.__setattr__(self, "cash", MappingProxyType(dict(self.cash)))
        object.__setattr__(self, "positions", tuple(self.positions))
        object.__setattr__(self, "applied_trades", tuple(self.applied_trades))

    def cash_balance(self, currency: str) -> Money:
        code = clean_code(currency, "currency", min_length=3, max_length=3)
        return self.cash.get(code, Money.zero(code))

    @property
    def realized_pnl(self) -> Mapping[str, Money]:
        totals: Dict[str, Money] = {}
        for position in self.positions:
            currency = position.instrument.contract.price_currency
            current = totals.get(currency, Money.zero(currency))
            totals[currency] = current + Money(position.realized_pnl, currency)
        return MappingProxyType(totals)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "accountId": str(self.account_id),
            "cash": {key: value.as_dict() for key, value in sorted(self.cash.items())},
            "positions": [position.as_dict() for position in self.positions],
            "appliedTrades": [str(trade_id) for trade_id in self.applied_trades],
        }


class Portfolio:
    """Applies fills exactly once and publishes immutable snapshots."""

    def __init__(
        self,
        account_id: AccountId,
        initial_cash: Optional[Iterable[Money]] = None,
    ) -> None:
        if not isinstance(account_id, AccountId):
            raise ValidationError("account_id must be an AccountId")
        self.account_id = account_id
        self._cash: Dict[str, Money] = {}
        self._positions: Dict[str, Position] = {}
        self._applied: Dict[str, TradeId] = {}
        self._lock = RLock()
        for amount in initial_cash or ():
            self.deposit(amount)

    def deposit(self, amount: Money) -> Money:
        if not isinstance(amount, Money):
            raise ValidationError("deposit must be Money")
        if amount.amount <= 0:
            raise ValidationError("deposit must be positive")
        with self._lock:
            current = self._cash.get(amount.currency, Money.zero(amount.currency))
            updated = current + amount
            self._cash[amount.currency] = updated
            return updated

    def withdraw(self, amount: Money, *, allow_negative: bool = False) -> Money:
        if not isinstance(amount, Money):
            raise ValidationError("withdrawal must be Money")
        if amount.amount <= 0:
            raise ValidationError("withdrawal must be positive")
        with self._lock:
            current = self._cash.get(amount.currency, Money.zero(amount.currency))
            updated = current - amount
            if updated.amount < 0 and not allow_negative:
                raise ValidationError(
                    "insufficient cash",
                    details={
                        "currency": amount.currency,
                        "available": format(current.amount, "f"),
                        "requested": format(amount.amount, "f"),
                    },
                )
            self._cash[amount.currency] = updated
            return updated

    def apply_fill(self, fill: Fill) -> PortfolioSnapshot:
        if not isinstance(fill, Fill):
            raise ValidationError("fill must be a Fill")
        trade_key = str(fill.trade_id)
        with self._lock:
            if trade_key in self._applied:
                return self.snapshot()
            key = fill.instrument.key
            position = self._positions.get(key, Position(fill.instrument))
            self._positions[key] = position.apply(fill)
            currency = fill.cash_effect.currency
            current_cash = self._cash.get(currency, Money.zero(currency))
            self._cash[currency] = current_cash + fill.cash_effect
            self._applied[trade_key] = fill.trade_id
            return self.snapshot()

    def mark(self, instrument_key: str, price: Any, at: Any) -> Position:
        with self._lock:
            try:
                current = self._positions[instrument_key]
            except KeyError:
                raise KeyError("unknown position %s" % instrument_key)
            updated = current.mark(price, at)
            self._positions[instrument_key] = updated
            return updated

    def get_position(self, instrument_key: str) -> Position:
        with self._lock:
            try:
                return self._positions[instrument_key]
            except KeyError:
                raise KeyError("unknown position %s" % instrument_key)

    def snapshot(self) -> PortfolioSnapshot:
        with self._lock:
            return PortfolioSnapshot(
                account_id=self.account_id,
                cash=dict(self._cash),
                positions=tuple(self._positions[key] for key in sorted(self._positions)),
                applied_trades=tuple(self._applied[key] for key in sorted(self._applied)),
            )
