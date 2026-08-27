from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from trading_engine.domain import (
    AccountId,
    AssetClass,
    ClientOrderId,
    ContractSpec,
    Fill,
    Instrument,
    Money,
    Order,
    OrderId,
    OrderRequest,
    OrderStatus,
    OrderType,
    Portfolio,
    Position,
    Side,
    TradeId,
)
from trading_engine.errors import MarketDataError, OrderStateError, ValidationError
from trading_engine.market import (
    Bar,
    BarAggregator,
    BookSide,
    MarketDataStore,
    OrderBook,
    PriceLevel,
    Quote,
    TradeTick,
    average_true_range,
    exponential_moving_average,
    simple_moving_average,
)


NOW = datetime(2025, 1, 2, 9, 30, tzinfo=timezone.utc)


def instrument(lot_size=1):
    return Instrument(
        "ACME",
        "NSE",
        AssetClass.EQUITY,
        ContractSpec(lot_size=lot_size, tick_size=Decimal("0.05")),
    )


class MoneyAndInstrumentTests(unittest.TestCase):
    def test_money_arithmetic_preserves_currency(self):
        amount = Money(Decimal("10.25"), "inr")
        self.assertEqual((amount + Money(Decimal("2.75"))).amount, Decimal("13.00"))
        self.assertEqual((amount * 2).amount, Decimal("20.50"))
        self.assertEqual(amount.currency, "INR")

    def test_money_rejects_cross_currency_arithmetic(self):
        with self.assertRaises(ValidationError):
            Money(1, "INR") + Money(1, "USD")

    def test_contract_rounds_to_nearest_tick_and_checks_lots(self):
        contract = ContractSpec(lot_size=25, tick_size="0.05")
        self.assertEqual(contract.round_price("101.027"), Decimal("101.05"))
        self.assertEqual(contract.validate_quantity(50), 50)
        with self.assertRaises(ValidationError):
            contract.validate_quantity(26)

    def test_instrument_notional_uses_multiplier(self):
        value = Instrument(
            "BANKNIFTY",
            "NFO",
            AssetClass.FUTURE,
            ContractSpec(lot_size=25, multiplier=25),
        )
        self.assertEqual(value.notional("100", 25), Decimal("62500"))


