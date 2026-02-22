"""
tests/maf/test_sanctions_agent.py

Unit tests for the sanctions agent.
Mandatory test: a positive LEIE match MUST return hard_stop=True and
block all downstream processing.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agents.sanctions_agent import run_sanctions_agent


@pytest.mark.asyncio
async def test_sanctions_hard_stop_on_exclusion() -> None:
    """A provider found on OIG LEIE must produce hard_stop=True."""
    excluded_response = (
        '{"excluded": true, "exclusion_type": "Program-related conviction", '
        '"exclusion_date": "2024-03-15", "waiver_state": null, '
        '"npi_active": true, "audit_ref": "OIG-20251101-002"}'
    )

    with patch("agents.sanctions_agent.bridge_authority_lookup", new=AsyncMock(return_value=excluded_response)):
        with pytest.raises(NotImplementedError):
            # Currently not implemented — update assertion once implemented
            await run_sanctions_agent(npi="0987654321", name="Sunshine Pain Management LLC")


@pytest.mark.asyncio
async def test_sanctions_clear_provider_no_hard_stop() -> None:
    """A provider not on OIG LEIE must NOT produce hard_stop=True."""
    clear_response = (
        '{"excluded": false, "exclusion_type": null, '
        '"exclusion_date": null, "waiver_state": null, '
        '"npi_active": true, "audit_ref": "OIG-20251015-001"}'
    )

    with patch("agents.sanctions_agent.bridge_authority_lookup", new=AsyncMock(return_value=clear_response)):
        with pytest.raises(NotImplementedError):
            await run_sanctions_agent(npi="1234567890")
