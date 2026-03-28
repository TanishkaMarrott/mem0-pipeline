from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    ISSUE = "issue"
    REVIEW = "review"


class GitHubEvent(BaseModel):
    event_id: str
    event_type: EventType
    author: str
    repository: str
    title: str
    body: Optional[str] = None
    created_at: datetime
    metadata: dict = Field(default_factory=dict)

    def to_memory_content(self) -> str:
        """Formats event as plain-language content for mem0 ingestion."""
        base = (
            f"{self.author} {self.event_type.value.replace('_', ' ')} "
            f"in {self.repository}: '{self.title}' on {self.created_at.strftime('%Y-%m-%d')}."
        )
        if self.body:
            base += f" Description: {self.body[:200]}"
        if self.metadata:
            extras = ", ".join(f"{k}={v}" for k, v in self.metadata.items())
            base += f" ({extras})"
        return base


class DeveloperInsight(BaseModel):
    developer: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    contribution_areas: list[str] = Field(default_factory=list)
    activity_summary: str = ""
    patterns: list[str] = Field(default_factory=list)
    memory_count: int = 0


class CohortInsight(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    active_developers: list[str] = Field(default_factory=list)
    top_repositories: list[str] = Field(default_factory=list)
    collaboration_patterns: list[str] = Field(default_factory=list)
    summary: str = ""
