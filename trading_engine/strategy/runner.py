"""Connect strategy signals to orders without embedding policy in strategies."""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..errors import TradingEngineError, ValidationError
from ..domain.identifiers import AccountId, ClientOrderId
from ..domain.orders import Order, OrderRequest, OrderType, Side
from ..domain.portfolio import Portfolio
from ..execution.service import ExecutionService
from ..market.models import Bar, Quote
from .base import Strategy
from .signals import Signal, SignalAction
from .sizing import PositionSizer


class StrategyRunner:
    def __init__(
        self,
        strategy: Strategy,
        sizer: PositionSizer,
        execution: ExecutionService,
        portfolio: Portfolio,
    ) -> None:
        if not isinstance(strategy, Strategy):
            raise ValidationError("strategy must be Strategy")
        if not isinstance(sizer, PositionSizer):
            raise ValidationError("sizer must implement PositionSizer")
        if not isinstance(execution, ExecutionService):
            raise ValidationError("execution must be ExecutionService")
        if portfolio is not execution.portfolio:
            raise ValidationError("runner and execution must share a portfolio")
        self.strategy = strategy
        self.sizer = sizer
        self.execution = execution
        self.portfolio = portfolio
        self._signals: List[Signal] = []
        self._orders: List[Order] = []
        self._errors: List[TradingEngineError] = []

    def start(self) -> None:
        self.strategy.start()

    def stop(self) -> None:
        self.strategy.stop()

    def on_bar(self, bar: Bar, quote: Quote) -> Optional[Order]:
        if bar.instrument.key != quote.instrument.key:
            raise ValidationError("bar and quote must describe the same instrument")
        signal = self.strategy.evaluate(bar, self.portfolio.snapshot())
        if signal is None:
            return None
        self._signals.append(signal)
        request = self._to_request(signal)
        if request is None:
            return None
        try:
            order = self.execution.submit(request, quote)
        except TradingEngineError as exc:
            self._errors.append(exc)
            return None
        self._orders.append(order)
        return order

    def _to_request(self, signal: Signal) -> Optional[OrderRequest]:
        snapshot = self.portfolio.snapshot()
        current = next(
            (
                position.quantity
                for position in snapshot.positions
                if position.instrument.key == signal.instrument.key
            ),
            0,
        )
        if signal.action is SignalAction.EXIT:
            if current == 0:
                return None
            side = Side.SELL if current > 0 else Side.BUY
            quantity = abs(current)
        else:
            quantity = self.sizer.quantity(signal, snapshot)
            if quantity <= 0 or signal.action is SignalAction.HOLD:
                return None
            side = Side.BUY if signal.action is SignalAction.BUY else Side.SELL
        return OrderRequest(
            account_id=self.portfolio.account_id,
            client_order_id=ClientOrderId.new(),
            instrument=signal.instrument,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            strategy_id=signal.strategy_id,
        )

    @property
    def signals(self) -> Tuple[Signal, ...]:
        return tuple(self._signals)

    @property
    def orders(self) -> Tuple[Order, ...]:
        return tuple(self._orders)

    @property
    def errors(self) -> Tuple[TradingEngineError, ...]:
        return tuple(self._errors)
