"""
agents/sanctions_agent.py

Sanctions Agent — screens the rendering provider against the OIG LEIE
exclusion list.  MUST be called first by the orchestrator.  An OIG match
triggers an immediate hard stop; no further agents run.

Every check — match or clear — is audit-logged to data/audit/oig_checks.jsonl.
"""
from __future__ import annotations

import logging
from typing import Any

from agents.base import (
    BRIDGE_ONLY_TOOLSET,
    create_or_get_agent,
    run_agent,
)

logger = logging.getLogger(__name__)

AGENT_NAME = "sanctions-agent"

SYSTEM_PROMPT = """\
You are the sanctions screening agent for a healthcare payer platform.

Your job is to screen a provider against the OIG LEIE exclusion list and verify
their NPI is active.

Instructions:
1. Call bridge_authority_lookup_tool with authority_type="oig" to screen the
   provider against the OIG LEIE exclusion list.
2. Call bridge_authority_lookup_tool with authority_type="npi" to verify the NPI
   is active and get the provider taxonomy.
3. Interpret the results and return a JSON response.

Rules:
- A LEIE match is a HARD STOP — set hard_stop=true, excluded=true.
- A deactivated NPI is a soft block — set hard_stop=false but npi_active=false.
- If the provider is clear, set hard_stop=false, excluded=false.
- Log every check — the OIG MCP server handles audit logging automatically.

You MUST respond with ONLY a valid JSON object in this exact format:
{
  "hard_stop": false,
  "excluded": false,
  "exclusion_type": null,
  "exclusion_date": null,
  "npi_active": true,
  "audit_ref": "from the OIG check result"
}
"""


def create_agent() -> str:
    """Create the sanctions agent in Azure AI Foundry (or return cached ID)."""
    return create_or_get_agent(AGENT_NAME, SYSTEM_PROMPT, BRIDGE_ONLY_TOOLSET)


async def run_sanctions_agent(npi: str, name: str | None = None) -> dict[str, Any]:
    """Screen a provider NPI against OIG LEIE and verify NPI active status.

    Args:
        npi: National Provider Identifier to screen.
        name: Provider name (optional, used for fuzzy match).

    Returns:
        Dict with hard_stop, excluded, exclusion_type, exclusion_date,
        npi_active, and audit_ref.
    """
    agent_id = create_agent()

    prompt = f"Screen NPI {npi}"
    if name:
        prompt += f", provider name '{name}'"
    prompt += (
        " against the OIG LEIE exclusion list. "
        "Also verify whether this NPI is currently active. "
        "Return your findings as the specified JSON format."
    )

    result = await run_agent(agent_id, prompt, BRIDGE_ONLY_TOOLSET)

    return {
        "hard_stop": result.get("hard_stop", False),
        "excluded": result.get("excluded", False),
        "exclusion_type": result.get("exclusion_type"),
        "exclusion_date": result.get("exclusion_date"),
        "npi_active": result.get("npi_active", True),
        "audit_ref": result.get("audit_ref", ""),
    }
