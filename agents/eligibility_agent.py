"""
agents/eligibility_agent.py

Eligibility Agent — confirms member benefits are active for the requested
service and that the rendering provider is valid and in-network.

NEVER runs before sanctions_agent clears the provider.
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

AGENT_NAME = "eligibility-agent"

SYSTEM_PROMPT = """\
You are the eligibility verification agent for a healthcare payer platform.

Your job is to verify that a rendering provider is valid and in-network, and that
the member has active coverage for the requested service.

Instructions:
1. Call bridge_authority_lookup_tool with authority_type="npi" to verify the provider's
   NPI is active, get their taxonomy/specialty, and practice address.
2. Call knowledge_search_tool to retrieve the member's benefit plan documents from
   the policy database, filtering by LOB (line of business).
3. Cross-reference the provider's specialty with the benefit plan's network rules.
4. Check whether the service requires a referral or step therapy.

Rules:
- Verify provider NPI is active and taxonomy matches the requested service.
- Confirm member has active coverage for the LOB and service category.
- Check whether the requested service requires a referral or step therapy.
- If benefit plan docs mention plan exclusions, note them.

You MUST respond with ONLY a valid JSON object in this exact format:
{
  "provider_valid": true,
  "provider_in_network": true,
  "member_eligible": true,
  "benefit_details": {
    "coverage_tier": "Tier 1",
    "copay": null,
    "plan_exclusions": []
  },
  "requires_referral": false
}
"""

def create_agent() -> str:
    """Create the eligibility agent in Azure AI Foundry (or return cached ID)."""
    return create_or_get_agent(AGENT_NAME, SYSTEM_PROMPT, FULL_TOOLSET)


async def run_eligibility_agent(
    member_id: str,
    npi: str,
    lob: str,
    service_category: str = "",
) -> dict[str, Any]:
    """Verify provider validity and member benefit eligibility.

    Args:
        member_id: Payer-assigned member identifier.
        npi: Rendering provider NPI.
        lob: Line of business.
        service_category: Service category for benefit lookup (optional).

    Returns:
        Dict with provider_valid, provider_in_network, member_eligible,
        benefit_details, and requires_referral.
    """
    agent_id = create_agent()

    prompt = (
        f"Verify eligibility for the following:\n"
        f"Member ID: {member_id}\n"
        f"Provider NPI: {npi}\n"
        f"Line of Business: {lob}\n"
        f"Service Category: {service_category or 'general'}\n\n"
        "1. Look up the provider NPI to confirm active status and specialty.\n"
        "2. Search the knowledge base for benefit plan coverage details.\n"
        "Return your findings as the specified JSON format."
    )

    result = await run_agent(agent_id, prompt, FULL_TOOLSET)

    return {
        "provider_valid": result.get("provider_valid", True),
        "provider_in_network": result.get("provider_in_network", True),
        "member_eligible": result.get("member_eligible", True),
        "benefit_details": result.get("benefit_details", {}),
        "requires_referral": result.get("requires_referral", False),
    }
