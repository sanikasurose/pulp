from __future__ import annotations

from pathlib import Path

import pytest

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
        input_pdf,
        detection,
        settings=Settings(columns_mode=ColumnsMode.OFF),
    )
    text_off = extraction_off.pages[0].raw_text
    assert text_off

    extraction_auto = extract_pdf(
        input_pdf,
        detection,
        settings=Settings(columns_mode=ColumnsMode.AUTO),
    )
    text_auto = extraction_auto.pages[0].raw_text
    assert text_auto

    # In AUTO mode, we read left column top-to-bottom, then right column.
    expected_join = "Left column line four has words\n\nRight column line one has words"
    assert expected_join in text_auto
    # In OFF mode, we should not see the explicit left-then-right column join marker.
    assert expected_join not in text_off


def test_extract_pdf_force_ocr_uses_mocked_tesseract_and_populates_confidence(
    mocker: pytest.MockFixture,
) -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"
    detection = detect_pdf(input_pdf, settings=Settings())
    assert detection.meta.classification == DocumentClassification.TEXT_LAYER

    page_count = detection.meta.page_count
    fake_images = [object() for _ in range(page_count)]

    mocker.patch("pdf2image.convert_from_path", return_value=fake_images)
    mocker.patch(
        "pytesseract.image_to_string",
        side_effect=[f"page {i+1} text" for i in range(page_count)],
    )
    mocker.patch(
        "pytesseract.image_to_data",
        return_value={"conf": ["95", "96", "-1", "94.0"]},
    )

    extraction = extract_pdf(input_pdf, detection, settings=Settings(force_ocr=True))
    assert len(extraction.pages) == page_count
    assert extraction.pages[0].raw_text == "page 1 text"
    assert extraction.pages[0].ocr_confidence is not None
    assert 94.9 < extraction.pages[0].ocr_confidence < 95.1
    assert not any("not implemented" in w.lower() for w in extraction.warnings)


def test_extract_pdf_ocr_page_failure_keeps_pipeline_alive(
    mocker: pytest.MockFixture,
) -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"
    detection = detect_pdf(input_pdf, settings=Settings())
    page_count = detection.meta.page_count
    fake_images = [object() for _ in range(page_count)]

    mocker.patch("pdf2image.convert_from_path", return_value=fake_images)

    def _image_to_string(img: object) -> str:
        if img is fake_images[0]:
            raise RuntimeError("tesseract crashed")
        return "ok"

    mocker.patch("pytesseract.image_to_string", side_effect=_image_to_string)
    mocker.patch("pytesseract.image_to_data", return_value={"conf": ["90"]})

    extraction = extract_pdf(input_pdf, detection, settings=Settings(force_ocr=True))
    assert extraction.pages[0].raw_text == ""
    assert extraction.pages[0].ocr_confidence is None
    assert extraction.pages[1].raw_text == "ok"
    assert any("OCR failed for page 1" in w for w in extraction.warnings)


def test_extract_pdf_ocr_confidence_is_optional(mocker: pytest.MockFixture) -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"
    detection = detect_pdf(input_pdf, settings=Settings())
    page_count = detection.meta.page_count
    fake_images = [object() for _ in range(page_count)]

    mocker.patch("pdf2image.convert_from_path", return_value=fake_images)
    mocker.patch("pytesseract.image_to_string", return_value="ok")
    mocker.patch("pytesseract.image_to_data", side_effect=ValueError("no data"))

    extraction = extract_pdf(input_pdf, detection, settings=Settings(force_ocr=True))
    assert extraction.pages[0].raw_text == "ok"
    assert extraction.pages[0].ocr_confidence is None
