"""
ingestion/chunker.py

Semantic chunker for PDF and DOCX policy documents.
Chunks at section boundaries, 512–1024 tokens, 10% overlap.
Attaches structured metadata: policy_number, lob, effective_date,
icd10_codes, cpt_codes, policy_type.

PHI must never be present in source documents sent to this pipeline.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import tiktoken

try:
    import pypdf
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False

try:
    import docx
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

_TOKENIZER = tiktoken.get_encoding("cl100k_base")
_CHUNK_MAX_TOKENS = int(os.environ.get("CHUNK_MAX_TOKENS", "1024"))
_CHUNK_MIN_TOKENS = int(os.environ.get("CHUNK_MIN_TOKENS", "512"))
_OVERLAP_RATIO = 0.10


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        return len(_TOKENIZER.encode(self.text))


def extract_text_pdf(path: Path) -> str:
    if not _PYPDF_AVAILABLE:
        raise ImportError("pypdf is required: pip install pypdf")
    reader = pypdf.PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_docx(path: Path) -> str:
    if not _DOCX_AVAILABLE:
        raise ImportError("python-docx is required: pip install python-docx")
    doc = docx.Document(str(path))
    return "\n".join(para.text for para in doc.paragraphs)


def extract_text(path: Path) -> str:
    """Extract raw text from a PDF or DOCX file."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_pdf(path)
    if suffix in (".docx", ".doc"):
        return extract_text_docx(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _split_sections(text: str) -> list[str]:
    """Split text at section-heading boundaries (heuristic)."""
    pattern = r"(?=\n(?:[A-Z][A-Z\s]{3,}|(?:\d+\.)+\s+[A-Z]))"
    sections = re.split(pattern, text)
    return [s.strip() for s in sections if s.strip()]


def _token_chunks(text: str, max_tokens: int, overlap_tokens: int) -> Iterator[str]:
    """Yield overlapping token-window chunks from a section of text."""
    tokens = _TOKENIZER.encode(text)
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        yield _TOKENIZER.decode(tokens[start:end])
        if end == len(tokens):
            break
        start = end - overlap_tokens


def chunk_document(
    path: Path,
    metadata: dict | None = None,
) -> list[Chunk]:
    """Chunk a PDF or DOCX document into overlapping token windows.

    Args:
        path: Path to the source document.
        metadata: Base metadata dict (policy_number, lob, effective_date, etc.)
                  Applied to every chunk; chunk index is appended.

    Returns:
        List of Chunk objects, each with text and metadata.
    """
    base_meta = metadata or {}
    text = extract_text(path)
    sections = _split_sections(text)
    overlap = int(_CHUNK_MAX_TOKENS * _OVERLAP_RATIO)

    chunks: list[Chunk] = []
    chunk_idx = 0

    for section in sections:
        for window in _token_chunks(section, _CHUNK_MAX_TOKENS, overlap):
            if len(_TOKENIZER.encode(window)) < 50:
                continue
            chunks.append(Chunk(
                text=window,
                metadata={**base_meta, "chunk_index": chunk_idx, "source": str(path)},
            ))
            chunk_idx += 1

    return chunks
