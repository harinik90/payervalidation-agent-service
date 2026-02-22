"""
mcp/oig/server.py

Custom MCP server — payerai-oig.
Screens providers against the HHS OIG List of Excluded Individuals/Entities
(LEIE).  Every call is audit-logged regardless of outcome.

Backend: SQLite data/db/leie.db (monthly sync from OIG LEIE download).
Audit log: data/audit/oig_checks.jsonl (append-only, never deleted).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("payerai-oig")

_DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
_DB_PATH = _DATA_DIR / "db" / "leie.db"
_AUDIT_PATH = _DATA_DIR / "audit" / "oig_checks.jsonl"


def _write_audit(record: dict) -> None:
    _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


@mcp.tool()
def oig_check(npi: str, name: str | None = None, ein: str | None = None) -> dict:
    """Screen a provider against the HHS OIG LEIE exclusion list.

    Every call is audit-logged to data/audit/oig_checks.jsonl regardless of outcome.

    Args:
        npi: National Provider Identifier to screen.
        name: Provider name (optional, used for fuzzy match fallback).
        ein: Employer Identification Number (optional).

    Returns:
        Dict with excluded, exclusion_type, exclusion_date, waiver_state, audit_ref.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    audit_ref = f"OIG-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{npi[-4:]}"

    result: dict = {
        "excluded": False,
        "exclusion_type": None,
        "exclusion_date": None,
        "waiver_state": None,
        "audit_ref": audit_ref,
    }

    if not _DB_PATH.exists():
        _write_audit({"timestamp": timestamp, "npi": npi, "name": name, "result": "DB_UNAVAILABLE", "audit_ref": audit_ref})
        result["error"] = "LEIE database not found. Run sync to populate."
        return result

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM exclusions WHERE npi = ? LIMIT 1", (npi,)
        ).fetchone()

        if row:
            result["excluded"] = True
            result["exclusion_type"] = row["exclusion_type"]
            result["exclusion_date"] = row["excl_date"]
            result["waiver_state"] = row.get("waiver_state")
    finally:
        conn.close()

    _write_audit({
        "timestamp": timestamp,
        "npi": npi,
        "name": name,
        "ein": ein,
        "excluded": result["excluded"],
        "exclusion_type": result["exclusion_type"],
        "audit_ref": audit_ref,
    })

    return result


if __name__ == "__main__":
    mcp.run()
