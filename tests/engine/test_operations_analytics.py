from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from trading_engine.analytics import (
    DecimalSeries,
    Observation,
    StressScenario,
    correlation_matrix,
    historical_tail_risk,
    stress_portfolio,
)
from trading_engine.audit import DomainEvent, EventStore, build_chain, export_jsonl, read_jsonl, verify_chain
from trading_engine.clock import FixedClock
from trading_engine.config import load_settings
from trading_engine.domain import (
    AccountId,
    AssetClass,
    EventId,
    Fill,
    Instrument,
    Money,
    OrderId,
    Portfolio,
    Side,
    TradeId,
)
from trading_engine.errors import BrokerError, ConfigurationError, DuplicateRequestError, ValidationError
from trading_engine.execution import BrokerRetryExecutor, BrokerRetryPolicy
from trading_engine.market import ProviderNormalizer
from trading_engine.scheduling import Job, JobScheduler, RetryPolicy, TradingCalendar
from trading_engine.serialization import decode_instrument, decode_quote, dumps


NOW = datetime(2025, 1, 2, 9, 30, tzinfo=timezone.utc)


class AuditTests(unittest.TestCase):
    def event(self, index):
        return DomainEvent(
            EventId("evt-%d" % index),
            "order.updated",
            "order",
            "order-1",
            NOW + timedelta(seconds=index),
            {"status": "state-%d" % index},
        )

    def test_store_versions_and_hash_chain(self):
        store = EventStore()
        store.append(self.event(1), expected_version=0)
        store.append(self.event(2), expected_version=1)
        self.assertEqual(store.version("order", "order-1"), 2)
        chain = build_chain(store.stream())
        self.assertTrue(verify_chain(chain))
        self.assertNotEqual(chain[0].event_hash, chain[1].event_hash)

    def test_version_conflict_keeps_store_unchanged(self):
        store = EventStore()
        store.append(self.event(1))
        with self.assertRaises(ValidationError):
            store.append(self.event(2), expected_version=0)
        self.assertEqual(len(store), 1)

    def test_json_lines_export_is_readable(self):
        store = EventStore()
        store.append(self.event(1))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            self.assertEqual(export_jsonl(store, path), 1)
            records = read_jsonl(path)
        self.assertEqual(records[0]["record"]["aggregateVersion"], 1)


class SchedulingTests(unittest.TestCase):
    def test_calendar_skips_weekends_and_holidays(self):
        calendar = TradingCalendar("NSE", holidays=[date(2025, 1, 6)])
        self.assertEqual(calendar.next_trading_day(date(2025, 1, 3)), date(2025, 1, 7))
        session = calendar.session(date(2025, 1, 7))
        self.assertEqual(session.duration, timedelta(hours=6, minutes=15))

    def test_next_open_handles_before_and_after_session(self):
        calendar = TradingCalendar(
            "UTC",
            opens_at=time(9),
            closes_at=time(17),
            utc_offset=timedelta(0),
        )
        before = datetime(2025, 1, 2, 8, tzinfo=timezone.utc)
        after = datetime(2025, 1, 2, 18, tzinfo=timezone.utc)
        self.assertEqual(calendar.next_open(before).hour, 9)
        self.assertEqual(calendar.next_open(after).date(), date(2025, 1, 3))

    def test_scheduler_retries_failed_job(self):
        clock = FixedClock(NOW)
        scheduler = JobScheduler(clock=clock)
        calls = []

        def handler(payload):
            calls.append(payload["value"])
            if len(calls) == 1:
                raise RuntimeError("temporary")
            return "done"

        scheduler.schedule(
            Job("job-1", "retry", NOW, handler, {"value": 3}, RetryPolicy(2, timedelta(seconds=5)))
        )
        self.assertEqual(scheduler.run_due()[0].status.value, "failed")
        clock.advance(timedelta(seconds=5))
        self.assertEqual(scheduler.run_due()[0].status.value, "succeeded")
        self.assertEqual(calls, [3, 3])

    def test_scheduler_rejects_duplicate_job_id(self):
        scheduler = JobScheduler(clock=FixedClock(NOW))
        job = Job("job-1", "one", NOW, lambda payload: None, {})
        scheduler.schedule(job)
        with self.assertRaises(DuplicateRequestError):
            scheduler.schedule(job)


