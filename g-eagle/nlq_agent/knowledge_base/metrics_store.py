"""
Metrics Store — loads, looks up, and updates metric definitions
from the knowledge base (metrics.json).
"""

import json
from pathlib import Path
from typing import Optional


_METRICS_FILE = Path(__file__).parent / "metrics.json"


class MetricsStore:
    """In-memory metrics knowledge base backed by metrics.json."""

    def __init__(self, path: str = None):
        self.path = Path(path) if path else _METRICS_FILE
        self.metrics = self._load()

    def _load(self) -> dict:
        """Load metrics from JSON file."""
        if not self.path.exists():
            return {}
        with open(self.path, "r") as f:
            return json.load(f)

    def save(self):
        """Persist current metrics to JSON file."""
        with open(self.path, "w") as f:
            json.dump(self.metrics, f, indent=2)

    def lookup(self, metric_name: str) -> Optional[dict]:
        """
        Look up a metric by name.

        Returns None if not found.
        """
        return self.metrics.get(metric_name.lower())

    def get_approved(self) -> dict:
        """Return only approved metrics."""
        return {
            k: v for k, v in self.metrics.items()
            if v.get("approved", False)
        }

    def get_all(self) -> dict:
        """Return all metrics."""
        return self.metrics

    def add_or_update(
        self,
        name: str,
        definition: str,
        sql_expression: str,
        table: str,
        filters: str = "",
        approved: bool = False,
        updated_by: str = "system",
    ):
        """Add or update a metric definition."""
        from datetime import datetime

        self.metrics[name.lower()] = {
            "definition": definition,
            "sql_expression": sql_expression,
            "table": table,
            "filters": filters,
            "approved": approved,
            "last_updated": datetime.utcnow().isoformat()[:10],
            "updated_by": updated_by,
        }
        self.save()

    def approve(self, name: str, approved_by: str = "user"):
        """Mark a metric as approved."""
        if name.lower() in self.metrics:
            self.metrics[name.lower()]["approved"] = True
            self.metrics[name.lower()]["updated_by"] = approved_by
            self.save()
