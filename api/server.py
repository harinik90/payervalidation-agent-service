"""
api/server.py

Production FastAPI server for PayerAI GPT.

Routes prior authorization requests through the full MAF agent orchestration
pipeline (sanctions → coding → eligibility → policy → regulatory).

Run:
    python main.py

    OR directly:
    uvicorn api.server:app --host 0.0.0.0 --port 8000

Endpoints:
    POST /api/prior-auth   -> PAResponse
    GET  /api/health       -> { status, agents, db_stats }
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.orchestrator import run_orchestrator

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
LEIE_DB = DATA_DIR / "db" / "leie.db"
ICD10_DB = DATA_DIR / "db" / "icd10.db"

app = FastAPI(title="PayerAI GPT", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class PARequest(BaseModel):
    member_id: str
    npi: str
    provider_name: str
    icd10_codes: list[str]
    cpt_codes: list[str]
    lob: str
    service_date: str
    clinical_notes: str | None = None
    state: str | None = None


class CodingIssue(BaseModel):
    code: str
    issue: str


class PAResponse(BaseModel):
    decision: str
    hard_stop: bool = False
    policy_refs: list[str] = []
    doc_requirements: list[str] = []
    reason: str | None = None
    coding_issues: list[CodingIssue] | None = None
    regulatory_refs: list[str] | None = None
    audit_ref: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/prior-auth", response_model=PAResponse)
async def prior_auth(request: PARequest) -> PAResponse:
    """Process a prior authorization request through the agent pipeline."""
    try:
        result = await run_orchestrator(request.model_dump())
    except Exception:
        logger.exception("Orchestrator failed for request: %s", request.model_dump())
        raise HTTPException(
            status_code=500,
            detail="Prior authorization processing failed. Check server logs for details.",
        )

    # Normalize coding_issues to CodingIssue models
    coding_issues = None
    raw_issues = result.get("coding_issues")
    if raw_issues:
        coding_issues = [
            CodingIssue(code=ci.get("code", ""), issue=ci.get("issue", ""))
            for ci in raw_issues
            if isinstance(ci, dict)
        ]

    return PAResponse(
        decision=result.get("decision", "PEND"),
        hard_stop=result.get("hard_stop", False),
        policy_refs=result.get("policy_refs", []),
        doc_requirements=result.get("doc_requirements", []),
        reason=result.get("reason"),
        coding_issues=coding_issues,
        regulatory_refs=result.get("regulatory_refs"),
        audit_ref=result.get("audit_ref"),
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Health check endpoint with database and agent readiness info."""
    leie_count = 0
    icd_count = 0

    try:
        if LEIE_DB.exists():
            con = sqlite3.connect(str(LEIE_DB))
            leie_count = con.execute("SELECT COUNT(*) FROM exclusions").fetchone()[0]
            con.close()
    except Exception:
        pass

    try:
        if ICD10_DB.exists():
            con = sqlite3.connect(str(ICD10_DB))
            icd_count = con.execute("SELECT COUNT(*) FROM icd10_codes").fetchone()[0]
            con.close()
    except Exception:
        pass

    from agents.base import _agent_cache
    agents_ready = {name: bool(aid) for name, aid in _agent_cache.items()}

    return {
        "status": "ok",
        "mode": "production",
        "leie_records": leie_count,
        "icd10_codes": icd_count,
        "agents": agents_ready,
    }
