"""
Database connection and session management for FAIRSHIFT.
Provides transaction safety, thread-safe connection handling, and schema initialization.
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import config

_local = threading.local()

def get_db_path() -> str:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return config.DB_PATH

def create_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db_cursor(commit: bool = False) -> Generator[sqlite3.Cursor, None, None]:
    conn = create_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def init_db(force: bool = False) -> None:
    """Initializes the database schema."""
    db_file = Path(get_db_path())
    if force and db_file.exists():
        db_file.unlink()

    schema_file = Path(__file__).resolve().parent / "schema.sql"
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_cursor(commit=True) as cursor:
        cursor.executescript(schema_sql)

def reset_db() -> None:
    """Safely resets the database and reapplies schema."""
    init_db(force=True)
