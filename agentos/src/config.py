"""
config.py

Environment-driven configuration for the onboarding agent system.

Local development defaults to SQLite.  Set DATABASE_URL to a
PostgreSQL connection string for production use.

Factors addressed:
  5 - Durable state persistence
"""

import logging
import os

from agno.models.aws import Claude

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

MODEL = Claude(
    id=os.environ.get(
        "AGENT_MODEL",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    ),
)

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_db():
    """Return the appropriate Agno DB backend based on DATABASE_URL.

    - If DATABASE_URL starts with ``postgresql``, use ``PostgresDb``.
    - Otherwise fall back to ``SqliteDb`` for local development.
    """
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        try:
            from agno.db.postgres import PostgresDb

            logger.info("Using PostgresDb for production persistence.")
            return PostgresDb(db_url=DATABASE_URL)
        except ImportError:
            logger.warning(
                "agno.db.postgres or psycopg not installed. "
                "Install with: pip install 'psycopg[binary]'. "
                "Falling back to SqliteDb.",
            )

    from agno.db.sqlite import SqliteDb

    db_path = os.environ.get("SQLITE_DB_PATH", "tmp/agentos.db")
    if DATABASE_URL:
        logger.warning(
            "DATABASE_URL is set but not a PostgreSQL URL. Falling back to SqliteDb.",
        )
    else:
        logger.info("No DATABASE_URL set. Using SqliteDb for local development.")
    return SqliteDb(db_file=db_path)


def get_state_db_url() -> str:
    """Return a SQLAlchemy-compatible connection string for the StateStore.

    Re-uses DATABASE_URL when available; otherwise points at a local SQLite
    file next to the Agno DB.
    """
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        return DATABASE_URL
    return f"sqlite:///{os.environ.get('SQLITE_DB_PATH', 'tmp/agentos_state.db')}"


DB = get_db()

# ---------------------------------------------------------------------------
# Control-flow configuration
# ---------------------------------------------------------------------------

MAX_STEP_RETRIES = int(os.environ.get("MAX_STEP_RETRIES", "3"))
