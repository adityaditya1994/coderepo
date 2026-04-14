"""
Flat-file connector — searches a local JSON/CSV metadata
catalog for tables matching a user query.
"""

import json
from pathlib import Path
from typing import List


class FlatFileConnector:
    """Search a local flat-file metadata catalog."""

    # Default location — can be overridden
    DEFAULT_CATALOG_PATH = Path(__file__).parent.parent.parent / "knowledge_base" / "table_catalog.json"

    def __init__(self, catalog_path: str = None):
        self.catalog_path = Path(catalog_path) if catalog_path else self.DEFAULT_CATALOG_PATH

    def search(self, query: str) -> List[dict]:
        """
        Simple keyword search over a local JSON catalog.

        Expected catalog format (table_catalog.json):
        [
          {
            "name": "orders",
            "database": "analytics_db",
            "columns": [{"name": "order_id", "type": "bigint"}, ...],
            "description": "All customer orders",
            "tags": ["orders", "revenue", "sales"]
          },
          ...
        ]

        Returns
        -------
        list[dict]
            Matching table metadata dicts.
        """
        if not self.catalog_path.exists():
            return []

        try:
            with open(self.catalog_path, "r") as f:
                catalog = json.load(f)
        except Exception:
            return []

        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        results = []
        for table in catalog:
            # Build searchable text from name, description, tags, and column names
            searchable = " ".join([
                table.get("name", ""),
                table.get("description", ""),
                " ".join(table.get("tags", [])),
                " ".join(c.get("name", "") for c in table.get("columns", [])),
            ]).lower()

            # Score by how many query tokens appear in the searchable text
            matches = sum(1 for token in query_tokens if token in searchable)
            if matches > 0:
                results.append({
                    "source": "flatfile",
                    "name": table.get("name", ""),
                    "database": table.get("database", ""),
                    "columns": table.get("columns", []),
                    "description": table.get("description", ""),
                    "score": matches / len(query_tokens) if query_tokens else 0,
                })

        # Sort by score descending
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:10]
