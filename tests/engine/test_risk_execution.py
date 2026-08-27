from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from trading_engine.clock import FixedClock
from trading_engine.domain import (
    AccountId,
    AssetClass,
    ClientOrderId,
    Instrument,
    Money,
    OrderRequest,
    OrderStatus,
    OrderType,
    Portfolio,
    Side,
    TimeInForce,
)
from trading_engine.errors import BrokerError, DuplicateRequestError, RiskRejectedError
from trading_engine.execution import (
    ExecutionService,
    FixedBasisPointSlippage,
    OrderRepository,
    PercentageCommission,
    SimulatedBroker,
)
from trading_engine.market import Quote
from trading_engine.risk import CircuitBreaker, CircuitState, RiskEngine, RiskLimits


NOW = datetime(2025, 1, 2, 9, 30, tzinfo=timezone.utc)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.clock = FixedClock(NOW)
        self.instrument = Instrument("ACME", "NSE", AssetClass.EQUITY)
        self.account = AccountId("acct-demo")
        self.portfolio = Portfolio(self.account, [Money(Decimal("100000"))])
        self.quote = Quote(self.instrument, 99, 101, 100, 100, NOW, "fixture")

    def request(self, **changes):
        values = dict(
            account_id=self.account,
            client_order_id=ClientOrderId.new(),
            instrument=self.instrument,
            side=Side.BUY,
            quantity=10,
        )
        values.update(changes)
        return OrderRequest(**values)


class RiskTests(Fixture):
    def test_default_limits_allow_small_fresh_order(self):
        decision = RiskEngine(RiskLimits()).evaluate(
            self.request(), self.portfolio.snapshot(), self.quote, NOW
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.violations, ())

    def test_engine_reports_multiple_policy_failures(self):
        limits = RiskLimits(
            max_order_quantity=5,
            max_order_notional=100,
            max_position_quantity=5,
            max_gross_exposure=100,
            max_net_exposure=100,
        )
        decision = RiskEngine(limits).evaluate(
            self.request(quantity=10), self.portfolio.snapshot(), self.quote, NOW
        )
        self.assertFalse(decision.allowed)
        rules = {item.rule for item in decision.violations}
        self.assertTrue({"max_order_quantity", "max_order_notional", "max_position_quantity"} <= rules)

    def test_stale_quote_is_rejected(self):
        with self.assertRaises(RiskRejectedError):
            RiskEngine(RiskLimits(max_quote_age_seconds=5)).require_allowed(
                self.request(),
                self.portfolio.snapshot(),
                self.quote,
                NOW + timedelta(seconds=6),
            )

    def test_price_band_applies_to_limit_orders(self):
        request = self.request(order_type=OrderType.LIMIT, limit_price=120)
        decision = RiskEngine(RiskLimits(price_band_percent=5)).evaluate(
            request, self.portfolio.snapshot(), self.quote, NOW
        )
        self.assertIn("price_band", {item.rule for item in decision.violations})

    def test_circuit_breaker_recovers_through_half_open_trial(self):
        circuit = CircuitBreaker(2, timedelta(seconds=10), clock=self.clock)
        circuit.record_failure("first")
        circuit.record_failure("second")
        self.assertEqual(circuit.snapshot().state, CircuitState.OPEN)
        self.assertFalse(circuit.allow())
        self.clock.advance(timedelta(seconds=10))
        self.assertTrue(circuit.allow())
        self.assertFalse(circuit.allow())
        circuit.record_success()
        self.assertEqual(circuit.snapshot().state, CircuitState.CLOSED)


