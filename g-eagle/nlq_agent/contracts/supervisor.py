"""
Supervisor Agent Contract
─────────────────────────
Input:  user_query, session_id (initial); full state on re-entry
Output: confidence_score, needs_human, error_log
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class SupervisorInput(BaseModel):
    """Input expected by the supervisor on first invocation."""
    user_query: str = Field(..., description="Natural-language user question")
    session_id: str = Field(default="", description="Session identifier")
    # Re-entry fields (populated on subsequent calls)
    sql: Optional[str] = Field(default=None, description="Current SQL (None on first pass)")
    confidence_score: float = Field(default=0.5, description="Current confidence score")
    retry_count: int = Field(default=0)
    validation_result: dict = Field(default_factory=dict)

    @classmethod
    def from_state(cls, state: dict) -> "SupervisorInput":
        return cls(
            user_query=state.get("user_query", ""),
            session_id=state.get("session_id", ""),
            sql=state.get("sql"),
            confidence_score=state.get("confidence_score", 0.5),
            retry_count=state.get("retry_count", 0),
            validation_result=state.get("validation_result", {}),
        )


class SupervisorOutput(BaseModel):
    """Output produced by the supervisor."""
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0.0–1.0")
    needs_human: bool = Field(..., description="True if human review required")
    error_log: List[str] = Field(default_factory=list)

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "SupervisorOutput":
        return cls(
            confidence_score=state.get("confidence_score", 0.5),
            needs_human=state.get("needs_human", False),
            error_log=state.get("error_log", []),
        )
