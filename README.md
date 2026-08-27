# Autodub trading dashboard

Autodub is a Django trading dashboard backed by an original, dependency-free
execution and research engine. The dashboard configures Bank Nifty bots and
Fyers authentication, while `trading_engine` supplies the reusable domain,
risk, simulation, and operations layers. SQLite works out of the box and
deployed environments can use PostgreSQL through `DATABASE_URL`.

## Trading engine

The engine is intentionally separate from Django and third-party broker SDKs.
It can be imported from management commands, background workers, notebooks,
or a future API service without initializing Django.

- Immutable instruments, money, orders, fills, positions, and portfolio
  snapshots use decimal arithmetic and explicit state transitions.
- Quotes, trades, OHLCV bars, order books, rolling indicators, provider
  normalization, and bounded history share one validated market-data model.
- Pre-trade risk checks cover quantities, notionals, positions, exposure,
  daily loss, stale quotes, price bands, open orders, and circuit breaking.
- Broker interfaces, a simulated broker, commissions, slippage, retry policy,
  idempotent order storage, and an execution service support paper trading.
- Moving-average, breakout, and composite strategies plug into position
  sizing and the same execution path used by historical backtests.
- Backtest reports include equity, drawdown, volatility, Sharpe and Sortino
  ratios, while analytics add correlations, attribution, tail risk, and stress
  scenarios.
- Audit events form a tamper-evident hash chain. Exchange calendars, job
  retries, health probes, reconciliation, and strict JSON codecs cover common
  operational needs.

Run a deterministic demonstration without broker credentials:

```bash
python manage.py run_engine_demo
python manage.py run_engine_demo --fast-period 2 --slow-period 4 --compact
```

## Local setup

Python 3.9 is the supported runtime.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://localhost:8000/`, sign in, and add Fyers application credentials
for your user in Django admin before starting the broker authentication flow.
The optional legacy market-data packages are loaded only when an order is
explicitly executed. Engine tests, management commands, and the dashboard work
without a live broker connection.

Configuration is read from environment variables. Copy `.env.example` as a
reference; never commit real broker, database, or Django credentials.

## Docker

`docker compose up --build` starts the dashboard and PostgreSQL. Database
migrations run when the web container starts, not while its image is built.

## Tests

The repository includes app-level regression tests, project smoke tests, and
50 focused engine tests in `tests/engine`. GitHub Actions runs the same checks
on every pull request and push to `main`.

```bash
python -m pip install -r requirements-test.txt
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```
