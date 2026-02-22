"""
tests/maf/test_orchestrator.py

Unit tests for orchestrator agent routing and guardrail logic.
Asserts that sanctions runs first, hard stops halt downstream agents,
and regulatory agent is only called on PEND/DENY.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_orchestrator_sanctions_runs_first() -> None:
    """Sanctions agent must be called before any other agent."""
    pytest.skip("Orchestrator not yet implemented — add assertions once run_orchestrator is built.")


@pytest.mark.asyncio
async def test_orchestrator_hard_stop_halts_all_downstream() -> None:
    """When sanctions returns hard_stop=True, no other agents run."""
    pytest.skip("Orchestrator not yet implemented.")


@pytest.mark.asyncio
async def test_orchestrator_regulatory_called_on_deny() -> None:
    """Regulatory agent is called when policy determination is DENY."""
    pytest.skip("Orchestrator not yet implemented.")


@pytest.mark.asyncio
async def test_orchestrator_regulatory_not_called_on_approve() -> None:
    """Regulatory agent is NOT called when policy determination is APPROVE."""
    pytest.skip("Orchestrator not yet implemented.")


@pytest.mark.asyncio
async def test_orchestrator_coding_error_returns_before_policy() -> None:
    """When coding agent returns codes_valid=False, policy/eligibility are NOT called."""
    pytest.skip("Orchestrator not yet implemented.")
