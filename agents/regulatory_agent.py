"""
agents/regulatory_agent.py

Regulatory Agent — identifies recent regulatory changes (federal rules, state
mandates, CMS notices) that affect the payer's coverage obligations.

Called by the orchestrator when policy determination is PEND or DENY to check
if a newer regulation overrides the policy document.
"""
from __future__ import annotations

import logging
from typing import Any

from agents.base import (
    FULL_TOOLSET,
    create_or_get_agent,
    run_agent,
)

logger = logging.getLogger(__name__)

AGENT_NAME = "regulatory-agent"

SYSTEM_PROMPT = """\
You are the regulatory intelligence agent for a healthcare payer platform.

Your job is to identify recent regulatory changes that may override a payer's
internal policy denial or pend decision.

Instructions:
1. Call bridge_authority_lookup_tool with authority_type="regulatory" to search for
   federal and state regulatory updates affecting the requested service codes.
2. Call knowledge_search_tool to find any indexed regulatory guidance in ChromaDB,
   filtering by policy_type="regulatory".
3. Determine whether any regulation mandates coverage that would override the
   payer's internal policy.

Rules:
- Search for regulatory updates effective on or before the service_date.
- Flag any federal or state rule that mandates coverage for the requested
  service/diagnosis combination.
- If a mandate is found, set override_flag=true — the orchestrator will use
  this to escalate a DENY to PEND for manual review.
- Be precise about jurisdiction (Federal vs state-specific).

You MUST respond with ONLY a valid JSON object in this exact format:
{
  "override_flag": false,
  "items": [
    {
      "title": "regulation title",
      "effective_date": "YYYY-MM-DD",
      "jurisdiction": "Federal or state code",
      "summary": "brief summary of impact",
      "mandates_coverage": false
    }
  ]
}
"""

def create_agent() -> str:
    """Create the regulatory agent in Azure AI Foundry (or return cached ID)."""
    return create_or_get_agent(AGENT_NAME, SYSTEM_PROMPT, FULL_TOOLSET)


async def run_regulatory_agent(
    icd10_codes: list[str],
    cpt_codes: list[str],
    lob: str,
    state: str,
    service_date: str,
    lookback_days: int = 730,
) -> dict[str, Any]:
    """Search for regulatory updates that may override a policy denial.

    Args:
        icd10_codes: Diagnosis codes on the claim.
        cpt_codes: Procedure codes on the claim.
        lob: Line of business.
        state: Two-letter state code for state mandate lookup.
        service_date: ISO date string — regulations must be effective on or before.
        lookback_days: How far back to search for regulatory changes (default 2 years).

    Returns:
        Dict with override_flag and items list of RegulatoryItem dicts.
    """
    agent_id = create_agent()

    prompt = (
        f"Search for regulatory updates that may affect coverage for:\n"
        f"ICD-10 codes: {icd10_codes}\n"
        f"CPT codes: {cpt_codes}\n"
        f"Line of Business: {lob}\n"
        f"State: {state or 'all'}\n"
        f"Service date: {service_date}\n"
        f"Lookback period: {lookback_days} days\n\n"
        "1. Search the regulatory authority for federal and state rules.\n"
        "2. Search the knowledge base for indexed regulatory guidance.\n"
        "Determine if any regulation mandates coverage that would override "
        "a payer's internal policy denial. "
        "Return your findings as the specified JSON format."
    )

    result = await run_agent(agent_id, prompt, FULL_TOOLSET)

    return {
        "override_flag": result.get("override_flag", False),
        "items": result.get("items", []),
    }
