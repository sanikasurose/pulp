from __future__ import annotations

import pytest

from pulp.config import Settings
from pulp.models import CleaningResult, DocumentClassification, DocumentMeta
from pulp.structure import structure_document


def test_structure_document_remains_stubbed() -> None:
    meta = DocumentMeta(
        source_path="in.pdf",
        page_count=1,
        file_size_bytes=0,
        classification=DocumentClassification.TEXT_LAYER,
        language=None,
    )
    cleaned = CleaningResult(meta=meta, pages=[], warnings=[])

    with pytest.raises(NotImplementedError):
        structure_document(cleaned, settings=Settings(), llm_enabled=False)
