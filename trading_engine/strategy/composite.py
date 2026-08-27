"""Combine independent strategies with explicit consensus rules."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..errors import ValidationError
from ..validation import enum_value, integer_value
from ..domain.portfolio import PortfolioSnapshot
from ..market.models import Bar
from .base import Strategy
from .signals import Signal, SignalAction


class ConsensusMode(Enum):
    ANY = "any"
    MAJORITY = "majority"
    UNANIMOUS = "unanimous"


class CompositeStrategy(Strategy):
    def __init__(
        self,
        strategy_id: str,
        strategies: Iterable[Strategy],
        *,
        mode: ConsensusMode = ConsensusMode.MAJORITY,
        minimum_votes: int = 1,
    ) -> None:
        super().__init__(strategy_id)
        checked = tuple(strategies)
        if not checked or not all(isinstance(item, Strategy) for item in checked):
            raise ValidationError("composite requires at least one strategy")
        if len({item.strategy_id for item in checked}) != len(checked):
            raise ValidationError("child strategy ids must be unique")
        self.strategies = checked
        self.mode = enum_value(mode, ConsensusMode, "mode")
        self.minimum_votes = integer_value(
            minimum_votes,
            "minimum_votes",
            minimum=1,
            maximum=len(checked),
        )
        self._last_votes: Tuple[Signal, ...] = ()

    def on_start(self) -> None:
        self._last_votes = ()
        for strategy in self.strategies:
            if strategy.started:
                strategy.stop()
            strategy.start()

    def on_stop(self) -> None:
        for strategy in self.strategies:
            strategy.stop()

    def on_bar(self, bar: Bar, portfolio: PortfolioSnapshot) -> Optional[Signal]:
        votes = tuple(
            signal
            for strategy in self.strategies
            for signal in (strategy.evaluate(bar, portfolio),)
            if signal is not None and signal.action is not SignalAction.HOLD
        )
        self._last_votes = votes
        if not votes:
            return None
        counts = Counter(signal.action for signal in votes)
        action, count = counts.most_common(1)[0]
        tied = sum(1 for value in counts.values() if value == count) > 1
        if tied or count < self.minimum_votes:
            return None
        if self.mode is ConsensusMode.UNANIMOUS and count != len(self.strategies):
            return None
        if self.mode is ConsensusMode.MAJORITY and count <= len(self.strategies) // 2:
            return None
        reference_values = [
            signal.reference_price for signal in votes if signal.reference_price is not None
        ]
        reference = (
            sum(reference_values, Decimal("0")) / len(reference_values)
            if reference_values
            else None
        )
        strength = Decimal(count) / len(self.strategies)
        return Signal(
            self.strategy_id,
            bar.instrument,
            action,
            bar.closed_at,
            strength=strength,
            reference_price=reference,
            reason="%d of %d child strategies agreed" % (count, len(self.strategies)),
            metadata={
                "mode": self.mode.value,
                "votes": [
                    {"strategyId": signal.strategy_id, "action": signal.action.value}
                    for signal in votes
                ],
            },
        )

    def state(self) -> Dict[str, Any]:
        result = super().state()
        result.update(
            {
                "mode": self.mode.value,
                "minimumVotes": self.minimum_votes,
                "children": [strategy.state() for strategy in self.strategies],
                "lastVotes": [signal.as_dict() for signal in self._last_votes],
            }
        )
        return result
