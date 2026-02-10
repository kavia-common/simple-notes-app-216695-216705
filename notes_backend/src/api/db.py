"""
SQLite database helper utilities for the Notes backend.

This module centralizes:
- Database path resolution (env-driven with a sensible default)
- Connection creation
- Schema initialization (ensure notes table + updated_at trigger exist)

The database is expected to be shared with the SQLite "database" container.
Per project conventions, the primary configuration is via the SQLITE_DB env var.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional


def _default_db_path() -> str:
    """
    Compute the default SQLite DB path.

    Default is 'database/myapp.db' relative to the backend container root
    (notes_backend/...). We compute it from this file location to avoid relying
    on current working directory.
    """
    # notes_backend/src/api/db.py -> notes_backend/
    backend_root = Path(__file__).resolve().parents[3]
    return str(backend_root / "database" / "myapp.db")


def get_db_path() -> str:
    """Resolve SQLite DB file path from env with a safe default."""
    return os.getenv("SQLITE_DB", _default_db_path())


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection with Row factory enabled."""
    db_path = get_db_path()

    # Ensure parent directory exists when using the default path.
    # If SQLITE_DB points elsewhere, we do not create arbitrary directories.
    if db_path == _default_db_path():
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_note_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a SQLite Row to a JSON-serializable dict matching our API schema."""
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# PUBLIC_INTERFACE
def init_db() -> None:
    """Ensure the notes schema exists (idempotent)."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Keep schema aligned with database container init_db.py
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Maintain updated_at automatically on update.
        cur.execute(
            """
            CREATE TRIGGER IF NOT EXISTS notes_set_updated_at
            AFTER UPDATE ON notes
            FOR EACH ROW
            BEGIN
                UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
            END;
            """
        )

        conn.commit()
    finally:
        conn.close()


def fetch_one_note(conn: sqlite3.Connection, note_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single note by id; returns None if not found."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?",
        (note_id,),
    )
    row = cur.fetchone()
    return row_to_note_dict(row) if row else None
