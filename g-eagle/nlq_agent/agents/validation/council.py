"""
Validation Council — aggregates the 4 validators
(schema, logic, data, business) and computes an overall
confidence score and recommendation.
"""

import json

from agents.validation.schema_validator import SchemaValidator
from agents.validation.logic_validator import LogicValidator
from agents.validation.data_validator import DataValidator
from agents.validation.business_validator import BusinessValidator


def validation_council_node(state: dict, config: dict, llm) -> dict:
    """
    LangGraph node: run all 4 validators and aggregate results.

    Reads: state["sql"], state["schema"], state["user_query"],
           state["query_plan"], state["execution_result"], state["memory_context"]
    Writes: state["validation_result"], state["confidence_score"]
    """
    sql = state.get("sql", "")
    schema = state.get("schema", {})
    user_query = state.get("user_query", "")
    query_plan = state.get("query_plan", {})
    execution_result = state.get("execution_result", {})
    metrics_context = state.get("memory_context", {}).get("metrics", {})

    # ── Run all 4 validators ──

    # 1. Schema validation (rule-based)
    schema_val = SchemaValidator()
    schema_check = schema_val.validate(sql, schema)

    # 2. Logic validation (LLM-based)
    logic_val = LogicValidator(llm)
    logic_check = logic_val.validate(user_query, query_plan, sql)

    # 3. Data sanity (rule-based)
    data_val = DataValidator()
    data_check = data_val.validate(execution_result)

    # 4. Business validation (LLM-based)
    business_val = BusinessValidator(llm)
    business_check = business_val.validate(
        user_query, sql, execution_result, metrics_context
    )

    # ── Aggregate ──
    all_checks = [schema_check, logic_check, data_check, business_check]
    all_passed = all(c.get("passed", False) for c in all_checks)
    all_issues = []
    for c in all_checks:
        all_issues.extend(c.get("issues", []))

    # Confidence: start at 1.0, deduct per failed check
    confidence = 1.0
    weight_map = {
        "schema": 0.15,
        "logic": 0.30,
        "data": 0.25,
        "business": 0.30,
    }
    checks_named = {
        "schema": schema_check,
        "logic": logic_check,
        "data": data_check,
        "business": business_check,
    }
    for name, check in checks_named.items():
        if not check.get("passed", True):
            confidence -= weight_map[name]

    confidence = max(0.0, min(1.0, confidence))

    # Determine recommendation
    threshold = config.get("human_fallback", {}).get("confidence_threshold", 0.4)
    if all_passed and confidence > 0.7:
        recommendation = "proceed"
    elif confidence >= threshold:
        recommendation = "retry"
    else:
        recommendation = "escalate"

    validation_result = {
        "overall_valid": all_passed,
        "confidence": confidence,
        "schema_check": schema_check,
        "logic_check": logic_check,
        "data_sanity_check": data_check,
        "business_check": business_check,
        "recommendation": recommendation,
        "issues": all_issues,
    }

    return {
        "validation_result": validation_result,
        "confidence_score": confidence,
    }
