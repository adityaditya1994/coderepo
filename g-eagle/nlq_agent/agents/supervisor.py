"""
Supervisor agent — the top-level orchestrator that interprets
user intent, monitors confidence, and decides routing.
"""

import json

from prompts.supervisor import SUPERVISOR_DECISION_PROMPT


def supervisor_node(state: dict, config: dict, llm) -> dict:
    """
    LangGraph node (entry point): evaluate current state and decide routing.

    On first call (no sql yet): just pass through to start the pipeline.
    On subsequent calls: evaluate whether to proceed, retry, or escalate.

    Reads: state["user_query"], state["confidence_score"], state["retry_count"],
           state["validation_result"]
    Writes: state["needs_human"], state["confidence_score"]
    """
    user_query = state.get("user_query", "")

    # First pass — no SQL generated yet, just initialize state
    if not state.get("sql"):
        return {
            "confidence_score": 1.0,
            "needs_human": False,
            "error_log": state.get("error_log", []),
        }

    # Subsequent passes — evaluate confidence and decide
    confidence = state.get("confidence_score", 0.5)
    retry_count = state.get("retry_count", 0)
    validation = state.get("validation_result", {})
    max_retries = config.get("retry", {}).get("max_attempts", 3)
    threshold = config.get("human_fallback", {}).get("confidence_threshold", 0.4)

    issues = validation.get("issues", [])
    if not issues:
        # Collect issues from sub-checks
        for check_key in ["schema_check", "logic_check", "data_sanity_check", "business_check"]:
            check = validation.get(check_key, {})
            issues.extend(check.get("issues", []))

    prompt = SUPERVISOR_DECISION_PROMPT.format(
        user_query=user_query,
        confidence_score=confidence,
        retry_count=retry_count,
        max_retries=max_retries,
        validation_result=json.dumps(validation, indent=2),
        issues=json.dumps(issues),
    )

    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    try:
        decision = json.loads(_extract_json(content))
    except json.JSONDecodeError:
        decision = {"decision": "proceed", "reasoning": "parse error, defaulting"}

    needs_human = decision.get("decision") in ("escalate", "clarify")

    return {
        "needs_human": needs_human,
        "confidence_score": confidence,
    }


def _extract_json(text: str) -> str:
    """Strip markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text
