"""Run a deterministic backtest to verify the trading engine installation."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from trading_engine.backtest import BacktestRunner, HistoricalFeed
from trading_engine.domain import AssetClass, ContractSpec, Instrument
from trading_engine.market import Bar
from trading_engine.strategy import FixedQuantitySizer, MovingAverageCrossStrategy


DEFAULT_PRICES = (
    "100.00",
    "99.50",
    "98.75",
    "98.00",
    "98.50",
    "99.25",
    "100.50",
    "102.00",
    "103.25",
    "102.75",
    "101.50",
    "100.25",
    "99.00",
    "98.25",
    "99.75",
    "101.25",
    "103.00",
    "104.50",
)


class Command(BaseCommand):
    help = "Run a local moving-average backtest and print its report as JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            default="AUTODUB",
            help="Synthetic instrument symbol used in the report.",
        )
        parser.add_argument(
            "--exchange",
            default="DEMO",
            help="Synthetic exchange code used in the report.",
        )
        parser.add_argument(
            "--prices",
            help="Comma-separated positive closing prices; at least six are required.",
        )
        parser.add_argument(
            "--fast-period",
            type=int,
            default=3,
            help="Fast moving-average period.",
        )
        parser.add_argument(
            "--slow-period",
            type=int,
            default=5,
            help="Slow moving-average period.",
        )
        parser.add_argument(
            "--quantity",
            type=int,
            default=1,
            help="Units submitted for each generated signal.",
        )
        parser.add_argument(
            "--initial-cash",
            default="100000",
            help="Starting paper-trading cash balance.",
        )
        parser.add_argument(
            "--compact",
            action="store_true",
            help="Print compact JSON instead of an indented report.",
        )

    def handle(self, *args, **options):
        prices = self._prices(options.get("prices"))
        fast = options["fast_period"]
        slow = options["slow_period"]
        quantity = options["quantity"]
        if fast < 1:
            raise CommandError("--fast-period must be positive")
        if slow <= fast:
            raise CommandError("--slow-period must be greater than --fast-period")
        if quantity < 1:
            raise CommandError("--quantity must be positive")
        try:
            initial_cash = Decimal(options["initial_cash"])
        except InvalidOperation:
            raise CommandError("--initial-cash must be numeric")
        if not initial_cash.is_finite() or initial_cash <= 0:
            raise CommandError("--initial-cash must be a positive finite number")

        instrument = Instrument(
            options["symbol"],
            options["exchange"],
            AssetClass.EQUITY,
            ContractSpec(lot_size=1, tick_size=Decimal("0.01")),
            "Django management-command demonstration instrument",
        )
        feed = HistoricalFeed.from_bars(self._bars(instrument, prices))
        strategy = MovingAverageCrossStrategy(
            "django-demo-moving-average",
            fast_period=fast,
            slow_period=slow,
        )
        report = BacktestRunner(
            "Django trading engine demonstration",
            strategy,
            FixedQuantitySizer(quantity),
            initial_cash=initial_cash,
        ).run(feed)
        self.stdout.write(report.to_json(indent=None if options["compact"] else 2))

    @staticmethod
    def _prices(raw):
        values = DEFAULT_PRICES if raw is None else tuple(item.strip() for item in raw.split(","))
        if len(values) < 6:
            raise CommandError("--prices must contain at least six observations")
        result = []
        for index, value in enumerate(values, 1):
            try:
                price = Decimal(value)
            except InvalidOperation:
                raise CommandError("price %d is not numeric" % index)
            if not price.is_finite() or price <= 0:
                raise CommandError("price %d must be positive and finite" % index)
            result.append(price)
        return tuple(result)

    @staticmethod
    def _bars(instrument, prices):
        start = datetime(2025, 1, 2, 3, 45, tzinfo=timezone.utc)
        interval = timedelta(days=1)
        bars = []
        for index, price in enumerate(prices):
            opened_at = start + interval * index
            movement = max(Decimal("0.10"), price * Decimal("0.005"))
            bars.append(
                Bar(
                    instrument=instrument,
                    interval=interval,
                    opened_at=opened_at,
                    closed_at=opened_at + interval,
                    open=price,
                    high=price + movement,
                    low=max(Decimal("0.01"), price - movement),
                    close=price,
                    volume=1000 + index * 25,
                    trade_count=100 + index,
                    provider="django-demo",
                )
            )
        return tuple(bars)
