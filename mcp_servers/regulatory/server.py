"""
mcp/regulatory/server.py

Custom MCP server — payerai-regulatory.
Surfaces regulatory updates (Federal Register, state DOI, AMA CPT, NCQA)
that may affect payer coverage obligations.

Backend: SQLite data/db/regulatory.db (daily/weekly/annual sync).
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("payerai-regulatory")

_DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
_DB_PATH = _DATA_DIR / "db" / "regulatory.db"


@mcp.tool()
def regulatory_feed_fetch(
    icd10: str | None = None,
    cpt: str | None = None,
    lob: str | None = None,
    state: str | None = None,
    since: str | None = None,
) -> list[dict]:
    """Fetch regulatory items affecting coverage for a given code/LOB/state combination.

    Args:
        icd10: ICD-10 code to filter by (optional).
        cpt: CPT/HCPCS code to filter by (optional).
        lob: Line of business filter (optional).
        state: Two-letter state code for state-mandate lookup (optional).
        since: ISO date string — only return items effective on or after this date.

    Returns:
        List of RegulatoryItem dicts: title, effective_date, jurisdiction,
        summary, mandates_coverage.
    """
    if not _DB_PATH.exists():
        return [{"error": "Regulatory database not found. Run sync to populate."}]

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        query = "SELECT * FROM regulatory_items WHERE 1=1"
        params: list = []

        if icd10:
            query += " AND (icd10_codes LIKE ? OR icd10_codes IS NULL)"
            params.append(f"%{icd10}%")
        if cpt:
            query += " AND (cpt_codes LIKE ? OR cpt_codes IS NULL)"
            params.append(f"%{cpt}%")
        if lob:
            query += " AND (lob = ? OR lob IS NULL)"
            params.append(lob)
        if state:
            query += " AND (state = ? OR jurisdiction = 'Federal')"
            params.append(state)
        if since:
            query += " AND effective_date >= ?"
            params.append(since)

        query += " ORDER BY effective_date DESC LIMIT 50"
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return [
        {
            "title": r["title"],
            "effective_date": r["effective_date"],
            "jurisdiction": r["jurisdiction"],
            "summary": r["summary"],
            "mandates_coverage": bool(r["mandates_coverage"]),
        }
        for r in rows
    ]


if __name__ == "__main__":
    mcp.run()
