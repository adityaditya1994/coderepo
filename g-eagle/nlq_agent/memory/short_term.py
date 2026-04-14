"""
Short-Term Memory — session-scoped in-memory store for the
current conversation context, retries, and corrections.
"""

from typing import Optional


class ShortTermMemory:
    """In-memory dict scoped to a single session."""

    def __init__(self):
        self._store: dict = {}

    def set(self, session_id: str, key: str, value):
        """Store a value for the current session."""
        if session_id not in self._store:
            self._store[session_id] = {}
        self._store[session_id][key] = value

    def get(self, session_id: str, key: str, default=None):
        """Retrieve a value from the current session."""
        return self._store.get(session_id, {}).get(key, default)

    def get_all(self, session_id: str) -> dict:
        """Get the full context for a session."""
        return self._store.get(session_id, {})

    def append(self, session_id: str, key: str, value):
        """Append to a list in the session store."""
        if session_id not in self._store:
            self._store[session_id] = {}
        if key not in self._store[session_id]:
            self._store[session_id][key] = []
        self._store[session_id][key].append(value)

    def clear(self, session_id: str):
        """Clear all data for a session."""
        self._store.pop(session_id, None)

    def clear_all(self):
        """Clear all sessions."""
        self._store.clear()
