"""
mcp/knowledge/server.py

Custom MCP server — payerai-knowledge.
Exposes the ChromaDB policy vector store as an MCP tool.

Backend: ChromaDB persistent store at data/chroma/.
PHI is never stored here — index content is policy text only.
"""
from __future__ import annotations

import asyncio

from mcp.server.fastmcp import FastMCP

from tools.knowledge import knowledge_search as _knowledge_search

mcp = FastMCP("payerai-knowledge")


@mcp.tool()
def knowledge_search(
    query: str,
    lob: str | None = None,
    policy_type: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Search policy, benefit, and regulatory documents in ChromaDB.

    Args:
        query: Natural-language or code-based search string.
        lob: Line of business filter (commercial, medicaid, medicare_advantage).
        policy_type: Document type filter (policy, benefit, regulatory).
        top_k: Number of results to return (default 5).

    Returns:
        List of dicts with text, metadata, and distance score.
    """
    return asyncio.run(_knowledge_search(query=query, lob=lob, policy_type=policy_type, top_k=top_k))


if __name__ == "__main__":
    mcp.run()
