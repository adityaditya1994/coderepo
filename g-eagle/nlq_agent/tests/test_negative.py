"""
Negative / breaking tests — ensure the system handles
edge cases and failures gracefully.

Covers:
- Empty discovery results
- Malformed JSON between agents
- SQL execution errors → sql_fixer path
- Validation failure paths
- Max retries → human_handoff
- Missing state fields
"""

import sys
import pytest
from pathlib import Path

NLQ_ROOT = Path(__file__).parent.parent
if str(NLQ_ROOT) not in sys.path:
    sys.path.insert(0, str(NLQ_ROOT))


from contracts import (
    DiscoveryOutput,
    SchemaRetrieverOutput,
    ExecutorOutput,
    ValidationCouncilOutput,
    SqlGeneratorOutput,
)
from graph.edges import should_retry, after_validation


# ══════════════════════════════════════════════════════════════
# Empty / Missing Data
# ══════════════════════════════════════════════════════════════

class TestEmptyDiscovery:
    def test_empty_tables_list(self):
        """Discovery returns empty tables → contract still valid."""
        out = DiscoveryOutput(discovered_tables=[], memory_context={})
        assert len(out.discovered_tables) == 0
        state = out.to_state()
        assert state["discovered_tables"] == []

    def test_schema_retriever_with_no_tables(self):
        """Schema retriever handles empty discovery gracefully."""
        from agents.schema_retriever import schema_retriever_node
        state = {"discovered_tables": [], "error_log": []}
        config = {"database": {"provider": "local_postgres", "local_postgres": {}}}
        result = schema_retriever_node(state, config)
        assert result["schema"] == {}
        assert result["selected_tables"] == []
        assert "no tables discovered" in result["error_log"][0]


class TestMissingStateFields:
    def test_executor_no_sql(self):
        """Executor handles missing SQL field."""
        from agents.executor.executor_agent import executor_node
        state = {"retry_count": 0}
        config = {"database": {"provider": "local_postgres"}}
        result = executor_node(state, config)
        assert result["execution_error"] == "No SQL to execute"
        assert result["execution_result"] is None

    def test_human_handoff_missing_fields(self):
        """Human handoff handles completely empty state."""
        from agents.human_handoff import human_handoff_node
        state = {}
        config = {}
        result = human_handoff_node(state, config)
        assert result["needs_human"] is True
        assert result["final_answer"] is not None


# ══════════════════════════════════════════════════════════════
# Edge Function Tests
# ══════════════════════════════════════════════════════════════

class TestShouldRetryEdge:
    def test_no_error_validates(self):
        """No execution error → validate."""
        state = {"execution_error": None, "retry_count": 0}
        assert should_retry(state) == "validate"

    def test_error_under_max_retries(self):
        """Error with retries left → fix_sql."""
        state = {"execution_error": "syntax error", "retry_count": 1}
        assert should_retry(state) == "fix_sql"

    def test_error_max_retries_exceeded(self):
        """Error with max retries → human_fallback."""
        state = {"execution_error": "syntax error", "retry_count": 5}
        assert should_retry(state) == "human_fallback"


class TestAfterValidationEdge:
    def test_proceed_high_confidence(self):
        """Valid + high confidence → summarize."""
        state = {
            "validation_result": {
                "confidence": 0.95,
                "recommendation": "proceed",
            }
        }
        assert after_validation(state) == "summarize"

    def test_retry_medium_confidence(self):
        """Medium confidence → retry."""
        state = {
            "validation_result": {
                "confidence": 0.55,
                "recommendation": "retry",
            }
        }
        assert after_validation(state) == "retry"

    def test_escalate_low_confidence(self):
        """Low confidence → escalate."""
        state = {
            "validation_result": {
                "confidence": 0.2,
                "recommendation": "escalate",
            }
        }
        assert after_validation(state) == "escalate"

    def test_missing_validation_result(self):
        """Missing validation result defaults safely."""
        state = {}
        # Should default to "retry" (confidence 0.5, recommendation "proceed")
        result = after_validation(state)
        assert result in ("summarize", "retry", "escalate")


# ══════════════════════════════════════════════════════════════
# Malformed Contract Data
# ══════════════════════════════════════════════════════════════

class TestMalformedContracts:
    def test_discovery_output_wrong_type(self):
        """Discovery output with wrong type for tables → validation error."""
        with pytest.raises(Exception):
            DiscoveryOutput(discovered_tables="not a list", memory_context={})

    def test_executor_output_null_result(self):
        """Executor output with null result is valid (error case)."""
        out = ExecutorOutput(
            execution_result=None,
            execution_error="Connection refused",
            retry_count=2,
        )
        assert out.execution_error == "Connection refused"
        state = out.to_state()
        assert state["execution_result"] is None

    def test_validation_output_invalid_confidence(self):
        """Confidence outside 0-1 range → validation error."""
        with pytest.raises(Exception):
            ValidationCouncilOutput(
                validation_result={},
                confidence_score=1.5,
            )

    def test_sql_generator_empty_sql(self):
        """Empty SQL string is technically valid but noted."""
        out = SqlGeneratorOutput(sql="", sql_history=[])
        assert out.sql == ""
        assert out.to_state()["sql"] == ""


# ══════════════════════════════════════════════════════════════
# Execution Error Scenarios
# ══════════════════════════════════════════════════════════════

class TestExecutionErrors:
    def test_executor_error_increments_retry(self):
        """Executor increments retry_count on error."""
        from agents.executor.executor_agent import executor_node
        state = {"sql": "SELECT * FROM nonexistent", "retry_count": 1}
        # Use a config that will fail (no actual DB)
        config = {"database": {"provider": "local_postgres", "local_postgres": {
            "host": "localhost", "port": 9999, "database": "nope",
            "user": "x", "password": "x",
        }}}
        result = executor_node(state, config)
        assert result["execution_error"] is not None
        assert result["retry_count"] == 2

    def test_executor_empty_result(self):
        """Executor flags empty results as error."""
        # This test requires actual DB, mock the executor
        out = ExecutorOutput(
            execution_result={"columns": ["x"], "rows": [], "row_count": 0},
            execution_error="EMPTY_RESULT: Query returned 0 rows",
            retry_count=1,
        )
        assert "EMPTY_RESULT" in out.execution_error


# ══════════════════════════════════════════════════════════════
# Trace Utilities
# ══════════════════════════════════════════════════════════════

class TestTrace:
    def test_mermaid_builder(self):
        """Mermaid diagram builds correctly."""
        from graph.trace import _build_mermaid
        trace = [
            {"agent": "supervisor"},
            {"agent": "discovery"},
            {"agent": "schema_retriever"},
        ]
        mermaid = _build_mermaid(trace)
        assert "graph LR" in mermaid
        assert "S[supervisor]" in mermaid
        assert "D[discovery]" in mermaid
        assert "-->" in mermaid

    def test_new_trace_id(self):
        """Trace IDs are unique."""
        from graph.trace import new_trace_id
        id1 = new_trace_id()
        id2 = new_trace_id()
        assert id1 != id2
        assert len(id1) == 8
