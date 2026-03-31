from __future__ import annotations

from pathlib import Path

from pulp.models import CleanedPage, CleaningResult, DocumentClassification, DocumentMeta, StructuredDoc
from pulp.render import build_structured_doc, render_markdown


def test_render_markdown_writes_utf8_with_trailing_newline(tmp_path: Path) -> None:
    meta = DocumentMeta(
        source_path="in.pdf",
        page_count=1,
        file_size_bytes=0,
        classification=DocumentClassification.TEXT_LAYER,
        language=None,
    )
    doc = StructuredDoc(meta=meta, markdown="hello", warnings=[])

    out = tmp_path / "out.md"
    render_markdown(doc, output_path=out)
    assert out.read_text(encoding="utf-8") == "hello\n"


def test_build_structured_doc_joins_pages_in_order() -> None:
    meta = DocumentMeta(
        source_path="in.pdf",
        page_count=2,
        file_size_bytes=0,
        classification=DocumentClassification.TEXT_LAYER,
        language=None,
    )
    cleaned = CleaningResult(
        meta=meta,
        pages=[
            CleanedPage(page_number=1, clean_text="Page one", warnings=[]),
            CleanedPage(page_number=2, clean_text="Page two", warnings=[]),
        ],
        warnings=[],
    )

    doc = build_structured_doc(cleaned)
    assert doc.markdown == "Page one\n\nPage two\n"
