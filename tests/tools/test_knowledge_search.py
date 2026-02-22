"""
tests/tools/test_knowledge_search.py

Unit tests for ChromaDB knowledge_search.
Mocks the ChromaDB client — never touches data/chroma/.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.knowledge import knowledge_search


def _mock_chroma_collection(docs, metas, distances):
    """Return a mock ChromaDB collection that returns fixed query results."""
    collection = MagicMock()
    collection.query.return_value = {
        "documents": [docs],
        "metadatas": [metas],
        "distances": [distances],
    }
    return collection


@pytest.mark.asyncio
async def test_knowledge_search_returns_results() -> None:
    mock_collection = _mock_chroma_collection(
        docs=["Policy text about knee arthroplasty."],
        metas=[{"policy_number": "POL-ORTHO-2024-007", "lob": "commercial"}],
        distances=[0.12],
    )
    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    with patch("tools.knowledge._get_client", return_value=mock_client):
        results = await knowledge_search("knee arthroplasty M17.11", lob="commercial")

    assert len(results) == 1
    assert results[0]["metadata"]["policy_number"] == "POL-ORTHO-2024-007"
    assert results[0]["distance"] == pytest.approx(0.12)


@pytest.mark.asyncio
async def test_knowledge_search_returns_empty_when_collection_missing() -> None:
    mock_client = MagicMock()
    mock_client.get_collection.side_effect = Exception("Collection not found")

    with patch("tools.knowledge._get_client", return_value=mock_client):
        results = await knowledge_search("some query")

    assert results == []


@pytest.mark.asyncio
async def test_knowledge_search_applies_lob_filter() -> None:
    mock_collection = _mock_chroma_collection([], [], [])
    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    with patch("tools.knowledge._get_client", return_value=mock_client):
        await knowledge_search("spinal cord stimulator", lob="commercial", policy_type="policy")

    call_kwargs = mock_collection.query.call_args.kwargs
    assert call_kwargs["where"] == {"lob": "commercial", "policy_type": "policy"}
