"""
FastAPI Discovery Agent — Local Testing Server

This is a standalone API that wraps the NLQ discovery agent for local testing.
It uses Claude Sonnet as the LLM and the flat-file connector with demo data.

Run with:
    cd nlq_agent && uvicorn api.main:app --reload --port 8000
"""

import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

# ── Configure logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-18s │ %(levelname)-5s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("discovery-api")

# ── Ensure nlq_agent root is on sys.path so existing modules are importable ──
NLQ_ROOT = Path(__file__).parent.parent
if str(NLQ_ROOT) not in sys.path:
    sys.path.insert(0, str(NLQ_ROOT))

# ── Load .env files (api/.env first, then config/.env as fallback) ──
_API_DIR = Path(__file__).parent
_ENV_FILE = _API_DIR / ".env"
_CONFIG_ENV = _API_DIR.parent / "config" / ".env"

# Load config/.env first (base), then api/.env overrides it
load_dotenv(_CONFIG_ENV, override=False)
load_dotenv(_ENV_FILE, override=True)


def _create_llm():
    """Create a LangChain ChatOllama instance using local Gemma 4."""
    from langchain_ollama import ChatOllama

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma4:latest")

    logger.info(f"Connecting to Ollama at {base_url} with model '{model}'")

    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=0.0,
    )


# ── Shared state for the app ──
_app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LLM and connectors on startup."""
    logger.info("🚀 Starting Discovery API...")

    try:
        llm = _create_llm()
        _app_state["llm"] = llm
        model_name = os.getenv("OLLAMA_MODEL", "gemma4:latest")
        logger.info(f"✅ LLM initialized: {model_name} (Ollama local)")
    except Exception as e:
        logger.warning(f"⚠️  LLM init failed: {e}")
        logger.warning("→ /discover endpoint will fail, but /discover/search and /discover/catalog will work")
        _app_state["llm"] = None

    # Flat-file catalog path
    catalog_path = str(_API_DIR / "demo_data" / "table_catalog.json")
    _app_state["catalog_path"] = catalog_path
    logger.info(f"✅ Demo catalog loaded: {catalog_path}")

    logger.info("✅ Ready at http://localhost:8000")
    logger.info("📖 Swagger docs at http://localhost:8000/docs")

    yield  # App running

    logger.info("🛑 Shutting down Discovery API")


# ── Create the FastAPI app ──
app = FastAPI(
    title="NLQ Discovery Agent API",
    description=(
        "Local testing API for the NLQ discovery agent. "
        "Uses Claude Sonnet for table ranking and a flat-file demo catalog."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


def get_app_state():
    """Access shared app state (LLM, config) from routes."""
    return _app_state


# ── Register routes ──
from api.routes import router  # noqa: E402
from api.agent_routes import router as agent_router  # noqa: E402

app.include_router(router)
app.include_router(agent_router)
