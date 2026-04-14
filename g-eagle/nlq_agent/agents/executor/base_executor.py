"""
Abstract base class for all database executors.
Each concrete executor (Athena, Snowflake, Postgres, …)
must implement the execute() method.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseExecutor(ABC):
    """Base interface every database executor must implement."""

    @abstractmethod
    def execute(self, sql: str) -> dict:
        """
        Execute a SQL query and return results.

        Parameters
        ----------
        sql : str
            The SQL query string to execute.

        Returns
        -------
        dict
            Query result with keys like 'columns', 'rows', 'row_count'.
        """
        pass
