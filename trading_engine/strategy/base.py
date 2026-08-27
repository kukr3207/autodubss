"""Strategy protocol and lifecycle helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from ..errors import ValidationError
from ..validation import clean_text
from ..domain.portfolio import PortfolioSnapshot
from ..market.models import Bar
from .signals import Signal


class Strategy(ABC):
    def __init__(self, strategy_id: str) -> None:
        self.strategy_id = clean_text(strategy_id, "strategy_id", max_length=80)
        self._started = False

    @property
    def started(self) -> bool:
        return self._started

    def start(self) -> None:
        if self._started:
            raise ValidationError("strategy is already started")
        self._started = True
        self.on_start()

    def stop(self) -> None:
        if not self._started:
            return
        self.on_stop()
        self._started = False

    def evaluate(self, bar: Bar, portfolio: PortfolioSnapshot) -> Optional[Signal]:
        if not self._started:
            raise ValidationError("strategy must be started before evaluation")
        if not isinstance(bar, Bar):
            raise ValidationError("bar must be a Bar")
        if not isinstance(portfolio, PortfolioSnapshot):
            raise ValidationError("portfolio must be a PortfolioSnapshot")
        return self.on_bar(bar, portfolio)

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    @abstractmethod
    def on_bar(self, bar: Bar, portfolio: PortfolioSnapshot) -> Optional[Signal]:
        pass

    def state(self) -> Dict[str, Any]:
        return {"strategyId": self.strategy_id, "started": self.started}