class AnalyticsAndCodecTests(unittest.TestCase):
    def series(self, name, values):
        return DecimalSeries(
            name,
            [Observation(NOW + timedelta(days=i), Decimal(value)) for i, value in enumerate(values)],
        )

    def test_series_returns_rolling_mean_and_alignment(self):
        series = self.series("prices", [100, 110, 121])
        self.assertEqual(series.percentage_returns().values, (Decimal("0.1"), Decimal("0.1")))
        self.assertEqual(series.rolling_mean(2).values[-1], Decimal("115.5"))

    def test_correlation_matrix_is_symmetric(self):
        left = self.series("left", [1, 2, 3])
        right = self.series("right", [2, 4, 6])
        matrix = correlation_matrix([left, right])
        self.assertAlmostEqual(float(matrix.get("left", "right")), 1.0)
        self.assertEqual(matrix.get("left", "right"), matrix.get("right", "left"))

    def test_configuration_requires_credentials_only_for_live_mode(self):
        settings = load_settings({"TRADING_PAPER": "true"})
        self.assertTrue(settings.broker.paper_trading)
        with self.assertRaises(ConfigurationError):
            load_settings({"TRADING_PAPER": "false"})

    def test_json_codec_round_trips_quote(self):
        raw = {
            "symbol": "ACME",
            "exchange": "NSE",
            "assetClass": "equity",
            "contract": {"lotSize": 1, "tickSize": "0.05", "multiplier": "1", "priceCurrency": "INR"},
        }
        instrument = decode_instrument(raw)
        quote = decode_quote(
            {
                "instrument": instrument.as_dict(),
                "bid": "99",
                "ask": "101",
                "bidSize": 1,
                "askSize": 2,
                "observedAt": NOW.isoformat(),
                "provider": "fixture",
            }
        )
        self.assertIn('"provider":"fixture"', dumps(quote))

    def test_historical_tail_risk_uses_worst_returns(self):
        result = historical_tail_risk(
            [Decimal("0.02"), Decimal("-0.10"), Decimal("-0.05"), Decimal("0.01")],
            Decimal("1000"),
            Decimal("0.75"),
        )
        self.assertEqual(result.value_at_risk, Decimal("100.00"))
        self.assertEqual(result.expected_shortfall, Decimal("100.00"))

    def test_stress_scenario_marks_open_positions(self):
        instrument = Instrument("ACME", "NSE", AssetClass.EQUITY)
        portfolio = Portfolio(AccountId("acct-demo"), [Money(10000)])
        portfolio.apply_fill(
            Fill(
                TradeId.new(),
                OrderId.new(),
                instrument,
                Side.BUY,
                10,
                Decimal("100"),
                NOW,
            )
        )
        result = stress_portfolio(
            portfolio.snapshot(),
            StressScenario("market fall", {instrument.key: Decimal("-0.2")}),
        )
        self.assertEqual(result.profit_loss, Decimal("-200.0"))

    def test_provider_normalizer_sorts_and_deduplicates(self):
        normalizer = ProviderNormalizer(
            "vendor",
            Instrument("ACME", "NSE", AssetClass.EQUITY),
        )
        early = {
            "bid": 99,
            "ask": 101,
            "bid_size": 1,
            "ask_size": 2,
            "timestamp": NOW.isoformat(),
        }
        late = dict(early, timestamp=(NOW + timedelta(seconds=1)).isoformat())
        quotes = normalizer.quotes([late, early, early])
        self.assertEqual(len(quotes), 2)
        self.assertEqual(quotes[0].observed_at, NOW)

    def test_broker_retry_only_retries_transient_errors(self):
        attempts = []

        def operation():
            attempts.append(1)
            if len(attempts) < 3:
                raise BrokerError("temporary", retryable=True)
            return "ok"

        waits = []
        executor = BrokerRetryExecutor(
            BrokerRetryPolicy(3, timedelta(seconds=1)),
            wait=waits.append,
        )
        self.assertEqual(executor.run(operation), "ok")
        self.assertEqual(len(waits), 2)


if __name__ == "__main__":
    unittest.main()
