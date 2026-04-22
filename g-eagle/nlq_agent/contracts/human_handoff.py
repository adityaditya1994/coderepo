"""
Human Handoff Agent Contract
──────────────────────────────
Input:  full pipeline state (user_query, sql, sql_history, errors, validation, confidence)
Output: final_answer, needs_human
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class HumanHandoffInput(BaseModel):
    """Input expected by the human handoff agent."""
    user_query: str = Field(default="", description="Original user question")
    sql: str = Field(default="", description="Current SQL attempt")
    sql_history: List[str] = Field(default_factory=list, description="All SQL attempts")
    execution_error: Optional[str] = Field(default=None, description="Last execution error")
    retry_count: int = Field(default=0)
    validation_result: dict = Field(default_factory=dict)
    error_log: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @classmethod
    def from_state(cls, state: dict) -> "HumanHandoffInput":
        return cls(
            user_query=state.get("user_query", ""),
            sql=state.get("sql", ""),
            sql_history=state.get("sql_history", []),
            execution_error=state.get("execution_error"),
            retry_count=state.get("retry_count", 0),
            validation_result=state.get("validation_result", {}),
            error_log=state.get("error_log", []),
            confidence_score=state.get("confidence_score", 0.0),
        )


class HumanHandoffOutput(BaseModel):
    """Output from the human handoff agent."""
    final_answer: str = Field(..., description="Human-readable handoff message")
    needs_human: bool = Field(default=True, description="Always True for handoff")

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "HumanHandoffOutput":
        return cls(
            final_answer=state.get("final_answer", ""),
            needs_human=state.get("needs_human", True),
        )
