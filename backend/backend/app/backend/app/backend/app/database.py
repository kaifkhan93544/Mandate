import sqlite3
from .config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mandates (
                id TEXT PRIMARY KEY,
                purpose TEXT NOT NULL,
                max_amount REAL NOT NULL,
                currency TEXT NOT NULL,
                allowed_merchants TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                require_approval INTEGER NOT NULL,
                signature TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                mandate_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                merchant TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
