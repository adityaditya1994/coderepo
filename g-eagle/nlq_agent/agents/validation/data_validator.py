"""
Data Validator — performs sanity checks on query results:
unexpected NULLs, numeric ranges, obvious outliers.
"""

from typing import List, Any


class DataValidator:
    """Rule-based sanity checks on execution results."""

    def validate(self, execution_result: dict) -> dict:
        """
        Run data sanity checks on the query result.

        Parameters
        ----------
        execution_result : dict
            {"columns": [...], "rows": [[...], ...], "row_count": int}

        Returns
        -------
        dict
            {"passed": bool, "issues": list[str]}
        """
        if not execution_result:
            return {"passed": False, "issues": ["No execution result to validate"]}

        columns = execution_result.get("columns", [])
        rows = execution_result.get("rows", [])
        issues: List[str] = []

        if not rows:
            issues.append("Result set is empty (0 rows)")
            return {"passed": False, "issues": issues}

        # Check for excessive NULLs
        for col_idx, col_name in enumerate(columns):
            null_count = sum(
                1 for row in rows
                if col_idx < len(row) and row[col_idx] is None
            )
            null_pct = null_count / len(rows) if rows else 0

            if null_pct > 0.5:
                issues.append(
                    f"Column '{col_name}' has {null_pct:.0%} NULL values"
                )

        # Check for numeric outliers (simple z-score-like check)
        for col_idx, col_name in enumerate(columns):
            numeric_values = []
            for row in rows:
                if col_idx < len(row) and row[col_idx] is not None:
                    try:
                        numeric_values.append(float(row[col_idx]))
                    except (ValueError, TypeError):
                        continue

            if len(numeric_values) >= 3:
                mean = sum(numeric_values) / len(numeric_values)
                variance = sum((x - mean) ** 2 for x in numeric_values) / len(numeric_values)
                std = variance ** 0.5

                if std > 0:
                    for val in numeric_values:
                        z = abs(val - mean) / std
                        if z > 4:
                            issues.append(
                                f"Column '{col_name}' has potential outlier: "
                                f"{val} (z-score: {z:.1f})"
                            )
                            break  # one outlier warning per column

        # Check for negative values in typically-positive columns
        positive_keywords = {"revenue", "amount", "count", "price", "total", "quantity"}
        for col_idx, col_name in enumerate(columns):
            if any(kw in col_name.lower() for kw in positive_keywords):
                for row in rows:
                    if col_idx < len(row) and row[col_idx] is not None:
                        try:
                            if float(row[col_idx]) < 0:
                                issues.append(
                                    f"Column '{col_name}' has negative values "
                                    f"(unusual for this metric type)"
                                )
                                break
                        except (ValueError, TypeError):
                            continue

        passed = len(issues) == 0
        return {"passed": passed, "issues": issues}
