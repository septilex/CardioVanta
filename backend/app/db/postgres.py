"""
Short-lived PostgreSQL connections for research metadata.

The connection string comes only from ``settings.require_secret("DATABASE_URL")`` (a SecretStr, never logged).
``psycopg`` is imported inside ``connect()``, so importing this module, or serving predictions, never loads it.
One connection per request suits a serverless function: there is no pool to keep alive between invocations.
"""
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from backend.app.core.config import Settings, settings as default_settings

CONNECT_TIMEOUT_S = 5


class ResearchDatabaseUnavailable(RuntimeError):
    """The database could not be reached or queried. The message never contains the connection string."""


@contextmanager
def connect(cfg: Optional[Settings] = None, *, read_only: bool = True) -> Iterator[Any]:
    """Open one connection (read-only by default) and always close it.

    Raises MissingSecretError when DATABASE_URL is not configured, and ResearchDatabaseUnavailable when the
    server cannot be reached.
    """
    url = (cfg or default_settings).require_secret("DATABASE_URL")
    import psycopg  # lazy: only the research endpoint and the migration runner need the driver

    try:
        conn = psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_S, application_name="cardiovanta-research")
    except psycopg.Error as e:
        raise ResearchDatabaseUnavailable(f"could not connect to the research database ({type(e).__name__})") from None
    try:
        conn.read_only = read_only
        # Writers manage their own transactions with conn.transaction(); with autocommit on, each such block is
        # a real transaction that commits on exit (otherwise it would be a savepoint, rolled back on close).
        conn.autocommit = not read_only
        yield conn
    finally:
        conn.close()
