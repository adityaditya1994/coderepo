"""
Cross-agent contract tests — verify that Agent A's output
can be fed as Agent B's input without errors.

Tests the 6 agent-to-agent boundaries:
  discovery → schema_retriever
  schema_retriever → query_planner
  query_planner → sql_generator
  sql_generator → executor
  executor → validation_council
  validation_council → summarizer
"""

import pytest
import sys
from pathlib import Path

# Ensure nlq_agent is importable
NLQ_ROOT = Path(__file__).parent.parent
if str(NLQ_ROOT) not in sys.path:
    sys.path.insert(0, str(NLQ_ROOT))

from contracts import (
    DiscoveryOutput,
    SchemaRetrieverInput,
    SchemaRetrieverOutput,
    QueryPlannerInput,
    QueryPlannerOutput,
    SqlGeneratorInput,
    SqlGeneratorOutput,
    ExecutorInput,
    ExecutorOutput,
    ValidationCouncilInput,
    ValidationCouncilOutput,
    SummarizerInput,
)


# ── Fixtures: realistic agent outputs ──

@pytest.fixture
def discovery_output():
    """Realistic discovery agent output."""
    return {
        "discovered_tables": [
            {
                "name": "orders",
                "database": "ecommerce_analytics",
                "source": "flatfile",
                "score": 0.9,
                "columns": [
                    {"name": "order_id", "type": "bigint"},
                    {"name": "order_date", "type": "date"},
                    {"name": "total_amount", "type": "double"},
                    {"name": "region_id", "type": "int"},
                    {"name": "status", "type": "varchar"},
                ],
            },
            {
                "name": "regions",
                "database": "ecommerce_analytics",
                "source": "flatfile",
                "score": 0.7,
                "columns": [
                    {"name": "region_id", "type": "int"},
                    {"name": "region_name", "type": "varchar"},
                ],
            },
        ],
        "memory_context": {"session": {}, "past_queries": []},
        "user_query": "total revenue by region",
        "session_id": "test-001",
    }


@pytest.fixture
def schema_retriever_output(discovery_output):
    """Realistic schema retriever output."""
    return {
        **discovery_output,
        "schema": {
            "orders": [
                {"name": "order_id", "type": "bigint"},
                {"name": "order_date", "type": "date"},
                {"name": "total_amount", "type": "double"},
                {"name": "region_id", "type": "int"},
                {"name": "status", "type": "varchar"},
            ],
            "regions": [
                {"name": "region_id", "type": "int"},
                {"name": "region_name", "type": "varchar"},
            ],
        },
        "selected_tables": ["orders", "regions"],
    }


@pytest.fixture
def query_planner_output(schema_retriever_output):
    """Realistic query planner output."""
    return {
        **schema_retriever_output,
        "query_plan": {
            "objective": "Total revenue by region",
            "tables": ["orders", "regions"],
            "joins": [{"left": "orders.region_id", "right": "regions.region_id", "type": "INNER"}],
            "filters": [{"column": "status", "op": "=", "value": "completed"}],
            "aggregations": [{"function": "SUM", "column": "total_amount", "alias": "total_revenue"}],
            "group_by": ["regions.region_name"],
        },
    }


@pytest.fixture
def sql_generator_output(query_planner_output):
    """Realistic SQL generator output."""
    return {
        **query_planner_output,
        "sql": "SELECT r.region_name, SUM(o.total_amount) AS total_revenue FROM orders o JOIN regions r ON o.region_id = r.region_id WHERE o.status = 'completed' GROUP BY r.region_name ORDER BY total_revenue DESC",
        "sql_history": ["SELECT r.region_name, SUM(o.total_amount) ..."],
    }


@pytest.fixture
def executor_output(sql_generator_output):
    """Realistic executor output (success)."""
    return {
        **sql_generator_output,
        "execution_result": {
            "columns": ["region_name", "total_revenue"],
            "rows": [["APAC", 3549.96], ["North America", 1919.92]],
            "row_count": 2,
        },
        "execution_error": None,
        "retry_count": 0,
    }


@pytest.fixture
def validation_output(executor_output):
    """Realistic validation council output."""
    return {
        **executor_output,
        "validation_result": {
            "overall_valid": True,
            "confidence": 0.95,
            "recommendation": "proceed",
            "issues": [],
        },
        "confidence_score": 0.95,
    }


# ── Tests ──

