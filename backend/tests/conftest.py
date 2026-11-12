import os

# Environment variables must be set before the application is imported.
os.environ["APP_ENV"] = "test"
os.environ["APP_SECRET_KEY"] = "test-only-secret-key-must-be-32-chars"
os.environ["DATABASE_URL"] = "postgresql+psycopg://epp:local-dev-only-change-me@localhost:5432/epp_test"
os.environ["COOKIE_SECURE"] = "false"
os.environ["COOKIE_SAMESITE"] = "lax"
os.environ["EPP_AGENT_MODE"] = "test"
os.environ["GOOGLE_CLIENT_ID"] = ""

import pytest
from sqlalchemy import text


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database():
    import psycopg
    from alembic import command
    from alembic.config import Config

    with psycopg.connect(
        "postgresql://epp:local-dev-only-change-me@localhost:5432/epp",
        autocommit=True,
    ) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'epp_test'").fetchone()
        if not exists:
            conn.execute("CREATE DATABASE epp_test")
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def clean_database(migrated_test_database):
    yield
    from app.core.config import get_settings
    from app.core.rate_limit import rate_limiter
    from app.db.session import engine

    get_settings.cache_clear()
    rate_limiter.reset()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
