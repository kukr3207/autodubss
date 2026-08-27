"""Deterministic event loop for historical strategy evaluation."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Optional

from ..clock import FixedClock
from ..errors import ValidationError
from ..domain.identifiers import AccountId
from ..domain.money import Money
from ..domain.portfolio import Portfolio
from ..execution.repository import OrderRepository
from ..execution.service import ExecutionService
from ..execution.simulated import SimulatedBroker
from ..risk.engine import RiskEngine
from ..risk.models import RiskLimits
from ..strategy.base import Strategy
from ..strategy.runner import StrategyRunner
from ..strategy.sizing import PositionSizer
from .equity import EquityCurve, EquityPoint
from .feed import HistoricalFeed
from .metrics import performance_metrics
from .report import BacktestReport


class BacktestRunner:
    def __init__(
        self,
        name: str,
        strategy: Strategy,
        sizer: PositionSizer,
        *,
        initial_cash: Decimal = Decimal("1000000"),
        currency: str = "INR",
        risk_limits: Optional[RiskLimits] = None,
    ) -> None:
        if not isinstance(strategy, Strategy):
            raise ValidationError("strategy must be Strategy")
        if not isinstance(sizer, PositionSizer):
            raise ValidationError("sizer must implement PositionSizer")
        self.name = str(name).strip()
        if not self.name:
            raise ValidationError("name cannot be blank")
        self.strategy = strategy
        self.sizer = sizer
        self.initial_cash = Money(initial_cash, currency)
        if self.initial_cash.amount <= 0:
            raise ValidationError("initial_cash must be positive")
        self.risk_limits = risk_limits or RiskLimits(
            max_order_quantity=100000,
            max_order_notional=Decimal("1000000000"),
            max_position_quantity=1000000,
            max_gross_exposure=Decimal("1000000000"),
            max_net_exposure=Decimal("1000000000"),
            max_daily_loss=Decimal("1000000000"),
            max_open_orders=1000,
            max_quote_age_seconds=86400,
            price_band_percent=Decimal("100"),
        )

    def run(self, feed: HistoricalFeed) -> BacktestReport:
        if not isinstance(feed, HistoricalFeed):
            raise ValidationError("feed must be HistoricalFeed")
        if len(feed) == 0:
            raise ValidationError("feed cannot be empty")
        clock = FixedClock(feed.start)
        portfolio = Portfolio(AccountId.new(), [self.initial_cash])
        broker = SimulatedBroker(clock=clock)
        repository = OrderRepository()
        execution = ExecutionService(
            broker,
            repository,
            portfolio,
            RiskEngine(self.risk_limits),
            clock=clock,
        )
        strategy_runner = StrategyRunner(
            self.strategy,
            self.sizer,
            execution,
            portfolio,
        )
        curve = EquityCurve()
        strategy_runner.start()
        try:
            for frame in feed:
                clock.set(frame.time)
                broker.update_quote(frame.quote)
                self._mark_existing(portfolio, frame)
                strategy_runner.on_bar(frame.bar, frame.quote)
                self._mark_existing(portfolio, frame)
                snapshot = portfolio.snapshot()
                cash = snapshot.cash_balance(self.initial_cash.currency).amount
                market_value = sum(
                    (
                        position.market_value.amount
                        for position in snapshot.positions
                        if position.instrument.contract.price_currency == self.initial_cash.currency
                    ),
                    Decimal("0"),
                )
                point_time = frame.time
                if curve.points and point_time <= curve.points[-1].observed_at:
                    point_time = curve.points[-1].observed_at + timedelta(microseconds=1)
                curve.append(EquityPoint(point_time, cash + market_value, cash, market_value))
        finally:
            strategy_runner.stop()
        rejected = len(strategy_runner.errors)
        return BacktestReport(
            name=self.name,
            started_at=feed.start,
            finished_at=feed.end,
            metrics=performance_metrics(curve),
            equity_curve=curve,
            final_portfolio=portfolio.snapshot(),
            signals=strategy_runner.signals,
            orders=strategy_runner.orders,
            rejected_signals=rejected,
        )

    @staticmethod
    def _mark_existing(portfolio: Portfolio, frame) -> None:
        snapshot = portfolio.snapshot()
        for position in snapshot.positions:
            if position.instrument.key == frame.bar.instrument.key:
                portfolio.mark(position.instrument.key, frame.bar.close, frame.time)
