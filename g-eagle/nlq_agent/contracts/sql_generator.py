"""
SQL Generator Agent Contract
──────────────────────────────
Input:  user_query, schema, selected_tables, query_plan, memory_context, sql_history
Output: sql, sql_history
"""

from typing import List
from pydantic import BaseModel, Field


class SqlGeneratorInput(BaseModel):
    """Input expected by the SQL generator."""
    user_query: str
    schema: dict
    selected_tables: List[str]
    query_plan: dict
    memory_context: dict = Field(default_factory=dict)
    sql_history: List[str] = Field(default_factory=list)

    @classmethod
    def from_query_planner(cls, state: dict) -> "SqlGeneratorInput":
        return cls(
            user_query=state.get("user_query", ""),
            schema=state.get("schema", {}),
            selected_tables=state.get("selected_tables", []),
            query_plan=state.get("query_plan", {}),
            memory_context=state.get("memory_context", {}),
            sql_history=state.get("sql_history", []),
        )

    @classmethod
    def from_state(cls, state: dict) -> "SqlGeneratorInput":
        return cls.from_query_planner(state)


class SqlGeneratorOutput(BaseModel):
    """Output from the SQL generator."""
    sql: str = Field(..., description="Generated SQL query")
    sql_history: List[str] = Field(
        default_factory=list, description="All SQL versions attempted"
    )

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "SqlGeneratorOutput":
        return cls(
            sql=state.get("sql", ""),
            sql_history=state.get("sql_history", []),
        )
