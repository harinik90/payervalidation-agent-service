"""
ingestion/sync_icd10.py

Download CMS ICD-10-CM annual code tables and load them into data/db/icd10.db.

Run annually (or when a new CMS FY release is published):

    conda activate payerai-gpt
    python ingestion/sync_icd10.py

CMS fiscal years:  FY2025 = Oct 2024 – Sep 2025
                   FY2026 = Oct 2025 – Sep 2026

Schema (icd10.db → table: icd10_codes):
    code, description, is_billable, fiscal_year
"""
from __future__ import annotations

import io
import os
import re
import sqlite3
import sys
import urllib.request
import zipfile
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DB_PATH = DATA_DIR / "db" / "icd10.db"

# CMS ZIP files contain a fixed-width "order" file that is the authoritative
# billable-code list.  The file naming convention has varied slightly between
# fiscal years; we try several candidate names inside the ZIP.
FY_SOURCES: list[dict] = [
    {
        "fiscal_year": "FY2025",
        "url": "https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip",
        # Candidate file names inside the ZIP (first match wins)
        "order_candidates": [
            "icd10cm_order_2025.txt",
            "icd10cm_tabular_order_2025.txt",
            "order_2025.txt",
        ],
    },
    {
        "fiscal_year": "FY2026",
        "url": "https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order.zip",
        "order_candidates": [
            "icd10cm_order_2026.txt",
            "icd10cm_tabular_order_2026.txt",
            "order_2026.txt",
        ],
    },
]

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS icd10_codes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT NOT NULL,
    description  TEXT NOT NULL,
    is_billable  INTEGER NOT NULL DEFAULT 1,
    fiscal_year  TEXT NOT NULL,
    UNIQUE (code, fiscal_year)
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_icd10_code   ON icd10_codes (code);",
    "CREATE INDEX IF NOT EXISTS idx_icd10_fy     ON icd10_codes (fiscal_year);",
    "CREATE INDEX IF NOT EXISTS idx_icd10_code_fy ON icd10_codes (code, fiscal_year);",
]


def _download_zip(url: str) -> bytes:
    print(f"  Downloading {url} …")
    with urllib.request.urlopen(url, timeout=180) as resp:  # noqa: S310
        data = resp.read()
    print(f"  Downloaded {len(data) / 1_048_576:.1f} MB.")
    return data


def _find_order_file(zf: zipfile.ZipFile, candidates: list[str]) -> str | None:
    """Return the first candidate name found in the ZIP (case-insensitive)."""
    names_lower = {n.lower(): n for n in zf.namelist()}
    for candidate in candidates:
        if candidate.lower() in names_lower:
            return names_lower[candidate.lower()]
    # Fallback: any file matching icd10cm_order_*.txt
    for name in zf.namelist():
        if re.search(r"icd10cm_order.*\.txt$", name, re.IGNORECASE):
            return name
    return None


def _parse_order_file(content: str) -> list[dict]:
    """
    Parse CMS fixed-width order file.

    Verified format (0-indexed Python positions):
        line[0:5]   : order number (ignored)
        line[5]     : space
        line[6:13]  : ICD-10-CM code (7 chars, right-padded with spaces)
        line[13]    : space
        line[14]    : billable flag ('1' = billable, '0' = header/category)
        line[15]    : space
        line[16:76] : short description (60 chars)
        line[76]    : space
        line[77:]   : long description (preferred when present)
    """
    rows: list[dict] = []
    for line in content.splitlines():
        if len(line) < 16:
            continue
        code = line[6:13].strip()
        billable = line[14].strip()
        short_desc = line[16:76].strip()
        long_desc = line[77:].strip() if len(line) > 77 else ""
        description = long_desc if long_desc else short_desc
        if not code:
            continue
        rows.append(
            {
                "code": code,
                "description": description,
                "is_billable": 1 if billable == "1" else 0,
            }
        )
    return rows


def _load_fy(con: sqlite3.Connection, rows: list[dict], fiscal_year: str) -> int:
    cur = con.cursor()
    # Replace existing data for this FY.
    cur.execute("DELETE FROM icd10_codes WHERE fiscal_year = ?", (fiscal_year,))
    cur.executemany(
        """
        INSERT OR REPLACE INTO icd10_codes (code, description, is_billable, fiscal_year)
        VALUES (:code, :description, :is_billable, :fiscal_year)
        """,
        [{"fiscal_year": fiscal_year, **r} for r in rows],
    )
    con.commit()
    return len(rows)


def _sync_fy(con: sqlite3.Connection, source: dict) -> None:
    fy = source["fiscal_year"]
    print(f"\nProcessing {fy} …")
    zip_bytes = _download_zip(source["url"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        order_name = _find_order_file(zf, source["order_candidates"])
        if order_name is None:
            available = [n for n in zf.namelist() if n.endswith(".txt")]
            print(
                f"  WARNING: Could not locate order file for {fy}.\n"
                f"  Available .txt files: {available}\n"
                f"  Skipping {fy}."
            )
            return
        print(f"  Parsing {order_name} …")
        content = zf.read(order_name).decode("utf-8", errors="replace")

    rows = _parse_order_file(content)
    n = _load_fy(con, rows, fy)
    print(f"  Loaded {n:,} codes for {fy}.")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(CREATE_TABLE)
    for idx_sql in CREATE_INDEXES:
        cur.execute(idx_sql)
    con.commit()

    for source in FY_SOURCES:
        _sync_fy(con, source)

    total = con.execute("SELECT COUNT(*) FROM icd10_codes").fetchone()[0]
    con.close()
    print(f"\nICD-10 sync complete — {total:,} total rows in {DB_PATH}.")


if __name__ == "__main__":
    sys.exit(main())
