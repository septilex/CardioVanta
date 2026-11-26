"""
Apply the research-database SQL files in order: ``python -m backend.app.db.migrate``.

Each file in ``backend/app/db/sql/`` runs once, inside its own transaction, and is recorded in
``schema_migrations``; running the command again applies nothing. Reads DATABASE_URL like the API does.
"""
import sys
from pathlib import Path
from typing import List, Optional

from backend.app.core.config import Settings
from backend.app.db.postgres import connect

SQL_DIR = Path(__file__).resolve().parent / "sql"


def migration_files() -> List[Path]:
    return sorted(SQL_DIR.glob("*.sql"))


def apply_migrations(cfg: Optional[Settings] = None) -> List[str]:
    """Apply pending migrations; return the file names applied by this run."""
    applied: List[str] = []
    with connect(cfg, read_only=False) as conn:
        with conn.transaction():
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
        done = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
        for path in migration_files():
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied


if __name__ == "__main__":
    names = apply_migrations()
    print("applied: " + (", ".join(names) if names else "nothing (database is up to date)"))
    sys.exit(0)
