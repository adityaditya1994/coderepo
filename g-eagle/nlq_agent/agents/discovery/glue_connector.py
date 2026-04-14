"""
AWS Glue connector — searches the Glue Data Catalog
for tables matching a user query.
"""

import boto3
from typing import List


class GlueConnector:
    """Search AWS Glue Data Catalog for relevant tables."""

    def __init__(self, region: str = "us-east-1"):
        self.client = boto3.client("glue", region_name=region)

    def search(self, query: str) -> List[dict]:
        """
        Search Glue catalog for tables matching the query string.

        Returns
        -------
        list[dict]
            Normalized table metadata dicts with keys:
            source, name, database, columns, description.
        """
        try:
            response = self.client.search_tables(
                SearchText=query, MaxResults=10
            )
        except Exception as e:
            # Graceful degradation — return empty if Glue is unavailable
            return []

        results = []
        for table in response.get("TableList", []):
            columns = [
                {"name": c["Name"], "type": c["Type"]}
                for c in table.get("StorageDescriptor", {})
                               .get("Columns", [])
            ]
            # Also include partition keys as columns
            for pk in table.get("PartitionKeys", []):
                columns.append({"name": pk["Name"], "type": pk["Type"]})

            results.append({
                "source": "glue",
                "name": table["Name"],
                "database": table.get("DatabaseName", ""),
                "columns": columns,
                "description": table.get("Description", ""),
            })

        return results
