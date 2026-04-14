"""
Human Handoff agent — formats the current pipeline state
for human review when confidence is too low or retries exhausted.
"""


def human_handoff_node(state: dict, config: dict) -> dict:
    """
    LangGraph node: prepare a human-readable handoff package.

    This node is placed behind interrupt_before in the graph,
    so the graph will pause here and let a human review.

    Reads: entire state
    Writes: state["final_answer"], state["needs_human"]
    """
    user_query = state.get("user_query", "")
    sql = state.get("sql", "")
    sql_history = state.get("sql_history", [])
    execution_error = state.get("execution_error", "")
    retry_count = state.get("retry_count", 0)
    validation = state.get("validation_result", {})
    error_log = state.get("error_log", [])
    confidence = state.get("confidence_score", 0.0)

    # Build a structured handoff message
    handoff = {
        "status": "HUMAN_REVIEW_REQUIRED",
        "user_query": user_query,
        "confidence_score": confidence,
        "retry_count": retry_count,
        "current_sql": sql,
        "sql_attempts": sql_history,
        "last_error": execution_error,
        "validation_result": validation,
        "error_log": error_log,
        "message": (
            f"The agent was unable to confidently answer this query "
            f"after {retry_count} attempts. "
            f"Current confidence: {confidence:.2f}. "
            f"Please review the SQL and errors above."
        ),
    }

    # Format as readable text for display
    lines = [
        "═" * 60,
        "🚨 HUMAN REVIEW REQUIRED",
        "═" * 60,
        f"Query: {user_query}",
        f"Confidence: {confidence:.2f}",
        f"Retries: {retry_count}",
        "",
        "── Current SQL ──",
        sql or "(none)",
        "",
        "── Last Error ──",
        execution_error or "(none)",
        "",
        "── Error Log ──",
    ]
    for entry in error_log:
        lines.append(f"  • {entry}")
    lines.append("═" * 60)

    final_answer = "\n".join(lines)

    return {
        "final_answer": final_answer,
        "needs_human": True,
    }
