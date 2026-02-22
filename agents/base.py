"""
agents/base.py

Shared Azure AI Foundry infrastructure for all MAF agents.

Provides:
- Singleton AIProjectClient
- Agent creation with in-memory caching
- Run execution using create_thread_and_process_run with auto tool calling
- JSON response parsing from assistant messages

The Azure SDK's FunctionTool accepts Python callables and auto-generates
JSON schemas from type hints.  Tool calls during a run are executed
automatically by the ToolSet.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    FunctionTool,
    MessageRole,
    RunStatus,
    ToolOutput,
    ToolSet,
)
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# ── Singleton client ─────────────────────────────────────────────────────────

_client: AIProjectClient | None = None
_agent_cache: dict[str, str] = {}  # name -> agent_id


def get_client() -> AIProjectClient:
    """Return the shared AIProjectClient singleton."""
    global _client
    if _client is None:
        endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT"]
        _client = AIProjectClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential(),
        )
    return _client


# ── Sync tool wrappers ───────────────────────────────────────────────────────
# FunctionTool requires sync callables.  These wrappers call into the async
# bridge/knowledge functions using asyncio.run(), which is safe because
# create_thread_and_process_run is executed via asyncio.to_thread() (no
# existing event loop in the worker thread).

def bridge_authority_lookup_tool(authority_type: str, prompt: str) -> str:
    """Query an external healthcare authority via Claude Agent SDK + MCP servers.

    Use this for CMS coverage validation, ICD-10 code lookups, NPI registry
    checks, OIG LEIE sanctions screening, and regulatory feed searches.

    Args:
        authority_type: The external authority to query.  One of: cms_coverage,
            icd10, npi, oig, regulatory, literature.
        prompt: Natural-language query or structured lookup request.
    """
    from agents.bridge import bridge_authority_lookup
    return asyncio.run(bridge_authority_lookup(authority_type, prompt))


def knowledge_search_tool(
    query: str,
    lob: str = "",
    policy_type: str = "",
    top_k: int = 5,
) -> str:
    """Search payer policy, benefit, and regulatory documents in ChromaDB.

    Returns relevant policy text chunks with metadata and distance scores.

    Args:
        query: Natural-language or code-based search string.
        lob: Line of business filter (commercial, medicaid, medicare_advantage).
        policy_type: Document type filter (policy, benefit, regulatory).
        top_k: Number of results to return.
    """
    from tools.knowledge import knowledge_search
    results = asyncio.run(
        knowledge_search(
            query=query,
            lob=lob or None,
            policy_type=policy_type or None,
            top_k=top_k,
        )
    )
    return json.dumps(results, default=str)


# ── Tool sets ────────────────────────────────────────────────────────────────

def _make_toolset(include_knowledge: bool = False) -> ToolSet:
    """Build a ToolSet with the bridge tool and optionally knowledge search."""
    functions = {bridge_authority_lookup_tool}
    if include_knowledge:
        functions.add(knowledge_search_tool)

    toolset = ToolSet()
    toolset.add(FunctionTool(functions=functions))
    return toolset


# Pre-built tool sets for agent types
BRIDGE_ONLY_TOOLSET = _make_toolset(include_knowledge=False)
FULL_TOOLSET = _make_toolset(include_knowledge=True)


# ── Agent lifecycle ──────────────────────────────────────────────────────────

def create_or_get_agent(
    name: str,
    instructions: str,
    toolset: ToolSet,
    model: str = "gpt-4o",
) -> str:
    """Create a Foundry agent or return its cached ID.

    If the environment variable ``{NAME}_AGENT_ID`` is set (uppercased, hyphens
    replaced with underscores), that value is used directly.  Otherwise a new
    agent is created in Azure AI Foundry and the ID is cached for the session.
    """
    env_key = name.upper().replace("-", "_") + "_AGENT_ID"
    env_id = os.environ.get(env_key, "").strip()
    if env_id:
        _agent_cache[name] = env_id
        logger.info("Agent '%s' loaded from env: %s", name, env_id)
        return env_id

    if name in _agent_cache:
        return _agent_cache[name]

    client = get_client()
    defs_and_resources = toolset.get_definitions_and_resources()
    agent = client.agents.create_agent(
        model=model,
        name=name,
        instructions=instructions,
        tools=defs_and_resources.get("tools", []),
        tool_resources=defs_and_resources.get("tool_resources"),
    )
    _agent_cache[name] = agent.id
    logger.info("Agent '%s' created: %s", name, agent.id)
    return agent.id


# ── Run execution ────────────────────────────────────────────────────────────

def _run_agent_sync(agent_id: str, user_message: str, toolset: ToolSet) -> dict[str, Any]:
    """Synchronous agent execution — called via asyncio.to_thread().

    Creates a thread, adds the user message, runs the agent with auto
    tool-call handling, and extracts the assistant's JSON response.
    """
    client = get_client()

    thread = client.agents.threads.create()
    client.agents.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=user_message,
    )

    run = client.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent_id,
        toolset=toolset,
    )

    if run.status != RunStatus.COMPLETED:
        logger.error("Agent run ended with status: %s (error: %s)", run.status, run.last_error)
        return {"error": f"Agent run failed: {run.status}", "details": str(run.last_error)}

    # Extract last assistant message
    last_msg = client.agents.messages.get_last_message_text_by_role(
        thread_id=thread.id,
        role=MessageRole.AGENT,
    )

    if last_msg is None:
        return {"error": "No assistant response found"}

    text = last_msg.text.value.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text}


async def run_agent(agent_id: str, user_message: str, toolset: ToolSet) -> dict[str, Any]:
    """Execute a Foundry agent run asynchronously.

    Wraps the synchronous SDK call in asyncio.to_thread so it doesn't
    block the FastAPI event loop.

    Args:
        agent_id: The Foundry agent ID to run.
        user_message: The user message to send to the agent.
        toolset: ToolSet with function tools for auto tool-call handling.

    Returns:
        Parsed JSON dict from the assistant's final message.
    """
    return await asyncio.to_thread(_run_agent_sync, agent_id, user_message, toolset)


# ── Initialization ───────────────────────────────────────────────────────────

def initialize_agents() -> dict[str, str]:
    """Create all sub-agents in Azure AI Foundry and return their IDs.

    Called once at startup by main.py.
    """
    from agents.sanctions_agent import create_agent as create_sanctions
    from agents.coding_agent import create_agent as create_coding
    from agents.eligibility_agent import create_agent as create_eligibility
    from agents.policy_agent import create_agent as create_policy
    from agents.regulatory_agent import create_agent as create_regulatory

    ids = {
        "sanctions": create_sanctions(),
        "coding": create_coding(),
        "eligibility": create_eligibility(),
        "policy": create_policy(),
        "regulatory": create_regulatory(),
    }
    logger.info("All agents initialized: %s", ids)
    return ids
