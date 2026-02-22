"""
tests/mcp/test_oig_server.py

Unit tests for the payerai-oig MCP server tool functions.
Uses an in-memory SQLite fixture — never touches data/db/leie.db.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_servers.oig.server import oig_check


@pytest.fixture()
def leie_db(tmp_path: Path) -> Path:
    """Create a minimal in-memory LEIE SQLite fixture."""
    db_path = tmp_path / "leie.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE exclusions (
            npi TEXT PRIMARY KEY,
            exclusion_type TEXT,
            excl_date TEXT,
            waiver_state TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO exclusions VALUES (?, ?, ?, ?)",
        ("0987654321", "Program-related conviction", "2024-03-15", None),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def audit_dir(tmp_path: Path) -> Path:
    audit = tmp_path / "audit"
    audit.mkdir()
    return audit


def test_oig_check_excluded(leie_db: Path, audit_dir: Path) -> None:
    with (
        patch("mcp_servers.oig.server._DB_PATH", leie_db),
        patch("mcp_servers.oig.server._AUDIT_PATH", audit_dir / "oig_checks.jsonl"),
    ):
        result = oig_check(npi="0987654321", name="Sunshine Pain Management LLC")

    assert result["excluded"] is True
    assert result["exclusion_type"] == "Program-related conviction"
    assert result["exclusion_date"] == "2024-03-15"
    assert result["audit_ref"].startswith("OIG-")

    # Audit log must have been written
    log_entries = [
        json.loads(line)
        for line in (audit_dir / "oig_checks.jsonl").read_text().splitlines()
    ]
    assert len(log_entries) == 1
    assert log_entries[0]["excluded"] is True


def test_oig_check_clear(leie_db: Path, audit_dir: Path) -> None:
    with (
        patch("mcp_servers.oig.server._DB_PATH", leie_db),
        patch("mcp_servers.oig.server._AUDIT_PATH", audit_dir / "oig_checks.jsonl"),
    ):
        result = oig_check(npi="1234567890")

    assert result["excluded"] is False
    assert result["exclusion_type"] is None

    # Audit log written even on clear result
    log_entries = [
        json.loads(line)
        for line in (audit_dir / "oig_checks.jsonl").read_text().splitlines()
    ]
    assert len(log_entries) == 1
    assert log_entries[0]["excluded"] is False


def test_oig_check_db_missing(tmp_path: Path) -> None:
    with (
        patch("mcp_servers.oig.server._DB_PATH", tmp_path / "nonexistent.db"),
        patch("mcp_servers.oig.server._AUDIT_PATH", tmp_path / "audit" / "oig_checks.jsonl"),
    ):
        result = oig_check(npi="1111111111")

    assert result["excluded"] is False
    assert "error" in result
