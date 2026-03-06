"""
Database connection utilities.

Provides the shared connection context manager and database path configuration.
"""

import os
import sqlite3
from contextlib import contextmanager

# Database path - stored in trinity-data volume
DB_PATH = os.getenv("TRINITY_DB_PATH", "/data/trinity.db")


@contextmanager
def get_db_connection():
    """Context manager for database connections with proper transaction handling."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
