"""
Database executor factory — returns the right executor subclass
based on the configured database provider.
"""

from agents.executor.athena_executor import AthenaExecutor


def get_executor(config: dict):
    """
    Return a database executor based on config["database"]["provider"].

    Parameters
    ----------
    config : dict
        Full application config.

    Returns
    -------
    BaseExecutor
        An executor subclass with an .execute(sql) method.
    """
    provider = config["database"]["provider"]

    if provider == "athena":
        return AthenaExecutor(config["database"]["athena"])
    # ── Extend here ──
    # elif provider == "snowflake":
    #     return SnowflakeExecutor(config["database"]["snowflake"])
    # elif provider == "postgres":
    #     return PostgresExecutor(config["database"]["postgres"])
    # elif provider == "bigquery":
    #     return BigQueryExecutor(config["database"]["bigquery"])
    else:
        raise ValueError(f"Unsupported database provider: {provider}")
