"""
Memory Manager — unified facade for the 3-layer memory system.
Handles retrieval (context building) and storage (post-execution).
"""

import uuid
from typing import List

from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.semantic_memory import SemanticMemory
from knowledge_base.metrics_store import MetricsStore


class MemoryManager:
    """Unified interface for short-term, long-term, and semantic memory."""

    def __init__(self, config: dict):
        self.config = config
        memory_cfg = config.get("memory", {})

        # Initialize layers based on config toggles
        self.short_term = ShortTermMemory() if memory_cfg.get("short_term", True) else None
        self.long_term = LongTermMemory() if memory_cfg.get("long_term", True) else None
        self.semantic = SemanticMemory(config) if memory_cfg.get("semantic", False) else None
        self.metrics_store = MetricsStore()

    def retrieve_context(self, user_query: str, session_id: str) -> dict:
        """
        Build a memory context dict for the current query.

        Combines:
        - Short-term: current session context
        - Long-term: similar past queries from SQLite
        - Semantic: similar past queries from Pinecone
        - Metrics: relevant metric definitions

        Returns
        -------
        dict
            Memory context with keys: session, past_queries, similar_patterns, metrics.
        """
        context = {
            "session": {},
            "past_queries": [],
            "similar_patterns": [],
            "metrics": {},
        }

        # Short-term context
        if self.short_term:
            context["session"] = self.short_term.get_all(session_id)

        # Long-term keyword search
        if self.long_term:
            context["past_queries"] = self.long_term.search(user_query, limit=3)

        # Semantic similarity search
        if self.semantic:
            context["similar_patterns"] = self.semantic.search(user_query, top_k=3)

        # Metrics from knowledge base
        context["metrics"] = self.metrics_store.get_approved()

        return context

    def store_result(self, state: dict, feedback: str = None):
        """
        Store the completed query result across all memory layers.

        Parameters
        ----------
        state : dict
            Full agent state after completion.
        feedback : str, optional
            User feedback on the result.
        """
        session_id = state.get("session_id", "")

        # Short-term: store latest query in session
        if self.short_term:
            self.short_term.set(session_id, "last_query", state.get("user_query", ""))
            self.short_term.set(session_id, "last_sql", state.get("sql", ""))
            self.short_term.append(session_id, "query_history", {
                "query": state.get("user_query", ""),
                "sql": state.get("sql", ""),
                "success": state.get("execution_error") is None,
            })

        # Long-term: persist to SQLite
        if self.long_term:
            self.long_term.store(state, feedback)

        # Semantic: store successful patterns
        if self.semantic and state.get("execution_error") is None:
            self.semantic.store(
                query_id=str(uuid.uuid4()),
                user_query=state.get("user_query", ""),
                sql=state.get("sql", ""),
                metadata={
                    "session_id": session_id,
                    "confidence": state.get("confidence_score", 0.0),
                },
            )


def memory_writer_node(state: dict, config: dict) -> dict:
    """
    LangGraph node: write the completed pipeline result to memory.

    This is the last node in the graph before END.
    """
    mm = MemoryManager(config)
    mm.store_result(state)
    return {}
