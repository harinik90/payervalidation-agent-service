"""
tests/ingestion/test_chunker.py

Unit tests for the semantic chunker.
Tests chunking logic, metadata attachment, and token window sizes.
Does not require real PDF/DOCX files — uses temp text files via monkeypatching.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ingestion.chunker import Chunk, chunk_document


# Helper: create a temp .pdf-named file with text content via mocked extract_text
SAMPLE_POLICY_TEXT = """
POLICY: POL-ORTHO-2024-007
LINE OF BUSINESS: Commercial
EFFECTIVE DATE: 2024-01-01

1. COVERAGE CRITERIA

1.1 Total Knee Arthroplasty (CPT 27447) is covered for members who meet ALL of the following:
   (a) Diagnosis of osteoarthritis of the knee (M17.x) confirmed by imaging
   (b) Failure of at least 6 months of conservative therapy
   (c) Functional impairment documented by treating physician

1.2 Conservative therapy includes physical therapy, anti-inflammatory medication,
and intra-articular injections.

2. DOCUMENTATION REQUIREMENTS

The following must be submitted with the prior authorization request:
   - Operative report (post-service)
   - Imaging reports (X-ray or MRI within 12 months)
   - Documentation of failed conservative therapy

3. EXCLUSIONS

Services are not covered if the member has an active infection at the surgical site
or if the BMI exceeds plan limits without documented medical clearance.
""" * 3  # repeat to ensure multiple chunks


@pytest.fixture()
def policy_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "POL-ORTHO-2024-007.pdf"
    p.touch()  # empty file; extract_text will be mocked
    return p


def test_chunk_returns_list_of_chunks(policy_pdf: Path) -> None:
    with patch("ingestion.chunker.extract_text", return_value=SAMPLE_POLICY_TEXT):
        chunks = chunk_document(policy_pdf, metadata={"policy_number": "POL-ORTHO-2024-007", "lob": "commercial"})

    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)


def test_chunk_metadata_attached(policy_pdf: Path) -> None:
    meta = {"policy_number": "POL-ORTHO-2024-007", "lob": "commercial", "effective_date": "2024-01-01"}
    with patch("ingestion.chunker.extract_text", return_value=SAMPLE_POLICY_TEXT):
        chunks = chunk_document(policy_pdf, metadata=meta)

    for chunk in chunks:
        assert chunk.metadata["policy_number"] == "POL-ORTHO-2024-007"
        assert chunk.metadata["lob"] == "commercial"
        assert "chunk_index" in chunk.metadata


def test_chunk_token_size_within_bounds(policy_pdf: Path) -> None:
    with patch("ingestion.chunker.extract_text", return_value=SAMPLE_POLICY_TEXT):
        chunks = chunk_document(policy_pdf)

    for chunk in chunks:
        assert chunk.token_count <= 1024, f"Chunk exceeds max tokens: {chunk.token_count}"
        assert chunk.token_count >= 50, f"Chunk too small: {chunk.token_count}"


def test_chunk_unsupported_format(tmp_path: Path) -> None:
    bad_file = tmp_path / "doc.txt"
    bad_file.touch()
    with pytest.raises(ValueError, match="Unsupported file type"):
        chunk_document(bad_file)
