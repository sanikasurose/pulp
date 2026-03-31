from __future__ import annotations

from pathlib import Path

import pdfplumber

from pulp.config import Settings
from pulp.models import (
    ColumnsMode,
    DetectionResult,
    DocumentClassification,
    ExtractedPage,
    ExtractionResult,
)


def extract_pdf(
    input_pdf: Path, detection: DetectionResult, *, settings: Settings
) -> ExtractionResult:
    """Extract raw text (text-layer) or OCR text (scanned) from a PDF."""
    input_pdf = Path(input_pdf)

    if settings.force_ocr or detection.meta.classification == DocumentClassification.SCANNED:
        pages, warnings = _extract_pdf_ocr(
            input_pdf, page_count=detection.meta.page_count, settings=settings
        )
        return ExtractionResult(meta=detection.meta, pages=pages, warnings=warnings)

    warnings: list[str] = []
    pages: list[ExtractedPage] = []

    with pdfplumber.open(str(input_pdf)) as pdf:
        for i, page in enumerate(pdf.pages):
            if settings.columns_mode == ColumnsMode.OFF:
                raw_text = page.extract_text() or ""
            else:
                raw_text = _extract_page_columns_auto(page)

            pages.append(ExtractedPage(page_number=i + 1, raw_text=raw_text, ocr_confidence=None))

    _attempt_camelot_tables(input_pdf, warnings=warnings)

    return ExtractionResult(meta=detection.meta, pages=pages, warnings=warnings)


def _extract_pdf_ocr(
    input_pdf: Path, *, page_count: int, settings: Settings
) -> tuple[list[ExtractedPage], list[str]]:
    warnings: list[str] = []
    pages: list[ExtractedPage] = []

    try:
        from pdf2image import convert_from_path
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"OCR unavailable: pdf2image import failed ({exc.__class__.__name__}).")
        pages = [
            ExtractedPage(page_number=i + 1, raw_text="", ocr_confidence=None)
            for i in range(page_count)
        ]
        return pages, warnings

    try:
        import pytesseract
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"OCR unavailable: pytesseract import failed ({exc.__class__.__name__}).")
        pages = [
            ExtractedPage(page_number=i + 1, raw_text="", ocr_confidence=None)
            for i in range(page_count)
        ]
        return pages, warnings

    try:
        images = convert_from_path(str(input_pdf), dpi=300, thread_count=1)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"OCR page rendering failed ({exc.__class__.__name__}).")
        pages = [
            ExtractedPage(page_number=i + 1, raw_text="", ocr_confidence=None)
            for i in range(page_count)
        ]
        return pages, warnings

    for i in range(page_count):
        page_number = i + 1
        if i >= len(images):
            warnings.append(f"OCR missing rendered image for page {page_number}.")
            pages.append(ExtractedPage(page_number=page_number, raw_text="", ocr_confidence=None))
            continue

        image = _preprocess_ocr_image(images[i], page_number=page_number, warnings=warnings)

        try:
            text = pytesseract.image_to_string(image) or ""
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"OCR failed for page {page_number} ({exc.__class__.__name__}).")
            pages.append(ExtractedPage(page_number=page_number, raw_text="", ocr_confidence=None))
            continue

        confidence: float | None = None
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidence = _ocr_confidence_from_data(data)
        except Exception:  # noqa: BLE001
            confidence = None

        if confidence is not None and confidence < float(settings.ocr_low_confidence_threshold):
            warnings.append(f"Low OCR confidence on page {page_number} (avg={confidence:.1f}).")

        pages.append(
            ExtractedPage(page_number=page_number, raw_text=text, ocr_confidence=confidence)
        )

    return pages, warnings


def _preprocess_ocr_image(image: object, *, page_number: int, warnings: list[str]) -> object:
    try:
        from PIL import Image, ImageEnhance, ImageOps
    except Exception:
        return image

    if not isinstance(image, Image.Image):
        return image

    try:
        # Grayscale.
        out = ImageOps.grayscale(image)
        # Contrast enhancement (deterministic).
        out = ImageEnhance.Contrast(out).enhance(1.6)
        # Autocontrast to stretch values.
        out = ImageOps.autocontrast(out)
    except Exception as exc:  # noqa: BLE001
        warnings.append(
            f"OCR preprocessing failed for page {page_number} ({exc.__class__.__name__})."
        )
        return image

    return out


