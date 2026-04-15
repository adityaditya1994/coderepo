# Discovery Agent API — Local Testing

A FastAPI service that wraps the NLQ discovery agent for local testing.  
Uses **Claude Sonnet** as the LLM and a **flat-file demo catalog** (10 e-commerce tables).

## Quick Start

### 1. Install Dependencies

```bash
cd nlq_agent
pip3 install fastapi uvicorn langchain-anthropic python-dotenv pyyaml
```

### 2. Set Your API Key

Edit `api/.env` and replace the placeholder:

```bash
# api/.env
ANTHROPIC_API_KEY=sk-ant-api03-your-real-key-here
```

> ⚠️ The `api/.env` file is gitignored and will NOT be committed.

### 3. Start the Server

```bash
cd nlq_agent
uvicorn api.main:app --reload --port 8000
```

You should see:
```
🚀 Starting Discovery API...
  ✅ Claude Sonnet LLM initialized
  ✅ Demo catalog: .../api/demo_data/table_catalog.json
  ✅ Ready at http://localhost:8000
  📖 Docs at http://localhost:8000/docs
```

### 4. Open Interactive Docs

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser for Swagger UI.

---

## API Endpoints

### `GET /health` — Health Check

```bash
curl http://localhost:8000/health
```

### `GET /discover/catalog` — View Full Demo Catalog

```bash
curl http://localhost:8000/discover/catalog | python3 -m json.tool
```

### `POST /discover/search` — Keyword Search (No LLM)

Search the flat-file catalog without using Claude. Free and instant — useful for debugging.

```bash
curl -X POST http://localhost:8000/discover/search \
  -H "Content-Type: application/json" \
  -d '{"query": "total revenue by region", "top_k": 5}'
```

### `POST /discover` — Full Discovery Pipeline (with LLM)

Searches catalog → sends candidates to Claude Discovery Council → returns ranked tables.

```bash
curl -X POST http://localhost:8000/discover \
  -H "Content-Type: application/json" \
  -d '{"query": "total revenue by region for Q1 2024", "top_k": 5}'
```

---

## Example Queries to Try

| Query | Expected Tables |
|-------|----------------|
| `"total revenue by region"` | orders, regions, order_items |
| `"top 10 customers by lifetime value"` | customers |
| `"return rate by product category"` | returns, products, order_items |
| `"marketing campaign ROI"` | marketing_campaigns |
| `"average support ticket resolution time"` | customer_support_tickets |
| `"inventory levels for electronics"` | inventory, products |
| `"conversion rate from web sessions"` | web_sessions, orders |

## Demo Catalog

The demo catalog (`api/demo_data/table_catalog.json`) contains 10 interconnected e-commerce analytics tables:

| Table | Description |
|-------|-------------|
| `orders` | Fact table with order totals, dates, channels |
| `order_items` | Line-item details (quantity, unit_price) |
| `customers` | Customer master data with segments |
| `products` | Product catalog with categories, pricing |
| `regions` | Geographic dimension (NA, EMEA, APAC, LATAM) |
| `inventory` | Current stock levels by warehouse |
| `returns` | Product returns with reasons |
| `web_sessions` | Web/app traffic data |
| `marketing_campaigns` | Campaign spend and performance |
| `customer_support_tickets` | Support tickets and satisfaction |

## File Structure

```
api/
├── __init__.py           # Package init
├── main.py               # FastAPI app, LLM setup, lifespan
├── routes.py             # API endpoints
├── .env                  # Your Anthropic API key (gitignored)
├── .env.example          # Template (safe to commit)
├── README.md             # This file
└── demo_data/
    └── table_catalog.json  # 10-table demo catalog
```
