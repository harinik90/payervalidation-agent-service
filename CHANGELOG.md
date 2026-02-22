# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- Project scaffold: `agents/`, `mcp/`, `tools/`, `ingestion/`, `tests/`, `data/`, `frontend/`
- `agents/bridge.py` — async bridge connecting MAF agents to Claude Agent SDK + MCP servers
- Agent stubs: orchestrator, policy, coding, eligibility, sanctions, regulatory
- Custom MCP server stubs: `payerai-oig`, `payerai-icd10`, `payerai-regulatory`, `payerai-knowledge`
- `tools/knowledge.py` — ChromaDB RAG wrapper (`knowledge_search`)
- `ingestion/chunker.py` — semantic chunker for PDF/DOCX policy documents
- `pyproject.toml` with pytest, ruff, and mypy configuration
- `environment.yml` and `requirements.txt` for conda/pip dependency management
- `.env.example` with all required environment variable stubs
- `WORKFLOWS.md` — six end-to-end PA workflow scenarios with agent call traces
- `CLAUDE.md` — architecture, agent specs, compliance rules, and dev conventions
- Official MCP servers registered: `cms-coverage`, `npi-registry`, `pubmed`
- Claude Code skills installed: `prior-auth-review@healthcare`, `fhir-developer@healthcare`

---

## [0.1.0] — 2026-02-19

### Added
- Initial repository setup
- `CLAUDE.md` project architecture document
- `WORKFLOWS.md` sample PA workflow scenarios

[Unreleased]: https://github.com/your-org/payerai-gpt/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/payerai-gpt/releases/tag/v0.1.0
