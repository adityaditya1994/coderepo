"""
LangGraph state schema — the single shared state object
passed through every node in the agent graph.
"""

from typing import TypedDict, Optional, List, Any


class AgentState(TypedDict):
    # ── Input ──
    user_query: str
    session_id: str

    # ── Discovery ──
    discovered_tables: List[dict]       # [{name, source, confidence, reason}]
    selected_tables: List[str]
    schema: dict                         # {table_name: [{name, type}, ...]}

    # ── Query Planning ──
    query_plan: dict                     # structured plan from planner

    # ── SQL ──
    sql: str
    sql_history: List[str]              # all versions of SQL tried

    # ── Execution ──
    execution_result: Optional[Any]
    execution_error: Optional[str]
    retry_count: int

    # ── Validation ──
    validation_result: dict             # {valid, issues, confidence}

    # ── Summarization ──
    summary: str

    # ── Control ──
    confidence_score: float
    needs_human: bool
    final_answer: Optional[str]

    # ── Memory ──
    memory_context: dict

    # ── Errors / Trace ──
    error_log: List[str]

    # ── Observability (v2) ──
    trace: List[dict]                    # [{agent, duration_ms, trace_id, output_keys}]
    agent_mermaid: str                   # cumulative mermaid diagram of execution path

