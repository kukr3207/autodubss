from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import unittest

from trading_engine.backtest import (
    BacktestRunner,
    EquityCurve,
    EquityPoint,
    HistoricalFeed,
    HistoricalFrame,
    performance_metrics,
    trade_statistics,
)
from trading_engine.domain import AssetClass, Instrument
from trading_engine.errors import ValidationError
from trading_engine.market import Bar, Quote
from trading_engine.strategy import (
    BreakoutStrategy,
    FixedQuantitySizer,
    MovingAverageCrossStrategy,
    SignalAction,
)


START = datetime(2025, 1, 1, tzinfo=timezone.utc)
INSTRUMENT = Instrument("ACME", "NSE", AssetClass.EQUITY)


def bars(prices):
    result = []
    for index, raw in enumerate(prices):
        price = Decimal(str(raw))
        opened = START + timedelta(days=index)
        result.append(
            Bar(
                INSTRUMENT,
                timedelta(days=1),
                opened,
                opened + timedelta(days=1),
                price,
                price + 1,
                price - 1,
                price,
                1000,
                20,
                "fixture",
            )
        )
    return tuple(result)


class StrategyTests(unittest.TestCase):
    def test_moving_average_emits_only_on_regime_transition(self):
        strategy = MovingAverageCrossStrategy("cross", 2, 3)
        strategy.start()
        from trading_engine.domain import AccountId, Portfolio

        portfolio = Portfolio(AccountId("acct-demo")).snapshot()
        signals = [strategy.evaluate(bar, portfolio) for bar in bars([5, 4, 3, 4, 6, 5, 2])]
        actions = [signal.action for signal in signals if signal]
        self.assertEqual(actions, [SignalAction.BUY, SignalAction.SELL])

    def test_breakout_enters_and_trailing_stop_exits(self):
        strategy = BreakoutStrategy("break", lookback=3, trailing_percent=5)
        strategy.start()
        from trading_engine.domain import AccountId, Portfolio

        snapshot = Portfolio(AccountId("acct-demo")).snapshot()
        signals = [strategy.evaluate(bar, snapshot) for bar in bars([100, 101, 102, 105, 110, 103])]
        actions = [signal.action for signal in signals if signal]
        self.assertEqual(actions, [SignalAction.BUY, SignalAction.EXIT])

    def test_strategy_must_be_started(self):
        strategy = MovingAverageCrossStrategy("cross", 2, 3)
        from trading_engine.domain import AccountId, Portfolio

        with self.assertRaises(ValidationError):
            strategy.evaluate(bars([1])[0], Portfolio(AccountId("acct-demo")).snapshot())


class BacktestTests(unittest.TestCase):
    def test_feed_from_bars_preserves_order_and_spread(self):
        feed = HistoricalFeed.from_bars(bars([100, 101, 102]))
        self.assertEqual(len(feed), 3)
        self.assertEqual(feed.instruments, (INSTRUMENT.key,))
        self.assertGreater(next(iter(feed)).quote.ask, Decimal("100"))

    def test_feed_rejects_duplicate_frames(self):
        bar = bars([100])[0]
        quote = Quote(INSTRUMENT, 99, 101, 1, 1, bar.closed_at, "fixture")
        frame = HistoricalFrame(bar, quote)
        with self.assertRaises(ValidationError):
            HistoricalFeed([frame, frame])

    def test_end_to_end_backtest_returns_portable_report(self):
        feed = HistoricalFeed.from_bars(bars([100, 99, 98, 97, 99, 102, 105, 103, 100, 97]))
        report = BacktestRunner(
            "moving average",
            MovingAverageCrossStrategy("cross", 2, 3),
            FixedQuantitySizer(2),
        ).run(feed)
        self.assertEqual(len(report.equity_curve.points), len(feed))
        self.assertGreaterEqual(len(report.signals), 1)
        payload = json.loads(report.to_json())
        self.assertEqual(payload["name"], "moving average")
        self.assertIn("maxDrawdown", payload["metrics"])

    def test_equity_metrics_measure_drawdown(self):
        curve = EquityCurve(
            [
                EquityPoint(START, 100, 100, 0),
                EquityPoint(START + timedelta(days=1), 120, 120, 0),
                EquityPoint(START + timedelta(days=2), 90, 90, 0),
            ]
        )
        self.assertEqual(curve.max_drawdown, Decimal("0.25"))
        self.assertEqual(performance_metrics(curve).observations, 3)

    def test_trade_statistics_handle_wins_losses_and_flat_trades(self):
        stats = trade_statistics([Decimal("10"), Decimal("-5"), Decimal("0")])
        self.assertEqual(stats.count, 3)
        self.assertEqual(stats.win_rate, Decimal("1") / 3)
        self.assertEqual(stats.profit_factor, Decimal("2"))


if __name__ == "__main__":
    unittest.main()
