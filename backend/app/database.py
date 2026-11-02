
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import DATABASE_PATH

SCHEMA_VERSION = 1


def get_connection():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")

    return conn


@contextmanager
def db_session():
    """Commit on success, roll back on error, always close."""
    conn = get_connection()

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database():
    with db_session() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]

        if version >= SCHEMA_VERSION:
            return

        # Check for an older database structure.
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        if "mandates" in tables:
            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(mandates)"
                ).fetchall()
            }

            if "max_amount" in columns and "max_amount_minor" not in columns:
                raise RuntimeError(
                    "An older database schema was found. "
                    "A safe migration is required before starting the API."
                )

        # Create tables.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mandates (
                id TEXT PRIMARY KEY,
                purpose TEXT NOT NULL,
                max_amount_minor INTEGER NOT NULL
                    CHECK (max_amount_minor > 0),
                currency TEXT NOT NULL
                    CHECK (length(currency) = 3),
                allowed_merchants TEXT NOT NULL
                    CHECK (json_valid(allowed_merchants)),
                expires_at TEXT NOT NULL,
                require_approval INTEGER NOT NULL
                    CHECK (require_approval IN (0, 1)),
                signature TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                mandate_id TEXT NOT NULL REFERENCES mandates(id),
                amount_minor INTEGER NOT NULL
                    CHECK (amount_minor >= 0),
                currency TEXT NOT NULL
                    CHECK (length(currency) = 3),
                merchant TEXT NOT NULL,
                decision TEXT NOT NULL
                    CHECK (decision IN ('allow', 'deny', 'needs_approval')),
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Index for faster mandate history lookup.
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_mandate
            ON decisions(mandate_id, created_at)
        """)

        # Keep the audit log immutable.
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS decisions_no_update
            BEFORE UPDATE ON decisions
            BEGIN
                SELECT RAISE(ABORT, 'decisions are immutable');
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS decisions_no_delete
            BEFORE DELETE ON decisions
            BEGIN
                SELECT RAISE(ABORT, 'decisions are immutable');
            END
        """)

        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
