"""
Long-Term Memory — SQLite-backed persistent store for
query history (query → SQL → result → feedback).
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Optional
from pathlib import Path


_DEFAULT_DB = Path(__file__).parent / "query_history.db"


class LongTermMemory:
    """SQLite-backed query history store."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(_DEFAULT_DB)
        self._init_db()

    def _init_db(self):
        """Create the query_history table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                user_query TEXT,
                query_plan TEXT,
                sql_generated TEXT,
                execution_success INTEGER,
                retry_count INTEGER,
                validation_passed INTEGER,
                summary TEXT,
                user_feedback TEXT,
                confidence_score REAL,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def store(self, state: dict, feedback: str = None):
        """
        Store a completed query run in the history.

        Parameters
        ----------
        state : dict
            The full agent state after completion.
        feedback : str, optional
            User feedback (thumbs up/down or correction).
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO query_history
            (id, session_id, user_query, query_plan, sql_generated,
             execution_success, retry_count, validation_passed,
             summary, user_feedback, confidence_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                state.get("session_id", ""),
                state.get("user_query", ""),
                json.dumps(state.get("query_plan", {})),
                state.get("sql", ""),
                1 if state.get("execution_error") is None else 0,
                state.get("retry_count", 0),
                1 if state.get("validation_result", {}).get("overall_valid") else 0,
                state.get("summary", ""),
                feedback,
                state.get("confidence_score", 0.0),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def search(self, query: str, limit: int = 5) -> List[dict]:
        """
        Search past queries by keyword match.

        Returns
        -------
        list[dict]
            Matching history records.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT * FROM query_history
            WHERE user_query LIKE ? AND execution_success = 1
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_recent(self, session_id: str = None, limit: int = 10) -> List[dict]:
        """Get recent query history, optionally filtered by session."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if session_id:
            cursor = conn.execute(
                "SELECT * FROM query_history WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM query_history ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
