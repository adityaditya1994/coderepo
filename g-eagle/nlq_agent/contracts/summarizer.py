"""
Summarizer Agent Contract
──────────────────────────
Input:  user_query, sql, execution_result, validation_result, confidence_score, memory_context
Output: summary, final_answer
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class SummarizerInput(BaseModel):
    """Input expected by the summarizer."""
    user_query: str
    sql: str
    execution_result: Optional[Any] = None
    validation_result: dict = Field(default_factory=dict)
    confidence_score: float = 0.0
    memory_context: dict = Field(default_factory=dict)

    @classmethod
    def from_validation(cls, state: dict) -> "SummarizerInput":
        return cls(
            user_query=state.get("user_query", ""),
            sql=state.get("sql", ""),
            execution_result=state.get("execution_result"),
            validation_result=state.get("validation_result", {}),
            confidence_score=state.get("confidence_score", 0.0),
            memory_context=state.get("memory_context", {}),
        )

    @classmethod
    def from_state(cls, state: dict) -> "SummarizerInput":
        return cls.from_validation(state)


class SummarizerOutput(BaseModel):
    """Output from the summarizer."""
    summary: str = Field(..., description="Business-friendly narrative of results")
    final_answer: str = Field(..., description="Final answer for the user")

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "SummarizerOutput":
        return cls(
            summary=state.get("summary", ""),
            final_answer=state.get("final_answer", ""),
        )
