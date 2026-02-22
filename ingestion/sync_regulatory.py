"""
ingestion/sync_regulatory.py

Seed data/db/regulatory.db from the Federal Register API.

Pulls CMS-related final rules and notices from the past 24 months that are
relevant to prior authorization and coverage determination.

Run daily or weekly to stay current:

    conda activate payerai-gpt
    python ingestion/sync_regulatory.py

Schema (regulatory.db → table: regulatory_items):
    title, agency, document_number, document_type, publication_date,
    effective_date, action, summary, full_text_url, lob, keywords_json,
    mandates_coverage
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DB_PATH = DATA_DIR / "db" / "regulatory.db"

# Federal Register API base URL
FR_API_BASE = "https://www.federalregister.gov/api/v1"

# Agencies whose documents are most relevant to payer prior-auth / coverage
AGENCIES = ["centers-for-medicare-medicaid-services"]

# Document types to ingest
DOC_TYPES = ["RULE", "PRULE", "NOTICE"]

# How far back to pull on first run (days)
DEFAULT_LOOKBACK_DAYS = 730  # 2 years

# Keywords to flag as potentially mandating coverage
COVERAGE_MANDATE_KEYWORDS = [
    "mandates coverage",
    "required to cover",
    "coverage requirement",
    "shall cover",
    "must provide coverage",
    "coverage mandate",
    "prior authorization reform",
    "prior authorization requirements",
]

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS regulatory_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    document_number  TEXT UNIQUE,
    title            TEXT,
    agency           TEXT,
    document_type    TEXT,
    publication_date TEXT,
    effective_date   TEXT,
    action           TEXT,
    summary          TEXT,
    full_text_url    TEXT,
    lob              TEXT,
    keywords_json    TEXT,
    mandates_coverage INTEGER DEFAULT 0
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_reg_pub_date  ON regulatory_items (publication_date);",
    "CREATE INDEX IF NOT EXISTS idx_reg_eff_date  ON regulatory_items (effective_date);",
    "CREATE INDEX IF NOT EXISTS idx_reg_mandate   ON regulatory_items (mandates_coverage);",
    "CREATE INDEX IF NOT EXISTS idx_reg_doc_type  ON regulatory_items (document_type);",
]


def _build_search_url(
    agency_slug: str,
    doc_type: str,
    start_date: str,
    end_date: str,
    page: int = 1,
) -> str:
    params = {
        "fields[]": [
            "document_number",
            "title",
            "agencies",
            "type",
            "publication_date",
            "effective_on",
            "action",
            "abstract",
            "html_url",
            "full_text_xml_url",
        ],
        "conditions[agencies][]": agency_slug,
        "conditions[type][]": doc_type,
        "conditions[publication_date][gte]": start_date,
        "conditions[publication_date][lte]": end_date,
        "per_page": "100",
        "page": str(page),
        "order": "newest",
    }
    qs = urllib.parse.urlencode(params, doseq=True)
    return f"{FR_API_BASE}/documents.json?{qs}"


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _infer_lob(title: str, summary: str) -> str:
    """Best-effort LOB tag from document content."""
    text = (title + " " + (summary or "")).lower()
    if "medicaid" in text:
        return "medicaid"
    if "medicare advantage" in text or "part c" in text:
        return "medicare_advantage"
    if "medicare" in text:
        return "medicare_advantage"
    return "commercial"


def _detect_mandate(title: str, summary: str) -> int:
    text = (title + " " + (summary or "")).lower()
    return int(any(kw in text for kw in COVERAGE_MANDATE_KEYWORDS))


def _extract_keywords(title: str, summary: str) -> list[str]:
    text = (title + " " + (summary or "")).lower()
    keywords: list[str] = []
    for term in [
        "prior authorization", "step therapy", "coverage determination",
        "icd-10", "cpt", "hcpcs", "ncd", "lcd", "pa reform",
        "interoperability", "claims processing",
    ]:
        if term in text:
            keywords.append(term)
    return keywords


def _fetch_all_for_agency_type(
    agency_slug: str, doc_type: str, start_date: str, end_date: str
) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        url = _build_search_url(agency_slug, doc_type, start_date, end_date, page)
        try:
            data = _fetch_json(url)
        except Exception as exc:
            print(f"    WARNING: API error on page {page}: {exc}")
            break

        results = data.get("results", [])
        if not results:
            break

        items.extend(results)
        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.25)  # respect FR API rate limits

    return items


def _upsert_items(con: sqlite3.Connection, raw_items: list[dict]) -> int:
    inserted = 0
    for item in raw_items:
        doc_num = item.get("document_number", "")
        if not doc_num:
            continue
        title = item.get("title", "")
        summary = item.get("abstract") or ""
        pub_date = item.get("publication_date", "")
        eff_date = item.get("effective_on") or ""
        agency = ", ".join(
            a.get("name", "") for a in (item.get("agencies") or [])
        )
        doc_type = item.get("type", "")
        action = item.get("action") or ""
        full_text_url = item.get("html_url") or item.get("full_text_xml_url") or ""

        lob = _infer_lob(title, summary)
        mandates = _detect_mandate(title, summary)
        keywords = _extract_keywords(title, summary)

        try:
            con.execute(
                """
                INSERT OR REPLACE INTO regulatory_items
                  (document_number, title, agency, document_type,
                   publication_date, effective_date, action, summary,
                   full_text_url, lob, keywords_json, mandates_coverage)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    doc_num, title, agency, doc_type,
                    pub_date, eff_date, action, summary,
                    full_text_url, lob, json.dumps(keywords), mandates,
                ),
            )
            inserted += 1
        except sqlite3.Error as exc:
            print(f"    DB error for {doc_num}: {exc}")
    con.commit()
    return inserted


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(CREATE_TABLE)
    for idx_sql in CREATE_INDEXES:
        cur.execute(idx_sql)
    con.commit()

    # Determine sync window: from last publication_date in DB, or DEFAULT_LOOKBACK_DAYS ago.
    row = con.execute(
        "SELECT MAX(publication_date) FROM regulatory_items"
    ).fetchone()
    last_date = row[0] if row and row[0] else None

    if last_date:
        # Incremental: re-fetch from 7 days before last record to catch edits
        start = (date.fromisoformat(last_date) - timedelta(days=7)).isoformat()
    else:
        start = (date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)).isoformat()

    end = date.today().isoformat()
    print(f"Fetching Federal Register documents from {start} to {end} ...")

    total_inserted = 0
    for agency in AGENCIES:
        for doc_type in DOC_TYPES:
            print(f"  {agency} / {doc_type} ...", end=" ", flush=True)
            items = _fetch_all_for_agency_type(agency, doc_type, start, end)
            n = _upsert_items(con, items)
            print(f"{len(items)} fetched, {n} upserted.")
            total_inserted += n

    total = con.execute("SELECT COUNT(*) FROM regulatory_items").fetchone()[0]
    mandates = con.execute(
        "SELECT COUNT(*) FROM regulatory_items WHERE mandates_coverage = 1"
    ).fetchone()[0]
    con.close()

    print(
        f"\nRegulatory sync complete -- {total_inserted} new/updated rows.\n"
        f"  Total in DB: {total:,}  |  Coverage mandates flagged: {mandates}"
    )


if __name__ == "__main__":
    sys.exit(main())