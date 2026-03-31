from __future__ import annotations

from pathlib import Path

import pdfplumber

from pulp.config import Settings
from pulp.models import DetectionResult, DocumentClassification, DocumentMeta


def detect_pdf(input_pdf: Path, *, settings: Settings) -> DetectionResult:
    """Classify PDF as text-layer vs scanned and return basic metadata."""
    input_pdf = Path(input_pdf)
    stat = input_pdf.stat()

    with pdfplumber.open(str(input_pdf)) as pdf:
        page_count = len(pdf.pages)
        if page_count < 1:
            raise ValueError("PDF has no pages.")

        sample_pages = max(1, min(settings.detect_sample_pages, page_count))
        sampled_indices = _sample_page_indices(page_count, sample_pages)

        sampled_chars: list[int] = []
        for page_index in sampled_indices:
            text = pdf.pages[page_index].extract_text() or ""
            sampled_chars.append(len(text.strip()))

    avg_chars_per_page = sum(sampled_chars) / max(1, len(sampled_chars))
    classification = (
        DocumentClassification.SCANNED
        if (settings.force_ocr or avg_chars_per_page < settings.scanned_chars_threshold)
        else DocumentClassification.TEXT_LAYER
    )

    meta = DocumentMeta(
        source_path=str(input_pdf),
        page_count=page_count,
        file_size_bytes=stat.st_size,
        classification=classification,
        language=None,
    )

    return DetectionResult(
        meta=meta,
        sampled_pages=len(sampled_indices),
        avg_chars_per_page=avg_chars_per_page,
    )


def _sample_page_indices(page_count: int, sample_pages: int) -> list[int]:
    sample_pages = max(1, min(sample_pages, page_count))
    if sample_pages == 1:
        return [0]

    indices: list[int] = []
    for k in range(sample_pages):
        # Evenly spaced, inclusive of first/last page.
        idx = round(k * (page_count - 1) / (sample_pages - 1))
        if idx not in indices:
            indices.append(idx)

    if len(indices) < sample_pages:
        for idx in range(page_count):
            if idx not in indices:
                indices.append(idx)
            if len(indices) >= sample_pages:
                break

    return indices
