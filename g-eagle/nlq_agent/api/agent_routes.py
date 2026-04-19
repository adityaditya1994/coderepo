"""
Per-agent invocation routes — allows testing any single agent
in isolation via POST /agents/{agent_name}/invoke.

Returns a normalized response envelope with trace info.
"""

import time
import uuid
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("discovery-api")

router = APIRouter(prefix="/agents", tags=["Agent Testing"])


# ── Request / Response models ──

class AgentInvokeRequest(BaseModel):
    """Request body for invoking a single agent."""
    state: dict = Field(
        ..., description="Partial AgentState dict — only fields the agent reads"
    )


class AgentInvokeResponse(BaseModel):
    """Normalized response envelope from any agent invocation."""
    agent: str
    ok: bool
    input: dict
    output: dict
    trace_id: str
    duration_ms: float
    error: Optional[str] = None


# ── Supported agents and their runner functions ──

def _get_agent_runner(agent_name: str, config: dict, llm):
    """Return a callable (state) -> dict for the given agent."""
    from agents.supervisor import supervisor_node
    from agents.discovery.discovery_agent import DiscoveryAgent
    from agents.discovery.flatfile_connector import FlatFileConnector
    from agents.discovery.discovery_council import DiscoveryCouncil
    from agents.schema_retriever import schema_retriever_node
    from agents.query_planner import query_planner_node
    from agents.sql_generator import sql_generator_node
    from agents.executor.executor_agent import executor_node
    from agents.sql_fixer import sql_fixer_node
    from agents.validation.council import validation_council_node
    from agents.summarizer import summarizer_node
    from agents.human_handoff import human_handoff_node

    runners = {
        "supervisor": lambda s: supervisor_node(s, config, llm),
        "discovery": lambda s: _run_discovery(s, config, llm),
        "schema_retriever": lambda s: schema_retriever_node(s, config),
        "query_planner": lambda s: query_planner_node(s, config, llm),
        "sql_generator": lambda s: sql_generator_node(s, config, llm),
        "executor": lambda s: executor_node(s, config),
        "sql_fixer": lambda s: sql_fixer_node(s, config, llm),
        "validator": lambda s: validation_council_node(s, config, llm),
        "summarizer": lambda s: summarizer_node(s, config, llm),
        "human_handoff": lambda s: human_handoff_node(s, config),
    }
    return runners.get(agent_name)


def _run_discovery(state: dict, config: dict, llm):
    """Run discovery inline (no catalog path required — uses flatfile from demo)."""
    from pathlib import Path
    api_dir = Path(__file__).parent
    catalog_path = str(api_dir / "demo_data" / "table_catalog.json")

    connector = FlatFileConnector(catalog_path=catalog_path)
    candidates = connector.search(state.get("user_query", ""))

    from agents.discovery.discovery_council import DiscoveryCouncil
    top_k = state.get("top_k", 5)
    council = DiscoveryCouncil(llm=llm, top_k=top_k)

    try:
        selected = council.evaluate(state.get("user_query", ""), candidates)
    except Exception:
        selected = candidates[:top_k]

    return {
        "discovered_tables": selected,
        "memory_context": {},
    }


# ── Main route ──

SUPPORTED_AGENTS = [
    "supervisor", "discovery", "schema_retriever", "query_planner",
    "sql_generator", "executor", "validator", "summarizer",
    "sql_fixer", "human_handoff",
]


@router.post(
    "/{agent_name}/invoke",
    response_model=AgentInvokeResponse,
    summary="Invoke a single agent",
    description=f"Supported agents: {', '.join(SUPPORTED_AGENTS)}",
)
async def invoke_agent(agent_name: str, request: AgentInvokeRequest):
    """
    Invoke a single agent node with the given partial state.
    Returns normalized response envelope.
    """
    from api.main import get_app_state

    if agent_name not in SUPPORTED_AGENTS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent '{agent_name}'. Supported: {SUPPORTED_AGENTS}",
        )

    app_state = get_app_state()
    llm = app_state.get("llm")

    # Build config for the agent
    from config.config_loader import load_config
    config = load_config()

    runner = _get_agent_runner(agent_name, config, llm)
    if not runner:
        raise HTTPException(status_code=500, detail=f"No runner for '{agent_name}'")

    trace_id = str(uuid.uuid4())[:8]
    state = request.state

    logger.info("═" * 50)
    logger.info(f"🔧 POST /agents/{agent_name}/invoke  trace={trace_id}")
    logger.info(f"   input keys: {list(state.keys())}")

    t0 = time.time()
    try:
        output = runner(state)
        duration_ms = (time.time() - t0) * 1000

        logger.info(f"   ✅ ok | output keys: {list(output.keys())} | {duration_ms:.0f}ms")
        logger.info("═" * 50)

        return AgentInvokeResponse(
            agent=agent_name,
            ok=True,
            input=state,
            output=output,
            trace_id=trace_id,
            duration_ms=round(duration_ms, 1),
        )
    except Exception as e:
        duration_ms = (time.time() - t0) * 1000

        logger.error(f"   ❌ error: {e} | {duration_ms:.0f}ms")
        logger.info("═" * 50)

        return AgentInvokeResponse(
            agent=agent_name,
            ok=False,
            input=state,
            output={},
            trace_id=trace_id,
            duration_ms=round(duration_ms, 1),
            error=str(e),
        )
