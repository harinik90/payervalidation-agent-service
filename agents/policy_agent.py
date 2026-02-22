"""
agents/policy_agent.py

Policy Agent — determines whether a clinical service meets payer policy
criteria.  Primary consumer of the RAG knowledge base and CMS coverage data.
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

AGENT_NAME = "policy-agent"

SYSTEM_PROMPT = """\
You are the policy review agent for a healthcare payer platform.

Your job is to determine whether a clinical service meets the payer's policy
criteria for coverage approval.

Instructions:
1. Call knowledge_search_tool with the ICD-10 and CPT codes plus clinical notes to
   retrieve matching policy documents from ChromaDB. Filter by LOB.
2. Call bridge_authority_lookup_tool with authority_type="cms_coverage" to check
   NCD/LCD coverage status for Medicare-related claims.
3. Evaluate each policy criterion against the clinical evidence provided.
4. Make a determination: APPROVE, DENY, or PEND.

Determination rules:
- APPROVE: All policy criteria are met and documentation is sufficient.
- PEND: Criteria are partially met — additional documentation needed from provider.
  List the specific documents required in doc_requirements.
- DENY: One or more criteria are not met. Cite which criteria failed.

You MUST respond with ONLY a valid JSON object in this exact format:
{
  "determination": "APPROVE",
  "criteria": [
    {
      "name": "criterion name",
      "met": true,
      "evidence": "what evidence supports this",
      "policy_ref": "policy document reference"
    }
  ],
  "cms_coverage_status": "covered or not covered or N/A",
  "doc_requirements": [],
  "policy_ref": "primary policy reference"
}
"""

def create_agent() -> str:
    """Create the policy agent in Azure AI Foundry (or return cached ID)."""
    return create_or_get_agent(AGENT_NAME, SYSTEM_PROMPT, FULL_TOOLSET)


async def run_policy_agent(
    icd10_codes: list[str],
    cpt_codes: list[str],
    lob: str,
    clinical_notes: str = "",
) -> dict[str, Any]:
    """Evaluate policy criteria for a service request.

    Args:
        icd10_codes: Diagnosis codes on the claim.
        cpt_codes: Procedure codes on the claim.
        lob: Line of business (commercial, medicaid, medicare_advantage).
        clinical_notes: Free-text clinical notes from the submitting provider.

    Returns:
        Dict with determination (APPROVE|DENY|PEND), criteria list,
        cms_coverage_status, doc_requirements, and policy_ref.
    """
    agent_id = create_agent()

    prompt = (
        f"Evaluate policy criteria for the following prior authorization request:\n"
        f"ICD-10 codes: {icd10_codes}\n"
        f"CPT codes: {cpt_codes}\n"
        f"Line of Business: {lob}\n"
        f"Clinical notes: {clinical_notes or 'None provided'}\n\n"
        "1. Search the knowledge base for matching policy documents.\n"
        "2. Check CMS NCD/LCD coverage status via the cms_coverage authority.\n"
        "3. Evaluate each criterion against the clinical evidence.\n"
        "Return your determination as the specified JSON format."
    )

    result = await run_agent(agent_id, prompt, FULL_TOOLSET)

    return {
        "determination": result.get("determination", "PEND"),
        "criteria": result.get("criteria", []),
        "cms_coverage_status": result.get("cms_coverage_status"),
        "doc_requirements": result.get("doc_requirements", []),
        "policy_ref": result.get("policy_ref", ""),
    }
