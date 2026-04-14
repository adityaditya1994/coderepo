"""
Unit and Integration Tests for the NLQ Agent.

These tests use mocks for external services (LLM, AWS, Pinecone) so they
can run without credentials. They validate:
1. Config loading
2. State schema
3. Edge logic (should_retry, after_validation)
4. Individual agent node functions
5. Memory system (short-term, long-term)
6. Knowledge base operations
7. Validator logic (data validator)
8. Discovery connectors (flatfile)
9. Full graph compilation (integration)
10. Prompt template formatting
"""

import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import date

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════
# 1. CONFIG TESTS
# ═══════════════════════════════════════════════════

class TestConfigLoader(unittest.TestCase):
    """Test configuration loading."""

    def test_config_yaml_exists(self):
        config_path = PROJECT_ROOT / "config" / "config.yaml"
        self.assertTrue(config_path.exists(), "config.yaml must exist")

    def test_config_yaml_valid(self):
        import yaml
        config_path = PROJECT_ROOT / "config" / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        self.assertIn("llm", config)
        self.assertIn("database", config)
        self.assertIn("discovery", config)
        self.assertIn("retry", config)
        self.assertIn("memory", config)

    def test_config_loader(self):
        from config.config_loader import load_config
        config = load_config()
        self.assertIsInstance(config, dict)
        self.assertIn("llm", config)
        self.assertEqual(config["llm"]["provider"], "openai")

    def test_config_has_retry_max_attempts(self):
        from config.config_loader import load_config
        config = load_config()
        self.assertIn("max_attempts", config["retry"])
        self.assertIsInstance(config["retry"]["max_attempts"], int)
        self.assertGreater(config["retry"]["max_attempts"], 0)


# ═══════════════════════════════════════════════════
# 2. STATE SCHEMA TESTS
# ═══════════════════════════════════════════════════

class TestAgentState(unittest.TestCase):
    """Test the state TypedDict definition."""

    def test_state_importable(self):
        from graph.state import AgentState
        self.assertIsNotNone(AgentState)

    def test_state_has_required_keys(self):
        from graph.state import AgentState
        required_keys = [
            "user_query", "session_id", "discovered_tables",
            "selected_tables", "schema", "query_plan", "sql",
            "sql_history", "execution_result", "execution_error",
            "retry_count", "validation_result", "summary",
            "confidence_score", "needs_human", "final_answer",
            "memory_context", "error_log",
        ]
        annotations = AgentState.__annotations__
        for key in required_keys:
            self.assertIn(key, annotations, f"State missing key: {key}")


# ═══════════════════════════════════════════════════
# 3. EDGE LOGIC TESTS
# ═══════════════════════════════════════════════════

class TestEdgeLogic(unittest.TestCase):
    """Test conditional edge functions."""

    def test_should_retry_success(self):
        from graph.edges import should_retry
        state = {"execution_error": None, "retry_count": 0}
        self.assertEqual(should_retry(state), "validate")

    def test_should_retry_with_error(self):
        from graph.edges import should_retry
        state = {"execution_error": "column not found", "retry_count": 1}
        self.assertEqual(should_retry(state), "fix_sql")

    def test_should_retry_exhausted(self):
        from graph.edges import should_retry
        state = {"execution_error": "still failing", "retry_count": 5}
        self.assertEqual(should_retry(state), "human_fallback")

    def test_after_validation_proceed(self):
        from graph.edges import after_validation
        state = {
            "validation_result": {
                "confidence": 0.9,
                "recommendation": "proceed",
            }
        }
        self.assertEqual(after_validation(state), "summarize")

    def test_after_validation_retry(self):
        from graph.edges import after_validation
        state = {
            "validation_result": {
                "confidence": 0.6,
                "recommendation": "retry",
            }
        }
        self.assertEqual(after_validation(state), "retry")

    def test_after_validation_escalate(self):
        from graph.edges import after_validation
        state = {
            "validation_result": {
                "confidence": 0.2,
                "recommendation": "escalate",
            }
        }
        self.assertEqual(after_validation(state), "escalate")

    def test_after_validation_low_confidence_escalates(self):
        from graph.edges import after_validation
        state = {
            "validation_result": {
                "confidence": 0.1,
                "recommendation": "proceed",  # even "proceed" escalates if conf < threshold
            }
        }
        self.assertEqual(after_validation(state), "escalate")


