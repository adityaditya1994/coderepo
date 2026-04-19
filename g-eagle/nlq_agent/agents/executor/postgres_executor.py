"""
PostgreSQL executor — runs SQL against a local or remote
PostgreSQL database and returns structured results.
"""

import psycopg2
from agents.executor.base_executor import BaseExecutor


class PostgresExecutor(BaseExecutor):
    """Execute SQL queries against PostgreSQL."""

    def __init__(self, config: dict):
        """
        Parameters
        ----------
        config : dict
            Postgres-specific config with keys: host, port, database, user, password.
        """
        self.conn_params = {
            "host": config.get("host", "localhost"),
            "port": config.get("port", 5432),
            "database": config.get("database", "nlq_demo"),
            "user": config.get("user", "nlq_user"),
            "password": config.get("password", "nlq_pass"),
        }

    def execute(self, sql: str) -> dict:
        """
        Execute SQL against Postgres and return structured results.

        Returns
        -------
        dict
            {"columns": [...], "rows": [[...], ...], "row_count": int}
        """
        conn = psycopg2.connect(**self.conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute(sql)

                # Handle non-SELECT statements (INSERT, UPDATE, etc.)
                if cur.description is None:
                    conn.commit()
                    return {
                        "columns": [],
                        "rows": [],
                        "row_count": cur.rowcount,
                    }

                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

                # Convert to list of lists (psycopg2 returns tuples)
                rows = [list(row) for row in rows]

                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                }
        finally:
            conn.close()
