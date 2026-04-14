"""
Graph Builder — assembles the full LangGraph StateGraph
with all nodes, edges, conditional edges, and checkpointing.
"""

from functools import partial

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import AgentState
from graph.edges import should_retry, after_validation

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

    # ── Wrap node functions with config/llm dependencies ──

    def _supervisor(state: AgentState) -> dict:
        return supervisor_node(state, config, llm)

    def _discovery(state: AgentState) -> dict:
        agent = DiscoveryAgent(config, llm)
        tables = agent.discover(state["user_query"])

        # Build memory context and attach
        ctx = memory_mgr.retrieve_context(
            state["user_query"], state.get("session_id", "")
        )

        return {
            "discovered_tables": tables,
            "memory_context": ctx,
        }

    def _schema_retriever(state: AgentState) -> dict:
        return schema_retriever_node(state, config)

    def _query_planner(state: AgentState) -> dict:
        return query_planner_node(state, config, llm)

    def _sql_generator(state: AgentState) -> dict:
        return sql_generator_node(state, config, llm)

    def _executor(state: AgentState) -> dict:
        return executor_node(state, config)

    def _sql_fixer(state: AgentState) -> dict:
        return sql_fixer_node(state, config, llm)

    def _validator(state: AgentState) -> dict:
        return validation_council_node(state, config, llm)

    def _summarizer(state: AgentState) -> dict:
        return summarizer_node(state, config, llm)

    def _human_handoff(state: AgentState) -> dict:
        return human_handoff_node(state, config)

    def _memory_writer(state: AgentState) -> dict:
        return memory_writer_node(state, config)

    # ── Build the graph ──
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
