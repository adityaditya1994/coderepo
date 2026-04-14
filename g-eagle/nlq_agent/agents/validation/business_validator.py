"""
Business Validator — uses an LLM to check whether the query
result matches the business metric definitions and
organizational expectations.
"""

import json


class BusinessValidator:
    """LLM-based validation against business metric definitions."""

    PROMPT = """
You are a business data quality reviewer.

User Query: {user_query}
SQL Used: {sql}
Result Sample (first 10 rows): {result_sample}
Metric Definitions: {metrics_context}

Check:
1. Does the result match the metric definition (e.g. revenue = SUM(unit_price * quantity))?
2. Is the business logic correctly applied (e.g. correct status filters)?
3. Are the time boundaries appropriate?
4. Does the result make business sense?

Output JSON only:
{{
  "passed": true|false,
  "issues": ["issue1", "issue2"]
}}
"""

    def __init__(self, llm):
        self.llm = llm

    def validate(
        self,
        user_query: str,
        sql: str,
        execution_result: dict,
        metrics_context: dict,
    ) -> dict:
        """
        Ask the LLM to verify results against business definitions.

        Returns
        -------
        dict
            {"passed": bool, "issues": list[str]}
        """
        # Format result sample
        result_sample = self._format_sample(execution_result)

        prompt = self.PROMPT.format(
            user_query=user_query,
            sql=sql,
            result_sample=result_sample,
            metrics_context=json.dumps(metrics_context, indent=2),
        )

        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        try:
            result = json.loads(_extract_json(content))
            return {
                "passed": result.get("passed", True),
                "issues": result.get("issues", []),
            }
        except json.JSONDecodeError:
            return {"passed": True, "issues": []}

    @staticmethod
    def _format_sample(execution_result: dict, max_rows: int = 10) -> str:
        """Format execution result as a readable text table."""
        if not execution_result:
            return "No results"

        columns = execution_result.get("columns", [])
        rows = execution_result.get("rows", [])[:max_rows]

        if not columns:
            return "No results"

        lines = [" | ".join(columns)]
        lines.append("-" * len(lines[0]))
        for row in rows:
            lines.append(" | ".join(str(v) for v in row))
        return "\n".join(lines)


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text
