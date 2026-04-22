# Agent I/O Contracts

All contracts are defined as Pydantic models — **one file per agent** under `contracts/`.

## Contract Files

| Agent | File | Input Class | Output Class |
|-------|------|-------------|--------------|
| Supervisor | [`supervisor.py`](supervisor.py) | `SupervisorInput` | `SupervisorOutput` |
| Discovery | [`discovery.py`](discovery.py) | `DiscoveryInput` | `DiscoveryOutput` |
| Schema Retriever | [`schema_retriever.py`](schema_retriever.py) | `SchemaRetrieverInput` | `SchemaRetrieverOutput` |
| Query Planner | [`query_planner.py`](query_planner.py) | `QueryPlannerInput` | `QueryPlannerOutput` |
| SQL Generator | [`sql_generator.py`](sql_generator.py) | `SqlGeneratorInput` | `SqlGeneratorOutput` |
| Executor | [`executor.py`](executor.py) | `ExecutorInput` | `ExecutorOutput` |
| SQL Fixer | [`sql_fixer.py`](sql_fixer.py) | `SqlFixerInput` | `SqlFixerOutput` |
| Validation Council | [`validation_council.py`](validation_council.py) | `ValidationCouncilInput` | `ValidationCouncilOutput` |
| Summarizer | [`summarizer.py`](summarizer.py) | `SummarizerInput` | `SummarizerOutput` |
| Human Handoff | [`human_handoff.py`](human_handoff.py) | `HumanHandoffInput` | `HumanHandoffOutput` |
| Memory Writer | [`memory_writer.py`](memory_writer.py) | `MemoryWriterInput` | `MemoryWriterOutput` |

## Happy-Path Chain

```
Supervisor → Discovery → Schema Retriever → Query Planner → SQL Generator → Executor → Validation Council → Summarizer → Memory Writer
```

| From Agent | To Agent | Output → Input | Key Fields |
|-----------|----------|---------------|------------|
| Supervisor | Discovery | `SupervisorOutput` → `DiscoveryInput` | `user_query`, `session_id` (passthrough in state) |
| Discovery | Schema Retriever | `DiscoveryOutput` → `SchemaRetrieverInput` | `discovered_tables: List[dict]`, `memory_context: dict` |
| Schema Retriever | Query Planner | `SchemaRetrieverOutput` → `QueryPlannerInput` | `schema: dict`, `selected_tables: List[str]` |
| Query Planner | SQL Generator | `QueryPlannerOutput` → `SqlGeneratorInput` | `query_plan: dict` |
| SQL Generator | Executor | `SqlGeneratorOutput` → `ExecutorInput` | `sql: str`, `sql_history: List[str]` |
| Executor | Validation Council | `ExecutorOutput` → `ValidationCouncilInput` | `execution_result: Any?`, `execution_error: str?` |
| Validation Council | Summarizer | `ValidationCouncilOutput` → `SummarizerInput` | `validation_result: dict`, `confidence_score: float` |
| Summarizer | Memory Writer | `SummarizerOutput` → `MemoryWriterInput` | `summary`, `final_answer` (passthrough in state) |

## Error / Retry Paths

| From Agent | To Agent | Output → Input | Trigger |
|-----------|----------|---------------|---------|
| Executor | SQL Fixer | `ExecutorOutput` → `SqlFixerInput` | `execution_error is not None` and `retry_count < max_attempts` |
| SQL Fixer | Executor | `SqlFixerOutput` → `ExecutorInput` | Always (re-execute fixed SQL) |
| Executor | Human Handoff | `ExecutorOutput` → `HumanHandoffInput` | `retry_count >= max_attempts` |
| Validation Council | Human Handoff | `ValidationCouncilOutput` → `HumanHandoffInput` | `confidence < threshold` or `recommendation == "escalate"` |
| Validation Council | SQL Generator | `ValidationCouncilOutput` → `SqlGeneratorInput` | `recommendation == "retry"` |

## Adapters

Each output model has:
- `to_state() → dict` — serialize to AgentState slice
- `from_state(state) → Model` — deserialize from AgentState

Each input model has:
- `from_state(state) → Model` — deserialize from AgentState
- `from_{previous_agent}(state_or_output)` — factory classmethod from upstream output
