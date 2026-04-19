"""
Database executor factory — returns the right executor subclass
based on the configured database provider.
"""

from agents.executor.athena_executor import AthenaExecutor
from agents.executor.postgres_executor import PostgresExecutor


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
    elif provider == "local_postgres":
        return PostgresExecutor(config["database"]["local_postgres"])
    else:
        raise ValueError(f"Unsupported database provider: {provider}")

