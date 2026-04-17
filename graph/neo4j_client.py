"""
Neo4j Entity Graph Client

Queries the knowledge graph that mem0 builds automatically during ingestion.

mem0 populates Neo4j with nodes and relationships extracted from each event:
  (Developer)-[:AUTHORED]->(Commit)
  (Developer)-[:OPENED]->(PullRequest)
  (PullRequest)-[:MODIFIES]->(Repository)
  (Developer)-[:COLLABORATES_WITH]->(Developer)

This client runs graph queries on top of that structure to surface
patterns that pure vector search (Qdrant) cannot find — e.g.
"which developers collaborate most?" or "which repos have the most activity?"
"""

from __future__ import annotations

import os
from typing import Any

from neo4j import GraphDatabase

NEO4J_URL = os.getenv("NEO4J_URL", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class KnowledgeGraphClient:
    def __init__(self) -> None:
        self.driver = GraphDatabase.driver(
            NEO4J_URL,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )

    def close(self) -> None:
        self.driver.close()

    def _run(self, query: str, **params: Any) -> list[dict]:
        with self.driver.session() as session:
            result = session.run(query, **params)
            return [record.data() for record in result]

    def get_developer_repositories(self, developer: str) -> list[str]:
        """Which repositories has this developer contributed to?"""
        results = self._run(
            """
            MATCH (d {name: $developer})-[]->(r)
            WHERE r.name IS NOT NULL
            RETURN DISTINCT r.name AS repo
            ORDER BY repo
            """,
            developer=developer,
        )
        return [r["repo"] for r in results if r.get("repo")]

    def get_collaborators(self, developer: str) -> list[dict]:
        """Which developers share repositories with this developer?"""
        results = self._run(
            """
            MATCH (d1 {name: $developer})-[]->(shared)<-[]-(d2)
            WHERE d2.name <> $developer AND d2.name IS NOT NULL
            RETURN d2.name AS collaborator, count(*) AS shared_items
            ORDER BY shared_items DESC
            LIMIT 10
            """,
            developer=developer,
        )
        return results

    def get_most_active_repositories(self) -> list[dict]:
        """Which repositories have the most activity across all developers?"""
        results = self._run(
            """
            MATCH ()-[]->(r)
            WHERE r.name IS NOT NULL
            RETURN r.name AS repository, count(*) AS activity_count
            ORDER BY activity_count DESC
            LIMIT 10
            """
        )
        return results

    def get_all_developers(self) -> list[str]:
        """List all developers who have activity in the graph."""
        results = self._run(
            """
            MATCH (d)
            WHERE d.name IS NOT NULL AND (d)-[]-()
            RETURN DISTINCT d.name AS developer
            ORDER BY developer
            """
        )
        return [r["developer"] for r in results if r.get("developer")]
