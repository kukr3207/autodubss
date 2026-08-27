"""Moving-average crossover strategy with transition-only signals."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from ..errors import ValidationError
from ..validation import integer_value
from ..domain.portfolio import PortfolioSnapshot
from ..market.indicators import RollingWindow
from ..market.models import Bar
from .base import Strategy
from .signals import Signal, SignalAction


class MovingAverageCrossStrategy(Strategy):
    def __init__(self, strategy_id: str, fast_period: int = 10, slow_period: int = 30) -> None:
        super().__init__(strategy_id)
        self.fast_period = integer_value(fast_period, "fast_period", minimum=1)
        self.slow_period = integer_value(slow_period, "slow_period", minimum=2)
        if self.fast_period >= self.slow_period:
            raise ValidationError("fast_period must be below slow_period")
        self._fast = RollingWindow(self.fast_period)
        self._slow = RollingWindow(self.slow_period)
        self._regime: Optional[int] = None

    def on_start(self) -> None:
        self._fast = RollingWindow(self.fast_period)
        self._slow = RollingWindow(self.slow_period)
        self._regime = None

    def on_bar(self, bar: Bar, portfolio: PortfolioSnapshot) -> Optional[Signal]:
        fast = self._fast.push(bar.close)
        slow = self._slow.push(bar.close)
        if fast is None or slow is None:
            return None
        regime = 1 if fast > slow else -1 if fast < slow else 0
        previous = self._regime
        self._regime = regime
        if previous is None or regime == previous or regime == 0:
            return None
        action = SignalAction.BUY if regime > 0 else SignalAction.SELL
        return Signal(
            self.strategy_id,
            bar.instrument,
            action,
            bar.closed_at,
            reference_price=bar.close,
            reason="fast moving average crossed %s slow average" % (
                "above" if regime > 0 else "below"
            ),
            metadata={
                "fast": format(fast, "f"),
                "slow": format(slow, "f"),
                "fastPeriod": self.fast_period,
                "slowPeriod": self.slow_period,
            },
        )

    def state(self) -> Dict[str, Any]:
        result = super().state()
        result.update(
            {
                "fastPeriod": self.fast_period,
                "slowPeriod": self.slow_period,
                "fast": None if self._fast.mean is None else format(self._fast.mean, "f"),
                "slow": None if self._slow.mean is None else format(self._slow.mean, "f"),
                "regime": self._regime,
            }
        )
        return result
