"""
Agent I/O Contracts — Pydantic models defining the data contract
between each pair of adjacent agents in the graph.

Each model maps 1:1 to slices of AgentState and provides
to_state() / from_state() adapters for serialization.
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Discovery → Schema Retriever
# ══════════════════════════════════════════════════════════════

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


class SchemaRetrieverInput(BaseModel):
    """Input expected by the schema retriever."""
    discovered_tables: List[dict] = Field(
        ..., description="Tables to retrieve schema for"
    )

    @classmethod
    def from_discovery(cls, output: DiscoveryOutput) -> "SchemaRetrieverInput":
        return cls(discovered_tables=output.discovered_tables)


# ══════════════════════════════════════════════════════════════
# Schema Retriever → Query Planner
# ══════════════════════════════════════════════════════════════

class SchemaRetrieverOutput(BaseModel):
    """Output from the schema retriever."""
    schema: dict = Field(
        ..., description="Map of table_name → [{name, type}] columns"
    )
    selected_tables: List[str] = Field(
        ..., description="List of table names with schema retrieved"
    )

    def to_state(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_state(cls, state: dict) -> "SchemaRetrieverOutput":
        return cls(
            schema=state.get("schema", {}),
            selected_tables=state.get("selected_tables", []),
        )


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


# ══════════════════════════════════════════════════════════════
# Query Planner → SQL Generator
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# SQL Generator → Executor
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Executor → Validation Council
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Validation Council → Summarizer
# ══════════════════════════════════════════════════════════════

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
