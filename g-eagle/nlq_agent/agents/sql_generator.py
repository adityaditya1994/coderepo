"""
SQL Generator agent — converts a structured query plan
into a SQL string using the LLM.
"""

import json

from prompts.sql_generator import SQL_GENERATOR_PROMPT


def sql_generator_node(state: dict, config: dict, llm) -> dict:
    """
    LangGraph node: generate SQL from the query plan.

    Reads: state["query_plan"], state["schema"]
    Writes: state["sql"], state["sql_history"]
    """
    query_plan = state.get("query_plan", {})
    schema = state.get("schema", {})
    db_provider = config.get("database", {}).get("provider", "athena")

    # Dialect mapping
    dialect_map = {
        "athena": "Presto/Athena SQL",
        "snowflake": "Snowflake SQL",
        "postgres": "PostgreSQL",
        "bigquery": "BigQuery SQL",
    }
    dialect = dialect_map.get(db_provider, db_provider)

    # Build a simple join map from schema (tables sharing column names)
    join_map = _infer_join_map(schema)

    prompt = SQL_GENERATOR_PROMPT.format(
        dialect=dialect,
        query_plan=json.dumps(query_plan, indent=2),
        schema=json.dumps(schema, indent=2),
        join_map=json.dumps(join_map, indent=2),
    )

    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    sql = _extract_sql(content)

    # Append to SQL history
    sql_history = list(state.get("sql_history", []))
    sql_history.append(sql)

    return {
        "sql": sql,
        "sql_history": sql_history,
    }


def _infer_join_map(schema: dict) -> dict:
    """
    Heuristically infer join relationships between tables
    based on shared column names (e.g. 'user_id' in both tables).
    """
    join_map = {}
    table_names = list(schema.keys())

    for i, t1 in enumerate(table_names):
        cols1 = {c["name"] for c in schema.get(t1, [])}
        for t2 in table_names[i + 1:]:
            cols2 = {c["name"] for c in schema.get(t2, [])}
            shared = cols1 & cols2
            if shared:
                key = f"{t1} <-> {t2}"
                join_map[key] = list(shared)

    return join_map


def _extract_sql(text: str) -> str:
    """Strip markdown fences from LLM SQL output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
