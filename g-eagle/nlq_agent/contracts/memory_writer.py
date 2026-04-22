"""
Memory Writer Agent Contract
──────────────────────────────
Input:  full pipeline state (user_query, sql, execution results, session_id)
Output: (empty dict — writes to memory stores as side effect)
"""

from typing import Optional, Any, List
from pydantic import BaseModel, Field


class MemoryWriterInput(BaseModel):
    """Input expected by the memory writer."""
    user_query: str = Field(default="", description="Original user question")
    session_id: str = Field(default="", description="Session identifier")
    sql: str = Field(default="", description="Final SQL query")
    execution_result: Optional[Any] = Field(default=None, description="Query results")
    execution_error: Optional[str] = Field(default=None, description="Execution error if any")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @classmethod
    def from_state(cls, state: dict) -> "MemoryWriterInput":
        return cls(
            user_query=state.get("user_query", ""),
            session_id=state.get("session_id", ""),
            sql=state.get("sql", ""),
            execution_result=state.get("execution_result"),
            execution_error=state.get("execution_error"),
            confidence_score=state.get("confidence_score", 0.0),
        )


class MemoryWriterOutput(BaseModel):
    """Output from the memory writer (empty — side-effect only)."""

    def to_state(self) -> dict:
        return {}

    @classmethod
    def from_state(cls, state: dict) -> "MemoryWriterOutput":
        return cls()
