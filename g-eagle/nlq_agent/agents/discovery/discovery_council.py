"""
Discovery Council — an LLM-powered mini-council that deduplicates,
scores, and selects the top-K most relevant tables from all
discovery sources.
"""

import json
from typing import List

from prompts.discovery import DISCOVERY_COUNCIL_PROMPT


class DiscoveryCouncil:
    """Use an LLM to rank and select the best tables from all sources."""

    def __init__(self, llm, top_k: int = 5):
        self.llm = llm
        self.top_k = top_k

    def evaluate(self, user_query: str, candidates: List[dict]) -> List[dict]:
        """
        Send all candidate tables to the LLM council for ranking.

        Parameters
        ----------
        user_query : str
            The original natural-language query.
        candidates : list[dict]
            Merged candidate tables from all connectors.

        Returns
        -------
        list[dict]
            Top-K selected tables with confidence and reason.
        """
        if not candidates:
            return []

        prompt = DISCOVERY_COUNCIL_PROMPT.format(
            user_query=user_query,
            candidates=json.dumps(candidates, indent=2),
            top_k=self.top_k,
        )

        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        try:
            # Extract JSON from LLM response
            result = json.loads(self._extract_json(content))
            return result.get("selected_tables", [])
        except (json.JSONDecodeError, KeyError):
            # Fallback: return top-K candidates by any existing score
            sorted_candidates = sorted(
                candidates,
                key=lambda x: x.get("score", 0),
                reverse=True,
            )
            return sorted_candidates[: self.top_k]

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from LLM response that may have markdown fences."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            lines = lines[1:] if lines[0].startswith("```") else lines
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text
