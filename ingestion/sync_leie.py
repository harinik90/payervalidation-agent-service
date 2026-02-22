"""
ingestion/sync_leie.py

Download the OIG LEIE exclusions CSV and load it into data/db/leie.db.

Run monthly (or on demand) to keep the local mirror current:

    conda activate payerai-gpt
    python ingestion/sync_leie.py

Schema (leie.db → table: exclusions):
    lastname, firstname, midname, busname, general, specialty,
    upin, npi, dob, address, city, state, zip, excl_type,
    excl_date, reinstate_date, waiver_date, waiver_state
"""
from __future__ import annotations

import csv
import io
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

LEIE_URL = "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv"
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DB_PATH = DATA_DIR / "db" / "leie.db"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS exclusions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lastname      TEXT,
    firstname     TEXT,
    midname       TEXT,
    busname       TEXT,
    general       TEXT,
    specialty     TEXT,
    upin          TEXT,
    npi           TEXT,
    dob           TEXT,
    address       TEXT,
    city          TEXT,
    state         TEXT,
    zip           TEXT,
    excl_type     TEXT,
    excl_date     TEXT,
    reinstate_date TEXT,
    waiver_date   TEXT,
    waiver_state  TEXT
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_leie_npi      ON exclusions (npi);",
    "CREATE INDEX IF NOT EXISTS idx_leie_lastname  ON exclusions (lastname);",
    "CREATE INDEX IF NOT EXISTS idx_leie_busname   ON exclusions (busname);",
]


def _download_csv() -> list[dict]:
    """Download the OIG LEIE CSV and return rows as list of dicts."""
    print(f"Downloading LEIE from {LEIE_URL} …")
    with urllib.request.urlopen(LEIE_URL, timeout=120) as resp:  # noqa: S310
        raw = resp.read().decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)
    print(f"  Downloaded {len(rows):,} exclusion records.")
    return rows


# Map CSV column names (lowercased) → DB column names
_COL_MAP = {
    "excltype":   "excl_type",
    "excldate":   "excl_date",
    "reindate":   "reinstate_date",
    "waiverdate": "waiver_date",
    "wvrstate":   "waiver_state",
}


def _normalise(row: dict) -> dict:
    """Lowercase keys, remap to DB names, strip whitespace from values."""
    out: dict = {}
    for k, v in row.items():
        key = k.strip().lower()
        key = _COL_MAP.get(key, key)
        out[key] = v.strip() if isinstance(v, str) else v
    return out


def _load(rows: list[dict]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute(CREATE_TABLE)
    for idx_sql in CREATE_INDEXES:
        cur.execute(idx_sql)

    # Wipe existing data so each sync is a full replacement.
    cur.execute("DELETE FROM exclusions")

    insert_sql = """
        INSERT INTO exclusions
          (lastname, firstname, midname, busname, general, specialty,
           upin, npi, dob, address, city, state, zip,
           excl_type, excl_date, reinstate_date, waiver_date, waiver_state)
        VALUES
          (:lastname, :firstname, :midname, :busname, :general, :specialty,
           :upin, :npi, :dob, :address, :city, :state, :zip,
           :excl_type, :excl_date, :reinstate_date, :waiver_date, :waiver_state)
    """

    normalised = [_normalise(r) for r in rows]
    cur.executemany(insert_sql, normalised)
    con.commit()

    count = cur.execute("SELECT COUNT(*) FROM exclusions").fetchone()[0]
    con.close()
    print(f"  Loaded {count:,} rows into {DB_PATH}.")


def main() -> None:
    rows = _download_csv()
    _load(rows)
    print("LEIE sync complete.")


if __name__ == "__main__":
    sys.exit(main())
