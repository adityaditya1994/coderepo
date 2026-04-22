"""
Schema Retriever Agent Contract
────────────────────────────────
Input:  discovered_tables
Output: schema, selected_tables
"""

from typing import List
from pydantic import BaseModel, Field


class SchemaRetrieverInput(BaseModel):
    """Input expected by the schema retriever."""
    discovered_tables: List[dict] = Field(
        ..., description="Tables to retrieve schema for"
    )

    @classmethod
    def from_discovery(cls, output) -> "SchemaRetrieverInput":
        """Build from a DiscoveryOutput instance."""
        return cls(discovered_tables=output.discovered_tables)

    @classmethod
    def from_state(cls, state: dict) -> "SchemaRetrieverInput":
        return cls(discovered_tables=state.get("discovered_tables", []))


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
