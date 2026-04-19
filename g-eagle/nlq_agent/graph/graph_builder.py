"""
Graph Builder — assembles the full LangGraph StateGraph
with all nodes, edges, conditional edges, and checkpointing.

All node wrappers include trace instrumentation for structured
logging and mermaid diagram generation (see graph/trace.py).
Topology is unchanged from the original design.
"""

import logging
from functools import partial

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import AgentState
from graph.edges import should_retry, after_validation
from graph.trace import trace_start, trace_end, new_trace_id

from agents.supervisor import supervisor_node
from agents.discovery.discovery_agent import DiscoveryAgent
from agents.schema_retriever import schema_retriever_node
from agents.query_planner import query_planner_node
from agents.sql_generator import sql_generator_node
from agents.executor.executor_agent import executor_node
from agents.sql_fixer import sql_fixer_node
from agents.validation.council import validation_council_node
from agents.summarizer import summarizer_node
from agents.human_handoff import human_handoff_node
from memory.memory_manager import MemoryManager, memory_writer_node

from llm.llm_factory import get_llm
from knowledge_base.metrics_store import MetricsStore

logger = logging.getLogger("discovery-api")


def build_graph(config: dict):
    """
    Build and compile the full agent graph.

    Parameters
    ----------
    config : dict
        Full application config from config_loader.

    Returns
    -------
    CompiledGraph
        A compiled LangGraph ready for .invoke() or .stream().
    """
    llm = get_llm(config)
    memory_mgr = MemoryManager(config)
    metrics_store = MetricsStore()

    # ── Wrap node functions with config/llm + trace instrumentation ──

    def _supervisor(state: AgentState) -> dict:
        t0 = trace_start("supervisor", state)
        result = supervisor_node(state, config, llm)
        return trace_end(state, "supervisor", result, t0)

    def _discovery(state: AgentState) -> dict:
        t0 = trace_start("discovery", state)
        agent = DiscoveryAgent(config, llm)
        tables = agent.discover(state["user_query"])
        ctx = memory_mgr.retrieve_context(
            state["user_query"], state.get("session_id", "")
        )
        result = {
            "discovered_tables": tables,
            "memory_context": ctx,
        }
        return trace_end(state, "discovery", result, t0)

    def _schema_retriever(state: AgentState) -> dict:
        t0 = trace_start("schema_retriever", state)
        result = schema_retriever_node(state, config)
        return trace_end(state, "schema_retriever", result, t0)

    def _query_planner(state: AgentState) -> dict:
        t0 = trace_start("query_planner", state)
        result = query_planner_node(state, config, llm)
        return trace_end(state, "query_planner", result, t0)

    def _sql_generator(state: AgentState) -> dict:
        t0 = trace_start("sql_generator", state)
        result = sql_generator_node(state, config, llm)
        return trace_end(state, "sql_generator", result, t0)

    def _executor(state: AgentState) -> dict:
        t0 = trace_start("executor", state)
        result = executor_node(state, config)
        return trace_end(state, "executor", result, t0)

    def _sql_fixer(state: AgentState) -> dict:
        t0 = trace_start("sql_fixer", state)
        result = sql_fixer_node(state, config, llm)
        return trace_end(state, "sql_fixer", result, t0)

    def _validator(state: AgentState) -> dict:
        t0 = trace_start("validator", state)
        result = validation_council_node(state, config, llm)
        return trace_end(state, "validator", result, t0)

    def _summarizer(state: AgentState) -> dict:
        t0 = trace_start("summarizer", state)
        result = summarizer_node(state, config, llm)
        return trace_end(state, "summarizer", result, t0)

    def _human_handoff(state: AgentState) -> dict:
        t0 = trace_start("human_handoff", state)
        result = human_handoff_node(state, config)
        return trace_end(state, "human_handoff", result, t0)

    def _memory_writer(state: AgentState) -> dict:
        t0 = trace_start("memory_writer", state)
        result = memory_writer_node(state, config)
        return trace_end(state, "memory_writer", result, t0)

    # ── Build the graph (topology unchanged) ──
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", _supervisor)
    graph.add_node("discovery", _discovery)
    graph.add_node("schema_retriever", _schema_retriever)
    graph.add_node("query_planner", _query_planner)
    graph.add_node("sql_generator", _sql_generator)
    graph.add_node("executor", _executor)
    graph.add_node("sql_fixer", _sql_fixer)
    graph.add_node("validator", _validator)
    graph.add_node("summarizer", _summarizer)
    graph.add_node("human_handoff", _human_handoff)
    graph.add_node("memory_writer", _memory_writer)

    # Entry point
    graph.set_entry_point("supervisor")

    # Linear happy path
    graph.add_edge("supervisor", "discovery")
    graph.add_edge("discovery", "schema_retriever")
    graph.add_edge("schema_retriever", "query_planner")
    graph.add_edge("query_planner", "sql_generator")
    graph.add_edge("sql_generator", "executor")

    # Retry loop (after executor)
    graph.add_conditional_edges("executor", should_retry, {
        "validate": "validator",
        "fix_sql": "sql_fixer",
        "human_fallback": "human_handoff",
    })
    graph.add_edge("sql_fixer", "executor")

    # Post-validation routing
    graph.add_conditional_edges("validator", after_validation, {
        "summarize": "summarizer",
        "retry": "sql_generator",
        "escalate": "human_handoff",
    })

    # Final edges → memory writer → END
    graph.add_edge("summarizer", "memory_writer")
    graph.add_edge("human_handoff", "memory_writer")
    graph.add_edge("memory_writer", END)

    # Enable checkpointing (session persistence)
    memory = MemorySaver()

    return graph.compile(
        checkpointer=memory,
        interrupt_before=["human_handoff"],
    )