# ═══════════════════════════════════════════════════
# 4. AGENT NODE TESTS (with mocked LLM)
# ═══════════════════════════════════════════════════

def _make_mock_llm(response_text: str):
    """Create a mock LLM that returns the given text."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.content = response_text
    mock.invoke.return_value = mock_response
    return mock


class TestSupervisorNode(unittest.TestCase):
    """Test supervisor agent."""

    def test_first_pass_returns_initial_state(self):
        from agents.supervisor import supervisor_node
        state = {"user_query": "test query", "sql": "", "error_log": []}
        config = {"retry": {"max_attempts": 3}, "human_fallback": {"confidence_threshold": 0.4}}
        llm = _make_mock_llm("")
        result = supervisor_node(state, config, llm)
        self.assertEqual(result["confidence_score"], 1.0)
        self.assertFalse(result["needs_human"])

    def test_subsequent_pass_proceed(self):
        from agents.supervisor import supervisor_node
        llm = _make_mock_llm('{"decision": "proceed", "reasoning": "all good"}')
        state = {
            "user_query": "test",
            "sql": "SELECT 1",
            "confidence_score": 0.9,
            "retry_count": 0,
            "validation_result": {"overall_valid": True},
        }
        config = {"retry": {"max_attempts": 3}, "human_fallback": {"confidence_threshold": 0.4}}
        result = supervisor_node(state, config, llm)
        self.assertFalse(result["needs_human"])

    def test_subsequent_pass_escalate(self):
        from agents.supervisor import supervisor_node
        llm = _make_mock_llm('{"decision": "escalate", "reasoning": "too many retries"}')
        state = {
            "user_query": "test",
            "sql": "SELECT 1",
            "confidence_score": 0.2,
            "retry_count": 3,
            "validation_result": {},
        }
        config = {"retry": {"max_attempts": 3}, "human_fallback": {"confidence_threshold": 0.4}}
        result = supervisor_node(state, config, llm)
        self.assertTrue(result["needs_human"])


class TestQueryPlannerNode(unittest.TestCase):
    """Test query planner agent."""

    def test_valid_json_response(self):
        from agents.query_planner import query_planner_node
        plan = {
            "intent": "aggregation",
            "metrics": [{"name": "revenue"}],
            "dimensions": [{"name": "region"}],
            "filters": [],
            "ambiguities": [],
        }
        llm = _make_mock_llm(json.dumps(plan))
        state = {
            "user_query": "total revenue by region",
            "schema": {"orders": [{"name": "revenue", "type": "double"}]},
            "memory_context": {"metrics": {}},
        }
        config = {}
        result = query_planner_node(state, config, llm)
        self.assertIn("query_plan", result)
        self.assertEqual(result["query_plan"]["intent"], "aggregation")

    def test_invalid_json_fallback(self):
        from agents.query_planner import query_planner_node
        llm = _make_mock_llm("This is not valid JSON sorry")
        state = {
            "user_query": "test",
            "schema": {},
            "memory_context": {},
        }
        result = query_planner_node(state, {}, llm)
        self.assertEqual(result["query_plan"]["intent"], "unknown")
        self.assertIn("raw_response", result["query_plan"])


class TestSQLGeneratorNode(unittest.TestCase):
    """Test SQL generator agent."""

    def test_generates_sql(self):
        from agents.sql_generator import sql_generator_node
        llm = _make_mock_llm("SELECT region, SUM(revenue) FROM orders GROUP BY region")
        state = {
            "query_plan": {"intent": "aggregation"},
            "schema": {"orders": [{"name": "revenue", "type": "double"}, {"name": "region", "type": "varchar"}]},
            "sql_history": [],
            "memory_context": {},
        }
        config = {"database": {"provider": "athena"}}
        result = sql_generator_node(state, config, llm)
        self.assertIn("sql", result)
        self.assertIn("SELECT", result["sql"])
        self.assertEqual(len(result["sql_history"]), 1)

    def test_sql_history_appends(self):
        from agents.sql_generator import sql_generator_node
        llm = _make_mock_llm("SELECT 1")
        state = {
            "query_plan": {},
            "schema": {},
            "sql_history": ["SELECT 0"],
            "memory_context": {},
        }
        config = {"database": {"provider": "athena"}}
        result = sql_generator_node(state, config, llm)
        self.assertEqual(len(result["sql_history"]), 2)


class TestSQLFixerNode(unittest.TestCase):
    """Test SQL fixer agent."""

    def test_classify_and_fix(self):
        from agents.sql_fixer import sql_fixer_node
        classification = '{"error_type": "MISSING_COLUMN", "affected_part": "SELECT revnue", "root_cause": "typo", "fix_hint": "change to revenue"}'
        fixed_sql = "SELECT SUM(o.revenue) FROM orders o"

        call_count = [0]
        def side_effect(prompt):
            call_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.content = classification if call_count[0] == 1 else fixed_sql
            return mock_resp

        llm = MagicMock()
        llm.invoke.side_effect = side_effect

        state = {
            "sql": "SELECT SUM(o.revnue) FROM orders o",
            "execution_error": "Column 'revnue' not found",
            "schema": {"orders": [{"name": "revenue", "type": "double"}]},
            "sql_history": [],
            "error_log": [],
        }
        config = {}
        result = sql_fixer_node(state, config, llm)
        self.assertIn("revenue", result["sql"])
        self.assertIsNone(result["execution_error"])
        self.assertEqual(len(result["error_log"]), 1)


class TestExecutorNode(unittest.TestCase):
    """Test executor agent."""

    def test_no_sql_returns_error(self):
        from agents.executor.executor_agent import executor_node
        state = {"sql": "", "retry_count": 0}
        config = {}
        result = executor_node(state, config)
        self.assertIsNotNone(result["execution_error"])
        self.assertIsNone(result["execution_result"])

    @patch("agents.executor.executor_agent.get_executor")
    def test_successful_execution(self, mock_get_executor):
        from agents.executor.executor_agent import executor_node
        mock_exec = MagicMock()
        mock_exec.execute.return_value = {
            "columns": ["region", "revenue"],
            "rows": [["NA", "1000"], ["EMEA", "2000"]],
            "row_count": 2,
        }
        mock_get_executor.return_value = mock_exec
        state = {"sql": "SELECT 1", "retry_count": 0}
        config = {"database": {"provider": "athena", "athena": {}}}
        result = executor_node(state, config)
        self.assertIsNone(result["execution_error"])
        self.assertEqual(result["execution_result"]["row_count"], 2)

    @patch("agents.executor.executor_agent.get_executor")
    def test_execution_error_increments_retry(self, mock_get_executor):
        from agents.executor.executor_agent import executor_node
        mock_exec = MagicMock()
        mock_exec.execute.side_effect = Exception("table not found")
        mock_get_executor.return_value = mock_exec
        state = {"sql": "SELECT 1", "retry_count": 1}
        config = {"database": {"provider": "athena", "athena": {}}}
        result = executor_node(state, config)
        self.assertIsNotNone(result["execution_error"])
        self.assertEqual(result["retry_count"], 2)


class TestHumanHandoff(unittest.TestCase):
    """Test human handoff agent."""

    def test_produces_handoff(self):
        from agents.human_handoff import human_handoff_node
        state = {
            "user_query": "test query",
            "sql": "SELECT 1",
            "sql_history": ["SELECT 1"],
            "execution_error": "failed",
            "retry_count": 3,
            "validation_result": {},
            "error_log": ["Error 1"],
            "confidence_score": 0.2,
        }
        result = human_handoff_node(state, {})
        self.assertTrue(result["needs_human"])
        self.assertIn("HUMAN REVIEW REQUIRED", result["final_answer"])


class TestSummarizerNode(unittest.TestCase):
    """Test summarizer agent."""

    def test_summarizes_results(self):
        from agents.summarizer import summarizer_node
        llm = _make_mock_llm("Total revenue was $4.2M across all regions.")
        state = {
            "user_query": "what is total revenue by region?",
            "execution_result": {
                "columns": ["region", "revenue"],
                "rows": [["NA", "4200000"]],
            },
            "sql": "SELECT region, SUM(revenue) FROM orders GROUP BY region",
            "query_plan": {"intent": "aggregation"},
            "confidence_score": 0.9,
        }
        result = summarizer_node(state, {}, llm)
        self.assertIn("summary", result)
        self.assertIn("final_answer", result)
        self.assertIn("$4.2M", result["summary"])


# ═══════════════════════════════════════════════════
# 5. MEMORY SYSTEM TESTS
# ═══════════════════════════════════════════════════

class TestShortTermMemory(unittest.TestCase):
    """Test in-memory session store."""

    def test_set_and_get(self):
        from memory.short_term import ShortTermMemory
        mem = ShortTermMemory()
        mem.set("s1", "key1", "value1")
        self.assertEqual(mem.get("s1", "key1"), "value1")

    def test_get_missing_key(self):
        from memory.short_term import ShortTermMemory
        mem = ShortTermMemory()
        self.assertIsNone(mem.get("s1", "missing"))
        self.assertEqual(mem.get("s1", "missing", "default"), "default")

    def test_append(self):
        from memory.short_term import ShortTermMemory
        mem = ShortTermMemory()
        mem.append("s1", "history", "item1")
        mem.append("s1", "history", "item2")
        self.assertEqual(mem.get("s1", "history"), ["item1", "item2"])

    def test_clear_session(self):
        from memory.short_term import ShortTermMemory
        mem = ShortTermMemory()
        mem.set("s1", "key1", "value1")
        mem.clear("s1")
        self.assertIsNone(mem.get("s1", "key1"))

    def test_session_isolation(self):
        from memory.short_term import ShortTermMemory
        mem = ShortTermMemory()
        mem.set("s1", "key1", "value1")
        mem.set("s2", "key1", "value2")
        self.assertEqual(mem.get("s1", "key1"), "value1")
        self.assertEqual(mem.get("s2", "key1"), "value2")


class TestLongTermMemory(unittest.TestCase):
    """Test SQLite-backed query history."""

    def setUp(self):
        self.db_path = "/tmp/test_query_history.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_store_and_search(self):
        from memory.long_term import LongTermMemory
        mem = LongTermMemory(db_path=self.db_path)
        state = {
            "session_id": "test-session",
            "user_query": "total revenue by region",
            "query_plan": {"intent": "aggregation"},
            "sql": "SELECT region, SUM(revenue) FROM orders GROUP BY region",
            "execution_error": None,
            "retry_count": 0,
            "validation_result": {"overall_valid": True},
            "summary": "Revenue was $4M",
            "confidence_score": 0.9,
        }
        mem.store(state, feedback="correct")
        results = mem.search("revenue")
        self.assertEqual(len(results), 1)
        self.assertIn("revenue", results[0]["user_query"])

    def test_get_recent(self):
        from memory.long_term import LongTermMemory
        mem = LongTermMemory(db_path=self.db_path)
        for i in range(3):
            state = {
                "session_id": "s1",
                "user_query": f"query {i}",
                "query_plan": {},
                "sql": f"SELECT {i}",
                "execution_error": None,
                "retry_count": 0,
                "validation_result": {},
                "summary": "",
                "confidence_score": 0.8,
            }
            mem.store(state)
        recent = mem.get_recent(limit=2)
        self.assertEqual(len(recent), 2)


# ═══════════════════════════════════════════════════
# 6. KNOWLEDGE BASE TESTS
# ═══════════════════════════════════════════════════

class TestMetricsStore(unittest.TestCase):
    """Test metrics knowledge base."""

    def test_load_default_metrics(self):
        from knowledge_base.metrics_store import MetricsStore
        store = MetricsStore()
        metrics = store.get_all()
        self.assertIn("revenue", metrics)
        self.assertIn("active_users", metrics)

    def test_lookup_existing(self):
        from knowledge_base.metrics_store import MetricsStore
        store = MetricsStore()
        revenue = store.lookup("revenue")
        self.assertIsNotNone(revenue)
        self.assertTrue(revenue["approved"])

    def test_lookup_missing(self):
        from knowledge_base.metrics_store import MetricsStore
        store = MetricsStore()
        result = store.lookup("nonexistent_metric")
        self.assertIsNone(result)

    def test_get_approved(self):
        from knowledge_base.metrics_store import MetricsStore
        store = MetricsStore()
        approved = store.get_approved()
        for name, defn in approved.items():
            self.assertTrue(defn["approved"])


# ═══════════════════════════════════════════════════
# 7. DATA VALIDATOR TESTS
# ═══════════════════════════════════════════════════

class TestDataValidator(unittest.TestCase):
    """Test rule-based data sanity validator."""

    def test_valid_data_passes(self):
        from agents.validation.data_validator import DataValidator
        val = DataValidator()
        result = val.validate({
            "columns": ["region", "revenue"],
            "rows": [["NA", "1000"], ["EMEA", "2000"], ["APAC", "1500"]],
            "row_count": 3,
        })
        self.assertTrue(result["passed"])

    def test_empty_result_fails(self):
        from agents.validation.data_validator import DataValidator
        val = DataValidator()
        result = val.validate({"columns": ["a"], "rows": [], "row_count": 0})
        self.assertFalse(result["passed"])
        self.assertTrue(any("empty" in i.lower() for i in result["issues"]))

    def test_excessive_nulls_flagged(self):
        from agents.validation.data_validator import DataValidator
        val = DataValidator()
        result = val.validate({
            "columns": ["id", "value"],
            "rows": [["1", None], ["2", None], ["3", None], ["4", "100"]],
            "row_count": 4,
        })
        self.assertFalse(result["passed"])
        self.assertTrue(any("NULL" in i for i in result["issues"]))

    def test_negative_revenue_flagged(self):
        from agents.validation.data_validator import DataValidator
        val = DataValidator()
        result = val.validate({
            "columns": ["customer", "revenue"],
            "rows": [["Acme", "-500"], ["Beta", "1000"]],
            "row_count": 2,
        })
        self.assertFalse(result["passed"])
        self.assertTrue(any("negative" in i.lower() for i in result["issues"]))

    def test_no_result_fails(self):
        from agents.validation.data_validator import DataValidator
        val = DataValidator()
        result = val.validate(None)
        self.assertFalse(result["passed"])


class TestSchemaValidator(unittest.TestCase):
    """Test schema validation."""

    def test_basic_validation(self):
        from agents.validation.schema_validator import SchemaValidator
        val = SchemaValidator()
        result = val.validate(
            "SELECT region FROM orders",
            {"orders": [{"name": "region", "type": "varchar"}]}
        )
        # orders is referenced in SQL
        self.assertTrue(result["passed"])


# ═══════════════════════════════════════════════════
# 8. FLATFILE CONNECTOR TESTS
# ═══════════════════════════════════════════════════

class TestFlatFileConnector(unittest.TestCase):
    """Test flat file discovery connector."""

    def setUp(self):
        self.catalog_path = "/tmp/test_table_catalog.json"
        catalog = [
            {
                "name": "orders",
                "database": "analytics_db",
                "columns": [
                    {"name": "order_id", "type": "bigint"},
                    {"name": "revenue", "type": "double"},
                    {"name": "region", "type": "varchar"},
                ],
                "description": "All customer orders with revenue",
                "tags": ["orders", "revenue", "sales"],
            },
            {
                "name": "customers",
                "database": "analytics_db",
                "columns": [
                    {"name": "customer_id", "type": "bigint"},
                    {"name": "name", "type": "varchar"},
                ],
                "description": "Customer master data",
                "tags": ["customers"],
            },
        ]
        with open(self.catalog_path, "w") as f:
            json.dump(catalog, f)

    def tearDown(self):
        if os.path.exists(self.catalog_path):
            os.remove(self.catalog_path)

    def test_search_finds_relevant_table(self):
        from agents.discovery.flatfile_connector import FlatFileConnector
        conn = FlatFileConnector(catalog_path=self.catalog_path)
        results = conn.search("revenue by region")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["name"], "orders")  # best match

    def test_search_no_match(self):
        from agents.discovery.flatfile_connector import FlatFileConnector
        conn = FlatFileConnector(catalog_path=self.catalog_path)
        results = conn.search("xyznonexistent")
        self.assertEqual(len(results), 0)

    def test_missing_catalog_returns_empty(self):
        from agents.discovery.flatfile_connector import FlatFileConnector
        conn = FlatFileConnector(catalog_path="/tmp/does_not_exist.json")
        results = conn.search("anything")
        self.assertEqual(len(results), 0)


# ═══════════════════════════════════════════════════
# 9. PROMPT TEMPLATE TESTS
# ═══════════════════════════════════════════════════

class TestPromptTemplates(unittest.TestCase):
    """Test that all prompt templates format without errors."""

    def test_supervisor_prompt_formats(self):
        from prompts.supervisor import SUPERVISOR_DECISION_PROMPT
        result = SUPERVISOR_DECISION_PROMPT.format(
            user_query="test",
            confidence_score=0.8,
            retry_count=0,
            max_retries=3,
            validation_result="{}",
            issues="[]",
        )
        self.assertIn("test", result)

    def test_discovery_prompt_formats(self):
        from prompts.discovery import DISCOVERY_COUNCIL_PROMPT
        result = DISCOVERY_COUNCIL_PROMPT.format(
            user_query="revenue by region",
            candidates="[]",
            top_k=5,
        )
        self.assertIn("revenue", result)

    def test_query_planner_prompt_formats(self):
        from prompts.query_planner import QUERY_PLANNER_PROMPT
        result = QUERY_PLANNER_PROMPT.format(
            user_query="revenue",
            schema="{}",
            metrics_context="{}",
            today_date="2024-04-15",
        )
        self.assertIn("2024-04-15", result)

    def test_sql_generator_prompt_formats(self):
        from prompts.sql_generator import SQL_GENERATOR_PROMPT
        result = SQL_GENERATOR_PROMPT.format(
            dialect="Presto/Athena SQL",
            query_plan="{}",
            schema="{}",
            join_map="{}",
            memory_context="None available",
        )
        self.assertIn("Presto", result)

    def test_error_classifier_prompt_formats(self):
        from prompts.sql_fixer import ERROR_CLASSIFIER_PROMPT
        result = ERROR_CLASSIFIER_PROMPT.format(
            sql="SELECT 1",
            error="column not found",
            schema="{}",
        )
        self.assertIn("column not found", result)

    def test_sql_fixer_prompt_formats(self):
        from prompts.sql_fixer import SQL_FIXER_PROMPT
        result = SQL_FIXER_PROMPT.format(
            error_type="MISSING_COLUMN",
            affected_part="SELECT",
            root_cause="typo",
            fix_hint="fix name",
            sql="SELECT revnue",
            error="column not found",
            schema="{}",
            sql_history="None",
        )
        self.assertIn("MISSING_COLUMN", result)

    def test_validator_prompt_formats(self):
        from prompts.validator import VALIDATION_COUNCIL_PROMPT
        result = VALIDATION_COUNCIL_PROMPT.format(
            user_query="test",
            query_plan="{}",
            sql="SELECT 1",
            result_sample="no data",
            metrics_context="{}",
        )
        self.assertIn("SCHEMA", result)

    def test_summarizer_prompt_formats(self):
        from prompts.summarizer import SUMMARIZER_PROMPT
        result = SUMMARIZER_PROMPT.format(
            user_query="test",
            result="data",
            sql="SELECT 1",
            query_plan="{}",
            confidence="0.85",
        )
        self.assertIn("test", result)


# ═══════════════════════════════════════════════════
# 10. INTEGRATION: GRAPH COMPILATION
# ═══════════════════════════════════════════════════

class TestGraphCompilation(unittest.TestCase):
    """Integration test: the full graph compiles without errors."""

    def test_graph_compiles(self):
        try:
            import graph.graph_builder as gb
            from config.config_loader import load_config
            config = load_config()

            original_get_llm = gb.get_llm
            original_memory = gb.MemorySaver
            try:
                gb.get_llm = lambda cfg: MagicMock()
                gb.MemorySaver = MagicMock
                graph = gb.build_graph(config)
                self.assertIsNotNone(graph)
            finally:
                gb.get_llm = original_get_llm
                gb.MemorySaver = original_memory
        except ImportError as e:
            self.skipTest(f"langgraph not available: {e}")

    def test_graph_has_all_nodes(self):
        try:
            import graph.graph_builder as gb
            from config.config_loader import load_config
            config = load_config()

            original_get_llm = gb.get_llm
            original_memory = gb.MemorySaver
            try:
                gb.get_llm = lambda cfg: MagicMock()
                gb.MemorySaver = MagicMock
                graph = gb.build_graph(config)

                expected_nodes = [
                    "supervisor", "discovery", "schema_retriever",
                    "query_planner", "sql_generator", "executor",
                    "sql_fixer", "validator", "summarizer",
                    "human_handoff", "memory_writer",
                ]
                graph_obj = graph.get_graph()
                node_ids = [n.id for n in graph_obj.nodes]
                for node_name in expected_nodes:
                    self.assertIn(
                        node_name, node_ids,
                        f"Graph missing node: {node_name}"
                    )
            finally:
                gb.get_llm = original_get_llm
                gb.MemorySaver = original_memory
        except ImportError as e:
            self.skipTest(f"langgraph not available: {e}")


# ═══════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
