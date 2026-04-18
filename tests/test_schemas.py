"""
Tests for mem0-pipeline data models.
No external services required.
"""

from datetime import datetime

import pytest

from models.schemas import CohortInsight, DeveloperInsight, EventType, GitHubEvent


class TestGitHubEvent:
    def test_basic_creation(self):
        event = GitHubEvent(
            event_id="abc123",
            event_type=EventType.COMMIT,
            author="alice",
            repository="auth-service",
            title="fix: token expiry validation",
            created_at=datetime(2026, 4, 10, 12, 0, 0),
        )
        assert event.author == "alice"
        assert event.repository == "auth-service"
        assert event.event_type == EventType.COMMIT

    def test_body_defaults_to_none(self):
        event = GitHubEvent(
            event_id="x1",
            event_type=EventType.ISSUE,
            author="bob",
            repository="api",
            title="bug: null pointer",
            created_at=datetime.utcnow(),
        )
        assert event.body is None

    def test_metadata_defaults_to_empty_dict(self):
        event = GitHubEvent(
            event_id="x2",
            event_type=EventType.COMMIT,
            author="carol",
            repository="infra",
            title="chore: update deps",
            created_at=datetime.utcnow(),
        )
        assert event.metadata == {}

    def test_to_memory_content_includes_author_and_repo(self):
        event = GitHubEvent(
            event_id="m1",
            event_type=EventType.PULL_REQUEST,
            author="alice",
            repository="auth-service",
            title="feat: add OAuth2 support",
            created_at=datetime(2026, 4, 11, 9, 0, 0),
        )
        content = event.to_memory_content()
        assert "alice" in content
        assert "auth-service" in content
        assert "2026-04-11" in content

    def test_to_memory_content_includes_body_when_present(self):
        event = GitHubEvent(
            event_id="m2",
            event_type=EventType.PULL_REQUEST,
            author="bob",
            repository="api",
            title="feat: rate limiting",
            body="Implements token bucket algorithm for per-user rate limits.",
            created_at=datetime.utcnow(),
        )
        content = event.to_memory_content()
        assert "token bucket" in content

    def test_to_memory_content_includes_metadata(self):
        event = GitHubEvent(
            event_id="m3",
            event_type=EventType.COMMIT,
            author="carol",
            repository="infra",
            title="fix: terraform state",
            created_at=datetime.utcnow(),
            metadata={"files_changed": 3, "sha": "d4e5f6"},
        )
        content = event.to_memory_content()
        assert "files_changed" in content

    def test_to_memory_content_truncates_body_at_200_chars(self):
        long_body = "x" * 500
        event = GitHubEvent(
            event_id="m4",
            event_type=EventType.ISSUE,
            author="dave",
            repository="backend",
            title="bug: memory leak",
            body=long_body,
            created_at=datetime.utcnow(),
        )
        content = event.to_memory_content()
        assert long_body not in content
        assert "x" * 200 in content

    def test_event_type_enum_values(self):
        assert EventType.COMMIT == "commit"
        assert EventType.PULL_REQUEST == "pull_request"
        assert EventType.ISSUE == "issue"
        assert EventType.REVIEW == "review"

    def test_to_memory_content_is_string(self):
        event = GitHubEvent(
            event_id="s1",
            event_type=EventType.COMMIT,
            author="alice",
            repository="repo",
            title="some commit",
            created_at=datetime.utcnow(),
        )
        assert isinstance(event.to_memory_content(), str)


class TestDeveloperInsight:
    def test_basic_creation(self):
        insight = DeveloperInsight(developer="alice")
        assert insight.developer == "alice"
        assert insight.contribution_areas == []
        assert insight.patterns == []
        assert insight.memory_count == 0
        assert insight.activity_summary == ""

    def test_generated_at_auto_set(self):
        insight = DeveloperInsight(developer="bob")
        assert isinstance(insight.generated_at, datetime)

    def test_with_full_fields(self):
        insight = DeveloperInsight(
            developer="carol",
            contribution_areas=["auth-service", "api-gateway"],
            activity_summary="Carol focuses on security-critical components.",
            patterns=["consistent daily commits", "heavy PR reviewer"],
            memory_count=25,
        )
        assert "auth-service" in insight.contribution_areas
        assert insight.memory_count == 25


class TestCohortInsight:
    def test_basic_creation(self):
        insight = CohortInsight()
        assert insight.active_developers == []
        assert insight.top_repositories == []
        assert insight.collaboration_patterns == []
        assert insight.summary == ""

    def test_generated_at_auto_set(self):
        insight = CohortInsight()
        assert isinstance(insight.generated_at, datetime)

    def test_with_developers_and_repos(self):
        insight = CohortInsight(
            active_developers=["alice", "bob", "carol"],
            top_repositories=["auth-service", "api-gateway"],
            summary="Team is heavily focused on auth-service this sprint.",
        )
        assert len(insight.active_developers) == 3
        assert "auth-service" in insight.top_repositories
