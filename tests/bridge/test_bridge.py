"""
tests/bridge/test_bridge.py

Unit tests for bridge_authority_lookup.
Mocks claude_code_sdk.query — never hits real MCP servers or the Anthropic API.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.bridge import AUTHORITY_MCP_MAP, MCP_REGISTRY, bridge_authority_lookup


@pytest.fixture()
def mock_query():
    """Async generator that yields a single result message."""
    async def _gen(*args, **kwargs):
        yield SimpleNamespace(type="result", result="mocked authority response")

    with patch("agents.bridge.query", side_effect=_gen) as m:
        yield m


@pytest.mark.asyncio
async def test_bridge_oig_uses_correct_servers(mock_query) -> None:
    result = await bridge_authority_lookup("oig", "Screen NPI 0987654321")

    assert result == "mocked authority response"
    call_kwargs = mock_query.call_args.kwargs
    servers = call_kwargs["options"].mcp_servers
    assert "payerai-oig" in servers
    assert "npi-registry" in servers


@pytest.mark.asyncio
async def test_bridge_cms_coverage_uses_correct_server(mock_query) -> None:
    await bridge_authority_lookup("cms_coverage", "NCD for M17.11 CPT 27447")

    servers = mock_query.call_args.kwargs["options"].mcp_servers
    assert "cms-coverage" in servers
    assert len(servers) == 1


@pytest.mark.asyncio
async def test_bridge_icd10_uses_local_server(mock_query) -> None:
    await bridge_authority_lookup("icd10", "Validate M17.11 for 2025-10-15")

    servers = mock_query.call_args.kwargs["options"].mcp_servers
    assert "payerai-icd10" in servers


@pytest.mark.asyncio
async def test_bridge_invalid_authority_raises() -> None:
    with pytest.raises(ValueError, match="Unknown authority_type"):
        await bridge_authority_lookup("unknown_authority", "some prompt")


@pytest.mark.asyncio
async def test_bridge_returns_empty_string_on_no_result() -> None:
    async def _no_result(*args, **kwargs):
        yield SimpleNamespace(type="text", text="intermediate text")

    with patch("agents.bridge.query", side_effect=_no_result):
        result = await bridge_authority_lookup("npi", "verify NPI 1234567890")

    assert result == ""