class SimulatedBrokerTests(Fixture):
    def test_market_order_fills_at_quote(self):
        broker = SimulatedBroker(clock=self.clock)
        broker.update_quote(self.quote)
        response = broker.submit(__import__("trading_engine").OrderId.new(), self.request())
        self.assertEqual(response.state.value, "filled")
        self.assertEqual(response.fills[0].price, Decimal("101"))

    def test_limit_order_waits_until_executable_quote(self):
        broker = SimulatedBroker(clock=self.clock)
        broker.update_quote(self.quote)
        request = self.request(order_type=OrderType.LIMIT, limit_price=100)
        response = broker.submit(__import__("trading_engine").OrderId.new(), request)
        self.assertEqual(response.state.value, "accepted")
        self.clock.advance(timedelta(seconds=1))
        broker.update_quote(Quote(self.instrument, 98, 100, 100, 100, self.clock.now(), "fixture"))
        self.assertEqual(broker.get(response.broker_order_id).state.value, "filled")

    def test_ioc_without_liquidity_is_cancelled(self):
        broker = SimulatedBroker(clock=self.clock)
        broker.update_quote(Quote(self.instrument, 99, 101, 0, 0, NOW, "fixture"))
        response = broker.submit(
            __import__("trading_engine").OrderId.new(),
            self.request(time_in_force=TimeInForce.IOC),
        )
        self.assertEqual(response.state.value, "cancelled")

    def test_partial_fill_completes_on_later_quote(self):
        broker = SimulatedBroker(clock=self.clock)
        broker.update_quote(Quote(self.instrument, 99, 101, 4, 4, NOW, "fixture"))
        response = broker.submit(__import__("trading_engine").OrderId.new(), self.request(quantity=10))
        self.assertEqual(response.state.value, "partially_filled")
        self.assertEqual(response.filled_quantity, 4)
        self.clock.advance(timedelta(seconds=1))
        broker.update_quote(
            Quote(self.instrument, 99, 101, 10, 10, self.clock.now(), "fixture")
        )
        completed = broker.get(response.broker_order_id)
        self.assertEqual(completed.state.value, "filled")
        self.assertEqual(completed.filled_quantity, 10)
        self.assertEqual(len(completed.fills), 2)

    def test_client_order_ids_are_idempotency_keys(self):
        broker = SimulatedBroker(clock=self.clock)
        request = self.request()
        broker.submit(__import__("trading_engine").OrderId.new(), request)
        with self.assertRaises(DuplicateRequestError):
            broker.submit(__import__("trading_engine").OrderId.new(), request)

    def test_commission_and_slippage_models_affect_fill(self):
        broker = SimulatedBroker(
            clock=self.clock,
            commission=PercentageCommission(Decimal("1")),
            slippage=FixedBasisPointSlippage(Decimal("100")),
        )
        broker.update_quote(self.quote)
        response = broker.submit(__import__("trading_engine").OrderId.new(), self.request())
        fill = response.fills[0]
        self.assertEqual(fill.price, Decimal("102.01"))
        self.assertEqual(fill.commission, Decimal("10.201"))


class ExecutionServiceTests(Fixture):
    def service(self):
        broker = SimulatedBroker(clock=self.clock)
        broker.update_quote(self.quote)
        return ExecutionService(
            broker,
            OrderRepository(),
            self.portfolio,
            RiskEngine(RiskLimits()),
            clock=self.clock,
        )

    def test_submission_updates_order_portfolio_and_cash(self):
        service = self.service()
        order = service.submit(self.request(), self.quote)
        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertEqual(self.portfolio.get_position(self.instrument.key).quantity, 10)
        self.assertEqual(self.portfolio.snapshot().cash_balance("INR").amount, Decimal("98990"))

    def test_risk_rejection_does_not_add_order(self):
        broker = SimulatedBroker(clock=self.clock)
        service = ExecutionService(
            broker,
            OrderRepository(),
            self.portfolio,
            RiskEngine(RiskLimits(max_order_quantity=1)),
            clock=self.clock,
        )
        with self.assertRaises(RiskRejectedError):
            service.submit(self.request(quantity=10), self.quote)
        self.assertEqual(service.repository.count(), 0)


if __name__ == "__main__":
    unittest.main()
