"""
Semantic Memory — Pinecone-backed embedding store for
past queries, enabling similarity retrieval of successful
query patterns.
"""

from typing import List


class SemanticMemory:
    """Vector-based semantic search over past query patterns."""

    def __init__(self, config: dict):
        self.enabled = config.get("memory", {}).get("semantic", False)
        self.config = config

        if self.enabled:
            try:
                from pinecone import Pinecone
                from langchain_openai import OpenAIEmbeddings

                pc = Pinecone(api_key=config.get("PINECONE_API_KEY", ""))
                self.index = pc.Index(
                    config.get("pinecone", {}).get("index_name", "schema-metadata")
                )
                self.embedder = OpenAIEmbeddings(
                    model=config.get("pinecone", {}).get(
                        "embedding_model", "text-embedding-3-small"
                    ),
                    api_key=config.get("OPENAI_API_KEY", ""),
                )
            except Exception:
                self.enabled = False

    def store(self, query_id: str, user_query: str, sql: str, metadata: dict = None):
        """
        Store a successful query pattern as a vector.

        Parameters
        ----------
        query_id : str
            Unique ID for this query.
        user_query : str
            The original natural-language query.
        sql : str
            The generated SQL that succeeded.
        metadata : dict, optional
            Additional metadata to store with the vector.
        """
        if not self.enabled:
            return

        try:
            vector = self.embedder.embed_query(user_query)
            meta = {
                "user_query": user_query,
                "sql": sql,
                **(metadata or {}),
            }
            self.index.upsert(
                vectors=[(query_id, vector, meta)],
                namespace="query_patterns",
            )
        except Exception:
            pass  # Graceful degradation

    def search(self, query: str, top_k: int = 3) -> List[dict]:
        """
        Find similar past queries.

        Returns
        -------
        list[dict]
            Past query patterns with similarity scores.
        """
        if not self.enabled:
            return []

        try:
            vector = self.embedder.embed_query(query)
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True,
                namespace="query_patterns",
            )
            return [
                {
                    "user_query": m["metadata"].get("user_query", ""),
                    "sql": m["metadata"].get("sql", ""),
                    "score": m.get("score", 0.0),
                }
                for m in results.get("matches", [])
            ]
        except Exception:
            return []
