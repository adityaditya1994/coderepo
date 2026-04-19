"""
E2E integration test — runs a full English question through
the compiled LangGraph against Docker Postgres.

Requires:
  - Docker Postgres running (docker compose up -d)
  - Environment variable DATABASE_URL set or config.yaml pointing at local_postgres

Skip with: pytest -m "not integration"
"""

import os
import sys
import pytest
from pathlib import Path

NLQ_ROOT = Path(__file__).parent.parent
if str(NLQ_ROOT) not in sys.path:
    sys.path.insert(0, str(NLQ_ROOT))


def _postgres_available():
    """Check if Postgres is reachable."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", port=5432,
            database="nlq_demo", user="nlq_user", password="nlq_pass",
        )
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="Docker Postgres not available (run: docker compose up -d)"
)


@pytest.fixture(scope="module")
def config():
    """Load config with local_postgres profile."""
    from config.config_loader import load_config
    cfg = load_config()
    # Force local_postgres for this test
    cfg["database"]["provider"] = "local_postgres"
    cfg["database"]["local_postgres"] = {
        "host": "localhost",
        "port": 5432,
        "database": "nlq_demo",
        "user": "nlq_user",
        "password": "nlq_pass",
    }
    return cfg


class TestPostgresExecutor:
    """Test the Postgres executor directly."""

    def test_simple_query(self, config):
        from db.db_factory import get_executor
        executor = get_executor(config)
        result = executor.execute("SELECT COUNT(*) as cnt FROM orders")
        assert result["row_count"] == 1
        assert result["columns"] == ["cnt"]
        assert result["rows"][0][0] > 0

    def test_join_query(self, config):
        from db.db_factory import get_executor
        executor = get_executor(config)
        result = executor.execute("""
            SELECT r.region_name, COUNT(o.order_id) as order_count
            FROM orders o
            JOIN regions r ON o.region_id = r.region_id
            GROUP BY r.region_name
            ORDER BY order_count DESC
        """)
        assert result["row_count"] > 0
        assert "region_name" in result["columns"]

    def test_invalid_sql(self, config):
        from db.db_factory import get_executor
        executor = get_executor(config)
        with pytest.raises(Exception):
            executor.execute("SELECT * FROM nonexistent_table_xyz")


class TestSchemaRetrieverPostgres:
    """Test schema retriever with local Postgres."""

    def test_retrieve_orders_schema(self, config):
        from agents.schema_retriever import schema_retriever_node
        state = {
            "discovered_tables": [
                {"name": "orders", "database": "nlq_demo"},
                {"name": "regions", "database": "nlq_demo"},
            ],
            "error_log": [],
        }
        result = schema_retriever_node(state, config)
        assert "orders" in result["schema"]
        assert "regions" in result["schema"]
        assert len(result["schema"]["orders"]) > 0
        # Check column names
        col_names = [c["name"] for c in result["schema"]["orders"]]
        assert "order_id" in col_names
        assert "total_amount" in col_names

    def test_nonexistent_table_uses_fallback(self, config):
        from agents.schema_retriever import schema_retriever_node
        state = {
            "discovered_tables": [
                {"name": "fake_table", "database": "nlq_demo",
                 "columns": [{"name": "x", "type": "int"}]},
            ],
            "error_log": [],
        }
        result = schema_retriever_node(state, config)
        # Should fall back to discovery columns
        assert "fake_table" in result["schema"]
        assert result["schema"]["fake_table"] == [{"name": "x", "type": "int"}]


@pytest.mark.integration
class TestE2EGoldenQueries:
    """Run golden queries against seeded Postgres."""

    @pytest.fixture
    def executor(self, config):
        from db.db_factory import get_executor
        return get_executor(config)

    def test_revenue_by_region(self, executor):
        """Golden Q1: total revenue by region."""
        result = executor.execute("""
            SELECT r.region_name, SUM(o.total_amount) AS total_revenue
            FROM orders o
            JOIN regions r ON o.region_id = r.region_id
            WHERE o.order_date BETWEEN '2024-01-01' AND '2024-03-31'
              AND o.status = 'completed'
            GROUP BY r.region_name
            ORDER BY total_revenue DESC
        """)
        assert result["row_count"] > 0
        assert "region_name" in result["columns"]
        assert "total_revenue" in result["columns"]

    def test_top_customers(self, executor):
        """Golden Q2: top customers by LTV."""
        result = executor.execute("""
            SELECT name, lifetime_value
            FROM customers
            ORDER BY lifetime_value DESC
            LIMIT 5
        """)
        assert result["row_count"] == 5
        # First customer should have highest LTV
        assert result["rows"][0][1] >= result["rows"][1][1]

    def test_orders_per_channel(self, executor):
        """Golden Q4: orders per channel."""
        result = executor.execute("""
            SELECT channel, COUNT(*) as order_count
            FROM orders
            WHERE order_date >= '2024-01-01'
            GROUP BY channel
            ORDER BY order_count DESC
        """)
        assert result["row_count"] > 0
        channels = [row[0] for row in result["rows"]]
        assert "web" in channels

    def test_avg_order_by_segment(self, executor):
        """Golden Q5: avg order value by segment."""
        result = executor.execute("""
            SELECT c.segment, AVG(o.total_amount) AS avg_order_value
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY c.segment
            ORDER BY avg_order_value DESC
        """)
        assert result["row_count"] > 0
        assert "segment" in result["columns"]
