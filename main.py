"""
main.py — PayerAI GPT entry point.

Initializes all Azure AI Foundry agents and starts the FastAPI server.

Usage:
    python main.py

The server runs on http://0.0.0.0:8000 by default.
The React frontend (http://localhost:5173) proxies API calls here.

Required environment variables (see .env):
    AZURE_AI_FOUNDRY_PROJECT  — Azure AI Foundry project endpoint
    AZURE_OPENAI_ENDPOINT     — Azure OpenAI for embeddings
    AZURE_OPENAI_API_KEY      — Azure OpenAI key
    ANTHROPIC_API_KEY          — Used by the bridge for Claude Agent SDK
"""
from __future__ import annotations

import logging
import os
import sys

# Load environment variables from .env before any other imports
from dotenv import load_dotenv
load_dotenv()

import uvicorn

from agents.base import initialize_agents

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _check_env() -> bool:
    """Verify required environment variables are set."""
    required = [
        "AZURE_AI_FOUNDRY_PROJECT",
    ]
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        logger.error("Copy .env.example to .env and fill in values.")
        return False
    return True


def main() -> None:
    """Initialize agents and start the server."""
    if not _check_env():
        sys.exit(1)

    logger.info("Initializing Azure AI Foundry agents...")
    try:
        agent_ids = initialize_agents()
        logger.info("Agents initialized successfully:")
        for name, aid in agent_ids.items():
            logger.info("  %s: %s", name, aid)
    except Exception:
        logger.exception("Failed to initialize agents")
        sys.exit(1)

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))

    logger.info("Starting PayerAI GPT server on %s:%d", host, port)
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
