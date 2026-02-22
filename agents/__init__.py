"""
agents — MAF agent layer for PayerAI GPT.

Sub-agents run in Azure AI Foundry (GPT-4o) with tool access to the bridge
(Claude Agent SDK + MCP servers) and knowledge search (ChromaDB RAG).

The orchestrator sequences sub-agent calls in compliance order.
"""
from agents.orchestrator import run_orchestrator
from agents.base import initialize_agents

__all__ = ["run_orchestrator", "initialize_agents"]
