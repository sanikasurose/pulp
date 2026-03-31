from __future__ import annotations

from pathlib import Path

from pulp.clean import clean_extraction
from pulp.config import Settings
from pulp.detect import detect_pdf
from pulp.extract import extract_pdf
from pulp.models import ColumnsMode

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
PDFS_DIR = FIXTURES_DIR / "pdfs"


def test_clean_extraction_removes_noise_and_tracks_stats() -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"
    settings = Settings(columns_mode=ColumnsMode.OFF)

    detection = detect_pdf(input_pdf, settings=settings)
    extraction = extract_pdf(input_pdf, detection, settings=settings)
    cleaned = clean_extraction(extraction, settings=settings)

    assert cleaned.stats.removed_page_number_lines == 3
    assert cleaned.stats.removed_header_footer_lines == 6
    assert cleaned.stats.rejoined_hyphenations == 1
    assert cleaned.stats.reassembled_paragraphs >= 1
    assert cleaned.stats.dropped_blank_pages == 0

    assert len(cleaned.pages) == 3
    combined = "\n\n".join(p.clean_text for p in cleaned.pages)

    assert "DocClean PRD" not in combined
    assert "Confidential" not in combined
    assert "continued" not in combined.lower()
    assert "Page 1 of 3" not in combined
    assert "hyphenated" in combined
    assert "paragraph that continues across the page break" in combined
