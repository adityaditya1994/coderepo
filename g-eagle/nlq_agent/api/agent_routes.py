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


# ── OpenAPI examples per agent ──

AGENT_EXAMPLES = {
    "discovery": {
        "summary": "Discovery — find tables for a revenue query",
        "value": {
            "state": {
                "user_query": "What is the total revenue by region for Q1 2024?",
                "session_id": "demo-001",
            }
        },
    },
    "schema_retriever": {
        "summary": "Schema Retriever — fetch columns for discovered tables",
        "value": {
            "state": {
                "discovered_tables": [
                    {"name": "orders", "database": "ecommerce_analytics", "columns": [
                        {"name": "order_id", "type": "bigint"},
                        {"name": "total_amount", "type": "double"},
                        {"name": "region_id", "type": "int"},
                    ]},
                    {"name": "regions", "database": "ecommerce_analytics", "columns": [
                        {"name": "region_id", "type": "int"},
                        {"name": "region_name", "type": "varchar"},
                    ]},
                ]
            }
        },
    },
    "query_planner": {
        "summary": "Query Planner — create structured plan from schema",
        "value": {
            "state": {
                "user_query": "What is the total revenue by region for Q1 2024?",
                "schema": {
                    "orders": [{"name": "order_id", "type": "bigint"}, {"name": "total_amount", "type": "double"}, {"name": "region_id", "type": "int"}],
                    "regions": [{"name": "region_id", "type": "int"}, {"name": "region_name", "type": "varchar"}],
                },
                "selected_tables": ["orders", "regions"],
                "memory_context": {},
            }
        },
    },
    "sql_generator": {
        "summary": "SQL Generator — generate SQL from a query plan",
        "value": {
            "state": {
                "user_query": "What is the total revenue by region for Q1 2024?",
                "schema": {
                    "orders": [{"name": "total_amount", "type": "double"}, {"name": "region_id", "type": "int"}],
                    "regions": [{"name": "region_id", "type": "int"}, {"name": "region_name", "type": "varchar"}],
                },
                "selected_tables": ["orders", "regions"],
                "query_plan": {"objective": "Total revenue by region Q1 2024", "tables": ["orders", "regions"]},
                "memory_context": {},
                "sql_history": [],
            }
        },
    },
    "executor": {
        "summary": "Executor — run SQL against the database",
        "value": {
            "state": {
                "sql": "SELECT r.region_name, SUM(o.total_amount) AS total_revenue FROM orders o JOIN regions r ON o.region_id = r.region_id GROUP BY r.region_name",
                "retry_count": 0,
            }
        },
    },
    "validator": {
        "summary": "Validator — run 4-validator council on results",
        "value": {
            "state": {
                "user_query": "What is the total revenue by region?",
                "sql": "SELECT r.region_name, SUM(o.total_amount) AS total_revenue FROM orders o JOIN regions r ON o.region_id = r.region_id GROUP BY r.region_name",
                "schema": {"orders": [{"name": "total_amount", "type": "double"}, {"name": "region_id", "type": "int"}], "regions": [{"name": "region_id", "type": "int"}, {"name": "region_name", "type": "varchar"}]},
                "query_plan": {"objective": "Total revenue by region"},
                "execution_result": {"columns": ["region_name", "total_revenue"], "rows": [["APAC", 3549.96]], "row_count": 1},
                "memory_context": {},
            }
        },
    },
    "summarizer": {
        "summary": "Summarizer — generate business narrative",
        "value": {
            "state": {
                "user_query": "What is the total revenue by region?",
                "sql": "SELECT r.region_name, SUM(o.total_amount) AS total_revenue FROM orders o JOIN regions r ON o.region_id = r.region_id GROUP BY r.region_name",
                "execution_result": {"columns": ["region_name", "total_revenue"], "rows": [["APAC", 3549.96], ["North America", 1919.92]], "row_count": 2},
                "validation_result": {"overall_valid": True, "confidence": 0.95, "recommendation": "proceed"},
                "confidence_score": 0.95,
                "memory_context": {},
            }
        },
    },
    "memory_writer": {
        "summary": "Memory Writer — save conversation context",
        "value": {
            "state": {
                "user_query": "What is the total revenue by region?",
                "session_id": "test-session-123",
                "final_answer": "Total revenue for APAC is 3549.96 and North America is 1919.92.",
                "sql": "SELECT r.region_name, SUM(o.total_amount) FROM orders o JOIN regions r ON o.region_id = r.region_id GROUP BY r.region_name"
            }
        },
    },
}


# ── Request / Response models ──

class AgentInvokeRequest(BaseModel):
    """Request body for invoking a single agent."""
    state: dict = Field(
        ..., description="Partial AgentState dict — only fields the agent reads"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [ex["value"] for ex in AGENT_EXAMPLES.values()],
        }
    }


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
    from memory.memory_manager import memory_writer_node

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
        "memory_writer": lambda s: memory_writer_node(s, config),
    }
    return runners.get(agent_name)


def _run_discovery(state: dict, config: dict, llm):
    """Run discovery inline (no catalog path required — uses flatfile from demo)."""
    from pathlib import Path
    from agents.discovery.flatfile_connector import FlatFileConnector
    
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
    "sql_fixer", "human_handoff", "memory_writer",
]


@router.post(
    "/{agent_name}/invoke",
    response_model=AgentInvokeResponse,
    summary="Invoke a single agent",
    description=f"Supported agents: {', '.join(SUPPORTED_AGENTS)}. "
                "See demo_requests/ folder for sample JSON per agent.",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": AGENT_EXAMPLES,
                }
            }
        }
    },
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
