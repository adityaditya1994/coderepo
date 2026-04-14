"""
Discovery Agent — orchestrates all 4 metadata connectors
in parallel, then feeds results to the Discovery Council
for ranking and selection.
"""

import asyncio
import concurrent.futures
from typing import List

from agents.discovery.glue_connector import GlueConnector
from agents.discovery.pinecone_connector import PineconeConnector
from agents.discovery.datahub_connector import DataHubConnector
from agents.discovery.flatfile_connector import FlatFileConnector
from agents.discovery.discovery_council import DiscoveryCouncil


class DiscoveryAgent:
    """Run all discovery connectors and let the council pick the best tables."""

    def __init__(self, config: dict, llm):
        self.config = config
        self.llm = llm
        self.enabled_sources = config.get("discovery", {}).get("sources", [])
        self.top_k = config.get("discovery", {}).get("top_k", 5)

    def discover(self, user_query: str) -> List[dict]:
        """
        Run all enabled connectors, merge results, run council.

        Returns
        -------
        list[dict]
            Selected tables from the discovery council.
        """
        candidates = self._run_connectors(user_query)
        council = DiscoveryCouncil(llm=self.llm, top_k=self.top_k)
        return council.evaluate(user_query, candidates)

    def _run_connectors(self, query: str) -> List[dict]:
        """Run enabled connectors in parallel using ThreadPoolExecutor."""
        connectors = self._build_connectors()
        all_results: List[dict] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(conn.search, query): name
                for name, conn in connectors.items()
            }
            for future in concurrent.futures.as_completed(futures):
                source_name = futures[future]
                try:
                    results = future.result(timeout=30)
                    all_results.extend(results)
                except Exception as e:
                    # Log but don't fail — other sources may succeed
                    print(f"[Discovery] {source_name} failed: {e}")

        return all_results

    def _build_connectors(self) -> dict:
        """Instantiate only the connectors that are enabled in config."""
        connectors = {}
        db_config = self.config.get("database", {})
        region = db_config.get("athena", {}).get("region", "us-east-1")

        if "glue" in self.enabled_sources:
            connectors["glue"] = GlueConnector(region=region)

        if "pinecone" in self.enabled_sources:
            connectors["pinecone"] = PineconeConnector(self.config)

        if "datahub" in self.enabled_sources:
            connectors["datahub"] = DataHubConnector(self.config)

        if "flatfile" in self.enabled_sources:
            connectors["flatfile"] = FlatFileConnector()

        return connectors
