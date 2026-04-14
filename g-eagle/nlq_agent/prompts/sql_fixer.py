"""Prompt templates for the SQL Fixer agent (error classification + fix)."""

ERROR_CLASSIFIER_PROMPT = """
You are an expert SQL debugger.

Classify the execution error into exactly one category:

Categories:
- SYNTAX_ERROR: invalid SQL syntax
- MISSING_COLUMN: column doesn't exist in table
- MISSING_TABLE: table doesn't exist
- JOIN_ERROR: incorrect join key or Cartesian product
- EMPTY_RESULT: query ran but returned 0 rows
- TIMEOUT: query exceeded time limit
- PERMISSION_ERROR: access denied
- UNKNOWN: cannot determine

SQL:
{sql}

Error:
{error}

Output JSON only:
{{
  "error_type": "CATEGORY",
  "affected_part": "which part of SQL caused it",
  "fix_hint": "short suggestion for fix"
}}
"""

SQL_FIXER_PROMPT = """
You are a senior data engineer fixing a broken SQL query.

Error Type: {error_type}
Affected Part: {affected_part}
Fix Hint: {fix_hint}

Original SQL:
{sql}

Error Message:
{error}

Schema (for reference):
{schema}

Rules:
- Fix ONLY what is broken
- Preserve the original analytical intent
- Do NOT change business logic unless the error requires it
- If EMPTY_RESULT, try relaxing filters or checking joins

Output: Corrected SQL ONLY. No explanation.
"""
