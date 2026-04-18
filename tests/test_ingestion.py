"""
Tests for GitHub event ingestion logic in DEMO_MODE.
Loads mock data directly to avoid mem0/Qdrant/Neo4j dependencies.
"""

import json
import os
from pathlib import Path

import pytest

from models.schemas import EventType, GitHubEvent

MOCK_DATA_PATH = Path(__file__).parent.parent / "demo" / "mock_github_events.json"


def load_mock_events() -> list[GitHubEvent]:
    with open(MOCK_DATA_PATH) as f:
        raw = json.load(f)
    return [GitHubEvent(**e) for e in raw]


class TestMockEventLoading:
    def test_loads_events(self):
        events = load_mock_events()
        assert len(events) > 0

    def test_events_are_github_event_instances(self):
        events = load_mock_events()
        for event in events:
            assert isinstance(event, GitHubEvent)

    def test_events_have_valid_event_types(self):
        events = load_mock_events()
        valid_types = {e.value for e in EventType}
        for event in events:
            assert event.event_type.value in valid_types

    def test_events_have_non_empty_authors(self):
        events = load_mock_events()
        for event in events:
            assert event.author.strip() != ""

    def test_events_have_non_empty_repositories(self):
        events = load_mock_events()
        for event in events:
            assert event.repository.strip() != ""

    def test_events_have_titles(self):
        events = load_mock_events()
        for event in events:
            assert event.title.strip() != ""

    def test_events_cover_multiple_authors(self):
        events = load_mock_events()
        authors = {e.author for e in events}
        assert len(authors) > 1

    def test_memory_content_generated_for_all_events(self):
        events = load_mock_events()
        for event in events:
            content = event.to_memory_content()
            assert isinstance(content, str)
            assert len(content) > 0
            assert event.author in content
            assert event.repository in content
