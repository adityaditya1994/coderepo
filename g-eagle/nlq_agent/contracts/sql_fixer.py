"""
SQL Fixer Agent Contract
─────────────────────────
Input:  sql, execution_error, schema, sql_history
Output: sql, sql_history, error_log, execution_error (cleared)
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class SqlFixerInput(BaseModel):
    """Input expected by the SQL fixer."""
    sql: str = Field(..., description="The SQL that failed")
    execution_error: str = Field(..., description="The execution error message")
    schema: dict = Field(default_factory=dict, description="DB schema for context")
    sql_history: List[str] = Field(default_factory=list, description="Previous SQL attempts")

    @classmethod
    def from_executor(cls, state: dict) -> "SqlFixerInput":
        return cls(
            sql=state.get("sql", ""),
            execution_error=state.get("execution_error", ""),
            schema=state.get("schema", {}),
            sql_history=state.get("sql_history", []),
        )

    @classmethod
    def from_state(cls, state: dict) -> "SqlFixerInput":
        return cls.from_executor(state)


class SqlFixerOutput(BaseModel):
    """Output from the SQL fixer."""
    sql: str = Field(..., description="Corrected SQL query")
    sql_history: List[str] = Field(default_factory=list, description="All SQL versions")
    error_log: List[str] = Field(default_factory=list, description="Error descriptions")
    execution_error: Optional[str] = Field(
        default=None, description="Cleared to None after fix"
    )

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "SqlFixerOutput":
        return cls(
            sql=state.get("sql", ""),
            sql_history=state.get("sql_history", []),
            error_log=state.get("error_log", []),
            execution_error=state.get("execution_error"),
        )
