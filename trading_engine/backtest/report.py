"""Portable backtest reports with stable JSON serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from ..errors import ValidationError
from ..validation import aware_time, clean_text
from ..domain.orders import Order
from ..domain.portfolio import PortfolioSnapshot
from ..strategy.signals import Signal
from .equity import EquityCurve
from .metrics import PerformanceMetrics


@dataclass(frozen=True)
class BacktestReport:
    name: str
    started_at: datetime
    finished_at: datetime
    metrics: PerformanceMetrics
    equity_curve: EquityCurve
    final_portfolio: PortfolioSnapshot
    signals: Tuple[Signal, ...]
    orders: Tuple[Order, ...]
    rejected_signals: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", clean_text(self.name, "name", max_length=120))
        object.__setattr__(self, "started_at", aware_time(self.started_at, "started_at"))
        object.__setattr__(self, "finished_at", aware_time(self.finished_at, "finished_at"))
        if self.finished_at < self.started_at:
            raise ValidationError("finished_at cannot predate started_at")
        if not isinstance(self.metrics, PerformanceMetrics):
            raise ValidationError("metrics must be PerformanceMetrics")
        if not isinstance(self.equity_curve, EquityCurve):
            raise ValidationError("equity_curve must be EquityCurve")
        if not isinstance(self.final_portfolio, PortfolioSnapshot):
            raise ValidationError("final_portfolio must be PortfolioSnapshot")
        object.__setattr__(self, "signals", tuple(self.signals))
        object.__setattr__(self, "orders", tuple(self.orders))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "startedAt": self.started_at.isoformat(),
            "finishedAt": self.finished_at.isoformat(),
            "metrics": self.metrics.as_dict(),
            "equityCurve": [point.as_dict() for point in self.equity_curve.points],
            "finalPortfolio": self.final_portfolio.as_dict(),
            "signals": [signal.as_dict() for signal in self.signals],
            "orders": [order.as_dict() for order in self.orders],
            "rejectedSignals": self.rejected_signals,
        }

    def to_json(self, *, indent: Optional[int] = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent, sort_keys=True)
