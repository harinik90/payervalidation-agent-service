"""
agents/coding_agent.py

Coding Agent — validates and corrects ICD-10-CM/PCS and CPT/HCPCS codes.
Flags invalid codes, billability issues, FY mismatches, and CCI bundling
violations before the claim reaches policy review.
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

AGENT_NAME = "coding-agent"

SYSTEM_PROMPT = """\
You are the medical coding validation agent for a healthcare payer platform.

Your job is to validate ICD-10-CM and CPT/HCPCS codes on a claim submission.

Instructions:
1. For each ICD-10 code, call bridge_authority_lookup_tool with authority_type="icd10"
   to validate the code against the CMS fiscal year table for the given service_date.
2. Check for non-billable codes (header/category codes submitted as billable).
3. Check CPT codes against known CCI bundling edits:
   - 27447 bundles: 27370, 27310, 27330 (total knee arthroplasty)
   - 43644 bundles: 43235, 43239 (gastric bypass)
   - 63685 bundles: 63650 (SCS permanent includes trial)
4. Check for clinically redundant diagnosis pairs:
   - M17.11 (primary OA right knee) makes M25.361 (knee stiffness) redundant
5. Return a structured result.

Rules:
- Always validate against the ICD-10 FY table matching the claim's service_date.
- Flag non-billable codes (header/category codes submitted as billable).
- Suggest the most specific valid alternative if an invalid or imprecise code is submitted.
- Check CPT/HCPCS against known CCI bundling edits and mutually exclusive pairs.

You MUST respond with ONLY a valid JSON object in this exact format:
{
  "codes_valid": true,
  "issues": [],
  "corrected_codes": {
    "icd10": ["list of corrected ICD-10 codes"],
    "cpt": ["list of corrected CPT codes"]
  }
}

Each issue in the issues array should be:
{
  "code": "the code with the issue",
  "type": "INVALID | NON_BILLABLE | CCI_BUNDLE | REDUNDANT_DX",
  "description": "human-readable explanation",
  "suggestion": "suggested fix or null",
  "action": "REMOVE | REPLACE | REVIEW"
}
"""

def create_agent() -> str:
    """Create the coding agent in Azure AI Foundry (or return cached ID)."""
    return create_or_get_agent(AGENT_NAME, SYSTEM_PROMPT, BRIDGE_ONLY_TOOLSET)


async def run_coding_agent(
    icd10_codes: list[str],
    cpt_codes: list[str],
    service_date: str,
) -> dict[str, Any]:
    """Validate ICD-10 and CPT codes for a claim.

    Args:
        icd10_codes: Diagnosis codes to validate.
        cpt_codes: Procedure codes to validate.
        service_date: ISO date string (YYYY-MM-DD) — gates ICD-10 FY lookup.

    Returns:
        Dict with codes_valid, issues list, and corrected_codes.
    """
    agent_id = create_agent()

    prompt = (
        f"Validate the following codes for a claim with service date {service_date}:\n"
        f"ICD-10 codes: {icd10_codes}\n"
        f"CPT codes: {cpt_codes}\n\n"
        "For each ICD-10 code, look it up using the icd10 authority to check validity "
        "and billability. Then check CPT codes for CCI bundling violations. "
        "Also check for clinically redundant diagnosis pairs. "
        "Return your findings as the specified JSON format."
    )

    result = await run_agent(agent_id, prompt, BRIDGE_ONLY_TOOLSET)

    return {
        "codes_valid": result.get("codes_valid", True),
        "issues": result.get("issues", []),
        "corrected_codes": result.get("corrected_codes", {
            "icd10": list(icd10_codes),
            "cpt": list(cpt_codes),
        }),
    }
