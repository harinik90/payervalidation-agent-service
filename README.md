# PayerAI GPT

A healthcare payer AI platform for prior authorization, claims intelligence, and coverage determination. Built on Azure AI Foundry (MAF agents) and Claude Agent SDK (MCP bridge layer).

---

## Architecture

```
Frontend (React/Vite)
        │
        ▼
FastAPI Server (api/server.py)
        │
        ▼
Orchestrator (agents/orchestrator.py)
        │
  ┌─────┼─────────────────────────────┐
  ▼     ▼         ▼         ▼         ▼
Sanctions  Coding  Eligibility  Policy  Regulatory
Agent      Agent   Agent        Agent   Agent
        │
        ▼
  Bridge (agents/bridge.py)
        │
  Claude Agent SDK + MCP Servers
  ├── cms-coverage   (remote)
  ├── npi-registry   (remote)
  ├── pubmed         (remote)
  ├── payerai-oig    (local)
  ├── payerai-icd10  (local)
  ├── payerai-knowledge (local)
  └── payerai-regulatory (local)
```

---

## Agent Pipeline

Prior authorization requests run through agents in this order (compliance enforced):

| Step | Agent | Purpose |
|------|-------|---------|
| 1 | **sanctions-agent** | OIG LEIE exclusion check — hard stop on match |
| 2 | **coding-agent** | ICD-10 / CPT validation, CCI bundling checks |
| 3 | **eligibility-agent** | Member benefit coverage + provider NPI verification |
| 4 | **policy-agent** | RAG-based policy criteria evaluation (APPROVE / PEND / DENY) |
| 5 | **regulatory-agent** | Federal/state mandate check — escalates DENY to PEND if override found |

---

## Project Structure

```
payerai-gpt/
├── agents/
│   ├── base.py              # Azure AI Foundry client, tool sets, run execution
│   ├── bridge.py            # Claude Agent SDK + MCP bridge
│   ├── orchestrator.py      # PA pipeline coordinator
│   ├── sanctions_agent.py
│   ├── coding_agent.py
│   ├── eligibility_agent.py
│   ├── policy_agent.py
│   └── regulatory_agent.py
├── api/
│   └── server.py            # FastAPI endpoints (/api/prior-auth, /api/health)
├── mcp_servers/
│   ├── icd10/               # ICD-10 code lookup MCP server
│   ├── knowledge/           # ChromaDB policy RAG MCP server
│   ├── oig/                 # OIG LEIE sanctions MCP server
│   └── regulatory/          # Regulatory feed MCP server
├── ingestion/
│   ├── chunker.py           # PDF/DOCX policy document chunker
│   ├── sync_icd10.py        # ICD-10 database sync
│   ├── sync_leie.py         # OIG LEIE database sync
│   └── sync_regulatory.py   # Regulatory feed sync
├── tools/
│   └── knowledge.py         # ChromaDB RAG wrapper
├── frontend/                # React + Vite UI
├── tests/                   # pytest test suite
├── data/                    # Local data (not committed)
├── pyproject.toml
├── .env.example
└── main.py                  # Entry point
```

---

## Setup

### 1. Install dependencies

```bash
pip install -e ".[test,dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in Azure and Anthropic credentials
```

### 3. Sync databases

```bash
python ingestion/sync_leie.py
python ingestion/sync_icd10.py
python ingestion/sync_regulatory.py
```

### 4. Run the server

```bash
python main.py
```

Server starts at `http://0.0.0.0:8000`. Frontend dev server: `http://localhost:5173`.

---

## API

### `POST /api/prior-auth`

```json
{
  "member_id": "M123456",
  "npi": "1234567890",
  "provider_name": "Dr. Jane Smith",
  "icd10_codes": ["M17.11"],
  "cpt_codes": ["27447"],
  "lob": "commercial",
  "service_date": "2026-02-22",
  "clinical_notes": "Patient has severe osteoarthritis...",
  "state": "TX"
}
```

**Response:**

```json
{
  "decision": "APPROVE",
  "hard_stop": false,
  "policy_refs": ["POL-2024-027"],
  "doc_requirements": [],
  "reason": "All prior authorization criteria have been met.",
  "audit_ref": "OIG-20260222-001"
}
```

### `GET /api/health`

Returns agent readiness, LEIE record count, and ICD-10 code count.

---

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_AI_FOUNDRY_PROJECT` | Azure AI Foundry project endpoint |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint (embeddings) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude Agent SDK bridge) |
| `DATA_DIR` | Local data directory (default: `./data`) |
| `BRIDGE_MODEL` | Claude model for bridge (default: `claude-opus-4-6`) |

See [.env.example](.env.example) for the full list.

---

## Running Tests

```bash
pytest
```

---

## License

Proprietary
