"""
agents/bridge.py

Async bridge — the single crossing point between the MAF layer and the
Claude Agent SDK + MCP layer.  MAF agents call bridge_authority_lookup()
as a regular Python tool.  Each call is stateless: a fresh Claude Agent SDK
session is created, the result is returned, and the session exits.
"""
from __future__ import annotations

import os

from claude_code_sdk import ClaudeCodeOptions, query

# ── MCP server registry ───────────────────────────────────────────────────────
# Official remote endpoints — no local process required.
# Custom local servers — spawned by Claude Agent SDK on demand.
MCP_REGISTRY: dict[str, dict] = {
    # Official remote
    "cms-coverage": {"url": "https://mcp.deepsense.ai/cms_coverage/mcp"},
    "npi-registry": {"url": "https://mcp.deepsense.ai/npi_registry/mcp"},
    "pubmed": {"url": "https://pubmed.mcp.claude.com/mcp"},
    # Custom local
    "payerai-knowledge": {"command": "python", "args": ["mcp_servers/knowledge/server.py"]},
    "payerai-icd10": {"command": "python", "args": ["mcp_servers/icd10/server.py"]},
    "payerai-oig": {"command": "python", "args": ["mcp_servers/oig/server.py"]},
    "payerai-regulatory": {"command": "python", "args": ["mcp_servers/regulatory/server.py"]},
}

# Which MCP servers each authority type requires.
AUTHORITY_MCP_MAP: dict[str, list[str]] = {
    "cms_coverage": ["cms-coverage"],
    "icd10": ["payerai-icd10"],
    "npi": ["npi-registry"],
    "oig": ["payerai-oig", "npi-registry"],
    "regulatory": ["payerai-regulatory"],
    "literature": ["pubmed"],
}

_BRIDGE_MODEL = os.environ.get("BRIDGE_MODEL", "claude-opus-4-6")


async def bridge_authority_lookup(authority_type: str, prompt: str) -> str:
    """Delegate an external authority query to Claude Agent SDK + MCP.

    Called by MAF agents whenever they need CMS, ICD-10, NPI, OIG, or
    regulatory data.  Never leaks MAF state into the Claude Agent SDK session.

    Args:
        authority_type: One of 'cms_coverage', 'icd10', 'npi', 'oig',
                        'regulatory', 'literature'.
        prompt: Natural-language query or structured lookup request.

    Returns:
        Plain-text result from the Claude Agent SDK session.

    Raises:
        ValueError: If authority_type is not registered in AUTHORITY_MCP_MAP.
    """
    if authority_type not in AUTHORITY_MCP_MAP:
        raise ValueError(
            f"Unknown authority_type '{authority_type}'. "
            f"Valid values: {list(AUTHORITY_MCP_MAP)}"
        )

    servers = {k: MCP_REGISTRY[k] for k in AUTHORITY_MCP_MAP[authority_type]}
    result: str | None = None

    async for message in query(
        prompt=prompt,
        options=ClaudeCodeOptions(
            model=_BRIDGE_MODEL,
            mcp_servers=servers,
            max_turns=5,
        ),
    ):
        if hasattr(message, "type") and message.type == "result":
            result = message.result

    return result or ""
