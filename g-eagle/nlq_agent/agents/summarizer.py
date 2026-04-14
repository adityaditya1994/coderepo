"""
Summarizer agent — produces a business-friendly summary
of query results for the end user.
"""

from prompts.summarizer import SUMMARIZER_PROMPT


def summarizer_node(state: dict, config: dict, llm) -> dict:
    """
    LangGraph node: summarize execution results in business language.

    Reads: state["user_query"], state["execution_result"]
    Writes: state["summary"], state["final_answer"]
    """
    user_query = state.get("user_query", "")
    result = state.get("execution_result", {})
    sql = state.get("sql", "")
    query_plan = state.get("query_plan", {})
    confidence = state.get("confidence_score", 0.0)

    # Format result for the prompt
    if isinstance(result, dict):
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        # Show first 20 rows max
        display_rows = rows[:20]
        result_text = _format_result_table(columns, display_rows)
    else:
        result_text = str(result)

    import json
    prompt = SUMMARIZER_PROMPT.format(
        user_query=user_query,
        result=result_text,
        sql=sql,
        query_plan=json.dumps(query_plan, indent=2) if isinstance(query_plan, dict) else str(query_plan),
        confidence=f"{confidence:.2f}",
    )

    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    return {
        "summary": content,
        "final_answer": content,
    }


def _format_result_table(columns: list, rows: list) -> str:
    """Format columns/rows into a readable text table."""
    if not columns:
        return "No results"

    lines = [" | ".join(columns)]
    lines.append("-" * len(lines[0]))

    for row in rows:
        lines.append(" | ".join(str(v) for v in row))

    return "\n".join(lines)