class TestDiscoveryToSchemaRetriever:
    def test_contract_valid(self, discovery_output):
        """Discovery output can be deserialized and fed to schema retriever."""
        out = DiscoveryOutput.from_state(discovery_output)
        assert len(out.discovered_tables) == 2
        inp = SchemaRetrieverInput.from_discovery(out)
        assert len(inp.discovered_tables) == 2
        assert inp.discovered_tables[0]["name"] == "orders"

    def test_to_state_roundtrip(self, discovery_output):
        """to_state produces valid dict."""
        out = DiscoveryOutput.from_state(discovery_output)
        state_dict = out.to_state()
        assert "discovered_tables" in state_dict
        assert "memory_context" in state_dict


class TestSchemaRetrieverToQueryPlanner:
    def test_contract_valid(self, schema_retriever_output):
        """Schema retriever output feeds query planner input."""
        out = SchemaRetrieverOutput.from_state(schema_retriever_output)
        assert "orders" in out.schema
        assert "regions" in out.selected_tables
        inp = QueryPlannerInput.from_schema_retriever(schema_retriever_output)
        assert inp.user_query == "total revenue by region"
        assert len(inp.selected_tables) == 2


class TestQueryPlannerToSqlGenerator:
    def test_contract_valid(self, query_planner_output):
        """Query planner output feeds SQL generator input."""
        out = QueryPlannerOutput.from_state(query_planner_output)
        assert "objective" in out.query_plan
        inp = SqlGeneratorInput.from_query_planner(query_planner_output)
        assert inp.query_plan["tables"] == ["orders", "regions"]
        assert len(inp.sql_history) == 0


class TestSqlGeneratorToExecutor:
    def test_contract_valid(self, sql_generator_output):
        """SQL generator output feeds executor input."""
        out = SqlGeneratorOutput.from_state(sql_generator_output)
        assert "SELECT" in out.sql
        inp = ExecutorInput.from_sql_generator(sql_generator_output)
        assert inp.sql != ""
        assert inp.retry_count == 0


class TestExecutorToValidation:
    def test_contract_valid(self, executor_output):
        """Executor output feeds validation council input."""
        out = ExecutorOutput.from_state(executor_output)
        assert out.execution_error is None
        assert out.execution_result["row_count"] == 2
        inp = ValidationCouncilInput.from_executor(executor_output)
        assert "SELECT" in inp.sql
        assert inp.execution_result is not None


class TestValidationToSummarizer:
    def test_contract_valid(self, validation_output):
        """Validation council output feeds summarizer input."""
        out = ValidationCouncilOutput.from_state(validation_output)
        assert out.confidence_score == 0.95
        assert out.validation_result["recommendation"] == "proceed"
        inp = SummarizerInput.from_validation(validation_output)
        assert inp.confidence_score == 0.95
        assert inp.user_query == "total revenue by region"


class TestFullChain:
    def test_contracts_chain_no_errors(self, discovery_output):
        """Full contract chain from discovery → summarizer without errors."""
        # Discovery → SchemaRetriever
        d_out = DiscoveryOutput.from_state(discovery_output)
        sr_in = SchemaRetrieverInput.from_discovery(d_out)
        assert sr_in.discovered_tables

        # SchemaRetriever → QueryPlanner
        sr_state = {**discovery_output, "schema": {"orders": [{"name": "order_id", "type": "bigint"}]}, "selected_tables": ["orders"]}
        sr_out = SchemaRetrieverOutput.from_state(sr_state)
        qp_in = QueryPlannerInput.from_schema_retriever(sr_state)
        assert qp_in.schema

        # QueryPlanner → SqlGenerator
        qp_state = {**sr_state, "query_plan": {"objective": "test"}}
        qp_out = QueryPlannerOutput.from_state(qp_state)
        sg_in = SqlGeneratorInput.from_query_planner(qp_state)
        assert sg_in.query_plan

        # SqlGenerator → Executor
        sg_state = {**qp_state, "sql": "SELECT 1", "sql_history": []}
        sg_out = SqlGeneratorOutput.from_state(sg_state)
        ex_in = ExecutorInput.from_sql_generator(sg_state)
        assert ex_in.sql

        # Executor → Validator
        ex_state = {**sg_state, "execution_result": {"columns": ["x"], "rows": [[1]], "row_count": 1}, "execution_error": None, "retry_count": 0}
        ex_out = ExecutorOutput.from_state(ex_state)
        vc_in = ValidationCouncilInput.from_executor(ex_state)
        assert vc_in.execution_result

        # Validator → Summarizer
        vc_state = {**ex_state, "validation_result": {"overall_valid": True, "confidence": 0.9, "recommendation": "proceed"}, "confidence_score": 0.9}
        vc_out = ValidationCouncilOutput.from_state(vc_state)
        sum_in = SummarizerInput.from_validation(vc_state)
        assert sum_in.confidence_score == 0.9
