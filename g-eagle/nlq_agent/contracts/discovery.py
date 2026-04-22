"""
Discovery Agent Contract
────────────────────────
Input:  user_query, session_id
Output: discovered_tables, memory_context
"""

from typing import List
from pydantic import BaseModel, Field


class DiscoveryInput(BaseModel):
    """Input expected by the discovery agent."""
    user_query: str = Field(..., description="Natural-language user question")
    session_id: str = Field(default="", description="Session identifier")

    @classmethod
    def from_state(cls, state: dict) -> "DiscoveryInput":
        return cls(
            user_query=state.get("user_query", ""),
            session_id=state.get("session_id", ""),
        )


class DiscoveryOutput(BaseModel):
    """Output from the discovery agent."""
    discovered_tables: List[dict] = Field(
        ..., description="List of table metadata dicts with name, source, columns, score"
    )
    memory_context: dict = Field(
        default_factory=dict, description="Memory context from retrieval"
    )

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "DiscoveryOutput":
        return cls(
            discovered_tables=state.get("discovered_tables", []),
            memory_context=state.get("memory_context", {}),
        )
