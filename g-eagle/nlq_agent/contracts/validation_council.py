"""
Validation Council Agent Contract
───────────────────────────────────
Input:  sql, schema, user_query, query_plan, execution_result, memory_context
Output: validation_result, confidence_score
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class ValidationCouncilInput(BaseModel):
    """Input expected by the validation council."""
    sql: str
    schema: dict
    user_query: str
    query_plan: dict
    execution_result: Optional[Any] = None
    memory_context: dict = Field(default_factory=dict)

    @classmethod
    def from_executor(cls, state: dict) -> "ValidationCouncilInput":
        return cls(
            sql=state.get("sql", ""),
            schema=state.get("schema", {}),
            user_query=state.get("user_query", ""),
            query_plan=state.get("query_plan", {}),
            execution_result=state.get("execution_result"),
            memory_context=state.get("memory_context", {}),
        )

    @classmethod
    def from_state(cls, state: dict) -> "ValidationCouncilInput":
        return cls.from_executor(state)


class ValidationCouncilOutput(BaseModel):
    """Output from the validation council."""
    validation_result: dict = Field(
        ..., description="{overall_valid, confidence, recommendation, issues, ...}"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated confidence 0.0–1.0"
    )

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "ValidationCouncilOutput":
        return cls(
            validation_result=state.get("validation_result", {}),
            confidence_score=state.get("confidence_score", 0.0),
        )
