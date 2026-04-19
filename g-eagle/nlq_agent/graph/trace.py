"""
Trace utilities — structured logging and mermaid diagram
generation for every graph node invocation.
"""

import time
import uuid
import logging
from typing import Any

logger = logging.getLogger("discovery-api")

# Shared trace_id for the current graph invocation
_current_trace_id = ""


def new_trace_id() -> str:
    """Generate a new trace ID for a graph invocation."""
    global _current_trace_id
    _current_trace_id = str(uuid.uuid4())[:8]
    return _current_trace_id


def get_trace_id() -> str:
    return _current_trace_id or "no-trace"


def trace_start(agent_name: str, state: dict) -> float:
    """Log the start of a node and return the start timestamp."""
    logger.info("─" * 50)
    logger.info(f"▶ [{get_trace_id()}] {agent_name.upper()}")

    # Log key inputs (truncated)
    if agent_name == "supervisor":
        logger.info(f"   query: \"{_trunc(state.get('user_query', ''), 100)}\"")
    elif agent_name == "discovery":
        logger.info(f"   query: \"{_trunc(state.get('user_query', ''), 100)}\"")
    elif agent_name == "schema_retriever":
        tables = [t.get("name", "?") for t in state.get("discovered_tables", [])]
        logger.info(f"   tables to retrieve: {tables}")
    elif agent_name == "query_planner":
        logger.info(f"   tables: {state.get('selected_tables', [])}")
    elif agent_name == "sql_generator":
        logger.info(f"   plan keys: {list(state.get('query_plan', {}).keys())}")
    elif agent_name == "executor":
        logger.info(f"   sql: \"{_trunc(state.get('sql', ''), 120)}\"")
        logger.info(f"   retry_count: {state.get('retry_count', 0)}")
    elif agent_name == "sql_fixer":
        logger.info(f"   error: \"{_trunc(state.get('execution_error', ''), 100)}\"")
    elif agent_name == "validator":
        has_result = state.get("execution_result") is not None
        logger.info(f"   has_result: {has_result}")
    elif agent_name == "summarizer":
        conf = state.get("confidence_score", 0)
        logger.info(f"   confidence: {conf}")
    elif agent_name == "human_handoff":
        logger.info(f"   retries: {state.get('retry_count', 0)}")
    elif agent_name == "memory_writer":
        logger.info(f"   has_sql: {bool(state.get('sql'))}")

    return time.time()


def trace_end(state: dict, agent_name: str, output: dict, start_time: float) -> dict:
    """
    Log the end of a node, update trace in state, build mermaid.
    Returns the output dict augmented with trace fields.
    """
    duration_ms = (time.time() - start_time) * 1000

    # Log key outputs (truncated)
    out_keys = list(output.keys()) if output else []
    logger.info(f"   ✓ output keys: {out_keys}")

    if "sql" in output and output["sql"]:
        logger.info(f"   sql: \"{_trunc(output['sql'], 120)}\"")
    if "execution_error" in output and output["execution_error"]:
        logger.info(f"   ⚠ error: \"{_trunc(output['execution_error'], 100)}\"")
    if "confidence_score" in output:
        logger.info(f"   confidence: {output['confidence_score']}")
    if "validation_result" in output:
        vr = output["validation_result"]
        logger.info(f"   valid: {vr.get('overall_valid')} | rec: {vr.get('recommendation')}")
    if "final_answer" in output and output["final_answer"]:
        logger.info(f"   answer: \"{_trunc(output['final_answer'], 100)}\"")

    logger.info(f"   ⏱ {duration_ms:.0f}ms")

    # Build trace entry
    trace_entry = {
        "agent": agent_name,
        "duration_ms": round(duration_ms, 1),
        "trace_id": get_trace_id(),
        "output_keys": out_keys,
    }

    # Update cumulative trace list
    existing_trace = list(state.get("trace", []))
    existing_trace.append(trace_entry)

    # Build mermaid
    mermaid = _build_mermaid(existing_trace)
    logger.info(f"   📊 {mermaid}")

    # Augment output with trace data
    output["trace"] = existing_trace
    output["agent_mermaid"] = mermaid

    return output


def _build_mermaid(trace: list, max_nodes: int = 8) -> str:
    """Build a cumulative mermaid diagram from trace entries."""
    if not trace:
        return ""

    # Use last N entries to avoid log spam
    recent = trace[-max_nodes:]
    names = [_mermaid_label(e["agent"]) for e in recent]

    if len(names) == 1:
        return f"graph LR; {names[0]}"

    edges = [f"{names[i]}-->{names[i+1]}" for i in range(len(names) - 1)]
    return "graph LR; " + "; ".join(edges)


def _mermaid_label(agent_name: str) -> str:
    """Convert agent name to a Mermaid node label."""
    short = {
        "supervisor": "S[supervisor]",
        "discovery": "D[discovery]",
        "schema_retriever": "R[schema_retriever]",
        "query_planner": "P[query_planner]",
        "sql_generator": "G[sql_generator]",
        "executor": "X[executor]",
        "sql_fixer": "F[sql_fixer]",
        "validator": "V[validator]",
        "summarizer": "SUM[summarizer]",
        "human_handoff": "H[human_handoff]",
        "memory_writer": "M[memory_writer]",
    }
    return short.get(agent_name, f"{agent_name[0].upper()}[{agent_name}]")


def _trunc(s: str, max_len: int) -> str:
    """Truncate a string for logging."""
    if not s:
        return ""
    s = s.replace("\n", " ")
    return s[:max_len] + "..." if len(s) > max_len else s
