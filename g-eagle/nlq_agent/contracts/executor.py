"""
Executor Agent Contract
────────────────────────
Input:  sql, retry_count
Output: execution_result, execution_error, retry_count
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class ExecutorInput(BaseModel):
    """Input expected by the executor."""
    sql: str
    retry_count: int = 0

    @classmethod
    def from_sql_generator(cls, state: dict) -> "ExecutorInput":
        return cls(
            sql=state.get("sql", ""),
            retry_count=state.get("retry_count", 0),
        )

    @classmethod
    def from_state(cls, state: dict) -> "ExecutorInput":
        return cls.from_sql_generator(state)


class ExecutorOutput(BaseModel):
    """Output from the executor."""
    execution_result: Optional[Any] = None
    execution_error: Optional[str] = None
    retry_count: int = 0

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "ExecutorOutput":
        return cls(
            execution_result=state.get("execution_result"),
            execution_error=state.get("execution_error"),
            retry_count=state.get("retry_count", 0),
        )
