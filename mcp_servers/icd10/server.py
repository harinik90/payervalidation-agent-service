"""
mcp/icd10/server.py

Custom MCP server — payerai-icd10.
Validates ICD-10-CM/PCS codes against CMS annual fiscal-year tables.
Lookups are gated by service_date to ensure the correct FY is used.

Backend: SQLite data/db/icd10.db (annual CMS release, version-gated).
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("payerai-icd10")

_DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
_DB_PATH = _DATA_DIR / "db" / "icd10.db"


def _service_date_to_fy(service_date: str) -> int:
    """Map a service date (YYYY-MM-DD) to a CMS fiscal year.
    CMS FY runs Oct 1 – Sep 30.  Oct 1 2024 → FY 2025.
    """
    year, month, _ = service_date.split("-")
    y, m = int(year), int(month)
    return y + 1 if m >= 10 else y


@mcp.tool()
def icd10_lookup(code: str, service_date: str) -> dict:
    """Validate an ICD-10-CM code against the CMS FY table for a given service date.

    Args:
        code: ICD-10-CM code to validate (e.g. 'M17.11').
        service_date: ISO date string (YYYY-MM-DD) used to select the correct FY table.

    Returns:
        Dict with valid, billable, description, fiscal_year, and optional suggestion.
    """
    fy = _service_date_to_fy(service_date)
    result = {"code": code, "fiscal_year": fy, "valid": False, "billable": False, "description": None}

    if not _DB_PATH.exists():
        result["error"] = "ICD-10 database not found. Run sync to populate."
        return result

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM icd10_codes WHERE code = ? AND fiscal_year = ? LIMIT 1",
            (code.replace(".", ""), fy),
        ).fetchone()
        if row:
            result["valid"] = True
            result["billable"] = bool(row["is_billable"])
            result["description"] = row["description"]
    finally:
        conn.close()

    return result


@mcp.tool()
def icd10_expand(parent_code: str, service_date: str) -> list[dict]:
    """Return all billable child codes under a parent ICD-10 category.

    Args:
        parent_code: Header/category code (e.g. 'M17').
        service_date: ISO date string to select the correct FY table.

    Returns:
        List of dicts with code, description, and billable flag.
    """
    fy = _service_date_to_fy(service_date)

    if not _DB_PATH.exists():
        return [{"error": "ICD-10 database not found."}]

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT code, description, is_billable FROM icd10_codes "
            "WHERE code LIKE ? AND fiscal_year = ? AND is_billable = 1",
            (parent_code.replace(".", "") + "%", fy),
        ).fetchall()
    finally:
        conn.close()

    return [{"code": r["code"], "description": r["description"], "billable": True} for r in rows]


if __name__ == "__main__":
    mcp.run()
