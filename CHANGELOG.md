# Changelog

## [1.0.0] — 2026-04-30

### Added
- Three-layer memory pipeline: vector (Qdrant) + graph (Neo4j) + facts (mem0)
- GitHub event ingestion: commits, PRs, issues, reviews
- `DeveloperInsight` and `CohortInsight` Pydantic schemas with `to_memory_content()` serialisation
- Local LLM support via Ollama llama3.1:8b for fact extraction
- 23 unit tests for schemas and mock event ingestion — no mem0/Qdrant/Neo4j required
- GitHub Actions CI — ruff lint + pytest

### Changed
- Mock event ingestion bypasses the mem0 import chain for test reliability

### Fixed
- Import chain through `DeveloperMemoryStore` caused `ModuleNotFoundError` in CI — tests now load mock JSON directly
