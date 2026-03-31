from __future__ import annotations

from pathlib import Path

from pulp.config import Settings
from pulp.detect import detect_pdf
from pulp.extract import extract_pdf
from pulp.models import ColumnsMode, DocumentClassification

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
PDFS_DIR = FIXTURES_DIR / "pdfs"


def test_extract_pdf_text_layer_includes_camelot_warning() -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"
    settings = Settings(columns_mode=ColumnsMode.OFF)

    detection = detect_pdf(input_pdf, settings=settings)
    assert detection.meta.classification == DocumentClassification.TEXT_LAYER

    extraction = extract_pdf(input_pdf, detection, settings=settings)
    assert len(extraction.pages) == detection.meta.page_count
    assert any("Camelot" in w or "tables" in w.lower() for w in extraction.warnings)


def test_extract_pdf_columns_auto_orders_two_column_reasonably() -> None:
    input_pdf = PDFS_DIR / "two_column.pdf"

    detection = detect_pdf(input_pdf, settings=Settings())

    extraction_off = extract_pdf(
        input_pdf, detection, settings=Settings(columns_mode=ColumnsMode.OFF)
    )
    text_off = extraction_off.pages[0].raw_text
    assert text_off

    extraction_auto = extract_pdf(
        input_pdf, detection, settings=Settings(columns_mode=ColumnsMode.AUTO)
    )
    text_auto = extraction_auto.pages[0].raw_text
    assert text_auto

    # In AUTO mode, we read left column top-to-bottom, then right column.
    assert "Left column line four has words\n\nRight column line one has words" in text_auto
    # In OFF mode, we should not see the explicit left-then-right column join marker.
    assert "Left column line four has words\n\nRight column line one has words" not in text_off
