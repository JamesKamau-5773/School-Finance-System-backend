# School Financial System Backend

Flask-based backend API for school finance, fees, students, inventory, and reporting workflows.

## Tech Stack

- Python + Flask
- SQLAlchemy + Flask-Migrate (Alembic)
- JWT authentication and role-based access
- Pytest for unit and integration tests

## Project Structure

- `app/` - application package (controllers, services, models, repositories)
- `migrations/` - Alembic migrations
- `tests/` - unit and integration tests
- `run.py` - local app entrypoint
- `config.py` - environment-driven configuration

## Prerequisites

- Python 3.10+ recommended
- `pip`
- PostgreSQL (optional; SQLite works for local development)

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` in the project root and set required variables:

```env
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
DATABASE_URL=sqlite:///school_db.db
CORS_ORIGINS=http://localhost:5173
ENFORCE_HTTPS=False
```

## Run the Application

```bash
python run.py
```

Server runs on:

- `http://0.0.0.0:5000`
- Health check: `GET /api/health`

## Database Migrations

Run migrations from the project root:

```bash
flask db upgrade
```

If needed, create a new migration:

```bash
flask db migrate -m "describe change"
flask db upgrade
```

## Test Commands

Install test extras (if needed):

```bash
pip install -r requirements-test.txt
```

Run full test suite:

```bash
pytest tests/
```

Run by marker:

```bash
pytest -m unit
pytest -m integration
```

## Main API Areas

- `/api/auth` - login, registration, user administration
- `/api/finance` - transactions, expenses, summaries, ledgers
- `/api/fees` - fee structures, payments, invoices
- `/api/students` - student directory and ledgers
- `/api/inventory` - stock status, consumption, add-stock, item management
- `/api/reports` - reporting endpoints
- `/api/transactions` - transaction listing and creation

## Notes

- The app enforces required secrets (`SECRET_KEY`, `JWT_SECRET_KEY`) at startup.
- CORS origins are configurable via `CORS_ORIGINS`.
- Log files are ignored by git and should not be committed.
