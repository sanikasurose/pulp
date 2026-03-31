from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli import app
from pulp.clean import clean_extraction
from pulp.config import Settings
from pulp.detect import detect_pdf
from pulp.extract import extract_pdf
from pulp.models import ColumnsMode
from pulp.render import build_structured_doc, render_markdown

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
PDFS_DIR = FIXTURES_DIR / "pdfs"
EXPECTED_DIR = FIXTURES_DIR / "expected"


@pytest.mark.parametrize(
    ("pdf_name", "expected_name"),
    [
        ("simple_noise.pdf", "simple_noise.md"),
        ("two_column.pdf", "two_column.md"),
    ],
)
def test_pipeline_end_to_end_text_layer(
    tmp_path: Path,
    pdf_name: str,
    expected_name: str,
) -> None:
    input_pdf = PDFS_DIR / pdf_name
    expected_md = (EXPECTED_DIR / expected_name).read_text(encoding="utf-8")

    settings = Settings(columns_mode=ColumnsMode.AUTO)
    detection = detect_pdf(input_pdf, settings=settings)
    extraction = extract_pdf(input_pdf, detection, settings=settings)
    cleaned = clean_extraction(extraction, settings=settings)
    doc = build_structured_doc(cleaned)

    out1 = tmp_path / f"{pdf_name}.md"
    render_markdown(doc, output_path=out1)
    got1 = out1.read_text(encoding="utf-8")
    assert got1 == expected_md

    # Determinism: identical output on rerun.
    out2 = tmp_path / f"{pdf_name}.rerun.md"
    render_markdown(doc, output_path=out2)
    got2 = out2.read_text(encoding="utf-8")
    assert got2 == expected_md


def test_pipeline_end_to_end_force_ocr_is_deterministic_with_mocks(
    tmp_path: Path, mocker: pytest.MockFixture
) -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"

    detection = detect_pdf(input_pdf, settings=Settings())
    page_count = detection.meta.page_count
    fake_images = [object() for _ in range(page_count)]

    mocker.patch("pdf2image.convert_from_path", return_value=fake_images)
    mocker.patch(
        "pytesseract.image_to_string",
        side_effect=[f"OCR page {i + 1} content is here." for i in range(page_count)],
    )
    mocker.patch("pytesseract.image_to_data", return_value={"conf": ["90"]})

    settings = Settings(force_ocr=True, columns_mode=ColumnsMode.AUTO)
    detection2 = detect_pdf(input_pdf, settings=settings)
    extraction = extract_pdf(input_pdf, detection2, settings=settings)
    cleaned = clean_extraction(extraction, settings=settings)
    doc = build_structured_doc(cleaned)

    out1 = tmp_path / "ocr.md"
    render_markdown(doc, output_path=out1)
    got1 = out1.read_text(encoding="utf-8")
    assert got1 == (
        "OCR page 1 content is here.\n\n"
        "OCR page 2 content is here.\n\n"
        "OCR page 3 content is here.\n"
    )

    out2 = tmp_path / "ocr.rerun.md"
    render_markdown(doc, output_path=out2)
    got2 = out2.read_text(encoding="utf-8")
    assert got2 == got1


def test_cli_diff_integration(tmp_path: Path) -> None:
    input_pdf = PDFS_DIR / "simple_noise.pdf"
    out_md = tmp_path / "cli.md"

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            str(input_pdf),
            "--no-llm",
            "--diff",
            "-o",
            str(out_md),
        ],
    )
    assert result.exit_code == 0
    assert out_md.exists()
    assert "classification: TEXT_LAYER" in result.stderr
    assert "llm.enabled: false" in result.stderr