class OrderLifecycleTests(unittest.TestCase):
    def request(self, **changes):
        values = dict(
            account_id=AccountId("acct-demo"),
            client_order_id=ClientOrderId("client-demo"),
            instrument=instrument(),
            side=Side.BUY,
            quantity=10,
        )
        values.update(changes)
        return OrderRequest(**values)

    def test_price_fields_follow_order_type(self):
        limit = self.request(order_type=OrderType.LIMIT, limit_price="100.03")
        self.assertEqual(limit.limit_price, Decimal("100.05"))
        with self.assertRaises(ValidationError):
            self.request(order_type=OrderType.MARKET, limit_price=100)
        with self.assertRaises(ValidationError):
            self.request(order_type=OrderType.STOP)

    def test_order_accepts_partial_and_full_fills(self):
        pending = Order(OrderId.new(), self.request(), OrderStatus.PENDING, NOW, NOW)
        accepted = pending.transition(OrderStatus.ACCEPTED, NOW + timedelta(seconds=1))
        partial = accepted.apply_fill(4, "101", NOW + timedelta(seconds=2))
        self.assertEqual(partial.status, OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(partial.remaining_quantity, 6)
        filled = partial.apply_fill(6, "103", NOW + timedelta(seconds=3))
        self.assertEqual(filled.status, OrderStatus.FILLED)
        self.assertEqual(filled.average_fill_price, Decimal("102.2"))

    def test_terminal_order_cannot_transition(self):
        pending = Order(OrderId.new(), self.request(), OrderStatus.PENDING, NOW, NOW)
        cancelled = pending.transition(OrderStatus.CANCELLED, NOW)
        with self.assertRaises(OrderStateError):
            cancelled.transition(OrderStatus.ACCEPTED, NOW)


class PositionAndPortfolioTests(unittest.TestCase):
    def fill(self, side, quantity, price, when=NOW, commission="0"):
        return Fill(
            TradeId.new(),
            OrderId.new(),
            instrument(),
            side,
            quantity,
            Decimal(price),
            when,
            Money(Decimal(commission)),
        )

    def test_position_tracks_weighted_cost_and_realized_profit(self):
        position = Position(instrument())
        position = position.apply(self.fill(Side.BUY, 10, "100"))
        position = position.apply(
            self.fill(Side.BUY, 10, "110", NOW + timedelta(seconds=1))
        )
        self.assertEqual(position.average_price, Decimal("105"))
        position = position.apply(
            self.fill(Side.SELL, 5, "120", NOW + timedelta(seconds=2), "1")
        )
        self.assertEqual(position.quantity, 15)
        self.assertEqual(position.realized_pnl, Decimal("74"))

    def test_position_flips_direction_at_new_fill_price(self):
        position = Position(instrument()).apply(self.fill(Side.BUY, 5, "100"))
        position = position.apply(
            self.fill(Side.SELL, 8, "90", NOW + timedelta(seconds=1))
        )
        self.assertEqual(position.quantity, -3)
        self.assertEqual(position.average_price, Decimal("90"))
        self.assertEqual(position.realized_pnl, Decimal("-50"))

    def test_portfolio_applies_trade_once(self):
        portfolio = Portfolio(AccountId("acct-demo"), [Money(Decimal("5000"))])
        fill = self.fill(Side.BUY, 10, "100", commission="2")
        first = portfolio.apply_fill(fill)
        second = portfolio.apply_fill(fill)
        self.assertEqual(first.cash_balance("INR").amount, Decimal("3998"))
        self.assertEqual(second.cash_balance("INR").amount, Decimal("3998"))
        self.assertEqual(len(second.applied_trades), 1)


class MarketDataTests(unittest.TestCase):
    def test_quote_spread_midpoint_and_staleness(self):
        quote = Quote(instrument(), 99, 101, 10, 20, NOW, " Feed ")
        self.assertEqual(quote.midpoint, Decimal("100"))
        self.assertEqual(quote.spread, Decimal("2"))
        self.assertEqual(quote.provider, "feed")
        self.assertTrue(quote.is_stale(NOW + timedelta(seconds=61), timedelta(seconds=60)))

    def test_market_store_retrieves_history_and_rejects_time_reversal(self):
        store = MarketDataStore(3)
        for offset in range(3):
            store.append_quote(
                Quote(instrument(), 99 + offset, 100 + offset, 1, 1, NOW + timedelta(seconds=offset), "feed")
            )
        self.assertEqual(len(store.quote_history(instrument().key, limit=2)), 2)
        self.assertEqual(store.latest_quote(instrument().key).bid, Decimal("101"))
        with self.assertRaises(MarketDataError):
            store.append_quote(Quote(instrument(), 1, 2, 1, 1, NOW, "feed"))

    def test_bar_aggregator_emits_ohlcv(self):
        aggregator = BarAggregator(timedelta(minutes=1))
        ticks = [
            TradeTick(instrument(), 100, 2, NOW, "feed"),
            TradeTick(instrument(), 103, 3, NOW + timedelta(seconds=20), "feed"),
            TradeTick(instrument(), 99, 4, NOW + timedelta(seconds=40), "feed"),
        ]
        for tick in ticks:
            self.assertEqual(aggregator.push(tick), ())
        completed = aggregator.push(
            TradeTick(instrument(), 101, 1, NOW + timedelta(minutes=1), "feed")
        )
        self.assertEqual(len(completed), 1)
        bar = completed[0]
        self.assertEqual((bar.open, bar.high, bar.low, bar.close), (Decimal("100"), Decimal("103"), Decimal("99"), Decimal("99")))
        self.assertEqual((bar.volume, bar.trade_count), (9, 3))

    def test_order_book_sorts_levels_and_prevents_crossing(self):
        book = OrderBook(instrument())
        snapshot = book.replace(
            [PriceLevel(99, 5), PriceLevel(100, 2)],
            [PriceLevel(102, 3), PriceLevel(101, 4)],
            sequence=1,
            observed_at=NOW,
        )
        self.assertEqual(snapshot.best_bid.price, Decimal("100"))
        self.assertEqual(snapshot.best_ask.price, Decimal("101"))
        with self.assertRaises(MarketDataError):
            book.update(BookSide.BID, PriceLevel(102, 1), sequence=2, observed_at=NOW)
        self.assertEqual(book.snapshot().best_bid.price, Decimal("100"))
        self.assertEqual(book.snapshot().sequence, 1)

    def test_indicators_have_defined_warmup(self):
        values = [Decimal(value) for value in (1, 2, 3, 4)]
        self.assertEqual(simple_moving_average(values, 3), (None, None, Decimal("2"), Decimal("3")))
        self.assertEqual(exponential_moving_average(values, 3)[-1], Decimal("3.125"))


if __name__ == "__main__":
    unittest.main()
