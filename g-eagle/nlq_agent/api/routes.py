"""
API routes for the Discovery Agent.

Endpoints:
  POST /discover           — Full pipeline: flat-file search → LLM council ranking
  POST /discover/search    — Flat-file keyword search only (no LLM)
  GET  /discover/catalog   — Return the full demo catalog
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.discovery.flatfile_connector import FlatFileConnector
from agents.discovery.discovery_council import DiscoveryCouncil

logger = logging.getLogger("discovery-api")

router = APIRouter(tags=["Discovery"])


# ── Request / Response models ──

class DiscoverRequest(BaseModel):
    """Request body for discovery endpoints."""
    query: str = Field(
        ...,
        description="Natural language question about data",
        examples=["What is the total revenue by region for Q1 2024?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of top tables to return",
    )


class TableResult(BaseModel):
    """A single table result from discovery."""
    name: str
    database: Optional[str] = ""
    source: Optional[str] = "flatfile"
    confidence: Optional[float] = None
    reason: Optional[str] = None
    columns: Optional[list] = None
    score: Optional[float] = None
    description: Optional[str] = None
    key_columns: Optional[list] = None
    potential_joins: Optional[list] = None


class DiscoverResponse(BaseModel):
    """Response from the full discovery pipeline."""
    query: str
    selected_tables: list
    total_candidates: int
    council_used: bool


class SearchResponse(BaseModel):
    """Response from flat-file search only."""
    query: str
    results: list
    result_count: int


class CatalogResponse(BaseModel):
    """Response from catalog listing."""
    tables: list
    table_count: int


class QueryRequest(BaseModel):
    """Request body for full E2E query."""
    question: str = Field(
        ...,
        description="Natural language question about data",
        examples=["What is the total revenue by region for Q1 2024?"],
    )
    session_id: Optional[str] = Field(
        default="demo-session-123",
        description="Optional session ID for memory persistence",
    )


class QueryResponse(BaseModel):
    """Response from full E2E pipeline."""
    final_answer: Optional[str] = None
    sql: Optional[str] = None
    trace: Optional[list] = None
    mermaid: Optional[str] = None


# ── Endpoints ──

@router.post(
    "/discover",
    response_model=DiscoverResponse,
    summary="Full Discovery Pipeline",
    description="Searches demo catalog and uses Claude to rank/select best tables.",
)
async def discover(request: DiscoverRequest):
    """
    Run the full discovery pipeline:
    1. Search the flat-file catalog for candidate tables
    2. Send candidates to LLM (Discovery Council) for ranking
    3. Return top-K selected tables with confidence scores
    """
    from api.main import get_app_state
    total_start = time.time()

    logger.info("═" * 60)
    logger.info(f"📥 POST /discover")
    logger.info(f"   Query: \"{request.query}\"")
    logger.info(f"   Top-K: {request.top_k}")
    logger.info("═" * 60)

    state = get_app_state()
    llm = state.get("llm")
    catalog_path = state.get("catalog_path")

    if not llm:
        logger.error("❌ LLM not available — cannot run discovery council")
        raise HTTPException(
            status_code=503,
            detail="LLM not available. Ensure Ollama is running and restart the server.",
        )

    # ── Step 1: Flat-file catalog search ──
    logger.info("─" * 40)
    logger.info("🔍 STEP 1: Flat-file catalog search")
    t0 = time.time()
    connector = FlatFileConnector(catalog_path=catalog_path)
    candidates = connector.search(request.query)
    search_ms = (time.time() - t0) * 1000

    if not candidates:
        logger.warning(f"   ⚠️  No candidates found ({search_ms:.0f}ms)")
        logger.info("═" * 60)
        return DiscoverResponse(
            query=request.query,
            selected_tables=[],
            total_candidates=0,
            council_used=False,
        )

    logger.info(f"   ✅ Found {len(candidates)} candidate tables ({search_ms:.0f}ms):")
    for i, c in enumerate(candidates, 1):
        logger.info(f"      {i}. {c['name']:<30s}  score={c.get('score', 'N/A'):.2f}  source={c.get('source', '?')}")

    # ── Step 2: LLM Discovery Council ──
    logger.info("─" * 40)
    logger.info(f"🧠 STEP 2: LLM Discovery Council (Gemma 4)")
    logger.info(f"   Sending {len(candidates)} candidates to LLM for ranking...")
    t1 = time.time()

    council = DiscoveryCouncil(llm=llm, top_k=request.top_k)
    try:
        selected = council.evaluate(request.query, candidates)
        council_used = True
        council_ms = (time.time() - t1) * 1000
        logger.info(f"   ✅ Council returned {len(selected)} tables ({council_ms:.0f}ms)")
        for i, t in enumerate(selected, 1):
            name = t.get('name', '?')
            conf = t.get('confidence', t.get('score', 'N/A'))
            reason = t.get('reason', 'no reason provided')
            logger.info(f"      {i}. {name:<30s}  confidence={conf}")
            logger.info(f"         └─ {reason[:120]}")
    except Exception as e:
        council_ms = (time.time() - t1) * 1000
        logger.warning(f"   ⚠️  Council error ({council_ms:.0f}ms): {e}")
        logger.info(f"   ↩️  Falling back to keyword-ranked results (top {request.top_k})")
        selected = candidates[:request.top_k]
        council_used = False

    # ── Summary ──
    total_ms = (time.time() - total_start) * 1000
    logger.info("─" * 40)
    logger.info(f"📤 Response: {len(selected)} tables selected from {len(candidates)} candidates")
    logger.info(f"   Council used: {council_used}  |  Total time: {total_ms:.0f}ms")
    logger.info("═" * 60)

    return DiscoverResponse(
        query=request.query,
        selected_tables=selected,
        total_candidates=len(candidates),
        council_used=council_used,
    )


@router.post(
    "/discover/search",
    response_model=SearchResponse,
    summary="Flat-File Search Only",
    description="Keyword search against the demo catalog. No LLM call — free and instant.",
)
async def discover_search(request: DiscoverRequest):
    """
    Search the flat-file catalog using keyword matching only.
    Useful for debugging which tables the system finds before the LLM council.
    """
    from api.main import get_app_state

    logger.info(f"🔍 POST /discover/search  query=\"{request.query}\"")
    t0 = time.time()

    state = get_app_state()
    catalog_path = state.get("catalog_path")

    connector = FlatFileConnector(catalog_path=catalog_path)
    results = connector.search(request.query)
    elapsed_ms = (time.time() - t0) * 1000

    logger.info(f"   ✅ {len(results)} tables found ({elapsed_ms:.0f}ms):")
    for r in results:
        logger.info(f"      - {r['name']:<30s}  score={r.get('score', 'N/A'):.2f}")

    return SearchResponse(
        query=request.query,
        results=results,
        result_count=len(results),
    )


@router.get(
    "/discover/catalog",
    response_model=CatalogResponse,
    summary="View Full Catalog",
    description="Returns all tables in the demo catalog.",
)
async def get_catalog():
    """Return the complete demo catalog for inspection."""
    from api.main import get_app_state

    logger.info("📋 GET /discover/catalog")

    state = get_app_state()
    catalog_path = state.get("catalog_path")

    try:
        with open(catalog_path, "r") as f:
            tables = json.load(f)
    except Exception as e:
        logger.error(f"   ❌ Failed to load catalog: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load catalog: {e}",
        )

    logger.info(f"   ✅ Returning {len(tables)} tables")
    for t in tables:
        col_count = len(t.get('columns', []))
        logger.info(f"      - {t['name']:<30s}  ({col_count} columns)")

    return CatalogResponse(
        tables=tables,
        table_count=len(tables),
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="E2E LangGraph Pipeline",
    description="Run the full agentic pipeline end-to-end and get the final answer, SQL, trace, and mermaid layout.",
)
async def run_query(request: QueryRequest):
    """Execute the full agent pipeline for a query."""
    import time
    from config.config_loader import load_config
    from graph.graph_builder import build_graph

    logger.info("═" * 60)
    logger.info(f"🚀 POST /query")
    logger.info(f"   Question: \"{request.question}\"")
    logger.info("═" * 60)

    t0 = time.time()
    
    config = load_config()
    graph = build_graph(config)
    
    initial_state = {
        "user_query": request.question,
        "session_id": request.session_id,
        "discovered_tables": [],
        "selected_tables": [],
        "schema": {},
        "query_plan": {},
        "sql": "",
        "sql_history": [],
        "execution_result": None,
        "execution_error": None,
        "retry_count": 0,
        "validation_result": {},
        "summary": "",
        "confidence_score": 0.0,
        "needs_human": False,
        "final_answer": None,
        "memory_context": {},
        "error_log": [],
        "trace": [],
        "agent_mermaid": ""
    }
    
    thread = {"configurable": {"thread_id": request.session_id}}
    
    try:
        final_state = graph.invoke(initial_state, thread)
        elapsed_ms = (time.time() - t0) * 1000
        
        logger.info(f"   ✅ Finished in {elapsed_ms:.0f}ms")
        
        return QueryResponse(
            final_answer=final_state.get("final_answer") or final_state.get("summary"),
            sql=final_state.get("sql"),
            trace=final_state.get("trace", []),
            mermaid=final_state.get("agent_mermaid")
        )
    except Exception as e:
        elapsed_ms = (time.time() - t0) * 1000
        logger.error(f"   ❌ Pipeline error ({elapsed_ms:.0f}ms): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    summary="Health Check",
)
async def health():
    """Check API health and LLM status."""
    from api.main import get_app_state

    state = get_app_state()
    llm_ready = state.get("llm") is not None

    return {
        "status": "healthy",
        "llm_ready": llm_ready,
        "llm_model": "gemma4:latest (Ollama local)" if llm_ready else None,
        "catalog_path": state.get("catalog_path"),
    }
