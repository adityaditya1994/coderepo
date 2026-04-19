# Agent I/O Contracts

All contracts are defined as Pydantic models in [`contracts/__init__.py`](../contracts/__init__.py).

## Chain: Discovery → Schema Retriever → Query Planner → SQL Generator → Executor → Validator → Summarizer

| From Agent | To Agent | Contract Class | Key Fields |
|-----------|----------|---------------|------------|
| Discovery | Schema Retriever | `DiscoveryOutput` → `SchemaRetrieverInput` | `discovered_tables: List[dict]`, `memory_context: dict` |
| Schema Retriever | Query Planner | `SchemaRetrieverOutput` → `QueryPlannerInput` | `schema: dict`, `selected_tables: List[str]` |
| Query Planner | SQL Generator | `QueryPlannerOutput` → `SqlGeneratorInput` | `query_plan: dict` |
| SQL Generator | Executor | `SqlGeneratorOutput` → `ExecutorInput` | `sql: str`, `sql_history: List[str]` |
| Executor | Validation Council | `ExecutorOutput` → `ValidationCouncilInput` | `execution_result: Any?`, `execution_error: str?` |
| Validation Council | Summarizer | `ValidationCouncilOutput` → `SummarizerInput` | `validation_result: dict`, `confidence_score: float` |

## Adapters

Each output model has:
- `to_state() → dict` — serialize to AgentState slice
- `from_state(state) → Model` — deserialize from AgentState

Each input model has:
- `from_{previous_agent}(state_or_output)` — factory classmethod
