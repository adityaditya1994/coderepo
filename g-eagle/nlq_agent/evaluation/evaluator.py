"""
Evaluation Framework — measures the quality of the NLQ agent
across multiple dimensions.
"""

import time
import json
from typing import List, Callable
from dataclasses import dataclass, field, asdict


@dataclass
class EvalResult:
    """Result of a single evaluation run."""
    query: str
    expected_tables: List[str] = field(default_factory=list)
    expected_sql_contains: List[str] = field(default_factory=list)
    expected_answer_contains: List[str] = field(default_factory=list)

    # Measured
    discovered_tables: List[str] = field(default_factory=list)
    generated_sql: str = ""
    execution_success: bool = False
    retry_count: int = 0
    validation_passed: bool = False
    confidence_score: float = 0.0
    summary: str = ""
    latency_seconds: float = 0.0
    human_escalated: bool = False

    # Scores (computed)
    discovery_accuracy: float = 0.0
    sql_correctness: float = 0.0
    summary_relevance: float = 0.0


class Evaluator:
    """Run evaluation suites against the NLQ agent graph."""

    # Metric definitions
    METRICS = {
        "discovery_accuracy": "% correct tables identified",
        "sql_correctness": "% queries returning expected result",
        "retry_rate": "avg retries per query (lower = better)",
        "validation_pass_rate": "% passing council without retry",
        "summary_faithfulness": "LLM judge: does summary match data?",
        "end_to_end_latency": "seconds from query → answer",
        "human_escalation_rate": "% queries needing human (lower = better)",
    }

    def __init__(self, graph, config: dict, llm=None):
        self.graph = graph
        self.config = config
        self.llm = llm
        self.results: List[EvalResult] = []

    def run_test_case(self, test_case: dict) -> EvalResult:
        """
        Run a single test case and measure results.

        Parameters
        ----------
        test_case : dict
            {
                "query": str,
                "expected_tables": list[str],
                "expected_sql_contains": list[str],
                "expected_answer_contains": list[str],
            }
        """
        query = test_case["query"]
        result = EvalResult(
            query=query,
            expected_tables=test_case.get("expected_tables", []),
            expected_sql_contains=test_case.get("expected_sql_contains", []),
            expected_answer_contains=test_case.get("expected_answer_contains", []),
        )

        initial_state = {
            "user_query": query,
            "session_id": f"eval_{int(time.time())}",
            "discovered_tables": [],
            "selected_tables": [],
            "schema": {},
            "query_plan": {},
            "sql": "",
            "sql_history": [],
            "execution_result": None,
            "execution_error": None,
            "retry_count": 0,
            "validation_result": {},
            "summary": "",
            "confidence_score": 0.0,
            "needs_human": False,
            "final_answer": None,
            "memory_context": {},
            "error_log": [],
        }

        start_time = time.time()

        try:
            thread_config = {"configurable": {"thread_id": f"eval_{int(time.time())}"}}
            output = self.graph.invoke(initial_state, config=thread_config)

            result.latency_seconds = time.time() - start_time
            result.discovered_tables = [
                t.get("name", "") for t in output.get("discovered_tables", [])
            ]
            result.generated_sql = output.get("sql", "")
            result.execution_success = output.get("execution_error") is None
            result.retry_count = output.get("retry_count", 0)
            result.validation_passed = (
                output.get("validation_result", {}).get("overall_valid", False)
            )
            result.confidence_score = output.get("confidence_score", 0.0)
            result.summary = output.get("summary", "")
            result.human_escalated = output.get("needs_human", False)

        except Exception as e:
            result.latency_seconds = time.time() - start_time

        # Compute scores
        result.discovery_accuracy = self._compute_discovery_accuracy(result)
        result.sql_correctness = self._compute_sql_correctness(result)

        self.results.append(result)
        return result

    def run_suite(self, test_cases: List[dict]) -> dict:
        """Run a full test suite and return aggregate metrics."""
        for tc in test_cases:
            self.run_test_case(tc)
        return self.aggregate()

    def aggregate(self) -> dict:
        """Compute aggregate metrics across all results."""
        n = len(self.results)
        if n == 0:
            return {}

        return {
            "total_queries": n,
            "discovery_accuracy": (
                sum(r.discovery_accuracy for r in self.results) / n
            ),
            "sql_correctness": (
                sum(1 for r in self.results if r.execution_success) / n
            ),
            "retry_rate": (
                sum(r.retry_count for r in self.results) / n
            ),
            "validation_pass_rate": (
                sum(1 for r in self.results if r.validation_passed) / n
            ),
            "avg_latency_seconds": (
                sum(r.latency_seconds for r in self.results) / n
            ),
            "human_escalation_rate": (
                sum(1 for r in self.results if r.human_escalated) / n
            ),
            "avg_confidence": (
                sum(r.confidence_score for r in self.results) / n
            ),
        }

    def _compute_discovery_accuracy(self, result: EvalResult) -> float:
        """What fraction of expected tables were discovered?"""
        if not result.expected_tables:
            return 1.0
        found = set(t.lower() for t in result.discovered_tables)
        expected = set(t.lower() for t in result.expected_tables)
        if not expected:
            return 1.0
        return len(found & expected) / len(expected)

    def _compute_sql_correctness(self, result: EvalResult) -> float:
        """Check if SQL contains expected fragments."""
        if not result.expected_sql_contains:
            return 1.0 if result.execution_success else 0.0
        sql_lower = result.generated_sql.lower()
        matches = sum(
            1 for frag in result.expected_sql_contains
            if frag.lower() in sql_lower
        )
        return matches / len(result.expected_sql_contains)

    def report(self) -> str:
        """Generate a human-readable evaluation report."""
        agg = self.aggregate()
        lines = [
            "=" * 50,
            "  NLQ Agent Evaluation Report",
            "=" * 50,
            f"  Total queries:          {agg.get('total_queries', 0)}",
            f"  Discovery accuracy:     {agg.get('discovery_accuracy', 0):.1%}",
            f"  SQL correctness:        {agg.get('sql_correctness', 0):.1%}",
            f"  Avg retry rate:         {agg.get('retry_rate', 0):.2f}",
            f"  Validation pass rate:   {agg.get('validation_pass_rate', 0):.1%}",
            f"  Avg latency:            {agg.get('avg_latency_seconds', 0):.1f}s",
            f"  Human escalation rate:  {agg.get('human_escalation_rate', 0):.1%}",
            f"  Avg confidence:         {agg.get('avg_confidence', 0):.2f}",
            "=" * 50,
        ]
        return "\n".join(lines)
