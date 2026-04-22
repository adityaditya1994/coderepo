"""
Query Planner Agent Contract
─────────────────────────────
Input:  user_query, schema, selected_tables, memory_context
Output: query_plan
"""

from typing import List
from pydantic import BaseModel, Field


class QueryPlannerInput(BaseModel):
    """Input expected by the query planner."""
    user_query: str
    schema: dict
    selected_tables: List[str]
    memory_context: dict = Field(default_factory=dict)

    @classmethod
    def from_schema_retriever(cls, state: dict) -> "QueryPlannerInput":
        return cls(
            user_query=state.get("user_query", ""),
            schema=state.get("schema", {}),
            selected_tables=state.get("selected_tables", []),
            memory_context=state.get("memory_context", {}),
        )

    @classmethod
    def from_state(cls, state: dict) -> "QueryPlannerInput":
        return cls.from_schema_retriever(state)


class QueryPlannerOutput(BaseModel):
    """Output from the query planner."""
    query_plan: dict = Field(
        ..., description="Structured query plan with steps, tables, aggregations"
    )

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "QueryPlannerOutput":
        return cls(query_plan=state.get("query_plan", {}))