def _ocr_confidence_from_data(data: object) -> float | None:
    if not isinstance(data, dict):
        return None
    confs = data.get("conf")
    if not isinstance(confs, list):
        return None

    values: list[float] = []
    for v in confs:
        try:
            fv = float(v)
        except Exception:  # noqa: BLE001
            continue
        if fv < 0:
            continue
        if fv > 100:
            continue
        values.append(fv)

    if not values:
        return None
    return sum(values) / float(len(values))


def _attempt_camelot_tables(input_pdf: Path, *, warnings: list[str]) -> None:
    try:
        import camelot  # type: ignore

        # Deterministic, fast-ish attempt: first page only.
        tables = camelot.read_pdf(str(input_pdf), flavor="stream", pages="1")
        table_count = getattr(tables, "n", None)
        if table_count is None:
            try:
                table_count = len(tables)  # type: ignore[arg-type]
            except Exception:  # noqa: BLE001
                table_count = 0

        if int(table_count or 0) == 0 or _camelot_tables_look_empty(tables):
            warnings.append("No tables detected by Camelot.")
    except Exception as exc:  # noqa: BLE001 - must not crash on Camelot failures
        warnings.append(f"Camelot table extraction failed ({exc.__class__.__name__}).")


def _camelot_tables_look_empty(tables: object) -> bool:
    # Camelot occasionally returns a non-empty TableList with empty/degenerate frames.
    try:
        iterable = list(tables)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return True

    meaningful = 0
    for table in iterable:
        df = getattr(table, "df", None)
        if df is None:
            continue
        shape = getattr(df, "shape", None)
        if not shape or shape[0] < 2 or shape[1] < 2:
            continue
        try:
            values = df.to_numpy().ravel()
        except Exception:  # noqa: BLE001
            continue
        if any(str(v).strip() for v in values):
            meaningful += 1
    return meaningful == 0


def _extract_page_columns_auto(page: pdfplumber.page.Page) -> str:
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
    if not words:
        return page.extract_text() or ""

    midpoint = float(page.width) / 2.0
    left_words = [w for w in words if float(w.get("x0", 0.0)) < midpoint]
    right_words = [w for w in words if float(w.get("x0", 0.0)) >= midpoint]

    if not _looks_two_column(
        page_width=float(page.width),
        left_words=left_words,
        right_words=right_words,
    ):
        return page.extract_text() or ""

    left_text = _words_to_text(left_words)
    right_text = _words_to_text(right_words)

    if left_text and right_text:
        return f"{left_text}\n\n{right_text}"
    return left_text or right_text or (page.extract_text() or "")


def _looks_two_column(
    *, page_width: float, left_words: list[dict], right_words: list[dict]
) -> bool:
    total = len(left_words) + len(right_words)
    if total < 30:
        return False
    if len(left_words) < 10 or len(right_words) < 10:
        return False

    left_max_x1 = max(float(w.get("x1", w.get("x0", 0.0))) for w in left_words)
    right_min_x0 = min(float(w.get("x0", 0.0)) for w in right_words)
    gap = right_min_x0 - left_max_x1

    # Require a noticeable gap between the two clusters.
    return gap > max(24.0, page_width * 0.04)


def _words_to_text(words: list[dict]) -> str:
    # pdfplumber words contain at least: text, x0, top
    if not words:
        return ""

    sorted_words = sorted(words, key=lambda w: (float(w.get("top", 0.0)), float(w.get("x0", 0.0))))
    tolerance = 3.0

    lines: list[tuple[float, list[dict]]] = []
    for w in sorted_words:
        top = float(w.get("top", 0.0))
        if not lines or abs(top - lines[-1][0]) > tolerance:
            lines.append((top, [w]))
        else:
            lines[-1][1].append(w)

    out_lines: list[str] = []
    for _, line_words in lines:
        line_words = sorted(line_words, key=lambda w: float(w.get("x0", 0.0)))
        text = " ".join(str(w.get("text", "")).strip() for w in line_words).strip()
        if text:
            out_lines.append(text)

    return "\n".join(out_lines).strip()
