"""
agents/orchestrator.py

Orchestrator — entry point for every prior authorization request.
Sequences sub-agent calls in compliance order, enforces hard-stop rules,
and assembles the final determination.

This is a pure Python async function (not a Foundry agent) that coordinates
the five MAF sub-agents.

Compliance ordering (hard rule):
  1. sanctions-agent  — MUST run first; hard stop on OIG match
  2. coding-agent     — validate ICD-10 + CPT before further processing
  3. eligibility-agent
  4. policy-agent
  5. regulatory-agent — only when policy result is PEND or DENY
"""
from __future__ import annotations

import logging
from typing import Any

from agents.sanctions_agent import run_sanctions_agent
from agents.coding_agent import run_coding_agent
from agents.eligibility_agent import run_eligibility_agent
from agents.policy_agent import run_policy_agent
from agents.regulatory_agent import run_regulatory_agent

logger = logging.getLogger(__name__)


async def run_orchestrator(request: dict[str, Any]) -> dict[str, Any]:
    """Run the full PA orchestration pipeline for a single request.

    Args:
        request: Dict with keys member_id, npi, icd10_codes, cpt_codes,
                 lob, service_date, clinical_notes, state (optional),
                 provider_name (optional).

    Returns:
        Dict with decision, hard_stop, reason, policy_refs, doc_requirements,
        and optional coding_issues, regulatory_refs, audit_ref.
    """
    member_id = request["member_id"]
    npi = request["npi"]
    provider_name = request.get("provider_name")
    icd10_codes = request["icd10_codes"]
    cpt_codes = request["cpt_codes"]
    lob = request["lob"]
    service_date = request["service_date"]
    clinical_notes = request.get("clinical_notes", "")
    state = request.get("state", "")

    # ── Step 1: Sanctions check (MUST be first) ─────────────────────────────
    logger.info("Step 1: Sanctions check for NPI %s", npi)
    sanctions = await run_sanctions_agent(npi=npi, name=provider_name)

    if sanctions.get("hard_stop") or sanctions.get("excluded"):
        logger.warning("HARD STOP: NPI %s excluded from OIG LEIE", npi)
        return {
            "decision": "DENIED",
            "hard_stop": True,
            "reason": (
                f"Provider NPI {npi} is excluded from federal healthcare programs "
                f"per OIG LEIE (exclusion type: {sanctions.get('exclusion_type', 'unknown')}, "
                f"effective: {sanctions.get('exclusion_date', 'unknown')}). "
                "No claims may be submitted or paid for this provider."
            ),
            "audit_ref": sanctions.get("audit_ref", ""),
            "policy_refs": [],
            "doc_requirements": [],
        }

    audit_ref = sanctions.get("audit_ref", "")

    # ── Step 2: Coding validation ────────────────────────────────────────────
    logger.info("Step 2: Coding validation for ICD-10=%s CPT=%s", icd10_codes, cpt_codes)
    coding = await run_coding_agent(
        icd10_codes=icd10_codes,
        cpt_codes=cpt_codes,
        service_date=service_date,
    )

    if not coding.get("codes_valid", True):
        issues = coding.get("issues", [])
        coding_issues = []
        for issue in issues:
            if isinstance(issue, dict):
                coding_issues.append({
                    "code": issue.get("code", ""),
                    "issue": issue.get("description", issue.get("issue", "")),
                })
            else:
                coding_issues.append({"code": "", "issue": str(issue)})

        logger.info("Coding issues found: %d — returning for correction", len(coding_issues))
        return {
            "decision": "RETURNED_FOR_CORRECTION",
            "hard_stop": False,
            "reason": (
                f"Submission contains {len(coding_issues)} coding issue(s). "
                "Correct and resubmit; eligibility and policy review will proceed "
                "after clean resubmission."
            ),
            "coding_issues": coding_issues,
            "audit_ref": audit_ref,
            "policy_refs": [],
            "doc_requirements": [],
        }

    # ── Step 3: Eligibility check ────────────────────────────────────────────
    logger.info("Step 3: Eligibility check for member=%s NPI=%s LOB=%s", member_id, npi, lob)
    eligibility = await run_eligibility_agent(
        member_id=member_id,
        npi=npi,
        lob=lob,
    )

    if not eligibility.get("member_eligible", True):
        return {
            "decision": "DENY",
            "hard_stop": False,
            "reason": "Member is not eligible for the requested service under the current benefit plan.",
            "audit_ref": audit_ref,
            "policy_refs": [],
            "doc_requirements": [],
        }

    if not eligibility.get("provider_valid", True):
        return {
            "decision": "DENY",
            "hard_stop": False,
            "reason": f"Provider NPI {npi} could not be validated or is not in-network.",
            "audit_ref": audit_ref,
            "policy_refs": [],
            "doc_requirements": [],
        }

    # ── Step 4: Policy evaluation ────────────────────────────────────────────
    logger.info("Step 4: Policy evaluation")
    policy = await run_policy_agent(
        icd10_codes=icd10_codes,
        cpt_codes=cpt_codes,
        lob=lob,
        clinical_notes=clinical_notes,
    )

    determination = policy.get("determination", "PEND")
    policy_refs = []
    if policy.get("policy_ref"):
        policy_refs.append(policy["policy_ref"])

    # ── Step 5: Regulatory check (only if DENY or PEND) ─────────────────────
    regulatory_refs: list[str] = []

    if determination in ("DENY", "PEND"):
        logger.info("Step 5: Regulatory check (policy determination=%s)", determination)
        regulatory = await run_regulatory_agent(
            icd10_codes=icd10_codes,
            cpt_codes=cpt_codes,
            lob=lob,
            state=state,
            service_date=service_date,
        )

        for item in regulatory.get("items", []):
            if isinstance(item, dict) and item.get("title"):
                ref = item["title"]
                if item.get("effective_date"):
                    ref += f" (eff. {item['effective_date']})"
                regulatory_refs.append(ref)

        if regulatory.get("override_flag") and determination == "DENY":
            logger.info("Regulatory override found — escalating DENY to PEND")
            determination = "PEND"
            reason = (
                f"Policy determination was DENY, but a regulatory mandate overrides "
                f"the internal policy. Escalating to PEND for manual review and policy update. "
                f"Regulatory references: {', '.join(regulatory_refs) or 'see items'}."
            )
            return {
                "decision": "PEND",
                "hard_stop": False,
                "reason": reason,
                "policy_refs": policy_refs,
                "regulatory_refs": regulatory_refs,
                "doc_requirements": policy.get("doc_requirements", []),
                "audit_ref": audit_ref,
            }
    else:
        logger.info("Step 5: Skipped (policy determination=%s)", determination)

    # ── Assemble final response ──────────────────────────────────────────────
    if determination == "APPROVE":
        reason = (
            "All prior authorization criteria have been met. "
            "OIG sanctions check cleared. Coding validated. "
            "Member eligibility confirmed. Clinical documentation supports medical necessity."
        )
    elif determination == "PEND":
        reason = policy.get("reason") or (
            "Service meets some policy criteria but additional documentation is required. "
            "See doc_requirements for items needed from the submitting provider."
        )
    elif determination == "DENY":
        reason = policy.get("reason") or (
            "One or more policy criteria were not met. See criteria details."
        )
    else:
        reason = f"Policy determination: {determination}"

    return {
        "decision": determination,
        "hard_stop": False,
        "reason": reason,
        "policy_refs": policy_refs,
        "doc_requirements": policy.get("doc_requirements", []),
        "regulatory_refs": regulatory_refs or None,
        "coding_issues": None,
        "audit_ref": audit_ref,
    }
