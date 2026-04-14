"""
Schema Retriever agent — fetches full column-level schema
for the selected tables from the database catalog (Glue).
"""

import json
import boto3
from typing import List


def schema_retriever_node(state: dict, config: dict) -> dict:
    """
    LangGraph node: fetch detailed schema for selected tables.

    Reads: state["discovered_tables"]
    Writes: state["schema"], state["selected_tables"]
    """
    discovered = state.get("discovered_tables", [])
    if not discovered:
        return {
            "schema": {},
            "selected_tables": [],
            "error_log": state.get("error_log", []) + [
                "Schema retriever: no tables discovered"
            ],
        }

    db_config = config.get("database", {})
    region = db_config.get("athena", {}).get("region", "us-east-1")

    try:
        glue = boto3.client("glue", region_name=region)
    except Exception as e:
        return {
            "schema": {},
            "selected_tables": [],
            "error_log": state.get("error_log", []) + [
                f"Schema retriever: Glue client error — {e}"
            ],
        }

    schema = {}
    selected_tables = []

    for table_info in discovered:
        table_name = table_info.get("name", "")
        database = table_info.get("database", "")

        if not table_name or not database:
            # If no database, use columns from discovery if available
            if table_info.get("columns"):
                schema[table_name] = table_info["columns"]
                selected_tables.append(table_name)
            continue

        try:
            resp = glue.get_table(DatabaseName=database, Name=table_name)
            table = resp.get("Table", {})

            columns = [
                {"name": c["Name"], "type": c["Type"]}
                for c in table.get("StorageDescriptor", {})
                               .get("Columns", [])
            ]
            # Include partition keys
            for pk in table.get("PartitionKeys", []):
                columns.append({"name": pk["Name"], "type": pk["Type"]})

            schema[table_name] = columns
            selected_tables.append(table_name)

        except Exception as e:
            # Fall back to columns from discovery
            if table_info.get("columns"):
                schema[table_name] = table_info["columns"]
                selected_tables.append(table_name)

    return {
        "schema": schema,
        "selected_tables": selected_tables,
    }
