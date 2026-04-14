"""
AWS Athena executor — submits queries, polls for completion,
and returns structured results.
"""

import time
import boto3
from typing import List

from agents.executor.base_executor import BaseExecutor


class AthenaExecutor(BaseExecutor):
    """Execute SQL queries against AWS Athena."""

    def __init__(self, config: dict):
        """
        Parameters
        ----------
        config : dict
            Athena-specific config with keys: region, s3_output, database.
        """
        self.client = boto3.client("athena", region_name=config["region"])
        self.s3_output = config["s3_output"]
        self.database = config["database"]

    def execute(self, sql: str) -> dict:
        """
        Submit SQL to Athena, wait for completion, return results.

        Returns
        -------
        dict
            {"columns": [...], "rows": [[...], ...], "row_count": int}
        """
        response = self.client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": self.database},
            ResultConfiguration={"OutputLocation": self.s3_output},
        )
        query_id = response["QueryExecutionId"]
        return self._poll_and_fetch(query_id)

    def _poll_and_fetch(self, query_id: str) -> dict:
        """Poll Athena until the query finishes, then fetch results."""
        while True:
            execution = self.client.get_query_execution(
                QueryExecutionId=query_id
            )
            status = execution["QueryExecution"]["Status"]["State"]

            if status == "SUCCEEDED":
                break
            elif status in ("FAILED", "CANCELLED"):
                reason = (
                    execution["QueryExecution"]["Status"]
                    .get("StateChangeReason", "Unknown error")
                )
                raise Exception(f"Athena query {status}: {reason}")

            time.sleep(1)

        return self._fetch_results(query_id)

    def _fetch_results(self, query_id: str) -> dict:
        """Fetch and structure query results from Athena."""
        raw = self.client.get_query_results(QueryExecutionId=query_id)
        result_set = raw["ResultSet"]

        columns = [
            col["Label"]
            for col in result_set["ResultSetMetadata"]["ColumnInfo"]
        ]

        rows: List[list] = []
        for i, row in enumerate(result_set["Rows"]):
            if i == 0:
                continue  # skip header row
            rows.append([
                datum.get("VarCharValue", None)
                for datum in row["Data"]
            ])

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
