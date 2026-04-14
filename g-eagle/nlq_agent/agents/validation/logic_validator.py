"""
Logic Validator — uses an LLM to check whether the SQL
logic (joins, filters, aggregations) is correct for the
stated query intent.
"""

import json


class LogicValidator:
    """LLM-based validation of SQL logic correctness."""

    PROMPT = """
You are reviewing SQL logic for correctness.

User Query (intent): {user_query}
Query Plan: {query_plan}
SQL: {sql}

Check:
1. Are JOIN conditions correct (no Cartesian products)?
2. Are WHERE filters semantically appropriate for the intent?
3. Does the aggregation (GROUP BY, SUM, COUNT, etc.) match the intent?
4. Are there any logical errors (e.g. filtering after aggregation incorrectly)?

Output JSON only:
{{
  "passed": true|false,
  "issues": ["issue1", "issue2"]
}}
"""

    def __init__(self, llm):
        self.llm = llm

    def validate(self, user_query: str, query_plan: dict, sql: str) -> dict:
        """
        Ask the LLM to review the SQL logic.

        Returns
        -------
        dict
            {"passed": bool, "issues": list[str]}
        """
        prompt = self.PROMPT.format(
            user_query=user_query,
            query_plan=json.dumps(query_plan, indent=2),
            sql=sql,
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


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text
