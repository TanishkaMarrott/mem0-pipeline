"""
mem0 Memory Store

Wraps mem0 configured with:
  - Qdrant  — vector store for semantic search over facts
  - Neo4j   — entity graph (developer → PR → repository relationships)
  - Ollama  — local LLM for fact extraction + embeddings (no API cost)

mem0 automatically:
  - Extracts structured facts from raw text
  - Embeds facts into Qdrant
  - Identifies entities and builds relationships in Neo4j
  - Deduplicates and updates existing memories

Each developer has their own user_id in mem0 — memories are
isolated per developer but the underlying graph connects them.
"""

from __future__ import annotations

import os
from typing import Optional

from mem0 import Memory

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
NEO4J_URL = os.getenv("NEO4J_URL", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.1:8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

MEM0_CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": QDRANT_HOST,
            "port": QDRANT_PORT,
            "collection_name": "developer-memory",
        },
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": NEO4J_URL,
            "username": NEO4J_USERNAME,
            "password": NEO4J_PASSWORD,
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": OLLAMA_LLM_MODEL,
            "base_url": OLLAMA_BASE_URL,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": OLLAMA_EMBED_MODEL,
            "base_url": OLLAMA_BASE_URL,
        },
    },
}


class DeveloperMemoryStore:
    """
    mem0-backed memory store scoped per developer.

    Each add() call:
      1. Sends raw event text to the Ollama LLM for fact extraction
      2. Embeds extracted facts into Qdrant (semantic search)
      3. Extracts entities + relationships into Neo4j (graph traversal)
    """

    def __init__(self) -> None:
        self.memory = Memory.from_config(MEM0_CONFIG)

    def add(self, content: str, developer: str, metadata: Optional[dict] = None) -> None:
        """Ingest a GitHub event into memory for a specific developer."""
        self.memory.add(
            content,
            user_id=developer,
            metadata=metadata or {},
        )

    def search(self, query: str, developer: str, limit: int = 10) -> list[dict]:
        """Semantic search over a developer's memories."""
        results = self.memory.search(query, user_id=developer, limit=limit)
        return results.get("results", []) if isinstance(results, dict) else results

    def get_all(self, developer: str) -> list[dict]:
        """Retrieve all memories for a developer."""
        results = self.memory.get_all(user_id=developer)
        return results.get("results", []) if isinstance(results, dict) else results

    def get_all_developers(self, developers: list[str]) -> dict[str, list[dict]]:
        """Retrieve memories for multiple developers at once."""
        return {dev: self.get_all(dev) for dev in developers}
