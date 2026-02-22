"""
tests/mcp/test_regulatory_server.py

Unit tests for the payerai-regulatory MCP server tool functions.
Uses an in-memory SQLite fixture — never touches data/db/regulatory.db.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_servers.regulatory.server import regulatory_feed_fetch


@pytest.fixture()
def regulatory_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "regulatory.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE regulatory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            effective_date TEXT,
            jurisdiction TEXT,
            state TEXT,
            lob TEXT,
            icd10_codes TEXT,
            cpt_codes TEXT,
            summary TEXT,
            mandates_coverage INTEGER
        )
        """
    )
    conn.executemany(
        "INSERT INTO regulatory_items (title, effective_date, jurisdiction, state, lob, icd10_codes, cpt_codes, summary, mandates_coverage) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("CMS NCD 280.1 Amendment", "2025-01-01", "Federal", None, "medicare_advantage", "E11.9", "95250", "Expanded CGM coverage to all T2D Medicare beneficiaries.", 1),
            ("FL Acupuncture Mandate", "2023-06-01", "State", "FL", "commercial", "M54.5", "97810", "Requires commercial plans to cover acupuncture for chronic pain.", 1),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def test_regulatory_fetch_mandate_found(regulatory_db: Path) -> None:
    with patch("mcp_servers.regulatory.server._DB_PATH", regulatory_db):
        items = regulatory_feed_fetch(icd10="E11.9", cpt="95250", lob="medicare_advantage", since="2024-01-01")

    assert len(items) == 1
    assert items[0]["mandates_coverage"] is True
    assert "CGM" in items[0]["summary"]


def test_regulatory_fetch_no_results(regulatory_db: Path) -> None:
    with patch("mcp_servers.regulatory.server._DB_PATH", regulatory_db):
        items = regulatory_feed_fetch(icd10="Z00.00", lob="commercial", since="2026-01-01")

    assert items == []


def test_regulatory_fetch_state_filter(regulatory_db: Path) -> None:
    with patch("mcp_servers.regulatory.server._DB_PATH", regulatory_db):
        items = regulatory_feed_fetch(cpt="97810", state="FL")

    assert any(i["jurisdiction"] == "State" for i in items)


def test_regulatory_fetch_db_missing(tmp_path: Path) -> None:
    with patch("mcp_servers.regulatory.server._DB_PATH", tmp_path / "nonexistent.db"):
        items = regulatory_feed_fetch(icd10="M54.5")

    assert len(items) == 1
    assert "error" in items[0]
