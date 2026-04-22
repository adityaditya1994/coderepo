"""
Schema Retriever agent — fetches full column-level schema
for the selected tables from the database catalog.

Supports:
- AWS Glue (production)
- Local Postgres via information_schema (local dev)
- Fallback to discovery-provided columns
"""

import json
import logging
from typing import List

logger = logging.getLogger("discovery-api")


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
    provider = db_config.get("provider", "athena")

    if provider == "local_postgres":
        return _retrieve_postgres(discovered, db_config.get("local_postgres", {}), state)
    else:
        return _retrieve_glue(discovered, db_config, state)


def _retrieve_postgres(discovered: list, pg_config: dict, state: dict) -> dict:
    """Retrieve schema from Postgres information_schema.columns."""
    schema = {}
    selected_tables = []

    try:
        import psycopg2
        conn = psycopg2.connect(
            host=pg_config.get("host", "localhost"),
            port=pg_config.get("port", 5432),
            database=pg_config.get("database", "nlq_demo"),
            user=pg_config.get("user", "nlq_user"),
            password=pg_config.get("password", "nlq_pass"),
        )
    except Exception as e:
        logger.warning(f"Schema retriever: Postgres connection failed — {e}")
        # Fall back to discovery columns
        return _fallback_to_discovery(discovered, state, str(e))

    try:
        with conn.cursor() as cur:
            for table_info in discovered:
                table_name = table_info.get("name", "")
                if not table_name:
                    continue

                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                      AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, (table_name,))
                rows = cur.fetchall()

                if rows:
                    # Maintain descriptions from the catalog if available
                    desc_map = {}
                    if table_info.get("columns"):
                        for c in table_info["columns"]:
                            desc_map[c["name"]] = c.get("description", "")
                            
                    enriched_cols = []
                    for row in rows:
                        col_dict = {"name": row[0], "type": row[1]}
                        if desc_map.get(row[0]):
                            col_dict["description"] = desc_map[row[0]]
                        enriched_cols.append(col_dict)
                        
                    schema[table_name] = enriched_cols
                    selected_tables.append(table_name)
                elif table_info.get("columns"):
                    # Table not in DB, use discovery columns
                    schema[table_name] = table_info["columns"]
                    selected_tables.append(table_name)
    finally:
        conn.close()

    return {
        "schema": schema,
        "selected_tables": selected_tables,
    }


def _retrieve_glue(discovered: list, db_config: dict, state: dict) -> dict:
    """Retrieve schema from AWS Glue Data Catalog."""
    import boto3

    region = db_config.get("athena", {}).get("region", "us-east-1")

    try:
        glue = boto3.client("glue", region_name=region)
    except Exception as e:
        return _fallback_to_discovery(discovered, state, f"Glue client error — {e}")

    schema = {}
    selected_tables = []

    for table_info in discovered:
        table_name = table_info.get("name", "")
        database = table_info.get("database", "")

        if not table_name or not database:
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
            for pk in table.get("PartitionKeys", []):
                columns.append({"name": pk["Name"], "type": pk["Type"]})

            schema[table_name] = columns
            selected_tables.append(table_name)

        except Exception:
            if table_info.get("columns"):
                schema[table_name] = table_info["columns"]
                selected_tables.append(table_name)

    return {
        "schema": schema,
        "selected_tables": selected_tables,
    }


def _fallback_to_discovery(discovered: list, state: dict, error_msg: str) -> dict:
    """Use columns from discovery output as a fallback."""
    schema = {}
    selected_tables = []
    for table_info in discovered:
        table_name = table_info.get("name", "")
        if table_info.get("columns"):
            schema[table_name] = table_info["columns"]
            selected_tables.append(table_name)

    return {
        "schema": schema,
        "selected_tables": selected_tables,
        "error_log": state.get("error_log", []) + [
            f"Schema retriever: {error_msg} — used discovery fallback"
        ],
    }

