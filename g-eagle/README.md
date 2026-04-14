# 🦅 G-Eagle — NLQ Agent

> **Natural Language → SQL → Business Insights**
>
> A production-grade multi-agent system built on [LangGraph](https://github.com/langchain-ai/langgraph) that translates natural language questions into SQL queries, executes them, validates results, and returns human-readable summaries.

![Architecture](nlq_agent/docs/architecture.png)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Source Discovery** | Searches Glue Catalog, Pinecone vector DB, DataHub, and flat-file catalogs in parallel to find the right tables |
| **LLM-Powered Query Planning** | Converts natural language into a structured analytical plan before writing SQL |
| **Self-Healing Execution** | Classifies SQL errors and auto-fixes with configurable retry limits |
| **4-Layer Validation Council** | Schema + Logic + Data Sanity + Business validation with weighted confidence scoring |
| **Metrics Knowledge Base** | Org-wide metric definitions (revenue, active users, etc.) with approval workflows |
| **3-Layer Memory** | Session context, SQLite history, and Pinecone semantic search over past queries |
| **Human Handoff** | Graceful escalation when confidence is too low or retries exhausted |
| **Multi-LLM Support** | Swap between OpenAI, Anthropic, and Google Gemini via config |
| **Multi-DB Support** | Athena today, extensible to Snowflake, Postgres, BigQuery |

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
cd nlq_agent
pip install -r requirements.txt
```

### 2. Configure

Edit `nlq_agent/config/config.yaml` to set your LLM provider, database, and discovery sources.

Add your secrets to `nlq_agent/config/.env`:

```env
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
PINECONE_API_KEY=...
```

### 3. Run

```bash
cd nlq_agent
python main.py
```

You'll get an interactive prompt:

```
══════════════════════════════════════════════════════════════
  🦅 G-Eagle NLQ Agent
  Natural Language → SQL → Insights
══════════════════════════════════════════════════════════════
✅ Agent graph compiled successfully.

📝 Enter your question (or 'quit'): Show me total revenue by region for last month
```

---

## 🏗️ Architecture

See [`DESIGN.md`](DESIGN.md) for the full architecture deep-dive.

### Agent Flow

```
User Query → Supervisor → Discovery → Schema Retriever → Query Planner
→ SQL Generator → Executor ──→ Validation Council → Summarizer → Output
                         ↘ (error) → SQL Fixer → Executor (retry)
                         ↘ (exhausted) → Human Handoff
```

### Project Structure

```
nlq_agent/
├── config/          # YAML config + .env secrets
├── graph/           # LangGraph state, edges, graph builder
├── agents/
│   ├── discovery/   # 4 connectors + council + orchestrator
│   ├── executor/    # Base executor + Athena implementation
│   └── validation/  # 4 validators + aggregating council
├── prompts/         # All LLM prompt templates
├── memory/          # Short-term, long-term, semantic memory
├── knowledge_base/  # Metrics definitions + CRUD + feedback loop
├── llm/             # LLM factory (OpenAI/Anthropic/Gemini)
├── db/              # DB executor factory
├── evaluation/      # Accuracy & scoring framework
└── main.py          # CLI entry point
```

---

## ⚙️ Configuration

All knobs live in `config/config.yaml`:

| Section | Key Options |
|---------|-------------|
| `llm` | `provider` (openai/anthropic/gemini), `model`, `temperature` |
| `database` | `provider` (athena), region, S3 output, database name |
| `discovery` | `sources` list, `top_k` tables to select |
| `retry` | `max_attempts` for self-healing loop |
| `memory` | Toggle `short_term`, `long_term`, `semantic` independently |
| `human_fallback` | `confidence_threshold` below which to escalate |

---

## 📊 Evaluation

The built-in evaluation framework measures:

- **Discovery accuracy** — % correct tables identified
- **SQL correctness** — % queries returning expected results
- **Retry rate** — avg retries per query (lower = better)
- **Validation pass rate** — % passing council without retry
- **End-to-end latency** — seconds from query to answer
- **Human escalation rate** — % queries needing human

```python
from evaluation.evaluator import Evaluator

evaluator = Evaluator(graph, config)
result = evaluator.run_suite(test_cases)
print(evaluator.report())
```

---

## 🗺️ Roadmap

| Week | Milestone |
|------|-----------|
| 1 | Config + factories + state skeleton |
| 2 | Discovery system (Glue + Pinecone + council) |
| 3 | Schema retriever + query planner |
| 4 | SQL generator + Athena executor |
| 5 | Error classifier + SQL fixer + retry loop |
| 6 | Validation council (all 4 layers) |
| 7 | Metrics KB + approval flow |
| 8 | Memory (all 3 layers) |
| 9 | Summarizer + supervisor + human handoff |
| 10 | Evaluation framework + tracing |

---

## 📄 License

Internal / Private repository.
