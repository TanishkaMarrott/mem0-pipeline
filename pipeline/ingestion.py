"""
GitHub Event Ingestion

Fetches developer activity from GitHub API and feeds it into
the mem0 memory store.

In DEMO_MODE=true — reads from demo/mock_github_events.json
In DEMO_MODE=false — fetches live from GitHub API via PyGithub

Each event is:
  1. Converted to plain-language text via to_memory_content()
  2. Added to mem0 under the developer's user_id
  3. mem0 handles extraction → Qdrant + Neo4j automatically
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from rich.console import Console

from models.schemas import EventType, GitHubEvent
from pipeline.memory_store import DeveloperMemoryStore

console = Console()

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_ORG = os.getenv("GITHUB_ORG", "")
MOCK_DATA_PATH = Path(__file__).parent.parent / "demo" / "mock_github_events.json"


def _load_mock_events() -> list[GitHubEvent]:
    with open(MOCK_DATA_PATH) as f:
        raw = json.load(f)
    return [GitHubEvent(**e) for e in raw]


def _fetch_live_events() -> list[GitHubEvent]:
    from github import Github

    gh = Github(GITHUB_TOKEN)
    events: list[GitHubEvent] = []

    target = gh.get_organization(GITHUB_ORG) if GITHUB_ORG else gh.get_user()

    for repo in list(target.get_repos())[:10]:
        # Commits
        for commit in list(repo.get_commits())[:20]:
            if not commit.author:
                continue
            events.append(GitHubEvent(
                event_id=commit.sha[:8],
                event_type=EventType.COMMIT,
                author=commit.author.login,
                repository=repo.name,
                title=commit.commit.message.split("\n")[0][:120],
                created_at=commit.commit.author.date,
                metadata={"sha": commit.sha[:8], "files_changed": len(commit.files)},
            ))

        # Pull requests
        for pr in list(repo.get_pulls(state="all"))[:10]:
            events.append(GitHubEvent(
                event_id=f"pr-{pr.number}",
                event_type=EventType.PULL_REQUEST,
                author=pr.user.login,
                repository=repo.name,
                title=pr.title,
                body=(pr.body or "")[:200],
                created_at=pr.created_at,
                metadata={"number": pr.number, "state": pr.state, "merged": pr.merged},
            ))

    return events


class GitHubIngestion:
    def __init__(self, store: DeveloperMemoryStore) -> None:
        self.store = store

    def run(self) -> dict[str, int]:
        """
        Ingest all GitHub events into mem0.
        Returns count of events ingested per developer.
        """
        console.print("[cyan]Fetching GitHub events...[/cyan]")

        events = _load_mock_events() if DEMO_MODE else _fetch_live_events()
        console.print(f"  Loaded {len(events)} events ({'mock' if DEMO_MODE else 'live'})")

        counts: dict[str, int] = {}

        for event in events:
            content = event.to_memory_content()
            self.store.add(
                content=content,
                developer=event.author,
                metadata={
                    "event_type": event.event_type.value,
                    "repository": event.repository,
                    "event_id": event.event_id,
                },
            )
            counts[event.author] = counts.get(event.author, 0) + 1

        for dev, count in sorted(counts.items(), key=lambda x: -x[1]):
            console.print(f"  [green]✓[/green] {dev}: {count} events ingested into mem0")

        return counts
