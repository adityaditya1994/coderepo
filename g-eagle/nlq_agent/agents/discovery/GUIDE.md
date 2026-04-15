# Discovery Agent — How It Works & Local Testing Guide

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [How the Discovery Agent Works](#how-the-discovery-agent-works)
- [API Endpoints](#api-endpoints)
- [Start / Stop / Test Locally](#start--stop--test-locally)
- [Code Walkthrough](#code-walkthrough)

---

## Architecture Overview

```
User Query ("total revenue by region")
        │
        ▼
┌──────────────────────────────────┐
│       FastAPI  (api/routes.py)   │   ← HTTP layer
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  STEP 1: Flat-File Connector     │   ← Keyword search over JSON catalog
│  (flatfile_connector.py)         │
│                                  │
│  Input:  user query              │
│  Output: candidate tables        │
│          (scored by token match)  │
└──────────┬───────────────────────┘
           │ candidates[]
           ▼
┌──────────────────────────────────┐
│  STEP 2: Discovery Council       │   ← LLM-powered ranking (Gemma 4)
│  (discovery_council.py)          │
│                                  │
│  Input:  user query + candidates │
│  Output: top-K ranked tables     │
│          with confidence scores  │
└──────────┬───────────────────────┘
           │ selected_tables[]
           ▼
       JSON Response
```

---

## How the Discovery Agent Works

### Step 1: Flat-File Keyword Search

The `FlatFileConnector` loads a JSON catalog and scores each table by how many query tokens appear in its metadata (name, description, tags, column names).

**Key code** (`flatfile_connector.py`):

```python
def search(self, query: str) -> List[dict]:
    query_tokens = set(query.lower().split())

    for table in catalog:
        # Build searchable text from name, description, tags, column names
        searchable = " ".join([
            table.get("name", ""),
            table.get("description", ""),
            " ".join(table.get("tags", [])),
            " ".join(c.get("name", "") for c in table.get("columns", [])),
        ]).lower()

        # Score = fraction of query tokens found in the table metadata
        matches = sum(1 for token in query_tokens if token in searchable)
        if matches > 0:
            results.append({...table, "score": matches / len(query_tokens)})

    return sorted(results, key=lambda x: x["score"], reverse=True)[:10]
```

**Example**: For query `"total revenue by region"`, the tokens are `{total, revenue, by, region}`.
- `orders` table matches "revenue" and "region" → score = 2/4 = 0.50
- `regions` table matches "region" → score = 1/4 = 0.25

### Step 2: LLM Discovery Council

The `DiscoveryCouncil` sends all candidate tables to the LLM with a detailed prompt asking it to deduplicate, score (0.0–1.0), and select the top-K most relevant tables.

**Key code** (`discovery_council.py`):

```python
def evaluate(self, user_query: str, candidates: List[dict]) -> List[dict]:
    # Format the prompt with query + all candidates as JSON
    prompt = DISCOVERY_COUNCIL_PROMPT.format(
        user_query=user_query,
        candidates=json.dumps(candidates, indent=2),
        top_k=self.top_k,
    )

    # Call the LLM (Gemma 4 via Ollama)
    response = self.llm.invoke(prompt)

    # Parse JSON response → extract selected_tables
    result = json.loads(self._extract_json(content))
    return result.get("selected_tables", [])
```

**The prompt** (`prompts/discovery.py`) instructs the LLM to:
1. **Understand** the user query — what data is needed?
2. **Deduplicate** — same table from different sources = one entry
3. **Score** each table 0.0–1.0 based on column relevance, table type, join keys
4. **Select** top-K tables, never including tables scored below 0.5
5. **Explain** reasoning for each selection

### Step 3: API Response

The API route in `api/routes.py` orchestrates these two steps and returns a structured JSON response:

```python
@router.post("/discover")
async def discover(request: DiscoverRequest):
    # Step 1: Flat-file search
    connector = FlatFileConnector(catalog_path=catalog_path)
    candidates = connector.search(request.query)

    # Step 2: LLM council ranking
    council = DiscoveryCouncil(llm=llm, top_k=request.top_k)
    selected = council.evaluate(request.query, candidates)

    return DiscoverResponse(
        query=request.query,
        selected_tables=selected,
        total_candidates=len(candidates),
        council_used=True,
    )
```

---

## API Endpoints

| Method | Path | LLM? | Description |
|--------|------|------|-------------|
| `POST` | `/discover` | ✅ Yes | Full pipeline: keyword search → LLM ranking |
| `POST` | `/discover/search` | ❌ No | Keyword search only (instant, free) |
| `GET` | `/discover/catalog` | ❌ No | View all tables in the demo catalog |
| `GET` | `/health` | ❌ No | Check server & LLM status |

**Request body** (for POST endpoints):
```json
{
  "query": "total revenue by region for Q1 2024",
  "top_k": 3
}
```

**Response** (from `/discover`):
```json
{
  "query": "total revenue by region for Q1 2024",
  "selected_tables": [
    {
      "name": "orders",
      "confidence": 0.95,
      "reason": "Contains total_amount, order_date, region_id..."
    }
  ],
  "total_candidates": 6,
  "council_used": true
}
```

---

## Start / Stop / Test Locally

### Prerequisites

```bash
# 1. Ensure Ollama is installed and Gemma 4 is pulled
ollama list                     # Should show gemma4:latest

# 2. Install Python dependencies (one-time)
cd nlq_agent
pip3 install fastapi uvicorn langchain-ollama python-dotenv pyyaml
```

### Start the Server

```bash
cd nlq_agent
uvicorn api.main:app --reload --port 8000
```

You should see:
```
00:00:01 │ discovery-api    │ INFO  │ 🚀 Starting Discovery API...
00:00:01 │ discovery-api    │ INFO  │ Connecting to Ollama at http://localhost:11434 with model 'gemma4:latest'
00:00:01 │ discovery-api    │ INFO  │ ✅ LLM initialized: gemma4:latest (Ollama local)
00:00:01 │ discovery-api    │ INFO  │ ✅ Demo catalog loaded
00:00:01 │ discovery-api    │ INFO  │ ✅ Ready at http://localhost:8000
00:00:01 │ discovery-api    │ INFO  │ 📖 Swagger docs at http://localhost:8000/docs
```

### Stop the Server

```bash
# Option 1: Press Ctrl+C in the terminal running uvicorn

# Option 2: Kill by port
lsof -ti:8000 | xargs kill -9
```

### Test the Endpoints

#### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status": "healthy", "llm_ready": true, "llm_model": "gemma4:latest (Ollama local)"}
```

#### 2. View Demo Catalog

```bash
curl http://localhost:8000/discover/catalog | python3 -m json.tool
```

Shows all 10 tables: `orders`, `order_items`, `customers`, `products`, `regions`, `inventory`, `returns`, `web_sessions`, `marketing_campaigns`, `customer_support_tickets`.

#### 3. Keyword Search (No LLM — Instant)

```bash
curl -X POST http://localhost:8000/discover/search \
  -H "Content-Type: application/json" \
  -d '{"query": "total revenue by region", "top_k": 5}'
```

#### 4. Full Discovery with LLM Ranking

```bash
curl -X POST http://localhost:8000/discover \
  -H "Content-Type: application/json" \
  -d '{"query": "total revenue by region for Q1 2024", "top_k": 3}'
```

> ⏱️ **Note**: Gemma 4 runs locally, so the LLM step takes 30–120 seconds depending on your machine. Watch the server logs for step-by-step progress.

#### 5. Interactive Swagger UI

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to test endpoints interactively.

### Example Queries to Try

| Query | Expected Top Tables |
|-------|-------------------|
| `"total revenue by region"` | orders, regions, order_items |
| `"top customers by lifetime value"` | customers |
| `"return rate by product category"` | returns, products, order_items |
| `"marketing campaign ROI"` | marketing_campaigns |
| `"support ticket resolution time"` | customer_support_tickets |
| `"inventory levels for electronics"` | inventory, products |
| `"conversion rate from web sessions"` | web_sessions, orders |

---

## Code Walkthrough

### File Map

```
agents/discovery/
├── discovery_agent.py      # Orchestrator — runs all connectors in parallel
├── discovery_council.py    # LLM jury — ranks and selects top-K tables
├── flatfile_connector.py   # Searches local JSON catalog by keyword matching
├── glue_connector.py       # AWS Glue metadata search (production)
├── pinecone_connector.py   # Vector similarity search (production)
├── datahub_connector.py    # DataHub GraphQL search (production)
└── GUIDE.md                # ← This file

api/
├── main.py                 # FastAPI app — LLM init, lifespan, env loading
├── routes.py               # API endpoints with step-by-step logging
├── demo_data/
│   └── table_catalog.json  # 10-table e-commerce demo catalog
├── .env                    # Ollama config (gitignored)
└── README.md               # Quick-start README

prompts/
└── discovery.py            # Discovery Council prompt template
```

### Key Classes

| Class | File | Role |
|-------|------|------|
| `DiscoveryAgent` | `discovery_agent.py` | Runs all enabled connectors in parallel using `ThreadPoolExecutor`, merges results, then feeds them to the council |
| `DiscoveryCouncil` | `discovery_council.py` | Sends candidates to the LLM with a structured prompt, parses the JSON response, returns top-K tables |
| `FlatFileConnector` | `flatfile_connector.py` | Loads a JSON catalog file, scores tables by keyword overlap, returns top 10 matches |
| `GlueConnector` | `glue_connector.py` | Queries AWS Glue Data Catalog for table metadata (requires AWS credentials) |
| `PineconeConnector` | `pinecone_connector.py` | Vector similarity search over pre-embedded table descriptions |
| `DataHubConnector` | `datahub_connector.py` | Queries DataHub's GraphQL API for table metadata |

### LLM Integration

The API creates the LLM in `api/main.py`:

```python
def _create_llm():
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model="gemma4:latest",          # Local Ollama model
        base_url="http://localhost:11434",
        temperature=0.0,                # Deterministic output
    )
```

The `DiscoveryCouncil` receives this LLM instance and calls `llm.invoke(prompt)` with the discovery prompt from `prompts/discovery.py`. The prompt asks the LLM to return structured JSON with selected tables, confidence scores, and reasoning.

### Demo Catalog

The demo catalog (`api/demo_data/table_catalog.json`) contains 10 interconnected tables simulating an e-commerce analytics database:

```
orders ───────┐
              ├──► order_items ◄── products
customers ────┘                     │
    │                          inventory
    │
regions ◄─── marketing_campaigns
    │
web_sessions     returns     customer_support_tickets
```

Each table has: `name`, `database`, `description`, `tags`, and full `columns` with types and descriptions.
