"""Prompt templates for the Discovery system."""

DISCOVERY_COUNCIL_PROMPT = """
You are a senior data architect acting as a discovery council.

You have received candidate tables from multiple metadata sources
(Glue Catalog, Vector Search, DataHub, Flat Files).

Some may be duplicates. Some may be irrelevant.

User Query: {user_query}

Candidate Tables:
{candidates}

Your Task:
1. Deduplicate tables (same table from multiple sources = one entry)
2. Score each table for relevance (0.0 to 1.0)
3. Select the TOP {top_k} most relevant tables
4. Explain why each was chosen

Output JSON only:
{{
  "selected_tables": [
    {{
      "name": "table_name",
      "database": "db_name",
      "source": "glue|pinecone|datahub|flatfile",
      "confidence": 0.0-1.0,
      "reason": "why this table is relevant"
    }}
  ]
}}
"""
