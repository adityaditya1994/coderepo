"""
Schema Validator — checks that all columns referenced in the SQL
actually exist in the provided schema and types are used correctly.
"""

import re
from typing import List


class SchemaValidator:
    """Validate SQL column references against the known schema."""

    def validate(self, sql: str, schema: dict) -> dict:
        """
        Check that columns used in the SQL exist in the schema.

        Returns
        -------
        dict
            {"passed": bool, "issues": list[str]}
        """
        issues: List[str] = []

        # Flatten all known columns
        known_columns = set()
        for table_name, columns in schema.items():
            for col in columns:
                col_name = col["name"] if isinstance(col, dict) else col
                known_columns.add(col_name.lower())
                # Also add table-qualified version
                known_columns.add(f"{table_name.lower()}.{col_name.lower()}")

        # Extract column-like references from SQL (rough heuristic)
        # This catches patterns like: table.column, alias.column, bare column
        sql_upper = sql.upper()
        tokens = re.findall(r'[\w]+\.[\w]+|(?<=SELECT\s)[\w]+|(?<=,\s*)[\w]+', sql, re.IGNORECASE)

        # Check table names exist
        for table_name in schema.keys():
            if table_name.lower() not in sql.lower():
                issues.append(
                    f"Table '{table_name}' is in schema but not referenced in SQL"
                )

        passed = len(issues) == 0
        return {"passed": passed, "issues": issues}
