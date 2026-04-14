"""
Executor agent — runs the generated SQL against the configured
database, captures result or error, increments retry count.
"""

from db.db_factory import get_executor


def executor_node(state: dict, config: dict) -> dict:
    """
    LangGraph node: execute the SQL query.

    Reads: state["sql"], state["retry_count"]
    Writes: state["execution_result"], state["execution_error"], state["retry_count"]
    """
    sql = state.get("sql", "")
    retry_count = state.get("retry_count", 0)

    if not sql:
        return {
            "execution_result": None,
            "execution_error": "No SQL to execute",
            "retry_count": retry_count,
        }

    try:
        executor = get_executor(config)
        result = executor.execute(sql)

        # Check for empty results
        if result.get("row_count", 0) == 0:
            return {
                "execution_result": result,
                "execution_error": "EMPTY_RESULT: Query returned 0 rows",
                "retry_count": retry_count + 1,
            }

        return {
            "execution_result": result,
            "execution_error": None,
            "retry_count": retry_count,
        }

    except Exception as e:
        return {
            "execution_result": None,
            "execution_error": str(e),
            "retry_count": retry_count + 1,
        }
