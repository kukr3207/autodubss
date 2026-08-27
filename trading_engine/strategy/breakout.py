"""Donchian-style range breakout with optional trailing exit."""

from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import Deque, Dict, Optional, Tuple

from ..errors import ValidationError
from ..validation import decimal_value, integer_value
from ..domain.portfolio import PortfolioSnapshot
from ..market.models import Bar
from .base import Strategy
from .signals import Signal, SignalAction


class BreakoutStrategy(Strategy):
    def __init__(
        self,
        strategy_id: str,
        lookback: int = 20,
        trailing_percent: Decimal = Decimal("5"),
    ) -> None:
        super().__init__(strategy_id)
        self.lookback = integer_value(lookback, "lookback", minimum=2)
        trailing = decimal_value(trailing_percent, "trailing_percent", non_negative=True)
        if trailing > 100:
            raise ValidationError("trailing_percent cannot exceed 100")
        self.trailing_percent = trailing
        self._highs: Deque[Decimal] = deque(maxlen=self.lookback)
        self._lows: Deque[Decimal] = deque(maxlen=self.lookback)
        self._direction = 0
        self._extreme: Optional[Decimal] = None

    def on_start(self) -> None:
        self._highs = deque(maxlen=self.lookback)
        self._lows = deque(maxlen=self.lookback)
        self._direction = 0
        self._extreme = None

    def on_bar(self, bar: Bar, portfolio: PortfolioSnapshot) -> Optional[Signal]:
        upper = max(self._highs) if len(self._highs) == self.lookback else None
        lower = min(self._lows) if len(self._lows) == self.lookback else None
        signal: Optional[Signal] = None
        if upper is not None and lower is not None:
            if self._direction == 0 and bar.close > upper:
                self._direction = 1
                self._extreme = bar.high
                signal = self._signal(bar, SignalAction.BUY, "close broke above the range")
            elif self._direction == 0 and bar.close < lower:
                self._direction = -1
                self._extreme = bar.low
                signal = self._signal(bar, SignalAction.SELL, "close broke below the range")
            elif self._direction > 0:
                self._extreme = max(self._extreme or bar.high, bar.high)
                stop = self._extreme * (Decimal("1") - self.trailing_percent / Decimal("100"))
                if bar.close <= stop:
                    signal = self._signal(bar, SignalAction.EXIT, "long trailing stop was reached")
                    self._direction = 0
                    self._extreme = None
            else:
                self._extreme = min(self._extreme or bar.low, bar.low)
                stop = self._extreme * (Decimal("1") + self.trailing_percent / Decimal("100"))
                if bar.close >= stop:
                    signal = self._signal(bar, SignalAction.EXIT, "short trailing stop was reached")
                    self._direction = 0
                    self._extreme = None
        self._highs.append(bar.high)
        self._lows.append(bar.low)
        return signal

    def _signal(self, bar: Bar, action: SignalAction, reason: str) -> Signal:
        return Signal(
            self.strategy_id,
            bar.instrument,
            action,
            bar.closed_at,
            reference_price=bar.close,
            reason=reason,
            metadata={
                "lookback": self.lookback,
                "trailingPercent": format(self.trailing_percent, "f"),
            },
        )

    def state(self) -> Dict[str, object]:
        result = super().state()
        result.update(
            {
                "lookback": self.lookback,
                "direction": self._direction,
                "extreme": None if self._extreme is None else format(self._extreme, "f"),
                "observations": len(self._highs),
            }
        )
        return result
