from __future__ import annotations

from pathlib import Path

import pdfplumber

from pulp.config import Settings
from pulp.detect import _detect_language, detect_pdf
from pulp.models import DocumentClassification

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
PDFS_DIR = FIXTURES_DIR / "pdfs"


def test_detect_pdf_text_layer_metadata_and_avg_chars() -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"
    settings = Settings(detect_sample_pages=3, scanned_chars_threshold=50)

    result = detect_pdf(input_pdf, settings=settings)

    assert result.meta.page_count == 3
    assert result.meta.file_size_bytes == input_pdf.stat().st_size
    assert result.meta.classification == DocumentClassification.TEXT_LAYER
    assert result.sampled_pages == 3

    # Exactness check (same method used by detect): extracted chars of sampled pages.
    with pdfplumber.open(str(input_pdf)) as pdf:
        chars = [len((pdf.pages[i].extract_text() or "").strip()) for i in range(3)]
    expected = sum(chars) / 3
    assert result.avg_chars_per_page == expected


def test_detect_pdf_populates_language() -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"
    result = detect_pdf(input_pdf, settings=Settings())
    # Text-layer English PDF — language should be detected (not None).
    assert result.meta.language is not None
    assert isinstance(result.meta.language, str)


def test_detect_language_english() -> None:
    text = "The quick brown fox jumps over the lazy dog. " * 5
    lang = _detect_language(text)
    assert lang == "en"


def test_detect_language_german_diacritics() -> None:
    lang = _detect_language("Über die Straße gehen die Schüler zur Schule.")
    assert lang == "de"


def test_detect_language_french_diacritics() -> None:
    lang = _detect_language("Les élèves français apprennent à l'école avec plaisir.")
    assert lang == "fr"


def test_detect_language_too_short_returns_none() -> None:
    assert _detect_language("hi") is None


def test_detect_language_empty_returns_none() -> None:
    assert _detect_language("") is None
    assert _detect_language("   ") is None
