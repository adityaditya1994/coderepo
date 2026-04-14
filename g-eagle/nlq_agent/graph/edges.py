"""
Edge functions — conditional routing logic for the LangGraph graph.
"""

from config.config_loader import load_config


def should_retry(state: dict) -> str:
    """
    After executor: decide whether to validate, fix SQL, or escalate.

    Returns
    -------
    str
        "validate" | "fix_sql" | "human_fallback"
    """
    config = load_config()
    max_attempts = config.get("retry", {}).get("max_attempts", 3)

    if state.get("execution_error") is None:
        return "validate"
    elif state.get("retry_count", 0) < max_attempts:
        return "fix_sql"
    else:
        return "human_fallback"


def after_validation(state: dict) -> str:
    """
    After validation council: decide whether to summarize, retry, or escalate.

    Returns
    -------
    str
        "summarize" | "retry" | "escalate"
    """
    config = load_config()
    threshold = config.get("human_fallback", {}).get("confidence_threshold", 0.4)

    validation = state.get("validation_result", {})
    confidence = validation.get("confidence", 0.5)
    recommendation = validation.get("recommendation", "proceed")

    if recommendation == "proceed" and confidence > 0.7:
        return "summarize"
    elif recommendation == "escalate" or confidence < threshold:
        return "escalate"
    else:
        return "retry"
