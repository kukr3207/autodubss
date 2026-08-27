# Autodub trading dashboard

Autodub is a small Django dashboard for configuring Bank Nifty trading bots
and authenticating them with Fyers. The dashboard uses SQLite for local
development and can use PostgreSQL through `DATABASE_URL` in deployed
environments.

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
The optional market-data packages are loaded only when an order is explicitly
executed, so management commands and the dashboard work without a live broker
connection.

Configuration is read from environment variables. Copy `.env.example` as a
reference; never commit real broker, database, or Django credentials.

## Docker

`docker compose up --build` starts the dashboard and PostgreSQL. Database
migrations run when the web container starts, not while its image is built.

## Tests

The repository includes app-level regression tests and project smoke tests in
`tests/`. GitHub Actions runs the same checks on every pull request and push to
`main`.

```bash
python -m pip install -r requirements-test.txt
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```
