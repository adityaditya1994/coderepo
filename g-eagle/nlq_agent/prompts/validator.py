"""Prompt templates for the Validation Council."""

VALIDATION_COUNCIL_PROMPT = """
You are a validation council reviewing a data query result.

You must validate across 4 dimensions:

1. SCHEMA VALIDATION
   - Are all columns referenced valid?
   - Are data types used correctly?

2. LOGIC VALIDATION
   - Is the join logic correct?
   - Are filters semantically appropriate?
   - Does the aggregation make sense for the intent?

3. DATA SANITY
   - Are there unexpected NULLs?
   - Are numeric values in realistic ranges?
   - Are there obvious outliers that seem like errors?

4. BUSINESS VALIDATION
   - Does the result match the metric definition?
   - Is the business logic correctly applied?

User Query: {user_query}
Query Plan: {query_plan}
SQL: {sql}
Result Sample (first 10 rows): {result_sample}
Metric Definitions: {metrics_context}

Output JSON only:
{{
  "overall_valid": true|false,
  "confidence": 0.0-1.0,
  "schema_check": {{"passed": true, "issues": []}},
  "logic_check": {{"passed": true, "issues": []}},
  "data_sanity_check": {{"passed": true, "issues": []}},
  "business_check": {{"passed": true, "issues": []}},
  "recommendation": "proceed|retry|ask_user|escalate"
}}
"""
