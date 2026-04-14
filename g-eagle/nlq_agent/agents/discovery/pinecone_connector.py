"""
Pinecone connector — performs vector similarity search
over pre-indexed schema/table metadata.
"""

from typing import List


class PineconeConnector:
    """Search Pinecone for semantically similar table metadata."""

    def __init__(self, config: dict):
        from pinecone import Pinecone
        from langchain_openai import OpenAIEmbeddings

        pc = Pinecone(api_key=config.get("PINECONE_API_KEY", ""))
        self.index = pc.Index(config["pinecone"]["index_name"])
        self.embedder = OpenAIEmbeddings(
            model=config["pinecone"]["embedding_model"],
            api_key=config.get("OPENAI_API_KEY", ""),
        )

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """
        Embed the query and search Pinecone for matching schema metadata.

        Returns
        -------
        list[dict]
            Normalized table metadata dicts.
        """
        try:
            vector = self.embedder.embed_query(query)
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True,
            )
        except Exception:
            return []

        return [
            {
                "source": "pinecone",
                "name": m["metadata"].get("table_name", ""),
                "database": m["metadata"].get("database", ""),
                "columns": m["metadata"].get("columns", []),
                "description": m["metadata"].get("description", ""),
                "score": m.get("score", 0.0),
            }
            for m in results.get("matches", [])
        ]
