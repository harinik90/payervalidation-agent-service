"""
tools/knowledge.py

ChromaDB RAG wrapper — knowledge_search tool used by MAF agents to retrieve
policy, benefit, and regulatory documents from the local vector store.

PHI is never stored in ChromaDB — index content is policy text only.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

# chromadb uses pydantic v1 compat which is incompatible with Python >=3.14.
# Import is deferred to _get_client() so the module loads cleanly on 3.14;
# calls will raise at runtime until chromadb ships a 3.14-compatible release.
if TYPE_CHECKING:
    import chromadb

_DATA_DIR = os.environ.get("DATA_DIR", "./data")
_CHROMA_PATH = os.path.join(_DATA_DIR, "chroma")

_chroma_client: "chromadb.PersistentClient | None" = None


def _get_client() -> "chromadb.PersistentClient":
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        from chromadb.config import Settings
        _chroma_client = chromadb.PersistentClient(
            path=_CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
    return _chroma_client


async def knowledge_search(
    query: str,
    lob: str | None = None,
    policy_type: str | None = None,
    icd10_codes: list[str] | None = None,
    cpt_codes: list[str] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve policy chunks from ChromaDB matching the query and filters.

    Args:
        query: Natural-language or code-based search string.
        lob: Line of business filter (commercial, medicaid, medicare_advantage).
        policy_type: Filter by document type (policy, benefit, regulatory).
        icd10_codes: Optional ICD-10 code filter tags.
        cpt_codes: Optional CPT code filter tags.
        top_k: Number of results to return.

    Returns:
        List of dicts with keys: text, metadata (policy_number, lob,
        effective_date, policy_type, icd10_codes, cpt_codes), distance.
    """
    client = _get_client()

    try:
        collection = client.get_collection("payerai_policies")
    except Exception:
        return []

    where: dict[str, Any] = {}
    if lob:
        where["lob"] = lob
    if policy_type:
        where["policy_type"] = policy_type
    if icd10_codes:
        where["icd10_codes"] = {"$contains": icd10_codes[0]}
    if cpt_codes:
        where["cpt_codes"] = {"$contains": cpt_codes[0]}

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where if where else None,
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(docs, metas, distances)
    ]
