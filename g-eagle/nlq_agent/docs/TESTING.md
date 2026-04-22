# API Testing Guide - NLQ Pipeline

This document provides End-to-End and Agent-level testing documentation. You can test each agent individually, maintaining the LangGraph state flow, or test the full pipeline.

## Prerequisites

1. Ensure **Ollama** is running locally with the active model (e.g. `gemma4:latest`).
2. Have the DB/Warehouse running (e.g., Docker Postgres via `docker-compose up -d` if querying Postgres).
3. Start the FastAPI test server from the `nlq_agent` directory:
   ```bash
   cd nlq_agent
   uvicorn api.main:app --reload --port 8000
   ```

## Mode 2: End-to-End Pipeline

Test the full LangGraph pipeline from start to finish via the unified querying endpoint.

```bash
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{
           "question": "What is the total revenue by region for Q1 2024?",
           "session_id": "test-session-123"
         }'
```

**Expected Result:** You will get a JSON payload containing:
- `final_answer`: The final summarized business narrative.
- `sql`: The actual SQL string compiled.
- `trace`: An array of agent execution timings and telemetry.
- `mermaid`: The mermaid execution path diagram.

---

## Mode 1: Individual Agent Testing

To verify each agent individually, you can POST partial graph states to `/agents/{agent_name}/invoke`. The series of curls below tells a continuous story ("What is the total revenue by region for Q1 2024?"), carrying forward the state at each step as it typically would in the LangGraph topology.

### 1. Supervisor
Analyzes the intent and sets off the pipeline.
```bash
curl -X POST http://localhost:8000/agents/supervisor/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "session_id": "demo-001"
           }
         }'
```

### 2. Discovery Agent
Finds the most relevant tables for the query.
```bash
curl -X POST http://localhost:8000/agents/discovery/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "session_id": "demo-001"
           }
         }'
```

### 3. Schema Retriever
Gets exact columns for the discovered tables (uses output of discovery).
```bash
curl -X POST http://localhost:8000/agents/schema_retriever/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "discovered_tables": [
               { "name": "orders", "database": "ecommerce_analytics", "columns": [{"name": "order_id", "type": "bigint"}, {"name": "total_amount", "type": "double"}, {"name": "region_id", "type": "int"}] },
               { "name": "regions", "database": "ecommerce_analytics", "columns": [{"name": "region_id", "type": "int"}, {"name": "region_name", "type": "varchar"}] }
             ]
           }
         }'
```

### 4. Query Planner
Designs the join/aggregation strategy.
```bash
curl -X POST http://localhost:8000/agents/query_planner/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "schema": {
                "orders": [{"name": "total_amount", "type": "double"}, {"name": "region_id", "type": "int"}],
                "regions": [{"name": "region_id", "type": "int"}, {"name": "region_name", "type": "varchar"}]
             },
             "selected_tables": ["orders", "regions"]
           }
         }'
```

### 5. SQL Generator
Generates dialect-specific SQL based on the plan.
```bash
curl -X POST http://localhost:8000/agents/sql_generator/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "schema": {
                "orders": [{"name": "total_amount", "type": "double"}, {"name": "region_id", "type": "int"}],
                "regions": [{"name": "region_id", "type": "int"}, {"name": "region_name", "type": "varchar"}]
             },
             "selected_tables": ["orders", "regions"],
             "query_plan": {"objective": "sum total_amount grouped by region where date is Q1 2024", "tables": ["orders", "regions"]},
             "sql_history": []
           }
         }'
```

### 6. Executor
Executes the generated SQL.
```bash
curl -X POST http://localhost:8000/agents/executor/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "sql": "SELECT r.region_name, SUM(o.total_amount) AS total_revenue FROM orders o JOIN regions r ON o.region_id = r.region_id GROUP BY r.region_name",
             "retry_count": 0
           }
         }'
```

### 7. SQL Fixer (Alternative Path)
If Executor fails, SQL Fixer steps in to repair errors.
```bash
curl -X POST http://localhost:8000/agents/sql_fixer/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "sql": "SELECT r.region_name, SUM(o.total_amount) AS total_revenue FROM order_broken o JOIN regions r ON o.region_id = r.region_id GROUP BY r.region_name",
             "execution_error": "Table order_broken does not exist",
             "schema": {
                "orders": [{"name": "total_amount", "type": "double"}, {"name": "region_id", "type": "int"}],
                "regions": [{"name": "region_id", "type": "int"}, {"name": "region_name", "type": "varchar"}]
             },
             "query_plan": {"objective": "calculate total revenue by region"}
           }
         }'
```

### 8. Validation Council
Checks if the data matches the user intent.
```bash
curl -X POST http://localhost:8000/agents/validator/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "sql": "SELECT r.region_name, SUM(o.total_amount) AS total_revenue FROM orders o JOIN regions r ON o.region_id = r.region_id GROUP BY r.region_name",
             "execution_result": {"columns": ["region_name", "total_revenue"], "rows": [["APAC", 3549.96]], "row_count": 1},
             "schema": {
                "orders": [{"name": "total_amount", "type": "double"}, {"name": "region_id", "type": "int"}],
                "regions": [{"name": "region_id", "type": "int"}, {"name": "region_name", "type": "varchar"}]
             },
             "query_plan": {"objective": "total revenue by region"}
           }
         }'
```

### 9. Summarizer
Turns validation + result into a business narrative.
```bash
curl -X POST http://localhost:8000/agents/summarizer/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "sql": "SELECT r.region_name, SUM(o.total_amount) AS total_revenue FROM orders o JOIN regions r ON o.region_id = r.region_id GROUP BY r.region_name",
             "execution_result": {"columns": ["region_name", "total_revenue"], "rows": [["APAC", 3549.96], ["North America", 1919.92]], "row_count": 2},
             "validation_result": {"overall_valid": true, "confidence": 0.95, "recommendation": "proceed"}
           }
         }'
```

### 10. Memory Writer
Persists conversation artifacts into graph memory.
```bash
curl -X POST http://localhost:8000/agents/memory_writer/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "session_id": "demo-123",
             "final_answer": "The total revenue by region is 3549.96 for APAC and 1919.92 for North America.",
             "sql": "SELECT r.region_name, SUM(o.total_amount) FROM orders..."
           }
         }'
```

### 11. Human Handoff (Alternative Mock Path)
Fallback triggered if validation confidence is too low.
```bash
curl -X POST http://localhost:8000/agents/human_handoff/invoke \
     -H "Content-Type: application/json" \
     -d '{
           "state": {
             "user_query": "What is the total revenue by region for Q1 2024?",
             "validation_result": {"overall_valid": false, "confidence": 0.30, "recommendation": "escalate"},
             "sql": "SELECT * FROM orders LIMIT 1",
             "confidence_score": 0.30
           }
         }'
```

## Reading Logs

The main uvicorn server output will automatically log the structured trace whenever an agent runs. Look out for the following details seamlessly populated for all agent requests:
- **Trace IDs** identifying individual paths logic takes.
- `input keys:` and `output keys:` showcasing data passing perfectly inside the partial state mappings.
- `duration_ms` tracking agent processing time in milliseconds.
- Graceful `error` logging matching the graph flow if an agent deliberately faults.
