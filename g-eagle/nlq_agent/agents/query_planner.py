"""
Query Planner agent — converts a natural-language query
into a structured analytical plan (JSON) without writing SQL.
"""

import json

from prompts.query_planner import QUERY_PLANNER_PROMPT


def query_planner_node(state: dict, config: dict, llm) -> dict:
    """
    LangGraph node: produce a structured query plan from the user query.

    Reads: state["user_query"], state["schema"], state["memory_context"]
    Writes: state["query_plan"]
    """
    user_query = state.get("user_query", "")
    schema = state.get("schema", {})
    memory_ctx = state.get("memory_context", {})
    metrics_context = memory_ctx.get("metrics", "{}")

    prompt = QUERY_PLANNER_PROMPT.format(
        user_query=user_query,
        schema=json.dumps(schema, indent=2),
        metrics_context=(
            json.dumps(metrics_context, indent=2)
            if isinstance(metrics_context, dict) else str(metrics_context)
        ),
    )

    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    try:
        plan = json.loads(_extract_json(content))
    except json.JSONDecodeError:
        plan = {
            "intent": "unknown",
            "metrics": [],
            "dimensions": [],
            "filters": [],
            "raw_response": content,
        }

    return {"query_plan": plan}


def _extract_json(text: str) -> str:
    """Strip markdown fences from LLM JSON output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text
