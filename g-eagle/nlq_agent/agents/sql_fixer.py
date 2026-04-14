"""
SQL Fixer agent — classifies the execution error using an LLM,
then generates a corrected SQL query.
"""

import json

from prompts.sql_fixer import ERROR_CLASSIFIER_PROMPT, SQL_FIXER_PROMPT


def sql_fixer_node(state: dict, config: dict, llm) -> dict:
    """
    LangGraph node: classify error → fix SQL.

    Reads: state["sql"], state["execution_error"], state["schema"]
    Writes: state["sql"], state["sql_history"], state["error_log"]
    """
    sql = state.get("sql", "")
    error = state.get("execution_error", "")
    schema = state.get("schema", {})

    # Step 1: Classify the error
    classify_prompt = ERROR_CLASSIFIER_PROMPT.format(
        sql=sql,
        error=error,
    )
    classify_response = llm.invoke(classify_prompt)
    classify_content = (
        classify_response.content
        if hasattr(classify_response, "content")
        else str(classify_response)
    )

    try:
        classification = json.loads(_extract_json(classify_content))
    except json.JSONDecodeError:
        classification = {
            "error_type": "UNKNOWN",
            "affected_part": "unknown",
            "fix_hint": "Review the full query",
        }

    # Step 2: Fix the SQL
    fix_prompt = SQL_FIXER_PROMPT.format(
        error_type=classification.get("error_type", "UNKNOWN"),
        affected_part=classification.get("affected_part", ""),
        fix_hint=classification.get("fix_hint", ""),
        sql=sql,
        error=error,
        schema=json.dumps(schema, indent=2),
    )
    fix_response = llm.invoke(fix_prompt)
    fix_content = (
        fix_response.content
        if hasattr(fix_response, "content")
        else str(fix_response)
    )
    fixed_sql = _extract_sql(fix_content)

    # Update history and error log
    sql_history = list(state.get("sql_history", []))
    sql_history.append(fixed_sql)

    error_log = list(state.get("error_log", []))
    error_log.append(
        f"Error: {classification.get('error_type')} — "
        f"{classification.get('affected_part')} — "
        f"Fix: {classification.get('fix_hint')}"
    )

    return {
        "sql": fixed_sql,
        "sql_history": sql_history,
        "error_log": error_log,
        "execution_error": None,    # clear the error for next attempt
    }


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
