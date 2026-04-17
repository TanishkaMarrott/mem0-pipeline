"""
mem0 Pipeline — Main Runner

End-to-end flow:
  1. Ingest GitHub events → mem0 (Qdrant + Neo4j + Ollama)
  2. Generate developer insights — per-developer deep profile
  3. Generate cohort insight — team-wide patterns

Usage:
  python main.py

Set DEMO_MODE=true in .env to run without GitHub credentials.
"""

from __future__ import annotations

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

load_dotenv()

from graph.neo4j_client import KnowledgeGraphClient
from pipeline.ingestion import GitHubIngestion
from pipeline.insight_generator import InsightGenerator
from pipeline.memory_store import DeveloperMemoryStore

console = Console()


def main() -> None:
    console.print(Rule("[bold]mem0 Pipeline[/bold]"))
    console.print("[dim]GitHub Events → mem0 (Qdrant + Neo4j + Ollama) → Claude Insights[/dim]\n")

    # Initialise components
    store = DeveloperMemoryStore()
    graph = KnowledgeGraphClient()

    # Step 1 — ingest GitHub events into mem0
    console.print(Rule("[cyan]Step 1 — Ingestion[/cyan]"))
    ingestion = GitHubIngestion(store=store)
    counts = ingestion.run()
    developers = list(counts.keys())

    console.print(f"\n[green]✓[/green] {sum(counts.values())} events ingested for {len(developers)} developers\n")

    # Step 2 — generate insights
    console.print(Rule("[magenta]Step 2 — Insights[/magenta]"))
    generator = InsightGenerator(store=store, graph=graph)
    dev_insights, cohort_insight = generator.run(developers)

    # Step 3 — print results
    console.print(Rule("[bold green]Developer Insights[/bold green]"))
    for insight in dev_insights:
        console.print(f"\n[bold cyan]{insight.developer}[/bold cyan]")
        console.print(Markdown(insight.activity_summary))

    console.print(Rule("[bold green]Cohort Insight[/bold green]"))
    console.print(Markdown(cohort_insight.summary))

    console.print(Rule("[bold]Complete[/bold]"))
    console.print(f"  Developers profiled: {len(dev_insights)}")
    console.print(f"  Total events in memory: {sum(counts.values())}")
    console.print(f"\n  Qdrant UI:  http://localhost:6333/dashboard")
    console.print(f"  Neo4j UI:   http://localhost:7474\n")

    graph.close()


if __name__ == "__main__":
    main()
