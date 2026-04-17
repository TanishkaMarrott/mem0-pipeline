"""
Insight Generator

Uses Claude to reason over memories retrieved from mem0 (Qdrant + Neo4j).

Two insight types:
  1. Developer insight  — deep profile of one developer's contributions
  2. Cohort insight     — patterns across all developers in the team

Claude does NOT search mem0 directly. The pipeline:
  1. Retrieves relevant memories via mem0.search()
  2. Queries the Neo4j graph for structural relationships
  3. Passes both to Claude as context
  4. Claude synthesises a natural-language insight

This separation keeps retrieval deterministic and reasoning in Claude.
"""

from __future__ import annotations

import os

import anthropic
from rich.console import Console
from rich.panel import Panel

from graph.neo4j_client import KnowledgeGraphClient
from models.schemas import CohortInsight, DeveloperInsight
from pipeline.memory_store import DeveloperMemoryStore

console = Console()

SYSTEM_PROMPT = """You are a developer activity analyst. You receive:
- A list of memory facts about a developer or team (from a mem0 vector store)
- Graph data showing entity relationships (from Neo4j)

Generate clear, specific insights. Be concrete — reference actual repositories,
PR titles, or activity patterns you see in the data.
Do not invent facts. Only use what is in the provided context.
"""


class InsightGenerator:
    def __init__(self, store: DeveloperMemoryStore, graph: KnowledgeGraphClient) -> None:
        self.store = store
        self.graph = graph
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-opus-4-6"

    def _ask_claude(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def developer_insight(self, developer: str) -> DeveloperInsight:
        """Generate a deep profile of one developer."""
        console.print(f"  [yellow]→ Generating insight for:[/yellow] {developer}")

        # Step 1 — retrieve memories from Qdrant via mem0
        contribution_memories = self.store.search(
            f"what does {developer} work on?", developer=developer, limit=15
        )
        pattern_memories = self.store.search(
            f"{developer} recent activity", developer=developer, limit=10
        )

        # Step 2 — query Neo4j graph for structural data
        repositories = self.graph.get_developer_repositories(developer)
        collaborators = self.graph.get_collaborators(developer)

        # Step 3 — build context for Claude
        memory_text = "\n".join(
            f"- {m['memory']}" for m in (contribution_memories + pattern_memories)
            if m.get("memory")
        )
        graph_text = (
            f"Repositories contributed to: {', '.join(repositories) or 'none found'}\n"
            f"Collaborators: {', '.join(c['collaborator'] for c in collaborators[:5]) or 'none found'}"
        )

        prompt = f"""Developer: {developer}

Memory facts (from Qdrant semantic search):
{memory_text or 'No memories found.'}

Graph relationships (from Neo4j):
{graph_text}

Generate a developer insight covering:
1. Main contribution areas (which repos, what type of work)
2. Activity patterns (frequency, consistency)
3. Collaboration style (who they work with)
4. One notable observation"""

        insight_text = self._ask_claude(prompt)

        return DeveloperInsight(
            developer=developer,
            activity_summary=insight_text,
            contribution_areas=repositories[:5],
            memory_count=len(contribution_memories),
        )

    def cohort_insight(self, developers: list[str]) -> CohortInsight:
        """Generate team-wide patterns across all developers."""
        console.print(f"  [yellow]→ Generating cohort insight for {len(developers)} developers[/yellow]")

        # Retrieve memories for all developers
        all_memories: list[str] = []
        for dev in developers:
            memories = self.store.search("recent activity contributions", developer=dev, limit=5)
            for m in memories:
                if m.get("memory"):
                    all_memories.append(f"[{dev}] {m['memory']}")

        # Graph-level patterns
        active_repos = self.graph.get_most_active_repositories()

        memory_text = "\n".join(all_memories[:40])
        repo_text = "\n".join(
            f"- {r['repository']}: {r['activity_count']} activities"
            for r in active_repos[:10]
        )

        prompt = f"""Team developers: {', '.join(developers)}

Recent activity memories across the team:
{memory_text or 'No memories found.'}

Most active repositories:
{repo_text or 'No repository data.'}

Generate a cohort insight covering:
1. Which repositories are most active
2. Collaboration patterns — who works together
3. Any concentration risks (single developer owning critical areas)
4. Team velocity observations"""

        insight_text = self._ask_claude(prompt)

        return CohortInsight(
            active_developers=developers,
            top_repositories=[r["repository"] for r in active_repos[:5]],
            summary=insight_text,
        )

    def run(self, developers: list[str]) -> tuple[list[DeveloperInsight], CohortInsight]:
        console.print(Panel("[bold green]Insight Generator[/bold green] reasoning over memory...", expand=False))

        dev_insights = []
        for dev in developers:
            insight = self.developer_insight(dev)
            dev_insights.append(insight)
            console.print(f"  [green]✓[/green] {dev} insight generated")

        cohort = self.cohort_insight(developers)
        console.print(f"  [green]✓[/green] Cohort insight generated")

        return dev_insights, cohort
