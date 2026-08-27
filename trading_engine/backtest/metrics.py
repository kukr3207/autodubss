"""Performance statistics with defined behavior for small samples."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from typing import Any, Dict, Iterable, Sequence, Tuple

from ..errors import ValidationError
from ..validation import decimal_value, integer_value
from .equity import EquityCurve


def mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / len(values)


def sample_standard_deviation(values: Sequence[Decimal]) -> Decimal:
    if len(values) < 2:
        return Decimal("0")
    average = mean(values)
    variance = sum((value - average) ** 2 for value in values) / Decimal(len(values) - 1)
    return Decimal(str(sqrt(float(variance))))


def downside_deviation(values: Sequence[Decimal], target: Decimal = Decimal("0")) -> Decimal:
    downside = [min(Decimal("0"), value - target) for value in values]
    if not downside:
        return Decimal("0")
    variance = sum(value ** 2 for value in downside) / len(downside)
    return Decimal(str(sqrt(float(variance))))


@dataclass(frozen=True)
class TradeStatistics:
    count: int
    winners: int
    losers: int
    gross_profit: Decimal
    gross_loss: Decimal
    net_profit: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    average_trade: Decimal

    def as_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "winners": self.winners,
            "losers": self.losers,
            "grossProfit": format(self.gross_profit, "f"),
            "grossLoss": format(self.gross_loss, "f"),
            "netProfit": format(self.net_profit, "f"),
            "winRate": format(self.win_rate, "f"),
            "profitFactor": format(self.profit_factor, "f"),
            "averageTrade": format(self.average_trade, "f"),
        }


def trade_statistics(profits: Iterable[Decimal]) -> TradeStatistics:
    checked = tuple(decimal_value(value, "profit") for value in profits)
    winners = [value for value in checked if value > 0]
    losers = [value for value in checked if value < 0]
    gross_profit = sum(winners, Decimal("0"))
    gross_loss = -sum(losers, Decimal("0"))
    count = len(checked)
    if gross_loss == 0:
        profit_factor = gross_profit if gross_profit else Decimal("0")
    else:
        profit_factor = gross_profit / gross_loss
    return TradeStatistics(
        count=count,
        winners=len(winners),
        losers=len(losers),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        net_profit=sum(checked, Decimal("0")),
        win_rate=Decimal(len(winners)) / count if count else Decimal("0"),
        profit_factor=profit_factor,
        average_trade=mean(checked),
    )


@dataclass(frozen=True)
class PerformanceMetrics:
    total_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown: Decimal
    observations: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "totalReturn": format(self.total_return, "f"),
            "annualizedReturn": format(self.annualized_return, "f"),
            "volatility": format(self.volatility, "f"),
            "sharpeRatio": format(self.sharpe_ratio, "f"),
            "sortinoRatio": format(self.sortino_ratio, "f"),
            "maxDrawdown": format(self.max_drawdown, "f"),
            "observations": self.observations,
        }


def performance_metrics(
    curve: EquityCurve,
    *,
    periods_per_year: int = 252,
    risk_free_rate: Decimal = Decimal("0"),
) -> PerformanceMetrics:
    if not isinstance(curve, EquityCurve):
        raise ValidationError("curve must be EquityCurve")
    periods = integer_value(periods_per_year, "periods_per_year", minimum=1)
    risk_free = decimal_value(risk_free_rate, "risk_free_rate")
    changes = curve.returns()
    periodic_rf = risk_free / periods
    excess = tuple(value - periodic_rf for value in changes)
    deviation = sample_standard_deviation(excess)
    downside = downside_deviation(excess)
    root = Decimal(str(sqrt(periods)))
    sharpe = mean(excess) / deviation * root if deviation else Decimal("0")
    sortino = mean(excess) / downside * root if downside else Decimal("0")
    if changes and curve.initial_equity > 0 and curve.final_equity > 0:
        years = Decimal(len(changes)) / periods
        annualized = Decimal(str(float(curve.final_equity / curve.initial_equity) ** (1 / float(years)))) - 1
    else:
        annualized = Decimal("0")
    return PerformanceMetrics(
        total_return=curve.total_return,
        annualized_return=annualized,
        volatility=sample_standard_deviation(changes) * root,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=curve.max_drawdown,
        observations=len(curve.points),
    )
